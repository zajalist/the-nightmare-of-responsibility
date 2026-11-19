"""The wake-up alarm clock (world lane): it rattles on the nightstand while it rings, and the slap crumbles it into
black sand that stays as a small pile. Edits BP_SandMaterialize (SandClock_WakeUp's class) in place:
  python Tools/Unreal/ui/hayba_replay.py Tools/Splats/build_clock_wakeup.py FOA_CLOCK=assets   # Pile part, vars, stubs
  python Tools/Unreal/ui/hayba_replay.py Tools/Splats/build_clock_wakeup.py FOA_CLOCK=graphs   # SetRing, RingJitter, SetDissolveAmount
  ... FOA_CLOCK=pile           # PileCore (lit dome) + PileSkirt under Pile, SetDissolveAmount grows the core
  ... FOA_CLOCK=hero           # ClockMesh (Lux3D hero clock) under Splats; SetDissolveAmount swaps it for the sand copy
  ... FOA_CLOCK=hero_instance  # SandClock_WakeUp only: the hero mesh, 15 cm tall, dial to the pillow (FOA_ACTORS)
(env: HAYBA_AGENT_ID=world, FOA_AREAS=VFX.) Agreed with the anim lane (LS_WakeUp owner), 2026-11-07:
  - Ring (exposed to cinematics, setter SetRing) keyed 1 from 2.30 s to 25.27 s, 0 at 25.30 s (the slap contact).
    Above 0 a looping 33 ms timer jitters the Splats part off its rest pose (hops up to 0.9 cm, slides 0.35 cm,
    rocks 3 degrees, all x Ring: it reads at 2 m and never walks off), and the alarm mechanism rattles from the clock.
  - DissolveAmount (existing, keyed 0 at 25.30 s, 1 at 26.50 s): the moment it leaves 0 the clock's grains fall
    (M_SplatMesh crumble) while the Pile part, a ~14 cm mound of the same black grains, materializes under them in
    1.4 s and stays. Back to 0 (scrubbing, a new morning) hides the pile again.
Sequencer calls the setters every frame, so both only act on a change of state (timer active / bPileShown)."""
import os

exec(open('P:/FoA/Tools/Unreal/encounter/enc_graph.py').read())  # noqa: S102  house helpers
import unreal  # noqa: E402

BP = '/Game/FoA/VFX/Sand/BP_SandMaterialize'
ME = BP + '.BP_SandMaterialize_C'
PRIM, SCENE = '/Script/Engine.PrimitiveComponent', '/Script/Engine.SceneComponent'
PILE_MESH = '/Game/FoA/VFX/Splats/Meshes/SM_SandMoundSplats_A'
PILE_MI = '/Game/FoA/VFX/Splats/Instances/MI_Sand_ClockPile'
SWAP_AT = 0.03
CRUMBLE = '/Game/FoA/Audio/MetaSounds/Sand/S_Sand_Crumble.S_Sand_Crumble'  # the hand crushes it (docs/design/horror/audio_wiring.md)
RATTLE = '/Game/FoA/Audio/MetaSounds/Clock/S_Clock_AlarmMechanism.S_Clock_AlarmMechanism'
PILE_SCALE = (0.39, 0.39, 0.75)        # SM_SandMoundSplats_A is ~100 x 22 cm; x the actor's 0.36: a 14 x 6 cm heap
COL.update({'sand': unreal.LinearColor(0.30, 0.22, 0.10, 1), 'ring': unreal.LinearColor(0.10, 0.20, 0.35, 1)})
phase = os.environ.get('FOA_CLOCK', 'assets')


def SELF(fn):
    return f'{ME}:{fn}'


