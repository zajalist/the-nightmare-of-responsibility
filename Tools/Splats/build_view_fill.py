"""BP_ViewFill (world lane, gameplay lighting): a faint, shadowless, specular-free point light that rides the player's
camera in first person so whatever is within reach (handles, drawers, interactables) always reads in the dark room.
It fades out for every authored camera (any view target that is not the player's own pawn: LS_WakeUp, the phone
push-in, the rollover, the battle cameras) and for the T7 top-down (BP_BeatDirector.bTopDown).
  python Tools/Unreal/ui/hayba_replay.py Tools/Splats/build_view_fill.py FOA_FILL=assets   # BP, Fill light, vars, stubs
  python Tools/Unreal/ui/hayba_replay.py Tools/Splats/build_view_fill.py FOA_FILL=graphs   # Hook, Follow, BeginPlay
  python Tools/Splats/view_fill_curve.py                                                # Curve_GameplayExposure keys
  FOA_ACTORS=ViewFill FOA_ACTORS_NEW=ViewFill ue_remote.py build_view_fill.py FOA_FILL=respawn, then save_level:
  the placed ViewFill keeps per-instance GameplayExposure settings, so template edits only reach a fresh instance.
(env: HAYBA_AGENT_ID=world, FOA_AREAS=Gameplay.) No Tick: BeginPlay hooks the actor onto the player camera manager
(which APlayerCameraManager moves to the final view every frame), then a 20 Hz timer eases the intensity.
GameplayExposure (unbound PostProcessComponent, priority above PP_DreamMono) eases in with the fill and gives gameplay a
FLOOR, not a bias: auto exposure may open up to EXPOSURE_MIN (EV100) in dark views while Curve_GameplayExposure (scene EV100
-> compensation) pulls every view that was already readable back to PP_DreamMono's EV -1. Every authored camera keeps EV -1,
and so does the jumpscare reveal (BP_Jumpscare Phase 3 hides the pawn but keeps the pawn's camera). Lighting sheet
2026-11-09: +1.5 EV takes T3/T4/T7/look-down from 0.03-0.08 to 0.11-0.19 mean luma; yaw 195 (0.26) should not move.
The 0.25 lm fill only keeps whatever is within reach from going pure black (it whitened hands at 0.7)."""
import os

exec(open('P:/FoA/Tools/Unreal/encounter/enc_graph.py').read())  # noqa: S102  house helpers (Graph, fcall, chain...)
import unreal  # noqa: E402

BP = '/Game/FoA/Gameplay/Ambient/BP_ViewFill'
ME = BP + '.BP_ViewFill_C'
DIR_C = '/Game/FoA/Gameplay/BP_BeatDirector.BP_BeatDirector_C'
JS_C = '/Game/FoA/Gameplay/Jumpscare/BP_Jumpscare.BP_Jumpscare_C'   # horror's scare: Phase 3 = revealed on the pawn's camera
ACT, SCENE, LIGHT = '/Script/Engine.Actor', '/Script/Engine.SceneComponent', '/Script/Engine.LightComponent'
COL.update({'fill': unreal.LinearColor(0.30, 0.22, 0.10, 1), 'sched': unreal.LinearColor(0.10, 0.20, 0.35, 1)})
FILL = dict(lumens=0.0, radius=260.0, offset=(-8.0, 0.0, 14.0))   # off: the exposure floor carries the room (moon_d 01:22); any fill whitened the near hand
EXPOSURE_MIN, EXPOSURE_MAX = -2.8, -1.0   # EV100: gameplay may open 1.8 stops past PP_DreamMono's locked -1, never close
LOW = dict(sky=0.2, bay=10.0)   # Low tier (sg.GlobalIlluminationQuality 0, no Lumen): SkyLight 0.07 -> 0.2, bay fill 3 -> 10 lm (sheet 19:10)
BAY_NAME = 'RectLight_2'   # the bay fill light's object name in L_Tutorial_Bedroom. shortcut: found by name (no level save
#   allowed for a tag on 2026-11-10); if the light is re-created, re-read its name and rebuild, or tag it and switch to tags.
CURVE = '/Game/FoA/Gameplay/Ambient/Curve_GameplayExposure'   # its keys: Tools/Splats/view_fill_curve.py (run after assets)   # just above and behind the eye: soft top-front modelling
phase = os.environ.get('FOA_FILL', 'assets')


