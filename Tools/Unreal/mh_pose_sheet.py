"""Outfit fit check on the PLAYABLE character, in a running PIE session (idle, walk mid-stride, sit, reach).

  All inside one EXCLUSIVE hold (Python can't spawn into the PIE world, so PIE copies pre-placed temp actors):
  FOA_STEP=place  (editor world, before PIE) spawn TMP_character_PoseCapture and TMP_character_PoseFill
  FOA_STEP=shoot  (PIE running) the pose sheet below
  FOA_STEP=clear  (editor world, after PIE) destroy every TMP_character_Pose* actor
  FOA_EXCLUSIVE=1 python Tools/Unreal/ue_remote.py Tools/Unreal/mh_pose_sheet.py FOA_STEP=<step> [FOA_OUT=...]

Finds the player pawn in the PIE world, logs every skeletal mesh component (mesh, leader pose, visibility), stands the
pawn on open floor at PlayerStart_WakeUp, then over a few seconds of ticks plays each pose on the body as a single
animation (the followers on Leader Pose must follow), and captures front and 3/4 full-body PNGs with a temporary
SceneCaptureComponent2D and a soft fill light added to the pawn (removed at the end; PIE is thrown away anyway).
Writes FOA_OUT/_done.txt when finished. Poses are UAL clips on the Mannequin skeleton (the body plays them through
skeleton compatibility, as ABP_FoAPlayer does).
"""
import math
import os
import time
import unreal

OUT = os.environ.get("FOA_OUT", "P:/FoA/Saved/CharacterShots/outfit_pie")
UAL = "/Game/FoA/Characters/Player/Anims/UAL/"
POSES = [("idle", "UAL_Idle_Loop", 0.4), ("walk", "UAL_Walk_Loop", 0.33), ("sit", "UAL_Sitting_Idle_Loop", 0.5),
         ("reach", "UAL_PickUp_Table", 0.55)]  # (name, clip, fraction of the clip)
VIEWS = [("front", 0.0), ("tq", 40.0)]
STEP = os.environ.get("FOA_STEP", "shoot")
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
def prep():
    for a in EAS.get_all_level_actors():
        if a.get_actor_label().startswith("TMP_character_Pose"):
            EAS.destroy_actor(a)
            print("POSE cleared", a.get_name())
    if STEP == "place":
        start = next((a for a in EAS.get_all_level_actors() if a.get_actor_label() == "PlayerStart_WakeUp"), None)
        b = start.get_actor_location() if start else unreal.Vector(0, 0, 0)
        cap_ = EAS.spawn_actor_from_class(unreal.SceneCapture2D, unreal.Vector(b.x, b.y, 300), unreal.Rotator())
        cap_.set_actor_label("TMP_character_PoseCapture")
        cap_.capture_component2d.set_editor_property("capture_every_frame", False)
        cap_.capture_component2d.set_editor_property("capture_on_movement", False)
        fill_ = EAS.spawn_actor_from_class(unreal.PointLight, unreal.Vector(b.x - 200, b.y + 150, 220), unreal.Rotator())
        fill_.set_actor_label("TMP_character_PoseFill")
        lc = fill_.point_light_component  # set here: PIE copies it as it is (runtime property writes may not render)
        lc.set_editor_property("intensity_units", unreal.LightUnits.CANDELAS)
        lc.set_editor_property("intensity", 40.0)
        lc.set_editor_property("attenuation_radius", 900.0)
        lc.set_editor_property("source_radius", 60.0)
        print("POSE placed")

