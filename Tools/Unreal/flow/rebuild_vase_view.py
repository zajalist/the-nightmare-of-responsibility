"""Rebuild only the two chase graphs that film the final reach from inside the bay (main's decision (b), 2026-11-09):
ReachClothingVase (mode 4 view: VASE_VIEW -> VASE_FOCUS) and FrameClothingBoss (BOSS_VIEW -> BOSS_FOCUS). The room's
ClueViewVase/ClueViewBoss markers looked through the closed bay curtain. Uses build_clothing_chase unchanged otherwise.
  python Tools/Unreal/flow/rebuild_vase_view.py"""
import os
import sys
sys.path[:0] = ['P:/FoA/Tools/Unreal', 'P:/FoA/Tools/Unreal/player', 'P:/FoA/Tools/Unreal/flow']
import hayba_call as h  # noqa: E402
import build_clothing_chase as chase  # noqa: E402
from clothing_chase_contract import VASE_VIEW, BOSS_VIEW  # noqa: E402

os.environ['HAYBA_AGENT_ID'] = 'story'
assert not chase.call('editor_get_state')['pie_running'], 'PIE running'
token = h.lease_acquire('story', ['asset:' + chase.P], ttl_s=180, wait_s=180)
try:
    chase.write_queue('ReachClothingVase', 7, 8, 4)
    chase.frame_boss()
    print('vase and boss filmed from inside the bay', VASE_VIEW, BOSS_VIEW)
finally:
    h.release('story', token)
