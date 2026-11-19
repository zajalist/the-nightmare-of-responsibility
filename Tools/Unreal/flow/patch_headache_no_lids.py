"""In-play headaches no longer close the HUD eyelids (QA 2026-11-09: the bars read as a letterbox, which the contract
reserves for cinematics). StepHeadache keeps its echo distortion and the montage; its two eyelid closures (the blink math
and the ApplyHeadacheBlink call) are removed. EndHeadache still calls ApplyHeadacheBlink(0), so the lids stay open.
build_story_moments.py no longer runs build_headache_blink.py. Idempotent.
  python Tools/Unreal/flow/patch_headache_no_lids.py"""
import json
import os
import sys
from pathlib import Path

sys.path[:0] = ['P:/FoA/Tools/Unreal', 'P:/FoA/Tools/Unreal/player']
import hayba_call as h  # noqa: E402
from held_tool_graphs import Batch, inspect  # noqa: E402

P = '/Game/FoA/Gameplay/BP_BeatDirector'
os.environ['HAYBA_AGENT_ID'] = 'story'
assert not h.call('editor_get_state', {})['data']['pie_running'], 'PIE running'
token = h.lease_acquire('story', ['asset:' + P], ttl_s=120, wait_s=180)
try:
    ns, es = inspect(P, 'StepHeadache')
    by = {n['node_id']: n for n in ns}
    eyes = [n['node_id'] for n in ns if n['title'] == 'ApplyHeadacheBlink']
    doomed = set(eyes)
    frontier = list(eyes)
    while frontier:                                   # every pure node that only feeds the blink
        nid = frontier.pop()
        for e in es:
            if e['to_node'] == nid and e['to_pin'] not in ('execute',):
                src = e['from_node']
                outs = {x['to_node'] for x in es if x['from_node'] == src}
                if src not in doomed and outs <= doomed and not any(p['name'] in ('execute', 'then') for p in by[src]['pins']):
                    doomed.add(src)
                    frontier.append(src)
    comments = [n['node_id'] for n in ns if n['title'] == 'Two brief eyelid closures']
    report = {'removed': sorted(by[n]['title'] for n in doomed), 'comments': len(comments)}
    if doomed:
        b = Batch(P, 'StepHeadache')
        b.ops.append(dict(op='remove', node_ids=sorted(doomed) + comments))
        b.run()
    ns, _ = inspect(P, 'StepHeadache')
    assert not any(n['title'] == 'ApplyHeadacheBlink' for n in ns)
    assert any(n['title'] == 'SetEchoStrength' for n in ns)
    ns, _ = inspect(P, 'EndHeadache')
    assert any(n['title'] == 'ApplyHeadacheBlink' for n in ns), 'EndHeadache must still reopen the lids'
    Path('P:/FoA/Saved/StoryShots/headache_no_lids.json').write_text(json.dumps(report, indent=1))
    print('headache eyelids removed', report)
finally:
    h.release('story', token)
