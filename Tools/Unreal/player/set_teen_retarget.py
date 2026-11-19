"""Update the existing visible-body retarget node without replacing its IK graph or class."""
import unreal
P='/Game/FoA/Characters/Player'
bp=unreal.load_asset(P+'/ABP_FoAPlayer_MH')
unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(bp)
ed=unreal.BlueprintGraphEditor.get_graph_editor_by_name(bp,'AnimGraph')
node=next(n for n in ed.list_all_nodes() if n.get_class().get_name()=='AnimGraphNode_RetargetPoseFromMesh')
data=node.get_editor_property('node')
data.set_editor_property('ik_retargeter_asset',unreal.load_asset(P+'/Retarget/RTG_Mannequin_to_Teen'))
node.set_editor_property('node',data)
assert unreal.EditorAssetLibrary.save_loaded_asset(bp,False)
print('Existing visible body uses Teen retarget; IK/grip graph retained')
