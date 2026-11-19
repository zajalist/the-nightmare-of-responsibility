"""Anim lane: bakes AS_FoA_Grip_Tool_R, a right-hand power grip around a ~2.8 cm tool handle, on the Mannequin skeleton.
  FOA_AREAS=Characters python Tools/Unreal/ue_remote.py Tools/Unreal/player/bake_tool_grip.py
One held frame. Every bone keeps its reference local pose except the right fingers and thumb, which flex about their own
hinge axis (local Z on the UE5 Mannequin: each finger chain shares one Z, and a negative angle curls toward the palm).
ABP_FoAPlayer layers it onto the finger branches with GripWeight; the runtime retarget carries it to the visible body."""
import unreal

P = "/Game/FoA/Characters/Player"
SRC = P + "/Anims/UAL/UAL_Idle_Loop"
OUT = P + "/Anims/Hands/AS_FoA_Grip_Tool_R"
EAL, AP = unreal.EditorAssetLibrary, unreal.AnimPoseExtensions
LOCAL = unreal.AnimPoseSpaces.LOCAL
# degrees of flexion toward the palm: a power grip, tighter toward the little finger, the thumb wrapped over
CURL = {'index_01_r': 52, 'index_02_r': 68, 'index_03_r': 32,
        'middle_01_r': 64, 'middle_02_r': 80, 'middle_03_r': 38,
        'ring_01_r': 70, 'ring_02_r': 84, 'ring_03_r': 38,
        'pinky_01_r': 76, 'pinky_02_r': 84, 'pinky_03_r': 36,
        'ring_metacarpal_r': 4, 'pinky_metacarpal_r': 9,
        'thumb_01_r': 18, 'thumb_02_r': 26, 'thumb_03_r': 30}


def controller(seq):
    for get in (lambda s: s.get_editor_property("controller"), lambda s: s.controller, lambda s: s.get_controller()):
        try:
            c = get(seq)
            if c:
                return c
        except Exception:
            pass
    raise RuntimeError("no AnimDataController on " + seq.get_name())


def flex(q, deg):
    curl = unreal.MathLibrary.rotator_from_axis_and_angle(unreal.Vector(0, 0, 1), -deg).quaternion()
    return unreal.MathLibrary.multiply_quat_quat(q, curl) if hasattr(unreal.MathLibrary, "multiply_quat_quat") else q * curl


if not EAL.does_asset_exist(OUT):
    assert EAL.duplicate_asset(SRC, OUT), "duplicate"
seq = unreal.load_asset(OUT)
unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(seq)
ref = AP.get_reference_pose(seq.get_editor_property("skeleton"))
bones = [str(b) for b in AP.get_bone_names(ref)]
assert all(b in bones for b in CURL), [b for b in CURL if b not in bones]
c = controller(seq)
fr = unreal.FrameRate()
fr.set_editor_property("numerator", 30)
fr.set_editor_property("denominator", 1)
c.set_frame_rate(fr, True)
fn = unreal.FrameNumber()
fn.set_editor_property("value", 1)
c.set_number_of_frames(fn, True)
for b in bones:
    t = AP.get_bone_pose(ref, b, LOCAL)
    q = flex(t.rotation, CURL[b]) if b in CURL else t.rotation
    c.set_bone_track_keys(b, [t.translation] * 2, [q] * 2, [t.scale3d] * 2, True)
for tr in list(unreal.AnimationLibrary.get_animation_notify_track_names(seq)):
    unreal.AnimationLibrary.remove_animation_notify_events_by_track(seq, tr)
seq.set_editor_property("enable_root_motion", False)
EAL.save_loaded_asset(seq, False)
print("baked", OUT, "bones", len(bones), "curled", len(CURL))
