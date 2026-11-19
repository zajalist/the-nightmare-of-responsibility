"""SkipWakeUp loses the director's own fade (main, 2026-11-09): the post-wake hold and fade-up now has one owner,
BP_FoAPlayer (anim lane). Removes the held StartCameraFade(1 -> 1) after WakeUpDone, the SkipFadeUp timer, and the
SkipFadeUp event with its fade-up. GoToEndAndStop, BedSettleStart and WakeUpDone stay. Idempotent; build_director.py
matches.  python Tools/Unreal/flow/patch_skip_fade.py"""
import json
import os
import sys
from pathlib import Path

sys.path[:0] = ['P:/FoA/Tools/Unreal', 'P:/FoA/Tools/Unreal/player']
import hayba_call as h  # noqa: E402
from held_tool_graphs import Batch, inspect  # noqa: E402

P = '/Game/FoA/Gameplay/BP_BeatDirector'


def pin(n, name):
    return next((p.get('default_value') for p in n['pins'] if p['name'] == name), None)


os.environ['HAYBA_AGENT_ID'] = 'story'
assert not h.call('editor_get_state', {})['data']['pie_running'], 'PIE running'
token = h.lease_acquire('story', ['asset:' + P], ttl_s=120, wait_s=180)
try:
    ns, es = inspect(P, 'EventGraph')
    by = {n['node_id']: n for n in ns}
    feeds = lambda nid, p: [e['from_node'] for e in es if e['to_node'] == nid and e['to_pin'] == p]  # noqa: E731
    doomed = set()
    for n in ns:
        fade = n['title'] == 'StartCameraFade'
        if fade and pin(n, 'FromAlpha') == '1.0' and pin(n, 'ToAlpha') == '1.0' and pin(n, 'Duration') in ('0.01', '0.010000'):
            doomed.add(n['node_id'])                                        # the held black after WakeUpDone
        if n['title'] == 'Set Timer by Function Name' and pin(n, 'FunctionName') == 'SkipFadeUp':
            doomed.add(n['node_id'])
        if n['title'] == 'SkipFadeUp' and not any(p['name'] == 'self' and p['direction'] == 'input' for p in n['pins']):
            doomed.add(n['node_id'])                                        # the custom event
            for e in es:
                if e['from_node'] == n['node_id'] and e['from_pin'] == 'then':
                    doomed.add(e['to_node'])                                # its fade-up
    for nid in list(doomed):                                                # their camera-manager getters
        for src in feeds(nid, 'self'):
            if by[src]['title'] == 'GetPlayerCameraManager' and all(e['to_node'] in doomed for e in es if e['from_node'] == src):
                doomed.add(src)
    comments = [n['node_id'] for n in ns if n['title'] in ('Fade up after skip',)]
    report = {'removed': sorted(by[n]['title'] for n in doomed), 'comments': len(comments)}
    if doomed:
        b = Batch(P, 'EventGraph')
        b.ops.append(dict(op='remove', node_ids=sorted(doomed) + comments))
        b.run()
    ns, es = inspect(P, 'EventGraph')
    assert not any(n['title'] == 'SkipFadeUp' or pin(n, 'FunctionName') == 'SkipFadeUp' for n in ns)
    for keep in ('SkipWakeUp', 'GoToEndAndStop', 'WakeUpDone'):
        assert any(n['title'] == keep for n in ns), keep
    assert any(pin(n, 'ParameterName') == 'BedSettleStart' for n in ns)
    Path('P:/FoA/Saved/StoryShots/skip_fade_removed.json').write_text(json.dumps(report, indent=1))
    print('skip fade removed', report)
finally:
    h.release('story', token)
