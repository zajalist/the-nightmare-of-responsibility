"""BP_FoAPlayer: the twin-solved hand grips at runtime (anim lane, 2026-11-10). Hayba graph batches.
- BeginGrip(Anchor, Pose, HandInAnchor): the right hand goes to Anchor's world transform composed with HandInAnchor (the
  hand in the anchor's frame, solved at mesh level in the Blender twin: bake_grips.py), and the Teen finger pose
  AS_FoA_TeenGrip_<Pose>_R comes in (ABP_FoAPlayer_MH RightGrip_<Pose>, right_grip_layer.py). EndGrip() lets go.
- UpdateGrip(Dt), on Tick after UpdatePhoneHold: GripAlpha eases to GripTarget (6/s); while it is above zero and the
  anchor is valid it drives the Teen ABP's right two-bone IK (ToolHandTarget, ToolHandWeight, ToolElbowTarget: out to
  the right and down) and the world-space hand rotation (HeldToolRotation / HeldToolWeight), so the hand follows a
  turning key or an opening drawer frame by frame.
- SetToolHandTarget and SetToolHandRotation (the door tool's old hand placement) return at once while a grip is
  held, and the Manny finger layers (ABP_FoAPlayer GripWeight / KeyGrip) are left at zero: the Teen-native poses replace them.
Idempotent: functions already built are rebuilt from their entry (fresh). Compile 0/0 and save after each batch.
  $env:HAYBA_AGENT_ID='anim'; python Tools/Unreal/player/grip_runtime_graphs.py"""
import json
import sys

sys.path[:0] = ['P:/FoA/Tools/Unreal', 'P:/FoA/Tools/Unreal/player']
import hayba_call as h  # noqa: E402
from held_tool_graphs import Batch, inspect, find  # noqa: E402

P = '/Game/FoA/Characters/Player/BP_FoAPlayer'
MC = '/Game/FoA/Characters/Player/ABP_FoAPlayer_MH.ABP_FoAPlayer_MH_C'
K = '/Script/Engine.KismetMathLibrary:'
SYS = '/Script/Engine.KismetSystemLibrary:'
ACT = '/Script/Engine.Actor:'
NAMES = list(json.load(open('P:/FoA/Saved/AnimShots/grip_bake.json')))
MH_SET = 'AsABP Fo APlayer MH'

assert not h.call('editor_get_state')['data']['pie_running'], 'PIE running'


def ensure_function(name, inputs):
    have = [str(g) for g in (h.call('blueprint_get_info', dict(path=P))['data'].get('functions') or [])]
    if name not in have:
        r = h.call('blueprint_add_function', dict(path=P, function_name=name, inputs=inputs), owner='anim')
        assert r.get('ok'), r


def fresh(name):
    nodes, _ = inspect(P, name)
    e = find(nodes, name)
    b = Batch(P, name)
    old = [n['node_id'] for n in nodes if n['node_id'] != e and n['title'] != 'Return Node']
    if old:
        b.ops.append(dict(op='remove', node_ids=old))
    return b, e


