"""Tool-only hand contact on the visible MetaHuman, after retargeting. No new tick or animation asset.
Phases declare/graph/api/rotation. Compile/save atomically after every phase; normal pose weight defaults zero.
"""
import os
import unreal
exec(open('P:/FoA/Tools/Unreal/ui/bp_graph.py', encoding='utf-8').read())
MH = '/Game/FoA/Characters/Player/ABP_FoAPlayer_MH'
SOURCE = '/Game/FoA/Characters/Player/ABP_FoAPlayer.ABP_FoAPlayer_C'
PLAYER = '/Game/FoA/Characters/Player/BP_FoAPlayer'
K = '/Script/Engine.KismetMathLibrary:'
phase = os.environ.get('FOA_PHASE', 'declare')


def palette(ed, *parts):
    norm = lambda s: str(s).replace(' ', '').replace('_', '').lower()
    hits = [str(n) for n in ed.list_available_nodes([]) if all(norm(p) in norm(n) for p in parts)]
    assert hits, parts
    return min(hits, key=len)


def link(a, ap, b, bp):
    assert PIN.try_create_connection(Graph.pin(a, ap, 'out'), Graph.pin(b, bp, 'in')), (ap, bp)


if phase == 'declare':
    ensure_vars(MH, [('ToolHandTarget', ptype(unreal.Vector), '', 'Tool contact', False),
        ('ToolElbowTarget', ptype(unreal.Vector), '', 'Tool contact', False),
        ('ToolHandWeight', ptype('real'), '0.0', 'Tool contact', False),
        ('ToolHandRotation', ptype(unreal.Rotator), '', 'Tool contact', False)])
    compile_save(MH)
elif phase == 'graph':
    bp = unreal.load_asset(MH)
    unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(bp)
    ed = GE.get_graph_editor_by_name(bp, 'AnimGraph')
    nodes = list(ed.list_all_nodes())
    iks = [n for n in nodes if n.get_class().get_name() == 'AnimGraphNode_TwoBoneIK']; assert len(iks) <= 1
    if not iks:
        retarget = next(n for n in nodes if 'RetargetPoseFromMesh' in n.get_class().get_name())
        output = next(n for n in nodes if n.get_class().get_name() == 'AnimGraphNode_Root')
        PIN.break_pin_links(Graph.pin(retarget, 'Pose', 'out'))
        made = []
        for i, parts in enumerate((('ConvertSpaces', 'LocalToComponent'), ('SkeletalControls', 'TwoBoneIK'),
                                   ('SkeletalControls', 'Modify'), ('ConvertSpaces', 'ComponentToLocal'))):
            n = ed.create_node_from_name(palette(ed, *parts), unreal.Vector2D(i * 500, 0), []); assert n
            made.append(n)
        local, ik, wrist, component = made
        link(retarget, 'Pose', local, 'LocalPose'); link(local, 'ComponentPose', ik, 'ComponentPose')
        link(ik, 'Pose', wrist, 'ComponentPose'); link(wrist, 'Pose', component, 'ComponentPose')
        link(component, 'Pose', output, 'Result')
        BEL.set_node_pos(retarget, unreal.IntPoint(-500, 0)); BEL.set_node_pos(output, unreal.IntPoint(2100, 0))
    else:
        ik = iks[0]
        wrist = next(n for n in nodes if n.get_class().get_name() == 'AnimGraphNode_ModifyBone')
    bone = unreal.BoneReference(); bone.set_editor_property('bone_name', 'hand_r')
    n = ik.get_editor_property('node'); n.set_editor_property('ik_bone', bone)
    n.set_editor_property('effector_location_space', unreal.BoneControlSpace.BCS_WORLD_SPACE)
    n.set_editor_property('joint_target_location_space', unreal.BoneControlSpace.BCS_WORLD_SPACE)
    n.set_editor_property('allow_stretching', False); n.set_editor_property('maintain_effector_rel_rot', True)
    n.set_editor_property('take_rotation_from_effector_space', False); n.set_editor_property('alpha', 0.0)
    smooth = n.get_editor_property('alpha_scale_bias_clamp'); smooth.set_editor_property('interp_result', True)
    smooth.set_editor_property('interp_speed_increasing', 8.0); smooth.set_editor_property('interp_speed_decreasing', 10.0)
    n.set_editor_property('alpha_scale_bias_clamp', smooth); ik.set_editor_property('node', n)
    n = wrist.get_editor_property('node'); n.set_editor_property('bone_to_modify', bone)
    n.set_editor_property('rotation_mode', unreal.BoneModificationMode.BMM_ADDITIVE)
    n.set_editor_property('translation_mode', unreal.BoneModificationMode.BMM_IGNORE)
    n.set_editor_property('scale_mode', unreal.BoneModificationMode.BMM_IGNORE)
    n.set_editor_property('rotation_space', unreal.BoneControlSpace.BCS_WORLD_SPACE); n.set_editor_property('alpha', 0.0)
    wrist.set_editor_property('node', n)
    groups = {'Hold the visible tool': [ik], 'Turn the visible wrist': [wrist]}
    for name, target, pin, x, y in (('ToolHandTarget', ik, 'EffectorLocation', 400, 300),
        ('ToolElbowTarget', ik, 'JointTargetLocation', 400, 470), ('ToolHandWeight', ik, 'Alpha', 400, 640),
        ('ToolHandRotation', wrist, 'Rotation', 1000, 300)):
        old = [v for v in ed.list_all_nodes() if BEL.get_node_title(v).replace(' ', '') == 'Get' + name]
        v = old[0] if old else ed.add_get_member_variable_node(name, '')
        BEL.set_node_pos(v, unreal.IntPoint(x, y)); link(v, name, target, pin)
        groups['Turn the visible wrist' if target == wrist else 'Hold the visible tool'].append(v)
        if name == 'ToolHandWeight':
            link(v, name, wrist, 'Alpha')
    for c in list(ed.list_comment_nodes()):
        if BEL.get_comment_text(c) in groups:
            ed.remove_comment_node(c)
    for title, values in groups.items():
        c = ed.add_comment_to_nodes(title, values, 48); BEL.set_comment_color(c, C_VISUAL); house_comment_flags(c)
    compile_save(MH)
