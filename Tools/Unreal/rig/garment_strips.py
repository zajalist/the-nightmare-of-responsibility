"""In-engine strips of the battle-garment clips: each garment (shipped mesh and MI) plays each take on a transient
TMP_rig_garment actor far above the level, six frames per take, shot by a transient SceneCapture2D from a battle-camera
angle (front, slightly above, the garment facing the camera as BP_Encounter turns it). Everything is destroyed at the
end; nothing is saved but PNGs under FOA_OUT.
  $env:FOA_AREAS='Characters'; $env:FOA_ACTORS_NEW='TMP_rig_'; python Tools/Unreal/ue_remote.py Tools/Unreal/rig/garment_strips.py"""
import os
import time
from pathlib import Path

import unreal

OUT = Path(os.environ.get("FOA_OUT", "P:/FoA/Saved/RigShots/garments/engine"))
OUT.mkdir(parents=True, exist_ok=True)
(OUT / "done.txt").unlink(missing_ok=True)
GAR = "/Game/FoA/Characters/Garments/"
SPEC = {"Shirt": ("Lash", 1.6, -12), "Trousers": ("Kick", 1.0, -10), "Sock": ("Hop", 1.0, -6), "Tie": ("CoilStrike", 1.4, 10)}
TAKES = ["Idle", "Telegraph", "ATTACK", "HitReact", "Stun", "Defeat"]
E = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
w = E.get_editor_world()
assert not E.get_game_world(), "PIE is running"
gs = unreal.get_default_object(unreal.GameplayStatics)
made = []
for a in unreal.GameplayStatics.get_all_actors_of_class(w, unreal.Actor):
    if a.get_actor_label().startswith("TMP_rig_"):
        a.destroy_actor()
O = unreal.Vector(0, 0, 4000)


def spawn(cls, label, loc=O, rot=unreal.Rotator()):
    tr = unreal.Transform(location=loc, rotation=rot)
    a = gs.call_method("BeginDeferredActorSpawnFromClass", (w, cls.static_class(), tr, unreal.SpawnActorCollisionHandlingMethod.ALWAYS_SPAWN,
                                                            None, unreal.SpawnActorScaleMethod.MULTIPLY_WITH_ROOT))
    a = gs.call_method("FinishSpawningActor", (a, tr, unreal.SpawnActorScaleMethod.MULTIPLY_WITH_ROOT))
    a.set_actor_label("TMP_rig_" + label)
    made.append(a)
    return a


g_act = spawn(unreal.SkeletalMeshActor, "garment")
gc = g_act.skeletal_mesh_component
gc.set_animation_mode(unreal.AnimationMode.ANIMATION_SINGLE_NODE)
gc.set_update_animation_in_editor(True)
cap = spawn(unreal.SceneCapture2D, "cap")
cc = cap.capture_component2d
cc.texture_target = unreal.RenderingLibrary.create_render_target2d(w, 640, 640, unreal.TextureRenderTargetFormat.RTF_RGBA8_SRGB)
cc.capture_source = unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR
cc.capture_every_frame = True
cc.always_persist_rendering_state = True
cc.primitive_render_mode = unreal.SceneCapturePrimitiveRenderMode.PRM_USE_SHOW_ONLY_LIST
cc.clear_show_only_components()
cc.show_only_actor_components(g_act)
pp = cc.post_process_settings
pp.override_auto_exposure_method = True
pp.auto_exposure_method = unreal.AutoExposureMethod.AEM_MANUAL
pp.override_auto_exposure_apply_physical_camera_exposure = True
pp.auto_exposure_apply_physical_camera_exposure = False
pp.override_auto_exposure_bias = True
pp.auto_exposure_bias = -1.5
cc.post_process_settings = pp
cc.fov_angle = 35
lights = []
for i, (dx, dy, dz, inten) in enumerate(((-250, -120, 220, 220.0), (180, -60, 80, 70.0))):
    lt = spawn(unreal.PointLight, f"light{i}", O + unreal.Vector(dx, dy, dz))
    lc = lt.point_light_component
    lc.set_mobility(unreal.ComponentMobility.MOVABLE)
    for k, v in (("intensity_units", unreal.LightUnits.CANDELAS), ("intensity", inten), ("attenuation_radius", 900), ("source_radius", 30)):
        lc.set_editor_property(k, v)
ONLY = [x for x in os.environ.get("FOA_ONLY", "").split(",") if x]
shots = [(g, t, k) for g in SPEC if not ONLY or g in ONLY for t in TAKES for k in range(6)]
S = {"i": 0, "stage": 0, "ready": time.monotonic() + 0.5, "ticks": 0, "h": None, "error": None, "cur": None}


def finish():
    unreal.unregister_slate_post_tick_callback(S["h"])
    for a in reversed(made):
        a.destroy_actor()
    (OUT / "done.txt").write_text(S["error"] or "complete %d shots" % S["i"])


def tick(_dt):
    S["ticks"] += 1
    if time.monotonic() < S["ready"] or S["ticks"] < 3:
        return
    S["ticks"] = 0
    if E.get_game_world():
        S["stage"], S["ready"] = 0, time.monotonic() + 1.0
        return
    try:
        g, take, k = shots[S["i"]]
        attack, scale, z = SPEC[g]
        name = attack if take == "ATTACK" else take
        if S["stage"] == 0:
            if S["cur"] != g:
                gc.set_skeletal_mesh_asset(unreal.load_asset(GAR + f"SK_Garment_{g}"))
                g_act.set_actor_scale3d(unreal.Vector(scale, scale, scale))
                g_act.set_actor_rotation(unreal.Rotator(roll=0, pitch=0, yaw=90), False)  # BP_Encounter's yaw 90: faces the camera (-X)
                S["cur"] = g
            anim = unreal.load_asset(GAR + f"SK_Garment_{g}Armature_{name}")
            gc.set_animation(anim)
            gc.set_position(anim.get_play_length() * k / 5.0, False)
            h = 110 * scale
            tgt = O + unreal.Vector(0, 0, z + h * 0.55)
            eye = tgt + unreal.Vector(-430 * scale, -60, 70)
            cap.set_actor_location_and_rotation(eye, unreal.MathLibrary.find_look_at_rotation(eye, tgt), False, True)
            S["stage"], S["ready"] = 1, time.monotonic() + 0.45
        else:
            unreal.RenderingLibrary.export_render_target(w, cc.texture_target, str(OUT), f"{g}_{name}_{k}.png")
            S["i"] += 1
            if S["i"] == len(shots):
                return finish()
            S["stage"], S["ready"] = 0, time.monotonic() + 0.05
    except Exception as ex:
        S["error"] = repr(ex)
        finish()


S["h"] = unreal.register_slate_post_tick_callback(tick)
print("GARMENT_STRIPS queued", len(shots), "->", OUT)
