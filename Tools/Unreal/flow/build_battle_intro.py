"""LS_BattleIntro and LS_BattleIntro_Short (story lane, main's GO 2026-11-10): the T8 battle intro, the "Nightmare speaks"
version. Shot list and lines: Saved/StoryShots message log / docs (vo_script.json VO_BI_*, VO_NM_*).
Everything is a spawnable owned by the sequence (cameras, the sand figure, the wave, the mound, the garments) except
the player, a spawnable tagged "Player" that BP_BeatDirector.PlayBattleIntro overrides with the real pawn
(SetBindingByTag, as LS_WakeUp). Subtitles, VO, the pp calls and the sand bursts run on director timers
(patch_battle_intro.py), not in the sequence. Rebuilt in place on every run.
  $env:HAYBA_AGENT_ID='story'; $env:FOA_AREAS='/Game/FoA/Cinematics/BattleIntro'
  python Tools/Unreal/ue_remote.py Tools/Unreal/flow/build_battle_intro.py [FOA_VERSION=full|short]"""
import math
import os

import unreal

FOLDER = '/Game/FoA/Cinematics/BattleIntro'
VERSION = os.environ.get('FOA_VERSION', 'full')
NAME = 'LS_BattleIntro' if VERSION == 'full' else 'LS_BattleIntro_Short'
FPS = 30
END = 15.9 if VERSION == 'full' else 4.0
FILM_W, FILM_H = 36.0, 20.25
EAL, AT = unreal.EditorAssetLibrary, unreal.AssetToolsHelpers.get_asset_tools()
LSB = unreal.LevelSequenceEditorBlueprintLibrary
LES = unreal.get_editor_subsystem(unreal.LevelSequenceEditorSubsystem)
SMART, CONST, LIN = (unreal.MovieSceneKeyInterpolation.SMART_AUTO, unreal.MovieSceneKeyInterpolation.CONSTANT,
                     unreal.MovieSceneKeyInterpolation.LINEAR)
G = '/Game/FoA/Characters/Garments/'
PLAYER = '/Game/FoA/Characters/Player/BP_FoAPlayer'
UAL = '/Game/FoA/Characters/Player/Anims/UAL/'
SUIT = '/Game/FoA/VFX/Splats/Meshes/SM_SandSuit/SM_SandSuit/StaticMeshes/SM_SandSuit'
SUIT_MI = '/Game/FoA/VFX/Splats/Instances/MI_Sand_VaseBoss'
PATH_SPILL = '/Game/FoA/VFX/Sand/Spill/SM_SandSpill_Path/SM_SandSpill_Path/StaticMeshes/SM_SandSpill_Path'
MOUND = '/Game/FoA/Procedural/SM_SandMound_A/SM_SandMound_A/StaticMeshes/SM_SandMound_A'
MOUND_MI = '/Game/FoA/VFX/Sand/MI_SandSpill_Mound'

# The room (world cm). The sand figure stands where the vase broke (build_vase_boss_scene FLOOR, yaw -56, 0.85); the
# battle line is Encounter_T8 (-200,-55,0) yaw 180, slots along y, PlayerMark (60,-55,92) facing it.
FIG = (-15.0, -345.0, 0.35)
FIG_CHEST = (-15.0, -345.0, 125.0)
MOUND_AT = (-200.0, -55.0, 0.0)
MARK = (60.0, -55.0, 92.0)
H2 = (10.0, -240.0, 92.0)       # where he stands for the torn-away shirt, facing the figure
H6 = (115.0, -55.0, 92.0)       # half a step behind the mark, for his close-up


def nightmare_spot():
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    d = next((a for a in eas.get_all_level_actors() if a.get_class().get_name() == 'BP_BeatDirector_C'), None)
    comp = d.get_editor_property('NightmareT8') if d else None
    p = comp.get_world_location() if comp else unreal.Vector(-60.0, -320.0, 0.0)
    return (p.x, p.y, p.z + 150.0)


def yaw_to(src, dst):
    return math.degrees(math.atan2(dst[1] - src[1], dst[0] - src[0]))


