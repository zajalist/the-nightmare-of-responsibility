"""LS_WakeUp v3 (cine lane): the 8 shots of docs/cinematics/wakeup_shotlist.md, rebuilt in place.
  $env:HAYBA_AGENT_ID='cine'; $env:FOA_AREAS='Cinematics'; $env:FOA_ACTORS_NEW='CINE_'
  python Tools/Unreal/ue_remote.py Tools/Unreal/cine/build_ls_wakeup.py FOA_PART=core   (cameras, player, fade, sound, cuts)
  python Tools/Unreal/ue_remote.py Tools/Unreal/cine/build_ls_wakeup.py FOA_PART=lights (per-shot spawnable lights)
  python Tools/Unreal/ue_remote.py Tools/Unreal/cine/build_ls_wakeup.py FOA_PART=clock    (only the SandClock binding)
  python Tools/Unreal/ue_remote.py Tools/Unreal/cine/build_ls_wakeup.py FOA_PART=faceslip (only the FaceSlip track: calm, one burst at the dip)
Then set bCanBlend on the printed CUT_TRACK with Hayba object_set_property, and save.
Cameras and lights are spawnables: a temporary CINE_ level actor is configured, possessed, then converted (Sequencer
removes the level actor). The player is a spawnable tagged "Player": mech_flow's SetBindingByTag overrides it with the real pawn
(so it never spawns in game), while the editor preview and MRQ renders spawn their own. Placement comes from Saved/WakeUp/placement.json (Tools/Unreal/wakeup/build_anims.py)."""
import math
import os
import sys

import unreal

sys.path.insert(0, "P:/FoA/Tools/Unreal/wakeup")
import importlib  # noqa: E402

import wake_common as W  # noqa: E402

importlib.reload(W)
m = W.m
EAL = unreal.EditorAssetLibrary
LSB = unreal.LevelSequenceEditorBlueprintLibrary
LES = unreal.get_editor_subsystem(unreal.LevelSequenceEditorSubsystem)
EAS = W.EAS
SFX = "/Game/FoA/Audio/SFX/"
FILM_W, FILM_H = 36.0, 20.25
END = 36.4
EDGE_T = W.T["edge"]  # 19.7: the time shift
PART = os.environ.get("FOA_PART", "core")
if PART=='core' and os.environ.get('FOA_ALLOW_WAKE_SEQUENCE_REBUILD')!='1':
    raise RuntimeError('Manual pose handoff: preserve the user-edited Player animation/control tracks. Core rebuild requires explicit FOA_ALLOW_WAKE_SEQUENCE_REBUILD=1 after integrating those edits.')
SMART = unreal.MovieSceneKeyInterpolation.SMART_AUTO


# ---------------------------------------------------------------- helpers
def rot_to(src, dst):
    d = m.norm(m.sub(dst, src))
    return math.degrees(math.asin(max(-1.0, min(1.0, d[2])))), math.degrees(math.atan2(d[1], d[0]))


def fn(t):
    return unreal.FrameNumber(W.frames(t))


def key(ch, t, v, interp=SMART):
    ch.add_key(fn(t), v, 0.0, unreal.MovieSceneTimeUnit.DISPLAY_RATE, interp)


def channels(sec):
    return {str(c.channel_name): c for c in sec.get_all_channels()}


def transform_track(b, keys, interp=SMART, keep=False):
    """keys: [(t, loc, (pitch, yaw, roll))]; yaw unwrapped so a move never spins the long way."""
    sec = b.add_track(unreal.MovieScene3DTransformTrack).add_section()
    sec.set_range_seconds(0.0, END)
    if keep:
        sec.set_completion_mode(unreal.MovieSceneCompletionMode.KEEP_STATE)
    ch = channels(sec)
    prev = None
    for t, loc, (pit, yaw, rol) in keys:
        while prev is not None and yaw - prev > 180.0:
            yaw -= 360.0
        while prev is not None and yaw - prev < -180.0:
            yaw += 360.0
        prev = yaw
        for n, v in (("Location.X", loc[0]), ("Location.Y", loc[1]), ("Location.Z", loc[2]),
                     ("Rotation.X", rol), ("Rotation.Y", pit), ("Rotation.Z", yaw)):
            key(ch[n], t, v, interp)


def float_track(b, name, path, keys):
    tr = b.add_track(unreal.MovieSceneFloatTrack)
    tr.set_property_name_and_path(name, path)
    sec = tr.add_section()
    sec.set_range_seconds(0.0, END)
    ch = sec.get_all_channels()[0]
    for t, v in keys:
        key(ch, t, v)