def SELF(fn):
    return f'{ME}:{fn}'


def timer(g, name, x, y, seconds, loop=False):
    n = fcall(g, f'{KSL}:K2_SetTimer', x, y, FunctionName=name, bLooping='true' if loop else 'false')
    val(n, 'Time', seconds)
    return n


def assets():
    bp = unreal.load_asset(BP)
    if not bp:
        fac = unreal.BlueprintFactory()
        fac.set_editor_property('parent_class', unreal.Actor)
        bp = unreal.AssetToolsHelpers.get_asset_tools().create_asset('BP_ViewFill', '/Game/FoA/Gameplay/Ambient', unreal.Blueprint, fac)
    assert bp, BP
    unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(bp)
    sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    lib = unreal.SubobjectDataBlueprintFunctionLibrary
    by = {str(lib.get_variable_name(lib.get_data(h))): h for h in sds.k2_gather_subobject_data_for_blueprint(bp)}
    root = by.get('DefaultSceneRoot') or sds.k2_gather_subobject_data_for_blueprint(bp)[0]
    if 'Fill' not in by:
        h, fail = sds.add_new_subobject(unreal.AddNewSubobjectParams(parent_handle=root, new_class=unreal.PointLightComponent,
                                                                     blueprint_context=bp))
        assert not str(fail), fail
        sds.rename_subobject(h, 'Fill')
        by['Fill'] = h
    f = lib.get_associated_object(lib.get_data(by['Fill']))
    for k, v in (('intensity_units', unreal.LightUnits.LUMENS), ('intensity', 0.0), ('attenuation_radius', FILL['radius']),
                 ('source_radius', 12.0), ('soft_source_radius', 30.0), ('cast_shadows', False), ('specular_scale', 0.0),
                 ('volumetric_scattering_intensity', 0.0), ('use_temperature', True), ('temperature', 6000.0),
                 ('affect_translucent_lighting', False), ('visible', False),
                 ('relative_location', unreal.Vector(*FILL['offset']))):
        f.set_editor_property(k, v)
    if 'GameplayExposure' not in by:
        h, fail = sds.add_new_subobject(unreal.AddNewSubobjectParams(parent_handle=root, new_class=unreal.PostProcessComponent,
                                                                     blueprint_context=bp))
        assert not str(fail), fail
        sds.rename_subobject(h, 'GameplayExposure')
        by['GameplayExposure'] = h
    pp = lib.get_associated_object(lib.get_data(by['GameplayExposure']))
    cf = unreal.load_asset(CURVE)
    if not cf:
        cf = unreal.AssetToolsHelpers.get_asset_tools().create_asset(CURVE.rsplit('/', 1)[1], CURVE.rsplit('/', 1)[0],
                                                                      unreal.CurveFloat, unreal.CurveFloatFactory())
    # FloatCurve is not Python-editable: its keys go in through Hayba reflection (Tools/Splats/view_fill_curve.py)
    unreal.EditorAssetLibrary.save_loaded_asset(cf, False)
    st = pp.get_editor_property('settings')
    st.set_editor_property('override_auto_exposure_bias', False)
    st.set_editor_property('auto_exposure_bias', 0.0)
    for k, v in (('auto_exposure_min_brightness', EXPOSURE_MIN), ('auto_exposure_max_brightness', EXPOSURE_MAX),
                 ('auto_exposure_bias_curve', cf), ('auto_exposure_speed_up', 2.0), ('auto_exposure_speed_down', 1.0)):
        st.set_editor_property('override_' + k, True)
        st.set_editor_property(k, v)
    for k, v in (('settings', st), ('unbound', True), ('priority', 10.0), ('blend_weight', 0.0)):
        pp.set_editor_property(k, v)
    ensure_vars_nc(BP, [('Director', ptype(unreal.load_class(None, DIR_C)), '', 'Fill', False),
                        ('FillLumens', ptype('real'), str(FILL['lumens']), 'Fill', True),
                        ('Level', ptype('real'), '0.0', 'Fill', False), ('bTop', ptype('bool'), 'false', 'Fill', False),
                        ('Jumpscare', ptype(unreal.load_class(None, JS_C)), '', 'Fill', False), ('bScare', ptype('bool'), 'false', 'Fill', False),
                        ('SkyComp', ptype(unreal.SkyLightComponent), '', 'Low tier', False),
                        ('BayComp', ptype(unreal.LightComponent), '', 'Low tier', False),
                        ('SkyBase', ptype('real'), '0.0', 'Low tier', False), ('BayBase', ptype('real'), '0.0', 'Low tier', False),
                        ('LowSky', ptype('real'), str(LOW['sky']), 'Low tier', True), ('LowBay', ptype('real'), str(LOW['bay']), 'Low tier', True),
                        ('bLowApplied', ptype('bool'), 'false', 'Low tier', False)])
    have = [str(n) for n in BEL.list_graph_names(unreal.load_asset(BP))]
    for name in ('Hook', 'Follow', 'LowTier'):
        if name not in have:
            Graph.function(BP, name)
    compile_save(BP, {'FillLumens': FILL['lumens']})
    print('assets ok')


