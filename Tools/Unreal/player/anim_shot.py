"""Anim lane editor-world shots of BP_FoAPlayer (no PIE): spawns TMP_anim_Player and TMP_anim_Cap (SceneCapture2D),
waits FOA_WAIT s of editor ticks (grooms bind, textures stream), writes head / body PNGs to Saved/AnimShots/<FOA_TAG>_*.png,
then destroys both. Nothing is saved.
  python Tools/Unreal/ue_remote.py Tools/Unreal/player/anim_shot.py FOA_ACTORS_NEW=TMP_anim_ [FOA_TAG=groom] [FOA_WAIT=6]"""
import math
import os
import time

import unreal

OUT = "P:/FoA/Saved/AnimShots"
TAG = os.environ.get("FOA_TAG", "shot")
WAIT = float(os.environ.get("FOA_WAIT", "6"))
BASE = unreal.Vector(-120.0, 120.0, -3000.0)  # 30 m under the floor: out of every shot (cine renders the level)
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)


def sweep():
    for a in EAS.get_all_level_actors():
        if a.get_actor_label().startswith("TMP_anim_"):
            EAS.destroy_actor(a)


sweep()
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
cls = unreal.EditorAssetLibrary.load_blueprint_class(os.environ.get("FOA_BP", "/Game/FoA/Characters/Player/BP_FoAPlayer"))
pawn = EAS.spawn_actor_from_class(cls, BASE + unreal.Vector(0, 0, float(os.environ.get("FOA_Z", "90"))), unreal.Rotator(0, 0, 0))
pawn.set_actor_label("TMP_anim_Player")
cap = EAS.spawn_actor_from_class(unreal.SceneCapture2D, BASE, unreal.Rotator())
cap.set_actor_label("TMP_anim_Cap")
comp = cap.capture_component2d
rt = unreal.RenderingLibrary.create_render_target2d(world, 960, 960, unreal.TextureRenderTargetFormat.RTF_RGBA8)
comp.set_editor_property("texture_target", rt)
comp.set_editor_property("capture_source", unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
comp.set_editor_property("capture_every_frame", False)
comp.set_editor_property("always_persist_rendering_state", True)
pp = comp.get_editor_property("post_process_settings")
pp.set_editor_property("override_auto_exposure_method", True)
pp.set_editor_property("auto_exposure_method", unreal.AutoExposureMethod.AEM_MANUAL)
pp.set_editor_property("override_auto_exposure_apply_physical_camera_exposure", True)
pp.set_editor_property("auto_exposure_apply_physical_camera_exposure", False)
pp.set_editor_property("override_auto_exposure_bias", True)
pp.set_editor_property("auto_exposure_bias", float(os.environ.get("FOA_EXP_BIAS", "2")))
comp.set_editor_property("post_process_settings", pp)
lt = EAS.spawn_actor_from_class(unreal.PointLight, BASE + unreal.Vector(160, 60, 190), unreal.Rotator())
lt.set_actor_label("TMP_anim_Light")  # soft review key, destroyed with the rest
lc = lt.point_light_component
lc.set_editor_property("intensity_units", unreal.LightUnits.CANDELAS)
lc.set_editor_property("intensity", 40.0)
lc.set_editor_property("attenuation_radius", 600.0)
lc.set_editor_property("source_radius", 25.0)
st = {"t0": time.time(), "h": None, "busy": False}


def shoot(name, target, yaw_deg, dist, fov):
    a = math.radians(yaw_deg)  # yaw 0 = in front of him (the pawn faces +X)
    frm = target + unreal.Vector(math.cos(a) * dist, math.sin(a) * dist, 8.0)
    cap.set_actor_location_and_rotation(frm, unreal.MathLibrary.find_look_at_rotation(frm, target), False, True)
    comp.set_editor_property("fov_angle", fov)
    for _ in range(3):
        comp.capture_scene()
    unreal.RenderingLibrary.export_render_target(world, rt, OUT, f"{TAG}_{name}.png")


def tick(_dt):
    if st["busy"] or time.time() - st["t0"] < WAIT:
        return
    st["busy"] = True
    unreal.unregister_slate_post_tick_callback(st["h"])
    try:
        head = BASE + unreal.Vector(0, 0, 165)
        shoot("head_near", head, 30, 80, 35)
        shoot("head_far", head, 30, 260, 35)
        shoot("body", BASE + unreal.Vector(0, 0, 95), 35, 280, 45)
        hair = [c for c in pawn.get_components_by_class(unreal.GroomComponent)]
        print("ANIM_SHOT grooms", [(c.get_name(), c.is_visible(), c.get_editor_property("binding_asset") is not None) for c in hair])
    finally:
        sweep()
        print("ANIM_SHOT done", TAG)


st["h"] = unreal.register_slate_post_tick_callback(tick)
print("ANIM_SHOT scheduled", TAG)