def ease(sec, side, seconds, seq):
    """Section easing fields are bare UPROPERTYs: text import is the only way in from Python."""
    tick = seq.get_tick_resolution()
    ticks = int(round(seconds * tick.numerator / tick.denominator))
    es = sec.get_editor_property("easing")
    cap = "In" if side == "in" else "Out"
    es.import_text("(bManualEase%s=True,ManualEase%sDuration=%d)" % (cap, cap, ticks))
    sec.set_editor_property("easing", es)


def lifetime(b, t0, t1):
    """Spawnable alive only for [t0, t1): whichever lifetime track this engine gives the binding."""
    for tr in b.get_tracks():
        cls = tr.get_class().get_name()
        if cls == "MovieSceneSpawnTrack":
            for s in tr.get_sections():
                s.set_range_seconds(0.0, END)
                ch = s.get_all_channels()[0]
                for k in list(ch.get_keys()):
                    ch.remove_key(k)
                ch.set_default(False)
                ch.add_key(fn(0.0), False)
                ch.add_key(fn(t0), True)
                ch.add_key(fn(t1), False)
            return cls
        if cls == "MovieSceneBindingLifetimeTrack":
            secs = tr.get_sections()
            (secs[0] if secs else tr.add_section()).set_range_seconds(t0, t1)
            return cls
    return None


def convert(b, actor, name):
    out = LES.convert_to_spawnable(b)
    sp = out[0] if out else b
    sp.set_display_name(name)
    if unreal.SystemLibrary.is_valid(actor) and not actor.is_actor_being_destroyed():
        EAS.destroy_actor(actor)  # Sequencer normally removes it
    return sp


def V(p):
    return unreal.Vector(*p)


def R(r):
    return unreal.Rotator(roll=r[2], pitch=r[0], yaw=r[1])


# ---------------------------------------------------------------- placement and gameplay camera
P = W.load_placement()
LAY, EDGE = P["lay"], P["edge"]
CLOCK = tuple(EDGE["clock"])
YAW = EDGE["yaw"]
LAT = tuple(P["room"]["lat"])
BODY = m.norm(m.sub(LAY["head"], LAY["pelvis"]))
EYE = m.add(m.add(LAY["head"], (0.0, 0.0, 10.0)), m.mul(BODY, 5.0))  # POV: his eyes on the pillow
FACE = m.add(LAY["head"], (0.0, 0.0, 6.0))
FW = (math.cos(math.radians(YAW)), math.sin(math.radians(YAW)), 0.0)
SIT_HEAD = m.add(m.add(EDGE["pelvis"], (0.0, 0.0, 70.0)), m.mul(FW, 5.0))
STAND_HEAD = (EDGE["loc"][0], EDGE["loc"][1], 163.0)


def gameplay_camera(ctrl_yaw, pitch=-10.0):
    """BP_FoAPlayer's spring-arm camera pose with the pawn standing at the edge pose and control rotation (pitch, yaw)."""
    rig = P["rig"]
    ctrl = m.qmul(W.yaw_q(ctrl_yaw), m.qaxis((0.0, 1.0, 0.0), -pitch))
    arm, cam = rig.get("arm", W.RIG_DEFAULT["arm"]), rig.get("cam", W.RIG_DEFAULT["cam"])
    origin = m.add(m.add(EDGE["loc"], m.qrot(W.yaw_q(EDGE["yaw"]), arm.get("rel", (0, 0, 0)))), arm.get("target", (0, 0, 0)))
    end = m.add(m.sub(origin, m.mul(m.qrot(ctrl, (1.0, 0.0, 0.0)), arm.get("length", 220.0))),
                m.qrot(ctrl, arm.get("socket", (0, 0, 0))))
    return m.add(end, m.qrot(ctrl, cam.get("rel", (0, 0, 0)))), (pitch, ctrl_yaw, 0.0), cam.get("fov", 80.0)


def pick_ctrl_yaw(margin=35.0):
    """Control yaw nearest his facing whose arm camera stays inside the room, so the collision probe never pulls it."""
    best = None
    for d in range(-180, 181, 5):
        p = gameplay_camera(YAW + d)[0]
        if abs(p[0]) < 375 - margin and abs(p[1]) < 300 - margin and (best is None or abs(d) < abs(best)):
            best = d
    return YAW + (best or 0)