def assets():
    bp = unreal.load_asset(BP)
    unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(bp)
    sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    lib = unreal.SubobjectDataBlueprintFunctionLibrary
    by = {str(lib.get_variable_name(lib.get_data(h))): h for h in sds.k2_gather_subobject_data_for_blueprint(bp)}
    root = by.get('DefaultSceneRoot') or sds.k2_gather_subobject_data_for_blueprint(bp)[0]
    if 'Pile' not in by:
        h, fail = sds.add_new_subobject(unreal.AddNewSubobjectParams(parent_handle=root, new_class=unreal.StaticMeshComponent,
                                                                     blueprint_context=bp))
        assert not str(fail), fail
        sds.rename_subobject(h, 'Pile')
        by['Pile'] = h
    t = lib.get_object(lib.get_data(by['Pile']))
    t.set_editor_property('static_mesh', unreal.load_asset(PILE_MESH))
    t.set_editor_property('override_materials', [unreal.load_asset(PILE_MI)])
    t.set_editor_property('relative_scale3d', unreal.Vector(*PILE_SCALE))
    t.set_editor_property('visible', False)
    t.set_editor_property('cast_shadow', False)
    t.set_editor_property('render_custom_depth', True)      # stencil 5 = sand
    t.set_editor_property('custom_depth_stencil_value', 5)
    t.set_collision_profile_name('NoCollision')
    ensure_vars_nc(BP, [('Ring', ptype('real'), '0.0', 'Sand', True), ('bPileShown', ptype('bool'), 'false', 'Sand', False),
                        ('SplatsHome', ptype(unreal.Transform), '', 'Sand', False),
                        ('Rattle', ptype(unreal.AudioComponent), '', 'Sand', False)])
    BEL.set_blueprint_variable_expose_to_cinematics(unreal.load_asset(BP), 'Ring', True)   # Sequencer keys it
    have = [str(n) for n in BEL.list_graph_names(unreal.load_asset(BP))]
    for name, ins in (('SetRing', [('NewValue', ptype('real'))]), ('RingJitter', [])):
        if name not in have:
            Graph.function(BP, name, inputs=ins)
    compile_save(BP)
    print('assets ok')


