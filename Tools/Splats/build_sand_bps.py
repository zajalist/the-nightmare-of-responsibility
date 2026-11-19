"""Gameplay Blueprints for the splat sand (docs/mechanics/contract.md, 'VFX (owner: sandvfx)'). Run via ue_remote.py:
  python Tools/Unreal/ue_remote.py Tools/Splats/build_sand_bps.py FOA_SAND_BP=assets     # BPs, components, vars, signatures
  -> Hayba blueprint_compile + asset_save on all four
  python Tools/Unreal/ue_remote.py Tools/Splats/build_sand_bps.py FOA_SAND_BP=graphs_a   # mound, materialize, fx graphs
  -> Hayba blueprint_compile + asset_save on BP_SandMound, BP_SandMaterialize, BP_SandFX
  python Tools/Unreal/ue_remote.py Tools/Splats/build_sand_bps.py FOA_SAND_BP=graphs_b   # the BPL_SandFX graphs
  -> Hayba blueprint_compile + asset_save on BPL_SandFX; BloomSpots via Hayba blueprint_set_defaults (FOA_SAND_BP=spots
     prints them). Python never compiles or saves a Blueprint (editor rules, after two python311 crashes).

No Tick and no dynamic material instances: every event is one SetVectorParameterForCustomPrimitiveData on the splat
component (SandEvent, custom primitive data 0-3), and M_SplatMesh animates it from Time. All zeros = no event.
  BP_SandMound        Erupt(Strength), Settle()                         SandEvent = (strength, now, 2.6 s, calm)
  BP_SandMaterialize  Materialize(Seconds), Dissolve(Seconds), Loop     SandEvent = (from, now, seconds, to);
                                                                        ModeOverride (CPD 4) = Loop ? assemble : BaseMode
  BP_SandFX           Burst(Location, Scale), Step(Location),           pools of 8 + 6 + 4 splat components, round robin;
                      Bloom(Location, Size, Seconds, Crumble)           BloomSpots (class default) = where ambient blooms grow
  BPL_SandFX          SpawnSandBurst(Location, Scale), SpawnSandStep(FootLocation), SpawnSandBloom(Location, Size,
                      Seconds, Crumble), SpawnAmbientBloom(Tier), GetSandFX()
Each pooled one-shot also plays its sand SFX (Audio/SFX/Sand) at the spot.
"""
import os

exec(open('P:/FoA/Tools/Unreal/encounter/enc_graph.py').read())  # noqa: S102  house graph helpers (bp_graph + feed/palette)
import unreal  # noqa: E402

D = '/Game/FoA/VFX/Sand'
V = '/Game/FoA/VFX/Splats'
MOUND, MAT, FX, LIB = f'{D}/BP_SandMound', f'{D}/BP_SandMaterialize', f'{D}/BP_SandFX', f'{D}/BPL_SandFX'
PRIM = '/Script/Engine.PrimitiveComponent'
SCENE = '/Script/Engine.SceneComponent'
COL.update({'sand': unreal.LinearColor(0.30, 0.22, 0.10, 1), 'pool': unreal.LinearColor(0.12, 0.26, 0.16, 1)})
SFX = '/Game/FoA/Audio/SFX/Sand'
MS = '/Game/FoA/Audio/MetaSounds/Sand'   # horror's MetaSound presets (randomised takes), not the raw waves
SOUND = {'Burst': f'{MS}/S_Sand_Burst.S_Sand_Burst', 'Step': f'{MS}/S_Sand_Footstep.S_Sand_Footstep',
         'Bloom': f'{MS}/S_Sand_Shift.S_Sand_Shift'}
AT = unreal.AssetToolsHelpers.get_asset_tools()
phase = os.environ.get('FOA_SAND_BP', 'assets')


TOUCHED = []
_house_box = box


