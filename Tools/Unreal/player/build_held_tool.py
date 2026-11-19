"""Anim lane: the held screwdriver. The tool rides hand_r; the hand is placed from the tool's frame on the screw.
  FOA_AREAS=Characters python Tools/Unreal/ue_remote.py Tools/Unreal/player/build_held_tool.py FOA_PHASE=<phase>
Phases (each idempotent, edits in place, saves):
  grip_layer   ABP_FoAPlayer (Manny source): AS_FoA_Grip_Tool_R layered onto the right finger branches by GripWeight.
               The runtime retarget carries the closed fingers to the visible body (finger chains are mapped).
  hold_node    ABP_FoAPlayer_MH (visible body): one Transform Bone on hand_r after the key's additive turn, REPLACE in
               world space with HeldToolRotation by HeldToolWeight, so the wrist matches the tool's frame exactly.
  components   BP_FoAPlayer: HeldToolGrip (scene, on Body at hand_r, the palm grip frame) and HeldTool (static mesh,
               hidden, no collision) under it. ToolGripOffset (the grip frame in hand_r space) is written to the CDO.
The Blueprint functions (SetHeldTool, the tool branch of SetToolHandRotation) are Hayba graph batches:
  python Tools/Unreal/player/held_tool_graphs.py"""
import os
import unreal
exec(open('P:/FoA/Tools/Unreal/ui/bp_graph.py', encoding='utf-8').read())

PL = '/Game/FoA/Characters/Player/'
SRC_ABP, MH_ABP, PLAYER = PL + 'ABP_FoAPlayer', PL + 'ABP_FoAPlayer_MH', PL + 'BP_FoAPlayer'
GRIP_POSE = PL + 'Anims/Hands/AS_FoA_Grip_Tool_R'
FINGERS = ('thumb_01_r', 'index_metacarpal_r', 'middle_metacarpal_r', 'ring_metacarpal_r', 'pinky_metacarpal_r')
# The palm grip frame in hand_r space (MetaHuman body; -X runs to the fingers, +Y is the palm, +Z the thumb side):
# palm centre 4.5 cm toward the knuckles and 3 cm off the palm, tool axis 20 deg from the hand's long axis toward
# the thumb-index web (the shaft leaves the fist there), frame Z toward the thumb. The frame origin sits 4 cm up the
# axis from the palm centre, so with the tip 16 cm out the butt of a 23 cm screwdriver rests in the heel of the hand.
# Retune per body rig (BP_FoAPlayer.ToolGripOffset holds the live value).
GRIP_LOC, GRIP_ROT = unreal.Vector(-8.26, 3.0, 1.87), unreal.Rotator(roll=0.0, pitch=20.0, yaw=180.0)
phase = os.environ.get('FOA_PHASE', '')


def palette(ed, *parts):
    norm = lambda s: str(s).replace(' ', '').replace('_', '').lower()  # noqa: E731
    hits = [str(n) for n in ed.list_available_nodes([]) if all(norm(p) in norm(n) for p in parts)]
    assert hits, parts
    return min(hits, key=len)


def link(a, ap, b, bp):
    assert PIN.try_create_connection(Graph.pin(a, ap, 'out'), Graph.pin(b, bp, 'in')), (ap, bp)


def smooth(node, prop='alpha_scale_bias_clamp'):
    s = node.get_editor_property(prop)
    s.set_editor_property('interp_result', True)
    s.set_editor_property('interp_speed_increasing', 8.0)
    s.set_editor_property('interp_speed_decreasing', 10.0)
    node.set_editor_property(prop, s)


