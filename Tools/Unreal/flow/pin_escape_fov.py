"""One pin (QA B2 audit 2026-11-10): the escapes' lens, OnClothingCameraReady's SetFieldOfView for non-toss modes, 70 -> 55,
so the side camera keeps him out of the view cone. build_clothing_chase.build_motion matches."""
import os
import sys
sys.path[:0] = ['P:/FoA/Tools/Unreal', 'P:/FoA/Tools/Unreal/player']
import hayba_call as h  # noqa: E402
from held_tool_graphs import Batch, inspect  # noqa: E402

P = '/Game/FoA/Gameplay/BP_BeatDirector'
os.environ['HAYBA_AGENT_ID'] = 'story'
assert not h.call('editor_get_state', {})['data']['pie_running'], 'PIE running'
tok = h.lease_acquire('story', ['asset:' + P], ttl_s=120, wait_s=180)
try:
    ns, _ = inspect(P, 'OnClothingCameraReady')
    fov = [n for n in ns if n['title'] == 'SetFieldOfView']
    assert len(fov) == 1, fov
    b = Batch(P, 'OnClothingCameraReady')
    b.pin(fov[0]['node_id'], 'InFieldOfView', 55)
    b.run()
    print('escape lens 55')
finally:
    h.release('story', tok)