def graphs():
    # SetRing: Sequencer's setter for Ring. On: start the jitter timer and the rattle once. Off: stop both, rest pose.
    g = Graph.function(BP, 'SetRing')
    e = g.at(entry_node(g), 0, 0)
    sv = mset(g, 'Ring', 250, 0, po(e, 'NewValue'))
    on = g.branch(550, 0)
    feed(on, Condition=fcall(g, f'{KML}:Greater_DoubleDouble', 400, 200, A=po(e, 'NewValue'), B=0.01))
    running = g.branch(850, 0)
    feed(running, Condition=fcall(g, f'{KSL}:K2_IsTimerActive', 700, 200, FunctionName='RingJitter'))
    start = fcall(g, f'{KSL}:K2_SetTimer', 1150, 120, FunctionName='RingJitter', Time=0.033, bLooping='true')
    snd = fcall(g, f'{GS}:SpawnSoundAttached', 1450, 120, Sound=RATTLE, AttachToComponent=mget(g, 'Splats', 1250, 360))
    sr = mset(g, 'Rattle', 1800, 120, po(snd, 'ReturnValue'))
    stop = fcall(g, f'{KSL}:K2_ClearTimer', 850, 500, FunctionName='RingJitter')
    rest = fcall(g, f'{SCENE}:K2_SetRelativeTransform', 1150, 500, self=mget(g, 'Splats', 1000, 700),
                 NewTransform=mget(g, 'SplatsHome', 1000, 800))
    okr = g.branch(1450, 500)
    rat = mget(g, 'Rattle', 1300, 750)
    feed(okr, Condition=fcall(g, f'{KSL}:IsValid', 1350, 680, Object=rat))
    fade = fcall(g, '/Script/Engine.AudioComponent:FadeOut', 1750, 500, self=rat, FadeOutDuration=0.08, FadeVolumeLevel=0.0)
    chain(e, sv, on)
    go(on, running)
    go(running, start, 'else')
    chain(start, snd, sr)
    go(on, stop, 'else')
    chain(stop, rest, okr)
    go(okr, fade)
    box(g, 'Ring rattle', '', [e, sv, on, running, start, snd, sr, stop, rest, okr, rat, fade], 'ring')

    # RingJitter (33 ms while ringing): the Splats part hops, slides and rocks around its rest pose, scaled by Ring
    g = Graph.function(BP, 'RingJitter')
    e = g.at(entry_node(g), 0, 0)
    ring = mget(g, 'Ring', 0, 600)
    home = fcall(g, f'{KML}:BreakTransform', 200, 400, InTransform=mget(g, 'SplatsHome', 0, 400))

    def rnd(lo, hi, x, y):
        return fcall(g, f'{KML}:Multiply_DoubleDouble', x + 160, y, A=fcall(g, f'{KML}:RandomFloatInRange', x, y, Min=lo, Max=hi), B=ring)

    off = fcall(g, f'{KML}:MakeVector', 700, 300, X=rnd(-0.35, 0.35, 360, 260), Y=rnd(-0.35, 0.35, 360, 360),
                Z=rnd(0.0, 0.9, 360, 460))
    rock = fcall(g, f'{KML}:MakeRotator', 700, 600, Roll=rnd(-3.0, 3.0, 360, 560), Pitch=rnd(-3.0, 3.0, 360, 660),
                 Yaw=rnd(-2.0, 2.0, 360, 760))
    xf = fcall(g, f'{KML}:MakeTransform', 1000, 400, Location=fcall(g, f'{KML}:Add_VectorVector', 850, 300, A=po(home, 'Location'), B=off),
               Rotation=fcall(g, f'{KML}:ComposeRotators', 850, 600, A=rock, B=po(home, 'Rotation')), Scale=po(home, 'Scale'))
    st = fcall(g, f'{SCENE}:K2_SetRelativeTransform', 1300, 0, self=mget(g, 'Splats', 1100, 200), NewTransform=xf)
    go(e, st)
    box(g, 'Rattle on the table', '', [e, ring, home, off, rock, xf, st], 'ring')

    dissolve_graph()

    # Construction: remember the Splats part's rest pose (the jitter returns to it)
    g = Graph(BP, 'UserConstructionScript')
    have = [n for n in g.ed.list_all_nodes() if 'SplatsHome' in BEL.get_node_title(n)]
    if not have:
        last = None
        for n in g.ed.list_all_nodes():   # the Loop toggle chain's last node: SetScalarParameterForCustomPrimitiveData
            if 'Custom Primitive Data' in BEL.get_node_title(n) or 'CustomPrimitiveData' in BEL.get_node_title(n):
                last = n
        assert last, 'construction chain not found'
        p = BEL.get_node_pos(last)
        sh = mset(g, 'SplatsHome', p.x + 320, p.y, fcall(g, f'{SCENE}:GetRelativeTransform', p.x + 100, p.y + 240,
                                                            self=mget(g, 'Splats', p.x - 100, p.y + 240)))
        go(last, sh)
        box(g, 'Rest pose', '', [sh], 'ring')
    compile_save(BP)
    print('graphs ok')


CORE_MESH = '/Game/FoA/Procedural/SM_SandMound_A/SM_SandMound_A/StaticMeshes/SM_SandMound_A'   # R 50, H 24 cm dome
SKIRT_MESH = '/Game/FoA/VFX/Sand/Spill/SM_SandSpill_Pour/SM_SandSpill_Pour/StaticMeshes/SM_SandSpill_Pour'                                    # feathered floor spill
CORE_MI, SKIRT_MI = '/Game/FoA/VFX/Sand/MI_Sand_ClockPileCore', '/Game/FoA/VFX/Sand/MI_SandSpill_Floor'
# Children of Pile (actor 0.36 x Pile (0.39, 0.39, 0.75)): the core is a 14 cm wide, 5 cm high lit dome, the skirt a
# 18 cm feathered spill on the wood. The core casts a shadow (a heap, not a hole); the splat grains stay on top as sparkle.
CORE_REL = (1.2, 1.2, 0.45)  # ~17 cm base, ~3 cm high: a slumped heap, not a cone (the SM_SandMound_A dome is conical)
SANDFX = '/Game/FoA/VFX/Sand/BPL_SandFX.BPL_SandFX_C'
ACT = '/Script/Engine.Actor'
RIM_KEY = (420.0, 80.0, 120.0)   # the door side: hallway leak, door gap and the insert's L6_SandRim all come from there


