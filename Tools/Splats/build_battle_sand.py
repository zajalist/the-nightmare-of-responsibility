"""BP_BattleSand (world lane, plan approved 2026-11-10): the battle's black sand, driven by BP_Encounter without editing
story's graphs. Placed once next to Encounter_T8. Run via ue_remote.py, Hayba compiles and saves between phases:
  $env:FOA_AREAS='VFX'; python Tools/Unreal/ue_remote.py Tools/Splats/build_battle_sand.py FOA_BATTLE_SAND=assets
  -> Hayba blueprint_compile + asset_save /Game/FoA/VFX/Sand/BP_BattleSand
  $env:FOA_AREAS='VFX'; python Tools/Unreal/ue_remote.py Tools/Splats/build_battle_sand.py FOA_BATTLE_SAND=graphs
  -> Hayba blueprint_compile + asset_save

Listens (BeginPlay binds; a dispatcher wherever one already fires for the transition):
  OnStateChanged(State)      log only
  OnDamage(Who, Amount)      Who = the hero: a burst at his chest. Who = a garment: a burst thrown out of its far side,
                             and a ring of six pops pushed out from the hero's feet (mound pops pause 1 s)
  OnGarmentEquipped(Garment) defeat: a big burst, a crumbling bloom under it, sand drifting off it on its way to the
                             hero, and M_SandOverlay as an overlay material for 2.2 s (skipped when the garment already
                             wears an overlay: face's materials and stencils are never replaced)
  OnSandBurst                intro rise (the burst is not the defeat one): sand drifts off Garments[Step] as it rises
  OnEncounterWon             victory ring, only with bVictorySweep (off until story signs off the timing)
Polls at 10 Hz (nothing fires for these): each garment's State (Telegraph: a bloom wells up under it and sand drifts off
it; Stunned: sand drifts off it and a small burst falls), and the mound's tension (0.3, +0.3 in EnemyPhase, +0.4 with
a garment on Telegraph, +0.4 x lost composure) drives pops (BPL_SandFX.SpawnSandStep) around random garments' feet.
Every detected transition is logged with its time ([battlesand] lines, bLog) so a proof run can show none are missed.
Effects reuse BP_SandFX's pools (Burst, Step, Bloom) and four drift components (SM_SandFaceDrift, MI_Sand_FaceDrift).
"""
import os

exec(open('P:/FoA/Tools/Unreal/encounter/enc_graph.py').read())  # noqa: S102  house graph helpers
import unreal  # noqa: E402

D = '/Game/FoA/VFX/Sand'
BS = f'{D}/BP_BattleSand'
ENC_C = f'{ENC}/BP_Encounter.BP_Encounter_C'
G_C = f'{ENC}/BP_Garment.BP_Garment_C'
FXL = f'{D}/BPL_SandFX.BPL_SandFX_C'
KSTR = '/Script/Engine.KismetStringLibrary'
KMAT = '/Script/Engine.KismetMaterialLibrary'
MID = '/Script/Engine.MaterialInstanceDynamic'
SCN, MC, ACT = '/Script/Engine.SceneComponent', '/Script/Engine.MeshComponent', '/Script/Engine.Actor'
OVERLAY = f'{D}/M_SandOverlay.M_SandOverlay'
SHED_MESH = '/Game/FoA/VFX/Splats/Meshes/SM_SandFaceDrift/SM_SandFaceDrift/StaticMeshes/SM_SandFaceDrift'
SHED_MI = '/Game/FoA/VFX/Splats/Instances/MI_Sand_FaceDrift'
BLAST_MESH = '/Game/FoA/VFX/Splats/Meshes/SM_SandBurst/SM_SandBurst/StaticMeshes/SM_SandBurst'
BLAST_MI = f'{D}/MI_Sand_BurstDir'          # build_battle_hitfx.py: the burst as a cone along the component's +Z
VIGNETTE = f'{D}/M_PP_SandVignette.M_PP_SandVignette'
SHAKE = '/Game/FoA/VFX/CS_SandHit.CS_SandHit_C'
MPC = '/Game/FoA/PostProcess/MPC_Dream.MPC_Dream'
PRIM = '/Script/Engine.PrimitiveComponent'
SELF = lambda f: self_call(BS, f)  # noqa: E731
T = BEL.get_basic_type_by_name
COL.update({'sand': unreal.LinearColor(0.30, 0.22, 0.10, 1)})
RING = [(70, 0), (35, 61), (-35, 61), (-70, 0), (-35, -61), (35, -61)]   # six pops, 70 cm out from the hero's feet
SIGS = {   # name: (inputs, outputs, pure)
    'Now': ((), (('T', 'real'),), True),
    'Log': ((('Msg', 'string'),), (), False),
    'BodyOf': ((('Garment', G_C),), (('Body', SCN), ('Location', unreal.Vector)), True),
    'ShedOn': ((('Garment', G_C), ('Seconds', 'real')), (), False),
    'ExpireShed': ((('Index', 'int'),), (), False),
    'ClearOverlay': ((), (), False),
    'Pop': ((), (), False),
    'Poll': ((), (), False),
    'OnBattleState': ((('State', 'name'),), (), False),
    'OnHit': ((('Who', ACT), ('Amount', 'int')), (), False),
    'OnEquipped': ((('Garment', ACT),), (), False),
    'OnWorn': ((('Garment', ACT), ('Location', unreal.Vector), ('Socket', 'name')), (), False),
    'Blast': ((('Location', unreal.Vector), ('Dir', unreal.Vector), ('Scale', 'real')), (), False),
    'Flash': ((('Mesh', MC), ('Peak', 'real')), (), False),
    'Vignette': ((), (), False),
    'Shake': ((), (), False),
    'PulseTick': ((), (), False),
    'CutShed': ((('Index', 'int'), ('Parent', SCN)), (), False),
}


def fcall(g, path, x, y, **pins):  # noqa: F811  wires first, then literals: math nodes are promotable operators in 5.8
    """Like the house fcall, but a literal on a promotable operator (+, -, *, ==) goes in as a MakeLiteral node after the
    wired pins have fixed its type (a literal on a wildcard pin is refused: 'value A=1.0 on int - int')."""
    n = g.call(path, x, y)
    lits = {}
    for k, v in pins.items():
        if isinstance(v, (unreal.BlueprintGraphPin, unreal.EdGraphNode)):
            feed(n, **{k: v})
        else:
            lits[k] = v
    for slot, (k, v) in enumerate(lits.items()):
        if n.get_class().get_name() == 'K2Node_PromotableOperator':
            g.default(n, k, v, slot)
        else:
            val(n, k, v)
    return n


def ptype_of(k):
    if isinstance(k, str) and k.startswith('/'):
        return BEL.get_object_reference_type(unreal.load_class(None, k) or unreal.load_object(None, k))
    if isinstance(k, str):
        return T(k)
    return BEL.get_struct_type(k.static_struct())


def box(g, title, nodes, kind='sand'):  # noqa: F811  title only (the user's rule)
    c = g.ed.add_comment_to_nodes(title, list(nodes), 40)
    BEL.set_comment_color(c, COL[kind])
    for prop, v in (('font_size', 18), ('comment_bubble_visible_in_details_panel', True), ('color_comment_bubble', True)):
        c.set_editor_property(prop, v)


