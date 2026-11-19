"""BP_SandAmbience (world lane): the room's ambient sand life and the foreshadowing, one placed director, no Tick.
  python Tools/Unreal/ui/hayba_replay.py Tools/Splats/build_sand_ambience.py FOA_AMB=assets   # BP, parts, sites, vars, stubs
  python Tools/Unreal/ui/hayba_replay.py Tools/Splats/build_sand_ambience.py FOA_AMB=helpers  # state, scheduling, play
  python Tools/Unreal/ui/hayba_replay.py Tools/Splats/build_sand_ambience.py FOA_AMB=events   # Ev_*, Step, WatchStill, BeginPlay
(env: HAYBA_AGENT_ID=world, FOA_AREAS=Gameplay; each phase compiles through Hayba before the next calls into it.)
Design: docs/design/world/foreshadowing.md. One event at a time: Step hides the last one, reads the live game state
(BP_BeatDirector.BeatIndex / bRollingOver, GI_FoA.DayCount, and whether the player's own camera is the view target),
draws a function name from Deck and runs it by timer. Each Ev_* gates itself (beat window, a chance that grows with
failed days) and either plays (Play: move a hidden splat part to its site, show it, start its SandEvent, Rearm) or
re-draws (Retry). The gap after an event shrinks with Level = 0.07 x beat + 0.12 x failed days. WatchStill (1 Hz)
grows a goo bloom at the player's feet when they stand still; M_SplatMesh's player crawl pulls its grains up the legs.
Every part is hidden when idle, so idle costs nothing on the GPU; at most two splat parts (an event and the feet bloom)
draw at once (<= 25k quads)."""
import os

exec(open('P:/FoA/Tools/Unreal/encounter/enc_graph.py').read())  # noqa: S102  house helpers (Graph, fcall, chain...)
import unreal  # noqa: E402

BP = '/Game/FoA/Gameplay/Ambient/BP_SandAmbience'
ME = BP + '.BP_SandAmbience_C'
DIR_C = '/Game/FoA/Gameplay/BP_BeatDirector.BP_BeatDirector_C'
GI_C = '/Game/FoA/Gameplay/GI_FoA.GI_FoA_C'
NM_C = '/Game/FoA/Characters/Player/BP_Nightmare.BP_Nightmare_C'
PRIM, SCENE, ACT = '/Script/Engine.PrimitiveComponent', '/Script/Engine.SceneComponent', '/Script/Engine.Actor'
PCM = '/Script/Engine.PlayerCameraManager'
V = '/Game/FoA/VFX/Splats'
MESH = {'mound': f'{V}/Meshes/SM_SandMoundSplats_B',
        'trickle': f'{V}/Meshes/SM_SandTrickle_Ceiling/SM_SandTrickle_Ceiling/StaticMeshes/SM_SandTrickle_Ceiling',
        'clockdrip': f'{V}/Meshes/SM_SandTrickle_Clock/SM_SandTrickle_Clock/StaticMeshes/SM_SandTrickle_Clock',
        'drift': f'{V}/Meshes/SM_SandFaceDrift/SM_SandFaceDrift/StaticMeshes/SM_SandFaceDrift',
        'shirt': f'{V}/Meshes/SM_SandShirtImprint/SM_SandShirtImprint/StaticMeshes/SM_SandShirtImprint',
        'suit': f'{V}/Meshes/SM_SandSuit/SM_SandSuit/StaticMeshes/SM_SandSuit',
        'hourglass': f'{V}/Meshes/SM_SandHourglass/SM_SandHourglass/StaticMeshes/SM_SandHourglass',
        'sleeve': '/Game/FoA/Lux3D/the_shirt_enemy/SM_Lux3D_ShirtEnemy'}
MI = f'{V}/Instances/'
# (part, mesh, material, location, (pitch, yaw, roll), scale, splat): every part hidden until an event shows it
PARTS = [('Bloom', 'mound', MI + 'MI_Sand_Bloom', (0, 0, 0.3), (0, 0, 0), 0.6, True),
         ('Absorb', 'mound', MI + 'MI_Sand_Bloom', (0, 0, 0.5), (0, 0, 0), 0.8, True),
         ('Trickle', 'trickle', MI + 'MI_Sand_Trickle', (-50, -245, 299), (0, 90, 0), 1.0, True),
         ('ClockDrip', 'clockdrip', MI + 'MI_Sand_ClockDrip', (-322, 0, 183), (0, 0, 0), 1.0, True),
         ('Drift', 'drift', MI + 'MI_Sand_ShaftDrift', (-60, -285, 95), (0, 90, 0), 4.0, True),
         ('Shirt', 'shirt', MI + 'MI_Sand_Imprint', (-70, -215, 0.3), (0, 75, 0), 1.0, True),
         ('Suit', 'suit', MI + 'MI_Sand_Suit', (-60, -335, 0), (0, 0, 0), 1.0, True),
         ('Hourglass', 'hourglass', MI + 'MI_Sand_Hourglass', (-318, -48, 125.2), (0, 0, 0), 0.45, True),
         ('Sleeve', 'sleeve', '/Game/FoA/Lux3D/the_shirt_enemy/MI_Lux3D_ShirtEnemy', (223, 210, 125),
          (0, 90, 0), 1.0, False)]
