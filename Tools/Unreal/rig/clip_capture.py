"""Audit step B: capture the Teen (body + head + wake garments, leader-posed) and the Manny playing the same clip,
side by side, at a few moments of each clip retargeted by clip_retarget.py. Transient TMP_rig_* actors far above the
level, show-only capture, everything destroyed at the end. Frames land in <FOA_OUT> about 30-60 s later (taken on
later ticks, 0.4 s per shot), then done.txt.
  $env:FOA_AREAS='Characters'; $env:FOA_ACTORS_NEW='TMP_rig_'; python Tools/Unreal/ue_remote.py Tools/Unreal/rig/clip_capture.py FOA_OUT=P:/FoA/Saved/RigShots/audit/clips_before [FOA_CLIPS=a,b] [FOA_TIMES=0.2,0.5,0.8]"""
import json
import os
import time
from pathlib import Path

import unreal

OUT = Path(os.environ.get("FOA_OUT", "P:/FoA/Saved/RigShots/audit/clips_before"))
OUT.mkdir(parents=True, exist_ok=True)
(OUT / "done.txt").unlink(missing_ok=True)
CLIPS = json.load(open("P:/FoA/Saved/RigShots/audit/clip_retarget.json"))
WANT = [c for c in os.environ.get("FOA_CLIPS", ",".join(CLIPS)).split(",") if c in CLIPS]
TIMES = [float(x) for x in os.environ.get("FOA_TIMES", "0.2,0.5,0.8").split(",")]
VIEWS = os.environ.get("FOA_VIEWS", "full,fp,hand_r,hand_l").split(",")
M = "/Game/FoA/Characters/Teen/Mesh/"
E = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
w = E.get_editor_world()
assert not E.get_game_world(), "PIE is running: the user is playing"
gs = unreal.get_default_object(unreal.GameplayStatics)
made = []
for a in unreal.GameplayStatics.get_all_actors_of_class(w, unreal.Actor):
    if a.get_actor_label().startswith("TMP_rig_"):
        a.destroy_actor()


def spawn(cls, x=0.0):
    tr = unreal.Transform(location=unreal.Vector(x, 0, 3000))
    a = gs.call_method("BeginDeferredActorSpawnFromClass", (w, cls.static_class(), tr, unreal.SpawnActorCollisionHandlingMethod.ALWAYS_SPAWN,
                                                            None, unreal.SpawnActorScaleMethod.MULTIPLY_WITH_ROOT))
    a = gs.call_method("FinishSpawningActor", (a, tr, unreal.SpawnActorScaleMethod.MULTIPLY_WITH_ROOT))
    a.set_actor_label("TMP_rig_" + str(len(made)))
    made.append(a)
    return a


teen = spawn(unreal.SkeletalMeshActor, 0.0)
tc = teen.skeletal_mesh_component
tc.set_skeletal_mesh_asset(unreal.load_asset(M + "SK_Teen_Body"))
followers = []  # garments and head ride the body pose (as BP_FoAPlayer's leader-pose followers do)
for piece in ("SK_Teen_Head", "SK_Teen_Polo", "SK_Teen_Pants", "SK_Teen_Socks"):
    fa = spawn(unreal.SkeletalMeshActor, 0.0)
    c = fa.skeletal_mesh_component
    c.set_skeletal_mesh_asset(unreal.load_asset(M + piece))
    c.set_leader_pose_component(tc)
    followers.append(fa)
manny = spawn(unreal.SkeletalMeshActor, 400.0)
mc = manny.skeletal_mesh_component
mc.set_skeletal_mesh_asset(unreal.load_asset("/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple"))
for c in (tc, mc):
    c.set_animation_mode(unreal.AnimationMode.ANIMATION_SINGLE_NODE)
    c.set_update_animation_in_editor(True)
cap = spawn(unreal.SceneCapture2D, 0.0)
cc = cap.capture_component2d
cc.texture_target = unreal.RenderingLibrary.create_render_target2d(w, 900, 900, unreal.TextureRenderTargetFormat.RTF_RGBA8_SRGB)
cc.capture_source = unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR
cc.capture_every_frame = True
cc.always_persist_rendering_state = True
cc.override_custom_near_clipping_plane = True
cc.custom_near_clipping_plane = 9.0  # the first-person eye sits inside the head mesh
cc.primitive_render_mode = unreal.SceneCapturePrimitiveRenderMode.PRM_USE_SHOW_ONLY_LIST
pp = cc.post_process_settings
pp.override_auto_exposure_method = True
pp.auto_exposure_method = unreal.AutoExposureMethod.AEM_MANUAL
pp.override_auto_exposure_apply_physical_camera_exposure = True
pp.auto_exposure_apply_physical_camera_exposure = False
pp.override_auto_exposure_bias = True
pp.auto_exposure_bias = -3.5
cc.post_process_settings = pp
lights = []
for i in range(2):
    light = spawn(unreal.PointLight)
    lc = light.point_light_component
    for k, v in (("intensity_units", unreal.LightUnits.CANDELAS), ("intensity", 60 if i == 0 else 25),
                 ("attenuation_radius", 600), ("source_radius", 20)):
        lc.set_editor_property(k, v)
    lights.append(light)
