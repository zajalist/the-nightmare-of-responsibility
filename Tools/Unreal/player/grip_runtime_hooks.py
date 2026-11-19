"""BP_FoAPlayer, part 2 of the grip runtime (grip_runtime_graphs.py builds Begin/End/UpdateGrip). Hayba graph batches.
- EventGraph: UpdateGrip(Delta Seconds) after UpdatePhoneHold at the end of the Event Tick chain.
- SetToolHandTarget / SetToolHandRotation (the door tool's old hand placement): a Branch at the entry returns while a
  grip is held (GripTarget > 0.5), so the door tool and the grip never both write the Teen IK.
- --manny-off: the Manny finger layers (ABP_FoAPlayer GripWeight, KeyGrip) are cut off at their only writers
  (SetToolHandTarget, SetToolHandRotation, SetHeldTool): the setters stay, their value links are removed, so they write
  0 / false. Run it once the screwdriver's Teen pose lands; until then a held grip already skips those writers and the
  Teen layer (after the retarget) overrides the fingers.
Idempotent: each step checks for its own work first. Compile 0/0 and save per batch.
  $env:HAYBA_AGENT_ID='anim'; python Tools/Unreal/player/grip_runtime_hooks.py"""
import sys

sys.path[:0] = ['P:/FoA/Tools/Unreal', 'P:/FoA/Tools/Unreal/player']
import hayba_call as h  # noqa: E402
from held_tool_graphs import Batch, inspect, find  # noqa: E402

P = '/Game/FoA/Characters/Player/BP_FoAPlayer'
PC = P + '.BP_FoAPlayer_C'
K = '/Script/Engine.KismetMathLibrary:'
assert not h.call('editor_get_state')['data']['pie_running'], 'PIE running'


def tick_hook():
    nodes, edges = inspect(P, 'EventGraph')
    if any(n['title'] == 'UpdateGrip' for n in nodes):
        return print('tick hook: already there')
    tick, phone = find(nodes, 'Event Tick'), find(nodes, 'UpdatePhoneHold')
    assert not any(e['from_node'] == phone and e.get('from_pin') == 'then' for e in edges), 'UpdatePhoneHold is not the end of the tick chain'
    b = Batch(P, 'EventGraph')
    b.fn('grip', PC + ':UpdateGrip', 0, 0)
    b.link(phone, 'then', 'grip', 'execute'); b.link(tick, 'DeltaSeconds', 'grip', 'Dt')
    b.run()


def early_out(fn):
    nodes, edges = inspect(P, fn)
    e = find(nodes, fn)
    if any(n['title'] == 'Get GripTarget' for n in nodes):  # (SetToolHandRotation already opens with its own Branch)
        return print(fn, 'early-out: already there')
    first = next(x for x in edges if x['from_node'] == e and x.get('from_pin') == 'then')
    b = Batch(P, fn)
    b.cut(e, 'then', first['to_node'], first['to_pin'])
    b.get('gt', 'GripTarget', 0, -300)
    b.fn('held', K + 'Greater_DoubleDouble', 200, -300, B=0.5); b.link('gt', 'GripTarget', 'held', 'A')
    b.node('br', 'branch', 400, -200); b.link('held', 'ReturnValue', 'br', 'Condition')
    b.link(e, 'then', 'br', 'execute'); b.link('br', 'else', first['to_node'], first['to_pin'])
    b.comment('A twin-solved grip is held (BeginGrip): UpdateGrip places the hand, not this', ['gt', 'held', 'br'])
    b.run()


def manny_off(fn):
    nodes, edges = inspect(P, fn)
    setters = {n['node_id']: n['title'] for n in nodes if n['title'] in ('Set GripWeight', 'Set KeyGrip')}
    b = Batch(P, fn)
    for x in edges:
        if x['to_node'] in setters and x.get('to_pin') in ('GripWeight', 'KeyGrip'):
            b.cut(x['from_node'], x['from_pin'], x['to_node'], x['to_pin'])
    if not b.ops:
        return print(fn, 'Manny finger layer: already off')
    b.run()


lease = h.lease_acquire('anim', ['asset:/Game/FoA/Characters/Player'], ttl_s=120)
try:
    tick_hook()
    for fn in ('SetToolHandTarget', 'SetToolHandRotation'):
        early_out(fn)
    if '--manny-off' in sys.argv:  # once the screwdriver's Teen pose lands: until then its hold still uses the Manny layer
        for fn in ('SetToolHandTarget', 'SetToolHandRotation', 'SetHeldTool'):
            manny_off(fn)
finally:
    h.release('anim', lease)
print('GRIP_HOOKS done')
