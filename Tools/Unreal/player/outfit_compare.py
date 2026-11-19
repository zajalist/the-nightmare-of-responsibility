"""Anim lane outfit check (editor world, 30 m under the floor, nothing saved): BP_FoAPlayer and BP_MHC_Protagonist side by
side, front and side shots of the legs and torso to Saved/AnimShots/oc_<n>.png; variants of our pawn on FOA_VAR.
  python Tools/Unreal/ue_remote.py Tools/Unreal/player/outfit_compare.py FOA_ACTORS_NEW=TMP_anim_"""
import math
import time

import unreal

assert time.localtime().tm_min % 10 > 3, "minutes :x0-:x3 are cine's MRQ windows: wait"
OUT = "P:/FoA/Saved/AnimShots"
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
BASE = unreal.Vector(0.0, 0.0, -3000.0)


def sweep():
    for a in EAS.get_all_level_actors():
        if a.get_actor_label().startswith("TMP_anim_"):
            EAS.destroy_actor(a)


sweep()
try:
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    ours = EAS.spawn_actor_from_class(unreal.EditorAssetLibrary.load_blueprint_class("/Game/FoA/Characters/Player/BP_FoAPlayer"),
                                      BASE + unreal.Vector(0, 0, 90), unreal.Rotator(0, 0, 0))
    ours.set_actor_label("TMP_anim_Ours")
    mh = EAS.spawn_actor_from_class(unreal.EditorAssetLibrary.load_blueprint_class(
        "/Game/FoA/Characters/Protagonist/Built/MHC_Protagonist/BP_MHC_Protagonist"), BASE + unreal.Vector(0, 120, 0),
        unreal.Rotator(0, 0, 90))  # the build faces +Y in actor space: turn it to face +X like the pawn
    mh.set_actor_label("TMP_anim_MH")
    lt = EAS.spawn_actor_from_class(unreal.PointLight, BASE + unreal.Vector(250, 60, 200), unreal.Rotator())
    lt.set_actor_label("TMP_anim_Light")
    lt.point_light_component.set_editor_property("intensity_units", unreal.LightUnits.CANDELAS)
    lt.point_light_component.set_editor_property("intensity", 40.0)
    lt.point_light_component.set_editor_property("attenuation_radius", 900.0)
    cap = EAS.spawn_actor_from_class(unreal.SceneCapture2D, BASE, unreal.Rotator())
    cap.set_actor_label("TMP_anim_Cap")
    comp = cap.capture_component2d
    rt = unreal.RenderingLibrary.create_render_target2d(world, 960, 960, unreal.TextureRenderTargetFormat.RTF_RGBA8)
    for k, v in (("texture_target", rt), ("capture_source", unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR),
                 ("capture_every_frame", False), ("always_persist_rendering_state", True), ("fov_angle", 45.0)):
        comp.set_editor_property(k, v)
    pp = comp.get_editor_property("post_process_settings")
    for k, v in (("override_auto_exposure_method", True), ("auto_exposure_method", unreal.AutoExposureMethod.AEM_MANUAL),
                 ("override_auto_exposure_apply_physical_camera_exposure", True),
                 ("auto_exposure_apply_physical_camera_exposure", False), ("override_auto_exposure_bias", True),
                 ("auto_exposure_bias", 1.5)):
        pp.set_editor_property(k, v)
    comp.set_editor_property("post_process_settings", pp)
except Exception:
    sweep()
    raise
st = {"t0": time.time(), "h": None, "busy": False}


def shoot(name, target, yaw, dist, z):
    a = math.radians(yaw)
    frm = target + unreal.Vector(math.cos(a) * dist, math.sin(a) * dist, z)
    cap.set_actor_location_and_rotation(frm, unreal.MathLibrary.find_look_at_rotation(frm, target), False, True)
    for _ in range(3):
        comp.capture_scene()
    unreal.RenderingLibrary.export_render_target(world, rt, OUT, f"oc_{name}.png")


def tick(_dt):
    if st["busy"] or time.time() - st["t0"] < 6:
        return
    st["busy"] = True
    unreal.unregister_slate_post_tick_callback(st["h"])
    try:
        mid = BASE + unreal.Vector(0, 60, 80)
        shoot("front", mid, 0, 330, 20)
        shoot("legs", BASE + unreal.Vector(0, 0, 50), 20, 150, 0)
        outfit = next(c for c in ours.get_components_by_class(unreal.SkeletalMeshComponent) if c.get_name() == "StartOutfit")
        body = next(c for c in ours.get_components_by_class(unreal.SkeletalMeshComponent) if c.get_name() == "Body")
        print("OC outfit visible", outfit.is_visible(), "lod", outfit.get_predicted_lod_level(), "leader",
              outfit.get_editor_property("leader_pose_component").get_name() if outfit.get_editor_property("leader_pose_component") else None,
              "body lod", body.get_predicted_lod_level())
    finally:
        sweep()
        print("OC done")


st["h"] = unreal.register_slate_post_tick_callback(tick)
print("OC scheduled")