shots = [(k, f, v, who) for k in WANT for f in TIMES for v in VIEWS for who in ("teen", "manny")]
S = {"i": 0, "stage": 0, "ready": time.monotonic() + 0.5, "h": None, "error": None, "anim": None, "ticks": 0}


def finish():
    unreal.unregister_slate_post_tick_callback(S["h"])
    for a in reversed(made):
        a.destroy_actor()
    (OUT / "done.txt").write_text(S["error"] or "complete %d shots" % S["i"])


def frame(comp, view):
    """Camera eye/target for a view, from the posed bones."""
    V = unreal.Vector
    if view == "full":
        tgt = comp.get_socket_location("spine_01")
        fwd = comp.get_socket_location("ball_r") - comp.get_socket_location("foot_r")
        fwd.z = 0
        fwd = fwd.normal()
        side = V(fwd.y, -fwd.x, 0)
        return tgt + fwd * 260 + side * 140 + V(0, 0, 25), tgt, 30
    if view == "fp":  # roughly the player's own first-person view of his hands
        head = comp.get_socket_location("head")
        hand = (comp.get_socket_location("hand_r") + comp.get_socket_location("hand_l")) * 0.5
        return head + (hand - head).normal() * 8 + V(0, 0, 6), hand, 75
    s = view[-1]
    tgt = (comp.get_socket_location("middle_01_" + s) + comp.get_socket_location("hand_" + s)) * 0.5
    if view.startswith("side"):  # along the knuckle line, from the little-finger side: shows the curl profile
        k = comp.get_socket_location("pinky_01_" + s) - comp.get_socket_location("index_01_" + s)
        return tgt + k.normal() * 34 + V(0, 0, 6), tgt, 40
    away = tgt - comp.get_socket_location("spine_03")
    return tgt + (away.normal() + V(0, 0, 0.35)).normal() * 38, tgt, 40


def tick(_dt):
    S["ticks"] += 1
    if time.monotonic() < S["ready"] or S["ticks"] < 4:  # a busy editor renders slowly: wait time AND frames
        return
    S["ticks"] = 0
    if E.get_game_world():  # PIE stops the editor world rendering: captures would be stale, so wait it out
        S["stage"], S["ready"] = 0, time.monotonic() + 1.0
        return
    try:
        key, f, view, who = shots[S["i"]]
        comp, actor = (tc, teen) if who == "teen" else (mc, manny)
        if S["stage"] == 0:
            anim = unreal.load_asset(CLIPS[key]["target" if who == "teen" else "source"].split(".")[0])
            if S["anim"] != (who, key):
                comp.set_animation(anim)
                S["anim"] = (who, key)
            comp.set_position(f * anim.get_play_length(), False)
            cc.clear_show_only_components()
            for a in [actor] + (followers if who == "teen" else []):
                cc.show_only_actor_components(a)
            S["stage"], S["ready"] = 1, time.monotonic() + 0.4
        elif S["stage"] == 1:
            eye, tgt, fov = frame(comp, view)
            cc.fov_angle = fov
            cap.set_actor_location_and_rotation(eye, unreal.MathLibrary.find_look_at_rotation(eye, tgt), False, True)
            lights[0].set_actor_location(eye + unreal.Vector(0, 0, 80), False, True)
            lights[1].set_actor_location(tgt + (tgt - eye) * 0.6 + unreal.Vector(0, 0, 120), False, True)
            S["stage"], S["ready"] = 2, time.monotonic() + 0.5
        else:
            unreal.RenderingLibrary.export_render_target(w, cc.texture_target, str(OUT), f"{key}_{int(f * 100):02d}_{view}_{who}.png")
            S["i"] += 1
            if S["i"] == len(shots):
                return finish()
            S["stage"], S["ready"] = 0, time.monotonic() + 0.05
    except Exception as ex:
        S["error"] = repr(ex)
        finish()


S["h"] = unreal.register_slate_post_tick_callback(tick)
print("CLIP_CAPTURE queued", len(shots), "shots ->", OUT)
