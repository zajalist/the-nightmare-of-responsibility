"""Story lane (main's GO, 2026-11-10): the user's battle bug "when they get eliminated they move back to recenter in
the battle in front of him". Run via ue_remote.py in three steps (Hayba compiles and saves between them); the
exec rewiring of the two existing chains is fix_equip_rewire.py (Hayba batches).
  FOA_STEP=declare   BP_Garment vars WearFrom/WearAt/GlideFrom/GlideGoal/GlideAt, function stubs; BP_Encounter
                     dispatcher OnGarmentWorn(Garment, Location, Socket) and stubs GarmentWorn / Respace / RespaceFrom
  FOA_STEP=garment   WearTarget (pure): Data.EquipSocket on his Mesh (his origin + 40 cm up when the socket is missing)
                     FlyToWear: stops the battle flight WITHOUT the MotionHome restore (the old StopBattleMotion
                       teleported the actor back to its slot first), then a 60 Hz StepWearFlight timer
                     StepWearFlight: 0.45 s eased arc (30 cm lift at mid-flight) from where the Body was to the slot,
                       re-aimed every frame at his live socket; on arrival the Body hides WITH its children (the old
                       SetHiddenInGame left attached parts flying) and BP_Encounter.GarmentWorn runs
                     GlideHome(NewLocation) / StepGlide: MotionHome eases there in 0.6 s (the flight follows it; the actor
                       itself moves when the flight is off)
  FOA_STEP=encounter GarmentWorn: BP_FoAPlayer.Equip(GarmentId) (his worn piece appears on the arrival frame, not at the
                       defeat), CueSandBurst (the sand SFX, moved here from the defeat frame), OnGarmentWorn broadcast
                       (world's arrival burst, horror's arrival SFX bind to it)
                     Respace -> RespaceFrom(Index, Slot): the standing garments, in line order, glide to
                       (Slot - (Remaining - 1) / 2) * SlotSpacing along the encounter's local Y, as SpawnFrom placed them
  $env:FOA_AREAS='gameplay'; python Tools/Unreal/ue_remote.py Tools/Unreal/encounter/fix_equip_flight.py FOA_STEP=declare"""
import os

exec(open('P:/FoA/Tools/Unreal/encounter/enc_graph.py').read())  # noqa: S102  house graph helpers
import unreal  # noqa: E402

GB = f'{ENC}/BP_Garment'
EB = f'{ENC}/BP_Encounter'
G_C = GB + '.BP_Garment_C'
E_C = EB + '.BP_Encounter_C'
PLAYER_C = '/Game/FoA/Characters/Player/BP_FoAPlayer.BP_FoAPlayer_C'
SC = '/Script/Engine.SceneComponent'
ACT = '/Script/Engine.Actor'
FLIGHT, LIFT, GLIDE, HZ = 0.45, 30.0, 0.6, 0.0167
T = BEL.get_basic_type_by_name
VEC = BEL.get_struct_type(unreal.Vector.static_struct())
GAR = BEL.get_object_reference_type(unreal.load_class(None, G_C))
ACTOR_T = BEL.get_object_reference_type(unreal.Actor)
STEP = os.environ.get('FOA_STEP', '')


def now(g, x, y):
    return fcall(g, f'{GS}:GetTimeSeconds', x, y)


def alpha(g, start_var, seconds, x, y):
    """clamp((now - start) / seconds, 0, 1) -> (raw clamp node, eased node)"""
    el = fcall(g, f'{KML}:Subtract_DoubleDouble', x + 220, y, A=now(g, x, y), B=mget(g, start_var, x, y + 140))
    raw = fcall(g, f'{KML}:FClamp', x + 660, y, Value=fcall(g, f'{KML}:Divide_DoubleDouble', x + 440, y, A=el, B=seconds),
                Min=0.0, Max=1.0)
    ease = fcall(g, f'{KML}:FInterpEaseInOut', x + 880, y, A=0.0, B=1.0, Alpha=raw, Exponent=2.0)
    return raw, ease