def rot_to(src, dst):
    d = [b - a for a, b in zip(src, dst)]
    n = math.sqrt(sum(c * c for c in d)) or 1.0
    return math.degrees(math.asin(max(-1.0, min(1.0, d[2] / n)))), math.degrees(math.atan2(d[1], d[0]))


def lerp(a, b, t):
    return tuple(x + (y - x) * t for x, y in zip(a, b))


def fn(t):
    return unreal.FrameNumber(int(round(t * FPS)))


def key(ch, t, v, interp=SMART):
    ch.add_key(fn(t), v, 0.0, unreal.MovieSceneTimeUnit.DISPLAY_RATE, interp)


def channels(sec):
    return {str(c.channel_name): c for c in sec.get_all_channels()}


def transform_track(b, keys, interp=SMART, keep=False, scale=None):
    """keys: [(t, loc, (pitch, yaw, roll))]; scale: [(t, (sx, sy, sz))]"""
    for t in list(b.get_tracks()):
        if t.get_class().get_name() == 'MovieScene3DTransformTrack':
            b.remove_track(t)
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
        for n, v in (('Location.X', loc[0]), ('Location.Y', loc[1]), ('Location.Z', loc[2]),
                     ('Rotation.X', rol), ('Rotation.Y', pit), ('Rotation.Z', yaw)):
            key(ch[n], t, v, interp)
    for t, s in scale or ():
        for n, v in zip(('Scale.X', 'Scale.Y', 'Scale.Z'), s):
            key(ch[n], t, v, interp)
    return sec


def lifetime(b, t0, t1):
    for tr in b.get_tracks():
        cls = tr.get_class().get_name()
        if cls == 'MovieSceneSpawnTrack':
            for s in tr.get_sections():
                s.set_range_seconds(0.0, END)
                ch = s.get_all_channels()[0]
                for k in list(ch.get_keys()):
                    ch.remove_key(k)
                ch.set_default(False)
                ch.add_key(fn(0.0), False)
                ch.add_key(fn(t0), True)
                if t1 < END:
                    ch.add_key(fn(t1), False)
            return
        if cls == 'MovieSceneBindingLifetimeTrack':
            secs = tr.get_sections()
            (secs[0] if secs else tr.add_section()).set_range_seconds(t0, min(t1, END))
            return


def spawnable(seq, cls, name):
    b = LES.add_spawnable_from_class(seq, cls)
    b.set_display_name(name)
    return b, unreal.MovieSceneBindingExtensions.get_object_template(b)


def camera(seq, name, keys, focal, t_cut, focus=None):
    b, tpl = spawnable(seq, unreal.CineCameraActor, 'Cam_' + name)
    # Newly spawned camera property tracks otherwise override the authored lens defaults.
    for child in list(seq.get_bindings()):
        if child.get_parent().is_valid() and child.get_parent().get_id()==b.get_id():child.remove()
    cc = tpl.get_cine_camera_component()
    for prop in ('camera_component', 'CameraComponent'):  # a spawnable's template has no registered components
        if cc is None:
            try:
                cc = tpl.get_editor_property(prop)
            except Exception:  # noqa: BLE001
                pass
    if cc is None:
        cc = next((o for o in unreal.EditorUtilityLibrary.get_default_subobjects(tpl) if isinstance(o, unreal.CineCameraComponent)), None)             if hasattr(unreal, 'EditorUtilityLibrary') and hasattr(unreal.EditorUtilityLibrary, 'get_default_subobjects') else None
    assert cc is not None, 'no CineCameraComponent on the camera template'
    fb = cc.get_editor_property('filmback')
    fb.set_editor_property('sensor_width', FILM_W)
    fb.set_editor_property('sensor_height', FILM_H)
    cc.set_editor_property('filmback', fb)
    fs = cc.get_editor_property('focus_settings')
    if focus:
        fs.set_editor_property('focus_method', unreal.CameraFocusMethod.MANUAL)
        fs.set_editor_property('manual_focus_distance', focus)
        cc.set_editor_property('current_aperture', 2.8)
    else:
        fs.set_editor_property('focus_method', unreal.CameraFocusMethod.DISABLE)
    cc.set_editor_property('focus_settings', fs)
    cc.set_editor_property('current_focal_length', focal)
    transform_track(b, [(t, loc, (*rot_to(loc, aim), 0.0)) for t, loc, aim in keys])
    lifetime(b, max(0.0, t_cut[0] - 0.05), min(END, t_cut[1] + 0.05))
    return b, t_cut


