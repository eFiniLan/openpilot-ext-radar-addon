'''
MIT Non-Commercial License
Copyright (c) 2025 Rick Lan

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, for non-commercial purposes only, subject to the following conditions:

- The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
- Commercial use (e.g., use in a product, service, or activity intended to generate revenue) is prohibited without explicit written permission from Rick Lan. Contact ricklan@gmail.com for inquiries.
- Any project that uses the Software must visibly mention the following acknowledgment: "This project uses software from Rick Lan and is licensed under a custom license requiring permission for use."

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
'''

from opendbc.car.interfaces import RadarInterfaceBase
from opendbc.can.parser import CANParser
from opendbc.car.structs import RadarData
from typing import List, Tuple

DREL_OFFSET = -1.2 # car head to radar
MAX_OBJECTS = 50
MAX_LAT_DIST = 3.6 # lat distance
RCS_MIN = 0.
RCS_MAX = 30.

STATIONARY_OBJ_VREL = -20.
STATIONARY_OBJ_LAT_DIST = 3.

# Constants for static point filtering
# 33hz * 5 secs for decay
INITIAL_SCORE = 33*5

def _create_radar_parser():
  messages = [("ObjectData", 0)]
  messages += [(f"ObjectData_{i}", 0) for i in range(MAX_OBJECTS)]
  return CANParser('u_radar', messages, 1)


class RadarInterface(RadarInterfaceBase):
  def __init__(self, CP):
    super().__init__(CP)

    self.updated_messages = set()
    self.objs: dict[int, dict] = {}

    self.rcp = _create_radar_parser()

    self._radar_points = {}
    self._radar_point_properties = {}


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

  # called by card.py, 100hz
  def update(self, can_strings):
    self.frame += 1
    if self.rcp is None:
      return super().update(None)

    vls = self.rcp.update_strings(can_strings)
    self.updated_messages.update(vls)

    # update radar points
    if 0x60B in self.updated_messages:
      # parse objects, stored into objs array
      parsable_can_string, size = self._create_parsable_object_can_strings(can_strings)
      self.rcp.update_strings(parsable_can_string)

      # Batch update objects
      for i in range(size):
        cpt = self.rcp.vl[f'ObjectData_{i}']

        track_id = int(cpt['ID'])

        prev_track = self._radar_points[track_id] if track_id in self._radar_points else None

        if prev_track is None:
          self._radar_points[track_id] = RadarData.RadarPoint()
          self._radar_points[track_id].trackId = track_id

        if track_id not in self._radar_point_properties:
          self._radar_point_properties[track_id] = {
            'class': 0,
            'rcs': 0.,
            'movement': 0,
            'score': INITIAL_SCORE,
          }

        # radarPoint
        self._radar_points[track_id].yvRel = float(cpt['VRelLat'])
        self._radar_points[track_id].dRel = float(cpt['DistLong']) + DREL_OFFSET
        self._radar_points[track_id].yRel = -float(cpt['DistLat'])
        self._radar_points[track_id].vRel = float(cpt['VRelLong'])
        self._radar_points[track_id].aRel = float('nan')
        self._radar_points[track_id].measured = True

        # other properties
        self._radar_point_properties[track_id] = {
          'class': int(cpt['Class']),
          'rcs': float(cpt['RCS']),
          'movement': int(cpt['DynProp']),
        }

        # reset score when:
        # 1. it was not previously exists
        # 2. object has moved
        if prev_track is None or \
           'score' not in self._radar_point_properties[track_id] or \
          (
            prev_track.dRel != self._radar_points[track_id].dRel or \
		        prev_track.yRel != self._radar_points[track_id].yRel or \
		        prev_track.vRel != self._radar_point_properties[track_id].vRel or \
		        prev_track.yvRel != self._radar_point_properties[track_id].yvRel
          ):
          self._radar_point_properties[track_id]['score'] = INITIAL_SCORE

    self.updated_messages.clear()

    # published to liveTracks via card.py
    # liveTracks is 20hz
    # radard.py subscribed liveTracks, and is running at 20hz
    # publish at 33 hz
    if self.frame % 3 == 0:
      for track_id in list(self._radar_points.keys()):
        should_remove = False
        if track_id in self._radar_point_properties:
          # decay
          self._radar_point_properties[track_id]['score'] -= 1

          # idle too long
          if not should_remove and self._radar_point_properties[track_id]['score'] < 0:
            should_remove = True

          # on coming
          if not should_remove and self._radar_point_properties[track_id]['movement'] == 2:
            should_remove = True

          # ignore stationary object on the left/right when driving fast
          if not should_remove and self._radar_points[track_id].vRel < STATIONARY_OBJ_VREL and abs(self._radar_points[track_id].yRel) > STATIONARY_OBJ_LAT_DIST:
            should_remove = True

          # RCS (radar cross section) not within the range
          if not should_remove and not (RCS_MIN <= self._radar_point_properties[track_id]['rcs'] <= RCS_MAX):
            should_remove = True

          # object is outside the lat dist (too far left or too far right)
          if not should_remove and abs(self._radar_points[track_id].yRel) > MAX_LAT_DIST:
            should_remove = True

        # we don't need to remove elements in self._radar_points_properties (not necessary)
        if should_remove and track_id in self.pts:
          del self._radar_points[track_id]

      # update pts array
      self.pts = self._radar_points

      ret = RadarData()
      ret.points = list(self.pts.values()) if self.pts else []
      return ret

    # return None to card.py so it will not try to publish to liveTracks
    return None