def box(g, title, desc, nodes, kind, pad=40):  # noqa: F811  the user's rule: comment boxes carry a short title only
    c = g.ed.add_comment_to_nodes(title, list(nodes), pad)
    BEL.set_comment_color(c, COL[kind])
    for prop, v in (("font_size", 18), ("comment_bubble_visible_in_details_panel", True), ("color_comment_bubble", True)):
        c.set_editor_property(prop, v)
    return c


def compile_save(bp_path):  # noqa: F811  the house helper compiles from Python: here Hayba does it between phases
    TOUCHED.append(bp_path)


def ensure_vars(bp_path, specs):  # noqa: F811  the house helper without its compile
    bp = unreal.load_asset(bp_path)
    ed = GE.get_graph_editor_by_name(bp, 'EventGraph')
    have = [str(n) for n in BEL.list_member_variable_names(bp)]
    for name, t, val, cat, editable in specs:
        if name not in have:
            assert ed.add_member_variable(name, t, val), f"add var {name}"
        BEL.set_blueprint_variable_category(bp, name, cat)
        BEL.set_blueprint_variable_instance_editable(bp, name, editable)


def make_bp(path, parent, factory=unreal.BlueprintFactory):
    name = path.rsplit('/', 1)[1]
    bp = unreal.load_asset(f'{path}.{name}')
    if not bp:
        fac = factory()
        if factory is unreal.BlueprintFactory:
            fac.set_editor_property('parent_class', parent)
        bp = AT.create_asset(name, D, unreal.Blueprint, fac)
    assert bp, path
    unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(bp)
    return bp


def components(bp, specs):
    """specs: (name, StaticMesh path, material path, tags). Adds missing static-mesh components under the root and sets
    their templates: splats never cast shadows or collide."""
    sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    lib = unreal.SubobjectDataBlueprintFunctionLibrary
    by_name = {str(lib.get_variable_name(lib.get_data(h))): h for h in sds.k2_gather_subobject_data_for_blueprint(bp)}
    root = by_name.get('DefaultSceneRoot') or sds.k2_gather_subobject_data_for_blueprint(bp)[0]
    for name, mesh, mat, tags, splat in specs:
        if name not in by_name:
            h, fail = sds.add_new_subobject(unreal.AddNewSubobjectParams(parent_handle=root, new_class=unreal.StaticMeshComponent,
                                                                         blueprint_context=bp))
            assert not str(fail), fail
            sds.rename_subobject(h, name)
            by_name[name] = h
        t = lib.get_object(lib.get_data(by_name[name]))
        t.set_editor_property('static_mesh', unreal.load_asset(mesh))
        t.set_editor_property('override_materials', [unreal.load_asset(mat)])
        t.set_editor_property('component_tags', list(tags))
        t.set_editor_property('render_custom_depth', True)        # stencil 5 = sand (the pp lane's sand-only pass)
        t.set_editor_property('custom_depth_stencil_value', 5)
        if splat:
            t.set_editor_property('cast_shadow', False)
            t.set_collision_profile_name('NoCollision')


