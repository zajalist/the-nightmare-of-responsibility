"""ABP_FoAPlayer_MH (visible Teen body): the left-arm phone hold (v2: the whole arm from upperarm_l), layered right after the
retarget, so the phone hold's arm IK carries it. AS_FoA_Grip_Phone_L is evaluated at PhoneGripTime (0 = hold, 1/30 s =
thumb pressed), blended in by PhoneGripWeight. BP_FoAPlayer.UpdatePhoneHold drives both (phone_grip_graphs.py).
Idempotent. Compile and save with Hayba afterwards (bp_graph rule: Python never compiles).
  python Tools/Unreal/ue_remote.py Tools/Unreal/player/phone_grip_layer.py FOA_AREAS=Characters"""
import unreal
exec(open('P:/FoA/Tools/Unreal/ui/bp_graph.py', encoding='utf-8').read())

MH = '/Game/FoA/Characters/Player/ABP_FoAPlayer_MH'
POSE = '/Game/FoA/Characters/Player/Anims/Hands/AS_FoA_Grip_Phone_L'
DIGITS = ('upperarm_l',)  # v2: the whole left arm, hand and fingers (the phone rides hand_l)


def link(a, ap, b, bp):
    assert PIN.try_create_connection(Graph.pin(a, ap, 'out'), Graph.pin(b, bp, 'in')), (ap, bp)


ensure_vars(MH, [('PhoneGripWeight', ptype('real'), '0.0', 'Phone', False), ('PhoneGripTime', ptype('real'), '0.0', 'Phone', False)])
bp = unreal.load_asset(MH)
seq = unreal.load_asset(POSE)
assert seq, POSE
unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(bp)
ed = GE.get_graph_editor_by_name(bp, 'AnimGraph')
nodes = list(ed.list_all_nodes())
players = [n for n in nodes if n.get_class().get_name() == 'AnimGraphNode_SequenceEvaluator'
           and n.get_editor_property('node').get_editor_property('sequence') == seq]
if players:
    player = players[0]
    layer = PIN.get_owning_node(next(iter(PIN.list_connected_pins(Graph.pin(player, 'Pose', 'out')))))
else:
    rt = next(n for n in nodes if n.get_class().get_name() == 'AnimGraphNode_RetargetPoseFromMesh')
    out = Graph.pin(rt, 'Pose', 'out')
    after = list(PIN.list_connected_pins(out))
    assert len(after) == 1, len(after)
    pos = BEL.get_node_pos(rt)
    PIN.break_pin_links(out)
    blend = next(str(n) for n in ed.list_available_nodes([]) if 'layeredblendperbone' in str(n).replace(' ', '').lower())
    layer = ed.create_node_from_name(blend, V2(pos.x + 350, pos.y), [])
    player = ed.create_node_from_name("Animation|Sequences|Evaluate'AS_FoA_Grip_Phone_L'", V2(pos.x + 50, pos.y + 260), [])
    assert layer and player and player.get_class().get_name() == 'AnimGraphNode_SequenceEvaluator', (layer, player)
    link(rt, 'Pose', layer, 'BasePose')
    link(player, 'Pose', layer, 'BlendPoses_0')
    assert PIN.try_create_connection(Graph.pin(layer, 'Pose', 'out'), after[0])
n = player.get_editor_property('node')
n.set_editor_property('sequence', seq)
player.set_editor_property('node', n)
n = layer.get_editor_property('node')
setups = list(n.get_editor_property('layer_setup'))
setup = setups[0] if setups else unreal.InputBlendPose()
filters = []
for b in DIGITS:
    f = unreal.BranchFilter()
    f.set_editor_property('bone_name', b)
    f.set_editor_property('blend_depth', 0)
    filters.append(f)
setup.set_editor_property('branch_filters', filters)
n.set_editor_property('layer_setup', [setup])
layer.set_editor_property('node', n)
pos = BEL.get_node_pos(layer)
for name, target, dy in (('PhoneGripWeight', (layer, 'BlendWeights_0'), 420), ('PhoneGripTime', (player, 'ExplicitTime'), 560)):
    old = [v for v in ed.list_all_nodes() if BEL.get_node_title(v).replace(' ', '') == 'Get' + name]
    v = old[0] if old else ed.add_get_member_variable_node(name, '')
    BEL.set_node_pos(v, P(pos.x - 320, pos.y + dy))
    PIN.break_pin_links(Graph.pin(target[0], target[1], 'in'))
    link(v, name, target[0], target[1])
for c in list(ed.list_comment_nodes()):
    if BEL.get_comment_text(c) == 'Left hand holds the phone':
        ed.remove_comment_node(c)
c = ed.add_comment_to_nodes('Left hand holds the phone', [layer, player], 48)
BEL.set_comment_color(c, C_VISUAL)
house_comment_flags(c)
compile_save(MH)
print('PHONE_GRIP_LAYER', [str(f.get_editor_property('bone_name')) for f in filters])
