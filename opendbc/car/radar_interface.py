# MIT Non-Commercial License
# Copyright (c) 2025 Rick Lan
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, for non-commercial purposes only, subject to the following conditions:
#
# - The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
# - Commercial use (e.g., use in a product, service, or activity intended to generate revenue) is prohibited without explicit written permission from Rick Lan. Contact ricklan@gmail.com for inquiries.
# - Any project that uses the Software must visibly mention the following acknowledgment: "This project uses software from Rick Lan and is licensed under a custom license requiring permission for use."
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

from opendbc.car.interfaces import RadarInterfaceBase
from opendbc.can.parser import CANParser
from opendbc.car.structs import RadarData
from typing import List, Tuple, Optional, Dict

DREL_OFFSET = -1.3 # car head to radar
MAX_OBJECTS = 50
MAX_LAT_DIST = 1.2 # lat distance
MIN_LON_DIST = 1.5 # long distance
FREQ = 5 # 20 hz

def _create_radar_parser():
    messages = [("ObjectData", 0)]
    return CANParser('u_radar', messages, 1)

def _create_radar_object_parser():
    messages = [(f"ObjectData_{i}", 0) for i in range(MAX_OBJECTS)]
    return CANParser('u_radar', messages, 1)


class RadarInterface(RadarInterfaceBase):
    def __init__(self, CP):
        super().__init__(CP)

        self.updated_messages = set()
        self.objs: dict[int, dict] = {}

        self._radar_points_cache = {}
        self.rcp = _create_radar_parser()
        self.rop = _create_radar_object_parser()

    def _create_parsable_object_can_strings(self, can_strings: List[Tuple]) -> Tuple[List[Tuple], int]:
        """Optimized object string parsing with minimal allocations."""
        if not can_strings or not isinstance(can_strings[0], tuple) or len(can_strings[0]) < 2:
            return [], 0

        # Pre-allocate list with known maximum size
        new_list = []
        new_list_append = new_list.append  # Local reference for faster access

        records = can_strings[0][1]
        id_num = 1

        for record in records:
            if id_num > MAX_OBJECTS:
                break

            if record[0] == 0x60B:
                new_list_append((id_num + 383, record[1], record[2]))
                id_num += 1

        return [(can_strings[0][0], new_list)], len(new_list)

    def _is_valid_track(self, obj: Dict) -> bool:
        return (obj['d_rel'] > MIN_LON_DIST and
                abs(obj['y_rel']) < MAX_LAT_DIST and
                (obj['class'] == 1 or obj['rcs'] > 0.) and
                obj['movement'] != 2)

    def _update_pts(self, track_id: int, obj: Dict) -> None:
        if self._is_valid_track(obj):
            if track_id not in self.pts:
                if track_id in self._radar_points_cache:
                    self.pts[track_id] = self._radar_points_cache[track_id]
                else:
                    self.pts[track_id] = RadarData.RadarPoint()
                    self.pts[track_id].trackId = track_id
                    self._radar_points_cache[track_id] = self.pts[track_id]

            point = self.pts[track_id]
            point.yvRel = obj['yv_rel']
            point.dRel = obj['d_rel']
            point.yRel = obj['y_rel']
            point.vRel = obj['v_rel']
            point.aRel = float('nan')

        elif track_id in self.pts:
            del self.pts[track_id]

    def update(self, can_strings):
        if self.rcp is None:
            return super().update(None)

        self.frame += 1
        vls = self.rcp.update_strings(can_strings)
        self.updated_messages.update(vls)

        # update radar points
        if 0x60B in self.updated_messages:

            # parse objects, stored into objs array
            parsable_can_string, size = self._create_parsable_object_can_strings(can_strings)
            self.rop.update_strings(parsable_can_string)

            # Batch update objects
            for i in range(size):
                cpt = self.rop.vl[f'ObjectData_{i}']

                track_id = int(cpt['ID'])
                if track_id not in self.objs:
                    self.objs[track_id] = {}

                self.objs[track_id] = {
                    'track_id': track_id,
                    'class': int(cpt['Class']),
                    'rcs': float(cpt['RCS']),
                    'movement': int(cpt['DynProp']),
                    'yv_rel': float(cpt['VRelLat']),
                    'd_rel': float(cpt['DistLong']) + DREL_OFFSET,
                    'y_rel': -float(cpt['DistLat']),
                    'v_rel': float(cpt['VRelLong'])
                }

        self.updated_messages.clear()

        # dispatch
        if self.frame % FREQ == 0:
            # update self.pts before dispatch
            for track_id, obj in self.objs.items():
                self._update_pts(track_id, obj)

            ret = RadarData()
            ret.points = list(self.pts.values()) if self.pts else []
            return ret

        return None