"""T0, paced (QA and main 2026-11-09): after the wake-up the player gets the room first, then the phone.
  StartMorningBeats -> 2.7 s (the hand-off fade-up ends ~0.65 s after SetCinematic(false), then ~2 s on the room with
  free look) -> OpenMorningPhone: S_Phone_NightstandBuzz at the phone on the nightstand -> 0.5 s -> RaiseMorningPhone:
  EnterBeat(0) ("Wake up.", ShowPhone, so the UI raises the phone on the list) and BP_FoAFrontEnd.OpenPhone as a backup.
  T0 completes on the phone's Wake up (PhoneWakeUp). No front end: T0 enters and completes by itself.
T0 is entered late on purpose: entering it broadcasts ShowPhone, which opens the phone at once. Both timed functions
only act while no beat has started yet (BeatIndex < 0). Idempotent; build_director.py matches.
  python Tools/Unreal/flow/patch_t0_phone.py"""
import json
import os
import sys
from pathlib import Path

sys.path[:0] = ['P:/FoA/Tools/Unreal', 'P:/FoA/Tools/Unreal/player']
import hayba_call as h  # noqa: E402
from held_tool_graphs import Batch, inspect, find  # noqa: E402

P = '/Game/FoA/Gameplay/BP_BeatDirector'
C = P + '.BP_BeatDirector_C'
FE = '/Game/FoA/UI/Framework/BP_FoAFrontEnd.BP_FoAFrontEnd_C'
PHONE = '/Game/FoA/UI/Game/BP_Phone.BP_Phone_C'
BUZZ = '/Game/FoA/Audio/MetaSounds/Phone/S_Phone_NightstandBuzz.S_Phone_NightstandBuzz'
GS, KS, K = '/Script/Engine.GameplayStatics:', '/Script/Engine.KismetSystemLibrary:', '/Script/Engine.KismetMathLibrary:'
ROOM_HOLD, BUZZ_LEAD = 2.7, 0.5


def pin(n, name):
    return next((p.get('default_value') or p.get('default_object') for p in n['pins'] if p['name'] == name), None)


def fresh(name):
    ns, _ = inspect(P, name)
    entry = find(ns, name)
    b = Batch(P, name)
    old = [n['node_id'] for n in ns if n['node_id'] != entry]
    if old:
        b.ops.append(dict(op='remove', node_ids=old))
    return b, entry


def not_started(b, entry, x=0):
    b.get('beat', 'BeatIndex', x, 250)
    b.fn('early', K + 'Less_IntInt', x + 250, 250, B=0)
    b.link('beat', 'BeatIndex', 'early', 'A')
    b.node('gate', 'branch', x + 500, 0)
    b.link('early', 'ReturnValue', 'gate', 'Condition')
    b.link(entry, 'then', 'gate', 'execute')
    return 'gate'


