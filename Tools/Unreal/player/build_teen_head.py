"""A separate head copies Body bones while retaining the imported ARKit morph curves."""
import unreal
P = '/Game/FoA/Characters/Teen'
E, BEL, BGE, PIN = unreal.EditorAssetLibrary, unreal.BlueprintEditorLibrary, unreal.BlueprintGraphEditor, unreal.BlueprintGraphPinLibrary
body = unreal.load_asset(P + '/Mesh/SK_Teen_Body')
head = unreal.load_asset(P + '/Mesh/SK_Teen_Head')
assert body and head
path = P + '/Anim/ABP_FoA_TeenHead'
bp = unreal.load_asset(path)
if not bp:
    f = unreal.AnimBlueprintFactory()
    f.set_editor_property('target_skeleton', body.get_editor_property('skeleton'))
    f.set_editor_property('parent_class', unreal.AnimInstance)
    bp = unreal.AssetToolsHelpers.get_asset_tools().create_asset('ABP_FoA_TeenHead', P + '/Anim', unreal.AnimBlueprint, f)
unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(bp)
ed = BGE.get_graph_editor_by_name(bp, 'AnimGraph')
out = next(n for n in ed.list_all_nodes() if n.get_class().get_name() == 'AnimGraphNode_Root')
copies = [n for n in ed.list_all_nodes() if n.get_class().get_name() == 'AnimGraphNode_CopyPoseFromMesh']
if not copies:
    key = next(str(n) for n in ed.list_available_nodes([]) if str(n).replace(' ','').endswith('CopyPoseFromMesh'))
    copies = [ed.create_node_from_name(key, unreal.Vector2D(-400,0), [])]
node = copies[0].get_editor_property('node')
node.set_editor_property('use_attached_parent', True)
node.set_editor_property('copy_curves', True)
copies[0].set_editor_property('node', node)
sleep_curves = [n for n in ed.list_all_nodes() if n.get_class().get_name() == 'AnimGraphNode_ModifyCurve']
assert len(sleep_curves) <= 1
if sleep_curves:
    assert PIN.try_create_connection(BEL.find_output_pin(copies[0], 'Pose'), BEL.find_input_pin(sleep_curves[0], 'SourcePose'))
    assert PIN.try_create_connection(BEL.find_output_pin(sleep_curves[0], 'Pose'), BEL.find_input_pin(out, 'Result'))
else:
    assert PIN.try_create_connection(BEL.find_output_pin(copies[0], 'Pose'), BEL.find_input_pin(out, 'Result'))
E.save_loaded_asset(bp, False)
print('Teen head CopyPose + ARKit curves ready')