def pile_parts():
    """PileCore + PileSkirt under Pile, and MI_Sand_ClockPileCore (child of MI_SandSpill_Mound: a touch of albedo so the
    dome shades, more grain sheen, rim facing the door-side key). Idempotent."""
    ensure_vars_nc(BP, [('bHandDrip', ptype('bool'), 'false', 'Sand', False)])
    mi = unreal.load_asset(CORE_MI)
    if not mi:
        f = unreal.MaterialInstanceConstantFactoryNew()
        mi = unreal.AssetToolsHelpers.get_asset_tools().create_asset('MI_Sand_ClockPileCore', '/Game/FoA/VFX/Sand',
                                                                       unreal.MaterialInstanceConstant, f)
        mi.set_editor_property('parent', unreal.load_asset('/Game/FoA/VFX/Sand/MI_SandSpill_Mound'))
    MEL = unreal.MaterialEditingLibrary
    MEL.set_material_instance_vector_parameter_value(mi, 'Spill', unreal.LinearColor(0.035, 0.002, 0.55, 1.1))
    MEL.set_material_instance_vector_parameter_value(mi, 'Sheen', unreal.LinearColor(0.10, 0.5, 0.16, 0.9))
    MEL.set_material_instance_vector_parameter_value(mi, 'Rim', unreal.LinearColor(RIM_KEY[0], RIM_KEY[1], RIM_KEY[2], 8.0))
    unreal.EditorAssetLibrary.save_asset(CORE_MI, only_if_is_dirty=False)
    bp = unreal.load_asset(BP)
    unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(bp)
    sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    lib = unreal.SubobjectDataBlueprintFunctionLibrary
    by = {str(lib.get_variable_name(lib.get_data(h))): h for h in sds.k2_gather_subobject_data_for_blueprint(bp)}
    for name, mesh, mat in (('PileCore', CORE_MESH, CORE_MI), ('PileSkirt', SKIRT_MESH, SKIRT_MI)):
        if name not in by:
            h, fail = sds.add_new_subobject(unreal.AddNewSubobjectParams(parent_handle=by['Pile'], new_class=unreal.StaticMeshComponent,
                                                                         blueprint_context=bp))
            assert not str(fail), fail
            sds.rename_subobject(h, name)
            by[name] = h
        t = lib.get_associated_object(lib.get_data(by[name]))
        m = unreal.load_asset(mesh)
        t.set_editor_property('static_mesh', m)
        t.set_editor_property('override_materials', [unreal.load_asset(mat)])
        if name == 'PileCore':
            t.set_editor_property('relative_scale3d', unreal.Vector(*CORE_REL))
        else:   # 18 cm across in the world: undo the actor x Pile scale, then fit the spill's own footprint
            e = m.get_bounds().box_extent
            k = 10.5 / max(e.x, e.y) / (0.36 * 0.39)   # 21 cm: still on the top (the clock is 12 cm from its edge)
            t.set_editor_property('relative_scale3d', unreal.Vector(k, k, 0.6))
            t.set_editor_property('relative_location', unreal.Vector(0.0, 0.0, 0.15 / (0.36 * 0.75)))
        t.set_editor_property('cast_shadow', name == 'PileCore')
        t.set_editor_property('visible', True)       # Pile (hidden until the slap) carries them: SetVisibility propagates
        t.set_editor_property('render_custom_depth', True)
        t.set_editor_property('custom_depth_stencil_value', 5)
        t.set_collision_profile_name('NoCollision')
        print(name, mesh.rsplit('/', 1)[1], 'bounds', m.get_bounds().box_extent, 'rel scale', t.get_editor_property('relative_scale3d'))