def grip_layer():
    ensure_vars(SRC_ABP, [('GripWeight', ptype('real'), '0.0', 'Tool contact', False)])
    bp = unreal.load_asset(SRC_ABP)
    unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(bp)
    ed = GE.get_graph_editor_by_name(bp, 'AnimGraph')
    nodes = list(ed.list_all_nodes())
    layers = [n for n in nodes if n.get_class().get_name() == 'AnimGraphNode_LayeredBoneBlend']
    assert len(layers) <= 1
    root = next(n for n in nodes if n.get_class().get_name() == 'AnimGraphNode_Root')
    if layers:
        layer = layers[0]
        player = next(n for n in nodes if n.get_class().get_name() == 'AnimGraphNode_SequenceEvaluator')
    else:
        result = Graph.pin(root, 'Result', 'in')
        feed = list(PIN.list_connected_pins(result)); assert len(feed) == 1
        pos = BEL.get_node_pos(root)
        PIN.break_pin_links(result)
        layer = ed.create_node_from_name(palette(ed, 'Blends', 'LayeredBlendPerBone'), V2(pos.x, pos.y), []); assert layer
        player = ed.create_node_from_name("Animation|Sequences|Evaluate'AS_FoA_Grip_Tool_R'", V2(pos.x - 300, pos.y + 260), [])
        assert player and player.get_class().get_name() == 'AnimGraphNode_SequenceEvaluator', player
        assert PIN.try_create_connection(feed[0], Graph.pin(layer, 'BasePose', 'in'))
        link(player, 'Pose', layer, 'BlendPoses_0')
        link(layer, 'Pose', root, 'Result')
        BEL.set_node_pos(root, P(pos.x + 400, pos.y))
    n = player.get_editor_property('node')
    n.set_editor_property('sequence', unreal.load_asset(GRIP_POSE))
    n.set_editor_property('explicit_time', 0.0)
    player.set_editor_property('node', n)
    n = layer.get_editor_property('node')
    setups = list(n.get_editor_property('layer_setup'))
    setup = setups[0] if setups else unreal.InputBlendPose()
    filters = []
    for b in FINGERS:
        f = unreal.BranchFilter()
        f.set_editor_property('bone_name', b)
        f.set_editor_property('blend_depth', 0)
        filters.append(f)
    setup.set_editor_property('branch_filters', filters)
    n.set_editor_property('layer_setup', [setup])
    layer.set_editor_property('node', n)
    weights = [v for v in ed.list_all_nodes() if BEL.get_node_title(v).replace(' ', '') == 'GetGripWeight']
    weight = weights[0] if weights else ed.add_get_member_variable_node('GripWeight', '')
    pos = BEL.get_node_pos(layer)
    BEL.set_node_pos(weight, P(pos.x - 300, pos.y + 420))
    link(weight, 'GripWeight', layer, 'BlendWeights_0')
    for c in list(ed.list_comment_nodes()):
        if BEL.get_comment_text(c) == 'Close the working hand':
            ed.remove_comment_node(c)
    c = ed.add_comment_to_nodes('Close the working hand', [layer, player, weight], 48)
    BEL.set_comment_color(c, C_VISUAL); house_comment_flags(c)
    compile_save(SRC_ABP)