# ---------------------------------------------------------------- the shots (docs/cinematics/wakeup_shotlist.md)
def shots():
    def k(t, loc, aim, roll=0.0):
        return (t, loc, (*rot_to(loc, aim), roll))

    def focus(keys, tgt):
        return [(t, m.length(m.sub(tgt(t), loc))) for t, loc, _ in keys]

    # 2. POV: eyes open on the ceiling and the dead lantern; an eased head turn on the pillow to the clock
    up = (100.0, -110.0, 290.0)
    eye2 = m.add(EYE, m.mul(LAT, 4.0))
    clock_aim = m.add(CLOCK, (0.0, 0.0, 6.0))
    pov = [k(3.0, EYE, up), k(6.4, EYE, up), k(8.0, eye2, clock_aim, 12.0), k(9.2, eye2, clock_aim, 12.0)]
    d_up, d_clock = m.length(m.sub(up, EYE)), m.length(m.sub(CLOCK, eye2))
    # 3. wide: high north-west corner across the room to the bed, the moon shafts between
    w0 = (-300.0, 230.0, 250.0)
    bed_mid = (250.0, -185.0, 75.0)
    wide = [k(9.2, w0, bed_mid), k(13.2, w0, bed_mid)]
    # 4. the slow push-in on his face: high three-quarter from the room side and the foot, about 34 deg off his face
    # plane (his face points 20 deg from up toward his feet). Draft 1's low angle saw it edge-on from under the chin.
    d4 = m.norm((-0.45, 0.57, 0.69))
    s4, e4 = m.add(FACE, m.mul(d4, 150.0)), m.add(FACE, m.mul(d4, 100.0))
    push = [k(13.2, s4, FACE), k(14.2, s4, FACE), k(18.8, e4, FACE), k(19.7, e4, FACE)]
    # 5. bed-edge two-shot: front-right of him at seated eye height, him and the clock in one plane
    a5 = math.radians(YAW + 45.0)
    c5 = (EDGE["pelvis"][0] + 190.0 * math.cos(a5), EDGE["pelvis"][1] + 190.0 * math.sin(a5), 120.0)
    aim5 = m.lerp(SIT_HEAD, CLOCK, 0.35)
    two = [k(19.7, c5, aim5), k(24.2, c5, aim5)]
    # 6. high three-quarter insert includes the slap, the complete clock and its persistent sand pile.
    c6 = (CLOCK[0]-123.0,CLOCK[1]+83.5,189.97432)
    aim6 = (CLOCK[0]-5.0,CLOCK[1]-5.0,94.0)
    ins = [k(24.2, c6, aim6), k(28.4, c6, aim6)]
    # 7. the stand: front three-quarter from the room, an eased crane up with him
    a7 = math.radians(YAW + 25.0)
    d7 = (math.cos(a7), math.sin(a7), 0.0)
    c7a = m.add((EDGE["loc"][0], EDGE["loc"][1], 100.0), m.mul(d7, 210.0))
    c7b = m.add(m.add(c7a, (0.0, 0.0, 40.0)), m.mul(d7, 15.0))
    stand = [k(28.4, c7a, SIT_HEAD), k(29.4, c7a, SIT_HEAD), k(31.4, c7b, STAND_HEAD), k(33.4, c7b, STAND_HEAD)]
    # 8. hand-back: over his right shoulder on the gameplay axis, 60 % of the arm, then the camera-cut blend
    g_pos, g_rot, g_fov = gameplay_camera(EDGE["ctrl_yaw"])
    c8 = m.lerp(STAND_HEAD, g_pos, 0.8)
    back = [(33.4, c8, g_rot), (END, c8, g_rot)]
    head7 = lambda t: SIT_HEAD if t < 30.0 else STAND_HEAD  # noqa: E731
    return [
        dict(name="POV", keys=pov, focal=24.0, aperture=1.4, cut=(0.0, 9.2),
             focus=[(3.0, 15.0), (3.4, 15.0), (5.2, d_up), (6.4, d_up), (8.0, d_clock), (9.2, d_clock)],
             vignette=[(3.0, 1.0), (5.4, 0.45), (9.2, 0.45)]),
        dict(name="Wide", keys=wide, focal=28.0, aperture=4.0, cut=(9.2, 13.2), focus=focus(wide, lambda t: bed_mid)),
        # PushIn is DROPPED in the live LS_WakeUp (user, 11-10: "we can see his freaking head"; its close top-down filled
        # the frame with his head). The live film was retimed after this builder: reconcile timings before any rebuild.
        dict(name="PushIn", keys=push, focal=50.0, aperture=2.0, cut=(13.2, EDGE_T), focus=focus(push, lambda t: FACE)),
        dict(name="TwoShot", keys=two, focal=40.0, aperture=2.8, cut=(EDGE_T, 24.2), focus=focus(two, lambda t: SIT_HEAD)),
        dict(name="Insert", keys=ins, focal=40.0, aperture=5.6, cut=(24.2, 28.4), focus=focus(ins, lambda t: aim6)),
        dict(name="Stand", keys=stand, focal=32.0, aperture=2.8, cut=(28.4, 33.4), focus=focus(stand, head7)),
        dict(name="HandBack", keys=back, focal=35.0, aperture=8.0, cut=(33.4, END),
             focus=focus(back, lambda t: STAND_HEAD)),
    ], (g_pos, g_rot, g_fov)


