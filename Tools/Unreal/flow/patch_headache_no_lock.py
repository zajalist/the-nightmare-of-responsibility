"""In-play headaches never take control (QA B1 2026-11-09, main's pick (b)): the inner-voice line plays over gameplay
with the interactor live, so a prompt on screen stays usable. StartHeadache keeps its cached refs, the echo distortion
pulse and its timers; it loses StopMovementImmediately, StopJumping, SetIgnoreMoveInput/LookInput(true),
SetCinematic(true) and the headache montage. EndHeadache loses their exact counterparts (StopAnimMontage,
SetCinematic(false), SetIgnoreMoveInput/LookInput(false)), so no other system's input-ignore count is touched.
Idempotent; build_story_moments.py matches.  python Tools/Unreal/flow/patch_headache_no_lock.py"""
import json
import os
import sys
from pathlib import Path

sys.path[:0] = ['P:/FoA/Tools/Unreal', 'P:/FoA/Tools/Unreal/player']
import hayba_call as h  # noqa: E402
from held_tool_graphs import Batch, inspect  # noqa: E402

P = '/Game/FoA/Gameplay/BP_BeatDirector'
DROP = {'StartHeadache': ('StopMovementImmediately', 'StopJumping', 'SetIgnoreMoveInput', 'SetIgnoreLookInput', 'SetCinematic',
                          'PlayAnimMontage', 'Play Anim Montage'),
        'EndHeadache': ('StopAnimMontage', 'Stop Anim Montage', 'SetCinematic', 'SetIgnoreMoveInput', 'SetIgnoreLookInput')}


def strip(graph):
    ns, es = inspect(P, graph)
    by = {n['node_id']: n for n in ns}
    gone = {n['node_id'] for n in ns if n['title'] in DROP[graph]}
    if not gone:
        return []
    b = Batch(P, graph)
    # bridge the exec chain over each removed run: the predecessor's pin goes to the first survivor after it
    def survivor(nid):
        while nid in gone:
            nxt = [e for e in es if e['from_node'] == nid and e['from_pin'] == 'then']
            if not nxt:
                return None
            nid, pin = nxt[0]['to_node'], nxt[0]['to_pin']
        return nid
    for e in es:
        if e['to_node'] in gone and e['to_pin'] == 'execute' and e['from_node'] not in gone:
            after = survivor(e['to_node'])
            if after:
                b.link(e['from_node'], e['from_pin'], after, 'execute')
    # pure helpers that only fed removed nodes go too
    doomed = set(gone)
    changed = True
    while changed:
        changed = False
        for n in ns:
            nid = n['node_id']
            if nid in doomed or any(p['name'] in ('execute', 'then') for p in n['pins']):
                continue
            outs = {e['to_node'] for e in es if e['from_node'] == nid}
            if outs and outs <= doomed:
                doomed.add(nid)
                changed = True
    b.ops.insert(0, dict(op='remove', node_ids=sorted(doomed)))
    b.run()
    return sorted(by[n]['title'] for n in doomed)


os.environ['HAYBA_AGENT_ID'] = 'story'
assert not h.call('editor_get_state', {})['data']['pie_running'], 'PIE running'
token = h.lease_acquire('story', ['asset:' + P], ttl_s=120, wait_s=180)
try:
    report = {g: strip(g) for g in DROP}
    for g in DROP:
        ns, _ = inspect(P, g)
        assert not any(n['title'] in DROP[g] for n in ns), g
    ns, _ = inspect(P, 'StepHeadache')
    assert any(n['title'] == 'SetEchoStrength' for n in ns)
    Path('P:/FoA/Saved/StoryShots/headache_no_lock.json').write_text(json.dumps(report, indent=1))
    print('headache no longer takes control', report)
finally:
    h.release('story', token)