def graphs():
    # Hook: snap onto the player camera manager (it sits at the final view every frame), then start the 20 Hz ease.
    g = Graph.function(BP, 'Hook')
    e = g.at(entry_node(g), 0, 0)
    cm = fcall(g, f'{GS}:GetPlayerCameraManager', 150, 250, PlayerIndex=0)
    ok = g.branch(500, 0)
    feed(ok, Condition=fcall(g, f'{KSL}:IsValid', 350, 250, Object=po(cm)))
    att = fcall(g, f'{ACT}:K2_AttachToActor', 800, 0, ParentActor=po(cm))
    for pin, v in (('LocationRule', 'SnapToTarget'), ('RotationRule', 'SnapToTarget'), ('ScaleRule', 'KeepWorld')):
        val(att, pin, v)
    run = timer(g, 'Follow', 1150, 0, 0.05, loop=True)
    retry = timer(g, 'Hook', 800, 300, 0.25)
    go(e, ok)
    chain(ok, att, run)
    go(ok, retry, 'else')
    box(g, 'Ride the camera', '', [e, cm, ok, att, run, retry], 'sched')

    # Follow (20 Hz): on only while the player's own, visible pawn is the view target and the room is not in top-down.
    # Level eases 0..1: the fill is Level x FillLumens, GameplayExposure's blend weight is Level.
    g = Graph.function(BP, 'Follow')
    e = g.at(entry_node(g), 0, 0)
    ok = g.branch(300, 0)   # read bTopDown only through a valid Director (BP ANDs don't short-circuit: no Accessed None)
    feed(ok, Condition=fcall(g, f'{KSL}:IsValid', 150, 160, Object=mget(g, 'Director', 0, 160)))
    st = mset(g, 'bTop', 600, 0, field(g, mget(g, 'Director', 300, 220), 'bTopDown', DIR_C, 450, 220))
    box(g, 'Top-down?', '', [e, ok, st], 'sched')
    js = mget(g, 'Jumpscare', 650, 700)
    pok = g.branch(900, 0)   # the same guard for the jumpscare's Phase
    feed(pok, Condition=fcall(g, f'{KSL}:IsValid', 800, 560, Object=js))
    ph = mset(g, 'bScare', 1150, 0, fcall(g, f'{KML}:EqualEqual_IntInt', 1000, 700, A=field(g, mget(g, 'Jumpscare', 800, 760), 'Phase', JS_C, 900, 760), B=3))
    pn = mset(g, 'bScare', 1150, 250)
    val(pn, 'bScare', 'false')
    box(g, 'Jumpscare revealed?', '', [js, pok, ph, pn], 'sched')
    pc = fcall(g, f'{GS}:GetPlayerController', 1300, 400, PlayerIndex=0)
    own = fcall(g, f'{KML}:EqualEqual_ObjectObject', 1700, 400, A=fcall(g, '/Script/Engine.Controller:GetViewTarget', 1500, 400, self=po(pc)),
                B=fcall(g, f'{GS}:GetPlayerPawn', 1500, 520, PlayerIndex=0))
    free = fcall(g, f'{KML}:BooleanNOR', 1700, 620, A=mget(g, 'bTop', 1500, 640), B=mget(g, 'bScare', 1500, 740))
    live = fcall(g, f'{KML}:BooleanAND', 1900, 460, A=own, B=free)
    tgt = fcall(g, f'{KML}:SelectFloat', 2100, 460, A=1.0, B=0.0, bPickA=live)
    lv = fcall(g, f'{KML}:FInterpTo', 2350, 300, Current=mget(g, 'Level', 2150, 300), Target=tgt, DeltaTime=0.05, InterpSpeed=4.0)
    sl = mset(g, 'Level', 2650, 0, po(lv))
    lum = fcall(g, f'{KML}:Multiply_DoubleDouble', 2800, 300, A=po(sl), B=mget(g, 'FillLumens', 2650, 420))
    fl = mget(g, 'Fill', 2950, 200)
    si = fcall(g, f'{LIGHT}:SetIntensity', 3100, 0, self=fl, NewIntensity=po(lum))
    sv = fcall(g, f'{SCENE}:SetVisibility', 3450, 0, self=fl,
               bNewVisibility=fcall(g, f'{KML}:Greater_DoubleDouble', 3250, 220, A=po(lum), B=0.02))
    bw = g.at(g.ed.add_set_member_variable_node('BlendWeight', '/Script/Engine.PostProcessComponent'), 3750, 0)
    feed(bw, self=mget(g, 'GameplayExposure', 3600, 220), BlendWeight=po(sl))
    low_call = fcall(g, SELF('LowTier'), 4050, 0)
    go(e, ok)   # (the first build never wired the entry, so Follow was a no-op and the fill never lit)
    go(ok, st)
    chain(st, pok)
    go(ok, pok, 'else')
    go(pok, ph)
    go(pok, pn, 'else')
    go(ph, sl)
    go(pn, sl)
    chain(sl, si, sv, bw, low_call)
    box(g, 'Ease fill and exposure', '', [pc, own, free, live, tgt, lv, sl, lum, fl, si, sv, bw], 'fill')

    # LowTier (from Follow, so a Settings change at runtime is seen within 50 ms): on Low (no Lumen GI) the SkyLight and
    # the bay fill rise to LowSky / LowBay, otherwise they get their authored values back. Acts only when the tier flips.
    g = Graph.function(BP, 'LowTier')
    e = g.at(entry_node(g), 0, 0)
    cv = fcall(g, f'{KSL}:GetConsoleVariableIntValue', 200, 0, VariableName='sg.GlobalIlluminationQuality')   # impure: on the exec path
    low = fcall(g, f'{KML}:EqualEqual_IntInt', 300, 250, A=po(cv), B=0)   # A wired before the literal: a promotable operator
    flip = g.branch(500, 0)
    feed(flip, Condition=fcall(g, f'{KML}:NotEqual_BoolBool', 450, 250, A=po(low), B=mget(g, 'bLowApplied', 300, 400)))
    keep = mset(g, 'bLowApplied', 750, 0, po(low))
    sok = g.branch(1000, 0)
    feed(sok, Condition=fcall(g, f'{KSL}:IsValid', 900, 250, Object=mget(g, 'SkyComp', 750, 250)))
    ss = fcall(g, '/Script/Engine.SkyLightComponent:SetIntensity', 1250, 0, self=mget(g, 'SkyComp', 1100, 250),
               NewIntensity=fcall(g, f'{KML}:SelectFloat', 1100, 350, A=mget(g, 'LowSky', 950, 400), B=mget(g, 'SkyBase', 950, 480), bPickA=po(low)))
    bok = g.branch(1550, 0)
    feed(bok, Condition=fcall(g, f'{KSL}:IsValid', 1450, 250, Object=mget(g, 'BayComp', 1300, 250)))
    bs = fcall(g, f'{LIGHT}:SetIntensity', 1800, 0, self=mget(g, 'BayComp', 1650, 250),
               NewIntensity=fcall(g, f'{KML}:SelectFloat', 1650, 350, A=mget(g, 'LowBay', 1500, 400), B=mget(g, 'BayBase', 1500, 480), bPickA=po(low)))
    chain(e, cv)
    go(cv, flip)
    go(flip, keep)
    go(keep, sok)
    go(sok, ss)
    go(ss, bok)
    go(sok, bok, 'else')
    go(bok, bs)
    box(g, 'Low tier lights', '', list(g.ed.list_all_nodes()), 'fill')

    # BeginPlay: find the director once (top-down flag), then hook onto the camera
    g = Graph(BP).clear()
    bp_ev = g.event('ReceiveBeginPlay', 0, 0)
    fd = fcall(g, f'{GS}:GetActorOfClass', 250, 200, ActorClass=DIR_C)
    c1 = make(g, 500, 0, 'CastToBP_BeatDirector')
    feed(c1, Object=po(fd, 'ReturnValue'))
    s1 = mset(g, 'Director', 800, 0, as_pin(c1))
    fj = fcall(g, f'{GS}:GetActorOfClass', 900, 300, ActorClass=JS_C)
    c2 = make(g, 1100, 0, 'CastToBP_Jumpscare')
    feed(c2, Object=po(fj, 'ReturnValue'))
    s2 = mset(g, 'Jumpscare', 1400, 0, as_pin(c2))
    # the lights the Low tier lifts, with their authored intensities (LowTier puts these back when the tier is not Low)
    fs = fcall(g, f'{GS}:GetActorOfClass', 1700, 300, ActorClass='/Script/Engine.SkyLight')
    cs = make(g, 2000, 0, 'CastToSkyLightComponent')
    feed(cs, Object=fcall(g, f'{ACT}:GetComponentByClass', 1850, 300, self=po(fs), ComponentClass='/Script/Engine.SkyLightComponent'))
    ssk = mset(g, 'SkyComp', 2300, 0, as_pin(cs))
    ssb = mset(g, 'SkyBase', 2550, 0, field(g, as_pin(cs), 'Intensity', '/Script/Engine.SkyLightComponent', 2400, 250))
    ga = fcall(g, f'{GS}:GetAllActorsOfClass', 2650, 0, ActorClass='/Script/Engine.RectLight')   # impure: on the exec path
    loop = make(g, 2850, 0, 'ForEachLoop')
    feed(loop, Array=po(ga, 'OutActors'))
    named = g.branch(3250, 0)
    feed(named, Condition=fcall(g, '/Script/Engine.KismetStringLibrary:EqualEqual_StrStr', 3150, 300,
                                A=fcall(g, f'{KSL}:GetObjectName', 3000, 300, Object=po(loop, 'Array Element')), B=BAY_NAME))
    cb = make(g, 3500, 0, 'CastToLightComponent')
    feed(cb, Object=fcall(g, f'{ACT}:GetComponentByClass', 3350, 300, self=po(loop, 'Array Element'), ComponentClass='/Script/Engine.LightComponent'))
    sbc = mset(g, 'BayComp', 3800, 0, as_pin(cb))
    sbb = mset(g, 'BayBase', 4050, 0, field(g, as_pin(cb), 'Intensity', '/Script/Engine.LightComponentBase', 3900, 250))
    hk = fcall(g, SELF('Hook'), 3100, -300)
    chain(bp_ev, fd, c1, s1, fj, c2, s2, fs, cs, ssk, ssb, ga, loop)
    go(c2, fs, 'CastFailed')
    go(cs, ga, 'CastFailed')
    go(loop, named, 'LoopBody')
    go(named, cb)
    chain(cb, sbc, sbb)
    go(loop, hk, 'Completed')
    box(g, 'Low tier lights to lift', '', [fs, cs, ssk, ssb, ga, loop, named, cb, sbc, sbb], 'fill')
    go(c1, fj, 'CastFailed')   # no director (a test map): still fill, just never top-down
    box(g, 'Find the director and the scare', '', [bp_ev, fd, c1, s1, fj, c2, s2], 'sched')
    compile_save(BP)
    print('graphs ok')


def respawn():
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    old = [a for a in eas.get_all_level_actors() if a.get_actor_label() == 'ViewFill'][0]
    loc, rot, folder = old.get_actor_location(), old.get_actor_rotation(), old.get_folder_path()
    eas.destroy_actor(old)
    a = eas.spawn_actor_from_class(unreal.load_class(None, ME), loc, rot)
    a.set_actor_label('ViewFill')
    a.set_folder_path(folder)
    print('respawn ok', a.get_name())


{'assets': assets, 'graphs': graphs, 'respawn': respawn}[phase]()