# Per-shot lights: (name, kind, location, aim, candela, attenuation radius, t0, t1, extra). Moon = bay side, cold;
# levels set from MRQ frames (draft 4 had shots 2, 4, 5, 7 at mean luma 100-114 against the wide's 81), not the previz;
# door = hallway leak, warm and hard; dial = the clock's luminous face. All shadowless.
MOON, DOOR, DIAL = (0.78, 0.86, 1.0), (1.0, 0.86, 0.68), (0.9, 0.95, 1.0)


def lights():
    dial = m.add(CLOCK, (-5.0, 6.0, 7.0))
    return [
        ("L2_CeilingWash", "rect", (250.0, -275.0, 110.0), (90.0, -100.0, 300.0), 3.0, 520.0, 3.0, 9.2, dict(size=(220, 120), color=MOON)),
        ("L2_Dial", "point", dial, None, 1.5, 60.0, 3.0, 9.2, dict(src=3.0, color=DIAL)),
        ("L3_BedKick", "rect", (60.0, -280.0, 220.0), (280.0, -190.0, 70.0), 6.0, 650.0, 9.2, 13.2, dict(size=(120, 60), color=MOON)),
        ("L4_MoonKey", "rect", m.add(FACE, (-90.0, -75.0, 110.0)), FACE, 1.0, 420.0, 13.2, EDGE_T, dict(size=(60, 60), color=MOON)),
        ("L4_Eye", "point", m.add(FACE, (-45.0, 90.0, 40.0)), None, 0.12, 180.0, 13.2, EDGE_T, dict(src=2.0, color=MOON)),
        ("L5_DoorRim", "spot", (360.0, 60.0, 45.0), m.add(SIT_HEAD, (0.0, 0.0, -10.0)), 5.0, 420.0, EDGE_T, 24.2, dict(cone=(18, 34), src=1.0, color=DOOR)),
        ("L5_MoonBack", "rect", (200.0, -280.0, 200.0), SIT_HEAD, 2.5, 380.0, EDGE_T, 24.2, dict(size=(60, 60), color=MOON)),
        ("L6_Dial", "point", dial, None, 0.12, 50.0, 24.2, 28.4, dict(src=2.0, color=DIAL)),
        ("L6_SandRim", "spot", (360.0, 20.0, 95.0), CLOCK, 2.5, 260.0, 24.2, 28.4, dict(cone=(10, 20), src=0.5, color=DOOR)),
        ("L7_MoonKey", "rect", (180.0, -260.0, 210.0), STAND_HEAD, 2.0, 420.0, 28.4, END, dict(size=(70, 70), color=MOON)),
        ("L7_DoorRim", "spot", (365.0, 60.0, 80.0), (EDGE["loc"][0], EDGE["loc"][1], 140.0), 4.0, 450.0, 28.4, END, dict(cone=(20, 36), src=1.0, color=DOOR)),
    ]