# (tag, location, yaw, scale): where events happen; scene components, so a designer can move them in the level
SITES = [('Site.Creep.Door', (370, 88, 0.3), 0, 0.6), ('Site.Creep.Wardrobe', (224, 205, 0.3), 0, 0.7),
         ('Site.Pile', (-240, 110, 0.3), 0, 0.6), ('Site.Pile', (-110, -235, 0.3), 0, 0.7), ('Site.Pile', (-300, 30, 3.3), 0, 0.5),
         ('Site.Trickle', (-50, -245, 299), 90, 1.0), ('Site.Trickle', (-275, -110, 299), 0, 1.0),
         ('Site.Shirt', (-70, -215, 0.3), 75, 1.0), ('Site.Shirt', (-215, 70, 0.3), -20, 1.0),
         ('Site.Suit', (-60, -335, 0), 0, 1.0), ('Site.Suit', (-245, -15, 0), -90, 1.0),   # the moonlit bay, the hearth
         ('Site.Hourglass', (-318, -48, 125.2), 0, 0.45), ('Site.Sleeve', (223, 210, 125), 90, 1.0),
         ('Site.Glimpse', (-115, -345, 92), 0, 1.0), ('Site.Glimpse', (342, 262, 92), 0, 1.0),
         ('Site.Glimpse', (-345, -262, 92), 0, 1.0)]
DECK = ['Ev_Creep', 'Ev_Creep', 'Ev_Pile', 'Ev_Pile', 'Ev_Trickle', 'Ev_Trickle', 'Ev_Drift', 'Ev_ClockDrip',
        'Ev_Sleeve', 'Ev_Shirt', 'Ev_Glimpse', 'Ev_Suit', 'Ev_Hourglass']
EVENTS = sorted(set(DECK))
# Sounds (docs/design/horror/audio_wiring.md, the horror lane's S_Sand_* MetaSound presets)
SND = {k: f'/Game/FoA/Audio/MetaSounds/Sand/S_Sand_{k}.S_Sand_{k}' for k in ('Shift', 'Pour', 'Burst', 'Crumble', 'Trickle_Loop_01', 'Hiss_Loop_01')}
GSA = '/Script/Engine.GameplayStatics'
AUC = '/Script/Engine.AudioComponent'
COL.update({'amb': unreal.LinearColor(0.30, 0.22, 0.10, 1), 'fore': unreal.LinearColor(0.22, 0.14, 0.34, 1),
            'sched': unreal.LinearColor(0.10, 0.20, 0.35, 1), 'state': unreal.LinearColor(0.12, 0.26, 0.16, 1)})
phase = os.environ.get('FOA_AMB', 'assets')


def T(kind):
    return ptype(kind)


def SELF(fn):
    return f'{ME}:{fn}'


SIGS = {  # name: (inputs, outputs, pure)
    'UpdateState': ((), (('Live', 'bool'),), False),
    'Rearm': ((('Seconds', 'real'),), (), False),
    'Retry': ((), (), False),
    'Play': ((('Part', unreal.StaticMeshComponent), ('Where', unreal.Transform), ('X', 'real'), ('Seconds', 'real'),
              ('W', 'real'), ('Total', 'real')), (), False),
    'Site': ((('Tag', 'name'),), (('Where', unreal.Transform),), False),
    'Chance': ((('Base', 'real'), ('PerDay', 'real')), (('Yes', 'bool'),), True),   # pure: it feeds branches as data
    'InBeats': ((('Min', 'int'), ('Max', 'int')), (('Yes', 'bool'),), True),
    'CrumbleActive': ((), (), False), 'HideAbsorb': ((), (), False), 'EndGlimpse': ((), (), False),
    'SleeveJerk': ((), (), False), 'Step': ((), (), False), 'WatchStill': ((), (), False),
    **{e: ((), (), False) for e in EVENTS},
}


def sig_types(spec):
    return [(n, T(t)) for n, t in spec]


def make_bp():
    bp = unreal.load_asset(BP)
    if not bp:
        fac = unreal.BlueprintFactory()
        fac.set_editor_property('parent_class', unreal.Actor)
        bp = unreal.AssetToolsHelpers.get_asset_tools().create_asset('BP_SandAmbience', '/Game/FoA/Gameplay/Ambient',
                                                                       unreal.Blueprint, fac)
    assert bp, BP
    unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(bp)
    return bp


def assets():
    bp = make_bp()
    sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    lib = unreal.SubobjectDataBlueprintFunctionLibrary
    by = {str(lib.get_variable_name(lib.get_data(h))): h for h in sds.k2_gather_subobject_data_for_blueprint(bp)}
    root = by.get('DefaultSceneRoot') or sds.k2_gather_subobject_data_for_blueprint(bp)[0]

    def ensure(name, cls):
        if name not in by:
            h, fail = sds.add_new_subobject(unreal.AddNewSubobjectParams(parent_handle=root, new_class=cls, blueprint_context=bp))
            assert not str(fail), fail
            sds.rename_subobject(h, name)
            by[name] = h
        return lib.get_object(lib.get_data(by[name]))

    for name, mesh, mat, loc, (p, y, r), s, splat in PARTS:
        t = ensure(name, unreal.StaticMeshComponent)
        t.set_editor_property('static_mesh', unreal.load_asset(MESH[mesh]))
        t.set_editor_property('override_materials', [unreal.load_asset(mat)])
        t.set_editor_property('relative_location', unreal.Vector(*loc))
        t.set_editor_property('relative_rotation', unreal.Rotator(roll=r, pitch=p, yaw=y))
        t.set_editor_property('relative_scale3d', unreal.Vector(s, s, s))
        t.set_editor_property('visible', False)          # every part sleeps until an event shows it
        t.set_editor_property('cast_shadow', False)
        t.set_collision_profile_name('NoCollision')      # never blocks play
        if splat:
            t.set_editor_property('render_custom_depth', True)   # stencil 5 = sand (the pp lane's sand pass)
            t.set_editor_property('custom_depth_stencil_value', 5)
        t.set_editor_property('bounds_scale', 1.0)
    counts = {}
    for tag, loc, yaw, s in SITES:
        k = counts[tag] = counts.get(tag, -1) + 1
        t = ensure(f"{tag.replace('Site.', 'Site_').replace('.', '_')}{k}", unreal.SceneComponent)
        t.set_editor_property('component_tags', [tag])
        t.set_editor_property('relative_location', unreal.Vector(*loc))
        t.set_editor_property('relative_rotation', unreal.Rotator(roll=0, pitch=0, yaw=yaw))
        t.set_editor_property('relative_scale3d', unreal.Vector(s, s, s))
    smc = unreal.StaticMeshComponent
    ensure_vars_nc(BP, [('Director', T(unreal.load_class(None, DIR_C)), '', 'Ambience', False),
                        ('GameInst', T(unreal.load_class(None, GI_C)), '', 'Ambience', False),
                        ('Nightmare', T(unreal.load_class(None, NM_C)), '', 'Ambience', False),
                        ('Active', T(smc), '', 'Ambience', False),
                        ('Beat', T('int'), '-1', 'Ambience', False), ('Days', T('int'), '0', 'Ambience', False),
                        ('Level', T('real'), '0.0', 'Ambience', False), ('StillTime', T('int'), '0', 'Ambience', False),
                        ('bAbsorbing', T('bool'), 'false', 'Ambience', False),
                        ('ActiveSound', T(unreal.AudioComponent), '', 'Ambience', False),
                        ('AbsorbSound', T(unreal.AudioComponent), '', 'Ambience', False),
                        ('Deck', BEL.get_array_type(T('name')), '', 'Ambience', True)])
    for name, (ins, outs, pure) in SIGS.items():
        if name not in [str(n) for n in BEL.list_graph_names(unreal.load_asset(BP))]:
            Graph.function(BP, name, pure=pure, inputs=sig_types(ins), outputs=sig_types(outs))
    compile_save(BP, {'Deck': DECK})
    print('assets ok')


