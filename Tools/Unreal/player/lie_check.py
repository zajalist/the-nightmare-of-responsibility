"""Anim lane, wake-up: does the Mannequin-to-MetaHuman retarget keep a supine pose clean (neck, shoulders)?
Spawns TMP_anim_Lie (BP_FoAPlayer) at cine's lying transform on the bed, plays FOA_CLIP on the hidden Mannequin, then
captures the same two cameras twice: the retargeted MetaHuman (as the game shows it) and the Mannequin's own pose (the
Mannequin made visible, the MetaHuman hidden). Writes Saved/AnimShots/lie_<cam>_<mh|manny>.png, destroys everything.
Editor world only, minutes :x4-:x9 (cine renders :x0-:x3).
  python Tools/Unreal/ue_remote.py Tools/Unreal/player/lie_check.py FOA_ACTORS_NEW=TMP_anim_ [FOA_CLIP=/Game/...]"""
import math
import os
import time

import unreal

assert time.localtime().tm_min % 10 > 3, "minutes :x0-:x3 are cine's MRQ windows: wait"
OUT = "P:/FoA/Saved/AnimShots"
CLIP = os.environ.get("FOA_CLIP", "/Game/FoA/Characters/Player/Anims/Wake/AS_FoA_Lie_Breathe")
LOC = unreal.Vector(218.09, -191.31, 140.44)
ROT = unreal.Rotator(roll=0.0, pitch=-12.79, yaw=-179.97)
HEAD = unreal.Vector(325.5, -191.0, 88.0)
CAMS = {"side": (unreal.Vector(270.0, -40.0, 135.0), unreal.Vector(275.0, -191.0, 80.0), 50.0),
        "pillow": (unreal.Vector(250.0, -150.0, 150.0), HEAD, 35.0)}
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)


def sweep():
    for a in EAS.get_all_level_actors():
        if a.get_actor_label().startswith("TMP_anim_"):
            EAS.destroy_actor(a)


sweep()
try:
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    pawn = EAS.spawn_actor_from_class(unreal.EditorAssetLibrary.load_blueprint_class("/Game/FoA/Characters/Player/BP_FoAPlayer"),
                                      LOC, ROT)
    pawn.set_actor_label("TMP_anim_Lie")
    pawn.set_actor_enable_collision(False)
    sk = {c.get_name(): c for c in pawn.get_components_by_class(unreal.SkeletalMeshComponent)}
    manny = sk["CharacterMesh0"]
    manny.set_animation_mode(unreal.AnimationMode.ANIMATION_SINGLE_NODE)
    manny.play_animation(unreal.load_asset(CLIP), True)
    for n in ("CharacterMesh0", "Body", "Face"):  # the editor world only animates components told to
        sk[n].set_update_animation_in_editor(True)
    manny.set_position(1.0, False)
    cap = EAS.spawn_actor_from_class(unreal.SceneCapture2D, LOC, unreal.Rotator())
    cap.set_actor_label("TMP_anim_Cap")
    comp = cap.capture_component2d
    rt = unreal.RenderingLibrary.create_render_target2d(world, 1280, 720, unreal.TextureRenderTargetFormat.RTF_RGBA8)
    for k, v in (("texture_target", rt), ("capture_source", unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR),
                 ("capture_every_frame", False), ("always_persist_rendering_state", True)):
        comp.set_editor_property(k, v)
    pp = comp.get_editor_property("post_process_settings")
    for k, v in (("override_auto_exposure_method", True), ("auto_exposure_method", unreal.AutoExposureMethod.AEM_MANUAL),
                 ("override_auto_exposure_apply_physical_camera_exposure", True),
                 ("auto_exposure_apply_physical_camera_exposure", False), ("override_auto_exposure_bias", True),
                 ("auto_exposure_bias", 2.5)):
        pp.set_editor_property(k, v)
    comp.set_editor_property("post_process_settings", pp)
except Exception:
    sweep()
    raise
st = {"t0": time.time(), "h": None, "busy": False}


def shoot(tag):
    for name, (frm, at, fov) in CAMS.items():
        cap.set_actor_location_and_rotation(frm, unreal.MathLibrary.find_look_at_rotation(frm, at), False, True)
        comp.set_editor_property("fov_angle", fov)
        for _ in range(3):
            comp.capture_scene()
        unreal.RenderingLibrary.export_render_target(world, rt, OUT, f"lie_{name}_{tag}.png")


def tick(_dt):
    if st["busy"] or time.time() - st["t0"] < 5:
        return
    st["busy"] = True
    unreal.unregister_slate_post_tick_callback(st["h"])
    try:
        shoot("mh")
        head = sk["Face"].get_socket_location("head")
        neck = sk["Body"].get_socket_location("neck_01")
        print("LIE head", head, "neck_01", neck, "manny head", manny.get_socket_location("head"))
        manny.set_visibility(True, False)
        for n, c in sk.items():
            if n != "CharacterMesh0":
                c.set_visibility(False, False)
        for g in pawn.get_components_by_class(unreal.GroomComponent):
            g.set_visibility(False, False)
        shoot("manny")
    finally:
        sweep()
        print("LIE done")


st["h"] = unreal.register_slate_post_tick_callback(tick)
print("LIE scheduled", CLIP)
