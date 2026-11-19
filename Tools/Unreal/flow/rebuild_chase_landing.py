"""Rebuild only the two chase queues that read LANDINGS[2] (EscapeClothingTwo flies the shirt there; ReachClothingVase
starts from it) after the landing moved to the bay floor below the windowsill vase (2026-11-09). Uses
build_clothing_chase.write_queue unchanged; nothing else in the chase is rebuilt.
  python Tools/Unreal/flow/rebuild_chase_landing.py"""
import os
import sys
sys.path[:0] = ['P:/FoA/Tools/Unreal', 'P:/FoA/Tools/Unreal/player', 'P:/FoA/Tools/Unreal/flow']
import hayba_call as h  # noqa: E402
import build_clothing_chase as chase  # noqa: E402
from clothing_chase_contract import LANDINGS  # noqa: E402

os.environ['HAYBA_AGENT_ID'] = 'story'
assert not chase.call('editor_get_state')['pie_running'], 'PIE running'
token = h.lease_acquire('story', ['asset:' + chase.P], ttl_s=180, wait_s=120)
try:
    for row in (('EscapeClothingTwo', 6, 7, 3), ('ReachClothingVase', 7, 8, 4)):
        chase.write_queue(*row)
    print('chase landing rebuilt at', LANDINGS[2])
finally:
    h.release('story', token)
