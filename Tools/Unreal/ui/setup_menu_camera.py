"""BP_MenuCamera (CineCameraActor) + its placed instance in L_Tutorial_Bedroom (Outliner folder UI). Run via ue_remote.py.
Pose A is where the looping drift starts and ends (pose B lives only in LS_MainMenu_Camera).
Env: FOA_POSE_A / FOA_POSE_B = "x,y,z,pitch,yaw" to re-pose without editing the script.
APPLIED 2026-11-05. Do not rerun the CDO block as is: since 20:42 Python never writes a CDO and never compiles. Set the
lens through Hayba blueprint_set_defaults or object_set_property and compile with Hayba blueprint_compile instead."""
import os
import unreal

BEL = unreal.BlueprintEditorLibrary
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
PATH = '/Game/FoA/UI/Framework/BP_MenuCamera'
bp = unreal.load_asset(PATH + '.BP_MenuCamera')
if not bp:
    fac = unreal.BlueprintFactory()
    fac.set_editor_property('parent_class', unreal.CineCameraActor)
    bp = unreal.AssetToolsHelpers.get_asset_tools().create_asset('BP_MenuCamera', '/Game/FoA/UI/Framework', unreal.Blueprint, fac)
assert bp, 'BP_MenuCamera not created'
cdo = unreal.get_default_object(bp.generated_class())
assert cdo, 'no CDO'
cine = cdo.get_cine_camera_component()
cine.set_editor_property('current_focal_length', 26.0)
cine.set_editor_property('current_aperture', 2.0)
fs = cine.get_editor_property('focus_settings')
fs.set_editor_property('focus_method', unreal.CameraFocusMethod.MANUAL)
fs.set_editor_property('manual_focus_distance', 650.0)
cine.set_editor_property('focus_settings', fs)
unreal.EditorAssetLibrary.save_asset(PATH, only_if_is_dirty=False)


def pose(env, default):
    v = [float(x) for x in os.environ.get(env, default).split(',')]
    return unreal.Vector(*v[:3]), unreal.Rotator(roll=0.0, pitch=v[3], yaw=v[4])


A = pose('FOA_POSE_A', '-230,170,150,-6,-50')
B = pose('FOA_POSE_B', '-150,90,140,-7,-51')
actors = {a.get_actor_label(): a for a in EAS.get_all_level_actors()}
cam = actors.get('BP_MenuCamera') or EAS.spawn_actor_from_object(bp, A[0], A[1])
cam.set_actor_label('BP_MenuCamera'); cam.set_folder_path('UI')
cam.set_actor_location_and_rotation(A[0], A[1], False, False)
print('placed', cam.get_actor_label(), cam.get_actor_location())