def mesh_actor(seq, name, mesh, mi, keys, scale, t0, t1, interp=SMART):
    b, tpl = spawnable(seq, unreal.StaticMeshActor, name)
    smc = tpl.get_editor_property('static_mesh_component')
    smc.set_mobility(unreal.ComponentMobility.MOVABLE)
    smc.set_static_mesh(unreal.load_asset(mesh))
    if mi:
        smc.set_material(0, unreal.load_asset(mi))
    smc.set_editor_property('cast_shadow', False)
    transform_track(b, keys, interp, scale=scale)
    lifetime(b, t0, t1)
    return b


def garment(seq, name, mesh, anim, keys, scale, t0, t1, anim_from=None):
    b, tpl = spawnable(seq, unreal.SkeletalMeshActor, name)
    skc = tpl.get_editor_property('skeletal_mesh_component')
    skc.set_mobility(unreal.ComponentMobility.MOVABLE)
    try:
        skc.set_skeletal_mesh_asset(unreal.load_asset(G + mesh))
    except Exception:
        skc.set_editor_property('skeletal_mesh', unreal.load_asset(G + mesh))
    transform_track(b, keys, scale=scale)
    tr = b.add_track(unreal.MovieSceneSkeletalAnimationTrack)
    sec = tr.add_section()
    prm = sec.get_editor_property('params')
    prm.set_editor_property('animation', unreal.load_asset(G + anim))
    sec.set_editor_property('params', prm)
    sec.set_range_seconds(anim_from if anim_from is not None else t0, t1)
    lifetime(b, t0, t1)
    return b


def player(seq, keys, clips):
    cls = unreal.load_asset(PLAYER).generated_class()
    b = LES.add_spawnable_from_class(seq, cls)
    tpl = unreal.MovieSceneBindingExtensions.get_object_template(b)
    cmc = tpl.get_editor_property('character_movement') if tpl else None
    if cmc:
        cmc.set_editor_property('default_land_movement_mode', unreal.MovementMode.MOVE_NONE)
    b.set_display_name('Player')
    unreal.MovieSceneBindingTagExtensions.tag_binding(b, 'Player')
    transform_track(b, keys, CONST, keep=True)
    source=next(child for child in seq.get_bindings() if child.get_parent().is_valid()
                and child.get_parent().get_id()==b.get_id() and str(child.get_display_name())==tpl.get_editor_property('Mesh').get_name())
    # Sequencer auto-adds an unkeyed rig that otherwise overrides every animation with reference pose.
    for track in list(source.get_tracks()):
        if track.get_class().get_name()=='MovieSceneControlRigParameterTrack':source.remove_track(track)
    tr = source.add_track(unreal.MovieSceneSkeletalAnimationTrack)
    for row, (clip, t0, t1) in enumerate(clips):
        sec = tr.add_section()
        sec.set_row_index(row)
        prm = sec.get_editor_property('params')
        prm.set_editor_property('animation', unreal.load_asset(UAL + clip))
        prm.set_editor_property('force_custom_mode', True)
        sec.set_editor_property('params', prm)
        sec.set_range_seconds(t0, t1)
        sec.set_completion_mode(unreal.MovieSceneCompletionMode.RESTORE_STATE)
    return b


def fade(seq, keys):
    sec = seq.add_track(unreal.MovieSceneFadeTrack).add_section()
    sec.set_range_seconds(0.0, END)
    sec.set_completion_mode(unreal.MovieSceneCompletionMode.KEEP_STATE)  # black until the battle's HandoffFadeUp
    ch = sec.get_all_channels()[0]
    for t, v in keys:
        key(ch, t, v, LIN)