# ---------------------------------------------------------------- helpers
def fn(name):
    g = Graph.function(BP, name)
    return g, g.at(entry_node(g), 0, 0)


def ret(g, x, y=0):
    return g.at(result_node(g), x, y)


def now(g, x, y):
    return fcall(g, f'{GS}:GetTimeSeconds', x, y)


def timer(g, name, x, y, seconds=None, loop=False):
    n = fcall(g, f'{KSL}:K2_SetTimer', x, y, FunctionName=name, bLooping='true' if loop else 'false')
    if isinstance(seconds, (int, float)):
        val(n, 'Time', seconds)
    elif seconds is not None:
        feed(n, Time=seconds)
    return n


def dir_field(g, var, x, y):
    return field(g, mget(g, 'Director', x - 220, y), var, DIR_C, x, y)


def helpers():
    # UpdateState: is the room live (the player's own camera, a beat running, no rollover, not the battle or payoff)?
    g, e = fn('UpdateState')
    okd = fcall(g, f'{KSL}:IsValid', 200, 200, Object=mget(g, 'Director', 0, 200))
    okg = fcall(g, f'{KSL}:IsValid', 200, 320, Object=mget(g, 'GameInst', 0, 320))
    br = g.branch(500, 0)
    feed(br, Condition=fcall(g, f'{KML}:BooleanAND', 380, 240, A=okd, B=okg))
    beat = dir_field(g, 'BeatIndex', 700, 300)
    sb = mset(g, 'Beat', 800, 0, po(beat))
    dc = field(g, mget(g, 'GameInst', 760, 520), 'DayCount', GI_C, 980, 520)
    days = fcall(g, f'{KML}:Clamp', 1180, 520, Value=fcall(g, f'{KML}:Subtract_IntInt', 1000, 620, A=po(dc), B=18), Min=0, Max=5)
    sd = mset(g, 'Days', 1100, 0, po(days))
    lv = fcall(g, f'{KML}:FClamp', 1500, 520, Min=0.0, Max=1.0, Value=fcall(
        g, f'{KML}:Add_DoubleDouble', 1350, 620,
        A=fcall(g, f'{KML}:Multiply_DoubleDouble', 1200, 700, A=fcall(g, f'{KML}:Conv_IntToDouble', 1050, 760, InInt=po(beat)), B=0.07),
        B=fcall(g, f'{KML}:Multiply_DoubleDouble', 1200, 820, A=fcall(g, f'{KML}:Conv_IntToDouble', 1050, 880, InInt=po(days)), B=0.12)))
    sl = mset(g, 'Level', 1400, 0, po(lv))
    pc = fcall(g, f'{GS}:GetPlayerController', 1500, 1000, PlayerIndex=0)
    own = fcall(g, f'{KML}:EqualEqual_ObjectObject', 1800, 1000, A=fcall(g, '/Script/Engine.Controller:GetViewTarget', 1650, 1000, self=po(pc)),
                B=fcall(g, f'{GS}:GetPlayerPawn', 1650, 1120, PlayerIndex=0))
    live = fcall(g, f'{KML}:BooleanAND', 2100, 700,
                 A=fcall(g, f'{KML}:BooleanAND', 1950, 620,
                         A=fcall(g, f'{KML}:GreaterEqual_IntInt', 1800, 560, A=po(beat), B=0),
                         B=fcall(g, f'{KML}:Not_PreBool', 1800, 660, A=dir_field(g, 'bRollingOver', 1650, 740))),
                 B=fcall(g, f'{KML}:BooleanAND', 1950, 900, A=own,
                         B=fcall(g, f'{KML}:BooleanAND', 1800, 860,
                                 A=fcall(g, f'{KML}:NotEqual_IntInt', 1650, 860, A=po(beat), B=8),
                                 B=fcall(g, f'{KML}:NotEqual_IntInt', 1650, 940, A=po(beat), B=9))))
    r1 = ret(g, 1800)
    feed(r1, Live=live)
    r0 = g.at(g.ed.add_return_node(), 800, -200)
    val(r0, 'Live', 'false')
    go(e, br)
    go(br, sb)
    go(br, r0, 'else')
    chain(sb, sd, sl, r1)
    box(g, 'Read the game', '', [e, br, sb, sd, sl, r1, r0], 'state')

    # Rearm(Seconds): the next Step after this event plus a gap that shrinks as the story and the failed days pile up
    g, e = fn('Rearm')
    lvl = mget(g, 'Level', 0, 300)
    gap = fcall(g, f'{KML}:RandomFloatInRange', 400, 300, Min=fcall(g, f'{KML}:Lerp', 200, 260, A=22.0, B=6.0, Alpha=lvl),
                Max=fcall(g, f'{KML}:Lerp', 200, 420, A=32.0, B=10.0, Alpha=lvl))
    t = timer(g, 'Step', 700, 0, fcall(g, f'{KML}:Add_DoubleDouble', 560, 200, A=po(e, 'Seconds'), B=gap))
    go(e, t)
    box(g, 'Next event', '', [e, lvl, gap, t], 'sched')

    g, e = fn('Retry')
    t = timer(g, 'Step', 300, 0, 0.25)
    go(e, t)
    box(g, 'Draw again', '', [e, t], 'sched')

    # Play: move a sleeping part to its site, wake it, start its SandEvent (X, now, Seconds, W), then Rearm(Total)
    g, e = fn('Play')
    part = po(e, 'Part')
    st = fcall(g, f'{SCENE}:K2_SetWorldTransform', 300, 0, self=part, NewTransform=po(e, 'Where'))
    vis = fcall(g, f'{SCENE}:SetVisibility', 600, 0, self=part, bNewVisibility='true')
    ev = fcall(g, f'{PRIM}:SetVectorParameterForCustomPrimitiveData', 900, 0, self=part, ParameterName='SandEvent',
               Value=fcall(g, f'{KML}:MakeVector4', 700, 260, X=po(e, 'X'), Y=now(g, 500, 340), Z=po(e, 'Seconds'), W=po(e, 'W')))
    sa = mset(g, 'Active', 1200, 0, part)
    re = fcall(g, SELF('Rearm'), 1500, 0, Seconds=po(e, 'Total'))
    chain(e, st, vis, ev, sa, re)
    box(g, 'Wake a part', '', [e, st, vis, ev, sa, re], 'sched')

    # Site(Tag): a random scene component with that tag, as a world transform
    g, e = fn('Site')
    comps = fcall(g, f'{ACT}:GetComponentsByTag', 200, 200, ComponentClass=f'{SCENE}', Tag=po(e, 'Tag'))
    rnd = fcall(g, f'{KAL}:Array_Random', 500, 200, TargetArray=po(comps))
    cast = make(g, 800, 0, 'CastToSceneComponent')
    feed(cast, Object=po(rnd, 'OutItem') if 'OutItem' in [str(PIN.get_pin_name(p)) for p in BEL.list_output_pins(rnd)] else po(rnd))
    r = ret(g, 1300)
    feed(r, Where=fcall(g, f'{SCENE}:K2_GetComponentToWorld', 1050, 200, self=as_pin(cast)))
    seq(e, comps, rnd, cast, r)
    box(g, 'Pick a site', '', [e, comps, rnd, cast, r], 'sched')

    # Chance(Base, PerDay): a coin that lands more often on each failed day
    g, e = fn('Chance')
    g.ed.set_is_pure_function(True)
    w = fcall(g, f'{KML}:Add_DoubleDouble', 400, 200, A=po(e, 'Base'), B=fcall(
        g, f'{KML}:Multiply_DoubleDouble', 250, 300, A=po(e, 'PerDay'),
        B=fcall(g, f'{KML}:Conv_IntToDouble', 100, 400, InInt=mget(g, 'Days', -100, 400))))
    r = ret(g, 800)
    feed(r, Yes=fcall(g, f'{KML}:RandomBoolWithWeight', 600, 200, Weight=w))
    go(e, r)
    box(g, 'Weighted coin', '', [e, w, r], 'state')

    g, e = fn('InBeats')
    b = mget(g, 'Beat', 0, 300)
    r = ret(g, 700)
    feed(r, Yes=fcall(g, f'{KML}:BooleanAND', 500, 200, A=fcall(g, f'{KML}:GreaterEqual_IntInt', 300, 160, A=b, B=po(e, 'Min')),
                      B=fcall(g, f'{KML}:LessEqual_IntInt', 300, 300, A=b, B=po(e, 'Max'))))
    go(e, r)
    box(g, 'Beat window', '', [e, b, r], 'state')

    # CrumbleActive: the shown object falls back into sand (SandEvent from 0 to 1 over 2.4 s)
    g, e = fn('CrumbleActive')
    a = mget(g, 'Active', 0, 300)
    br = g.branch(300, 0)
    feed(br, Condition=fcall(g, f'{KSL}:IsValid', 160, 200, Object=a))
    ev = fcall(g, f'{PRIM}:SetVectorParameterForCustomPrimitiveData', 600, 0, self=a, ParameterName='SandEvent',
               Value=fcall(g, f'{KML}:MakeVector4', 400, 260, X=0.0, Y=now(g, 200, 400), Z=2.4, W=1.0))
    # the suit bursts, smaller parts crumble (a branch: SelectObject's wildcard pins take no asset defaults)
    pick = g.branch(900, 0)
    feed(pick, Condition=fcall(g, f'{KML}:EqualEqual_ObjectObject', 750, 300, A=mget(g, 'Active', 600, 300), B=mget(g, 'Suit', 600, 400)))
    cs = fcall(g, f'{GSA}:SpawnSoundAttached', 1200, -150, Sound=SND['Burst'], AttachToComponent=mget(g, 'Active', 1050, 100))
    cc = fcall(g, f'{GSA}:SpawnSoundAttached', 1200, 250, Sound=SND['Crumble'], AttachToComponent=mget(g, 'Active', 1050, 500))
    go(e, br)
    chain(br, ev, pick, cs)
    go(pick, cc, 'else')
    box(g, 'Crumble to sand', '', [e, a, br, ev, pick, cs, cc], 'amb')

    g, e = fn('HideAbsorb')
    h = fcall(g, f'{SCENE}:SetVisibility', 300, 0, self=mget(g, 'Absorb', 100, 200), bNewVisibility='false')
    go(e, h)
    box(g, 'Feet bloom gone', '', [e, h], 'amb')

    # EndGlimpse: the Nightmare goes again, unless the director has staged it since (T7 on)
    g, e = fn('EndGlimpse')
    nm = mget(g, 'Nightmare', 0, 300)
    br = g.branch(500, 0)
    feed(br, Condition=fcall(g, f'{KML}:BooleanAND', 350, 200, A=fcall(g, f'{KSL}:IsValid', 200, 200, Object=nm),
                             B=fcall(g, f'{KML}:LessEqual_IntInt', 200, 320, A=dir_field(g, 'BeatIndex', 60, 420), B=6)))
    va = fcall(g, f'{NM_C}:Vanish', 800, 0, self=nm)
    bs = fcall(g, f'{GSA}:SpawnSoundAtLocation', 1100, 0, Sound=SND['Burst'],
               Location=fcall(g, f'{ACT}:K2_GetActorLocation', 950, 250, self=mget(g, 'Nightmare', 800, 250)))
    go(e, br)
    chain(br, va, bs)
    box(g, 'Glimpse over', '', [e, nm, br, va, bs], 'fore')

    # SleeveJerk (looping 0.08 s while the sleeve shows): now and then a jerk off its rest pose, else back to rest
    g, e = fn('SleeveJerk')
    site = fcall(g, SELF('Site'), 200, 0, Tag='Site.Sleeve')
    rest = fcall(g, f'{KML}:BreakTransform', 450, 300, InTransform=po(site, 'Where'))
    jerk = fcall(g, f'{KML}:MakeRotator', 450, 500, Roll=fcall(g, f'{KML}:RandomFloatInRange', 250, 520, Min=-9.0, Max=9.0),
                 Pitch=fcall(g, f'{KML}:RandomFloatInRange', 250, 620, Min=-4.0, Max=4.0),
                 Yaw=fcall(g, f'{KML}:RandomFloatInRange', 250, 720, Min=-7.0, Max=7.0))
    pick = fcall(g, f'{KML}:SelectRotator', 900, 400, A=fcall(g, f'{KML}:ComposeRotators', 700, 460, A=jerk, B=po(rest, 'Rotation')),
                 B=po(rest, 'Rotation'), bPickA=fcall(g, f'{KML}:RandomBoolWithWeight', 700, 600, Weight=0.35))
    rot = fcall(g, f'{SCENE}:K2_SetWorldRotation', 1150, 0, self=mget(g, 'Sleeve', 900, 260), NewRotation=pick)
    chain(e, site, rot)
    box(g, 'Sleeve twitch', '', [e, site, rest, jerk, pick, rot], 'fore')
    compile_save(BP)
    print('helpers ok')