def assets():
    T = ptype
    bp = make_bp(MOUND, unreal.Actor)
    components(bp, [('Mound', '/Game/FoA/Procedural/SM_SandMound_A/SM_SandMound_A/StaticMeshes/SM_SandMound_A',
                     '/Game/FoA/Materials/MI_DarkSand_Black', (), False),
                    ('Splats', f'{V}/Meshes/SM_SandMoundSplats_A', f'{V}/Instances/MI_Sand_Mound_OnCommode', ('Splats',), True)])
    compile_save(MOUND)
    bp = make_bp(MAT, unreal.Actor)
    components(bp, [('Splats', f'{V}/Meshes/fear_of_adulthood_clock', f'{V}/Instances/MI_Sand_Clock', ('Splats',), True)])
    ensure_vars(MAT, [('Loop', T('bool'), 'true', 'Sand', True), ('BaseMode', T('real'), '3.0', 'Sand', True),
                      ('DissolveAmount', T('real'), '0.0', 'Sand', True)])
    BEL.set_blueprint_variable_expose_to_cinematics(unreal.load_asset(MAT), 'DissolveAmount', True)  # Sequencer keys it
    compile_save(MAT)
    bp = make_bp(FX, unreal.Actor)
    components(bp, [(f'Burst{i}', f'{V}/Meshes/SM_SandBurst/SM_SandBurst/StaticMeshes/SM_SandBurst', f'{V}/Instances/MI_Sand_Burst', ('Burst',), True) for i in range(8)]
               + [(f'Step{i}', f'{V}/Meshes/SM_SandBurst/SM_SandBurst/StaticMeshes/SM_SandBurst', f'{V}/Instances/MI_Sand_Step', ('Step',), True) for i in range(6)]
               + [(f'Bloom{i}', f'{V}/Meshes/SM_SandMoundSplats_B', f'{V}/Instances/MI_Sand_Bloom', ('Bloom',), True) for i in range(4)])
    ensure_vars(FX, [('Next', T('int'), '0', 'Sand', False),
                     ('BloomSpots', BEL.get_array_type(T(unreal.Vector)), '', 'Sand', True)])
    compile_save(FX)
    make_bp(LIB, None, unreal.BlueprintFunctionLibraryFactory)
    compile_save(LIB)
    signatures()
    print('assets ok; Hayba compile + save:', sorted(set(TOUCHED)))


def bloom_spots():
    """Where ambient blooms grow (floor z 0.3): two room corners, two wall bases, under the bed, under the desk and on
    the desk top, from the hand-placed furniture's bounds (read only, never moved)."""
    spots = [unreal.Vector(345.0, 270.0, 0.3), unreal.Vector(-345.0, -270.0, 0.3),      # corners
             unreal.Vector(40.0, 285.0, 0.3), unreal.Vector(360.0, -170.0, 0.3)]        # north and east wall bases
    by = {a.get_actor_label(): a for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()}
    for label, top in (('Bed', False), ('Desk', False), ('Desk', True)):
        a = by.get(label)
        if not a:
            continue
        o, e = a.get_actor_bounds(True)
        spots.append(unreal.Vector(o.x, o.y, o.z + e.z + 0.3) if top else unreal.Vector(o.x, o.y, 0.3))
    print('bloom spots', [(round(v.x), round(v.y), round(v.z)) for v in spots])
    return spots


def sound(g, key, loc, x, y, volume=1.0):
    """The pool's SFX at the spot (one-shot, no component)."""
    return fcall(g, f'{GS}:PlaySoundAtLocation', x, y, Sound=SOUND[key], Location=loc, VolumeMultiplier=volume)


def v4(g, x, y, **xyzw):
    return fcall(g, f'{KML}:MakeVector4', x, y, **xyzw)


def set_event(g, comp, value, x, y):
    """SandEvent on the splat component's custom primitive data (M_SplatMesh reads it, no MID)."""
    return fcall(g, f'{PRIM}:SetVectorParameterForCustomPrimitiveData', x, y, self=comp, ParameterName='SandEvent', Value=value)


def now(g, x, y):
    return fcall(g, f'{GS}:GetTimeSeconds', x, y)


def signatures():
    """Every function with its parameters (bodies empty), so the graph phases can call them on compiled classes."""
    T = ptype
    fx_t = T(unreal.load_class(None, f'{FX}.BP_SandFX_C'))
    sig = {MOUND: [('Erupt', [('Strength', T('real'))], []), ('Settle', [], [])],
           MAT: [('Materialize', [('Seconds', T('real'))], []), ('Dissolve', [('Seconds', T('real'))], [])],  # SetDissolveAmount: build_clock_wakeup.py
           FX: [('Play', [('Tag', T('name')), ('Location', T(unreal.Vector)), ('Scale', T('real')), ('Strength', T('real')),
                          ('Duration', T('real')), ('Extra', T('real'))], []),
                ('Burst', [('Location', T(unreal.Vector)), ('Scale', T('real'))], []),
                ('Step', [('Location', T(unreal.Vector))], []),
                ('Bloom', [('Location', T(unreal.Vector)), ('Size', T('real')), ('Seconds', T('real')), ('Crumble', T('bool'))], [])],
           LIB: [('GetSandFX', [], [('SandFX', fx_t)]),
                 ('SpawnSandBurst', [('Location', T(unreal.Vector)), ('Scale', T('real'))], []),
                 ('SpawnSandStep', [('FootLocation', T(unreal.Vector))], []),
                 ('SpawnSandBloom', [('Location', T(unreal.Vector)), ('Size', T('real')), ('Seconds', T('real')),
                                     ('Crumble', T('bool'))], []),
                 ('SpawnAmbientBloom', [('Tier', T('int'))], [])]}
    for bp, fns in sig.items():
        for name, ins, outs in fns:
            drop_function(bp, name)
            Graph.function(bp, name, inputs=ins, outputs=outs)