def audio(seq, cues):
    tr = seq.add_track(unreal.MovieSceneAudioTrack)
    missing = []
    for row, (path, t0, dur, vol) in enumerate(cues):
        snd = unreal.load_asset(path)
        if not snd:
            missing.append(path)
            continue
        sec = tr.add_section()
        sec.set_sound(snd)
        sec.set_range_seconds(t0, min(END, t0 + dur))
        sec.set_row_index(row)
        for c in sec.get_all_channels():
            if 'volume' in str(c.channel_name).lower():
                c.set_default(vol)
    return missing


def cuts(seq, cams):
    cut = seq.add_track(unreal.MovieSceneCameraCutTrack)
    for s0 in list(cut.get_sections()):
        cut.remove_section(s0)
    for b, (t0, t1) in cams:
        sec = cut.add_section()
        sec.set_range_seconds(t0, t1)
        sec.set_camera_binding_id(seq.get_binding_id(b))
    return cut


MS = '/Game/FoA/Audio/MetaSounds/'


def full(seq):
    nm = nightmare_spot()
    f2 = (math.cos(math.radians(yaw_to(H2, FIG))), math.sin(math.radians(yaw_to(H2, FIG))))
    r2 = (-f2[1], f2[0])  # his right (UE: X forward, Y right)
    ots = (H2[0] - 90 * f2[0] + 35 * r2[0], H2[1] - 90 * f2[1] + 35 * r2[1], 165.0)  # over his right shoulder
    hands = (H2[0] + 35 * f2[0], H2[1] + 35 * f2[1], 115.0)
    fpos = lambda t: lerp((-15.0, -330.0, 2.0), (-200.0, -55.0, 20.0), t)  # noqa: E731  the wave's front
    face6 = (H6[0], H6[1], 160.0)
    cams = [
        camera(seq, '01_Stands', [(0.0, (40.0, -235.0, 55.0), FIG_CHEST), (1.8, (33.0, -255.0, 62.0), FIG_CHEST)], 24.0, (0.0, 1.8)),
        camera(seq, '02_HadIt', [(1.8, ots, FIG_CHEST), (4.2, lerp(ots, FIG_CHEST, 0.08), FIG_CHEST)], 35.0, (1.8, 4.2)),
        camera(seq, '03_RoomGives', [(4.2, (330.0, 245.0, 235.0), (-90.0, -190.0, 30.0)),
                                     (6.8, (318.0, 232.0, 232.0), (-120.0, -150.0, 25.0))], 18.0, (4.2, 6.9)),
        camera(seq, '04a_Pants', [(6.9, (-70.0, -10.0, 40.0), (-200.0, -30.0, 55.0)), (7.7, (-78.0, -12.0, 40.0), (-200.0, -30.0, 60.0))], 35.0, (6.9, 7.7)),
        camera(seq, '04b_Socks', [(7.7, (-95.0, -150.0, 32.0), (-200.0, -105.0, 22.0)), (8.4, (-100.0, -148.0, 32.0), (-200.0, -105.0, 22.0))], 35.0, (7.7, 8.4)),
        camera(seq, '04c_Tie', [(8.4, (-115.0, -45.0, 70.0), (-200.0, -60.0, 85.0)), (9.1, (-125.0, -47.0, 66.0), (-200.0, -60.0, 70.0))], 35.0, (8.4, 9.1)),
        camera(seq, '05_Watches', [(9.1, (-170.0, -20.0, 45.0), nm), (12.5, lerp((-170.0, -20.0, 45.0), nm, 0.04), nm)], 60.0, (9.1, 12.5),
               focus=math.dist((-170.0, -20.0, 45.0), nm)),
        camera(seq, '06_Him', [(12.5, (H6[0] - 150.0, H6[1] + 45.0, 140.0), face6), (14.5, (H6[0] - 140.0, H6[1] + 43.0, 141.0), face6)], 40.0, (12.5, 14.5)),
        camera(seq, '07_ShirtFirst', [(14.5, (275.0, -135.0, 180.0), (-120.0, -55.0, 110.0)), (15.9, (270.0, -133.0, 180.0), (-120.0, -55.0, 110.0))], 28.3, (14.5, 15.9)),
    ]
    # the sand figure, then its collapse into the wave
    mesh_actor(seq, 'SandFigure', SUIT, SUIT_MI, [(0.0, FIG, (0.0, -56.0, 0.0)), (6.8, FIG, (0.0, -56.0, 0.0))],
               [(0.0, (0.85, 0.85, 0.85)), (4.4, (0.85, 0.85, 0.85)), (5.0, (1.05, 1.05, 0.05))], 0.0, 5.1)
    for i, (a, b0, t0) in enumerate(((0.15, 0.45, 4.6), (0.45, 0.75, 5.1), (0.75, 1.0, 5.6))):
        mid = lerp(fpos(a), fpos(b0), 0.5)
        yaw = yaw_to(fpos(a), fpos(b0))
        mesh_actor(seq, 'Wave%d' % (i + 1), PATH_SPILL, MOUND_MI, [(t0, (mid[0], mid[1], 0.5), (0.0, yaw, 0.0)), (END, (mid[0], mid[1], 0.5), (0.0, yaw, 0.0))],
                   [(t0, (0.05, 0.3, 0.2)), (t0 + 0.6, (1.0, 0.7, 1.5))], t0, END)
    mesh_actor(seq, 'Mound', MOUND, MOUND_MI, [(4.6, MOUND_AT, (0.0, 90.0, 0.0)), (END, MOUND_AT, (0.0, 90.0, 0.0))],
               [(4.6, (0.2, 0.2, 0.05)), (6.8, (1.2, 1.7, 0.7)), (END, (1.2, 1.7, 0.75))], 4.6, END)
    # the garments: the shirt torn from his hands into the figure, then riding the wave; the rest rise from the mound
    gy = yaw_to(MOUND_AT, MARK) - 90.0  # rigs are modelled facing -Y
    garment(seq, 'Shirt', 'SK_Garment_Shirt', 'SK_Garment_ShirtArmature_Lash',
            [(1.8, hands, (0.0, yaw_to(H2, FIG) - 90.0, 0.0)), (2.6, hands, (0.0, yaw_to(H2, FIG) - 90.0, 0.0)),
             (3.6, FIG_CHEST, (0.0, -146.0, 0.0)), (4.6, fpos(0.0), (0.0, gy, 0.0)), (6.6, fpos(0.95), (0.0, gy, 0.0)),
             (6.8, (MOUND_AT[0], MOUND_AT[1], -40.0), (0.0, gy, 0.0))],
            [(1.8, (1.0, 1.0, 1.0)), (3.6, (1.0, 1.0, 1.0)), (4.6, (1.2, 1.2, 1.2))], 1.8, 6.9)
    rise = lambda p, z0, z1, t0, t1, t2: [(t0, (p[0], p[1], z0), (0.0, gy, 0.0)), (t1, (p[0], p[1], z1), (0.0, gy, 0.0)),  # noqa: E731
                                          (t2, (p[0], p[1], z1), (0.0, gy, 0.0)), (9.0, (p[0], p[1], z0 - 30.0), (0.0, gy, 0.0))]
    garment(seq, 'Pants', 'SK_Garment_Trousers', 'SK_Garment_TrousersArmature_Kick', rise((-200.0, -30.0), -110.0, -10.0, 6.8, 7.3, 8.6), [(6.8, (1.0, 1.0, 1.0))], 6.8, 9.1)
    garment(seq, 'SockA', 'SK_Garment_Sock', 'SK_Garment_SockArmature_Hop', rise((-200.0, -90.0), -50.0, -6.0, 7.6, 7.9, 8.6), [(7.6, (1.0, 1.0, 1.0))], 7.6, 9.1)
    garment(seq, 'SockB', 'SK_Garment_Sock', 'SK_Garment_SockArmature_Hop', rise((-195.0, -125.0), -50.0, -6.0, 7.85, 8.15, 8.6), [(7.85, (0.9, 0.9, 0.9))], 7.85, 9.1)
    garment(seq, 'Tie', 'SK_Garment_Tie', 'SK_Garment_TieArmature_CoilStrike', rise((-200.0, -60.0), -120.0, 10.0, 8.3, 8.7, 8.95), [(8.3, (1.4, 1.4, 1.4))], 8.3, 9.1)
    # him: facing the figure for shot 2 (jolted as it tears free), then behind the mark, turning from the Nightmare to the
    # mound, then two steps onto the mark
    nm_yaw, mound_yaw = yaw_to(H6, nm), yaw_to(H6, MOUND_AT)
    player(seq, [(0.0, H2, (0.0, yaw_to(H2, FIG), 0.0)), (4.2, H6, (0.0, nm_yaw, 0.0)), (12.9, H6, (0.0, nm_yaw, 0.0)),
                 (13.0, H6, (0.0, nm_yaw + (mound_yaw - nm_yaw) * 0.33, 0.0)), (13.1, H6, (0.0, nm_yaw + (mound_yaw - nm_yaw) * 0.66, 0.0)),
                 (13.2, H6, (0.0, mound_yaw, 0.0))] +
           [(14.6 + 0.1 * i, lerp(H6, MARK, i / 8.0), (0.0, 180.0, 0.0)) for i in range(9)],
           [('UAL_Idle_Loop', 0.0, 2.6), ('UAL_Hit_Chest', 2.6, 3.6), ('UAL_Idle_Loop', 3.6, 12.5),
            ('UAL_Idle_No_Loop', 12.5, 14.6), ('UAL_Walk_Formal_Loop', 14.6, 15.4), ('UAL_Idle_Loop', 15.4, END)])
    fade(seq, [(0.0, 0.0), (15.3, 0.0), (15.9, 1.0)])
    missing = audio(seq, [
        (MS + 'Horror/S_Horror_Presence_Loop_01', 0.0, END, 0.6),
        (MS + 'Sand/S_Sand_Hiss_Loop_01', 0.0, 4.6, 0.7),
        (MS + 'Battle/S_Battle_FabricWhoosh', 2.2, 1.0, 1.0),
        (MS + 'Battle/S_Battle_ClothSnap', 2.6, 1.0, 1.0),
        (MS + 'Breath/S_Breath_Effort', 2.6, 1.2, 0.8),
        (MS + 'Sand/S_Sand_Crumble', 4.5, 2.0, 1.0),
        (MS + 'Sand/S_Sand_Pour', 4.8, 2.2, 0.9),
        (MS + 'Sand/S_Sand_Shift', 5.2, 1.8, 0.7),
        (MS + 'Creaks/S_Creaks_Settle', 5.6, 2.0, 0.6),
        (MS + 'Battle/S_Battle_ClothSnap', 7.0, 0.8, 0.9),
        (MS + 'Footsteps/S_Footsteps_SocksWood', 7.8, 0.5, 0.9),
        (MS + 'Footsteps/S_Footsteps_SocksWood', 8.05, 0.5, 0.8),
        (MS + 'Battle/S_Battle_FabricWhoosh', 8.6, 0.8, 1.0),
        (MS + 'Battle/S_Battle_Zipper', 8.75, 0.6, 0.8),
        (MS + 'Dream/S_Dream_Heartbeat_Loop_01', 9.1, 5.4, 0.8),
        (MS + 'Story/S_Story_TimeShift', 9.1, 1.5, 0.8),
        (MS + 'Breath/S_Breath_Panic_Loop_01', 12.5, 1.6, 0.6),
        (MS + 'Breath/S_Breath_Effort', 14.0, 1.2, 0.8),
        (MS + 'Sand/S_Sand_Shift', 14.6, 1.2, 0.6),
    ])
    return cams, missing