# ---------------------------------------------------------------- events
def play(g, part, where, x, secs, w, total, px, py=0):
    n = fcall(g, SELF('Play'), px, py, Part=mget(g, part, px - 200, py + 200), Where=where)
    for pin, v in (('X', x), ('Seconds', secs), ('W', w), ('Total', total)):
        feed(n, **{pin: v}) if not isinstance(v, (int, float)) else val(n, pin, v)
    return n


def sfx(g, key, part, x, y, vol=1.0, store=None):
    """A sand sound on a part (one-shots end by themselves; loops are kept in `store` so Step / WatchStill fade them).
    Returns (first, last) exec nodes."""
    n = fcall(g, f'{GSA}:SpawnSoundAttached', x, y, Sound=SND[key], AttachToComponent=mget(g, part, x - 150, y + 260))
    val(n, 'VolumeMultiplier', vol)
    if not store:
        return n, n
    st = mset(g, store, x + 300, y, po(n, 'ReturnValue'))
    go(n, st)
    return n, st


def fade(g, var, x, y, nxt):
    """Fade a stored loop out if it is playing, then continue at nxt. Returns the entry branch."""
    br = g.branch(x, y)
    a = mget(g, var, x - 150, y + 200)
    feed(br, Condition=fcall(g, f'{KSL}:IsValid', x - 100, y + 140, Object=a))
    f = fcall(g, f'{AUC}:FadeOut', x + 250, y, self=a, FadeOutDuration=0.6, FadeVolumeLevel=0.0)
    go(br, f)
    if nxt:
        go(f, nxt)
        go(br, nxt, 'else')
    return br