lease = h.lease_acquire('anim', ['asset:/Game/FoA/Characters/Player'], ttl_s=120)
try:
    for name, kind in (('GripAnchor', 'object:/Script/Engine.SceneComponent'), ('GripPose', 'name'), ('GripHand', 'transform'),
                       ('GripTarget', 'float'), ('GripAlpha', 'float')):
        r = h.call('blueprint_add_variable', dict(path=P, variable_name=name, variable_type=kind, instance_editable=False,
                                                  update_existing=True, category='Grip'), owner='anim')
        assert r.get('ok'), r
    ensure_function('BeginGrip', [dict(name='Anchor', type='object:/Script/Engine.SceneComponent'), dict(name='Pose', type='name'),
                                  dict(name='HandInAnchor', type='transform')])
    ensure_function('EndGrip', [])
    ensure_function('UpdateGrip', [dict(name='Dt', type='float')])

    b, e = fresh('BeginGrip')
    b.set('a', 'GripAnchor', 300, 0); b.link(e, 'Anchor', 'a', 'GripAnchor')
    b.set('p', 'GripPose', 600, 0); b.link(e, 'Pose', 'p', 'GripPose')
    b.set('hd', 'GripHand', 900, 0); b.link(e, 'HandInAnchor', 'hd', 'GripHand')
    b.set('t', 'GripTarget', 1200, 0); b.pin('t', 'GripTarget', 1.0)
    b.link(e, 'then', 'a', 'execute'); b.chain('a', 'p', 'hd', 't')
    b.comment('Take hold: the hand goes to the anchor composed with the twin-solved hand-in-anchor', ['a', 'p', 'hd', 't'])
    b.run()

    b, e = fresh('EndGrip')
    b.set('t', 'GripTarget', 300, 0); b.pin('t', 'GripTarget', 0.0)
    b.link(e, 'then', 't', 'execute')
    b.run()

    b, e = fresh('UpdateGrip')
    b.get('ga', 'GripAlpha', 200, 300); b.get('gt', 'GripTarget', 200, 400)
    b.fn('ease', K + 'FInterpTo', 450, 300, InterpSpeed=6.0)
    b.link('ga', 'GripAlpha', 'ease', 'Current'); b.link('gt', 'GripTarget', 'ease', 'Target'); b.link(e, 'Dt', 'ease', 'DeltaTime')
    b.set('sa', 'GripAlpha', 700, 0); b.link('ease', 'ReturnValue', 'sa', 'GripAlpha'); b.link(e, 'then', 'sa', 'execute')
    b.get('anc', 'GripAnchor', 700, 500)
    b.fn('valid', SYS + 'IsValid', 950, 500); b.link('anc', 'GripAnchor', 'valid', 'Object')
    b.fn('on', K + 'Greater_DoubleDouble', 950, 350, B=0.001); b.link('ease', 'ReturnValue', 'on', 'A')
    b.fn('both', K + 'BooleanAND', 1200, 400); b.link('valid', 'ReturnValue', 'both', 'A'); b.link('on', 'ReturnValue', 'both', 'B')
    b.node('br', 'branch', 1000, 0); b.link('both', 'ReturnValue', 'br', 'Condition'); b.link('sa', 'then', 'br', 'execute')
    b.fn('aw', '/Script/Engine.SceneComponent:K2_GetComponentToWorld', 1200, 650); b.link('anc', 'GripAnchor', 'aw', 'self')
    b.get('gh', 'GripHand', 1200, 800)
    b.fn('hw', K + 'ComposeTransforms', 1450, 700); b.link('gh', 'GripHand', 'hw', 'A'); b.link('aw', 'ReturnValue', 'hw', 'B')
    b.fn('hb', K + 'BreakTransform', 1700, 700); b.link('hw', 'ReturnValue', 'hb', 'InTransform')
    b.fn('right', ACT + 'GetActorRightVector', 1700, 950)
    b.fn('out', K + 'Multiply_VectorFloat', 1950, 950, B=25.0); b.link('right', 'ReturnValue', 'out', 'A')
    b.fn('down', K + 'MakeVector', 1950, 1100, X=0.0, Y=0.0, Z=-35.0)
    b.fn('pole', K + 'Add_VectorVector', 2200, 1000); b.link('out', 'ReturnValue', 'pole', 'A'); b.link('down', 'ReturnValue', 'pole', 'B')
    b.get('body', 'Body', 1300, 200)
    b.fn('shoulder', '/Script/Engine.SceneComponent:GetSocketLocation', 2200, 1150, InSocketName='upperarm_r')
    b.link('body', 'Body', 'shoulder', 'self')
    b.fn('elbow', K + 'Add_VectorVector', 2450, 900); b.link('shoulder', 'ReturnValue', 'elbow', 'A'); b.link('pole', 'ReturnValue', 'elbow', 'B')
    b.fn('anim', '/Script/Engine.SkeletalMeshComponent:GetAnimInstance', 1500, 200); b.link('body', 'Body', 'anim', 'self')
    b.node('mh', 'cast', 1300, 0, class_path=MC); b.link('anim', 'ReturnValue', 'mh', 'Object'); b.link('br', 'then', 'mh', 'execute')
    sets = [('ht', 'ToolHandTarget', ('hb', 'Location')), ('hwt', 'ToolHandWeight', ('ease', 'ReturnValue')),
            ('et', 'ToolElbowTarget', ('elbow', 'ReturnValue')), ('hr', 'HeldToolRotation', ('hb', 'Rotation')),
            ('hrw', 'HeldToolWeight', ('ease', 'ReturnValue'))]
    gp = b.get('pose', 'GripPose', 1600, 1300)
    for i, n in enumerate(NAMES):  # one weight per finger pose: the held one gets alpha, the rest zero
        b.fn('eq%d' % i, K + 'EqualEqual_NameName', 2000 + 300 * i, 1300, B=n); b.link('pose', 'GripPose', 'eq%d' % i, 'A')
        b.fn('w%d' % i, K + 'SelectFloat', 2000 + 300 * i, 1450, B=0.0)
        b.link('ease', 'ReturnValue', 'w%d' % i, 'A'); b.link('eq%d' % i, 'ReturnValue', 'w%d' % i, 'bPickA')
        sets.append(('g%d' % i, 'RightGrip_' + n, ('w%d' % i, 'ReturnValue')))
    prev = 'mh'
    for k, (ref, var, src) in enumerate(sets):
        b.set(ref, var, 1600 + 300 * k, 0, MC); b.link('mh', MH_SET, ref, 'self'); b.link(src[0], src[1], ref, var)
        b.link(prev, 'then', ref, 'execute'); prev = ref
    b.comment('Ease the grip in or out', ['ga', 'gt', 'ease', 'sa'])
    b.comment('While held: the right hand on the anchor (two-bone IK, world rotation) and its Teen finger pose',
              ['anc', 'valid', 'on', 'both', 'br', 'aw', 'gh', 'hw', 'hb', 'right', 'out', 'down', 'pole', 'elbow', 'body', 'anim', 'mh']
              + [r for r, _, _ in sets] + ['pose'] + ['eq%d' % i for i in range(len(NAMES))] + ['w%d' % i for i in range(len(NAMES))])
    b.run()
finally:
    h.release('anim', lease)
print('GRIP_RUNTIME built', NAMES)
