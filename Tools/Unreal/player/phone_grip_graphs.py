"""BP_FoAPlayer: drive the left-hand phone grip (phone_grip_layer.py) from the phone hold. Hayba graph batches.
- PhoneTap(): PhoneTapTarget = 1 (replaces the old montage-section jump; the grip is a layered pose now).
- UpdatePhoneHold, after the left-hand IK writes: PhoneTapAlpha runs to the target in 0.07 s and back in 0.14 s (the
  target drops to 0 once pressed), then ABP_FoAPlayer_MH.PhoneGripWeight = the raise ease and PhoneGripTime =
  PhoneTapAlpha / 30 (frame 1 of AS_FoA_Grip_Phone_L is the pressed thumb).
  $env:HAYBA_AGENT_ID='anim'; python Tools/Unreal/player/phone_grip_graphs.py"""
import sys

sys.path[:0] = ['P:/FoA/Tools/Unreal', 'P:/FoA/Tools/Unreal/player']
import hayba_call as h  # noqa: E402
from held_tool_graphs import Batch, inspect, find  # noqa: E402

P = '/Game/FoA/Characters/Player/BP_FoAPlayer'
MC = '/Game/FoA/Characters/Player/ABP_FoAPlayer_MH.ABP_FoAPlayer_MH_C'
K = '/Script/Engine.KismetMathLibrary:'

assert not h.call('editor_get_state')['data']['pie_running'], 'PIE running'
lease = h.lease_acquire('anim', ['asset:/Game/FoA/Characters/Player'], ttl_s=60)
try:
    for v in ('PhoneTapAlpha', 'PhoneTapTarget'):
        r = h.call('blueprint_add_variable', dict(path=P, variable_name=v, variable_type='float', default_value='0',
                                                  instance_editable=False, update_existing=True, category='Phone'))
        assert r.get('ok'), r
    nodes, _ = inspect(P, 'PhoneTap')
    if not any(n['title'] == 'Set PhoneTapTarget' for n in nodes):
        e = find(nodes, 'PhoneTap')
        b = Batch(P, 'PhoneTap')
        old = [n['node_id'] for n in nodes if n['node_id'] != e and n['title'] != 'Comment']
        if old:
            b.ops.append(dict(op='remove', node_ids=old))
        b.set('press', 'PhoneTapTarget', 300, 0); b.pin('press', 'PhoneTapTarget', 1.0); b.chain(e, 'press')
        b.run()
    nodes, edges = inspect(P, 'UpdatePhoneHold')
    if not any(n['title'] == 'Set PhoneTapAlpha' for n in nodes):
        last = find(nodes, 'Set EnvironmentForearmRotation')
        mh, mh_pin = next((x['from_node'], x['from_pin']) for x in edges if x['to_node'] == last and x['to_pin'] == 'self')
        ease = next(x['from_node'] for x in edges if x['to_pin'] == 'EnvironmentHandWeight'
                    and any(n['node_id'] == x['to_node'] and n['title'] == 'Set EnvironmentHandWeight' for n in nodes))
        b = Batch(P, 'UpdatePhoneHold')
        b.get('a0', 'PhoneTapAlpha', 6000, 300); b.get('t0', 'PhoneTapTarget', 6000, 450)
        b.fn('dt', '/Script/Engine.GameplayStatics:GetWorldDeltaSeconds', 6000, 600)
        b.fn('pressing', K + 'Greater_DoubleDouble', 6250, 500, B=0.5); b.link('t0', 'PhoneTapTarget', 'pressing', 'A')
        b.fn('speed', K + 'SelectFloat', 6500, 500, A=1.0 / 0.07, B=1.0 / 0.14); b.link('pressing', 'ReturnValue', 'speed', 'bPickA')
        b.fn('step', K + 'FInterpTo_Constant', 6750, 350)
        b.link('a0', 'PhoneTapAlpha', 'step', 'Current'); b.link('t0', 'PhoneTapTarget', 'step', 'Target')
        b.link('dt', 'ReturnValue', 'step', 'DeltaTime'); b.link('speed', 'ReturnValue', 'step', 'InterpSpeed')
        b.set('a', 'PhoneTapAlpha', 7000, -100); b.link('step', 'ReturnValue', 'a', 'PhoneTapAlpha')
        b.fn('full', K + 'GreaterEqual_DoubleDouble', 7250, 300, B=0.99); b.link('a', 'Output_Get', 'full', 'A')
        b.node('br', 'branch', 7300, -100); b.link('full', 'ReturnValue', 'br', 'Condition')
        b.set('lift', 'PhoneTapTarget', 7550, -250); b.pin('lift', 'PhoneTapTarget', 0.0)
        b.set('gw', 'PhoneGripWeight', 7850, -100, MC); b.link(mh, mh_pin, 'gw', 'self'); b.link(ease, 'ReturnValue', 'gw', 'PhoneGripWeight')
        b.fn('frame', K + 'Divide_DoubleDouble', 7850, 300, B=30.0); b.link('a', 'Output_Get', 'frame', 'A')
        b.set('gt', 'PhoneGripTime', 8150, -100, MC); b.link(mh, mh_pin, 'gt', 'self'); b.link('frame', 'ReturnValue', 'gt', 'PhoneGripTime')
        b.link(last, 'then', 'a', 'execute'); b.chain('a', 'br'); b.link('br', 'then', 'lift', 'execute')
        b.link('lift', 'then', 'gw', 'execute'); b.link('br', 'else', 'gw', 'execute'); b.chain('gw', 'gt')
        b.comment('Fingers hold the phone; the thumb taps', ['a0', 't0', 'dt', 'pressing', 'speed', 'step', 'a', 'full', 'br', 'lift',
                                                           'gw', 'frame', 'gt'])
        b.run()
finally:
    h.release('anim', lease)
print('PHONE_GRIP_GRAPHS done')