# ---------------------------------------------------------------- builders
def make_camera(seq, s):
    t0, loc0, rot0 = s["keys"][0]
    cam = EAS.spawn_actor_from_class(unreal.CineCameraActor, V(loc0), R(rot0))
    cam.set_actor_label("CINE_" + s["name"])
    cc = cam.get_cine_camera_component()
    fb = cc.get_editor_property("filmback")
    fb.set_editor_property("sensor_width", FILM_W)
    fb.set_editor_property("sensor_height", FILM_H)
    cc.set_editor_property("filmback", fb)
    fs = cc.get_editor_property("focus_settings")
    fs.set_editor_property("focus_method", unreal.CameraFocusMethod.MANUAL)
    fs.set_editor_property("manual_focus_distance", s["focus"][0][1])
    cc.set_editor_property("focus_settings", fs)
    cc.set_editor_property("current_focal_length", s["focal"])
    cc.set_editor_property("current_aperture", s["aperture"])
    if s.get("vignette"):
        pp = cc.get_editor_property("post_process_settings")
        pp.set_editor_property("override_vignette_intensity", True)
        pp.set_editor_property("vignette_intensity", s["vignette"][0][1])
        cc.set_editor_property("post_process_settings", pp)
    b = seq.add_possessable(cam)
    cb = seq.add_possessable(cc)
    transform_track(b, s["keys"])
    float_track(cb, "ManualFocusDistance", "FocusSettings.ManualFocusDistance", s["focus"])
    if s.get("vignette"):
        float_track(cb, "VignetteIntensity", "PostProcessSettings.VignetteIntensity", s["vignette"])
    return convert(b, cam, "Cam_" + s["name"])


def make_light(seq, name, kind, loc, aim, cd, radius, t0, t1, x):
    cls = {"point": unreal.PointLight, "spot": unreal.SpotLight, "rect": unreal.RectLight}[kind]
    rot = (*rot_to(loc, aim), 0.0) if aim else (0.0, 0.0, 0.0)
    a = EAS.spawn_actor_from_class(cls, V(loc), R(rot))
    a.set_actor_label("CINE_" + name)
    lc = a.get_component_by_class(unreal.LocalLightComponent)
    lc.set_mobility(unreal.ComponentMobility.MOVABLE)
    lc.set_editor_property("intensity_units", unreal.LightUnits.CANDELAS)
    lc.set_editor_property("intensity", cd)
    lc.set_editor_property("attenuation_radius", radius)
    lc.set_editor_property("cast_shadows", False)
    r_, g_, b_ = [int(c * 255) for c in x["color"]]
    lc.set_editor_property("light_color", unreal.Color(r=r_, g=g_, b=b_, a=255))
    if kind == "rect":
        lc.set_editor_property("source_width", float(x["size"][0]))
        lc.set_editor_property("source_height", float(x["size"][1]))
    else:
        lc.set_editor_property("source_radius", float(x.get("src", 1.0)))
    if kind == "spot":
        lc.set_editor_property("inner_cone_angle", float(x["cone"][0]))
        lc.set_editor_property("outer_cone_angle", float(x["cone"][1]))
    sp = convert(seq.add_possessable(a), a, name)
    return lifetime(sp, t0, t1)