def graphs_a():
    T = ptype
    # ---- BP_SandMound ----
    for f in ('Erupt', 'Settle'):
        drop_function(MOUND, f)
    Graph.function(MOUND, 'Erupt', inputs=[('Strength', T('real'))])
    Graph.function(MOUND, 'Settle')
    g = Graph(MOUND, 'Erupt')
    e = g.at(entry_node(g), 0, 0)
    ev = v4(g, 300, 160, X=po(e, 'Strength'), Y=now(g, 60, 220), Z=2.6, W=0)
    s = set_event(g, mget(g, 'Splats', 300, 340), ev, 600, 0)
    go(e, s)
    box(g, 'Erupt', 'Launch the grains ballistically; they land and slide home in 2.6 s (shader, no Tick)', [e, ev, s], 'sand')
    g = Graph(MOUND, 'Settle')
    e = g.at(entry_node(g), 0, 0)
    s = set_event(g, mget(g, 'Splats', 300, 200), v4(g, 300, 120, X=0, Y=0, Z=0, W=1), 600, 0)
    go(e, s)
    box(g, 'Settle', 'Calm = 1: avalanches, breathing, saltation and wisps go still. Erupt wakes the mound', [e, s], 'sand')
    compile_save(MOUND)

    # ---- BP_SandMaterialize ----
    for f in ('Materialize', 'Dissolve'):
        drop_function(MAT, f)
    Graph.function(MAT, 'Materialize', inputs=[('Seconds', T('real'))])
    Graph.function(MAT, 'Dissolve', inputs=[('Seconds', T('real'))])
    for name, frm, to, why in (('Materialize', 1, 0, 'Grains rise out of the sand and form the object over Seconds'),
                               ('Dissolve', 0, 1, 'The object crumbles top-first into falling sand over Seconds')):
        g = Graph(MAT, name)
        e = g.at(entry_node(g), 0, 0)
        s = set_event(g, mget(g, 'Splats', 300, 360), v4(g, 300, 160, X=frm, Y=now(g, 60, 220), Z=po(e, 'Seconds'), W=to), 620, 0)
        go(e, s)
        box(g, name, why + ' (SandEvent = from, now, seconds, to)', [e, s], 'sand')
    # SetDissolveAmount (Sequencer's setter for DissolveAmount) is owned by Tools/Splats/build_clock_wakeup.py since
    # 2026-11-07: it also shows the wake-up clock's sand pile. Not rebuilt here, so a rerun never drops the pile.
    g = Graph(MAT, 'UserConstructionScript')
    old = [n for n in g.ed.list_all_nodes() if not isinstance(n, unreal.K2Node_FunctionEntry)]  # rerun-safe, keep the entry
    if old:
        g.ed.remove_nodes(old)
    e = g.at(entry_node(g), 0, 0)
    sel = fcall(g, f'{KML}:SelectFloat', 420, 160, A=3.0, B=fcall(g, f'{KML}:Add_DoubleDouble', 200, 260,
                                                                  A=mget(g, 'BaseMode', 0, 300), B=1.0),
                bPickA=mget(g, 'Loop', 200, 160))
    s = fcall(g, f'{PRIM}:SetScalarParameterForCustomPrimitiveData', 700, 0, self=mget(g, 'Splats', 420, 360),
              ParameterName='ModeOverride', Value=sel)
    go(e, s)
    box(g, 'Loop toggle', 'ModeOverride (custom primitive data 4) = mode + 1: Loop plays the assemble loop, else BaseMode '
        '(3 static, 4 gallop)', [e, sel, s], 'sand')
    compile_save(MAT)

    # ---- BP_SandFX: pooled bursts ----
    for f in ('Play', 'Burst', 'Step'):
        drop_function(FX, f)
    Graph.function(FX, 'Play', inputs=[('Tag', T('name')), ('Location', T(unreal.Vector)), ('Scale', T('real')),
                                       ('Strength', T('real')), ('Duration', T('real')), ('Extra', T('real'))])
    Graph.function(FX, 'Burst', inputs=[('Location', T(unreal.Vector)), ('Scale', T('real'))])
    Graph.function(FX, 'Step', inputs=[('Location', T(unreal.Vector))])
    Graph.function(FX, 'Bloom', inputs=[('Location', T(unreal.Vector)), ('Size', T('real')), ('Seconds', T('real')),
                                        ('Crumble', T('bool'))])
    g = Graph(FX, 'Play')
    e = g.at(entry_node(g), 0, 0)
    comps = fcall(g, '/Script/Engine.Actor:GetComponentsByTag', 220, 200, ComponentClass='/Script/Engine.StaticMeshComponent',
                  Tag=po(e, 'Tag'))
    idx = fcall(g, f'{KML}:Percent_IntInt', 520, 300, A=mget(g, 'Next', 300, 380),
                B=fcall(g, f'{KAL}:Array_Length', 300, 460, TargetArray=po(comps, 'ReturnValue')))
    item = fcall(g, f'{KAL}:Array_Get', 760, 200, TargetArray=po(comps, 'ReturnValue'), Index=idx)
    cast = make(g, 1000, 0, 'CastToStaticMeshComponent')
    feed(cast, Object=po(item, 'Item'))
    comp = po(cast, 'AsStaticMeshComponent')
    loc = fcall(g, f'{SCENE}:K2_SetWorldLocation', 1300, 0, self=comp, NewLocation=po(e, 'Location'))
    scl = fcall(g, f'{SCENE}:SetWorldScale3D', 1600, 0, self=comp,
                NewScale=fcall(g, f'{KML}:MakeVector', 1400, 260, X=po(e, 'Scale'), Y=po(e, 'Scale'), Z=po(e, 'Scale')))
    evt = set_event(g, comp, v4(g, 1650, 300, X=po(e, 'Strength'), Y=now(g, 1450, 420), Z=po(e, 'Duration'),
                                W=po(e, 'Extra')), 1900, 0)
    nxt = mset(g, 'Next', 2200, 0, fcall(g, f'{KML}:Add_IntInt', 2000, 260, A=mget(g, 'Next', 1800, 300), B=1))
    chain(e, cast, loc, scl, evt, nxt)
    box(g, 'Round-robin pool', 'Next component with the tag: move it, scale it, start its SandEvent; nothing spawns',
        [e, comps, idx, item, cast, loc, scl, evt, nxt], 'pool')
    play = self_call(FX, 'Play')
    for name, tag, scale, dur, vol in (('Burst', 'Burst', None, 1.4, 1.0), ('Step', 'Step', 1.0, 0.7, 0.6)):
        g = Graph(FX, name)
        e = g.at(entry_node(g), 0, 0)
        p = fcall(g, play, 320, 0, Tag=tag, Location=po(e, 'Location'), Scale=po(e, 'Scale') if scale is None else scale,
                  Strength=1.0, Duration=dur, Extra=0.0)
        snd = sound(g, tag, po(e, 'Location'), 680, 0, vol)
        chain(e, p, snd)
        box(g, name, f'{dur} s of black grains from the {tag} pool (MI_Sand_{tag}), with its SFX', [e, p, snd], 'sand')
    g = Graph(FX, 'Bloom')
    e = g.at(entry_node(g), 0, 0)
    crumble = fcall(g, f'{KML}:SelectFloat', 120, 260, A=1.0, B=0.0, bPickA=po(e, 'Crumble'))
    p = fcall(g, play, 360, 0, Tag='Bloom', Location=po(e, 'Location'), Scale=po(e, 'Size'), Strength=1.5,
              Duration=po(e, 'Seconds'), Extra=crumble)
    snd = sound(g, 'Bloom', po(e, 'Location'), 720, 0, 0.8)
    chain(e, p, snd)
    box(g, 'Bloom', 'Goo wells up, spreads 1.5x the mound into a puddle with strands, holds, then recedes or crumbles '
        '(MI_Sand_Bloom, Mode 7)', [e, crumble, p, snd], 'sand')
    compile_save(FX)
    print('graphs_a ok; Hayba compile + save:', sorted(set(TOUCHED)))


