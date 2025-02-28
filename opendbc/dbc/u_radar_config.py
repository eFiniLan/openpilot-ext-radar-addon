#!/usr/bin/env python3
# MIT Non-Commercial License
# Copyright (c) 2025 Rick Lan
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, for non-commercial purposes only, subject to the following conditions:
#
# - The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
# - Commercial use (e.g., use in a product, service, or activity intended to generate revenue) is prohibited without explicit written permission from Rick Lan. Contact ricklan@gmail.com for inquiries.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

from panda import Panda
from opendbc.car.structs import CarParams
import hashlib
import time

MAGIC = "5f501a8e1ac815293bc23e72f126a8a4"
BUS = 0
GET_CONFIG_CAN_ID = 513
SET_CONFIG_CAN_ID = 0x200

def get_config_msg(msgs):
    val = None
    for msg in msgs:
        id = msg[0]
        bus = msg[2]
        if id == GET_CONFIG_CAN_ID and bus == BUS:
            val = msg[1]
            break
    return val

def config_is_correct(val):
    hash_val = hashlib.md5(val).hexdigest()
    if hash_val == MAGIC:
        return True
    return False

if __name__ == "__main__":
    panda = Panda()
    msgs = panda.can_recv()
    config_msg = get_config_msg(msgs)
    if config_msg is None:
        print("Radar Config Message not found, maybe on a different bus?")
    else:
        if not config_is_correct(config_msg):
            print("Invalid Radar Configuration, Setting now...")
            panda.set_safety_mode(CarParams.SafetyModel.allOutput)
            panda.can_send(SET_CONFIG_CAN_ID, b'\x7F\x14\x00\x00\x08\x1D\x03\x10', BUS)
            time.sleep(3)
            msgs = panda.can_recv()
            msg = get_config_msg(msgs)
            print("Radar Configuration update successful." if config_is_correct(msg) else "Radar Configuration update failed, please try again.")
        else:
            print("Radar Configuration is correct.")
    panda.close()