"""Wake-up hand-off for the retimed LS_WakeUp (19.1 s; anim lane, verified by main 2026-11-09). Narrow Hayba pin edits,
idempotent; build_director.py carries the same values:
- PlayWakeUp: MPC_FoAPlayer.BedSettleStart = Now + 9.37 (was + 19.7). Skip still writes Now.
- WakeUpDone: SetControlRotation(MakeRotator(pitch -10, yaw 195)) (was yaw 55), so the first gameplay view faces the room.
  python Tools/Unreal/flow/patch_wake_handoff.py"""
import json
import os
import sys
from pathlib import Path

sys.path[:0] = ['P:/FoA/Tools/Unreal', 'P:/FoA/Tools/Unreal/player']
import hayba_call as h  # noqa: E402
from held_tool_graphs import Batch, inspect  # noqa: E402

P = '/Game/FoA/Gameplay/BP_BeatDirector'
SETTLE, PITCH, YAW = 9.37, -10.0, 195.0


def pin(n, name):
    return next((p.get('default_value') for p in n['pins'] if p['name'] == name), None)


os.environ['HAYBA_AGENT_ID'] = 'story'
assert not h.call('editor_get_state', {})['data']['pie_running'], 'PIE running'
token = h.lease_acquire('story', ['asset:' + P], ttl_s=120, wait_s=180)
report = {}
try:
    graphs = json.loads(Path('P:/FoA/Saved/StoryShots/graph_names.json').read_text())[P]
    for g in graphs:
        ns, es = inspect(P, g)
        b = Batch(P, g)
        for s in [n for n in ns if n['title'] == 'SetScalarParameterValue' and pin(n, 'ParameterName') == 'BedSettleStart']:
            src = next((e['from_node'] for e in es if e['to_node'] == s['node_id'] and e['to_pin'] == 'ParameterValue'), None)
            add = next((n for n in ns if n['node_id'] == src and n['title'] in ('float + float', 'double + double')), None)
            if not add:
                continue  # the skip path writes Now directly
            lit = next((n for e in es if e['to_node'] == add['node_id'] and e['to_pin'] == 'B'
                        for n in ns if n['node_id'] == e['from_node']), None)  # B may come from a Make Literal Float
            target, name = (lit, 'Value') if lit else (add, 'B')
            if abs(float(pin(target, name)) - SETTLE) > 1e-3:
                report.setdefault(g, []).append(('BedSettle', pin(target, name), SETTLE))
                b.pin(target['node_id'], name, SETTLE)
        for cr in [n for n in ns if n['title'] == 'SetControlRotation']:
            src = next((e['from_node'] for e in es if e['to_node'] == cr['node_id'] and e['to_pin'] == 'NewRotation'), None)
            rot = next((n for n in ns if n['node_id'] == src and n['title'] == 'MakeRotator'), None)
            if rot and abs(float(pin(rot, 'Yaw')) - 55.0) < 1e-3 and abs(float(pin(rot, 'Pitch')) + 10.0) < 1e-3:
                report.setdefault(g, []).append(('ControlRotation yaw', pin(rot, 'Yaw'), YAW))
                b.pin(rot['node_id'], 'Yaw', YAW)
        if b.ops:
            b.run()
    Path('P:/FoA/Saved/StoryShots/wake_handoff_patch.json').write_text(json.dumps(report, indent=1))
    print('wake hand-off patched', report)
finally:
    h.release('story', token)