def graphs_b():
    T = ptype
    # ---- BPL_SandFX ----
    for f in ('GetSandFX', 'SpawnSandBurst', 'SpawnSandStep', 'SpawnSandBloom', 'SpawnAmbientBloom'):
        drop_function(LIB, f)
    fx_c = f'{FX}.BP_SandFX_C'
    fx_t = T(unreal.load_class(None, fx_c))
    Graph.function(LIB, 'GetSandFX', outputs=[('SandFX', fx_t)])
    Graph.function(LIB, 'SpawnSandBurst', inputs=[('Location', T(unreal.Vector)), ('Scale', T('real'))])
    Graph.function(LIB, 'SpawnSandStep', inputs=[('FootLocation', T(unreal.Vector))])
    Graph.function(LIB, 'SpawnSandBloom', inputs=[('Location', T(unreal.Vector)), ('Size', T('real')), ('Seconds', T('real')),
                                                 ('Crumble', T('bool'))])
    Graph.function(LIB, 'SpawnAmbientBloom', inputs=[('Tier', T('int'))])
    g = Graph(LIB, 'GetSandFX')
    e = g.at(entry_node(g), 0, 0)
    find = fcall(g, f'{GS}:GetActorOfClass', 200, 200, ActorClass=fx_c)
    c1 = make(g, 460, 0, 'CastToBP_SandFX')
    feed(c1, Object=po(find, 'ReturnValue'))
    r1 = g.at(result_node(g), 800, 0)
    chain(e, find, c1, r1)     # GetActorOfClass is impure: off the exec path the compiler prunes it
    feed(r1, SandFX=po(c1, 'AsBP Sand FX'))
    sp = fcall(g, f'{GS}:BeginDeferredActorSpawnFromClass', 800, 300, ActorClass=fx_c,
               SpawnTransform=fcall(g, f'{KML}:MakeTransform', 560, 420))
    fin = fcall(g, f'{GS}:FinishSpawningActor', 1120, 300, Actor=po(sp, 'ReturnValue'),
                SpawnTransform=fcall(g, f'{KML}:MakeTransform', 880, 520))
    c2 = make(g, 1420, 300, 'CastToBP_SandFX')
    feed(c2, Object=po(fin, 'ReturnValue'))
    r2 = g.at(g.ed.add_return_node(), 1720, 300)
    go(c1, sp, 'CastFailed')
    chain(sp, fin, c2, r2)
    feed(r2, SandFX=po(c2, 'AsBP Sand FX'))
    box(g, 'One manager per level', 'Find BP_SandFX, or spawn it once (its pools live on it)', [e, find, c1, r1, sp, fin, c2, r2], 'pool')
    get_fx = f'{LIB}.BPL_SandFX_C:GetSandFX'
    for name, arg, call in (('SpawnSandBurst', 'Location', 'Burst'), ('SpawnSandStep', 'FootLocation', 'Step')):
        g = Graph(LIB, name)
        e = g.at(entry_node(g), 0, 0)
        gf = fcall(g, get_fx, 260, 0)
        kw = {'Location': po(e, arg)}
        if call == 'Burst':
            kw['Scale'] = po(e, 'Scale')
        b = fcall(g, f'{fx_c}:{call}', 560, 0, self=po(gf, 'SandFX'), **kw)
        chain(e, gf, b)
        box(g, name, 'Pooled sand from the level\'s BP_SandFX (no spawn per call, no Tick)', [e, gf, b], 'sand')
    g = Graph(LIB, 'SpawnSandBloom')
    e = g.at(entry_node(g), 0, 0)
    gf = fcall(g, get_fx, 260, 0)
    b = fcall(g, f'{fx_c}:Bloom', 560, 0, self=po(gf, 'SandFX'), Location=po(e, 'Location'), Size=po(e, 'Size'),
              Seconds=po(e, 'Seconds'), Crumble=po(e, 'Crumble'))
    chain(e, gf, b)
    box(g, 'SpawnSandBloom', 'A pooled bloom: goo wells up at Location, spreads, holds, then recedes or crumbles', [e, gf, b], 'sand')
    g = Graph(LIB, 'SpawnAmbientBloom')
    e = g.at(entry_node(g), 0, 0)
    gf = fcall(g, get_fx, 240, 0)
    spots = feed(mget(g, 'BloomSpots', 240, 260, fx_c), self=po(gf, 'SandFX'))
    n = fcall(g, f'{KAL}:Array_Length', 520, 300, TargetArray=po(spots))
    br = g.branch(820, 0)
    feed(br, Condition=fcall(g, f'{KML}:Greater_IntInt', 600, 160, A=po(n, 'ReturnValue'), B=0))
    idx = fcall(g, f'{KML}:RandomIntegerInRange', 760, 360, Min=0,
                Max=fcall(g, f'{KML}:Subtract_IntInt', 620, 420, A=po(n, 'ReturnValue'), B=1))
    spot = fcall(g, f'{KAL}:Array_Get', 1000, 300, TargetArray=po(spots), Index=idx)
    tier = fcall(g, f'{KML}:Conv_IntToDouble', 760, 520, InInt=po(e, 'Tier'))
    size = fcall(g, f'{KML}:Add_DoubleDouble', 1000, 520, A=fcall(g, f'{KML}:RandomFloatInRange', 760, 600, Min=0.6, Max=1.0),
                 B=fcall(g, f'{KML}:Multiply_DoubleDouble', 900, 640, A=tier, B=0.2))
    b = fcall(g, f'{fx_c}:Bloom', 1300, 0, self=po(gf, 'SandFX'), Location=po(spot, 'Item'), Size=size,
              Seconds=fcall(g, f'{KML}:RandomFloatInRange', 1060, 700, Min=8.0, Max=14.0),
              Crumble=fcall(g, f'{KML}:RandomBool', 1100, 800))
    chain(e, gf, br)
    go(br, b)
    box(g, 'SpawnAmbientBloom', 'A random BloomSpots spot, size 0.6-1.0 + 0.2 x Tier, 8-14 s, recedes or crumbles at random. '
        'BP_DreamDirector calls it on a timer, more often as the tier rises', [e, gf, spots, n, br, idx, spot, tier, size, b], 'pool')
    compile_save(LIB)
    print('graphs_b ok; Hayba compile + save:', sorted(set(TOUCHED)))


def spots():
    """BloomSpots for Hayba blueprint_set_defaults on BP_SandFX (Python never writes a Blueprint CDO)."""
    import json
    print('BLOOMSPOTS', json.dumps([{'X': round(v.x, 1), 'Y': round(v.y, 1), 'Z': round(v.z, 1)} for v in bloom_spots()]))


{'assets': assets, 'graphs_a': graphs_a, 'graphs_b': graphs_b, 'spots': spots}[phase]()
