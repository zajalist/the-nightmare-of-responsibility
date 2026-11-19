"""Anim lane clip preview (editor world, nothing saved): poses the Mannequin through each clip in FOA_CLIPS
(asset paths, comma list) and writes FOA_FRAMES frames per clip to Saved/AnimShots/clips/<clip>_<i>.png, then
record side: python Tools/Unreal/player/clip_sheet.py --sheet builds <clip>.jpg contact sheets and .gif loops.
  python Tools/Unreal/ue_remote.py Tools/Unreal/player/clip_sheet.py FOA_ACTORS_NEW=TMP_anim_ FOA_CLIPS=/Game/... [FOA_FRAMES=8]
Spawns 30 m under the floor and only in minutes :x4-:x9 (cine's MRQ windows are :x0-:x3)."""
import os
import sys
import time

if "--sheet" in sys.argv:  # offline: contact sheets and GIFs from the frames
    import glob
    from PIL import Image
    d = "P:/FoA/Saved/AnimShots/clips"
    names = sorted({os.path.basename(f).rsplit("_", 1)[0] for f in glob.glob(f"{d}/*_*.png")})
    for n in names:
        fs = sorted(glob.glob(f"{d}/{n}_*.png"), key=lambda f: int(f.rsplit("_", 1)[1][:-4]))
        ims = [Image.open(f).convert("RGB").resize((320, 480)) for f in fs]
        sheet = Image.new("RGB", (320 * len(ims), 480))
        for i, im in enumerate(ims):
            sheet.paste(im, (i * 320, 0))
        sheet.save(f"{d}/{n}.jpg", quality=85)
        ims[0].save(f"{d}/{n}.gif", save_all=True, append_images=ims[1:], duration=120, loop=0)
        print(n, len(ims), "frames")
    sys.exit()

import unreal  # noqa: E402

assert time.localtime().tm_min % 10 > 3, "minutes :x0-:x3 are cine's MRQ windows (PIE copies the editor world): wait"
OUT = "P:/FoA/Saved/AnimShots/clips"
os.makedirs(OUT, exist_ok=True)
CLIPS = [c for c in os.environ["FOA_CLIPS"].split(",") if c]
FRAMES = int(os.environ.get("FOA_FRAMES", "8"))
BASE = unreal.Vector(0.0, 0.0, -3000.0)
BODY = "/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple"  # clips as authored (the MetaHuman retargets from this)
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)


def sweep():
    for a in EAS.get_all_level_actors():
        if a.get_actor_label().startswith("TMP_anim_"):
            EAS.destroy_actor(a)


sweep()
try:
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    actor = EAS.spawn_actor_from_class(unreal.SkeletalMeshActor, BASE, unreal.Rotator(0, 0, 0))
    actor.set_actor_label("TMP_anim_Clip")
    sk = actor.skeletal_mesh_component
    sk.set_skeletal_mesh_asset(unreal.load_asset(BODY))
    sk.set_update_animation_in_editor(True)
    cap = EAS.spawn_actor_from_class(unreal.SceneCapture2D, BASE, unreal.Rotator())
    cap.set_actor_label("TMP_anim_Cap")
    lt = EAS.spawn_actor_from_class(unreal.PointLight, BASE + unreal.Vector(200, 150, 220), unreal.Rotator())
    lt.set_actor_label("TMP_anim_Light")
    lt.point_light_component.set_editor_property("intensity_units", unreal.LightUnits.CANDELAS)
    lt.point_light_component.set_editor_property("intensity", 60.0)
    lt.point_light_component.set_editor_property("attenuation_radius", 900.0)
    comp = cap.capture_component2d
    rt = unreal.RenderingLibrary.create_render_target2d(world, 320, 480, unreal.TextureRenderTargetFormat.RTF_RGBA8)
    for k, v in (("texture_target", rt), ("capture_source", unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR),
                 ("capture_every_frame", False), ("always_persist_rendering_state", True), ("fov_angle", 40.0)):
        comp.set_editor_property(k, v)
    pp = comp.get_editor_property("post_process_settings")
    for k, v in (("override_auto_exposure_method", True), ("auto_exposure_method", unreal.AutoExposureMethod.AEM_MANUAL),
                 ("override_auto_exposure_apply_physical_camera_exposure", True),
                 ("auto_exposure_apply_physical_camera_exposure", False), ("override_auto_exposure_bias", True),
                 ("auto_exposure_bias", 2.0)):
        pp.set_editor_property(k, v)
    comp.set_editor_property("post_process_settings", pp)
    # 3/4 side view: the MetaHuman faces +Y in mesh space; the actor is unrotated
    frm = BASE + unreal.Vector(260.0, 180.0, 110.0)
    cap.set_actor_location_and_rotation(frm, unreal.MathLibrary.find_look_at_rotation(frm, BASE + unreal.Vector(0, 0, 90)), False, True)
except Exception:
    sweep()
    raise
jobs = [(c, i) for c in CLIPS for i in range(FRAMES)]
st = {"h": None, "k": 0, "wait": 0, "clip": None}


def tick(_dt):
    try:
        if st["k"] >= len(jobs):
            raise StopIteration
        clip, i = jobs[st["k"]]
        seq = unreal.load_asset(clip)
        if st["wait"] == 0:  # pose this frame, then let two editor ticks refresh the bones
            if st["clip"] != clip:
                sk.play_animation(seq, False)
                st["clip"] = clip
            sk.set_position(seq.get_play_length() * i / FRAMES, False)
            st["wait"] = 3
            return
        st["wait"] -= 1
        if st["wait"] > 0:
            return
        comp.capture_scene()
        comp.capture_scene()
        unreal.RenderingLibrary.export_render_target(world, rt, OUT, f"{clip.split('/')[-1]}_{i}.png")
        st["k"] += 1
    except StopIteration:
        unreal.unregister_slate_post_tick_callback(st["h"])
        sweep()
        print("CLIP_SHEET done", len(jobs))
    except Exception as e:
        unreal.unregister_slate_post_tick_callback(st["h"])
        sweep()
        print("CLIP_SHEET error", repr(e))


st["h"] = unreal.register_slate_post_tick_callback(tick)
print("CLIP_SHEET scheduled", len(jobs))