def player(seq, edge_len):
    # A plain spawnable, not a Replaceable: Replaceable bindings spawn their preview only in Editor worlds, so an MRQ
    # (PIE) render would have no protagonist. At runtime SetBindingByTag overrides it and the spawnable never spawns
    # (MovieSceneSpawnablesSystem skips overridden spawnables); in the editor and in MRQ it spawns its own pawn.
    cls = unreal.load_asset(W.PLAYER_BP).generated_class()
    b = LES.add_spawnable_from_class(seq, cls)
    tpl = unreal.MovieSceneBindingExtensions.get_object_template(b)
    cmc = tpl.get_editor_property("character_movement") if tpl else None  # template components aren't registered
    if cmc:  # the render copy must not fall under gravity between transform keys
        cmc.set_editor_property("default_land_movement_mode", unreal.MovementMode.MOVE_NONE)
    if tpl:  # player lane's flag: BeginPlay calls SetCinematic(true), so the render copy has no look-at or foot IK
        try:
            tpl.set_editor_property("bStartCinematic", True)
        except Exception as err:  # not added to BP_FoAPlayer yet
            print("bStartCinematic missing:", err)
    print("player binding: spawnable, template", tpl.get_class().get_name() if tpl else None, "movement none", bool(cmc))
    b.set_display_name("Player")
    unreal.MovieSceneBindingTagExtensions.tag_binding(b, "Player")
    for t in list(b.get_tracks()):  # Sequencer's seeded empty transform track blends 50/50 with ours: remove it
        if t.get_class().get_name() == "MovieScene3DTransformTrack":
            b.remove_track(t)
    transform_track(b, [(0.0, LAY["loc"], (LAY.get("pitch", 0.0), LAY["yaw"], 0.0)),
                        (EDGE_T, EDGE["loc"], (0.0, YAW, 0.0))], unreal.MovieSceneKeyInterpolation.CONSTANT, keep=True)
    # The POV camera sits inside his head: hide him (hair, brows, lashes) until the wide. The channel stores VISIBLE.
    vs = b.add_track(unreal.MovieSceneVisibilityTrack)
    vs.set_property_name_and_path("bHidden", "bHidden")
    vsec = vs.add_section()
    vsec.set_range_seconds(0.0, END)
    vch = vsec.get_all_channels()[0]
    vch.add_key(fn(0.0), False)
    vch.add_key(fn(9.2), True)
    tr = b.add_track(unreal.MovieSceneSkeletalAnimationTrack)
    lay_a = unreal.load_asset(W.WAKE + "/AS_FoA_Wake_Lying")  # LayToIdle frame 0 plus a breath (wakeup/build_lying.py)
    idle = unreal.load_asset("/Game/Characters/Mannequins/Anims/Unarmed/MM_Idle")
    edge_a = unreal.load_asset(W.EDGE_ANIM)
    tick = seq.get_tick_resolution()
    ticks = lambda s: unreal.FrameNumber(int(round(s * tick.numerator / tick.denominator)))  # noqa: E731
    t_up = EDGE_T + edge_len
    rows = [(lay_a, 0.0, EDGE_T, 0.0, 0.0, 0, None),  # lying, breathing: 9 s of two whole breaths, looped
            (edge_a, EDGE_T, t_up, 0.0, 0.0, 0, ("out", 0.4)),  # switches under black at the time shift
            (idle, t_up - 0.4, END, 0.0, 0.0, 1, ("in", 0.4))]
    for anim, t0, t1, s_off, e_off, row, ez in rows:
        sec = tr.add_section()
        sec.set_row_index(row)
        prm = sec.get_editor_property("params")
        prm.set_editor_property("animation", anim)
        prm.set_editor_property("start_frame_offset", ticks(s_off))
        prm.set_editor_property("end_frame_offset", ticks(max(0.0, e_off)))
        prm.set_editor_property("force_custom_mode", True)
        sec.set_editor_property("params", prm)
        sec.set_range_seconds(t0, t1)  # after the params (a play-rate change rescales the section)
        sec.set_completion_mode(unreal.MovieSceneCompletionMode.RESTORE_STATE)
        if ez:
            ease(sec, ez[0], ez[1], seq)
    return b


def fade(seq):
    sec = seq.add_track(unreal.MovieSceneFadeTrack).add_section()
    sec.set_range_seconds(0.0, END)
    sec.set_completion_mode(unreal.MovieSceneCompletionMode.KEEP_STATE)  # never restore the front end's black
    ch = sec.get_all_channels()[0]
    for t, v in ((0.0, 1.0), (3.0, 1.0), (3.6, 0.55), (3.8, 0.55), (4.1, 0.95), (4.3, 0.95), (5.4, 0.0),
                 (EDGE_T - 0.4, 0.0), (EDGE_T - 0.05, 1.0), (EDGE_T + 0.05, 1.0), (EDGE_T + 0.45, 0.0), (END, 0.0)):
        key(ch, t, v)


def audio(seq, grab_t):
    cues = W.wake_cues.cues_v3(grab_t, EDGE_T, END)  # one list for the track and the review mux
    tr = seq.add_track(unreal.MovieSceneAudioTrack)
    for row, (path, t0, t1, vol, loop, fo) in enumerate(cues):
        snd = unreal.load_asset(SFX + path)
        if not snd:
            print("missing sound", path)
            continue
        sec = tr.add_section()
        sec.set_sound(snd)
        end = t1 if t1 is not None else t0 + min(snd.get_editor_property("duration"), END - t0)
        sec.set_range_seconds(t0, max(end, t0 + 0.1))
        sec.set_row_index(row)
        if loop:
            sec.set_looping(True)
        for c in sec.get_all_channels():
            if "volume" in str(c.channel_name).lower():
                c.set_default(vol)
                if fo:
                    key(c, fo[0], vol)
                    key(c, fo[1], 0.0)


