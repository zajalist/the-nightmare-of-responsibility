"""Visible Teen follows the hidden Mannequin through IK retargeting.
The existing ABP_FoAPlayer_MH class name is retained for gameplay casts; its target is the Teen skeleton.
FOA_STEP=rig rebuilds IK_FoA_Teen/RTG_Mannequin_to_Teen; abp rebuilds the visible retarget graph.
Compile the AnimBlueprint through Hayba after graph authoring."""
import os

import unreal

P = "/Game/FoA/Characters/Player"
RIGS = P + "/Retarget"
MANNY = "/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple"
ABP_MH = P + "/ABP_FoAPlayer_MH"
EAL, BEL = unreal.EditorAssetLibrary, unreal.BlueprintEditorLibrary
AT = unreal.AssetToolsHelpers.get_asset_tools()
SOT = unreal.RetargetSourceOrTarget


def body_mesh():
    body = unreal.load_asset('/Game/FoA/Characters/Teen/Mesh/SK_Teen_Body')
    assert body, 'Import the normalized Teen meshes first'
    return body


def fresh(name, cls, factory):
    return unreal.load_asset(f"{RIGS}/{name}") or AT.create_asset(name, RIGS, cls, factory)


def step_rig():
    import runpy
    runpy.run_path('P:/FoA/Tools/Unreal/player/build_teen_rig.py', run_name='__main__')


def step_abp():
    body = body_mesh()
    a = unreal.load_asset(ABP_MH)
    if not a:
        f = unreal.AnimBlueprintFactory()
        f.set_editor_property("target_skeleton", body.get_editor_property("skeleton"))
        f.set_editor_property("parent_class", unreal.AnimInstance)
        a = AT.create_asset("ABP_FoAPlayer_MH", P, unreal.AnimBlueprint, f)
    unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(a)
    ed = unreal.BlueprintGraphEditor.get_graph_editor_by_name(a, "AnimGraph")
    for n in ed.list_all_nodes():
        if not BEL.get_node_title(n).startswith("Output Pose"):
            ed.remove_nodes([n])
    out = next(n for n in ed.list_all_nodes() if BEL.get_node_title(n).startswith("Output Pose"))
    entry = next(str(e) for e in ed.list_available_nodes([]) if str(e).replace(" ", "").endswith("RetargetPoseFromMesh"))
    rt = ed.create_node_from_name(entry, unreal.Vector2D(-320, 0), [])
    BEL.set_node_pos(rt, unreal.IntPoint(-320, 0))
    BEL.set_node_pos(out, unreal.IntPoint(0, 0))
    node = rt.get_editor_property("node")
    node.set_editor_property("retarget_from", unreal.RetargetSourceMode.PARENT_SKELETAL_MESH_COMPONENT)  # the hidden Mannequin
    node.set_editor_property("ik_retargeter_asset", unreal.load_asset(RIGS + "/RTG_Mannequin_to_Teen"))
    rt.set_editor_property("node", node)
    assert unreal.BlueprintGraphPinLibrary.try_create_connection(BEL.find_output_pin(rt, "Pose"), BEL.find_input_pin(out, "Result"))
    EAL.save_loaded_asset(a, False)
    if 'ToolHandWeight' in [str(n) for n in BEL.list_member_variable_names(a)]:
        import runpy
        old_phase = os.environ.get('FOA_PHASE')
        try:
            os.environ['FOA_PHASE'] = 'graph'
            runpy.run_path('P:/FoA/Tools/Unreal/player/build_tool_hand_contact.py', run_name='__main__')
        finally:
            if old_phase is None:
                os.environ.pop('FOA_PHASE', None)
            else:
                os.environ['FOA_PHASE'] = old_phase
    print("ABP_FoAPlayer_MH:", entry, "-> Output Pose (compile with Hayba anim_blueprint_compile)")


{"rig": step_rig, "abp": step_abp}[os.environ["FOA_STEP"]]()
