"""In-engine review shots of the protagonist in the bedroom light. Run inside the editor lock:

  python Tools/Unreal/ue_remote.py Tools/Unreal/mh_capture.py [FOA_ACTOR=/Game/...] [FOA_FRAMES=36]

Spawns TMP_character_Protagonist (an assembled MetaHuman Blueprint, or a SkeletalMesh) at PlayerStart_WakeUp on
the floor, plus TMP_character_Capture (SceneCapture2D, final colour with the level's post process), writes
face_front / face_tq / full_body / full_tq PNGs and FOA_FRAMES turntable frames to FOA_OUT, then destroys both
actors. The render target is transient (no asset). The level is not saved.
FOA_FWD_YAW rotates the assumed facing (MetaHuman meshes face +Y in actor space).
"""
import math
import os
import unreal

OUT = os.environ.get("FOA_OUT", "P:/FoA/Saved/CharacterShots/protagonist")
SRC = os.environ.get("FOA_ACTOR", "/Game/FoA/Characters/Protagonist/Built/BP_MHC_Protagonist")
FRAMES = int(os.environ.get("FOA_FRAMES", "0"))
FLOOR_Z = float(os.environ.get("FOA_FLOOR_Z", "0"))
FWD_YAW = float(os.environ.get("FOA_FWD_YAW", "90"))  # +Y
WAIT = float(os.environ.get("FOA_WAIT", "8"))  # seconds of editor ticks before shooting (grooms, streaming)
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)


def sweep(reason):
    """Destroy every TMP_character_ actor in the level, one by one (a failed destroy must not keep the rest)."""
    n = 0
    for a in EAS.get_all_level_actors():
        try:
            if a.get_actor_label().startswith("TMP_character_"):
                EAS.destroy_actor(a)
                n += 1
        except Exception as e:
            print("MH_CAPTURE sweep error", e)
    if n:
        print("MH_CAPTURE swept", n, "TMP actors", reason)


def look(cam, frm, to):
    cam.set_actor_location_and_rotation(frm, unreal.MathLibrary.find_look_at_rotation(frm, to), False, True)


def shoot(world, comp, rt, name, warm=3):
    for _ in range(warm):  # eye adaptation and streaming settle over a few captures
        comp.capture_scene()
    comp.capture_scene()
    unreal.RenderingLibrary.export_render_target(world, rt, OUT, name + ".png")


