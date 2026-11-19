"""ABP_FoAPlayer_MH (visible Teen body): the right hand's Teen-native grip poses (bake_grips.py:
AS_FoA_TeenGrip_<Name>_R, solved at mesh level in the Blender twin), each in its own Layered Blend Per Bone on the right
thumb and finger chains, chained after the existing post-retarget layers (the phone arm, the slap thumb) and before
Local To Component, so the right two-bone IK carries them. One weight per grip, RightGrip_<Name> (0 = off);
BP_FoAPlayer sets them (one at a time). Replaces the Manny finger layers (AS_FoA_Grip_Tool_R / _Key_R in ABP_FoAPlayer,
GripWeight / KeyGrip), which bend MetaHuman-proportioned fingers through the retarget and miss the Teen's objects.
Idempotent (a grip already wired is left alone; new grips are appended). Compile and save with Hayba afterwards.
  FOA_AREAS=Characters python Tools/Unreal/ue_remote.py Tools/Unreal/player/right_grip_layer.py"""
import json

import unreal
exec(open('P:/FoA/Tools/Unreal/ui/bp_graph.py', encoding='utf-8').read())

MH = '/Game/FoA/Characters/Player/ABP_FoAPlayer_MH'
POSE = '/Game/FoA/Characters/Player/Anims/Hands/AS_FoA_TeenGrip_{}_R'
CHAINS = ('thumb_01_r', 'index_01_r', 'middle_01_r', 'ring_01_r', 'pinky_01_r')
MANIFEST = json.load(open('P:/FoA/Saved/AnimShots/grip_bake.json'))
NAMES = list(MANIFEST)


def link(a, ap, b, bp):
    assert PIN.try_create_connection(Graph.pin(a, ap, 'out'), Graph.pin(b, bp, 'in')), (ap, bp)


assert not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world(), 'PIE running'
ensure_vars(MH, [('RightGrip_' + n, ptype('real'), '0.0', 'Grip', False) for n in NAMES])
ensure_vars(MH, [('ScrewGripTime', ptype('real'), '0.0', 'Grip', False),
                 ('ScrewReleaseWeight', ptype('real'), '0.0', 'Grip', False)])
bp = unreal.load_asset(MH)
unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(bp)
ed = GE.get_graph_editor_by_name(bp, 'AnimGraph')
blend = next(str(n) for n in ed.list_available_nodes([]) if 'layeredblendperbone' in str(n).replace(' ', '').lower())
added = []

def turn_time(player, name):
    if not name.startswith('Screwdriver'):
        return
    pin = Graph.pin(player, 'ExplicitTime', 'in')
    if not PIN.list_connected_pins(pin):
        pos = BEL.get_node_pos(player)
        value = ed.add_get_member_variable_node('ScrewGripTime', '')
        BEL.set_node_pos(value, P(pos.x-240, pos.y+140))
        link(value, 'ScrewGripTime', player, 'ExplicitTime')

