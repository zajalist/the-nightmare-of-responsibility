"""Right-hand contact for door tools. Phases declare, graph, api; preserve the existing locomotion/look/foot rig.
Runs only outside PIE under the ABP_FoAPlayer/BP_FoAPlayer asset leases. Native compile/save after each phase.
"""
import os
import unreal
exec(open('P:/FoA/Tools/Unreal/ui/bp_graph.py', encoding='utf-8').read())

ABP = '/Game/FoA/Characters/Player/ABP_FoAPlayer'
PLAYER = '/Game/FoA/Characters/Player/BP_FoAPlayer'
phase = os.environ.get('FOA_PHASE', 'declare')
K = '/Script/Engine.KismetMathLibrary:'


def palette(ed, *parts):
    norm = lambda s: str(s).replace(' ', '').replace('_', '').lower()
    found = [str(n) for n in ed.list_available_nodes([]) if all(norm(p) in norm(n) for p in parts)]
    assert found, parts
    return min(found, key=len)


if phase == 'rotation_declare_abp':
    ensure_vars(ABP, [('ToolHandRotation', ptype(unreal.Rotator), '', 'Tool contact', False)])
    compile_save(ABP)
elif phase == 'rotation_declare_player':
    if 'SetToolHandRotation' not in [str(n) for n in BEL.list_graph_names(unreal.load_asset(PLAYER))]:
        Graph.function(PLAYER, 'SetToolHandRotation', inputs=[('DeltaWorld', ptype(unreal.Rotator))])
    compile_save(PLAYER)
elif phase == 'declare':
    ensure_vars(ABP, [('ToolHandTarget', ptype(unreal.Vector), '', 'Tool contact', False),
                      ('ToolElbowTarget', ptype(unreal.Vector), '', 'Tool contact', False),
                      ('ToolHandRotation', ptype(unreal.Rotator), '', 'Tool contact', False),
                      ('ToolHandWeight', ptype('real'), '0.0', 'Tool contact', False)])
    if 'SetToolHandTarget' not in [str(n) for n in BEL.list_graph_names(unreal.load_asset(PLAYER))]:
        Graph.function(PLAYER, 'SetToolHandTarget', inputs=[('TargetWorld', ptype(unreal.Vector)), ('Weight', ptype('real'))])
    if 'SetToolHandRotation' not in [str(n) for n in BEL.list_graph_names(unreal.load_asset(PLAYER))]:
        Graph.function(PLAYER, 'SetToolHandRotation', inputs=[('DeltaWorld', ptype(unreal.Rotator))])
    compile_save(ABP); compile_save(PLAYER)
