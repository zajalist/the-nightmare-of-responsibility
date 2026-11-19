"""Reuse the existing Manny retarget route for the imported MPFB game_engine teen."""
import unreal
import sys
sys.path.insert(0,'P:/FoA/Tools/Unreal/player')
from finger_chains import fix_fingers
P = '/Game/FoA/Characters/Player'
T = '/Game/FoA/Characters/Teen'
E = unreal.EditorAssetLibrary
AT = unreal.AssetToolsHelpers.get_asset_tools()
SOT = unreal.RetargetSourceOrTarget
body = unreal.load_asset(T + '/Mesh/SK_Teen_Body')
assert body
rig = unreal.load_asset(P + '/Retarget/IK_FoA_Teen') or AT.create_asset('IK_FoA_Teen', P + '/Retarget', unreal.IKRigDefinition, unreal.IKRigDefinitionFactory())
c = unreal.IKRigController.get_controller(rig)
c.set_skeletal_mesh(body)
auto = c.apply_auto_generated_retarget_definition()
assert auto, 'The standard game_engine bone names must auto-characterize'
if not c.get_num_solvers():
    c.apply_auto_fbik()
E.save_loaded_asset(rig, False)
rtg = unreal.load_asset(P + '/Retarget/RTG_Mannequin_to_Teen') or AT.create_asset('RTG_Mannequin_to_Teen', P + '/Retarget', unreal.IKRetargeter, unreal.IKRetargetFactory())
r = unreal.IKRetargeterController.get_controller(rtg)
src = unreal.load_asset(P + '/Retarget/IK_FoA_Mannequin')
r.set_ik_rig(SOT.SOURCE, src); r.set_ik_rig(SOT.TARGET, rig)
r.set_preview_mesh(SOT.SOURCE, unreal.load_asset('/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple'))
r.set_preview_mesh(SOT.TARGET, body)
if not r.get_num_retarget_ops():
    r.add_default_ops()
names = [str(r.get_op_name(i)) for i in range(r.get_num_retarget_ops())]
if 'Retarget IK Goals' not in names:
    i = r.add_retarget_op('/Script/IKRig.IKRetargetIKChainsOp')
    r.move_retarget_op_in_stack(i, names.index('FK Chains') + 1)
r.assign_ik_rig_to_all_ops(SOT.SOURCE, src); r.assign_ik_rig_to_all_ops(SOT.TARGET, rig)
r.auto_map_chains(unreal.AutoMapChainType.FUZZY, True)
if 'FoA_MannyAligned' not in [str(k) for k in r.get_retarget_poses(SOT.TARGET)]:
    r.create_retarget_pose('FoA_MannyAligned', SOT.TARGET)
r.set_current_retarget_pose('FoA_MannyAligned', SOT.TARGET)
r.auto_align_all_bones(SOT.TARGET)
fix_fingers(r)
E.save_loaded_asset(rtg, False)
print('Teen retarget built:', len(c.get_retarget_chains()), 'chains;', names)
