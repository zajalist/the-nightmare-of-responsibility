"""Rebuild only the two escape queues with the pawn-relative camera (QA B2 2026-11-10: the fixed escape-one camera
framed his bent body): EscapeClothingOne (mode 2) and EscapeClothingTwo (mode 3). build_clothing_chase.write_queue.
  python Tools/Unreal/flow/rebuild_escape_views.py"""
import os
import sys
sys.path[:0] = ['P:/FoA/Tools/Unreal', 'P:/FoA/Tools/Unreal/player', 'P:/FoA/Tools/Unreal/flow']
import hayba_call as h  # noqa: E402
import build_clothing_chase as chase  # noqa: E402

os.environ['HAYBA_AGENT_ID'] = 'story'
assert not chase.call('editor_get_state')['pie_running'], 'PIE running'
token = h.lease_acquire('story', ['asset:' + chase.P], ttl_s=180, wait_s=180)
try:
    for row in (('EscapeClothingOne', 5, 6, 2), ('EscapeClothingTwo', 6, 7, 3)):
        chase.write_queue(*row)
    print('escape cameras face the landing, away from him')
finally:
    h.release('story', token)