def shoot():
    os.makedirs(OUT, exist_ok=True)
    marker = os.path.join(OUT, "_done.txt")
    if os.path.exists(marker):
        os.remove(marker)

    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
    if world is None:
        raise RuntimeError("no PIE world: start PIE first")
    pawn = unreal.GameplayStatics.get_player_pawn(world, 0)
    body = pawn.get_editor_property("mesh")
    print("POSE pawn", pawn.get_name(), "body", body.get_skeletal_mesh_asset().get_name() if body.get_skeletal_mesh_asset() else None,
          "anim", body.get_editor_property("anim_class"))
    for c in pawn.get_components_by_class(unreal.SkeletalMeshComponent):
        lead = c.get_editor_property("leader_pose_component")
        m = c.get_skeletal_mesh_asset()
        print("POSE comp", c.get_name(), m.get_name() if m else None, "leader", lead.get_name() if lead else None,
              "visible", c.is_visible(), "hidden_in_game", c.get_editor_property("hidden_in_game"))

    made = []


    def found(label):
        """The PIE copy of an actor placed by FOA_STEP=place."""
        for a in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor):
            if a.get_actor_label() == label:
                return a
        raise RuntimeError(f"{label} not in the PIE world: run FOA_STEP=place before starting PIE")


    ps = unreal.GameplayStatics.get_all_actors_of_class(world, unreal.PlayerStart)
    start = next((a for a in ps if a.get_actor_label() == "PlayerStart_WakeUp"), ps[0] if ps else None)
    base = unreal.Vector(20, 40, 0)  # open floor mid-room (bed x>173, commode y>215, chimney x<-330)
    half = pawn.get_editor_property("capsule_component").get_scaled_capsule_half_height()
    floor = unreal.Vector(base.x, base.y, 0.0)
    pawn.get_editor_property("character_movement").disable_movement()
    pawn.set_actor_location_and_rotation(unreal.Vector(base.x, base.y, half + 2.0), unreal.Rotator(yaw=180.0), False, True)

    cap = found("TMP_character_PoseCapture")
    comp = cap.capture_component2d
    rt = unreal.RenderingLibrary.create_render_target2d(world, 768, 1024, unreal.TextureRenderTargetFormat.RTF_RGBA8)
    comp.set_editor_property("texture_target", rt)
    comp.set_editor_property("capture_source", unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
    comp.set_editor_property("capture_every_frame", False)
    comp.set_editor_property("always_persist_rendering_state", True)
    comp.set_editor_property("fov_angle", 38.0)  # horizontal; a 180 cm body fills ~3/4 of the 1024 px height
    comp.set_editor_property("show_flag_settings", [unreal.EngineShowFlagsSetting(show_flag_name=f, enabled=False)
                                                    for f in ("DepthOfField", "MotionBlur", "Grain")])
    found("TMP_character_PoseFill")  # lit since FOA_STEP=place


    def fwd(deg):
        a = math.radians(pawn.get_actor_rotation().yaw + deg)
        return unreal.Vector(math.cos(a), math.sin(a), 0.0)


    def snap(name):
        for _ in range(12):
            comp.capture_scene()
        unreal.RenderingLibrary.export_render_target(world, rt, OUT, name + ".png")


    # a tick-driven sequence: set a pose, let the world tick it (followers copy the leader's pose), then shoot
    steps = []
    for pname, clip, frac in POSES:
        steps.append(("pose", pname, clip, frac))
        steps.append(("shoot", pname, None, None))
    st = {"i": 0, "t": time.time(), "h": None}


    def finish():
        unreal.unregister_slate_post_tick_callback(st["h"])
        # the PIE copies die with PIE; FOA_STEP=clear removes the editor-world originals
        with open(marker, "w") as fh:
            fh.write("done")
        print("POSE done", OUT)


    def tick(_dt):
        if time.time() - st["t"] < 0.6:
            return
        st["t"] = time.time()
        try:
            if st["i"] >= len(steps):
                return finish()
            kind, pname, clip, frac = steps[st["i"]]
            st["i"] += 1
            if kind == "pose":
                anim = unreal.load_asset(UAL + clip)
                body.set_animation_mode(unreal.AnimationMode.ANIMATION_SINGLE_NODE)
                body.set_animation(anim)
                body.set_position(anim.get_play_length() * frac, False)
                body.set_play_rate(0.0)
                body.play(False)
                body.set_play_rate(0.0)
            else:
                head = body.get_socket_location("head")
                mid = unreal.Vector(floor.x, floor.y, (head.z + floor.z) * 0.5 - 5)
                for vname, deg in VIEWS:
                    frm = mid + fwd(deg) * 260 + unreal.Vector(0, 0, 20)  # stays inside the 750 x 600 cm room
                    cap.set_actor_location_and_rotation(frm, unreal.MathLibrary.find_look_at_rotation(frm, mid), False, True)
                    snap(f"{pname}_{vname}")
                print("POSE shot", pname)
        except Exception as e:
            print("POSE error", e)
            finish()


    st["h"] = unreal.register_slate_post_tick_callback(tick)
    print("POSE started", len(steps), "steps")


prep() if STEP in ("place", "clear") else shoot()