for name in NAMES:
    seq = unreal.load_asset(POSE.format(name))
    assert seq, POSE.format(name)
    nodes = list(ed.list_all_nodes())
    existing = next((n for n in nodes if n.get_class().get_name() == 'AnimGraphNode_SequenceEvaluator'
                     and n.get_editor_property('node').get_editor_property('sequence') == seq), None)
    if existing:
        turn_time(existing, name)
        if 'stance' in MANIFEST[name]:
            dests = list(PIN.list_connected_pins(Graph.pin(existing, 'Pose', 'out')))
            assert len(dests) == 1
            layer = PIN.get_owning_node(dests[0])
            n = layer.get_editor_property('node')
            setup = list(n.get_editor_property('layer_setup'))[0]
            filters = list(setup.get_editor_property('branch_filters'))
            if len(filters) != 1 or str(filters[0].get_editor_property('bone_name')) != 'pelvis':
                f = unreal.BranchFilter()
                f.set_editor_property('bone_name', 'pelvis')
                f.set_editor_property('blend_depth', 0)
                setup.set_editor_property('branch_filters', [f])
                n.set_editor_property('layer_setup', [setup])
                layer.set_editor_property('node', n)
                added.append(name + ' stance')
        continue
    l2c = next(n for n in nodes if n.get_class().get_name() == 'AnimGraphNode_LocalToComponentSpace')
    dest = Graph.pin(l2c, 'LocalPose', 'in')
    prev = list(PIN.list_connected_pins(dest))
    assert len(prev) == 1, len(prev)
    prev_node = PIN.get_owning_node(prev[0])
    pos = BEL.get_node_pos(l2c)
    PIN.break_pin_links(dest)
    layer = ed.create_node_from_name(blend, V2(pos.x - 40, pos.y - 380 - 60 * len(added)), [])
    player = ed.create_node_from_name("Animation|Sequences|Evaluate'%s'" % seq.get_name(), V2(pos.x - 360, pos.y - 260 - 60 * len(added)), [])
    assert layer and player and player.get_class().get_name() == 'AnimGraphNode_SequenceEvaluator', (layer, player)
    assert PIN.try_create_connection(prev[0], Graph.pin(layer, 'BasePose', 'in'))
    link(player, 'Pose', layer, 'BlendPoses_0')
    link(layer, 'Pose', l2c, 'LocalPose')
    n = player.get_editor_property('node')
    n.set_editor_property('sequence', seq)
    player.set_editor_property('node', n)
    turn_time(player, name)
    n = layer.get_editor_property('node')
    setups = list(n.get_editor_property('layer_setup'))
    setup = setups[0] if setups else unreal.InputBlendPose()
    filters = []
    for b in (('pelvis',) if 'stance' in MANIFEST[name] else CHAINS):
        f = unreal.BranchFilter()
        f.set_editor_property('bone_name', b)
        f.set_editor_property('blend_depth', 0)
        filters.append(f)
    setup.set_editor_property('branch_filters', filters)
    n.set_editor_property('layer_setup', [setup])
    layer.set_editor_property('node', n)
    v = ed.add_get_member_variable_node('RightGrip_' + name, '')
    BEL.set_node_pos(v, P(pos.x - 360, pos.y - 120 - 60 * len(added)))
    link(v, 'RightGrip_' + name, layer, 'BlendWeights_0')
    c = ed.add_comment_to_nodes('Native %s grip' % name, [layer, player, v], 48)
    BEL.set_comment_color(c, C_VISUAL)
    house_comment_flags(c)
    added.append(name)

# Reuse the phone clip's neutral right fingers for the short ratchet release.
if not any(n.get_class().get_name() == 'K2Node_VariableGet' and
           any(str(PIN.get_pin_name(p)) == 'ScrewReleaseWeight' for p in BEL.list_all_pins(n))
           for n in ed.list_all_nodes()):
    l2c = next(n for n in ed.list_all_nodes() if n.get_class().get_name() == 'AnimGraphNode_LocalToComponentSpace')
    dest = Graph.pin(l2c, 'LocalPose', 'in'); prev = list(PIN.list_connected_pins(dest)); assert len(prev)==1
    pos = BEL.get_node_pos(l2c)
    layer = ed.create_node_from_name(blend, V2(pos.x-40,pos.y-850), [])
    seq = unreal.load_asset('/Game/FoA/Characters/Player/Anims/Hands/AS_FoA_Grip_Phone_L')
    player = ed.create_node_from_name("Animation|Sequences|Evaluate'%s'" % seq.get_name(), V2(pos.x-400,pos.y-800), [])
    n=player.get_editor_property('node');n.set_editor_property('sequence',seq);player.set_editor_property('node',n)
    n=layer.get_editor_property('node');setup=unreal.InputBlendPose();filters=[]
    for bone in CHAINS:
        f=unreal.BranchFilter();f.set_editor_property('bone_name',bone);f.set_editor_property('blend_depth',0);filters.append(f)
    setup.set_editor_property('branch_filters',filters);n.set_editor_property('layer_setup',[setup]);layer.set_editor_property('node',n)
    value=ed.add_get_member_variable_node('ScrewReleaseWeight','');BEL.set_node_pos(value,P(pos.x-400,pos.y-650))
    PIN.break_pin_links(dest);assert PIN.try_create_connection(prev[0],Graph.pin(layer,'BasePose','in'))
    link(player,'Pose',layer,'BlendPoses_0');link(value,'ScrewReleaseWeight',layer,'BlendWeights_0');link(layer,'Pose',l2c,'LocalPose')
    c=ed.add_comment_to_nodes('Release the ratchet',[layer,player,value],48);house_comment_flags(c)
compile_save(MH)
print('RIGHT_GRIP_LAYER added', added, 'of', NAMES)
