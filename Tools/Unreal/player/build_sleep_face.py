"""Protagonist-only DNA eyelid closure, preserving Face CopyPose and RigLogic. Run only after editor recovery.
Phases duplicate/declare/face/player/publish; compile with Hayba between phases. No new tick.
"""
import os
import unreal
exec(open('P:/FoA/Tools/Unreal/ui/bp_graph.py', encoding='utf-8').read())
assert not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world(), 'Never mutate during user PIE'
FACE = '/Game/FoA/Characters/Player/ABP_FoA_Face'
PLAYER = '/Game/FoA/Characters/Player/BP_FoAPlayer'
phase = os.environ.get('FOA_PHASE', 'duplicate')


def palette(ed, *parts):
    norm = lambda s: str(s).replace(' ', '').replace('_', '').lower()
    hits = [str(n) for n in ed.list_available_nodes([]) if all(norm(p) in norm(n) for p in parts)]
    assert hits, parts
    return min(hits, key=len)


if phase == 'duplicate':
    if not unreal.EditorAssetLibrary.does_asset_exist(FACE):
        assert unreal.EditorAssetLibrary.duplicate_asset('/Game/FoA/Characters/Protagonist/Common/Face/ABP_Face', FACE)
    assert unreal.EditorAssetLibrary.save_asset(FACE, False)
elif phase == 'declare':
    ensure_vars(FACE, [('SleepEyeClosure', ptype('real'), '0.0', 'Sleep', False)])
    ensure_vars(PLAYER, [('SleepEyeClosure', ptype('real'), '0.0', 'Sleep', True)])
    if 'UpdateSleepEyes' not in [str(n) for n in BEL.list_graph_names(unreal.load_asset(PLAYER))]:
        Graph.function(PLAYER, 'UpdateSleepEyes')
    compile_save(FACE); compile_save(PLAYER)
elif phase == 'face':
    bp = unreal.load_asset(FACE)
    unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(bp)
    ed = GE.get_graph_editor_by_name(bp, 'AnimGraph')
    nodes = list(ed.list_all_nodes())
    pose = next(n for n in nodes if n.get_class().get_name() == 'AnimGraphNode_CopyPoseFromMesh')
    output = next(n for n in nodes if n.get_class().get_name() == 'AnimGraphNode_Root')
    existing = [n for n in nodes if n.get_class().get_name() == 'AnimGraphNode_ModifyCurve']; assert len(existing) <= 1
    curve = existing[0] if existing else ed.create_node_from_name(palette(ed, 'ModifyCurve'), unreal.Vector2D(0, 0), [])
    assert curve and curve.get_class().get_name() == 'AnimGraphNode_ModifyCurve'
    data = curve.get_editor_property('node')
    # Exact raw controls are present in the current teenage DNA and Face_Archetype skeleton.
    data.set_editor_property('curve_map', {unreal.Name('CTRL_expressions_eyeBlinkL'): 1.0, unreal.Name('CTRL_expressions_eyeBlinkR'): 1.0})
    data.set_editor_property('apply_mode', unreal.ModifyCurveApplyMode.BLEND)
    data.set_editor_property('alpha', 0.0); curve.set_editor_property('node', data)
    PIN.break_pin_links(Graph.pin(pose, 'Pose', 'out'))
    assert PIN.try_create_connection(Graph.pin(pose, 'Pose', 'out'), Graph.pin(curve, 'SourcePose', 'in'))
    assert PIN.try_create_connection(Graph.pin(curve, 'Pose', 'out'), Graph.pin(output, 'Result', 'in'))
    variables = [n for n in nodes if BEL.get_node_title(n).replace(' ', '') == 'GetSleepEyeClosure']
    value = variables[0] if variables else ed.add_get_member_variable_node('SleepEyeClosure', '')
    assert PIN.try_create_connection(Graph.pin(value, 'SleepEyeClosure', 'out'), Graph.pin(curve, 'Alpha', 'in'))
    for n, x, y in ((pose, -400, 0), (curve, 0, 0), (output, 400, 0), (value, 0, 280)):
        BEL.set_node_pos(n, unreal.IntPoint(x, y))
    for c in list(ed.list_comment_nodes()):
        if BEL.get_comment_text(c) == 'Close sleeping eyelids':
            ed.remove_comment_node(c)
    c = ed.add_comment_to_nodes('Close sleeping eyelids', [curve, value], 48)
    BEL.set_comment_color(c, C_VISUAL); house_comment_flags(c); compile_save(FACE)
elif phase == 'player':
    g = Graph.function(PLAYER, 'UpdateSleepEyes'); e = g.at(entry_node(g), 0, 0)
    face = g.get('Face', 0, 300)
    anim = g.call('/Script/Engine.SkeletalMeshComponent:GetAnimInstance', 300, 300); g.link(face, 'Face', anim, 'self')
    cast = g.node(palette(g.ed, 'CastToABP_FoA_Face'), 600, 0); g.link(anim, 'ReturnValue', cast, 'Object')
    source = g.get('SleepEyeClosure', 600, 350)
    clamp = g.call('/Script/Engine.KismetMathLibrary:FClamp', 900, 350, Min=0.0, Max=1.0)
    g.link(source, 'SleepEyeClosure', clamp, 'Value')
    target = g.set('SleepEyeClosure', 1200, 0, class_path=FACE + '.ABP_FoA_Face_C')
    g.link(cast, 'AsABP_FoA_Face', target, 'self'); g.link(clamp, 'ReturnValue', target, 'SleepEyeClosure')
    g.exec_chain(e, cast, target)
    c = g.ed.add_comment_to_nodes('Publish the sleeping expression', list(g.ed.list_all_nodes()), 48)
    BEL.set_comment_color(c, C_VISUAL); house_comment_flags(c); compile_save(PLAYER)
elif phase == 'publish':
    g = Graph(PLAYER, 'UpdatePlayerPos')
    if not any(BEL.get_node_title(n).splitlines()[0] == 'UpdateSleepEyes' for n in g.ed.list_all_nodes()):
        last = next(n for n in g.ed.list_all_nodes() if BEL.get_node_title(n).splitlines()[0] == 'UpdateFaceMaskPose')
        follow = list(PIN.list_connected_pins(BEL.find_then_pin(last)))
        call = g.call(PLAYER + '.BP_FoAPlayer_C:UpdateSleepEyes', 1800, 0)
        PIN.break_pin_links(BEL.find_then_pin(last)); g.exec_chain(last, call)
        for pin in follow:
            assert PIN.try_create_connection(BEL.find_then_pin(call), pin)
    compile_save(PLAYER)
else:
    raise ValueError(phase)