def short(seq):
    cams = [
        camera(seq, '03_RoomGives', [(0.0, (330.0, 245.0, 235.0), (-90.0, -190.0, 30.0)), (2.0, (320.0, 235.0, 233.0), (-120.0, -150.0, 25.0))], 18.0, (0.0, 2.0)),
        camera(seq, '07_ShirtFirst', [(2.0, (275.0, -135.0, 180.0), (-120.0, -55.0, 110.0)), (4.0, (270.0, -133.0, 180.0), (-120.0, -55.0, 110.0))], 28.3, (2.0, 4.0)),
    ]
    fpos = lambda t: lerp((-15.0, -330.0, 2.0), (-200.0, -55.0, 20.0), t)  # noqa: E731
    mesh_actor(seq, 'SandFigure', SUIT, SUIT_MI, [(0.0, FIG, (0.0, -56.0, 0.0)), (2.0, FIG, (0.0, -56.0, 0.0))],
               [(0.0, (0.85, 0.85, 0.85)), (0.2, (0.85, 0.85, 0.85)), (0.7, (1.05, 1.05, 0.05))], 0.0, 0.8)
    for i, (a, b0, t0) in enumerate(((0.15, 0.45, 0.4), (0.45, 0.75, 0.8), (0.75, 1.0, 1.2))):
        mid = lerp(fpos(a), fpos(b0), 0.5)
        yaw = yaw_to(fpos(a), fpos(b0))
        mesh_actor(seq, 'Wave%d' % (i + 1), PATH_SPILL, MOUND_MI, [(t0, (mid[0], mid[1], 0.5), (0.0, yaw, 0.0)), (END, (mid[0], mid[1], 0.5), (0.0, yaw, 0.0))],
                   [(t0, (0.05, 0.3, 0.2)), (t0 + 0.4, (1.0, 0.7, 1.5))], t0, END)
    mesh_actor(seq, 'Mound', MOUND, MOUND_MI, [(0.3, MOUND_AT, (0.0, 90.0, 0.0)), (END, MOUND_AT, (0.0, 90.0, 0.0))],
               [(0.3, (0.2, 0.2, 0.05)), (1.8, (1.2, 1.7, 0.7))], 0.3, END)
    gy = yaw_to(MOUND_AT, MARK) - 90.0
    garment(seq, 'Shirt', 'SK_Garment_Shirt', 'SK_Garment_ShirtArmature_Lash',
            [(0.3, fpos(0.0), (0.0, gy, 0.0)), (1.7, fpos(0.95), (0.0, gy, 0.0)), (1.9, (MOUND_AT[0], MOUND_AT[1], -40.0), (0.0, gy, 0.0))],
            [(0.3, (1.2, 1.2, 1.2))], 0.3, 2.0)
    player(seq, [(0.0, H6, (0.0, 180.0, 0.0)), (2.1, H6, (0.0, 180.0, 0.0))] +
           [(2.1 + 0.1 * i, lerp(H6, MARK, i / 8.0), (0.0, 180.0, 0.0)) for i in range(9)],
           [('UAL_Idle_Loop', 0.0, 2.1), ('UAL_Walk_Formal_Loop', 2.1, 2.9), ('UAL_Idle_Loop', 2.9, END)])
    fade(seq, [(0.0, 0.0), (3.4, 0.0), (4.0, 1.0)])
    missing = audio(seq, [
        (MS + 'Sand/S_Sand_Crumble', 0.1, 1.5, 1.0),
        (MS + 'Sand/S_Sand_Pour', 0.3, 1.8, 0.9),
        (MS + 'Sand/S_Sand_Shift', 2.1, 1.2, 0.6),
    ])
    return cams, missing