def clock(seq, grab_t):
    """World lane's SandClock_WakeUp, possessed. The alarm rings from 2.3 s until his palm lands on it (grab_t, the
    slap contact from build_anims.py): Ring 1 shakes it on the nightstand. DissolveAmount leaves 0 exactly at contact
    (the crumble starts under the palm) and reaches 1 at +1.2 s; the black pile it leaves stays (KEEP_STATE)."""
    a = next((x for x in EAS.get_all_level_actors() if x.get_actor_label() == "SandClock_WakeUp"), None)
    if a is None:
        print("clock: SandClock_WakeUp not placed yet, skipped")
        return
    b = seq.add_possessable(a)
    b.set_display_name("SandClock")

    def float_track(prop, keys):
        tr = b.add_track(unreal.MovieSceneFloatTrack)
        tr.set_property_name_and_path(prop, prop)
        sec = tr.add_section()
        sec.set_range_seconds(0.0, END)
        sec.set_completion_mode(unreal.MovieSceneCompletionMode.KEEP_STATE)
        ch = sec.get_all_channels()[0]
        for t, v in keys:
            key(ch, t, v, unreal.MovieSceneKeyInterpolation.LINEAR)

    float_track("DissolveAmount", ((0.0, 0.0), (grab_t, 0.0), (grab_t + 1.2, 1.0)))
    has_ring = True
    try:  # the world lane adds Ring (SetRing, exposed to cinematics); until then the track is skipped
        a.get_editor_property("Ring")
    except Exception:
        has_ring = False
    if has_ring:
        float_track("Ring", ((0.0, 0.0), (2.27, 0.0), (2.30, 1.0), (grab_t - 0.03, 1.0), (grab_t, 0.0)))
    print("clock: contact %.2f, DissolveAmount 0 -> 1 by %.2f, Ring %s" % (grab_t, grab_t + 1.2, "keyed" if has_ring else "missing (skipped)"))


def shift_streak(seq):
    """pp's MPC_Dream ShiftStreak (x length, y angle, z intensity, w threshold): only z moves, straddling the time-shift
    dip so the smear shows on the way into and out of the black. Restores pp's resting value afterwards."""
    mpc = unreal.load_asset("/Game/FoA/PostProcess/MPC_Dream")
    if not mpc:
        print("shift streak: MPC_Dream missing, skipped")
        return
    tr = seq.add_track(unreal.MovieSceneMaterialParameterCollectionTrack)
    tr.set_editor_property("mpc", mpc)
    sec = tr.add_section()
    sec.set_range_seconds(EDGE_T - 0.5, EDGE_T + 0.7)
    sec.set_completion_mode(unreal.MovieSceneCompletionMode.RESTORE_STATE)
    for t, z in ((EDGE_T - 0.45, 0.0), (EDGE_T - 0.15, 2.5), (EDGE_T + 0.25, 2.5), (EDGE_T + 0.6, 0.0)):
        sec.add_color_parameter_key("ShiftStreak", fn(t), unreal.LinearColor(0.25, 0.0, z, 1.2))
    print("shift streak keyed")


# look's face slip (MPC_Dream FaceSlip): his face is never shown clean (main, 03:30: the slice distortion is his identity).
# Calm baseline all through; one burst at the time-shift dip, clear of the QA holds (push_in_end ends 19.2, two-shot 21.0).
# Scale (look, 03:35): 1 the standing slip, 0.6 for close-ups (fewer slices, shorter shifts), 2 a full burst, 0 off.
FACE_CALM, FACE_CLOSE, FACE_BURST = 1.0, 0.6, 2.0


def face_slip(seq):
    """Own MPC track, replaced on every run; Restore State hands look's resting value back when the sequence ends."""
    mpc = unreal.load_asset("/Game/FoA/PostProcess/MPC_Dream")
    names = [str(p.get_editor_property("parameter_name")) for p in mpc.get_editor_property("scalar_parameters")] if mpc else []
    for t in list(seq.get_tracks()):
        if isinstance(t, unreal.MovieSceneMaterialParameterCollectionTrack) and str(t.get_display_name()) == "FaceSlip":
            seq.remove_track(t)
    if "FaceSlip" not in names:
        print("face slip: MPC_Dream has no FaceSlip scalar yet, skipped")
        return
    tr = seq.add_track(unreal.MovieSceneMaterialParameterCollectionTrack)
    tr.set_editor_property("mpc", mpc)
    tr.set_display_name("FaceSlip")
    sec = tr.add_section()
    sec.set_range_seconds(0.0, END)
    sec.set_completion_mode(unreal.MovieSceneCompletionMode.RESTORE_STATE)
    for t, v in ((0.0, FACE_CALM), (13.17, FACE_CALM), (13.2, FACE_CLOSE), (EDGE_T - 0.5, FACE_CLOSE),  # 50 mm push-in
                 (EDGE_T - 0.25, FACE_BURST), (EDGE_T + 0.05, FACE_BURST), (EDGE_T + 0.9, FACE_CALM), (END, FACE_CALM)):
        sec.add_scalar_parameter_key("FaceSlip", fn(t), v)
    print("face slip: calm %.1f, push-in %.1f, burst %.1f at %.2f-%.2f s" % (FACE_CALM, FACE_CLOSE, FACE_BURST,
                                                                           EDGE_T - 0.25, EDGE_T + 0.05))


