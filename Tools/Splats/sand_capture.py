"""Sand VFX captures through a temporary SceneCapture2D (editor rules: no viewport or game-view calls from scripts, no
camera clutter). Runs inside the open editor and returns at once; frames are taken on later ticks, one per tick.
  python Tools/Unreal/ue_remote.py Tools/Splats/sand_capture.py SAND_CAP=loop [SAND_FROM=0] [SAND_TO=81]
  python Tools/Unreal/ue_remote.py Tools/Splats/sand_capture.py SAND_CAP=stills SAND_POSES=thirdperson,pathlow
  python Tools/Unreal/ue_remote.py Tools/Splats/sand_capture.py SAND_CAP=complexity SAND_TAG=after
loop:       [SAND_LOOPCAM=<pose> SAND_PREFIX=<file prefix>] the commode clock's seamless goo loop (hold -> melt -> ooze back -> hold), material time stepped exactly
            1/15 s per frame (TimeCfg.x = 0, offset set per frame) so it plays at real speed however slowly the editor
            ticks; Glitch held at 0. -> Saved/Screenshots/WindowsEditor/FoA_clockloop_###.png (Tools/Splats/loop_media.py)
stills:     named poses at 1920x1080 -> FoA_sand_<pose>.png ("@Label" aims at an actor); SAND_MASK=1 adds the GBuffer
            normals of the whole scene and of the sand actors alone (FoA_sand_<pose>_nall/_nsand.png): where they match,
            sand is visible (Tools/Splats/sand_mask.py turns the pair into the QA sand mask)
morph:      SAND_STATION=<label>: one full cycle of a BP_SandMorph station -> FoA_morph_<label>_###.png (12 fps)
topdown:    an orthographic map of the floor (where the moonlight pool lands) -> FoA_sand_floormap.png
complexity: the clock frozen mid-hold, lit and in Shader Complexity -> FoA_sc_clock_<tag>[_lit].png
Every instance parameter it touches is restored, and the capture actor (TMP_look_Capture) is destroyed."""


