# MIT Non-Commercial License
# Copyright (c) 2025 Rick Lan
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, for non-commercial purposes only, subject to the following conditions:
#
# - The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
# - Commercial use (e.g., use in a product, service, or activity intended to generate revenue) is prohibited without explicit written permission from Rick Lan. Contact ricklan@gmail.com for inquiries.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

from opendbc.car.interfaces import RadarInterfaceBase
from opendbc.can.parser import CANParser
from opendbc.car.structs import RadarData
from typing import List, Tuple, Dict, Optional

BUS = 1

class RadarConfig:
    DREL_OFFSET = -1.2 # in meters
    MAX_TRACKING_OBJS = 50

def _create_radar_parser():
    messages = [("Status", 16.7), ("ObjectData", 0)]
    return CANParser('u_radar', messages, BUS)

def _create_radar_object_parser():
    messages = [(f"ObjectData_{i}", 0) for i in range(RadarConfig.MAX_TRACKING_OBJS)]
    return CANParser('u_radar', messages, BUS)


class RadarInterface(RadarInterfaceBase):
    def __init__(self, CP):
        super().__init__(CP)

        self.updated_messages = set()

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
        count = 0

        for record in records:
            if count >= RadarConfig.MAX_TRACKING_OBJS:
                break

            if record[0] == 0x60B:
                new_list_append((count + 383, record[1], record[2]))
                count += 1

        return [(can_strings[0][0], new_list)], len(new_list)

    def _is_valid_track(self, obj_d_rel: float, obj_class: int, obj_rcs: float, obj_movement: int) -> bool:
        return (obj_d_rel > 0. and
                (obj_class == 1 or obj_rcs > 0.) and
                obj_movement != 2)

    def update(self, can_strings: List[Tuple]) -> Optional[RadarData]:
        if self.rcp is None:
            return super().update(None)

        vls = self.rcp.update_strings(can_strings)
        self.updated_messages.update(vls)

        # update radar points
        if 0x60B in self.updated_messages:
            parsable_can_string, obj_count = self._create_parsable_object_can_strings(can_strings)
            self.rop.update_strings(parsable_can_string)

            for i in range(obj_count):
                cpt = self.rop.vl[f'ObjectData_{i}']

                # Update object properties in batch
                track_id = int(cpt['ID'])
                obj_class = int(cpt['Class'])
                obj_rcs = float(cpt['RCS'])
                obj_movement = int(cpt['DynProp'])
                obj_yv_rel = float(cpt['VRelLat'])
                obj_d_rel = float(cpt['DistLong']) + RadarConfig.DREL_OFFSET
                obj_y_rel = -float(cpt['DistLat'])
                obj_v_rel = float(cpt['VRelLong'])

                # skip invalid objects
                if not self._is_valid_track(obj_d_rel, obj_class, obj_rcs, obj_movement):
                    if track_id in self.pts:
                        del self.pts[track_id]
                    continue

                if track_id not in self.pts:
                    self.pts[track_id] = RadarData.RadarPoint()
                    self.pts[track_id].trackId = track_id

                # update points
                point = self.pts[track_id]
                point.yvRel = obj_yv_rel
                point.dRel = obj_d_rel
                point.yRel = obj_y_rel
                point.vRel = obj_v_rel
                point.aRel = float('nan')

        # dispatch
        if 0x60A in self.updated_messages:
            ret = RadarData()
            # do not check can_valid
            ret.errors = []

            ret.points = list(self.pts.values()) if self.pts else []

            self.updated_messages.clear()
            self.pts.clear()

            return ret

        self.updated_messages.clear()
        return None