def site(g, tag, x, y):
    return fcall(g, SELF('Site'), x, y, Tag=tag)


def gate(g, e, cond, x=400):
    """Branch on cond: true runs on, false draws again. Returns (branch, retry)."""
    br = g.branch(x, 0)
    feed(br, Condition=cond)
    rt = fcall(g, SELF('Retry'), x + 300, 300)
    go(br, rt, 'else')
    return br, rt


def chance(g, base, per_day, x, y):
    return fcall(g, SELF('Chance'), x, y, Base=base, PerDay=per_day)


def events():
    # ---- ambient ----
    g, e = fn('Ev_Creep')        # goo creeps out from under the wardrobe (until it falls at T6) or the door (until T7)
    beat = mget(g, 'Beat', 0, 400)
    br, rt = gate(g, e, fcall(g, f'{KML}:Less_IntInt', 200, 300, A=beat, B=7))
    tag = fcall(g, f'{KML}:SelectName', 500, 500, A='Site.Creep.Wardrobe', B='Site.Creep.Door', bPickA=fcall(
        g, f'{KML}:BooleanAND', 350, 560, A=fcall(g, f'{KML}:Less_IntInt', 200, 520, A=beat, B=6), B=fcall(g, f'{KML}:RandomBool', 200, 640)))
    s = fcall(g, SELF('Site'), 700, 0)
    feed(s, Tag=tag)
    secs = fcall(g, f'{KML}:RandomFloatInRange', 900, 400, Min=9.0, Max=13.0)
    p = play(g, 'Bloom', po(s, 'Where'), 1.6, secs, 0.0, secs, 1100)
    a0, a1 = sfx(g, 'Shift', 'Bloom', 1400, 0)
    go(e, br)
    chain(br, s, p, a0)
    box(g, 'Creep from under', '', [e, beat, br, rt, tag, s, secs, p, a0], 'amb')

    g, e = fn('Ev_Pile')          # a pile wells up against a wall, slumps and drops its grains
    s = site(g, 'Site.Pile', 250, 0)
    secs = fcall(g, f'{KML}:RandomFloatInRange', 400, 400, Min=9.0, Max=12.0)
    p = play(g, 'Bloom', po(s, 'Where'), 0.7, secs, 1.0, secs, 600)
    a0, a1 = sfx(g, 'Shift', 'Bloom', 900, 0)
    chain(e, s, p, a0)
    box(g, 'Pile and slump', '', [e, s, secs, p, a0], 'amb')

    g, e = fn('Ev_Trickle')       # a thin pour from a ceiling corner onto the boards
    s = site(g, 'Site.Trickle', 250, 0)
    p = play(g, 'Trickle', po(s, 'Where'), 0.0, 0.0, 0.0, fcall(g, f'{KML}:RandomFloatInRange', 400, 400, Min=6.0, Max=10.0), 600)
    a0, a1 = sfx(g, 'Trickle_Loop_01', 'Trickle', 900, 0, store='ActiveSound')
    chain(e, s, p, a0)
    box(g, 'Ceiling trickle', '', [e, s, p, a0, a1], 'amb')

    g, e = fn('Ev_Drift')         # grains hang and sink in the moonbeam from the bay
    me_ = mget(g, 'Drift', 0, 300)
    p = play(g, 'Drift', po(fcall(g, f'{SCENE}:K2_GetComponentToWorld', 200, 300, self=me_)), 0.0, 0.0, 0.0, 12.0, 500)
    a0, a1 = sfx(g, 'Hiss_Loop_01', 'Drift', 800, 0, vol=0.4, store='ActiveSound')
    chain(e, p, a0)
    box(g, 'Grains in the beam', '', [e, me_, p, a0, a1], 'amb')

    # ---- foreshadowing (docs/design/world/foreshadowing.md) ----
    g, e = fn('Ev_ClockDrip')     # time leaks: sand runs out of the wall clock onto the mantel
    br, rt = gate(g, e, chance(g, 0.5, 0.1, 200, 300))
    me_ = mget(g, 'ClockDrip', 400, 400)
    p = play(g, 'ClockDrip', po(fcall(g, f'{SCENE}:K2_GetComponentToWorld', 600, 400, self=me_)), 0.0, 0.0, 0.0,
             fcall(g, f'{KML}:RandomFloatInRange', 800, 500, Min=5.0, Max=8.0), 900)
    a0, a1 = sfx(g, 'Trickle_Loop_01', 'ClockDrip', 1200, 0, vol=0.7, store='ActiveSound')
    go(e, br)
    chain(br, p, a0)
    box(g, 'Clock leaks sand', '', [e, br, rt, me_, p, a0, a1], 'fore')

    g, e = fn('Ev_Hourglass')     # an hourglass of sand forms on the mantel, holds, crumbles
    br, rt = gate(g, e, chance(g, 0.3, 0.1, 200, 300))
    s = site(g, 'Site.Hourglass', 700, 0)
    p = play(g, 'Hourglass', po(s, 'Where'), 1.0, 1.6, 0.0, 9.5, 1000)
    t = timer(g, 'CrumbleActive', 1300, 0, 5.0)
    go(e, br)
    chain(br, s, p, t)
    box(g, 'Hourglass forms', '', [e, br, rt, s, p, t], 'fore')

    g, e = fn('Ev_Sleeve')        # a shirt sleeve caught in the wardrobe doors twitches (T0-T5, before it falls)
    cond = fcall(g, f'{KML}:BooleanAND', 300, 300, A=fcall(g, SELF('InBeats'), 100, 260, Min=0, Max=5),
                 B=chance(g, 0.35, 0.15, 100, 400))
    br, rt = gate(g, e, cond, 600)
    s = site(g, 'Site.Sleeve', 900, 0)
    p = play(g, 'Sleeve', po(s, 'Where'), 0.0, 0.0, 0.0, 3.5, 1200)
    t = timer(g, 'SleeveJerk', 1500, 0, 0.08, loop=True)
    go(e, br)
    chain(br, s, p, t)
    box(g, 'Sleeve in the gap', '', [e, cond, br, rt, s, p, t], 'fore')

    g, e = fn('Ev_Shirt')         # the T8 shirt as a sand imprint on the boards (T1-T7)
    cond = fcall(g, f'{KML}:BooleanAND', 300, 300, A=fcall(g, SELF('InBeats'), 100, 260, Min=1, Max=7),
                 B=chance(g, 0.35, 0.15, 100, 400))
    br, rt = gate(g, e, cond, 600)
    s = site(g, 'Site.Shirt', 900, 0)
    p = play(g, 'Shirt', po(s, 'Where'), 1.0, 1.6, 0.0, 9.5, 1200)
    a0, a1 = sfx(g, 'Shift', 'Shirt', 1500, 300)
    t = timer(g, 'CrumbleActive', 1800, 0, 5.0)
    go(e, br)
    chain(br, s, p, a0, t)
    box(g, 'Shirt imprint', '', [e, cond, br, rt, s, p, a0, t], 'fore')

    g, e = fn('Ev_Suit')          # the T9 suit stands in sand: from T7 on day one, a beat earlier each failed day
    beat = mget(g, 'Beat', 0, 500)
    early = fcall(g, f'{KML}:Subtract_IntInt', 300, 560, B=fcall(g, f'{KML}:Min', 150, 620, A=mget(g, 'Days', 0, 640), B=4), A=7)  # wire first: operators type their wildcard pins from a link
    cond = fcall(g, f'{KML}:BooleanAND', 500, 300, A=fcall(g, f'{KML}:GreaterEqual_IntInt', 350, 440, A=beat, B=early),
                 B=chance(g, 0.4, 0.15, 300, 300))
    br, rt = gate(g, e, cond, 700)
    s = site(g, 'Site.Suit', 1000, 0)
    p = play(g, 'Suit', po(s, 'Where'), 1.0, 2.2, 0.0, 11.0, 1300)
    a0, a1 = sfx(g, 'Pour', 'Suit', 1600, 300)
    t = timer(g, 'CrumbleActive', 1900, 0, 6.5)
    go(e, br)
    chain(br, s, p, a0, t)
    box(g, 'Suit in sand', '', [e, beat, early, cond, br, rt, s, p, a0, t], 'fore')

    g, e = fn('Ev_Glimpse')       # the Nightmare at the edge of the view for a second (T2-T6)
    nm = mget(g, 'Nightmare', 0, 500)
    cond = fcall(g, f'{KML}:BooleanAND', 450, 300, A=fcall(g, f'{KML}:BooleanAND', 300, 260,
                                                          A=fcall(g, SELF('InBeats'), 100, 220, Min=2, Max=6),
                                                          B=fcall(g, f'{KSL}:IsValid', 100, 340, Object=nm)),
                 B=chance(g, 0.2, 0.2, 250, 420))
    br, rt = gate(g, e, cond, 650)
    s = site(g, 'Site.Glimpse', 900, 0)
    loc = fcall(g, f'{KML}:BreakTransform', 1100, 300, InTransform=po(s, 'Where'))
    cam = fcall(g, f'{GS}:GetPlayerCameraManager', 900, 500, PlayerIndex=0)
    cloc = fcall(g, f'{PCM}:GetCameraLocation', 1100, 500, self=po(cam))
    fwd = fcall(g, f'{KML}:GetForwardVector', 1300, 600, InRot=fcall(g, f'{PCM}:GetCameraRotation', 1100, 600, self=po(cam)))
    d = fcall(g, f'{KML}:Dot_VectorVector', 1500, 500, A=fwd, B=fcall(
        g, f'{KML}:Normal', 1300, 450, A=fcall(g, f'{KML}:Subtract_VectorVector', 1200, 420, A=po(loc, 'Location'), B=cloc)))
    br2 = g.branch(1700, 0)
    feed(br2, Condition=fcall(g, f'{KML}:InRange_FloatFloat', 1600, 300, Value=d, Min=0.35, Max=0.82))
    yaw = fcall(g, f'{KML}:BreakRotator', 1800, 500, InRot=fcall(g, f'{KML}:FindLookAtRotation', 1650, 560,
                                                                    Start=po(loc, 'Location'), Target=cloc))
    ap = fcall(g, f'{NM_C}:Appear', 2000, 0, self=nm, Location=po(loc, 'Location'), Yaw=po(yaw, 'Yaw'))
    t = timer(g, 'EndGlimpse', 2300, 0, fcall(g, f'{KML}:RandomFloatInRange', 2150, 300, Min=1.0, Max=1.6))
    re = fcall(g, SELF('Rearm'), 2600, 0, Seconds=2.0)
    rt2 = fcall(g, SELF('Retry'), 2000, 300)
    go(e, br)
    chain(br, s, br2, ap, t, re)
    go(br2, rt2, 'else')
    box(g, 'Nightmare glimpse', '', [e, nm, cond, br, rt, s, loc, cam, cloc, fwd, d, br2, yaw, ap, t, re, rt2], 'fore')

    # ---- scheduling ----
    g, e = fn('Step')
    a = mget(g, 'Active', 0, 300)
    br = g.branch(300, 0)
    feed(br, Condition=fcall(g, f'{KSL}:IsValid', 150, 200, Object=a))
    hide = fcall(g, f'{SCENE}:SetVisibility', 600, 0, self=a, bNewVisibility='false')
    c1 = fcall(g, f'{KSL}:K2_ClearTimer', 900, 0, FunctionName='SleeveJerk')
    fd = fade(g, 'ActiveSound', 750, -350, c1)
    c2 = fcall(g, f'{KSL}:K2_ClearTimer', 1200, 0, FunctionName='CrumbleActive')
    us = fcall(g, SELF('UpdateState'), 1500, 0)
    live = g.branch(1800, 0)
    feed(live, Condition=po(us, 'Live'))
    pick = fcall(g, f'{KAL}:Array_Random', 2000, 300, TargetArray=mget(g, 'Deck', 1800, 400))
    run = fcall(g, f'{KSL}:K2_SetTimer', 2300, 0, Time=0.05, bLooping='false')
    item = [p for p in BEL.list_output_pins(pick) if str(PIN.get_pin_name(p)) in ('OutItem', 'Item')][0]
    feed(run, FunctionName=fcall(g, '/Script/Engine.KismetStringLibrary:Conv_NameToString', 2150, 300, InName=item))
    idle = timer(g, 'Step', 2100, 400, 3.0)
    go(e, br)
    go(br, hide)
    go(br, fd, 'else')
    go(hide, fd)
    chain(c1, c2, us, live)
    seq(live, pick, run)
    go(live, idle, 'else')
    box(g, 'Next sand event', '', [e, a, br, hide, c1, c2, us, live, pick, run, idle], 'sched')

    # WatchStill (1 Hz): standing still grows a bloom at the feet that the player crawl pulls up the legs
    g, e = fn('WatchStill')
    us = fcall(g, SELF('UpdateState'), 200, 0)
    pawn = fcall(g, f'{GS}:GetPlayerPawn', 200, 400, PlayerIndex=0)
    still = fcall(g, f'{KML}:BooleanAND', 500, 300, A=po(us, 'Live'), B=fcall(
        g, f'{KML}:Less_DoubleDouble', 400, 420, A=fcall(g, f'{KML}:VSize', 300, 500, A=fcall(g, f'{ACT}:GetVelocity', 200, 560, self=po(pawn))), B=5.0))
    br = g.branch(700, 0)
    feed(br, Condition=still)
    inc = mset(g, 'StillTime', 1000, 0, fcall(g, f'{KML}:Add_IntInt', 850, 200, A=mget(g, 'StillTime', 700, 260), B=1))
    thr = fcall(g, f'{KML}:Round', 1150, 400, A=fcall(g, f'{KML}:Lerp', 1000, 450, A=9.0, B=4.0, Alpha=mget(g, 'Level', 850, 500)))
    due = fcall(g, f'{KML}:EqualEqual_IntInt', 1350, 300, A=fcall(g, f'{KML}:Percent_IntInt', 1200, 260,
                                                                   A=mget(g, 'StillTime', 1050, 260), B=30), B=thr)
    br2 = g.branch(1300, 0)
    feed(br2, Condition=due)
    ab = mget(g, 'Absorb', 1400, 600)
    feet = fcall(g, f'{KML}:MakeVector', 1600, 500, Z=0.5)
    pl = fcall(g, f'{KML}:BreakVector', 1450, 700, InVec=fcall(g, f'{ACT}:K2_GetActorLocation', 1300, 760, self=po(pawn)))
    feed(feet, X=po(pl, 'X'), Y=po(pl, 'Y'))
    mv = fcall(g, f'{SCENE}:K2_SetWorldLocation', 1600, 0, self=ab, NewLocation=feet)
    sh = fcall(g, f'{SCENE}:SetVisibility', 1900, 0, self=ab, bNewVisibility='true')
    ev = fcall(g, f'{PRIM}:SetVectorParameterForCustomPrimitiveData', 2200, 0, self=ab, ParameterName='SandEvent',
               Value=fcall(g, f'{KML}:MakeVector4', 2000, 300, X=1.2, Y=now(g, 1850, 360), Z=26.0, W=0.0))
    on = mset(g, 'bAbsorbing', 2500, 0)
    val(on, 'bAbsorbing', 'true')
    h0, h1 = sfx(g, 'Hiss_Loop_01', 'Absorb', 2800, 0, vol=0.4, store='AbsorbSound')
    # moving again: the bloom recedes from where it is (life 0.72 of a 3 s event = its vanish phase), then hides
    rs = mset(g, 'StillTime', 1000, 700)
    val(rs, 'StillTime', 0)
    br3 = g.branch(1300, 900)
    feed(br3, Condition=mget(g, 'bAbsorbing', 1100, 1000))
    ev2 = fcall(g, f'{PRIM}:SetVectorParameterForCustomPrimitiveData', 1600, 900, self=ab, ParameterName='SandEvent',
                Value=fcall(g, f'{KML}:MakeVector4', 1450, 1100, X=1.2, Y=fcall(g, f'{KML}:Subtract_DoubleDouble', 1300, 1150,
                                                                             A=now(g, 1150, 1150), B=2.16), Z=3.0, W=0.0))
    off = mset(g, 'bAbsorbing', 1900, 900)
    val(off, 'bAbsorbing', 'false')
    hid = timer(g, 'HideAbsorb', 2200, 900, 1.0)
    hf = fade(g, 'AbsorbSound', 2650, 900, None)
    chain(e, us, br)
    go(br, inc)
    chain(inc, br2, mv, sh, ev, on, h0)
    go(br, rs, 'else')
    chain(rs, br3, ev2, off, hid, hf)
    box(g, 'Stand still, sink', '', [e, us, pawn, still, br, inc, thr, due, br2, ab, feet, pl, mv, sh, ev, on, rs, br3, ev2, off, hid], 'amb')

    # BeginPlay: find the director, the game instance and the Nightmare once; start the two timers
    g = Graph(BP).clear()   # also drops the template's ghost (disabled) BeginPlay/Tick/Overlap nodes
    bp_ev = g.event('ReceiveBeginPlay', 0, 0)
    fd = fcall(g, f'{GS}:GetActorOfClass', 250, 200, ActorClass=DIR_C)
    c1 = make(g, 500, 0, 'CastToBP_BeatDirector')
    feed(c1, Object=po(fd, 'ReturnValue'))
    s1 = mset(g, 'Director', 800, 0, as_pin(c1))
    gi = fcall(g, f'{GS}:GetGameInstance', 900, 200)
    c2 = make(g, 1100, 0, 'CastToGI_FoA')
    feed(c2, Object=po(gi))
    s2 = mset(g, 'GameInst', 1400, 0, as_pin(c2))
    fn_ = fcall(g, f'{GS}:GetActorOfClass', 1500, 200, ActorClass=NM_C)
    c3 = make(g, 1700, 0, 'CastToBP_Nightmare')
    feed(c3, Object=po(fn_, 'ReturnValue'))
    s3 = mset(g, 'Nightmare', 2000, 0, as_pin(c3))
    t1 = timer(g, 'Step', 2300, 0, 12.0)
    t2 = timer(g, 'WatchStill', 2600, 0, 1.0, loop=True)
    chain(bp_ev, fd, c1, s1, c2, s2, fn_, c3, s3, t1, t2)   # GetGameInstance is pure: off the exec row
    for c, nxt in ((c1, c2), (c2, fn_), (c3, t1)):   # a missing actor skips its lookup, never the timers
        go(c, nxt, 'CastFailed')
    box(g, 'Find the world', '', [bp_ev, fd, c1, s1, gi, c2, s2, fn_, c3, s3, t1, t2], 'sched')
    compile_save(BP)
    print('events ok')


{'assets': assets, 'helpers': helpers, 'events': events}[phase]()