def core(seq):
    for b in list(seq.get_bindings()):
        b.remove()
    for t in list(seq.get_tracks()):
        seq.remove_track(t)
    seq.set_display_rate(unreal.FrameRate(W.FPS, 1))
    seq.set_playback_start_seconds(0.0)
    seq.set_playback_end_seconds(END)
    EDGE["ctrl_yaw"] = pick_ctrl_yaw()
    W.save_placement(P)
    shot_list, g = shots()
    cams = [make_camera(seq, s) for s in shot_list]
    pl = player(seq, P["edge_len"])
    fade(seq)
    audio(seq, P["grab_t"])
    clock(seq, P["grab_t"])
    shift_streak(seq)
    face_slip(seq)
    build_lights(seq)  # Core removed all bindings, including the shot lights.
    cut = seq.add_track(unreal.MovieSceneCameraCutTrack)
    print("CUT_TRACK", cut.get_path_name())
    for s0 in list(cut.get_sections()):  # the track arrives with a full-length default section; it would mask the blend-out
        cut.remove_section(s0)
    for cam, s in zip(cams, shot_list):
        sec = cut.add_section()
        sec.set_range_seconds(*s["cut"])
        sec.set_camera_binding_id(seq.get_binding_id(cam))
        sec.set_completion_mode(unreal.MovieSceneCompletionMode.RESTORE_STATE)
    ease(sec, "out", 1.5, seq)  # the hand-back blend into the pawn's own camera
    try:
        cut.set_editor_property("can_blend", True)
        print("cut track can_blend", cut.get_editor_property("can_blend"))
    except Exception as err:
        print("can_blend: set it with Hayba object_set_property", err)
    # The Control Rig child binding appears once the anim track lands on the pawn; it overrides the body pose.
    for child in list(seq.get_bindings()):
        if any("ControlRig" in t.get_class().get_name() for t in child.get_tracks()):
            print("removed auto child binding", child.get_display_name())
            child.remove()
    print("player tracks", [t.get_class().get_name() for t in pl.get_tracks()])
    print("ctrl yaw %.0f, gameplay camera %s rot %s fov %.0f" % (EDGE["ctrl_yaw"], [round(c) for c in g[0]],
                                                                 [round(c, 1) for c in g[1]], g[2]))


def build_lights(seq, names=None):
    for b in list(seq.get_bindings()):
        name = str(b.get_display_name())
        if name[:1] == "L" and name[1:2].isdigit() and (names is None or name in names):
            b.remove()
    for row in lights():
        if names is None or row[0] in names:
            print(row[0], make_light(seq, *row))


def main():
    seq = unreal.load_asset(W.LS_PATH)
    LSB.close_level_sequence()
    LSB.open_level_sequence(seq)
    LSB.set_lock_camera_cut_to_viewport(False)
    try:
        if PART == "core":
            core(seq)
        elif PART == "faceslip":
            face_slip(seq)
        elif PART == "insert_lights":
            build_lights(seq, {"L6_Dial", "L6_SandRim"})
        elif PART == "audio":
            for track in list(seq.get_tracks()):
                if isinstance(track, unreal.MovieSceneAudioTrack):
                    seq.remove_track(track)
            audio(seq, P['grab_t'])
        elif PART == "clock":  # look placed SandClock_WakeUp after the last core build: re-possess it only
            for b in list(seq.get_bindings()):
                if str(b.get_display_name()) == "SandClock":
                    b.remove()
            clock(seq, P["grab_t"])
        else:
            build_lights(seq)
    finally:
        LSB.close_level_sequence()
    EAL.save_loaded_asset(seq, False)
    if PART == "core" and EAL.does_asset_exist("/Game/FoA/Characters/Player/ABP_FoA_Face"):
        import runpy
        runpy.run_path("P:/FoA/Tools/Unreal/cine/fix_wake_mesh_and_eyes.py", run_name="__main__")
    print("saved", W.LS_PATH, PART, "bindings", [str(b.get_display_name()) for b in seq.get_bindings()])


main()
