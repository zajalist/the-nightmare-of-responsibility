"""BP_Garment: one enemy on the battle line (spawned by BP_Encounter, one per party member, socks twice).
  $env:FOA_AGENT='mech_encounter'; python Tools/Unreal/ue_remote.py Tools/Unreal/encounter/build_garment_bp.py
Its own small state machine, a Name: Idle, Telegraph (a big move announced a turn early), Attack, Stunned, Defeated.
  Setup(Data, Tier)    mesh, transform and tint from the PDA_Opponent row; sunk in the sand until Rise
  PickIntent(bOpening) a random ticket from the row's pool for the Tier, or PoolEnraged under 30% left
  AddProgress(Delta)   progress towards wearing it; a ripple on any change; Defeated at Resistance
  StatusLine(bRevealed) the line the battle UI shows under its name
  Rise / Lunge / Equip  latent motion: out of the sand, a lunge at the Nightmare, and the snap onto the hero
Placeholder meshes swap for the character lane's rigged garments by changing Data.Mesh only."""
import unreal

exec(open('P:/FoA/Tools/Unreal/encounter/enc_graph.py').read())
BP = f'{ENC}/BP_Garment'
SELF = lambda f: self_call(BP, f)  # noqa: E731
SC, PC_ = '/Script/Engine.SceneComponent', '/Script/Engine.PrimitiveComponent'
SUNK = '(X=0.0,Y=0.0,Z=-230.0)'


def T(name):
    return BEL.get_basic_type_by_name(name)


def band(g, y0, y1):
    """Nodes whose top edge lies in [y0, y1): one row of the event graph."""
    return [n for n in g.ed.list_all_nodes() if y0 <= BEL.get_node_pos(n).y < y1]


def skeleton():
    EAL = unreal.EditorAssetLibrary
    bp = unreal.load_asset(BP) if EAL.does_asset_exist(BP) else BEL.create_blueprint_asset_with_parent(BP, unreal.Actor)
    unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(bp)
    ensure_vars_nc(BP, [
        ('Data', BEL.get_object_reference_type(unreal.load_class(None, OPP_C)), '', 'Garment', True),
        ('Tier', T('int'), '2', 'Garment', True),
        ('Progress', T('int'), '0', 'Garment|State', False),
        ('Intent', BEL.get_object_reference_type(unreal.load_class(None, MOVE_C)), '', 'Garment|State', False),
        ('State', T('name'), 'Idle', 'Garment|State', False),
        ('Body', BEL.get_object_reference_type(unreal.SceneComponent), '', 'Garment|State', False),
    ])
    sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    handles = sds.k2_gather_subobject_data_for_blueprint(bp)
    lib = unreal.SubobjectDataBlueprintFunctionLibrary
    names = {str(lib.get_variable_name(lib.get_data(h))): h for h in handles}
    for name, cls in (('Mesh', unreal.StaticMeshComponent), ('Rig', unreal.SkeletalMeshComponent)):
        if name not in names:
            h, fail = sds.add_new_subobject(unreal.AddNewSubobjectParams(
                parent_handle=names.get('DefaultSceneRoot', handles[0]), new_class=cls, blueprint_context=bp))
            assert not str(fail), fail
            sds.rename_subobject(h, unreal.Text(name))
            names[name] = h
        comp = lib.get_object(lib.get_data(names[name]))  # deprecated, but returns the SCS template we edit
        comp.set_collision_profile_name('NoCollision')
        comp.set_editor_property('relative_location', unreal.Vector(0, 0, -230))
        comp.set_editor_property('hidden_in_game', True)
    print('garment skeleton ok')


def sigs():
    move = BEL.get_object_reference_type(unreal.load_class(None, MOVE_C))
    opp = BEL.get_object_reference_type(unreal.load_class(None, OPP_C))
    return {'IsEnraged': ((), (('bEnraged', T('bool')),), True), 'IsAlive': ((), (('bAlive', T('bool')),), True),
            'Pool': ((), (('Moves', BEL.get_array_type(move)),), True),
            'PickIntent': ((('bOpening', T('bool')),), (), False),
            'Setup': ((('InData', opp), ('InTier', T('int'))), (), False),
            'AddProgress': ((('Delta', T('int')),), (('bDefeated', T('bool')),), False),
            'StatusLine': ((('bRevealed', T('bool')),), (('Line', T('text')),), True)}