def declare():
    ensure_vars_nc(GB, [('WearFrom', VEC, '', 'Flight', False), ('WearAt', T('real'), '0.0', 'Flight', False),
                        ('GlideFrom', VEC, '', 'Flight', False), ('GlideGoal', VEC, '', 'Flight', False),
                        ('GlideAt', T('real'), '0.0', 'Flight', False)])
    stub_functions(GB, {'WearTarget': ((), (('Location', VEC), ('Socket', T('name'))), True),
                        'FlyToWear': ((), (), False), 'StepWearFlight': ((), (), False),
                        'GlideHome': ((('NewLocation', VEC),), (), False), 'StepGlide': ((), (), False)})
    bp = unreal.load_asset(EB)
    if 'OnGarmentWorn' not in [str(n) for n in BEL.list_event_dispatchers(bp)]:
        assert BEL.add_event_dispatcher(bp, 'OnGarmentWorn')
        for pn, pt in (('Garment', ACTOR_T), ('Location', VEC), ('Socket', T('name'))):
            BEL.add_event_dispatcher_parameter(bp, 'OnGarmentWorn', pn, pt)
    stub_functions(EB, {'GarmentWorn': ((('Garment', GAR), ('Location', VEC), ('Socket', T('name'))), (), False),
                        'Respace': ((), (), False), 'RespaceFrom': ((('Index', T('int')), ('Slot', T('int'))), (), False)})
    print('declare ok: now Hayba blueprint_compile both')