def dissolve_graph():
    # SetDissolveAmount: keyed by LS_WakeUp (0 at the slap 12.47 s, 1 at 13.67 s). Leaving 0 shows the pile once (with its
    # core and skirt, propagated); the core grows with the crumble (5% -> 100% by 0.85), so the heap builds under the
    # falling grains instead of popping in. Back to 0 hides it all again.
    g = Graph.function(BP, 'SetDissolveAmount')
    e = g.at(entry_node(g), 0, 0)
    sv = mset(g, 'DissolveAmount', 250, 0, po(e, 'NewValue'))
    ev = fcall(g, f'{PRIM}:SetVectorParameterForCustomPrimitiveData', 550, 0, self=mget(g, 'Splats', 350, 260),
               ParameterName='SandEvent', Value=fcall(g, f'{KML}:MakeVector4', 350, 360, X=po(e, 'NewValue'), Y=0.0, Z=0.0, W=0.0))
    grow = fcall(g, f'{KML}:FClamp', 950, 520, Value=fcall(g, f'{KML}:Divide_DoubleDouble', 800, 520, A=po(e, 'NewValue'), B=0.85),
                 Min=0.05, Max=1.0)
    core = fcall(g, f'{SCENE}:SetRelativeScale3D', 1250, 0, self=mget(g, 'PileCore', 1050, 400),
                 NewScale3D=fcall(g, f'{KML}:Multiply_VectorFloat', 1100, 520,
                                  A=fcall(g, f'{KML}:MakeVector', 950, 640, X=CORE_REL[0], Y=CORE_REL[1], Z=CORE_REL[2]), B=grow))
    # Swap at 0.03 (36 ms of the 1.2 s ramp after the keyed contact): the palm visibly lands ~1 frame after anim's hand_l
    # contact time (wake_film 20261109_215242: wrist bottoms at 12.51 s, key 12.467 s), so 0.0 popped the sand clock early
    gone = fcall(g, f'{KML}:Greater_DoubleDouble', 1450, 300, A=po(e, 'NewValue'), B=SWAP_AT)
    shown = mget(g, 'bPileShown', 1450, 420)
    change = g.branch(1750, 0)
    feed(change, Condition=fcall(g, f'{KML}:NotEqual_BoolBool', 1600, 300, A=gone, B=shown))
    sp = mset(g, 'bPileShown', 2000, 0, gone)
    pile = mget(g, 'Pile', 2000, 300)
    vis = fcall(g, f'{SCENE}:SetVisibility', 2300, 0, self=pile, bNewVisibility=gone, bPropagateToChildren='true')
    form = fcall(g, f'{PRIM}:SetVectorParameterForCustomPrimitiveData', 2600, 0, self=pile, ParameterName='SandEvent',
                 Value=fcall(g, f'{KML}:MakeVector4', 2400, 300, X=1.0, Y=fcall(g, f'{GS}:GetTimeSeconds', 2200, 420), Z=1.4, W=0.0))
    cmesh = mget(g, 'ClockMesh', 2700, 520)
    has = g.branch(2900, 0)
    feed(has, Condition=fcall(g, f'{KSL}:IsValid', 2750, 300, Object=fcall(g, '/Script/Engine.StaticMeshComponent:GetStaticMesh', 2600, 420, self=cmesh)))
    sand = fcall(g, f'{SCENE}:SetVisibility', 3200, 0, self=mget(g, 'Splats', 3050, 300), bNewVisibility=gone)
    hero = fcall(g, f'{SCENE}:SetVisibility', 3500, 0, self=cmesh, bNewVisibility=fcall(g, f'{KML}:Not_PreBool', 3300, 300, A=gone))
    # The slap's impact: a low pooled sand burst across the nightstand top (BP_SandFX, no Niagara) the frame it lands
    bg = g.branch(2750, -300)
    feed(bg, Condition=gone)
    burst = fcall(g, f'{SANDFX}:SpawnSandBurst', 3050, -300, Scale=0.45,
                  Location=fcall(g, f'{KML}:Add_VectorVector', 2900, -120, A=fcall(g, f'{ACT}:K2_GetActorLocation', 2750, -120), B='0,0,1.5'))
    crush = fcall(g, f'{GS}:SpawnSoundAtLocation', 3350, -300, Sound=CRUMBLE, Location=fcall(g, f'{ACT}:K2_GetActorLocation', 3200, -120))
    # (No palm drip: SpawnSandBurst holds still where it spawns, so at hand_l it hung in the air as a dark smudge as
    # the hand withdrew, wake_film 20261109_222157 slap_045-049.)
    chain(e, sv, ev, core, change)
    go(change, sp)
    chain(sp, vis, form, bg)
    go(bg, burst)
    chain(burst, crush, has)
    go(bg, has, 'else')
    chain(has, sand, hero)
    box(g, 'Crumble into a pile', '', [e, sv, ev, grow, core, gone, shown, change, sp, pile, vis, form], 'sand')
    box(g, 'Clock to sand', '', [cmesh, has, sand, hero], 'ring')
    box(g, 'Slap burst', '', [bg, burst, crush], 'sand')