def stubs():
    """Empty function graphs and custom events; the obsolete Weight function goes (MoveWeights became pools)."""
    unreal.get_editor_subsystem(unreal.EditorActorSubsystem).select_nothing()
    bp = unreal.load_asset(BP)
    unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(bp)
    if 'Weight' in [str(n) for n in BEL.list_graph_names(bp)]:
        BEL.remove_function_graph(bp, 'Weight')
    stub_functions(BP, sigs())
    stub_events(BP, ('Rise', 'Lunge', 'Equip'))
    print('garment stubs ok: now Hayba blueprint_compile BP_Garment')


def functions():
    move = BEL.get_object_reference_type(unreal.load_class(None, MOVE_C))
    opp = BEL.get_object_reference_type(unreal.load_class(None, OPP_C))

    # Enraged() -> bool: under 30% of the garment left to win
    g, e, r = new_function(BP, 'IsEnraged', [], [('bEnraged', T('bool'))], pure=True)
    g.at(e, 0, 0)
    res = field(g, mget(g, 'Data', 0, 200), 'Resistance', OPP_C, 200, 200)
    left = fcall(g, f'{KML}:Subtract_IntInt', 480, 160, A=res, B=mget(g, 'Progress', 260, 320))
    lim = fcall(g, f'{KML}:Multiply_DoubleDouble', 480, 320, A=fcall(g, f'{KML}:Conv_IntToDouble', 260, 420, InInt=res),
                B=0.3)
    lt = fcall(g, f'{KML}:Less_DoubleDouble', 760, 200, A=fcall(g, f'{KML}:Conv_IntToDouble', 620, 100, InInt=left),
               B=lim)
    g.at(r, 1000, 0)
    go(e, r)
    feed(r, bEnraged=lt)
    box(g, 'Enraged', 'Less than 30% of the garment left to win: it fights from the W column.', g.ed.list_all_nodes(),
        'data')

    # IsAlive() -> bool
    g, e, r = new_function(BP, 'IsAlive', [], [('bAlive', T('bool'))], pure=True)
    g.at(e, 0, 0)
    ne = fcall(g, f'{KML}:NotEqual_NameName', 260, 160, A=mget(g, 'State', 40, 200), B='Defeated')
    g.at(r, 520, 0)
    go(e, r)
    feed(r, bAlive=ne)
    box(g, 'Alive', 'Still fighting (not yet worn).', g.ed.list_all_nodes(), 'data')

    # Pool() -> Moves: this turn's ticket pool (a move's tickets are its weight; one random ticket is a weighted pick)
    g, e, r = new_function(BP, 'Pool', [], [('Moves', BEL.get_array_type(move))], pure=True)
    g.at(e, 0, 0)
    data = mget(g, 'Data', 0, 300)
    rage = fcall(g, SELF('IsEnraged'), 0, 160)
    col = fcall(g, f'{KML}:SelectInt', 260, 160, A=3, B=mget(g, 'Tier', 40, 440), bPickA=po(rage, 'bEnraged'))
    prev, nodes = e, []
    for i, (val_, pool) in enumerate(((3, 'PoolEnraged'), (0, 'PoolPlausible'), (1, 'PoolSuspicious'))):
        x = 560 + i * 560
        br = g.at(g.ed.add_branch_node(), x, 0)
        wire(po(fcall(g, f'{KML}:EqualEqual_IntInt', x - 220, 260, A=col, B=val_)), BEL.find_condition_pin(br))
        ret = r if i == 0 else g.at(g.ed.add_return_node(), x + 260, -200)
        g.at(ret, x + 260, -200)
        wire(po(field(g, data, pool, OPP_C, x + 20, -320)), pi(ret, 'Moves'))
        go(prev, br) if prev is e else go(prev, br, 'else')
        go(br, ret)
        prev = br
    last = g.at(g.ed.add_return_node(), 2300, 160)
    wire(po(field(g, data, 'PoolOpen', OPP_C, 2060, 300)), pi(last, 'Moves'))
    go(prev, last, 'else')
    box(g, 'Ticket pool', 'Enraged (under 30% left) draws from PoolEnraged, otherwise the pool for the Tier: Plausible, '
        'Suspicious or Open.', g.ed.list_all_nodes(), 'data')

    # PickIntent(bOpening): the move it will make next turn
    g, e, _ = new_function(BP, 'PickIntent', [('bOpening', T('bool'))])
    g.at(e, 0, 0)
    data = mget(g, 'Data', 0, 300)
    opening = field(g, data, 'OpeningMove', OPP_C, 200, 420)
    use = fcall(g, f'{KML}:BooleanAND', 700, 300, A=po(e, 'bOpening'),
                B=fcall(g, f'{KSL}:IsValid', 460, 420, Object=opening))
    br = g.at(g.ed.add_branch_node(), 300, 0)
    wire(po(use), BEL.find_condition_pin(br))
    set_open = mset(g, 'Intent', 600, -180, opening)
    rnd = fcall(g, f'{KAL}:Array_Random', 600, 160, TargetArray=po(fcall(g, SELF('Pool'), 420, 300), 'Moves'))
    set_rnd = mset(g, 'Intent', 900, 120, po(rnd, 'OutItem'))
    tel = field(g, mget(g, 'Intent', 1100, 300), 'bTelegraphed', MOVE_C, 1300, 300)
    ss = mset(g, 'State', 1500, 0, fcall(g, f'{KML}:SelectName', 1300, 420, A='Telegraph', B='Idle', bPickA=tel))
    go(e, br)
    go(br, set_open)
    go(set_open, ss)
    go(br, rnd, 'else') if impure(rnd) else go(br, set_rnd, 'else')
    seq(rnd, set_rnd, ss)
    box(g, 'Pick the next move', 'The opening move on a later day, else a random ticket from the pool for this turn. A '
        'telegraphed move announces itself a turn early.', g.ed.list_all_nodes(), 'turn')

    # Setup(InData, InTier)
    g, e, _ = new_function(BP, 'Setup', [('InData', opp), ('InTier', T('int'))])
    g.at(e, 0, 0)
    sd = mset(g, 'Data', 260, 0, po(e, 'InData'))
    stt = mset(g, 'Tier', 520, 0, po(e, 'InTier'))
    sp = mset(g, 'Progress', 780, 0, 0)
    ss = mset(g, 'State', 1040, 0, 'Idle')
    mesh = mget(g, 'Mesh', 1100, 300)
    sm = fcall(g, '/Script/Engine.StaticMeshComponent:SetStaticMesh', 1300, 0, self=mesh,
               NewMesh=field(g, po(sd), 'Mesh', OPP_C, 1100, 420))
    mat = fcall(g, f'{PC_}:SetMaterial', 1450, -160, self=mesh, ElementIndex=0,
                Material='/Game/FoA/Gameplay/Encounter/M_OpponentSway.M_OpponentSway')         if unreal.EditorAssetLibrary.does_asset_exist('/Game/FoA/Gameplay/Encounter/M_OpponentSway') else None
    tint = field(g, po(sd), 'Tint', OPP_C, 1700, 540)
    tv = fcall(g, f'{PC_}:SetCustomPrimitiveDataVector3', 1900, 0, self=mesh, DataIndex=1,
               Value=fcall(g, '/Script/Engine.KismetMathLibrary:Conv_LinearColorToVector', 2000, 420, InLinearColor=tint))
    chain(*[n for n in (e, sd, stt, sp, ss, sm, mat, tv) if n is not None])
    # the body: the character lane's rig when the row has one (it keeps its own materials), else the placeholder
    rig = field(g, po(sd), 'Rig', OPP_C, 2440, 420)
    has = fcall(g, f'{KSL}:IsValid', 2680, 420, Object=rig)
    brr = g.at(g.ed.add_branch_node(), 2900, 0)
    wire(po(has), BEL.find_condition_pin(brr))
    rigc = mget(g, 'Rig', 2900, 560)
    srig = fcall(g, '/Script/Engine.SkinnedMeshComponent:SetSkinnedAssetAndUpdate', 3160, -160, self=rigc, NewMesh=rig)
    b_rig = mset(g, 'Body', 3460, -160, rigc)
    b_mesh = mset(g, 'Body', 3460, 160, mget(g, 'Mesh', 3260, 300))
    body = mget(g, 'Body', 3700, 300)
    xf2 = fcall(g, f'{SC}:K2_SetRelativeTransform', 3940, 0, self=body,
                NewTransform=field(g, po(sd), 'MeshTransform', OPP_C, 3700, 420))
    sink2 = fcall(g, f'{SC}:K2_AddRelativeLocation', 4240, 0, self=body, DeltaLocation=SUNK)
    hide2 = fcall(g, f'{SC}:SetHiddenInGame', 4540, 0, self=body, NewHidden='true')
    go(tv, brr)
    go(brr, srig)
    go(srig, b_rig)
    go(brr, b_mesh, 'else')
    go(b_rig, xf2)
    go(b_mesh, xf2)
    chain(xf2, sink2, hide2)
    box(g, 'Set up from the row', 'Placeholder mesh with the shared cloth material and tint (custom primitive data 1-3), '
        'or the rigged garment when the row has one; that body is sunk in the sand and hidden until Rise.',
        g.ed.list_all_nodes(), 'data')

    # AddProgress(Delta) -> bDefeated
    g, e, r = new_function(BP, 'AddProgress', [('Delta', T('int'))], [('bDefeated', T('bool'))])
    g.at(e, 0, 0)
    res = field(g, mget(g, 'Data', 120, 420), 'Resistance', OPP_C, 300, 420)
    add = fcall(g, f'{KML}:Add_IntInt', 300, 220, A=mget(g, 'Progress', 100, 200), B=po(e, 'Delta'))
    cl = fcall(g, f'{KML}:Clamp', 560, 220, Value=add, Min=0, Max=res)
    sp = mset(g, 'Progress', 820, 0, cl)
    hit = fcall(g, f'{PC_}:SetCustomPrimitiveDataFloat', 1100, 0, self=mget(g, 'Mesh', 900, 220), DataIndex=0,
                Value=fcall(g, f'{GS}:GetTimeSeconds', 900, 340))
    done_ = fcall(g, f'{KML}:GreaterEqual_IntInt', 1100, 300, A=po(sp), B=res)
    br = g.at(g.ed.add_branch_node(), 1400, 0)
    wire(po(done_), BEL.find_condition_pin(br))
    sd = mset(g, 'State', 1660, -100, 'Defeated')
    g.at(r, 1960, 0)
    feed(r, bDefeated=done_)
    chain(e, sp, hit, br)
    go(br, sd)
    go(sd, r)
    go(br, r, 'else')
    box(g, 'Progress', 'Clamped to 0..Resistance; the cloth ripples (custom primitive data 0 = hit time); worn at '
        'Resistance.', g.ed.list_all_nodes(), 'turn')

    # StatusLine(bRevealed) -> Line, for the battle UI
    g, e, r = new_function(BP, 'StatusLine', [('bRevealed', T('bool'))], [('Line', T('text'))], pure=True)
    g.at(e, 0, 0)
    state = mget(g, 'State', 0, 240)
    intent = mget(g, 'Intent', 0, 520)
    rows = (('Defeated', 'Worn.'), ('Stunned', 'Stunned for a turn.'))
    nodes = [e, state, intent]
    prev, y = e, 0
    for i, (st, line) in enumerate(rows):
        br = g.at(g.ed.add_branch_node(), 300 + i * 560, y)
        wire(po(fcall(g, f'{KML}:EqualEqual_NameName', 60 + i * 560, 160, A=state, B=st)), BEL.find_condition_pin(br))
        ret = g.at(g.ed.add_return_node(), 560 + i * 560, y - 200)
        val(ret, 'Line', line)
        go(prev, br) if prev is e else go(prev, br, 'else')
        go(br, ret)
        nodes += [br, ret]
        prev = br
    tel = fcall(g, f'{KML}:EqualEqual_NameName', 1180, 300, A=state, B='Telegraph')
    br = g.at(g.ed.add_branch_node(), 1420, 0)
    wire(po(tel), BEL.find_condition_pin(br))
    go(prev, br, 'else')
    ret_t = g.at(g.ed.add_return_node(), 1700, -200)
    wire(po(field(g, intent, 'TelegraphLine', MOVE_C, 1420, 520)), pi(ret_t, 'Line'))
    br2 = g.at(g.ed.add_branch_node(), 1700, 120)
    wire(po(e, 'bRevealed'), BEL.find_condition_pin(br2))
    fmt = make(g, 1700, 420, 'Format Text')
    val(fmt, 'Format', 'Next, {Move}.')
    wire(po(field(g, intent, 'DisplayName', MOVE_C, 1460, 640)), pi(fmt, 'Move'))
    ret_r = g.at(g.ed.add_return_node(), 2000, 60)
    wire(po(fmt), pi(ret_r, 'Line'))
    g.at(r, 2000, 300)
    go(br, ret_t)
    go(br, br2, 'else')
    go(br2, ret_r)
    go(br2, r, 'else')
    box(g, 'Status line', 'Worn, stunned, the telegraph line, or (after Check Mirror) its next move; empty otherwise.',
        g.ed.list_all_nodes(), 'stage')