def main():
    """Everything lives in this closure: ue_remote clears the script's globals after the run, the tick outlives it."""
    import os
    import time

    import unreal

    E = {k: os.environ.pop(k) for k in ("SAND_CAP", "SAND_FROM", "SAND_TO", "SAND_POSES", "SAND_TAG", "SAND_WARM", "SAND_NOPPM", "SAND_LOOPCAM", "SAND_PREFIX",
                     "SAND_STATION", "SAND_MASK") if k in os.environ}
    WARM = int(E.get("SAND_WARM", 40))
    MODE = E.get("SAND_CAP", "loop")
    FPS, N = 15, 82
    PERIOD, START = N / FPS, 0.40 * N / FPS        # the clock's assemble cycle is one loop; begin mid-hold
    CLOCK_CAM = ((-132.0, 182.0, 132.0), (4.0, 102.1), 45.0)
    POSES = {
        "thirdperson": ((-60.0, -60.0, 175.0), (-8.1, 18.7), 90.0),
        "wide": ((-340.0, 280.0, 270.0), (-16.9, -50.3), 70.0),           # editor-rules Wide pose (the pp lane's sandmono shots)
        "gameplay": ((-40.0, 20.0, 175.0), (-25.6, 116.2), 90.0),
        "pathlow": ((235.0, -95.0, 45.0), (-18.0, 147.0), 50.0),
        "hearthlow": ((-185.0, -60.0, 55.0), (-17.0, -143.0), 50.0),
        "stream34": ((-60.0, 120.0, 110.0), (-19.5, 127.5), 60.0),
        "streamland": ((-95.0, 150.0, 45.0), (-12.0, 118.0), 40.0),        # close on the pour landing in its pile
        "streamside": ((60.0, 210.0, 70.0), (-1.4, 173.9), 60.0),         # the pour in silhouette against the lamp-lit wall
        "streamwest": ((-300.0, 228.0, 55.0), (-6.0, 0.0), 45.0),         # the pour in front of the moonlit floor strip
        "clock": CLOCK_CAM,
        "clockwake": ((282.0, -35.4, 92.0), (-8.0, -60.0), 40.0),         # LS_WakeUp's insert: SandClock_WakeUp from its dial side
        "clocktop": ((317.0, -96.0, 135.0), (-89.9, 0.0), 50.0),            # straight down on SandClock_WakeUp
        "topdown_path": ((150.0, -40.0, 290.0), (-89.9, 0.0), 60.0),         # floorboard direction and pitch (gap fill)
        "proto_path": ((69.5, -67.3, 85.0), (-32.0, 18.7), 55.0),           # the direction page's prototype camera on the Path spill
    }
    OUT = os.path.join(unreal.Paths.project_saved_dir(), "Screenshots", "WindowsEditor")
    I = "/Game/FoA/VFX/Splats/Instances/"
    MEL = unreal.MaterialEditingLibrary
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)

    if MODE == "loop":
        a, b = int(E.get("SAND_FROM", 0)), int(E.get("SAND_TO", N - 1))
        cam = POSES.get(E.get("SAND_LOOPCAM", "clock"), CLOCK_CAM)
        prefix = E.get("SAND_PREFIX", "FoA_clockloop")
        plan = [(cam, f"{prefix}_{i:03d}.png", START + i / FPS, False) for i in range(a, b + 1)]
        frozen = ("MI_Sand_Clock", "MI_Sand_Mound_OnCommode", "MI_Sand_Stream")
    elif MODE == "morph":     # one full cycle of a BP_SandMorph station: every object rising out of the sand and flowing on
        import json
        import math
        label = E.get("SAND_STATION", "SandMorph_Commode")
        st_actor = next(x for x in eas.get_all_level_actors() if x.get_actor_label() == label)
        rows = len(json.load(open("P:/FoA-Assets/splatmesh/sand_morph_params.json"))[label.split("_")[1]]["rows"])
        size = {"Commode": 26.0, "Desk": 20.0, "Floor": 50.0}[label.split("_")[1]]
        o = st_actor.get_actor_location()
        c = unreal.Vector(o.x - 1.9 * size - 20.0, o.y - 1.9 * size - 20.0, o.z + 0.7 * size + 6.0)
        tgt = unreal.Vector(o.x, o.y, o.z + 0.45 * size)
        dv = tgt - c
        cam = ((c.x, c.y, c.z), (math.degrees(math.atan2(dv.z, math.hypot(dv.x, dv.y))), math.degrees(math.atan2(dv.y, dv.x))), 45.0)
        sm = st_actor.get_component_by_class(unreal.StaticMeshComponent)
        plan, k = [], 0
        for i in range(rows):                          # 0 -> 1 -> ... -> rows-1 -> 0: rise, flow through each, slump back
            fr, to = i, (i + 1) % rows
            for j in range(36):                        # 30 morph frames (2.5 s at 12 fps) + 6 hold frames
                plan.append((cam, f"FoA_morph_{label}_{k:03d}.png", {"morph": (sm, fr, to, min(j / 29.0, 1.0), 4.0)}, False))
                k += 1
        frozen = ()
    elif MODE == "topdown":   # orthographic floor map, 1300 cm wide: world x = (px - 960) * 1300/1920, y = (py - 540) * same
        plan = [(((0.0, 0.0, 200.0), (-90.0, -90.0), -1300.0), "FoA_sand_floormap.png", None, False)]   # under the ceiling and lantern
        frozen = ()
    elif MODE == "complexity":
        tag = E.get("SAND_TAG", "after")
        plan = [(CLOCK_CAM, f"FoA_sc_clock_{tag}_lit.png", 0.5 * PERIOD, False),
                (CLOCK_CAM, f"FoA_sc_clock_{tag}.png", 0.5 * PERIOD, True)]
        frozen = ("MI_Sand_Clock",)
    else:
        import math
        by = {x.get_actor_label(): x for x in eas.get_all_level_actors()}

        def look_at(label):  # "@Label": 3/4 view from 1.6 m out and 1.1 m up, looking at the actor's bounds centre
            o, e = by[label].get_actor_bounds(True)
            c = unreal.Vector(o.x - 120.0, o.y - 100.0, 110.0)
            d = unreal.Vector(o.x - c.x, o.y - c.y, o.z - c.z)
            return ((c.x, c.y, c.z), (math.degrees(math.atan2(d.z, math.hypot(d.x, d.y))), math.degrees(math.atan2(d.y, d.x))), 60.0)
        def proto(label):  # the direction page's prototype camera on an actor: 85 cm up and back, pitch -32, FOV 55
            o = by[label].get_actor_location()
            f = (math.cos(math.radians(18.7)), math.sin(math.radians(18.7)))     # the ThirdPerson camera's yaw
            return ((o.x - f[0] * 85.0, o.y - f[1] * 85.0, 85.0), (-32.0, 18.7), 55.0)
        names = E.get("SAND_POSES", "thirdperson").split(",")
        plan = [(look_at(p[1:]) if p.startswith("@") else proto(p[6:]) if p.startswith("proto@") else POSES[p],
                 f"FoA_sand_{p.replace('@', '_').lstrip('_')}.png", None, False)
                for p in names if p in POSES or (p.startswith("@") and p[1:] in by) or (p.startswith("proto@") and p[6:] in by)]
        if E.get("SAND_MASK"):    # normals pass: (pose, file, None, "nall" | "nsand")
            plan += [(cam, name.replace(".png", f"_{k}.png"), None, k) for cam, name, _, _ in list(plan) for k in ("nall", "nsand")]
        frozen = ()
    mis = {n: unreal.load_asset(I + n) for n in frozen}
    saved = {n: (MEL.get_material_instance_vector_parameter_value(m, "TimeCfg"),
                 MEL.get_material_instance_scalar_parameter_value(m, "Glitch")) for n, m in mis.items()}

    rt = unreal.RenderingLibrary.create_render_target2d(world, 1920, 1080, unreal.TextureRenderTargetFormat.RTF_RGBA8_SRGB)
    cap = eas.spawn_actor_from_class(unreal.SceneCapture2D, unreal.Vector(0.0, 0.0, 200.0))
    cap.set_actor_label("TMP_look_Capture")
    comp = cap.capture_component2d

    def flags(complexity):
        out = []
        for name, on in (("DepthOfField", False), ("MotionBlur", False), ("ShaderComplexity", complexity),
                         ("EyeAdaptation", True),            # captures skip eye adaptation by default; the game uses it
                         ("PostProcessMaterial", "SAND_NOPPM" not in E)):   # SAND_NOPPM=1: judge the sand without the dream post
            f = unreal.EngineShowFlagsSetting()
            f.set_editor_property("show_flag_name", name)
            f.set_editor_property("enabled", on)
            out.append(f)
        return out

    for k, v in (("capture_every_frame", False), ("capture_on_movement", False), ("always_persist_rendering_state", True),
                 ("texture_target", rt), ("capture_source", unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR),
                 ("show_flag_settings", flags(False))):
        comp.set_editor_property(k, v)
    pps = comp.get_editor_property("post_process_settings")  # captures turn Lumen off by default; the game view uses it
    for flag, prop, value in (("override_dynamic_global_illumination_method", "dynamic_global_illumination_method",
                               unreal.DynamicGlobalIlluminationMethod.LUMEN),
                              ("override_reflection_method", "reflection_method", unreal.ReflectionMethod.LUMEN)):
        pps.set_editor_property(flag, True)
        pps.set_editor_property(prop, value)
    comp.set_editor_property("post_process_settings", pps)
    st = {"i": 0, "busy": False, "h": None, "t0": time.time(), "warm": True}

    def set_time(t):
        for n, m in mis.items():
            tc = saved[n][0]
            scale = 0.45 if n == "MI_Sand_Stream" else 1.0
            period = PERIOD if n == "MI_Sand_Clock" else tc.a
            MEL.set_material_instance_vector_parameter_value(m, "TimeCfg", unreal.LinearColor(0.0, t * scale + tc.g, -1.0, period))
            MEL.set_material_instance_scalar_parameter_value(m, "Glitch", 0.0)

    def finish():
        unreal.unregister_slate_post_tick_callback(st["h"])
        for n, m in mis.items():
            MEL.set_material_instance_vector_parameter_value(m, "TimeCfg", saved[n][0])
            MEL.set_material_instance_scalar_parameter_value(m, "Glitch", saved[n][1])
        eas.destroy_actor(cap)
        unreal.log(f"[FoA] sand capture {MODE} done: {st['i']} frames in {time.time() - st['t0']:.0f} s")

    def tick(_dt):
        if st["busy"]:
            return
        st["busy"] = True
        try:
            if st["i"] >= len(plan) or time.time() - st["t0"] > 240:   # hard stop: never a long-lived callback
                finish()
                return
            (loc, (pitch, yaw), fov), name, t, complexity = plan[st["i"]]
            cap.set_actor_location_and_rotation(unreal.Vector(*loc), unreal.Rotator(roll=0.0, pitch=pitch, yaw=yaw), False, False)
            if fov < 0.0:                                 # negative fov = orthographic width, cm
                comp.set_editor_property("projection_type", unreal.CameraProjectionMode.ORTHOGRAPHIC)
                comp.set_editor_property("ortho_width", -fov)
            else:
                comp.set_editor_property("projection_type", unreal.CameraProjectionMode.PERSPECTIVE)
                comp.set_editor_property("fov_angle", fov)
            normals = complexity in ("nall", "nsand")
            comp.set_editor_property("show_flag_settings", flags(complexity is True))
            comp.set_editor_property("capture_source", unreal.SceneCaptureSource.SCS_NORMAL if normals else unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
            comp.set_editor_property("primitive_render_mode", unreal.SceneCapturePrimitiveRenderMode.PRM_USE_SHOW_ONLY_LIST
                                     if complexity == "nsand" else unreal.SceneCapturePrimitiveRenderMode.PRM_RENDER_SCENE_PRIMITIVES)
            if complexity == "nsand":
                comp.clear_show_only_components()
                for x in eas.get_all_level_actors():
                    if x.get_actor_label().startswith(("Sand", "TMP_look_Sand")):
                        comp.show_only_actor_components(x, False)
            if isinstance(t, dict):                   # a morph frame: SandEvent started 'life' of the way back
                comp_, fr, to, life, secs = t["morph"]
                now = unreal.GameplayStatics.get_time_seconds(world)
                comp_.set_vector_parameter_for_custom_primitive_data("SandEvent", unreal.Vector4(fr, to, now - life * secs, secs))
            elif t is not None:
                set_time(t)
            new_view = st["warm"] or t is None or complexity
            for _ in range(WARM if new_view else 3):    # TSR and Lumen history: resolves the dithered splats, GI converges
                comp.capture_scene()
            st["warm"] = False
            unreal.RenderingLibrary.export_render_target(world, rt, OUT, name)
            st["i"] += 1
        except Exception as e:  # any failure ends the run cleanly
            unreal.log_error(f"[FoA] sand capture failed: {e}")
            finish()
        finally:
            st["busy"] = False

    st["h"] = unreal.register_slate_post_tick_callback(tick)
    print("sand capture", MODE, "scheduled", len(plan), "frames")


main()