def garment():
    # WearTarget: his own slot for this garment
    g, e, r = new_function(GB, 'WearTarget', (), (('Location', VEC), ('Socket', T('name'))), pure=True)
    g.at(e, 0, 0)
    pawn = fcall(g, f'{GS}:GetPlayerCharacter', 0, 200, PlayerIndex=0)
    mesh = field(g, pawn, 'Mesh', '/Script/Engine.Character', 260, 200)
    sock = field(g, mget(g, 'Data', 0, 420), 'EquipSocket', OPP_C, 260, 420)
    has = fcall(g, f'{SC}:DoesSocketExist', 560, 300, self=po(mesh), InSocketName=po(sock))
    at = fcall(g, f'{SC}:GetSocketLocation', 560, 100, self=po(mesh), InSocketName=po(sock))
    up = fcall(g, f'{KML}:Add_VectorVector', 560, 500, A=fcall(g, f'{ACT}:K2_GetActorLocation', 300, 600, self=po(pawn)),
               B='(X=0.0,Y=0.0,Z=40.0)')
    pick = fcall(g, f'{KML}:SelectVector', 860, 200, A=at, B=up, bPickA=has)
    feed(r, Location=pick, Socket=po(sock))
    go(e, r)  # a function's outputs are only written when its entry's exec reaches the result node
    box(g, 'His slot for it', 'Data.EquipSocket on his Mesh; his origin + 40 cm when the socket is missing.',
        g.ed.list_all_nodes(), 'outcome')

    # FlyToWear: leave the line where it is (no MotionHome restore), start the flight timer
    g, e, _ = new_function(GB, 'FlyToWear')
    g.at(e, 0, 0)
    clear = fcall(g, f'{KSL}:K2_ClearTimer', 260, 0, FunctionName='StepBattleMotion')
    off = mset(g, 'bMotionActive', 560, 0)
    val(off, 'bMotionActive', 'false')
    contact = fcall(g, self_call(GB, 'StopPlayerContact'), 820, 0)
    frm = mset(g, 'WearFrom', 1100, 0, fcall(g, f'{SC}:K2_GetComponentLocation', 900, 220, self=po(mget(g, 'Body', 700, 220))))
    at = mset(g, 'WearAt', 1400, 0, now(g, 1200, 220))
    tick = fcall(g, f'{KSL}:K2_SetTimer', 1700, 0, FunctionName='StepWearFlight', Time=HZ, bLooping='true')
    chain(e, clear, off, contact, frm, at, tick)
    box(g, 'Off to be worn', 'The battle flight stops where it is; the wear flight starts.', g.ed.list_all_nodes(),
        'outcome')

    # StepWearFlight: eased arc to his live slot; on arrival hide (with children) and hand over to the encounter
    g, e, _ = new_function(GB, 'StepWearFlight')
    g.at(e, 0, 0)
    raw, ease = alpha(g, 'WearAt', FLIGHT, 0, 300)
    goal = fcall(g, self_call(GB, 'WearTarget'), 600, 600)
    path = fcall(g, f'{KML}:VLerp', 1200, 450, A=mget(g, 'WearFrom', 1000, 450), B=po(goal, 'Location'), Alpha=ease)
    arc = fcall(g, f'{KML}:Multiply_DoubleDouble', 1200, 700,  # promotable operators: wire A before a literal B
                A=fcall(g, f'{KML}:Sin', 1000, 700, A=fcall(g, f'{KML}:Multiply_DoubleDouble', 900, 800, A=raw, B=3.14159265)),
                B=LIFT)
    lift = fcall(g, f'{KML}:MakeVector', 1400, 700, X=0.0, Y=0.0, Z=arc)
    there = fcall(g, f'{KML}:Add_VectorVector', 1600, 450, A=path, B=lift)
    body = mget(g, 'Body', 1600, 250)
    move = fcall(g, f'{SC}:K2_SetWorldLocation', 1850, 0, self=po(body), NewLocation=there, bSweep='false', bTeleport='true')
    br = g.at(g.ed.add_branch_node(), 2150, 0)
    wire(po(fcall(g, f'{KML}:GreaterEqual_DoubleDouble', 1950, 250, A=raw, B=1.0)), BEL.find_condition_pin(br))
    stop = fcall(g, f'{KSL}:K2_ClearTimer', 2400, 0, FunctionName='StepWearFlight')
    hide = fcall(g, f'{SC}:SetHiddenInGame', 2700, 0, self=po(mget(g, 'Body', 2500, 220)), NewHidden='true',
                 bPropagateToChildren='true')
    enc = fcall(g, f'{GS}:GetActorOfClass', 3000, 0, ActorClass=E_C)
    worn = g.call(f'{E_C}:GarmentWorn', 3300, 0)
    wire(po(enc), pi(worn, 'self'))
    wire(po(make(g, 3100, 300, 'reference', 'self')), pi(worn, 'Garment'))
    wire(po(goal, 'Location'), pi(worn, 'Location'))
    wire(po(goal, 'Socket'), pi(worn, 'Socket'))
    chain(e, move, br)
    go(br, stop)
    chain(stop, hide, enc, worn)
    box(g, 'Flight to his slot', 'Eased 0.45 s arc to his live slot; on arrival hidden with its children, then worn.',
        g.ed.list_all_nodes(), 'outcome')

    # GlideHome(NewLocation): MotionHome eases there
    g, e, _ = new_function(GB, 'GlideHome', (('NewLocation', VEC),))
    g.at(e, 0, 0)
    home = fcall(g, f'{KML}:BreakTransform', 200, 250, InTransform=po(mget(g, 'MotionHome', 0, 250)))
    frm = mset(g, 'GlideFrom', 500, 0, po(home, 'Location'))
    goal = mset(g, 'GlideGoal', 800, 0, po(e, 'NewLocation'))
    at = mset(g, 'GlideAt', 1100, 0, now(g, 900, 250))
    tick = fcall(g, f'{KSL}:K2_SetTimer', 1400, 0, FunctionName='StepGlide', Time=HZ, bLooping='true')
    chain(e, frm, goal, at, tick)
    box(g, 'Glide to a new place', 'The line closes up: MotionHome eases to its new slot.', g.ed.list_all_nodes(), 'stage')

    # StepGlide
    g, e, _ = new_function(GB, 'StepGlide')
    g.at(e, 0, 0)
    raw, ease = alpha(g, 'GlideAt', GLIDE, 0, 400)
    loc = fcall(g, f'{KML}:VLerp', 1200, 400, A=mget(g, 'GlideFrom', 1000, 400), B=mget(g, 'GlideGoal', 1000, 520), Alpha=ease)
    old = fcall(g, f'{KML}:BreakTransform', 1200, 700, InTransform=po(mget(g, 'MotionHome', 1000, 700)))
    xf = fcall(g, f'{KML}:MakeTransform', 1450, 500, Location=loc, Rotation=po(old, 'Rotation'), Scale=po(old, 'Scale'))
    seth = mset(g, 'MotionHome', 1700, 0, xf)
    flying = g.at(g.ed.add_branch_node(), 2000, 0)
    wire(po(mget(g, 'bMotionActive', 1800, 250)), BEL.find_condition_pin(flying))
    place = fcall(g, f'{ACT}:K2_SetActorLocation', 2300, 150, NewLocation=loc, bSweep='false', bTeleport='true')
    done = g.at(g.ed.add_branch_node(), 2600, 0)
    wire(po(fcall(g, f'{KML}:GreaterEqual_DoubleDouble', 2400, 300, A=raw, B=1.0)), BEL.find_condition_pin(done))
    stop = fcall(g, f'{KSL}:K2_ClearTimer', 2900, 0, FunctionName='StepGlide')
    chain(e, seth, flying)
    go(flying, done)
    go(flying, place, 'else')
    go(place, done)
    go(done, stop)
    box(g, 'Glide step', 'MotionHome eases (the flight follows it); the actor itself when the flight is off.',
        g.ed.list_all_nodes(), 'stage')
    print('garment ok: now Hayba blueprint_compile + asset_save BP_Garment')