def events():
    g = Graph(BP).clear()
    mesh = lambda x, y: mget(g, 'Body', x, y)  # noqa: E731  (the rig or the placeholder, chosen in Setup)
    # Rise: out of the sand to the row's transform
    rise = g.custom_event('Rise', 0, 0)
    show = fcall(g, f'{SC}:SetHiddenInGame', 300, 0, self=mesh(100, 200), NewHidden='false')
    xf = field(g, mget(g, 'Data', 300, 320), 'MeshTransform', OPP_C, 500, 320)
    brk = fcall(g, f'{KML}:BreakTransform', 760, 320, InTransform=xf)
    mv = fcall(g, f'{KSL}:MoveComponentTo', 1040, 0, Component=mesh(840, 200), TargetRelativeLocation=po(brk, 'Location'),
               TargetRelativeRotation=po(brk, 'Rotation'), bEaseOut='true', OverTime=1.2)
    go(rise, show)
    wire(BEL.find_then_pin(show), pi(mv, 'Move'))
    box(g, 'Rise', 'Out of the black sand to its place in the line.', band(g, -100, 500), 'stage')

    # Lunge: at the Nightmare (local -X) and back
    y = 860
    lunge = g.custom_event('Lunge', 0, y)
    xf2 = field(g, mget(g, 'Data', 0, y + 260), 'MeshTransform', OPP_C, 200, y + 260)
    brk2 = fcall(g, f'{KML}:BreakTransform', 440, y + 260, InTransform=xf2)
    fwd = fcall(g, f'{KML}:Add_VectorVector', 700, y + 220, A=po(brk2, 'Location'), B='(X=-90.0,Y=0.0,Z=10.0)')
    m1 = fcall(g, f'{KSL}:MoveComponentTo', 960, y, Component=mesh(760, y + 120), TargetRelativeLocation=fwd,
               TargetRelativeRotation=po(brk2, 'Rotation'), bEaseIn='true', OverTime=0.18)
    m2 = fcall(g, f'{KSL}:MoveComponentTo', 1400, y, Component=mesh(1200, y + 120),
               TargetRelativeLocation=po(brk2, 'Location'), TargetRelativeRotation=po(brk2, 'Rotation'),
               bEaseOut='true', OverTime=0.45)
    anim = field(g, mget(g, 'Data', 300, y - 260), 'AttackAnim', OPP_C, 500, y - 260)
    bra = g.at(g.ed.add_branch_node(), 300, y - 120)
    wire(po(fcall(g, f'{KSL}:IsValid', 700, y - 260, Object=anim)), BEL.find_condition_pin(bra))
    play = fcall(g, '/Script/Engine.SkeletalMeshComponent:PlayAnimation', 620, y - 120, self=mget(g, 'Rig', 420, y + 40),
                 NewAnimToPlay=anim, bLooping='false')
    go(lunge, bra)
    go(bra, play)
    wire(BEL.find_then_pin(play), pi(m1, 'Move'))
    wire(po(bra, 'else'), pi(m1, 'Move'))
    wire(po(m1, 'Completed'), pi(m2, 'Move'))
    nodes = band(g, y - 300, y + 500)
    box(g, 'Lunge', 'The rig plays its attack clip (Lash, Kick, CoilStrike, Hop) while the body strikes at the '
        'Nightmare and settles back.', nodes, 'turn')

    # Equip: snap onto the hero like RPG equipment, then hand over to the worn piece
    y = 1500
    eq = g.custom_event('Equip', 0, y)
    hero = fcall(g, f'{GS}:GetPlayerPawn', 40, y + 260, PlayerIndex=0)
    hero_mesh = fcall(g, '/Script/Engine.Actor:GetComponentByClass', 260, y + 260, self=hero,
                      ComponentClass='/Script/Engine.SkeletalMeshComponent')
    att = fcall(g, f'{SC}:K2_AttachToComponent', 600, y, self=mesh(400, y + 120), Parent=po(hero_mesh),
                SocketName=field(g, mget(g, 'Data', 400, y + 420), 'EquipSocket', OPP_C, 600, y + 420),
                LocationRule='KeepWorld', RotationRule='KeepWorld', ScaleRule='KeepWorld')
    snap = fcall(g, f'{KSL}:MoveComponentTo', 1000, y, Component=mesh(800, y + 160),
                 TargetRelativeLocation='(X=0.0,Y=0.0,Z=0.0)', TargetRelativeRotation='(Pitch=0.0,Yaw=0.0,Roll=0.0)',
                 bEaseIn='true', OverTime=0.35)
    hide = fcall(g, f'{SC}:SetHiddenInGame', 1400, y, self=mesh(1200, y + 160), NewHidden='true')
    seq(eq, hero_mesh, att)  # GetComponentByClass may be impure: keep it on the exec path
    wire(BEL.find_then_pin(att), pi(snap, 'Move'))
    wire(po(snap, 'Completed'), pi(hide, 'execute'))
    nodes = band(g, y - 50, y + 600)
    box(g, 'Equip', 'Worn: the garment snaps onto its socket on the hero, then hides; the worn piece belongs to the '
        'hero (OnGarmentEquipped).', nodes, 'outcome')
    print('garment events ok: now Hayba blueprint_compile and asset_save')


import os  # noqa: E402
for _p in os.environ.get('FOA_PHASE', 'skeleton,stubs').split(','):
    {'skeleton': skeleton, 'stubs': stubs, 'functions': functions, 'events': events}[_p]()

if ('events' in os.environ.get('FOA_PHASE', '').split(',')
        and 'bMotionActive' in [str(n) for n in BEL.list_member_variable_names(unreal.load_asset(BP))]):
    import runpy as _motion_runpy
    _motion_old_phase = os.environ.get('FOA_MOTION_PHASE')
    try:
        os.environ['FOA_MOTION_PHASE'] = 'body'
        _motion_runpy.run_path('P:/FoA/Tools/Unreal/encounter/battle_motion.py', run_name='__main__')
    finally:
        if _motion_old_phase is None:
            os.environ.pop('FOA_MOTION_PHASE', None)
        else:
            os.environ['FOA_MOTION_PHASE'] = _motion_old_phase
