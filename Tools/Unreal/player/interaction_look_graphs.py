"""First person: look at what you touch (anim lane, Hayba graph batches on BP_FoAPlayer).
In first person the camera sits in his eyes at the player's pitch, so a drawer, a door handle or the boot is 50-65 deg
below the view and the hands that work it are never on screen. The animation direction says "look first, reach
second": LockForInteraction(Seconds, Target) now remembers Target, and while the interaction lock holds,
UpdateFirstPersonVisibility eases the view (RInterpTo 4.5, pitch kept within the existing -65..65 clamp) onto the
target's bounds centre. The control rotation follows the same eased view, so nothing snaps back when the lock ends.
  $env:HAYBA_AGENT_ID='anim'; python Tools/Unreal/player/interaction_look_graphs.py"""
import sys

sys.path[:0] = ['P:/FoA/Tools/Unreal', 'P:/FoA/Tools/Unreal/player']
import hayba_call as h  # noqa: E402
from held_tool_graphs import Batch, inspect, find  # noqa: E402

P = '/Game/FoA/Characters/Player/BP_FoAPlayer'
K = '/Script/Engine.KismetMathLibrary:'
SPEED = 4.5

assert not h.call('editor_get_state')['data']['pie_running'], 'PIE running'
r = h.call('blueprint_add_variable', dict(path=P, variable_name='InteractLook', variable_type='object:/Script/Engine.Actor',
                                          instance_editable=False, update_existing=True, category='Camera'))
assert r.get('ok'), r

# 1. remember the target
nodes, edges = inspect(P, 'EventGraph')
if not any(n['title'] == 'Set InteractLook' for n in nodes):
    ev = find(nodes, 'Event LockForInteraction')
    first = next(e for e in edges if e['from_node'] == ev and e['from_pin'] == 'then')
    b = Batch(P, 'EventGraph')
    b.cut(ev, 'then', first['to_node'], first['to_pin'])
    b.set('remember', 'InteractLook', 300, -200)
    b.link(ev, 'Target', 'remember', 'InteractLook')
    b.link(ev, 'then', 'remember', 'execute'); b.link('remember', 'then', first['to_node'], first['to_pin'])
    b.comment('Look at it first', ['remember'])
    b.run()

# 2. ease the view onto it while the interaction lock holds
F = 'UpdateFirstPersonVisibility'
nodes, edges = inspect(P, F)
if any(n['title'] == 'Get InteractLook' for n in nodes):
    sys.exit('interaction look already built')
setview = find(nodes, 'Set FPViewRotation')
after = next(e for e in edges if e['from_node'] == setview and e['from_pin'] == 'then')
b = Batch(P, F)
b.cut(setview, 'then', after['to_node'], after['to_pin'])
b.get('locked', 'bInteractionLocked', 1700, -700)
b.get('target', 'InteractLook', 1700, -550)
b.fn('valid', '/Script/Engine.KismetSystemLibrary:IsValid', 1950, -550); b.link('target', 'InteractLook', 'valid', 'Object')
b.fn('both', K + 'BooleanAND', 2200, -700); b.link('locked', 'bInteractionLocked', 'both', 'A'); b.link('valid', 'ReturnValue', 'both', 'B')
b.node('ifat', 'branch', 2450, -900); b.link('both', 'ReturnValue', 'ifat', 'Condition')
b.fn('bounds', '/Script/Engine.Actor:GetActorBounds', 2200, -400, bOnlyCollidingComponents='true')
b.link('target', 'InteractLook', 'bounds', 'self')
b.get('cam', 'FollowCamera', 2200, -250)
b.fn('eye', '/Script/Engine.SceneComponent:K2_GetComponentLocation', 2450, -250); b.link('cam', 'FollowCamera', 'eye', 'self')
b.fn('aim', K + 'FindLookAtRotation', 2700, -400); b.link('eye', 'ReturnValue', 'aim', 'Start'); b.link('bounds', 'Origin', 'aim', 'Target')
b.fn('dt', '/Script/Engine.GameplayStatics:GetWorldDeltaSeconds', 2700, -250)
b.fn('ease', K + 'RInterpTo', 2950, -400, InterpSpeed=SPEED)
b.link(setview, 'Output_Get', 'ease', 'Current'); b.link('aim', 'ReturnValue', 'ease', 'Target'); b.link('dt', 'ReturnValue', 'ease', 'DeltaTime')
b.fn('parts', K + 'BreakRotator', 3200, -400); b.link('ease', 'ReturnValue', 'parts', 'InRot')
b.fn('pitch', K + 'FClamp', 3450, -400, Min=-65, Max=65); b.link('parts', 'Pitch', 'pitch', 'Value')
b.fn('flat', K + 'MakeRotator', 3700, -400, Roll=0); b.link('pitch', 'ReturnValue', 'flat', 'Pitch'); b.link('parts', 'Yaw', 'flat', 'Yaw')
b.set('look', 'FPViewRotation', 3950, -900); b.link('flat', 'ReturnValue', 'look', 'FPViewRotation')
b.link(setview, 'then', 'ifat', 'execute'); b.link('ifat', 'then', 'look', 'execute')
b.link('look', 'then', after['to_node'], after['to_pin']); b.link('ifat', 'else', after['to_node'], after['to_pin'])
# everything downstream reads the variable, not the first setter's output pin, so it sees the eased view
b.get('viewnow', 'FPViewRotation', 4200, -250)
for e in edges:
    if e['from_node'] == setview and e['from_pin'] == 'Output_Get':
        b.cut(setview, 'Output_Get', e['to_node'], e['to_pin']); b.link('viewnow', 'FPViewRotation', e['to_node'], e['to_pin'])
b.comment('Look at what you touch', ['locked', 'target', 'valid', 'both', 'ifat', 'bounds', 'cam', 'eye', 'aim', 'dt', 'ease',
                                      'parts', 'pitch', 'flat', 'look', 'viewnow'])
b.run()