def hold_node():
    ensure_vars(MH_ABP, [('HeldToolRotation', ptype(unreal.Rotator), '', 'Tool contact', False),
                         ('HeldToolWeight', ptype('real'), '0.0', 'Tool contact', False)])
    bp = unreal.load_asset(MH_ABP)
    unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(bp)
    ed = GE.get_graph_editor_by_name(bp, 'AnimGraph')
    mods = [n for n in ed.list_all_nodes() if n.get_class().get_name() == 'AnimGraphNode_ModifyBone']
    assert 1 <= len(mods) <= 2, len(mods)
    replace = [m for m in mods if m.get_editor_property('node').get_editor_property('rotation_mode') == unreal.BoneModificationMode.BMM_REPLACE]
    if replace:
        hold = replace[0]
    else:
        turn = mods[0]
        out = Graph.pin(turn, 'Pose', 'out'); after = list(PIN.list_connected_pins(out)); assert len(after) == 1
        pos = BEL.get_node_pos(turn)
        hold = ed.create_node_from_name(palette(ed, 'SkeletalControls', 'Modify'), V2(pos.x + 500, pos.y), [])
        assert hold and hold.get_class().get_name() == 'AnimGraphNode_ModifyBone'
        PIN.break_pin_links(out)
        link(turn, 'Pose', hold, 'ComponentPose')
        assert PIN.try_create_connection(Graph.pin(hold, 'Pose', 'out'), after[0])
        nxt = PIN.get_owning_node(after[0]); np_ = BEL.get_node_pos(nxt)
        BEL.set_node_pos(nxt, P(np_.x + 500, np_.y))
        for o in [n for n in ed.list_all_nodes() if n.get_class().get_name() == 'AnimGraphNode_Root']:
            op = BEL.get_node_pos(o); BEL.set_node_pos(o, P(op.x + 500, op.y))
    n = hold.get_editor_property('node')
    bone = unreal.BoneReference(); bone.set_editor_property('bone_name', 'hand_r')
    n.set_editor_property('bone_to_modify', bone)
    n.set_editor_property('translation_mode', unreal.BoneModificationMode.BMM_IGNORE)
    n.set_editor_property('rotation_mode', unreal.BoneModificationMode.BMM_REPLACE)
    n.set_editor_property('scale_mode', unreal.BoneModificationMode.BMM_IGNORE)
    n.set_editor_property('rotation_space', unreal.BoneControlSpace.BCS_WORLD_SPACE)
    n.set_editor_property('alpha', 0.0)
    smooth(n)
    hold.set_editor_property('node', n)
    pos = BEL.get_node_pos(hold)
    made = [hold]
    for i, (name, pin) in enumerate((('HeldToolRotation', 'Rotation'), ('HeldToolWeight', 'Alpha'))):
        old = [v for v in ed.list_all_nodes() if BEL.get_node_title(v).replace(' ', '') == 'Get' + name]
        v = old[0] if old else ed.add_get_member_variable_node(name, '')
        BEL.set_node_pos(v, P(pos.x - 20, pos.y + 300 + i * 160))
        link(v, name, hold, pin)
        made.append(v)
    for c in list(ed.list_comment_nodes()):
        if BEL.get_comment_text(c) == 'Hold the tool':
            ed.remove_comment_node(c)
    c = ed.add_comment_to_nodes('Hold the tool', made, 48)
    BEL.set_comment_color(c, C_VISUAL); house_comment_flags(c)
    compile_save(MH_ABP)


def components():
    bp = unreal.load_asset(PLAYER)
    unreal.get_editor_subsystem(unreal.EditorActorSubsystem).select_nothing()
    unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(bp)
    sub = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    lib = unreal.SubobjectDataBlueprintFunctionLibrary
    parts = {str(lib.get_variable_name(lib.get_data(h))): h for h in sub.k2_gather_subobject_data_for_blueprint(bp)}

    def ensure(name, kind, parent):
        if name not in parts:
            h, error = sub.add_new_subobject(unreal.AddNewSubobjectParams(parent_handle=parts[parent], new_class=kind, blueprint_context=bp))
            assert not str(error), error
            sub.rename_subobject(h, name); parts[name] = h
        return lib.get_object_for_blueprint(lib.get_data(parts[name]), bp)

    grip = ensure('HeldToolGrip', unreal.SceneComponent, 'Body')
    # SetHeldTool attaches it to hand_r at runtime (the SCS socket is not settable from Python)
    grip.set_editor_property('relative_location', GRIP_LOC)
    grip.set_editor_property('relative_rotation', GRIP_ROT)
    tool = ensure('HeldTool', unreal.StaticMeshComponent, 'HeldToolGrip')
    tool.set_collision_profile_name('NoCollision')
    tool.set_editor_property('visible', False)
    tool.set_editor_property('generate_overlap_events', False)
    compile_save(PLAYER)
    print('GRIP_OFFSET', unreal.Transform(GRIP_LOC, GRIP_ROT, unreal.Vector(1, 1, 1)).export_text() if hasattr(unreal.Transform, 'export_text') else '',
          GRIP_ROT.quaternion())


{'grip_layer': grip_layer, 'hold_node': hold_node, 'components': components}[phase]()