def pile():
    pile_parts()
    dissolve_graph()
    compile_save(BP)
    print('pile ok')


HERO_MESH_DIR = '/Game/FoA/Lux3D/alarm_clock_hero'


def hero_mesh():
    for p in unreal.EditorAssetLibrary.list_assets(HERO_MESH_DIR, recursive=True, include_folder=False):
        a = unreal.load_asset(p)
        if isinstance(a, unreal.StaticMesh):
            return a
    return None


def hero_parts():
    """ClockMesh: the Lux3D clock (pale dial, numerals, steel bells) as a child of Splats, so the ring judder moves it.
    It is the clock you see until the slap; the black-sand splat copy only shows from the slap on, and crumbles."""
    m = hero_mesh()
    assert m, 'import the Lux3D alarm_clock_hero first'
    bp = unreal.load_asset(BP)
    unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(bp)
    sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    lib = unreal.SubobjectDataBlueprintFunctionLibrary
    by = {str(lib.get_variable_name(lib.get_data(h))): h for h in sds.k2_gather_subobject_data_for_blueprint(bp)}
    if 'ClockMesh' not in by:
        h, fail = sds.add_new_subobject(unreal.AddNewSubobjectParams(parent_handle=by['Splats'], new_class=unreal.StaticMeshComponent,
                                                                     blueprint_context=bp))
        assert not str(fail), fail
        sds.rename_subobject(h, 'ClockMesh')
        by['ClockMesh'] = h
    t = lib.get_associated_object(lib.get_data(by['ClockMesh']))
    t.set_editor_property('static_mesh', None)          # the class stays generic; SandClock_WakeUp sets its own mesh
    t.set_editor_property('cast_shadow', True)
    t.set_collision_profile_name('NoCollision')
    compile_save(BP)


def hero_instance():
    """SandClock_WakeUp only: the hero mesh on ClockMesh, sized to the splat clock's silhouette, Splats hidden at rest."""
    m = hero_mesh()
    a = [x for x in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors() if x.get_actor_label() == 'SandClock_WakeUp'][0]
    comps = {c.get_name(): c for c in a.get_components_by_class(unreal.StaticMeshComponent)}
    cm, sp = comps['ClockMesh'], comps['Splats']
    cm.set_editor_property('static_mesh', m)
    b = m.get_bounds()
    h_world = float(os.environ.get('FOA_CLOCK_H', '15.0'))          # cm, the height the clock should stand
    k = h_world / (2.0 * b.box_extent.z) / a.get_actor_scale3d().z
    cm.set_editor_property('relative_scale3d', unreal.Vector(k, k, k))
    cm.set_editor_property('relative_location', unreal.Vector(0.0, 0.0, (b.box_extent.z - b.origin.z) * k))   # base on the table
    # The imported dial faces local +Y (the red second hand's triangles sit at +Y in the UE mesh; the old -Y guess left
    # the clock edge-on to Cam_Hit). FOA_CLOCK_FACE is the world yaw the dial looks along. LS_WakeUp's clock cameras,
    # seen from the clock: Cam_POV -75, Cam_PushIn -149/-130, Cam_TwoShot 170, Cam_Hit 156, Cam_Insert 146. -145 keeps
    # every one within 70 degrees of the dial (none edge-on, none on the back).
    face = float(os.environ.get('FOA_CLOCK_FACE', '-145'))
    cm.set_editor_property('relative_rotation', unreal.Rotator(roll=0.0, pitch=0.0, yaw=face - 90.0 - a.get_actor_rotation().yaw))
    cm.set_visibility(True)
    sp.set_visibility(False)
    print('ClockMesh', m.get_name(), 'k', round(k, 3), 'height cm', h_world)


def hero():
    hero_parts()
    dissolve_graph()
    compile_save(BP)
    print('hero ok')


{'assets': assets, 'graphs': graphs, 'pile': pile, 'hero': hero, 'hero_instance': hero_instance}[phase]()