def run():
    os.makedirs(os.path.join(OUT, "tt"), exist_ok=True)
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    ps = next((a for a in EAS.get_all_level_actors() if a.get_actor_label() == "PlayerStart_WakeUp"), None)
    p = ps.get_actor_location() if ps else unreal.Vector(60, -80, 100)
    base = unreal.Vector(p.x, p.y, FLOOR_Z)
    asset = unreal.load_asset(SRC) if unreal.EditorAssetLibrary.does_asset_exist(SRC) else None
    if asset is None:  # the build names its Blueprint itself: take the one in Built/
        built = "/Game/FoA/Characters/Protagonist/Built"
        unreal.AssetRegistryHelpers.get_asset_registry().scan_paths_synchronous([built], True)
        bps = [a for a in unreal.EditorAssetLibrary.list_assets(built, recursive=True)
               if os.path.basename(a).startswith("BP_")]
        print("MH_CAPTURE built blueprints", bps)
        if not bps:
            raise RuntimeError(f"missing {SRC} and no BP_ in {built}")
        asset = unreal.load_asset(bps[0])
    sweep("left by an earlier run")
    made = []
    made_deferred = [False]
    done = os.path.join(OUT, "_done.txt")
    if os.path.exists(done):
        os.remove(done)
    try:
        if isinstance(asset, unreal.SkeletalMesh):
            actor = EAS.spawn_actor_from_class(unreal.SkeletalMeshActor, base, unreal.Rotator())
            actor.skeletal_mesh_component.set_skeletal_mesh_asset(asset)
        else:
            actor = EAS.spawn_actor_from_object(asset, base, unreal.Rotator())
        made.append(actor)
        actor.set_actor_label("TMP_character_Protagonist")
        for i, path in enumerate(filter(None, os.environ.get("FOA_EXTRA", "").split(","))):
            # extra worn layers (e.g. the fitted sleep pants): same skeleton, bind pose = the body's pose here
            m = unreal.load_asset(path)
            if m is None:
                print("MH_CAPTURE missing extra", path)
                continue
            ex = EAS.spawn_actor_from_class(unreal.SkeletalMeshActor, base, unreal.Rotator())
            made.append(ex)
            ex.set_actor_label(f"TMP_character_Layer{i}")
            ex.skeletal_mesh_component.set_skeletal_mesh_asset(m)
            ex.attach_to_actor(actor, "", unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD,
                               unreal.AttachmentRule.KEEP_WORLD, False)
            print("MH_CAPTURE layer", path)
        cap = EAS.spawn_actor_from_class(unreal.SceneCapture2D, base, unreal.Rotator())
        made.append(cap)
        cap.set_actor_label("TMP_character_Capture")
        comp = cap.capture_component2d
        rt = unreal.RenderingLibrary.create_render_target2d(world, 1080, 1080,
                                                            unreal.TextureRenderTargetFormat.RTF_RGBA8)
        comp.set_editor_property("texture_target", rt)
        comp.set_editor_property("capture_source", unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
        comp.set_editor_property("capture_every_frame", False)
        comp.set_editor_property("always_persist_rendering_state", True)
        # fixed exposure (auto exposure never settles in a few captures of the night-time room) + a soft key and
        # fill so the review shots read; TMP lights, destroyed with the rest
        pp = comp.get_editor_property("post_process_settings")
        pp.set_editor_property("override_auto_exposure_method", True)
        pp.set_editor_property("auto_exposure_method", unreal.AutoExposureMethod.AEM_MANUAL)
        pp.set_editor_property("override_auto_exposure_apply_physical_camera_exposure", True)
        pp.set_editor_property("auto_exposure_apply_physical_camera_exposure", False)
        pp.set_editor_property("override_auto_exposure_bias", True)
        pp.set_editor_property("auto_exposure_bias", float(os.environ.get("FOA_EXP_BIAS", "0")))
        comp.set_editor_property("post_process_settings", pp)
        comp.set_editor_property("post_process_blend_weight", 1.0)
        rig = (((150, -60, 175), 1.0), ((-120, -90, 150), 0.35), ((-40, 160, 190), 0.6))
        # FOA_LIGHTS=fill: only the level's own lights plus one soft fill from the camera side (the rig's point
        # lights add their own specular hotspots)
        lights = rig if os.environ.get("FOA_LIGHTS", "rig") == "rig" else (((-60, 150, 170), 0.3),)
        for i_, (off, cd) in enumerate(lights):
            lt = EAS.spawn_actor_from_class(unreal.PointLight, base + unreal.Vector(*off), unreal.Rotator())
            made.append(lt)
            lt.set_actor_label(f"TMP_character_Light{i_}")
            lc = lt.point_light_component
            lc.set_editor_property("intensity_units", unreal.LightUnits.CANDELAS)
            lc.set_editor_property("intensity", float(os.environ.get("FOA_LIGHT_CD", "40")) * cd)
            lc.set_editor_property("attenuation_radius", 600.0)
            lc.set_editor_property("source_radius", 25.0)

        faces = [c for c in actor.get_components_by_class(unreal.SkeletalMeshComponent) if "face" in c.get_name().lower()]
        print("MH_CAPTURE face components", [c.get_name() for c in faces])
        # Stencil4 is only a candidate surface. The PP additionally clips the animated front facial region.
        # Hair/grooms must not write it: the Face skeletal primitive also contains scalp/neck/chest.
        for c_ in actor.get_components_by_class(unreal.GroomComponent):
            c_.set_render_custom_depth(False)
            c_.set_custom_depth_stencil_value(0)
        st4 = faces
        for c_ in st4:
            c_.set_render_custom_depth(True)
            c_.set_custom_depth_stencil_value(4)
        print("MH_CAPTURE stencil 4 on", [c.get_name() for c in st4])

        def masked(name, warm=3):
            """beauty shot, then a face-only base-colour pass as the smear mask (<name>_mask)"""
            shoot(world, comp, rt, name, warm)
            if not faces:
                return
            comp.set_editor_property("capture_source", unreal.SceneCaptureSource.SCS_BASE_COLOR)
            comp.set_editor_property("primitive_render_mode",
                                     unreal.SceneCapturePrimitiveRenderMode.PRM_USE_SHOW_ONLY_LIST)
            for c_ in faces:
                comp.show_only_component(c_)
            shoot(world, comp, rt, name + "_mask", 1)
            comp.clear_show_only_components()
            comp.set_editor_property("primitive_render_mode",
                                     unreal.SceneCapturePrimitiveRenderMode.PRM_RENDER_SCENE_PRIMITIVES)
            comp.set_editor_property("capture_source", unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR)

        def fwd(deg):
            a = math.radians(FWD_YAW + deg)
            return unreal.Vector(math.cos(a), math.sin(a), 0.0)

        face = base + unreal.Vector(0, 0, 165)
        body = base + unreal.Vector(0, 0, 92)

        def shots():
            for name, tgt, deg, dist, fov in (("face_front", face, 0, 95, 30), ("face_tq", face, 40, 95, 30),
                                              ("full_body", body, 0, 260, 45), ("full_tq", body, 40, 260, 45)):
                comp.set_editor_property("fov_angle", fov)
                look(cap, tgt + fwd(deg) * dist + unreal.Vector(0, 0, 4), tgt)
                masked(name)
            comp.set_editor_property("fov_angle", 40)
            tt_tgt = base + unreal.Vector(0, 0, 120)  # turntable: knees up, so the face reads
            look(cap, tt_tgt + fwd(25) * 220, tt_tgt)
            for i in range(FRAMES):
                actor.set_actor_rotation(unreal.Rotator(0, 0, 360.0 * i / FRAMES), False)
                masked(f"tt/f_{i + 1:04d}", warm=1)
            print("MH_CAPTURE", OUT, "frames", FRAMES)

        def cleanup():
            for a in reversed(made):  # layers first, then the character, lights and capture
                try:
                    EAS.destroy_actor(a)
                except Exception as e:
                    print("MH_CAPTURE destroy error", e)
            sweep("after the shots")  # belt and braces: nothing TMP_character_ survives a run
            with open(os.path.join(OUT, "_done.txt"), "w") as fh:
                fh.write("done")

        if WAIT <= 0:
            shots()
            return
        # grooms bind and textures stream only on later editor ticks: shoot from a short-lived tick callback
        import time as _t
        st = {"t0": _t.time(), "h": None, "busy": False}

        def tick(_dt):
            if st["busy"] or _t.time() - st["t0"] < WAIT:
                return
            st["busy"] = True
            unreal.unregister_slate_post_tick_callback(st["h"])
            try:
                shots()
            finally:
                cleanup()
        st["h"] = unreal.register_slate_post_tick_callback(tick)
        made_deferred[0] = True
        print("MH_CAPTURE deferred", WAIT, "s")
    finally:
        if not made_deferred[0]:
            for a in reversed(made):
                try:
                    EAS.destroy_actor(a)
                except Exception as e:
                    print("MH_CAPTURE destroy error", e)
            sweep("after a failed or immediate run")



if os.path.exists("P:/FoA/Saved/character_capture.pause"):  # coordinator asked to keep the game thread free
    print("MH_CAPTURE paused (P:/FoA/Saved/character_capture.pause exists)")
else:
    run()
