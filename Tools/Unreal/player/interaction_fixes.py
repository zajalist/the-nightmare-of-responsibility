"""Interaction fixes from the walk-up PIE proof (approach/20261109_151108) and QA's log scan. Hayba batches, BP_FoAPlayer.
1. LockForInteraction's MoveComponentTo ran its look-at with a None Target ("Accessed None", QA): the branch now also
   needs IsValid(Target).
2. During a locked interaction the capsule ignores the target actor when moving (IgnoreActorWhenMoving), so a door that
   rattles or swings into him can't depenetrate him upwards (he floated 80 cm at the locked door); SetInteractionLocked
   (false) clears it (ClearMoveIgnoreActors).
3. Look at what you touch looks at the measured contact point (EnvironmentContactAim: the knob, the handle) when a
   contact is live, and at the actor's bounds otherwise (during the walk-up).
4. The walk-up stands 20 cm (was 14) clear of the contact point.
  $env:HAYBA_AGENT_ID='anim'; python Tools/Unreal/player/interaction_fixes.py"""
import sys

sys.path[:0] = ['P:/FoA/Tools/Unreal', 'P:/FoA/Tools/Unreal/player']
import hayba_call as h  # noqa: E402
from held_tool_graphs import Batch, inspect, find  # noqa: E402

P = '/Game/FoA/Characters/Player/BP_FoAPlayer'
K = '/Script/Engine.KismetMathLibrary:'
SYS = '/Script/Engine.KismetSystemLibrary:'
CAP = '/Script/Engine.PrimitiveComponent:'
assert not h.call('editor_get_state')['data']['pie_running'], 'PIE running'

# 1 + 2: LockForInteraction (EventGraph)
nodes, edges = inspect(P, 'EventGraph')
byid = {n['node_id']: n for n in nodes}
if not any(n['title'] == 'Ignore Actor when Moving' or n['title'].replace(' ', '') == 'IgnoreActorWhenMoving' for n in nodes):
    ev = find(nodes, 'Event LockForInteraction')
    mv = find(nodes, 'MoveComponentTo')
    br = next(e['from_node'] for e in edges if e['to_node'] == mv and e['to_pin'] == 'Move')
    cond = next(e for e in edges if e['to_node'] == br and e['to_pin'] == 'Condition')
    remember = find(nodes, 'Set InteractLook')
    after = next(e for e in edges if e['from_node'] == remember and e['from_pin'] == 'then')
    b = Batch(P, 'EventGraph')
    b.fn('tvalid', SYS + 'IsValid', 3000, 3200); b.link(ev, 'Target', 'tvalid', 'Object')
    b.fn('both', K + 'BooleanAND', 3200, 3100)
    b.cut(cond['from_node'], cond['from_pin'], br, 'Condition')
    b.link(cond['from_node'], cond['from_pin'], 'both', 'A'); b.link('tvalid', 'ReturnValue', 'both', 'B'); b.link('both', 'ReturnValue', br, 'Condition')
    b.get('capsule', 'CapsuleComponent', 600, -350)
    b.fn('ignore', CAP + 'IgnoreActorWhenMoving', 600, -200, bShouldIgnore='true')
    b.link('capsule', 'CapsuleComponent', 'ignore', 'self'); b.link(ev, 'Target', 'ignore', 'Actor')
    b.cut(remember, 'then', after['to_node'], after['to_pin'])
    b.link(remember, 'then', 'ignore', 'execute'); b.link('ignore', 'then', after['to_node'], after['to_pin'])
    b.comment('Never pushed by what you touch', ['capsule', 'ignore'])
    b.comment('Only with a real target', ['tvalid', 'both'])
    b.run()

nodes, edges = inspect(P, 'SetInteractionLocked')
if not any(n['title'].replace(' ', '') == 'ClearMoveIgnoreActors' for n in nodes):
    e = find(nodes, 'SetInteractionLocked')
    tail = next(n['node_id'] for n in nodes if n['title'].replace(' ', '') == 'UpdateFirstPersonVisibility')
    assert not any(x['from_node'] == tail and x['from_pin'] == 'then' for x in edges), 'SetInteractionLocked tail moved'
    b = Batch(P, 'SetInteractionLocked')
    b.node('unlocking', 'branch', 1800, 0); b.link(tail, 'then', 'unlocking', 'execute')
    b.fn('locked', K + 'Not_PreBool', 1800, 250); b.link(e, 'bEnable', 'locked', 'A'); b.link('locked', 'ReturnValue', 'unlocking', 'Condition')
    b.get('capsule', 'CapsuleComponent', 2100, 250)
    b.fn('clear', CAP + 'ClearMoveIgnoreActors', 2100, 0); b.link('capsule', 'CapsuleComponent', 'clear', 'self')
    b.link('unlocking', 'then', 'clear', 'execute')
    b.comment('Collide normally again', ['unlocking', 'locked', 'capsule', 'clear'])
    b.run()

# 3: look at the live contact point
nodes, edges = inspect(P, 'UpdateFirstPersonVisibility')
byid = {n['node_id']: n for n in nodes}
if not any(n['title'] == 'Get EnvironmentContactAim' for n in nodes):
    aim = next(e['to_node'] for e in edges if byid[e['from_node']]['title'] == 'Get Actor Bounds' and e['from_pin'] == 'Origin'
               and byid[e['to_node']]['title'] == 'FindLookAtRotation')
    org = next(e for e in edges if e['to_node'] == aim and e['to_pin'] == 'Target')
    b = Batch(P, 'UpdateFirstPersonVisibility')
    b.get('cmesh', 'EnvironmentContactMesh', 2200, -100); b.fn('live', SYS + 'IsValid', 2450, -100); b.link('cmesh', 'EnvironmentContactMesh', 'live', 'Object')
    b.get('caim', 'EnvironmentContactAim', 2450, 50)
    b.fn('pick', K + 'SelectVector', 2700, -100); b.link('caim', 'EnvironmentContactAim', 'pick', 'A'); b.link(org['from_node'], org['from_pin'], 'pick', 'B')
    b.link('live', 'ReturnValue', 'pick', 'bPickA')
    b.cut(org['from_node'], org['from_pin'], aim, 'Target'); b.link('pick', 'ReturnValue', aim, 'Target')
    b.comment('Look at the handle itself', ['cmesh', 'live', 'caim', 'pick'])
    b.run()

# 4: a little more room to stand in
nodes, edges = inspect(P, 'ApproachAndInteract')
adds = [n for n in nodes if any(p['name'] == 'B' and p.get('default_value') in ('14.0', '14', '14.000000') for p in n.get('pins', []))]
if adds:
    b = Batch(P, 'ApproachAndInteract')
    b.pin(adds[0]['node_id'], 'B', 20.0)
    b.run()
print('INTERACTION_FIXES_DONE')