def assets():
    if not unreal.EditorAssetLibrary.does_asset_exist(BS):
        BEL.create_blueprint_asset_with_parent(BS, unreal.Actor)
    bp = unreal.load_asset(BS)
    unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(bp)
    sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    lib = unreal.SubobjectDataBlueprintFunctionLibrary
    by_name = {str(lib.get_variable_name(lib.get_data(h))): h for h in sds.k2_gather_subobject_data_for_blueprint(bp)}
    root = by_name.get('DefaultSceneRoot') or sds.k2_gather_subobject_data_for_blueprint(bp)[0]
    for i in range(4):
        name = f'Shed{i}'
        if name not in by_name:
            h, fail = sds.add_new_subobject(unreal.AddNewSubobjectParams(parent_handle=root, new_class=unreal.StaticMeshComponent,
                                                                         blueprint_context=bp))
            assert not str(fail), fail
            sds.rename_subobject(h, name)
            by_name[name] = h
        t = lib.get_object(lib.get_data(by_name[name]))
        t.set_editor_property('static_mesh', unreal.load_asset(SHED_MESH))
        t.set_editor_property('override_materials', [unreal.load_asset(SHED_MI)])
        t.set_editor_property('cast_shadow', False)
        t.set_collision_profile_name('NoCollision')
        t.set_editor_property('render_custom_depth', True)      # stencil 5 = sand (PP_DreamMono's sand pass)
        t.set_editor_property('custom_depth_stencil_value', 5)
        t.set_editor_property('visible', False)
        t.set_editor_property('relative_scale3d', unreal.Vector(0.6, 0.6, 0.6))
    for i in range(3):   # directional blasts (hit reads, 2026-11-10)
        name = f'Blast{i}'
        if name not in by_name:
            h, fail = sds.add_new_subobject(unreal.AddNewSubobjectParams(parent_handle=root, new_class=unreal.StaticMeshComponent,
                                                                         blueprint_context=bp))
            assert not str(fail), fail
            sds.rename_subobject(h, name)
            by_name[name] = h
        t = lib.get_object(lib.get_data(by_name[name]))
        t.set_editor_property('static_mesh', unreal.load_asset(BLAST_MESH))
        t.set_editor_property('override_materials', [unreal.load_asset(BLAST_MI)])
        t.set_editor_property('cast_shadow', False)
        t.set_collision_profile_name('NoCollision')
        t.set_editor_property('render_custom_depth', True)
        t.set_editor_property('custom_depth_stencil_value', 5)
    if 'EdgeSand' not in by_name:   # the hero-hit vignette: its own unbound post volume, weight 0 except during a pulse
        h, fail = sds.add_new_subobject(unreal.AddNewSubobjectParams(parent_handle=root, new_class=unreal.PostProcessComponent,
                                                                     blueprint_context=bp))
        assert not str(fail), fail
        sds.rename_subobject(h, 'EdgeSand')
        by_name['EdgeSand'] = h
    pp = lib.get_object(lib.get_data(by_name['EdgeSand']))
    st = pp.get_editor_property('settings')
    st.set_editor_property('weighted_blendables', unreal.WeightedBlendables([unreal.WeightedBlendable(1.0, unreal.load_asset(VIGNETTE))]))
    for k, v in (('settings', st), ('unbound', True), ('priority', 20.0), ('blend_weight', 0.0)):
        pp.set_editor_property(k, v)
    ensure_vars_nc(BS, [
        ('Blasts', BEL.get_array_type(ptype_of(PRIM)), '', 'Hit reads', False),
        ('NextBlast', T('int'), '0', 'Hit reads', False),
        ('FlashMID', ptype_of('/Script/Engine.MaterialInstanceDynamic'), '', 'Hit reads', False),
        ('FlashMesh', ptype_of(MC), '', 'Hit reads', False),
        ('FlashStart', T('real'), '-10.0', 'Hit reads', False), ('FlashPeak', T('real'), '0.0', 'Hit reads', False),
        ('VigStart', T('real'), '-10.0', 'Hit reads', False),
        ('Encounter', ptype_of(ENC_C), '', 'Battle sand', False),
        ('LastStates', BEL.get_array_type(T('name')), '', 'Battle sand', False),
        ('Sheds', BEL.get_array_type(ptype_of(SCN)), '', 'Battle sand', False),
        ('ShedUntil', BEL.get_array_type(T('real')), '', 'Battle sand', False),
        ('NextShed', T('int'), '0', 'Battle sand', False),
        ('PopAccum', T('real'), '0.0', 'Battle sand', False),
        ('QuietUntil', T('real'), '0.0', 'Battle sand', False),
        ('EquipTime', T('real'), '-10.0', 'Battle sand', False),
        ('MaxComposure', T('int'), '0', 'Battle sand', False),
        ('OverlayMesh', ptype_of(MC), '', 'Battle sand', False),
        ('OverlayUntil', T('real'), '0.0', 'Battle sand', False),
        ('PopRate', T('real'), '3.0', 'Battle sand', True),
        ('bVictorySweep', T('bool'), 'false', 'Battle sand', True),
        ('bLog', T('bool'), 'true', 'Battle sand', True),
    ])
    for name, (ins, outs, pure) in SIGS.items():
        if name not in [str(n) for n in BEL.list_graph_names(bp)]:
            new_function(BS, name, [(n, ptype_of(t)) for n, t in ins], [(n, ptype_of(t)) for n, t in outs], pure)
    g = Graph(BS)
    have = {event_name(n) for n in g.ed.list_all_nodes()}
    for i, name in enumerate(('EvWon', 'EvSandBurst')):
        if event_key(name) not in have:
            g.custom_event(name, -2400, i * 200)
    print('BATTLESAND assets ok')


def now(g, x, y):
    return po(fcall(g, SELF('Now'), x, y))


def body(g, garment_pin, x, y):
    return fcall(g, SELF('BodyOf'), x, y, Garment=garment_pin)


def log(g, x, y, *parts):
    """Log('a' + b + ...): parts are literals or string pins."""
    acc = None
    for i, p in enumerate(parts):
        if acc is None and not isinstance(p, unreal.BlueprintGraphPin):
            acc = p
            continue
        n = fcall(g, f'{KSTR}:Concat_StrStr', x - 600 + i * 60, y + 220 + i * 40, A=acc if acc is not None else '', B=p)
        acc = po(n)
    return fcall(g, SELF('Log'), x, y, Msg=acc)


def s_int(g, pin, x, y):
    return po(fcall(g, f'{KSTR}:Conv_IntToString', x, y, InInt=pin))


def s_name(g, pin, x, y):
    return po(fcall(g, f'{KSTR}:Conv_NameToString', x, y, InName=pin))


def vadd(g, a, b, x, y):
    if isinstance(b, unreal.Vector):   # a constant offset: MakeVector (literal vectors don't go on promotable pins)
        b = po(fcall(g, f'{KML}:MakeVector', x - 150, y + 120, X=float(b.x), Y=float(b.y), Z=float(b.z)))
    return po(fcall(g, f'{KML}:Add_VectorVector', x, y, A=a, B=b))


def fx(g, fn, x, y, **pins):
    return fcall(g, f'{FXL}:{fn}', x, y, **pins)


