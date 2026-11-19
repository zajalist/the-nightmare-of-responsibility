"""Anim lane: AS_FoA_Add_Tired, a one-frame local-space additive (base: the reference pose) that makes any clip his.
  FOA_AREAS=Characters python Tools/Unreal/ue_remote.py Tools/Unreal/player/bake_tired.py
Spine flexes forward a little (spine_03..05), the neck and head extend back so the eyes stay level, the shoulders roll forward. Every rotation is
about the body's own axes in the reference pose (lateral from the clavicles, up = component Z), and each sign is checked
numerically: flexion must move the head forward of the pelvis (+Y is his front), the roll must bring the upper arm forward.
ABP_FoAPlayer applies it over locomotion with TiredWeight (animation_direction.md section 2)."""
import unreal

P = "/Game/FoA/Characters/Player"
SRC = P + "/Anims/UAL/UAL_Idle_Loop"
OUT = P + "/Anims/Hands/AS_FoA_Add_Tired"
# v2 (2026-11-09, face lane: "head bowed in every still"): the upper back still rounds 8 deg, but the neck and head
# extend against it, so the head carries forward with the eyes nearly level (net 2 deg down) instead of hanging.
FLEX = {"spine_03": 3.0, "spine_04": 3.0, "spine_05": 2.0, "neck_01": -2.0, "head": -4.0}  # degrees forward
ROLL = {"clavicle_l": 5.0, "clavicle_r": 5.0}  # shoulders forward
EAL, AP = unreal.EditorAssetLibrary, unreal.AnimPoseExtensions
LOCAL, CS = unreal.AnimPoseSpaces.LOCAL, unreal.AnimPoseSpaces.WORLD


def controller(seq):
    for get in (lambda s: s.get_editor_property("controller"), lambda s: s.controller, lambda s: s.get_controller()):
        try:
            c = get(seq)
            if c:
                return c
        except Exception:
            pass
    raise RuntimeError("no AnimDataController on " + seq.get_name())


def aa(axis, deg):
    return unreal.MathLibrary.rotator_from_axis_and_angle(axis.normal(), deg).quaternion()


def mul(a, b):
    return unreal.MathLibrary.multiply_quat_quat(a, b) if hasattr(unreal.MathLibrary, "multiply_quat_quat") else a * b


if not EAL.does_asset_exist(OUT):
    assert EAL.duplicate_asset(SRC, OUT), "duplicate"
seq = unreal.load_asset(OUT)
unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(seq)
ref = AP.get_reference_pose(seq.get_editor_property("skeleton"))
bones = [str(b) for b in AP.get_bone_names(ref)]
pos = {b: AP.get_bone_pose(ref, b, CS).translation for b in bones}
lat = pos["clavicle_l"] - pos["clavicle_r"]
up = unreal.Vector(0, 0, 1)
# sign checks against the reference pose geometry
head = pos["head"] - pos["spine_03"]
flex_sign = 1.0 if (aa(lat, 10.0).rotate_vector(head)).y > head.y else -1.0
signs = {}
for c, arm in (("clavicle_l", "upperarm_l"), ("clavicle_r", "upperarm_r")):
    v = pos[arm] - pos[c]
    signs[c] = 1.0 if aa(up, 10.0).rotate_vector(v).y > v.y else -1.0
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
    q = t.rotation
    cs = AP.get_bone_pose(ref, b, CS).rotation
    if b in FLEX:
        q = mul(q, aa(cs.unrotate_vector(lat), flex_sign * FLEX[b]))
    if b in ROLL:
        q = mul(q, aa(cs.unrotate_vector(up), signs[b] * ROLL[b]))
    c.set_bone_track_keys(b, [t.translation] * 2, [q] * 2, [t.scale3d] * 2, True)
for tr in list(unreal.AnimationLibrary.get_animation_notify_track_names(seq)):
    unreal.AnimationLibrary.remove_animation_notify_events_by_track(seq, tr)
seq.set_editor_property("enable_root_motion", False)
seq.set_editor_property("additive_anim_type", unreal.AdditiveAnimationType.AAT_LOCAL_SPACE_BASE)
seq.set_editor_property("ref_pose_type", unreal.AdditiveBasePoseType.ABPT_REF_POSE)
EAL.save_loaded_asset(seq, False)
print("baked", OUT, "flex sign", flex_sign, "roll signs", signs)