os.environ['HAYBA_AGENT_ID'] = 'story'
assert not h.call('editor_get_state', {})['data']['pie_running'], 'PIE running'
token = h.lease_acquire('story', ['asset:' + P], ttl_s=180, wait_s=180)
report = {}
try:
    for fn in ('OpenMorningPhone', 'RaiseMorningPhone'):
        if not h.call('blueprint_inspect_graph', {'path': P, 'graph_name': fn}).get('ok'):
            r = h.call('blueprint_add_function', {'path': P, 'function_name': fn})
            assert r.get('ok'), r
    ns, _ = inspect(P, 'OpenMorningPhone')
    if not any(BUZZ.split('.')[0] in str(pin(n, 'Sound')) for n in ns):
        b, entry = fresh('OpenMorningPhone')
        gate = not_started(b, entry)
        b.fn('phone', GS + 'GetActorOfClass', 750, 0, ActorClass=PHONE)
        b.link(gate, 'then', 'phone', 'execute')
        b.fn('valid', KS + 'IsValid', 1000, 250)
        b.link('phone', 'ReturnValue', 'valid', 'Object')
        b.node('there', 'branch', 1250, 0)
        b.link('valid', 'ReturnValue', 'there', 'Condition')
        b.link('phone', 'then', 'there', 'execute')
        b.fn('where', '/Script/Engine.Actor:K2_GetActorLocation', 1250, 300)
        b.link('phone', 'ReturnValue', 'where', 'self')
        b.fn('buzz', GS + 'PlaySoundAtLocation', 1550, -100, Sound=BUZZ)
        b.link('where', 'ReturnValue', 'buzz', 'Location')
        b.link('there', 'then', 'buzz', 'execute')
        b.fn('rise', KS + 'K2_SetTimer', 1900, 0, FunctionName='RaiseMorningPhone', Time=BUZZ_LEAD, bLooping='false')
        b.link('buzz', 'then', 'rise', 'execute')
        b.link('there', 'else', 'rise', 'execute')
        b.comment('The phone buzzes on the nightstand', [o['ref'] for o in b.ops if o.get('op') == 'add_node'])
        b.run()
        report['OpenMorningPhone'] = 'buzz, then RaiseMorningPhone in %.1f s' % BUZZ_LEAD
    ns, _ = inspect(P, 'RaiseMorningPhone')
    if not any(n['title'] == 'OpenPhone' for n in ns):
        b, entry = fresh('RaiseMorningPhone')
        gate = not_started(b, entry)
        b.fn('enter', C + ':EnterBeat', 750, 0, Index=0)
        b.link(gate, 'then', 'enter', 'execute')
        b.fn('fe', GS + 'GetActorOfClass', 1050, 0, ActorClass=FE)
        b.link('enter', 'then', 'fe', 'execute')
        b.fn('ok', KS + 'IsValid', 1300, 250)
        b.link('fe', 'ReturnValue', 'ok', 'Object')
        b.node('has', 'branch', 1550, 0)
        b.link('ok', 'ReturnValue', 'has', 'Condition')
        b.link('fe', 'then', 'has', 'execute')
        b.fn('open', FE + ':OpenPhone', 1850, -120)
        b.link('fe', 'ReturnValue', 'open', 'self')
        b.link('has', 'then', 'open', 'execute')
        b.fn('skip', C + ':CompleteBeat', 1850, 160, Index=0)
        b.link('has', 'else', 'skip', 'execute')
        b.comment('T0: the phone rises on the list', [o['ref'] for o in b.ops if o.get('op') == 'add_node'])
        b.run()
        report['RaiseMorningPhone'] = 'EnterBeat(0), OpenPhone; no front end: CompleteBeat(0)'
    ns, es = inspect(P, 'StartMorningBeats')
    by = {n['node_id']: n for n in ns}
    tm = next(n for n in ns if pin(n, 'FunctionName') == 'OpenMorningPhone')
    enters = [n['node_id'] for n in ns if n['title'] == 'EnterBeat']
    b = Batch(P, 'StartMorningBeats')
    for en in enters:                                         # the earlier version entered T0 here: the phone rose at once
        for e in es:
            if e['to_node'] == en and e['to_pin'] == 'execute':
                b.link(e['from_node'], e['from_pin'], tm['node_id'], 'execute')
        b.ops.append(dict(op='remove', node_ids=[en]))
    if abs(float(pin(tm, 'Time') or 0) - ROOM_HOLD) > 1e-3:
        b.pin(tm['node_id'], 'Time', ROOM_HOLD)
    if b.ops:
        b.run()
        report['StartMorningBeats'] = 'timer OpenMorningPhone %.1f s, no EnterBeat' % ROOM_HOLD
    ns, _ = inspect(P, 'StartMorningBeats')
    assert not any(n['title'] in ('EnterBeat', 'CompleteBeat') for n in ns)
    assert any(pin(n, 'FunctionName') == 'OpenMorningPhone' and abs(float(pin(n, 'Time')) - ROOM_HOLD) < 1e-3 for n in ns)
    Path('P:/FoA/Saved/StoryShots/t0_phone_patch.json').write_text(json.dumps(report, indent=1))
    print('T0 paced', report)
finally:
    h.release('story', token)