def encounter():
    # GarmentWorn(Garment, Location, Socket)
    g, e, _ = new_function(EB, 'GarmentWorn', (('Garment', GAR), ('Location', VEC), ('Socket', T('name'))))
    g.at(e, 0, 0)
    cast = make(g, 260, 0, 'CastToBP_FoAPlayer')
    feed(cast, Object=fcall(g, f'{GS}:GetPlayerPawn', 60, 220, PlayerIndex=0))
    wear = fcall(g, f'{PLAYER_C}:Equip', 600, 0, self=as_pin(cast),
                 GarmentId=field(g, field(g, po(e, 'Garment'), 'Data', G_C, 300, 400), 'GarmentId', OPP_C, 450, 400))
    cue = g.call(self_call(EB, 'CueSandBurst'), 950, 0)
    tell = make(g, 1250, 0, 'Call', 'OnGarmentWorn')
    feed(tell, Garment=po(e, 'Garment'), Location=po(e, 'Location'), Socket=po(e, 'Socket'))
    chain(e, cast, wear, cue, tell)
    go(cast, cue, 'CastFailed')
    box(g, 'Worn on arrival', 'His worn piece appears, the sand cue plays, world and horror hear OnGarmentWorn.',
        g.ed.list_all_nodes(), 'outcome')

    g, e, _ = new_function(EB, 'Respace')
    g.at(e, 0, 0)
    chain(e, fcall(g, self_call(EB, 'RespaceFrom'), 300, 0, Index=0, Slot=0))
    box(g, 'Close the line', 'The standing garments glide to an even, centred line.', g.ed.list_all_nodes(), 'stage')

    g, e, _ = new_function(EB, 'RespaceFrom', (('Index', T('int')), ('Slot', T('int'))))
    g.at(e, 0, 0)
    gars = mget(g, 'Garments', -200, 300)
    br = g.at(g.ed.add_branch_node(), 260, 0)
    wire(po(fcall(g, f'{KML}:Less_IntInt', 40, 300, A=po(e, 'Index'),
                  B=fcall(g, f'{KAL}:Array_Length', -160, 420, TargetArray=gars))), BEL.find_condition_pin(br))
    gm = po(fcall(g, f'{KAL}:Array_Get', 260, 500, TargetArray=mget(g, 'Garments', 60, 560), Index=po(e, 'Index')), 'Item')
    alive = g.call(f'{G_C}:IsAlive', 520, 500)
    wire(gm, pi(alive, 'self'))
    br2 = g.at(g.ed.add_branch_node(), 560, 0)
    wire(po(alive, 'bAlive'), BEL.find_condition_pin(br2))
    mid = fcall(g, f'{KML}:Multiply_DoubleDouble', 560, 800,
                A=fcall(g, f'{KML}:Conv_IntToDouble', 360, 800,
                        InInt=fcall(g, f'{KML}:Subtract_IntInt', 160, 800, A=mget(g, 'Remaining', -40, 800), B=1)), B=0.5)
    y = fcall(g, f'{KML}:Multiply_DoubleDouble', 1000, 700,
              A=fcall(g, f'{KML}:Subtract_DoubleDouble', 800, 700,
                      A=fcall(g, f'{KML}:Conv_IntToDouble', 600, 650, InInt=po(e, 'Slot')), B=mid),
              B=mget(g, 'SlotSpacing', 800, 900))
    world = fcall(g, f'{KML}:TransformLocation', 1250, 600, T=fcall(g, f'{ACT}:GetTransform', 1000, 900),
                  Location=fcall(g, f'{KML}:MakeVector', 1150, 750, X=0.0, Y=y, Z=0.0))
    glide = g.call(f'{G_C}:GlideHome', 900, 0)
    wire(gm, pi(glide, 'self'))
    wire(po(world), pi(glide, 'NewLocation'))
    nxt = lambda x, y_, slot: fcall(g, self_call(EB, 'RespaceFrom'), x, y_,  # noqa: E731
                                    Index=fcall(g, f'{KML}:Add_IntInt', x - 200, y_ + 200, A=po(e, 'Index'), B=1),
                                    Slot=slot)
    taken = nxt(1500, 0, fcall(g, f'{KML}:Add_IntInt', 1300, 300, A=po(e, 'Slot'), B=1))
    skipped = nxt(1500, -300, po(e, 'Slot'))
    go(e, br)
    go(br, br2)
    go(br2, glide)
    go(glide, taken)
    go(br2, skipped, 'else')
    box(g, 'Next standing garment', 'Standing ones take the next slot, worn ones are skipped (index counter).',
        g.ed.list_all_nodes(), 'stage')
    print('encounter ok: now Hayba blueprint_compile + asset_save BP_Encounter')


{'declare': declare, 'garment': garment, 'encounter': encounter}[STEP]()