elif phase in ('api', 'rotation'):
    rotate = phase == 'rotation'
    g = Graph.function(PLAYER, 'SetToolHandRotation' if rotate else 'SetToolHandTarget'); e = g.at(entry_node(g), 0, 0)
    body = g.get('Body', 0, 300)
    anim = g.call('/Script/Engine.SkeletalMeshComponent:GetAnimInstance', 300, 300); g.link(body, 'Body', anim, 'self')
    cast = g.node(palette(g.ed, 'CastToABP_FoAPlayer_MH'), 600, 0); g.link(anim, 'ReturnValue', cast, 'Object')
    g.exec_chain(e, cast)
    if rotate:
        value = g.set('ToolHandRotation', 900, 0, class_path=MH + '.ABP_FoAPlayer_MH_C')
        g.link(cast, 'AsABP_FoAPlayer_MH', value, 'self'); g.link(e, 'DeltaWorld', value, 'ToolHandRotation'); g.exec_chain(cast, value)
    else:
        target = g.set('ToolHandTarget', 900, 0, class_path=MH + '.ABP_FoAPlayer_MH_C')
        g.link(cast, 'AsABP_FoAPlayer_MH', target, 'self'); g.link(e, 'TargetWorld', target, 'ToolHandTarget')
        weight = g.call(K + 'FClamp', 900, 400, Min=0.0, Max=1.0); g.link(e, 'Weight', weight, 'Value')
        alpha = g.set('ToolHandWeight', 1200, 0, class_path=MH + '.ABP_FoAPlayer_MH_C')
        g.link(cast, 'AsABP_FoAPlayer_MH', alpha, 'self'); g.link(weight, 'ReturnValue', alpha, 'ToolHandWeight')
        right = g.call('/Script/Engine.Actor:GetActorRightVector', 900, 650)
        rightoff = g.call(K + 'Multiply_VectorFloat', 1200, 650, B=35.0); g.link(right, 'ReturnValue', rightoff, 'A')
        forward = g.call('/Script/Engine.Actor:GetActorForwardVector', 900, 900)
        back = g.call(K + 'Multiply_VectorFloat', 1200, 900, B=-15.0); g.link(forward, 'ReturnValue', back, 'A')
        offset = g.call(K + 'Add_VectorVector', 1500, 650); g.link(rightoff, 'ReturnValue', offset, 'A'); g.link(back, 'ReturnValue', offset, 'B')
        world = g.call(K + 'Add_VectorVector', 1800, 650); g.link(e, 'TargetWorld', world, 'A'); g.link(offset, 'ReturnValue', world, 'B')
        elbow = g.set('ToolElbowTarget', 2100, 0, class_path=MH + '.ABP_FoAPlayer_MH_C')
        g.link(cast, 'AsABP_FoAPlayer_MH', elbow, 'self'); g.link(world, 'ReturnValue', elbow, 'ToolElbowTarget')
        source = g.get('Mesh', 2100, 1000)
        sourceanim = g.call('/Script/Engine.SkeletalMeshComponent:GetAnimInstance', 2400, 1000); g.link(source, 'Mesh', sourceanim, 'self')
        sourcecast = g.node(palette(g.ed, 'CastToABP_FoAPlayer'), 2400, 0); g.link(sourceanim, 'ReturnValue', sourcecast, 'Object')
        zero = g.set('ToolHandWeight', 2700, 0, class_path=SOURCE); g.default(zero, 'ToolHandWeight', 0.0)
        g.link(sourcecast, 'AsABP_FoAPlayer', zero, 'self'); g.exec_chain(cast, target, alpha, elbow, sourcecast, zero)
    c = g.ed.add_comment_to_nodes('Drive the visible working hand', list(g.ed.list_all_nodes()), 48)
    BEL.set_comment_color(c, C_VISUAL); house_comment_flags(c); compile_save(PLAYER)
else:
    raise ValueError(phase)