def main():
    assert unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world() is None, 'PIE running'
    if not EAL.does_directory_exist(FOLDER):
        EAL.make_directory(FOLDER)
    path = FOLDER + '/' + NAME
    seq = unreal.load_asset(path) if EAL.does_asset_exist(path) else AT.create_asset(
        NAME, FOLDER, unreal.LevelSequence, unreal.LevelSequenceFactoryNew())
    LSB.close_level_sequence()
    LSB.open_level_sequence(seq)
    LSB.set_lock_camera_cut_to_viewport(False)
    for b in list(seq.get_bindings()):
        if b.is_valid():  # Removing a parent also removes its component bindings.
            b.remove()
    assert not seq.get_bindings(), 'sequence bindings were not cleared'
    for t in list(seq.get_tracks()):
        seq.remove_track(t)
    seq.set_display_rate(unreal.FrameRate(FPS, 1))
    seq.set_playback_start_seconds(0.0)
    seq.set_playback_end_seconds(END)
    cams, missing = (full if VERSION == 'full' else short)(seq)
    cuts(seq, cams)
    LSB.close_level_sequence()
    assert EAL.save_loaded_asset(seq, False), path
    print('BATTLE_INTRO', NAME, 'built', len(seq.get_bindings()), 'bindings', len(cams), 'shots', '%.1f s' % END,
          'missing sounds', missing)


main()