elif phase == 'graph':
    bp = unreal.load_asset(ABP)
    unreal.get_editor_subsystem(unreal.EditorActorSubsystem).select_nothing()
    unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(bp)
    ed = GE.get_graph_editor_by_name(bp, 'AnimGraph')
    found = [n for n in ed.list_all_nodes() if n.get_class().get_name() == 'AnimGraphNode_TwoBoneIK']
    if found:
        assert len(found) == 1, 'Do not silently choose among pre-existing hand IK nodes'
        ik = found[0]
    else:
        look = next(n for n in ed.list_all_nodes() if n.get_class().get_name() == 'AnimGraphNode_LookAt')
        pos = BEL.get_node_pos(look)
        ik = ed.create_node_from_name(palette(ed, 'SkeletalControls', 'TwoBoneIK'), unreal.Vector2D(pos.x + 360, pos.y), [])
        assert ik
        pose = Graph.pin(look, 'Pose', 'out')
        targets = list(PIN.list_connected_pins(pose)); assert len(targets) == 1
        PIN.break_pin_links(pose)
        assert PIN.try_create_connection(pose, Graph.pin(ik, 'ComponentPose', 'in'))
        assert PIN.try_create_connection(Graph.pin(ik, 'Pose', 'out'), targets[0])
    node = ik.get_editor_property('node')
    node.set_editor_property('alpha', 0.0)
    bone = unreal.BoneReference(); bone.set_editor_property('bone_name', 'hand_r')
    node.set_editor_property('ik_bone', bone)
    node.set_editor_property('effector_location_space', unreal.BoneControlSpace.BCS_WORLD_SPACE)
    node.set_editor_property('joint_target_location_space', unreal.BoneControlSpace.BCS_WORLD_SPACE)
    node.set_editor_property('allow_stretching', False)
    node.set_editor_property('take_rotation_from_effector_space', False)
    node.set_editor_property('maintain_effector_rel_rot', True)
    clamp = node.get_editor_property('alpha_scale_bias_clamp')
    clamp.set_editor_property('interp_result', True)
    clamp.set_editor_property('interp_speed_increasing', 8.0)
    clamp.set_editor_property('interp_speed_decreasing', 10.0)
    node.set_editor_property('alpha_scale_bias_clamp', clamp)
    ik.set_editor_property('node', node)
    pos = BEL.get_node_pos(ik)
    for c in list(ed.list_comment_nodes()):
        if BEL.get_comment_text(c) == 'Hold the tool grip':
            ed.remove_comment_node(c)
    made = [ik]
    for i, (name, pin) in enumerate((('ToolHandTarget', 'EffectorLocation'), ('ToolElbowTarget', 'JointTargetLocation'), ('ToolHandWeight', 'Alpha'))):
        existing = [n for n in ed.list_all_nodes() if BEL.get_node_title(n).replace(' ', '') == 'Get' + name]
        get = existing[0] if existing else ed.add_get_member_variable_node(name, '')
        BEL.set_node_pos(get, unreal.IntPoint(pos.x - 300, pos.y + 250 + i * 160))
        assert PIN.try_create_connection(Graph.pin(get, name, 'out'), Graph.pin(ik, pin, 'in'))
        made.append(get)
    c = ed.add_comment_to_nodes('Hold the tool grip', made, 48); BEL.set_comment_color(c, C_VISUAL); house_comment_flags(c)
    if 'ToolHandRotation' in [str(n) for n in BEL.list_member_variable_names(bp)]:
        # One hand-only control after IK composes wrist turning with the existing grip pose.
        turns = [n for n in ed.list_all_nodes() if n.get_class().get_name() == 'AnimGraphNode_ModifyBone'
                 and str(n.get_editor_property('node').get_editor_property('bone_to_modify').get_editor_property('bone_name')) == 'hand_r']
        assert len(turns) <= 1, 'Do not add a second wrist rotation control'
        if turns:
            wrist = turns[0]
        else:
            pos = BEL.get_node_pos(ik)
            wrist = ed.create_node_from_name(palette(ed, 'SkeletalControls', 'Modify'), unreal.Vector2D(pos.x + 360, pos.y), [])
            assert wrist and wrist.get_class().get_name() == 'AnimGraphNode_ModifyBone'
            pose = Graph.pin(ik, 'Pose', 'out'); targets = list(PIN.list_connected_pins(pose)); assert len(targets) == 1
            PIN.break_pin_links(pose)
            assert PIN.try_create_connection(pose, Graph.pin(wrist, 'ComponentPose', 'in'))
            assert PIN.try_create_connection(Graph.pin(wrist, 'Pose', 'out'), targets[0])
        modifier = wrist.get_editor_property('node')
        bone = unreal.BoneReference(); bone.set_editor_property('bone_name', 'hand_r')
        modifier.set_editor_property('bone_to_modify', bone)
        modifier.set_editor_property('translation_mode', unreal.BoneModificationMode.BMM_IGNORE)
        modifier.set_editor_property('rotation_mode', unreal.BoneModificationMode.BMM_ADDITIVE)
        modifier.set_editor_property('scale_mode', unreal.BoneModificationMode.BMM_IGNORE)
        modifier.set_editor_property('rotation_space', unreal.BoneControlSpace.BCS_WORLD_SPACE)
        modifier.set_editor_property('alpha', 0.0)
        wrist.set_editor_property('node', modifier)
        pos = BEL.get_node_pos(wrist)
        wrist_nodes = [wrist]
        for i, (name, pin) in enumerate((('ToolHandRotation', 'Rotation'), ('ToolHandWeight', 'Alpha'))):
            matches = [n for n in ed.list_all_nodes() if BEL.get_node_title(n).replace(' ', '') == 'Get' + name]
            value = matches[0] if matches else ed.add_get_member_variable_node(name, '')
            BEL.set_node_pos(value, unreal.IntPoint(pos.x - 260, pos.y + 350 + i * 160))
            assert PIN.try_create_connection(Graph.pin(value, name, 'out'), Graph.pin(wrist, pin, 'in'))
            wrist_nodes.append(value)
        for c in list(ed.list_comment_nodes()):
            if BEL.get_comment_text(c) in ('Turn the wrist with the tool', 'Turn the working wrist'):
                ed.remove_comment_node(c)
        c = ed.add_comment_to_nodes('Turn the working wrist', wrist_nodes, 48)
        BEL.set_comment_color(c, C_VISUAL); house_comment_flags(c)
        # Give each added control its own column and keep existing foot IK/output to its right.
        look = next(n for n in ed.list_all_nodes() if n.get_class().get_name() == 'AnimGraphNode_LookAt')
        start = BEL.get_node_pos(look)
        BEL.set_node_pos(ik, unreal.IntPoint(start.x + 600, start.y))
        BEL.set_node_pos(wrist, unreal.IntPoint(start.x + 1200, start.y))
        tail, cursor = [], wrist
        for i in range(6):
            pins = [p for p in BEL.list_output_pins(cursor) if str(PIN.get_pin_name(p)) in ('Pose', 'ComponentPose')]
            links = [p for pin in pins for p in PIN.list_connected_pins(pin)]
            if not links:
                break
            assert len(links) == 1
            cursor = PIN.get_owning_node(links[0]); tail.append(cursor)
            BEL.set_node_pos(cursor, unreal.IntPoint(start.x + 1800 + i * 500, start.y))
        owned = {}
        for name in ('ToolHandTarget', 'ToolElbowTarget', 'ToolHandWeight', 'ToolHandRotation'):
            owned[name] = next(n for n in ed.list_all_nodes() if BEL.get_node_title(n).replace(' ', '') == 'Get' + name)
        for i, name in enumerate(('ToolHandTarget', 'ToolElbowTarget', 'ToolHandWeight')):
            BEL.set_node_pos(owned[name], unreal.IntPoint(start.x + 600, start.y + 300 + i * 170))
        BEL.set_node_pos(owned['ToolHandRotation'], unreal.IntPoint(start.x + 1200, start.y + 350))
        for c in list(ed.list_comment_nodes()):
            if BEL.get_comment_text(c) in ('Hold the tool grip', 'Turn the working wrist', 'Foot IK', 'FoA: foot IK gate', 'Head look-at'):
                ed.remove_comment_node(c)
        head = [look] + [PIN.get_owning_node(p) for p in PIN.list_connected_pins(Graph.pin(look, 'ComponentPose', 'in'))]
        head += [n for n in ed.list_all_nodes() if BEL.get_node_title(n).replace(' ', '') in ('GetLookAtAlpha', 'GetLookAtLocation')]
        c = ed.add_comment_to_nodes('Head look-at', head, 48); BEL.set_comment_color(c, C_VISUAL); house_comment_flags(c)
        for title, nodes in (('Hold the tool grip', [ik, owned['ToolHandTarget'], owned['ToolElbowTarget'], owned['ToolHandWeight']]),
                             ('Turn the working wrist', [wrist, owned['ToolHandRotation']])):
            c = ed.add_comment_to_nodes(title, nodes, 48); BEL.set_comment_color(c, C_VISUAL); house_comment_flags(c)
        rig = next((n for n in tail if n.get_class().get_name() == 'AnimGraphNode_ControlRig'), None)
        if rig:
            foot = [n for n in tail if n.get_class().get_name() != 'AnimGraphNode_Root']
            queue = [p for p in BEL.list_input_pins(rig) if str(PIN.get_pin_name(p)) == 'ShouldDoIKTrace']
            seen = set(foot)
            while queue:
                for p in PIN.list_connected_pins(queue.pop()):
                    n = PIN.get_owning_node(p)
                    if n not in seen:
                        seen.add(n); foot.append(n); queue += list(BEL.list_input_pins(n))
            pos = BEL.get_node_pos(rig)
            data = [n for n in foot if not n.get_class().get_name().startswith('AnimGraphNode_')]
            for i, n in enumerate(data):
                BEL.set_node_pos(n, unreal.IntPoint(pos.x - 300 + (i % 2) * 250, pos.y + 300 + (i // 2) * 170))
            c = ed.add_comment_to_nodes('Foot IK', foot, 48); BEL.set_comment_color(c, C_VISUAL); house_comment_flags(c)
    compile_save(ABP)
elif phase == 'api':
    g = Graph.function(PLAYER, 'SetToolHandTarget'); e = g.at(entry_node(g), 0, 0)
    mesh = g.get('Mesh', 0, 300)
    anim = g.call('/Script/Engine.SkeletalMeshComponent:GetAnimInstance', 300, 300); g.link(mesh, 'Mesh', anim, 'self')
    cast = g.node(palette(g.ed, 'CastToABP_FoAPlayer'), 600, 0); g.link(anim, 'ReturnValue', cast, 'Object'); g.exec_chain(e, cast)
    target = g.set('ToolHandTarget', 900, 0, class_path=ABP + '.ABP_FoAPlayer_C')
    g.link(cast, 'AsABP_FoAPlayer', target, 'self'); g.link(e, 'TargetWorld', target, 'ToolHandTarget')
    weight = g.call(K + 'FClamp', 900, 400, Min=0.0, Max=1.0); g.link(e, 'Weight', weight, 'Value')
    alpha = g.set('ToolHandWeight', 1200, 0, class_path=ABP + '.ABP_FoAPlayer_C')
    g.link(cast, 'AsABP_FoAPlayer', alpha, 'self'); g.link(weight, 'ReturnValue', alpha, 'ToolHandWeight')
    right = g.call('/Script/Engine.Actor:GetActorRightVector', 900, 650)
    rightoff = g.call(K + 'Multiply_VectorFloat', 1200, 650, B=35.0); g.link(right, 'ReturnValue', rightoff, 'A')
    forward = g.call('/Script/Engine.Actor:GetActorForwardVector', 900, 900)
    back = g.call(K + 'Multiply_VectorFloat', 1200, 900, B=-15.0); g.link(forward, 'ReturnValue', back, 'A')
    offset = g.call(K + 'Add_VectorVector', 1500, 650)
    g.link(rightoff, 'ReturnValue', offset, 'A'); g.link(back, 'ReturnValue', offset, 'B')
    elbowworld = g.call(K + 'Add_VectorVector', 1800, 650)
    g.link(e, 'TargetWorld', elbowworld, 'A'); g.link(offset, 'ReturnValue', elbowworld, 'B')
    elbow = g.set('ToolElbowTarget', 2100, 0, class_path=ABP + '.ABP_FoAPlayer_C')
    g.link(cast, 'AsABP_FoAPlayer', elbow, 'self'); g.link(elbowworld, 'ReturnValue', elbow, 'ToolElbowTarget')
    g.exec_chain(cast, target, alpha, elbow)
    c = g.ed.add_comment_to_nodes('Reach without stretching', list(g.ed.list_all_nodes()), 48)
    BEL.set_comment_color(c, C_VISUAL); house_comment_flags(c)
    compile_save(PLAYER)
elif phase == 'rotation_api':
    g = Graph.function(PLAYER, 'SetToolHandRotation'); e = g.at(entry_node(g), 0, 0)
    mesh = g.get('Mesh', 0, 300)
    anim = g.call('/Script/Engine.SkeletalMeshComponent:GetAnimInstance', 300, 300); g.link(mesh, 'Mesh', anim, 'self')
    cast = g.node(palette(g.ed, 'CastToABP_FoAPlayer'), 600, 0); g.link(anim, 'ReturnValue', cast, 'Object')
    target = g.set('ToolHandRotation', 900, 0, class_path=ABP + '.ABP_FoAPlayer_C')
    g.link(cast, 'AsABP_FoAPlayer', target, 'self'); g.link(e, 'DeltaWorld', target, 'ToolHandRotation')
    g.exec_chain(e, cast, target)
    c = g.ed.add_comment_to_nodes('Turn only the working wrist', list(g.ed.list_all_nodes()), 48)
    BEL.set_comment_color(c, C_VISUAL); house_comment_flags(c)
    compile_save(PLAYER)
else:
    raise ValueError(phase)

# Preserve visible-MH contact when the original source-animation helper is regenerated.
if phase in ('api', 'rotation_api'):
    mh = unreal.load_asset('/Game/FoA/Characters/Player/ABP_FoAPlayer_MH')
    if mh and 'ToolHandWeight' in [str(n) for n in BEL.list_member_variable_names(mh)]:
        import runpy
        previous_phase = os.environ.get('FOA_PHASE')
        try:
            os.environ['FOA_PHASE'] = 'rotation' if phase == 'rotation_api' else 'api'
            runpy.run_path('P:/FoA/Tools/Unreal/player/build_tool_hand_contact.py', run_name='__main__')
        finally:
            if previous_phase is None:
                os.environ.pop('FOA_PHASE', None)
            else:
                os.environ['FOA_PHASE'] = previous_phase