def graphs():
    # Now() -> T: seconds since this actor was made (no world-context pin: GetTimeSeconds built from script read 0)
    g, e, r = new_function(BS, 'Now', [], [('T', T('real'))], True)
    wire(po(fcall(g, f'{ACT}:GetGameTimeSinceCreation', 200, 100)), pi(r, 'T'))
    go(e, r)   # the entry keeps exec pins: an unwired return node never runs and the function returns 0 (19:22 run)

    # Log(Msg): '[battlesand] <t> <msg>' to the log only
    g, e, _ = new_function(BS, 'Log', [('Msg', T('string'))])
    br = g.at(g.ed.add_branch_node(), 200, 0)
    wire(po(mget(g, 'bLog', 0, 200)), BEL.find_condition_pin(br))
    t = po(fcall(g, f'{KSTR}:Conv_DoubleToString', 200, 300, InDouble=now(g, 0, 300)))
    a = po(fcall(g, f'{KSTR}:Concat_StrStr', 450, 300, A='[battlesand] ', B=t))
    b = po(fcall(g, f'{KSTR}:Concat_StrStr', 700, 300, A=a, B=' '))
    c = po(fcall(g, f'{KSTR}:Concat_StrStr', 950, 300, A=b, B=po(e, 'Msg')))
    ps = fcall(g, f'{KSL}:PrintString', 500, 0, InString=c, bPrintToScreen='false', bPrintToLog='true')
    chain(e, br, ps)
    box(g, 'Transition log', g.ed.list_all_nodes(), 'entry')

    # BodyOf(Garment) -> Body, Location (the moving visible part: Mesh or Rig; the actor root stays in the slot)
    g, e, r = new_function(BS, 'BodyOf', [('Garment', ptype_of(G_C))], [('Body', ptype_of(SCN)), ('Location', BEL.get_struct_type(unreal.Vector.static_struct()))], True)
    bd = field(g, po(e, 'Garment'), 'Body', G_C, 200, 100)
    wire(po(bd), pi(r, 'Body'))
    wire(po(fcall(g, f'{SCN}:K2_GetComponentLocation', 450, 200, self=po(bd))), pi(r, 'Location'))
    go(e, r)

    # ShedOn(Garment, Seconds): the next of four drift components rides the garment's body for Seconds
    g, e, _ = new_function(BS, 'ShedOn', [('Garment', ptype_of(G_C)), ('Seconds', T('real'))])
    k = mget(g, 'NextShed', 0, 300)
    comp = po(fcall(g, f'{KAL}:Array_Get', 250, 300, TargetArray=mget(g, 'Sheds', 0, 420), Index=k), 'Item')
    att = fcall(g, f'{SCN}:K2_AttachToComponent', 500, 0, self=comp, Parent=po(body(g, po(e, 'Garment'), 250, 500), 'Body'),
                LocationRule='SnapToTarget', RotationRule='KeepWorld', ScaleRule='KeepWorld', bWeldSimulatedBodies='false')
    vis = fcall(g, f'{SCN}:SetVisibility', 800, 0, self=comp, bNewVisibility='true', bPropagateToChildren='false')
    until = po(fcall(g, f'{KML}:Add_DoubleDouble', 800, 400, A=now(g, 600, 400), B=po(e, 'Seconds')))
    st = fcall(g, f'{KAL}:Array_Set', 1100, 0, TargetArray=mget(g, 'ShedUntil', 900, 300), Index=k, Item=until, bSizeToFit='true')
    nxt = mset(g, 'NextShed', 1400, 0, po(fcall(g, f'{KML}:Percent_IntInt', 1200, 300,
                                               A=po(fcall(g, f'{KML}:Add_IntInt', 1100, 400, A=k, B=1)), B=4)))
    lg = log(g, 1700, 0, 'shed ', s_int(g, k, 1500, 300))
    seq(e, att, vis, st, nxt, lg)
    box(g, 'Drift rides garment', g.ed.list_all_nodes())

    # ExpireShed(Index): hide and detach a drift component whose time is up
    g, e, _ = new_function(BS, 'ExpireShed', [('Index', T('int'))])
    i = po(e, 'Index')
    till = po(fcall(g, f'{KAL}:Array_Get', 200, 300, TargetArray=mget(g, 'ShedUntil', 0, 300), Index=i), 'Item')
    due = fcall(g, f'{KML}:BooleanAND', 600, 300, A=po(fcall(g, f'{KML}:Greater_DoubleDouble', 400, 260, A=till, B=0.0)),
                B=po(fcall(g, f'{KML}:Greater_DoubleDouble', 400, 400, A=now(g, 200, 460), B=till)))
    br = g.at(g.ed.add_branch_node(), 300, 0)
    wire(po(due), BEL.find_condition_pin(br))
    comp = po(fcall(g, f'{KAL}:Array_Get', 500, 600, TargetArray=mget(g, 'Sheds', 300, 600), Index=i), 'Item')
    hide = fcall(g, f'{SCN}:SetVisibility', 600, 0, self=comp, bNewVisibility='false', bPropagateToChildren='false')
    det = fcall(g, f'{SCN}:K2_DetachFromComponent', 900, 0, self=comp, LocationRule='KeepWorld', RotationRule='KeepWorld',
                ScaleRule='KeepWorld')
    clr = fcall(g, f'{KAL}:Array_Set', 1200, 0, TargetArray=mget(g, 'ShedUntil', 1000, 300), Index=i, Item=0.0, bSizeToFit='true')
    chain(e, br)
    go(br, hide)
    chain(hide, det, clr)
    box(g, 'Drift time up', g.ed.list_all_nodes())

    # ClearOverlay(): give the defeated garment its own (empty) overlay slot back
    g, e, _ = new_function(BS, 'ClearOverlay')
    om = mget(g, 'OverlayMesh', 0, 300)
    br = g.at(g.ed.add_branch_node(), 250, 0)
    wire(po(fcall(g, f'{KSL}:IsValid', 100, 200, Object=po(om))), BEL.find_condition_pin(br))
    so = fcall(g, f'{MC}:SetOverlayMaterial', 500, 0, self=po(mget(g, 'OverlayMesh', 300, 300)))
    nul = g.at(g.ed.add_set_member_variable_node('OverlayMesh', ''), 800, 0)
    chain(e, br)
    go(br, so)
    go(so, nul)
    box(g, 'Overlay off', g.ed.list_all_nodes())

    # Pop(): one pop on the sand around a random garment's feet
    g, e, _ = new_function(BS, 'Pop')
    gars = field(g, mget(g, 'Encounter', 0, 300), 'Garments', ENC_C, 200, 300)
    n = po(fcall(g, f'{KAL}:Array_Length', 400, 300, TargetArray=po(gars)))
    br = g.at(g.ed.add_branch_node(), 300, 0)
    wire(po(fcall(g, f'{KML}:Greater_IntInt', 600, 300, A=n, B=0)), BEL.find_condition_pin(br))
    idx = po(fcall(g, f'{KML}:RandomIntegerInRange', 700, 420, Min=0,
                   Max=po(fcall(g, f'{KML}:Subtract_IntInt', 600, 500, A=n, B=1))))
    gm = po(fcall(g, f'{KAL}:Array_Get', 900, 420, TargetArray=po(field(g, mget(g, 'Encounter', 700, 600), 'Garments', ENC_C, 800, 600)), Index=idx), 'Item')
    base = po(fcall(g, f'{ACT}:K2_GetActorLocation', 1100, 420, self=gm))
    ang = po(fcall(g, f'{KML}:RandomFloatInRange', 900, 700, Min=0.0, Max=360.0))
    rad = po(fcall(g, f'{KML}:RandomFloatInRange', 900, 820, Min=40.0, Max=110.0))
    off = po(fcall(g, f'{KML}:MakeVector', 1300, 700,
                   X=po(fcall(g, f'{KML}:Multiply_DoubleDouble', 1150, 700, A=po(fcall(g, f'{KML}:DegCos', 1050, 700, A=ang)), B=rad)),
                   Y=po(fcall(g, f'{KML}:Multiply_DoubleDouble', 1150, 800, A=po(fcall(g, f'{KML}:DegSin', 1050, 800, A=ang)), B=rad)), Z=0.0))
    step = fx(g, 'SpawnSandStep', 600, 0, FootLocation=vadd(g, base, off, 1400, 420))
    chain(e, br)
    go(br, step)
    box(g, 'Mound pop', g.ed.list_all_nodes())

    # Poll(): garment transitions, tension pops, timers (10 Hz from BeginPlay)
    g, e, _ = new_function(BS, 'Poll')
    g.ed.add_local_variable('AnyTelegraph', T('bool'), 'false')
    enc = lambda x, y: mget(g, 'Encounter', x, y)  # noqa: E731
    valid = g.at(g.ed.add_branch_node(), 100, 0)   # IsValid gates the exec: Blueprint ANDs read both inputs (Accessed None)
    wire(po(fcall(g, f'{KSL}:IsValid', 0, 200, Object=po(enc(-200, 200)))), BEL.find_condition_pin(valid))
    ok = g.at(g.ed.add_branch_node(), 250, 0)
    wire(po(field(g, enc(-200, 320), 'bActive', ENC_C, 0, 320)), BEL.find_condition_pin(ok))
    # inactive: forget the last battle
    clr = fcall(g, f'{KAL}:Array_Clear', 500, -300, TargetArray=mget(g, 'LastStates', 300, -200))
    mx0 = mset(g, 'MaxComposure', 800, -300, 0)
    # active: size LastStates to the line, then walk it
    gars = lambda x, y: po(field(g, enc(x - 200, y), 'Garments', ENC_C, x, y))  # noqa: E731
    n = po(fcall(g, f'{KAL}:Array_Length', 700, 300, TargetArray=gars(500, 300)))
    rs = fcall(g, f'{KAL}:Array_Resize', 500, 0, TargetArray=mget(g, 'LastStates', 300, 160), Size=n)
    t0 = g.at(g.ed.add_set_local_variable_node('AnyTelegraph'), 800, 0)
    val(t0, 'AnyTelegraph', 'false')
    loop = make(g, 1100, 0, 'ForLoop')
    feed(loop, FirstIndex=0, LastIndex=po(fcall(g, f'{KML}:Subtract_IntInt', 900, 300, A=n, B=1)))
    i = po(loop, 'Index')
    gm = po(fcall(g, f'{KAL}:Array_Get', 1300, 300, TargetArray=gars(1100, 300), Index=i), 'Item')
    st = po(field(g, gm, 'State', G_C, 1500, 300))
    last = po(fcall(g, f'{KAL}:Array_Get', 1500, 420, TargetArray=mget(g, 'LastStates', 1300, 460), Index=i), 'Item')
    is_tel = po(fcall(g, f'{KML}:EqualEqual_NameName', 1700, 520, A=st, B='Telegraph'))
    anyt = g.at(g.ed.add_set_local_variable_node('AnyTelegraph'), 1500, 0)
    wire(po(fcall(g, f'{KML}:BooleanOR', 1400, 160, A=po(g.at(g.ed.add_get_local_variable_node('AnyTelegraph'), 1200, 160)), B=is_tel)),
         pi(anyt, 'AnyTelegraph'))
    changed = g.at(g.ed.add_branch_node(), 1800, 0)
    wire(po(fcall(g, f'{KML}:NotEqual_NameName', 1700, 300, A=st, B=last)), BEL.find_condition_pin(changed))
    lg = log(g, 2100, 0, 'garment ', s_int(g, i, 1900, 300), ' ', s_name(g, last, 1900, 380), ' -> ', s_name(g, st, 1900, 460))
    tel = g.at(g.ed.add_branch_node(), 2400, 0)
    wire(is_tel, BEL.find_condition_pin(tel))
    bloom = fx(g, 'SpawnSandBloom', 2700, -200, Location=po(fcall(g, f'{ACT}:K2_GetActorLocation', 2500, -360, self=gm)),
               Size=0.45, Seconds=1.6, Crumble='false')
    shed_t = fcall(g, SELF('ShedOn'), 3000, -200, Garment=gm, Seconds=1.4)
    stun = g.at(g.ed.add_branch_node(), 2700, 100)
    wire(po(fcall(g, f'{KML}:EqualEqual_NameName', 2500, 300, A=st, B='Stunned')), BEL.find_condition_pin(stun))
    shed_s = fcall(g, SELF('ShedOn'), 3000, 100, Garment=gm, Seconds=1.2)
    fall = fx(g, 'SpawnSandBurst', 3300, 100, Location=vadd(g, po(body(g, gm, 3000, 300), 'Location'), unreal.Vector(0, 0, -25), 3200, 300),
              Scale=0.5)
    keep = fcall(g, f'{KAL}:Array_Set', 3600, 0, TargetArray=mget(g, 'LastStates', 3400, 300), Index=i, Item=st, bSizeToFit='true')
    # after the walk: tension -> pops
    comp = po(field(g, enc(1000, 900), 'Composure', ENC_C, 1200, 900))
    mx = mset(g, 'MaxComposure', 1400, 700, po(fcall(g, f'{KML}:Max', 1300, 1000, A=comp, B=mget(g, 'MaxComposure', 1100, 1050))))
    cmax = po(fcall(g, f'{KML}:FMax', 1450, 1100, A=1.0,
                    B=po(fcall(g, f'{KML}:Conv_IntToDouble', 1300, 1150, InInt=mget(g, 'MaxComposure', 1100, 1150)))))
    share = po(fcall(g, f'{KML}:Divide_DoubleDouble', 1600, 1000, A=po(fcall(g, f'{KML}:Conv_IntToDouble', 1450, 1000, InInt=comp)), B=cmax))
    lost = po(fcall(g, f'{KML}:FClamp', 1900, 1000, Min=0.0, Max=1.0,
                    Value=po(fcall(g, f'{KML}:Subtract_DoubleDouble', 1750, 1000, A=1.0, B=share))))
    sel = lambda x, y, on, v: po(fcall(g, f'{KML}:SelectFloat', x, y, A=v, B=0.0, bPickA=on))  # noqa: E731
    enemy = po(fcall(g, f'{KML}:EqualEqual_NameName', 1600, 1250, A=po(field(g, enc(1300, 1250), 'BattleState', ENC_C, 1450, 1250)),
                     B='EnemyPhase'))
    tension = po(fcall(g, f'{KML}:Add_DoubleDouble', 2300, 1000, A=po(fcall(
        g, f'{KML}:Add_DoubleDouble', 2150, 1000, A=0.3, B=po(fcall(g, f'{KML}:Multiply_DoubleDouble', 2050, 1050, A=lost, B=0.4)))),
        B=po(fcall(g, f'{KML}:Add_DoubleDouble', 2150, 1150, A=sel(1900, 1250, enemy, 0.3),
                   B=sel(1900, 1350, po(g.at(g.ed.add_get_local_variable_node('AnyTelegraph'), 1700, 1350)), 0.4)))))
    acc = mset(g, 'PopAccum', 1700, 700, po(fcall(g, f'{KML}:Add_DoubleDouble', 2500, 1000, A=mget(g, 'PopAccum', 2300, 1150), B=po(fcall(
        g, f'{KML}:Multiply_DoubleDouble', 2400, 1250, A=tension, B=po(fcall(g, f'{KML}:Multiply_DoubleDouble', 2300, 1350,
                                                                             A=mget(g, 'PopRate', 2100, 1400), B=0.1)))))))
    ready = g.at(g.ed.add_branch_node(), 2000, 700)
    wire(po(fcall(g, f'{KML}:BooleanAND', 1900, 850, A=po(fcall(g, f'{KML}:GreaterEqual_DoubleDouble', 1800, 820,
                                                                   A=mget(g, 'PopAccum', 1650, 820), B=1.0)),
                  B=po(fcall(g, f'{KML}:Greater_DoubleDouble', 1800, 900, A=now(g, 1650, 900), B=mget(g, 'QuietUntil', 1650, 960))))),
         BEL.find_condition_pin(ready))
    spend = mset(g, 'PopAccum', 2300, 700, po(fcall(g, f'{KML}:Subtract_DoubleDouble', 2200, 850, A=mget(g, 'PopAccum', 2050, 850), B=1.0)))
    pop = fcall(g, SELF('Pop'), 2600, 700)
    cap = mset(g, 'PopAccum', 2300, 560, po(fcall(g, f'{KML}:FMin', 2200, 600, A=mget(g, 'PopAccum', 2050, 600), B=2.0)))
    # timers, every tick
    exp = [fcall(g, SELF('ExpireShed'), 3000 + j * 260, 700, Index=j) for j in range(4)]
    ov = g.at(g.ed.add_branch_node(), 4100, 700)
    wire(po(fcall(g, f'{KML}:Greater_DoubleDouble', 4000, 850, A=now(g, 3850, 850), B=mget(g, 'OverlayUntil', 3850, 950))),
         BEL.find_condition_pin(ov))
    clo = fcall(g, SELF('ClearOverlay'), 4400, 700)
    chain(e, valid)
    go(valid, ok)
    go(ok, rs)
    go(ok, clr, 'else')
    chain(clr, mx0)
    go(mx0, exp[0])
    chain(rs, t0, loop)
    go(loop, anyt, 'LoopBody')
    chain(anyt, changed)
    go(changed, lg)
    chain(lg, tel)
    go(tel, bloom)
    chain(bloom, shed_t, keep)
    go(tel, stun, 'else')
    go(stun, shed_s)
    scast = make(g, 3450, 100, 'CastToMeshComponent')
    wire(po(body(g, gm, 3350, 400), 'Body'), pi(scast, 'Object'))
    sfl = fcall(g, SELF('Flash'), 3550, 100, Mesh=as_pin(scast), Peak=0.4)
    chain(shed_s, fall, scast, sfl, keep)
    go(scast, keep, 'CastFailed')
    go(stun, keep, 'else')
    go(loop, mx, 'Completed')
    chain(mx, acc, ready)
    go(ready, spend)
    chain(spend, pop, exp[0])
    go(ready, cap, 'else')
    go(cap, exp[0])
    chain(*exp, ov)
    go(ov, clo)
    box(g, 'Garment states and tension', g.ed.list_all_nodes())

    # Blast(Location, Dir, Scale): the next of three cone bursts, aimed along Dir tilted 25 deg up
    g, e, _ = new_function(BS, 'Blast', [('Location', BEL.get_struct_type(unreal.Vector.static_struct())),
                                         ('Dir', BEL.get_struct_type(unreal.Vector.static_struct())), ('Scale', T('real'))])
    k = mget(g, 'NextBlast', 0, 300)
    comp = po(fcall(g, f'{KAL}:Array_Get', 200, 300, TargetArray=mget(g, 'Blasts', 0, 420), Index=k), 'Item')
    aim = po(fcall(g, f'{KML}:MakeRotFromZ', 500, 400, Z=po(fcall(g, f'{KML}:Normal', 350, 400, A=vadd(g, po(e, 'Dir'), unreal.Vector(0, 0, 0.47), 200, 500)))))
    put = fcall(g, f'{SCN}:K2_SetWorldLocationAndRotation', 300, 0, self=comp, NewLocation=po(e, 'Location'), NewRotation=aim)
    scl = fcall(g, f'{SCN}:SetWorldScale3D', 600, 0, self=comp,
                NewScale=fcall(g, f'{KML}:MakeVector', 500, 250, X=po(e, 'Scale'), Y=po(e, 'Scale'), Z=po(e, 'Scale')))
    ev = fcall(g, f'{PRIM}:SetVectorParameterForCustomPrimitiveData', 900, 0, self=comp, ParameterName='SandEvent',
               Value=fcall(g, f'{KML}:MakeVector4', 800, 250, X=1.0, Y=po(fcall(g, f'{GS}:GetTimeSeconds', 650, 300)), Z=1.0, W=0.0))
    nx = mset(g, 'NextBlast', 1200, 0, po(fcall(g, f'{KML}:Percent_IntInt', 1100, 250,
                                               A=po(fcall(g, f'{KML}:Add_IntInt', 1000, 300, A=mget(g, 'NextBlast', 900, 350), B=1)), B=3)))
    chain(e, put, scl, ev, nx)
    box(g, 'Directional blast', g.ed.list_all_nodes())

    # Flash(Mesh, Peak): a short sand-overlay pulse; a garment already wearing another overlay keeps it (face's own)
    g, e, _ = new_function(BS, 'Flash', [('Mesh', ptype_of(MC)), ('Peak', T('real'))])
    ok = g.at(g.ed.add_branch_node(), 200, 0)
    wire(po(fcall(g, f'{KSL}:IsValid', 100, 200, Object=po(e, 'Mesh'))), BEL.find_condition_pin(ok))
    cur = po(fcall(g, f'{MC}:GetOverlayMaterial', 300, 300, self=po(e, 'Mesh')))
    free = g.at(g.ed.add_branch_node(), 500, 0)
    wire(po(fcall(g, f'{KML}:BooleanOR', 450, 300, A=po(fcall(g, f'{KML}:Not_PreBool', 400, 250, A=po(fcall(g, f'{KSL}:IsValid', 350, 250, Object=cur)))),
                  B=po(fcall(g, f'{KML}:EqualEqual_ObjectObject', 400, 400, A=cur, B=mget(g, 'FlashMID', 250, 450))))), BEL.find_condition_pin(free))
    s1 = mset(g, 'FlashMesh', 800, 0, po(e, 'Mesh'))
    s2 = mset(g, 'FlashPeak', 1050, 0, po(e, 'Peak'))
    s3 = mset(g, 'FlashStart', 1300, 0, now(g, 1150, 250))
    on = fcall(g, f'{MC}:SetOverlayMaterial', 1550, 0, self=po(e, 'Mesh'), NewOverlayMaterial=mget(g, 'FlashMID', 1400, 300))
    chain(e, ok)
    go(ok, free)
    go(free, s1)
    chain(s1, s2, s3, on)
    box(g, 'Hit flash', g.ed.list_all_nodes())

    # Vignette(): start the hero-hit edge pulse
    g, e, _ = new_function(BS, 'Vignette')
    chain(e, mset(g, 'VigStart', 300, 0, now(g, 100, 200)))
    box(g, 'Edge pulse', g.ed.list_all_nodes())

    # Shake(): a tiny camera shake, skipped with Reduce Motion (MPC_Dream ReduceMotion = 1, the Settings toggle)
    g, e, _ = new_function(BS, 'Shake')
    calm = g.at(g.ed.add_branch_node(), 300, 0)
    rm = fcall(g, '/Script/Engine.KismetMaterialLibrary:GetScalarParameterValue', 100, 0, Collection=MPC, ParameterName='ReduceMotion')
    wire(po(fcall(g, f'{KML}:Less_DoubleDouble', 250, 250, A=po(rm), B=0.5)), BEL.find_condition_pin(calm))
    sh = fcall(g, '/Script/Engine.PlayerCameraManager:StartCameraShake', 600, 0,
               self=po(fcall(g, f'{GS}:GetPlayerCameraManager', 400, 250, PlayerIndex=0)), ShakeClass=SHAKE, Scale=1.0)
    chain(e, rm, calm)   # impure: on the exec path or it is pruned and reads 0
    go(calm, sh)
    box(g, 'Camera shake', g.ed.list_all_nodes())

    # PulseTick (30 Hz): drive the flash overlay amount and the edge vignette weight, end the flash cleanly
    g, e, _ = new_function(BS, 'PulseTick')
    tf = po(fcall(g, f'{KML}:Divide_DoubleDouble', 300, 300, A=po(fcall(g, f'{KML}:Subtract_DoubleDouble', 150, 300,
                                                                         A=now(g, 0, 300), B=mget(g, 'FlashStart', 0, 400))), B=0.25))
    fv = g.at(g.ed.add_branch_node(), 200, 0)
    wire(po(fcall(g, f'{KSL}:IsValid', 100, 200, Object=mget(g, 'FlashMesh', 0, 200))), BEL.find_condition_pin(fv))
    live = g.at(g.ed.add_branch_node(), 450, 0)
    wire(po(fcall(g, f'{KML}:Less_DoubleDouble', 400, 250, A=tf, B=1.0)), BEL.find_condition_pin(live))
    amt = po(fcall(g, f'{KML}:Multiply_DoubleDouble', 700, 350, A=mget(g, 'FlashPeak', 550, 400),
                   B=po(fcall(g, f'{KML}:Sin', 600, 300, A=po(fcall(g, f'{KML}:Multiply_DoubleDouble', 550, 250,
                                                                       A=po(fcall(g, f'{KML}:FClamp', 450, 300, Value=tf, Min=0.0, Max=1.0)), B=3.14159))))))
    sa = fcall(g, '/Script/Engine.MaterialInstanceDynamic:SetScalarParameterValue', 800, -100, self=mget(g, 'FlashMID', 650, -200),
               ParameterName='Amount', Value=amt)
    mine = g.at(g.ed.add_branch_node(), 800, 150)
    wire(po(fcall(g, f'{KML}:EqualEqual_ObjectObject', 750, 400, A=po(fcall(g, f'{MC}:GetOverlayMaterial', 650, 450, self=mget(g, 'FlashMesh', 500, 500))),
                  B=mget(g, 'FlashMID', 600, 550))), BEL.find_condition_pin(mine))
    off = fcall(g, f'{MC}:SetOverlayMaterial', 1050, 150, self=mget(g, 'FlashMesh', 900, 350))
    clr = g.at(g.ed.add_set_member_variable_node('FlashMesh', ''), 1300, 150)
    tv = po(fcall(g, f'{KML}:Divide_DoubleDouble', 1500, 450, A=po(fcall(g, f'{KML}:Subtract_DoubleDouble', 1400, 450,
                                                                          A=now(g, 1250, 450), B=mget(g, 'VigStart', 1250, 550))), B=0.35))
    vw = po(fcall(g, f'{KML}:SelectFloat', 1800, 400, B=0.0, bPickA=po(fcall(g, f'{KML}:Less_DoubleDouble', 1650, 550, A=tv, B=1.0)),
                  A=po(fcall(g, f'{KML}:Sin', 1650, 400, A=po(fcall(g, f'{KML}:Multiply_DoubleDouble', 1550, 350,
                                                                     A=po(fcall(g, f'{KML}:FClamp', 1450, 350, Value=tv, Min=0.0, Max=1.0)), B=3.14159))))))
    bw = g.at(g.ed.add_set_member_variable_node('BlendWeight', '/Script/Engine.PostProcessComponent'), 1900, 0)
    feed(bw, self=mget(g, 'EdgeSand', 1750, 200), BlendWeight=vw)
    go(e, fv)
    go(fv, live)
    go(fv, bw, 'else')
    go(live, sa)
    go(sa, bw)
    go(live, mine, 'else')
    go(mine, off)
    go(off, clr)
    go(clr, bw)
    go(mine, clr, 'else')
    box(g, 'Pulses', g.ed.list_all_nodes())

    # CutShed(Index, Parent): a drift riding Parent ends now (the garment's body hides when it is worn)
    g, e, _ = new_function(BS, 'CutShed', [('Index', T('int')), ('Parent', ptype_of(SCN))])
    comp = po(fcall(g, f'{KAL}:Array_Get', 200, 300, TargetArray=mget(g, 'Sheds', 0, 300), Index=po(e, 'Index')), 'Item')
    rides = g.at(g.ed.add_branch_node(), 400, 0)
    wire(po(fcall(g, f'{KML}:EqualEqual_ObjectObject', 350, 250, A=po(fcall(g, f'{SCN}:GetAttachParent', 250, 250, self=comp)),
                  B=po(e, 'Parent'))), BEL.find_condition_pin(rides))
    hide = fcall(g, f'{SCN}:SetVisibility', 650, 0, self=comp, bNewVisibility='false', bPropagateToChildren='false')
    det = fcall(g, f'{SCN}:K2_DetachFromComponent', 900, 0, self=comp, LocationRule='KeepWorld', RotationRule='KeepWorld', ScaleRule='KeepWorld')
    zero = fcall(g, f'{KAL}:Array_Set', 1150, 0, TargetArray=mget(g, 'ShedUntil', 1000, 300), Index=po(e, 'Index'), Item=0.0, bSizeToFit='true')
    chain(e, rides)
    go(rides, hide)
    chain(hide, det, zero)
    box(g, 'Cut a drift', g.ed.list_all_nodes())

    # OnWorn(Garment, Location, Socket): story's arrival frame -> the burst where it lands on him; flight effects end
    g, e, _ = new_function(BS, 'OnWorn', [('Garment', ptype_of(ACT)), ('Location', BEL.get_struct_type(unreal.Vector.static_struct())),
                                          ('Socket', T('name'))])
    lg = log(g, 300, 0, 'worn ', s_name(g, po(e, 'Socket'), 100, 300))
    burst = fx(g, 'SpawnSandBurst', 600, 0, Location=po(e, 'Location'), Scale=0.9)
    clo = fcall(g, SELF('ClearOverlay'), 900, 0)
    cast = make(g, 1150, 0, 'CastToBP_Garment')
    wire(po(e, 'Garment'), pi(cast, 'Object'))
    par = po(body(g, as_pin(cast), 1250, 300), 'Body')
    cuts = [fcall(g, SELF('CutShed'), 1500 + j * 260, 0, Index=j, Parent=par) for j in range(4)]
    chain(e, lg, burst, clo, cast, *cuts)
    box(g, 'Worn arrival', g.ed.list_all_nodes())

    # OnBattleState(State)
    g, e, _ = new_function(BS, 'OnBattleState', [('State', T('name'))])
    chain(e, log(g, 400, 0, 'state ', s_name(g, po(e, 'State'), 200, 300)))
    box(g, 'Battle state log', g.ed.list_all_nodes(), 'entry')

    # OnHit(Who, Amount)
    g, e, _ = new_function(BS, 'OnHit', [('Who', ptype_of(ACT)), ('Amount', T('int'))])
    pawn = lambda x, y: po(fcall(g, f'{GS}:GetPlayerPawn', x, y, PlayerIndex=0))  # noqa: E731
    amt = po(fcall(g, f'{KML}:Abs', 300, 900, A=po(fcall(g, f'{KML}:Conv_IntToDouble', 150, 900, InInt=po(e, 'Amount')))))
    lg = log(g, 300, 0, 'hit ', po(fcall(g, f'{KSL}:GetDisplayName', 100, 300, Object=po(e, 'Who'))), ' ', s_int(g, po(e, 'Amount'), 100, 400))
    hero = g.at(g.ed.add_branch_node(), 600, 0)
    wire(po(fcall(g, f'{KML}:EqualEqual_ObjectObject', 500, 200, A=po(e, 'Who'), B=pawn(300, 260))), BEL.find_condition_pin(hero))
    # the hero is hit: a burst at his chest
    chest = vadd(g, po(fcall(g, f'{ACT}:K2_GetActorLocation', 700, -300, self=pawn(500, -300))), unreal.Vector(0, 0, 20), 900, -300)
    hb = fx(g, 'SpawnSandBurst', 1000, -200, Location=chest, Scale=po(fcall(g, f'{KML}:FClamp', 900, -100, Min=1.2, Max=1.8, Value=po(
        fcall(g, f'{KML}:Add_DoubleDouble', 800, -100, A=1.2, B=po(fcall(g, f'{KML}:Multiply_DoubleDouble', 700, -100, A=amt, B=0.08)))))))
    vg = fcall(g, SELF('Vignette'), 1300, -200)
    # a garment is hit: sand thrown out of its far side, and the hero's push ring
    cast = make(g, 900, 200, 'CastToBP_Garment')
    wire(po(e, 'Who'), pi(cast, 'Object'))
    bl = po(body(g, as_pin(cast), 1100, 400), 'Location')
    hp = po(fcall(g, f'{ACT}:K2_GetActorLocation', 1100, 550, self=pawn(900, 550)))
    away = po(fcall(g, f'{KML}:Multiply_VectorFloat', 1400, 500, A=po(fcall(g, f'{KML}:Normal', 1300, 500,
                                                                             A=po(fcall(g, f'{KML}:Subtract_VectorVector', 1250, 450, A=bl, B=hp)))), B=15.0))
    gb = fcall(g, SELF('Blast'), 1300, 200, Location=vadd(g, bl, away, 1500, 400), Dir=po(fcall(g, f'{KML}:Normal', 1450, 550, A=away)),
               Scale=po(fcall(g, f'{KML}:FClamp', 1400, 650, Min=1.2, Max=2.0,
               Value=po(fcall(g, f'{KML}:Add_DoubleDouble', 1300, 650, A=1.2, B=po(fcall(g, f'{KML}:Multiply_DoubleDouble', 1200, 650, A=amt, B=0.2)))))))
    mcast = make(g, 1300, -50, 'CastToMeshComponent')
    wire(po(body(g, as_pin(cast), 1150, -150), 'Body'), pi(mcast, 'Object'))
    fl = fcall(g, SELF('Flash'), 1550, -50, Mesh=as_pin(mcast), Peak=0.8)
    shk = fcall(g, SELF('Shake'), 1800, -50)
    feet = vadd(g, hp, unreal.Vector(0, 0, -85), 1600, 700)
    ring = [fx(g, 'SpawnSandStep', 1600 + j * 260, 200, FootLocation=vadd(g, feet, unreal.Vector(dx, dy, 0), 1600 + j * 260, 450))
            for j, (dx, dy) in enumerate(RING)]
    quiet = mset(g, 'QuietUntil', 3300, 200, po(fcall(g, f'{KML}:Add_DoubleDouble', 3200, 400, A=now(g, 3050, 400), B=1.0)))
    chain(e, lg, hero)
    go(hero, hb)
    go(hb, vg)
    go(hero, cast, 'else')
    chain(cast, gb, mcast, fl, shk, *ring, quiet)
    go(mcast, shk, 'CastFailed')
    box(g, 'Hit sand', g.ed.list_all_nodes())

    # OnEquipped(Garment): defeat collapse
    g, e, _ = new_function(BS, 'OnEquipped', [('Garment', ptype_of(ACT))])
    et = mset(g, 'EquipTime', 200, 0, now(g, 0, 200))
    lg = log(g, 500, 0, 'equipped ', po(fcall(g, f'{KSL}:GetDisplayName', 300, 300, Object=po(e, 'Garment'))))
    cast = make(g, 800, 0, 'CastToBP_Garment')
    wire(po(e, 'Garment'), pi(cast, 'Object'))
    gm = as_pin(cast)
    bo = body(g, gm, 1000, 300)
    burst = fx(g, 'SpawnSandBurst', 1100, 0, Location=po(bo, 'Location'), Scale=1.3)
    root = po(fcall(g, f'{ACT}:K2_GetActorLocation', 1200, 450, self=gm))
    bl = po(bo, 'Location')
    brk = fcall(g, f'{KML}:BreakVector', 1300, 300, InVec=bl)
    under = po(fcall(g, f'{KML}:MakeVector', 1500, 300, X=po(brk, 'X'), Y=po(brk, 'Y'),
                     Z=po(fcall(g, f'{KML}:BreakVector', 1400, 450, InVec=root), 'Z')))
    bloom = fx(g, 'SpawnSandBloom', 1400, 0, Location=under, Size=0.7, Seconds=2.6, Crumble='true')
    shed = fcall(g, SELF('ShedOn'), 1700, 0, Garment=gm, Seconds=2.2)
    old = fcall(g, SELF('ClearOverlay'), 2000, 0)
    mesh_cast = make(g, 2300, 0, 'CastToMeshComponent')
    wire(po(bo, 'Body'), pi(mesh_cast, 'Object'))
    mesh = as_pin(mesh_cast)
    free = g.at(g.ed.add_branch_node(), 2600, 0)
    wire(po(fcall(g, f'{KSL}:IsValid', 2500, 250, Object=po(fcall(g, f'{MC}:GetOverlayMaterial', 2400, 250, self=mesh)))), pi(free, 'Condition'))
    mk = fcall(g, f'{KMAT}:CreateDynamicMaterialInstance', 2900, 0, Parent=OVERLAY)
    tr = fcall(g, f'{MID}:SetScalarParameterValue', 3200, 0, self=po(mk), ParameterName='Transition', Value=1.0)
    am = fcall(g, f'{MID}:SetScalarParameterValue', 3500, 0, self=po(mk), ParameterName='Amount', Value=0.5)
    put = fcall(g, f'{MC}:SetOverlayMaterial', 3800, 0, self=mesh, NewOverlayMaterial=po(mk))
    keep = mset(g, 'OverlayMesh', 4100, 0, mesh)
    till = mset(g, 'OverlayUntil', 4400, 0, po(fcall(g, f'{KML}:Add_DoubleDouble', 4300, 250, A=now(g, 4150, 250), B=2.2)))
    chain(e, et, lg, cast, burst, bloom, shed, old, mesh_cast, free)
    go(free, mk, 'else')   # an overlay already there belongs to the garment (face): leave it
    chain(mk, tr, am, put, keep, till)
    box(g, 'Defeat collapse', g.ed.list_all_nodes())

    # Event graph: bind, start the poll; intro rise; victory
    g = Graph(BS)
    keep_ev = {'evwon', 'evsandburst'}
    g.ed.remove_nodes([n for n in g.ed.list_all_nodes() if event_name(n) not in keep_ev])
    for c in list(g.ed.list_comment_nodes()):
        g.ed.remove_comment_node(c)
    EV = {event_name(n): n for n in g.ed.list_all_nodes() if event_name(n)}
    bp_ = g.event('ReceiveBeginPlay', 0, 0)
    find = fcall(g, f'{GS}:GetActorOfClass', 250, 200, ActorClass=ENC_C)
    cast = make(g, 500, 0, 'CastToBP_Encounter')
    wire(po(find), pi(cast, 'Object'))
    se = mset(g, 'Encounter', 800, 0, as_pin(cast))
    adds = [fcall(g, f'{KAL}:Array_Add', 1050 + j * 250, 0, TargetArray=mget(g, 'Sheds', 1000 + j * 250, 200),
                  NewItem=mget(g, f'Shed{j}', 1000 + j * 250, 300)) for j in range(4)]
    # four expiry slots up front: Poll reads ShedUntil[0..3] from its first tick (an empty array logged 40 warnings/s)
    adds.append(fcall(g, f'{KAL}:Array_Resize', 2050, 0, TargetArray=mget(g, 'ShedUntil', 2000, 200), Size=4))
    adds += [fcall(g, f'{KAL}:Array_Add', 1050 + j * 250, -400, TargetArray=mget(g, 'Blasts', 1000 + j * 250, -250),
                   NewItem=mget(g, f'Blast{j}', 1000 + j * 250, -150)) for j in range(3)]
    mid = fcall(g, '/Script/Engine.KismetMaterialLibrary:CreateDynamicMaterialInstance', 1800, -400, Parent=OVERLAY)
    adds += [mid, mset(g, 'FlashMID', 2050, -400, po(mid)),
             fcall(g, '/Script/Engine.MaterialInstanceDynamic:SetScalarParameterValue', 2300, -400, self=po(mid), ParameterName='Transition', Value=1.0),
             fcall(g, '/Script/Engine.MaterialInstanceDynamic:SetScalarParameterValue', 2550, -400, self=po(mid), ParameterName='Amount', Value=0.0),
             fcall(g, f'{KSL}:K2_SetTimer', 2800, -400, FunctionName='PulseTick', Time=0.033, bLooping='true')]
    src = lambda x: mget(g, 'Encounter', x, 450)  # noqa: E731
    binds = []
    x = 2500
    for disp, fn in (('OnStateChanged', 'OnBattleState'), ('OnDamage', 'OnHit'), ('OnGarmentEquipped', 'OnEquipped'),
                     ('OnGarmentWorn', 'OnWorn')):
        s = src(x - 100)
        names = [nm for nm in g.ed.list_available_nodes([po(s)]) if nm.lower().replace(' ', '').endswith('bindeventto' + disp.lower())]
        b = g.at(g.ed.create_node_from_name(names[0], unreal.Vector2D(x, 0), [po(s)]), x, 0)
        if not PIN.list_connected_pins(pi(b, 'self')):
            wire(po(s), pi(b, 'self'))
        mk = make(g, x - 40, 250, 'Create Event')
        BEL.set_create_delegate_function(mk, fn)
        wire(po(mk, 'OutputDelegate'), pi(b, 'Delegate'))
        binds.append(b)
        x += 400
    for disp, ev in (('OnEncounterWon', 'EvWon'), ('OnSandBurst', 'EvSandBurst')):
        s = src(x - 100)
        names = [nm for nm in g.ed.list_available_nodes([po(s)]) if nm.lower().replace(' ', '').endswith('bindeventto' + disp.lower())]
        b = g.at(g.ed.create_node_from_name(names[0], unreal.Vector2D(x, 0), [po(s)]), x, 0)
        if not PIN.list_connected_pins(pi(b, 'self')):
            wire(po(s), pi(b, 'self'))
        wire(po(EV[event_key(ev)], 'OutputDelegate'), pi(b, 'Delegate'))
        binds.append(b)
        x += 400
    tm = fcall(g, f'{KSL}:K2_SetTimer', x, 0, FunctionName='Poll', Time=0.1, bLooping='true')
    chain(bp_, find, cast, se, *adds, *binds, tm)
    box(g, 'Listen to the battle', g.ed.list_all_nodes(), 'entry')
    # intro rise: OnSandBurst that is not the defeat one (that fires in the same frame as OnGarmentEquipped)
    y = 1300
    sb = g.at(EV['evsandburst'], 0, y)
    rise = g.at(g.ed.add_branch_node(), 300, y)
    wire(po(fcall(g, f'{KML}:Greater_DoubleDouble', 250, y + 200, A=po(fcall(
        g, f'{KML}:Subtract_DoubleDouble', 100, y + 200, A=now(g, -100, y + 200), B=mget(g, 'EquipTime', -100, y + 300))), B=0.1)),
        BEL.find_condition_pin(rise))
    step = po(field(g, mget(g, 'Encounter', 300, y + 400), 'Step', ENC_C, 500, y + 400))
    gars = po(field(g, mget(g, 'Encounter', 300, y + 520), 'Garments', ENC_C, 500, y + 520))
    valid = g.at(g.ed.add_branch_node(), 900, y)
    wire(po(fcall(g, f'{KAL}:Array_IsValidIndex', 700, y + 300, TargetArray=gars, IndexToTest=step)), BEL.find_condition_pin(valid))
    lg = log(g, 600, y, 'rise ', s_int(g, step, 400, y + 650))
    shed = fcall(g, SELF('ShedOn'), 1200, y, Garment=po(fcall(g, f'{KAL}:Array_Get', 1000, y + 400, TargetArray=gars, Index=step), 'Item'),
                 Seconds=1.6)
    chain(sb, rise)
    go(rise, lg)
    chain(lg, valid)
    go(valid, shed)
    # victory ring (story signs off the timing first)
    y = 1900
    wv = g.at(EV['evwon'], 0, y)
    lw = log(g, 300, y, 'won')
    on = g.at(g.ed.add_branch_node(), 600, y)
    wire(po(mget(g, 'bVictorySweep', 400, y + 200)), BEL.find_condition_pin(on))
    feet = vadd(g, po(fcall(g, f'{ACT}:K2_GetActorLocation', 600, y + 400, self=po(fcall(g, f'{GS}:GetPlayerPawn', 400, y + 400, PlayerIndex=0)))),
                unreal.Vector(0, 0, -75), 800, y + 400)
    sweep = [fx(g, 'SpawnSandBurst', 900 + j * 260, y, Location=vadd(g, feet, unreal.Vector(dx * 2.2, dy * 2.2, 0), 900 + j * 260, y + 250),
                Scale=0.9) for j, (dx, dy) in enumerate(RING)]
    chain(wv, lw, on)
    go(on, sweep[0])
    chain(*sweep)
    box(g, 'Intro rise and victory', [n for n in g.ed.list_all_nodes() if BEL.get_node_pos(n).y >= 1200])
    print('BATTLESAND graphs ok')


try:
    {'assets': assets, 'graphs': graphs}[os.environ.get('FOA_BATTLE_SAND', 'assets')]()
except Exception:
    import traceback
    print('BATTLESAND FAILED ' + ' | '.join(traceback.format_exc().strip().splitlines()[-3:]))
