"""One pin: ClearClothingHanger's fallback stand (when he started the unhook off the floor) moves to (105,-110,89), the
first spot by the bed that held a standing player with the wardrobe down in PIE (t7_hanger.json, 2026-11-10); the
survey's (150,-110) refused the teleport (the bed-foot chest). patch_chase_cutaway.T7_STAND matches."""
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
    ns, _ = inspect(P, 'ClearClothingHanger')
    mt = [n for n in ns if n['title'] == 'MakeTransform']
    assert len(mt) == 1, mt
    if '105' not in next(p.get('default_value') or '' for p in mt[0]['pins'] if p['name'] == 'Location'):
        b = Batch(P, 'ClearClothingHanger')
        b.pin(mt[0]['node_id'], 'Location', '105,-110,89')
        b.run()
    print('fallback stand at 105,-110,89')
finally:
    h.release('story', tok)
