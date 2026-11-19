"""BP_Encounter (level actor): the T8 boss fight as an old-RPG turn-based battle against a party of garments.
  $env:FOA_AGENT='mech_encounter'; python Tools/Unreal/ue_remote.py Tools/Unreal/encounter/build_encounter_bp.py FOA_PHASE=<phases>
Phases, comma-separated, in this order (each rerunnable; every graph it owns is cleared and rebuilt):
  skeleton   asset, components, variables, dispatchers
  rules      MoveCost, CanUseMove, KnowsPattern, TargetGarment, ApplySelf, CycleTarget, PickIntents, ResetStats,
             SpawnParty, ClearParty, BeginTimedInput, ApplyPlayerMove, EnemyAct
  stage      ShowEncounter / CutTo / EndEncounter (needs WBP_Encounter)
  stubs      bare custom events, so the public functions can call them before the event graph exists
  entries    SetState(State), StartEncounter(OpponentId), ChooseMove(Move), Flee(), Items(), SubmitKey, HandleKey
  events     the state machine: S_Intro, S_PlayerCommand, S_ResolvePlayerAction, S_EnemyPhase, S_CheckEnd,
             S_Victory, S_Defeat and their steps (IntroStep, EnemyStep, NextPrompt, AdvancePrompt, PlayerActionDone)
The state is a Name (BattleState) because enums can't be authored from script. SetState broadcasts OnStateChanged and
calls the event named S_<State> on the next tick, so every state is one event and the call stack never grows.
After rules/stubs, run `python Tools/Unreal/encounter/build_move_detail.py` outside Unreal.
That native Hayba phase fills the truthful MoveDetail helper without rebuilding any battle graph."""
import os

import unreal

exec(open('P:/FoA/Tools/Unreal/encounter/enc_graph.py').read())
BP = f'{ENC}/BP_Encounter'
SELF = lambda f: self_call(BP, f)  # noqa: E731
G_C = f'{ENC}/BP_Garment.BP_Garment_C'
GSELF = lambda f: f'{G_C}:{f}'  # noqa: E731
PHASE = os.environ.get('FOA_PHASE', 'skeleton')
WBP_C = f'{ENC}/WBP_Encounter.WBP_Encounter_C'
DIRECTOR_C = '/Game/FoA/Gameplay/BP_BeatDirector.BP_BeatDirector_C'
DREAM_C = '/Game/FoA/PostProcess/BP_DreamDirector.BP_DreamDirector_C'
GI_C = '/Game/FoA/Gameplay/GI_FoA.GI_FoA_C'
PLAYER_C = '/Game/FoA/Characters/Player/BP_FoAPlayer.BP_FoAPlayer_C'
PC_P, CTL_P, SC = '/Script/Engine.PlayerController', '/Script/Engine.Controller', '/Script/Engine.SceneComponent'
STATUS_LABELS = ('((SleeveLabyrinth, "The armhole is lost"), (ArmholeFound, "Armhole found"), '
                 '(Mismatched, "The socks are mismatched"), (TwistedLeg, "A trouser leg is twisted"), '
                 '(Constricted, "The tie is tight"))')
STATES = ('Intro', 'PlayerCommand', 'ResolvePlayerAction', 'EnemyPhase', 'CheckEnd', 'Victory', 'Defeat')
STEPS = ('IntroStep', 'EnemyStep', 'NextPrompt', 'AdvancePrompt', 'PlayerActionDone', 'Shake')


def T(name):
    return BEL.get_basic_type_by_name(name)


def S(struct):
    return BEL.get_struct_type(struct.static_struct())


def band(g, y0, y1, x0=-10 ** 6, x1=10 ** 6):
    """Nodes whose top-left lies in the given rows (and columns): one titled group of a graph."""
    return [n for n in g.ed.list_all_nodes() if y0 <= BEL.get_node_pos(n).y < y1 and x0 <= BEL.get_node_pos(n).x < x1]


SANDFX_C = '/Game/FoA/VFX/Sand/BPL_SandFX.BPL_SandFX_C'


def sand_fx(g, x, y, actor_pin):
    """sandvfx's BPL_SandFX.SpawnSandBurst(actor location, 1.0); not built while the library is missing (rebuild
    'rules' and 'events' when it lands)."""
    if not unreal.load_class(None, SANDFX_C):
        return None
    loc = fcall(g, '/Script/Engine.Actor:K2_GetActorLocation', x - 220, y + 200, self=actor_pin)
    return fcall(g, f'{SANDFX_C}:SpawnSandBurst', x, y, Location=loc, Scale=1.0)


def move_t():
    return BEL.get_object_reference_type(unreal.load_class(None, MOVE_C))


def garment_t():
    return BEL.get_object_reference_type(unreal.load_class(None, G_C))


# ---------------------------------------------------------------- skeleton
def skeleton():
    EAL = unreal.EditorAssetLibrary
    bp = unreal.load_asset(BP) if EAL.does_asset_exist(BP) else BEL.create_blueprint_asset_with_parent(BP, unreal.Actor)
    unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(bp)
    ed = GE.get_graph_editor_by_name(bp, 'EventGraph')
    have = [str(n) for n in BEL.list_member_variable_names(bp)]
    for gone in ('Opponent', 'Buttons', 'NextMove'):  # the single-shirt prototype's state
        if gone in have:
            ed.remove_member_variable(gone)
    move, opp = move_t(), BEL.get_object_reference_type(unreal.load_class(None, OPP_C))
    ensure_vars_nc(BP, [
        ('Opponents', BEL.get_map_type(T('name'), opp),
         '((Shirt, "/Game/FoA/Gameplay/Encounter/Data/DA_Opponent_Shirt.DA_Opponent_Shirt"))', 'Encounter', True),
        ('Tier', T('int'), '2', 'Encounter', True),
        ('BreatheMove', move, '/Game/FoA/Gameplay/Encounter/Data/DA_Move_DeepBreath.DA_Move_DeepBreath', 'Encounter', True),
        ('MirrorMove', move, '/Game/FoA/Gameplay/Encounter/Data/DA_Move_CheckMirror.DA_Move_CheckMirror', 'Encounter', True),
        ('FleeLine', T('text'), "You can't run from getting dressed.", 'Encounter', True),
        ('ItemsLine', T('text'), 'Nothing in your pockets helps with this.', 'Encounter', True),
        ('StatusLabels', BEL.get_map_type(T('name'), T('text')), STATUS_LABELS, 'Encounter', True),
        ('SlotSpacing', T('real'), '110.0', 'Encounter', True),
        ('TurnPause', T('real'), '1.6', 'Encounter', True),
        ('KeyCount', T('int'), '3', 'Encounter|Timed input', True),
        ('KeysToHit', T('int'), '2', 'Encounter|Timed input', True),
        ('KeyWindow', T('real'), '1.0', 'Encounter|Timed input', True),
        ('WidenFactor', T('real'), '1.75', 'Encounter|Timed input', True),
        ('PromptKeys', BEL.get_array_type(S(unreal.Key)), '((KeyName="W"),(KeyName="A"),(KeyName="S"),(KeyName="D"))',
         'Encounter|Timed input', True),
        ('Leader', opp, '', 'Encounter|State', False),
        ('Garments', BEL.get_array_type(garment_t()), '', 'Encounter|State', False),
        ('Lineup', BEL.get_array_type(opp), '', 'Encounter|State', False),
        ('Target', T('int'), '0', 'Encounter|State', False),
        ('Remaining', T('int'), '0', 'Encounter|State', False),
        ('Step', T('int'), '0', 'Encounter|State', False),
        ('BattleState', T('name'), 'None', 'Encounter|State', False),
        ('AfterCheck', T('name'), 'None', 'Encounter|State', False),
        ('Composure', T('int'), '0', 'Encounter|State', False),
        ('Resolve', T('int'), '0', 'Encounter|State', False),
        ('Statuses', BEL.get_array_type(T('name')), '', 'Encounter|State', False),
        ('PendingMove', move, '', 'Encounter|State', False),
        ('bActive', T('bool'), 'false', 'Encounter|State', False),
        ('bPlayerTurn', T('bool'), 'false', 'Encounter|State', False),
        ('bAwaitingKey', T('bool'), 'false', 'Encounter|State', False),
        ('bRevealed', T('bool'), 'false', 'Encounter|State', False),
        ('bFreePreview', T('bool'), 'false', 'Encounter|State', False),
        ('InputKeys', BEL.get_array_type(S(unreal.Key)), '', 'Encounter|State', False),
        ('InputIndex', T('int'), '0', 'Encounter|State', False),
        ('InputHits', T('int'), '0', 'Encounter|State', False),
        ('ActiveWindow', T('real'), '1.0', 'Encounter|State', False),
        ('KeyTimer', S(unreal.TimerHandle), '', 'Encounter|State', False),
        ('Narration', T('text'), '', 'Encounter|State', False),
        ('Widget', BEL.get_object_reference_type(unreal.UserWidget), '', 'Encounter|State', False),
    ])
    have = [str(n) for n in BEL.list_event_dispatchers(bp)]
    params = {'OnStateChanged': [('State', T('name'))],
              'OnDamage': [('Who', BEL.get_object_reference_type(unreal.Actor)), ('Amount', T('int'))],
              'OnGarmentEquipped': [('Garment', BEL.get_object_reference_type(unreal.Actor))]}
    for d in ('OnChanged', 'OnStateChanged', 'OnDamage', 'OnGarmentEquipped', 'OnEncounterWon', 'OnEncounterLost',
              'OnSandBurst'):
        if d not in have:
            BEL.add_event_dispatcher(bp, d)
            for pn, pt in params.get(d, ()):
                BEL.add_event_dispatcher_parameter(bp, d, pn, pt)
    components(bp)
    print('skeleton ok')


def components(bp):
    """Mound (the line-up stands in it), SandBurst anchor (sandvfx lane), PlayerMark, BattleCam (front-on line-up),
    HeroCam (the cut to the Nightmare on actions)."""
    sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    lib = unreal.SubobjectDataBlueprintFunctionLibrary
    handles = sds.k2_gather_subobject_data_for_blueprint(bp)
    by_name = {str(lib.get_variable_name(lib.get_data(h))): h for h in handles}
    root = by_name.get('DefaultSceneRoot', handles[0])
    if 'Shirt' in by_name:  # the single-shirt prototype's mesh; garments are BP_Garment actors now
        sds.delete_subobjects(root, [by_name.pop('Shirt')], bp)
    for name, cls in (('Mound', unreal.StaticMeshComponent), ('SandBurst', unreal.SceneComponent),
                      ('PlayerMark', unreal.ArrowComponent), ('BattleCam', unreal.CameraComponent),
                      ('HeroCam', unreal.CameraComponent)):
        if name not in by_name:
            h, fail = sds.add_new_subobject(unreal.AddNewSubobjectParams(parent_handle=root, new_class=cls,
                                                                          blueprint_context=bp))
            assert not str(fail), f'add {name}: {fail}'
            sds.rename_subobject(h, unreal.Text(name))
            by_name[name] = h
    obj = {n: lib.get_object(lib.get_data(h)) for n, h in by_name.items()}  # deprecated, but returns the SCS templates
    mound = obj['Mound']
    mound.set_editor_property('static_mesh', unreal.load_asset('/Game/FoA/Procedural/SM_SandMound_A/SM_SandMound_A/StaticMeshes/SM_SandMound_A'))
    mound.set_material(0, unreal.load_asset('/Game/FoA/VFX/Sand/MI_SandSpill_Mound'))
    # Preserve the original arena bounds: centre (20,0,-14), extent (120,290,25).
    mound.set_editor_property('relative_location', unreal.Vector(29.114425, -11.470319, -39))
    mound.set_editor_property('relative_scale3d', unreal.Vector(2.344421, 5.278216, 1.921295))
    mound.set_collision_profile_name('NoCollision')
    obj['SandBurst'].set_editor_property('relative_location', unreal.Vector(0, 0, 20))
    obj['PlayerMark'].set_editor_property('relative_location', unreal.Vector(-260, 0, 92))  # capsule centre
    cam = obj['BattleCam']
    cam.set_editor_property('relative_location', unreal.Vector(-480, 0, 200))
    cam.set_editor_property('relative_rotation', unreal.Rotator(roll=0, pitch=-10.0, yaw=0))
    cam.set_editor_property('field_of_view', 75.0)
    hero = obj['HeroCam']
    hero.set_editor_property('relative_location', unreal.Vector(-130, 170, 150))
    hero.set_editor_property('relative_rotation', unreal.Rotator(roll=0, pitch=-5.0, yaw=-127.0))
    hero.set_editor_property('field_of_view', 55.0)
    hero.set_editor_property('auto_activate', False)


# ---------------------------------------------------------------- rules
def rules():
    move, gar = move_t(), garment_t()

    g, e, r = new_function(BP, 'MoveCost', [('Move', move)], [('Cost', T('int'))], pure=True)
    g.at(e, 0, 0)
    cost = field(g, po(e, 'Move'), 'ResolveCost', MOVE_C, 300, 0)
    rev = field(g, po(e, 'Move'), 'bRevealsNext', MOVE_C, 300, 140)
    both = fcall(g, f'{KML}:BooleanAND', 600, 160, A=rev, B=mget(g, 'bFreePreview', 300, 260))
    sel = fcall(g, f'{KML}:SelectInt', 860, 0, A=0, B=cost, bPickA=both)
    g.at(r, 1120, 0)
    go(e, r)
    feed(r, Cost=sel)
    box(g, 'Resolve cost', 'A revealing move (Check Mirror) is free while bFreePreview holds (the knowledge flag).',
        g.ed.list_all_nodes(), 'data')

    g, e, r = new_function(BP, 'CanUseMove', [('Move', move)], [('bCan', T('bool'))], pure=True)
    g.at(e, 0, 0)
    mc = fcall(g, SELF('MoveCost'), 300, 100, Move=po(e, 'Move'))
    ge = fcall(g, f'{KML}:GreaterEqual_IntInt', 600, 0, A=mget(g, 'Resolve', 300, 0), B=po(mc, 'Cost'))
    has = fcall(g, f'{KAL}:Array_Contains', 600, 260, TargetArray=mget(g, 'Statuses', 300, 260),
                ItemToFind=field(g, po(e, 'Move'), 'BlockedBy', MOVE_C, 300, 380))
    ok = fcall(g, f'{KML}:BooleanAND', 1100, 0, A=ge, B=fcall(g, f'{KML}:Not_PreBool', 860, 260, A=has))
    g.at(r, 1360, 0)
    go(e, r)
    feed(r, bCan=ok)
    box(g, 'Can use move', 'Resolve covers the cost and no active status blocks it '
        '(Button Up under Sleeve Labyrinth, Deep Breath while the tie is tight).', g.ed.list_all_nodes(), 'data')

    g, e, r = new_function(BP, 'KnowsPattern', [], [('bKnows', T('bool'))])
    g.at(e, 0, 0)
    if unreal.load_class(None, GI_C):
        cast = make(g, 300, 0, 'CastToGI_FoA')
        feed(cast, Object=fcall(g, f'{GS}:GetGameInstance', 0, 200))
        knows = fcall(g, f'{GI_C}:HasKnowledge', 640, 160, self=as_pin(cast),
                      Flag=field(g, mget(g, 'Leader', 300, 340), 'KnowledgeFlag', OPP_C, 500, 340))
        g.at(r, 1000, 0)
        go(e, cast)
        seq(cast, knows, r)  # HasKnowledge is impure: on the exec path, or the compiler prunes it
        wire(po(knows), pi(r, 'bKnows'))
        f = g.at(g.ed.add_return_node(), 640, -180)
        go(cast, f, 'CastFailed')
    else:
        g.at(r, 400, 0)
        go(e, r)
    box(g, 'Knows this fight', 'GI_FoA.HasKnowledge(Leader.KnowledgeFlag); false without '
        'GI_FoA (dev maps).', g.ed.list_all_nodes(), 'data')

    g, e, r = new_function(BP, 'TargetGarment', [], [('Garment', gar)], pure=True)
    g.at(e, 0, 0)
    get = fcall(g, f'{KAL}:Array_Get', 260, 160, TargetArray=mget(g, 'Garments', 40, 160),
                Index=mget(g, 'Target', 40, 260))
    g.at(r, 560, 0)
    go(e, r)
    feed(r, Garment=po(get, 'Item'))
    box(g, 'Target', 'The garment the Act moves land on.', g.ed.list_all_nodes(), 'data')

    # ApplySelf(Move): the Nightmare's stats, statuses and the narration line
    g, e, _ = new_function(BP, 'ApplySelf', [('Move', move)])
    g.at(e, 0, 0)
    M = po(e, 'Move')
    L = mget(g, 'Leader', 0, 620)
    mc = fcall(g, SELF('MoveCost'), 260, 220, Move=M)
    sub = fcall(g, f'{KML}:Subtract_IntInt', 520, 180, A=mget(g, 'Resolve', 260, 120), B=po(mc, 'Cost'))
    add = fcall(g, f'{KML}:Add_IntInt', 760, 180, A=sub, B=field(g, M, 'ResolveDelta', MOVE_C, 520, 320))
    cl_r = fcall(g, f'{KML}:Clamp', 1000, 180, Value=add, Min=0, Max=field(g, L, 'StartResolve', OPP_C, 760, 620))
    set_r = mset(g, 'Resolve', 1260, 0, cl_r)
    add_c = fcall(g, f'{KML}:Add_IntInt', 1520, 180, A=mget(g, 'Composure', 1260, 220),
                  B=field(g, M, 'ComposureDelta', MOVE_C, 1260, 320))
    cl_c = fcall(g, f'{KML}:Clamp', 1760, 180, Value=add_c, Min=0, Max=field(g, L, 'StartComposure', OPP_C, 1520, 620))
    set_c = mset(g, 'Composure', 2020, 0, cl_c)
    chain(e, set_r, set_c)
    X = 2400
    box(g, 'The Nightmare\'s stats', 'Resolve pays the cost and takes ResolveDelta; Composure takes ComposureDelta. '
        'Both clamped to the leader row\'s starting values.', band(g, -200, 900, x1=X - 100), 'data')
    st = mget(g, 'Statuses', X, 200)
    rem = fcall(g, f'{KAL}:Array_RemoveItem', X + 240, 0, TargetArray=st, Item=field(g, M, 'StatusCleared', MOVE_C, X, 300))
    applied = field(g, M, 'StatusApplied', MOVE_C, X + 240, 300)
    some = fcall(g, f'{KML}:NotEqual_NameName', X + 500, 300, A=applied, B='None')
    br1 = g.at(g.ed.add_branch_node(), X + 760, 0)
    wire(po(some), BEL.find_condition_pin(br1))
    addu = fcall(g, f'{KAL}:Array_AddUnique', X + 1020, -100, TargetArray=st, NewItem=applied)
    br2 = g.at(g.ed.add_branch_node(), X + 1300, 0)
    wire(po(field(g, M, 'bRevealsNext', MOVE_C, X + 1040, 220)), BEL.find_condition_pin(br2))
    s_rev = mset(g, 'bRevealed', X + 1560, -100, 'true')
    s_free = mset(g, 'bFreePreview', X + 1820, -100, 'false')
    s_nar = mset(g, 'Narration', X + 2080, 0, field(g, M, 'Narration', MOVE_C, X + 1820, 200))
    go(set_c, rem)
    go(rem, br1)
    go(br1, addu)
    go(br1, br2, 'else')
    go(addu, br2)
    go(br2, s_rev)
    go(s_rev, s_free)
    go(s_free, s_nar)
    go(br2, s_nar, 'else')
    box(g, 'Statuses and narration', 'StatusCleared goes, StatusApplied comes once; a revealing move shows every '
        'garment\'s next move and spends the free preview; the move\'s line is narrated.',
        band(g, -200, 900, x0=X - 40), 'turn')

    # SeekTarget(Offset, Step, Tries): recursive index counter (no loop macros): the garment Offset places from the
    # target, wrapping; if it is worn, look Step further, up to one full lap
    g, e, _ = new_function(BP, 'SeekTarget', [('Offset', T('int')), ('Step', T('int')), ('Tries', T('int'))])
    g.at(e, 0, 0)
    n = fcall(g, f'{KAL}:Array_Length', 0, 300, TargetArray=mget(g, 'Garments', -220, 300))
    base = fcall(g, f'{KML}:Add_IntInt', 260, 400, A=mget(g, 'Target', 40, 440),
                 B=fcall(g, f'{KML}:Multiply_IntInt', 40, 560, A=n, B=4))
    t = fcall(g, f'{KML}:Percent_IntInt', 760, 400, A=fcall(g, f'{KML}:Add_IntInt', 500, 400, A=base, B=po(e, 'Offset')),
              B=n)
    gm = fcall(g, f'{KAL}:Array_Get', 1000, 400, TargetArray=mget(g, 'Garments', 780, 560), Index=t)
    br = g.at(g.ed.add_branch_node(), 1260, 0)
    wire(po(fcall(g, GSELF('IsAlive'), 1240, 400, self=po(gm, 'Item')), 'bAlive'), BEL.find_condition_pin(br))
    st = mset(g, 'Target', 1540, -140, t)
    br2 = g.at(g.ed.add_branch_node(), 1540, 160)
    wire(po(fcall(g, f'{KML}:Less_IntInt', 1500, 420, A=po(e, 'Tries'), B=n)), BEL.find_condition_pin(br2))
    again = fcall(g, SELF('SeekTarget'), 1840, 160, Step=po(e, 'Step'),
                  Offset=fcall(g, f'{KML}:Add_IntInt', 1640, 420, A=po(e, 'Offset'), B=po(e, 'Step')),
                  Tries=fcall(g, f'{KML}:Add_IntInt', 1640, 560, A=po(e, 'Tries'), B=1))
    go(e, br)
    go(br, st)
    go(br, br2, 'else')
    go(br2, again)
    box(g, 'Seek a standing garment', 'Offset places along the line from the target (wrapping); a worn one passes the '
        'search on Step further, for at most one lap.', g.ed.list_all_nodes(), 'input')

    g, e, _ = new_function(BP, 'CycleTarget', [('Direction', T('int'))])
    g.at(e, 0, 0)
    zero = fcall(g, f'{KML}:EqualEqual_IntInt', 0, 260, A=po(e, 'Direction'), B=0)
    seek = fcall(g, SELF('SeekTarget'), 520, 0, Offset=po(e, 'Direction'), Tries=0,
                 Step=fcall(g, f'{KML}:SelectInt', 260, 260, A=1, B=po(e, 'Direction'), bPickA=zero))
    go(e, seek)
    box(g, 'Cycle the target', 'Direction -1 or 1 steps along the line; 0 keeps the target if it still stands, else '
        'the next one.', g.ed.list_all_nodes(), 'input')

    # PickIntentsFrom(Index, bOpening, bAny) -> bTelegraph: recursive over the line; PickIntents(bOpening) starts it
    g, e, r = new_function(BP, 'PickIntentsFrom', [('Index', T('int')), ('bOpening', T('bool')), ('bAny', T('bool'))],
                           [('bTelegraph', T('bool'))])
    g.at(e, 0, 0)
    gars = mget(g, 'Garments', -200, 300)
    br = g.at(g.ed.add_branch_node(), 260, 0)
    wire(po(fcall(g, f'{KML}:Less_IntInt', 40, 300, A=po(e, 'Index'),
                  B=fcall(g, f'{KAL}:Array_Length', -160, 420, TargetArray=gars))), BEL.find_condition_pin(br))
    G = po(fcall(g, f'{KAL}:Array_Get', 260, 420, TargetArray=gars, Index=po(e, 'Index')), 'Item')
    br2 = g.at(g.ed.add_branch_node(), 520, -120)
    wire(po(fcall(g, GSELF('IsAlive'), 520, 420, self=G), 'bAlive'), BEL.find_condition_pin(br2))
    pick = fcall(g, GSELF('PickIntent'), 800, -240, self=G, bOpening=po(e, 'bOpening'))
    tel = fcall(g, f'{KML}:EqualEqual_NameName', 1060, 300, A=field(g, G, 'State', G_C, 860, 300), B='Telegraph')
    nxt = fcall(g, SELF('PickIntentsFrom'), 1360, -120, bOpening=po(e, 'bOpening'),
                Index=fcall(g, f'{KML}:Add_IntInt', 1100, 160, A=po(e, 'Index'), B=1),
                bAny=fcall(g, f'{KML}:BooleanOR', 1300, 300, A=po(e, 'bAny'),
                           B=fcall(g, f'{KML}:BooleanAND', 1100, 440, A=tel,
                                   B=po(fcall(g, GSELF('IsAlive'), 860, 560, self=G), 'bAlive'))))
    ret = g.at(g.ed.add_return_node(), 1700, -120)
    wire(po(nxt, 'bTelegraph'), pi(ret, 'bTelegraph'))
    g.at(r, 520, 220)
    wire(po(e, 'bAny'), pi(r, 'bTelegraph'))
    go(e, br)
    go(br, br2)
    go(br2, pick)
    go(pick, nxt)
    go(br2, nxt, 'else')
    go(nxt, ret)
    go(br, r, 'else')
    box(g, 'Every garment picks (index counter)', 'Garment Index picks its next move if it stands, then the next index; '
        'reports whether any of them telegraphs.', g.ed.list_all_nodes(), 'turn')

    g, e, r = new_function(BP, 'PickIntents', [('bOpening', T('bool'))], [('bTelegraph', T('bool'))])
    g.at(e, 0, 0)
    first = fcall(g, SELF('PickIntentsFrom'), 260, 0, Index=0, bOpening=po(e, 'bOpening'), bAny='false')
    g.at(r, 600, 0)
    go(e, first)
    go(first, r)
    wire(po(first, 'bTelegraph'), pi(r, 'bTelegraph'))
    box(g, 'Every garment picks', 'From the first garment in the line.', g.ed.list_all_nodes(), 'turn')

    g, e, _ = new_function(BP, 'ResetStats')
    g.at(e, 0, 0)
    L = mget(g, 'Leader', 0, 300)
    sc = mset(g, 'Composure', 260, 0, field(g, L, 'StartComposure', OPP_C, 160, 400))
    sr = mset(g, 'Resolve', 520, 0, field(g, L, 'StartResolve', OPP_C, 420, 400))
    clr = fcall(g, f'{KAL}:Array_Clear', 780, 0, TargetArray=mget(g, 'Statuses', 640, 260))
    srev = mset(g, 'bRevealed', 1040, 0, 'false')
    kp = fcall(g, SELF('KnowsPattern'), 1300, 0)
    sfree = mset(g, 'bFreePreview', 1560, 0, po(kp, 'bKnows'))
    chain(e, sc, sr, clr, srev, kp, sfree)
    box(g, 'Fresh stats', 'Composure and Resolve from the leader row, statuses cleared; the first Check Mirror is '
        'free when the player already knows the fight.', g.ed.list_all_nodes(), 'data')

    # SpawnFrom(Index): recursive index counter over Lineup: one BP_Garment per member, spaced along local Y
    g, e, _ = new_function(BP, 'SpawnFrom', [('Index', T('int'))])
    g.at(e, 0, 0)
    lin = mget(g, 'Lineup', -220, 300)
    cnt = fcall(g, f'{KAL}:Array_Length', 0, 420, TargetArray=lin)
    br = g.at(g.ed.add_branch_node(), 260, 0)
    wire(po(fcall(g, f'{KML}:Less_IntInt', 40, 300, A=po(e, 'Index'), B=cnt)), BEL.find_condition_pin(br))
    mid = fcall(g, f'{KML}:Multiply_DoubleDouble', 260, 560,
                A=fcall(g, f'{KML}:Conv_IntToDouble', 40, 660, InInt=fcall(g, f'{KML}:Subtract_IntInt', -180, 660, A=cnt, B=1)),
                B=0.5)
    y = fcall(g, f'{KML}:Multiply_DoubleDouble', 760, 420,
              A=fcall(g, f'{KML}:Subtract_DoubleDouble', 520, 420,
                      A=fcall(g, f'{KML}:Conv_IntToDouble', 300, 380, InInt=po(e, 'Index')), B=mid),
              B=mget(g, 'SlotSpacing', 520, 560))
    world = fcall(g, f'{KML}:TransformLocation', 1240, 420, T=fcall(g, '/Script/Engine.Actor:GetTransform', 1000, 600),
                  Location=fcall(g, f'{KML}:MakeVector', 1000, 420, X=0.0, Y=y, Z=0.0))
    xf = fcall(g, f'{KML}:MakeTransform', 1480, 420, Location=world,
               Rotation=fcall(g, '/Script/Engine.Actor:K2_GetActorRotation', 1240, 620))
    spawn = make(g, 1720, 0, 'SpawnActorFromClass')
    val(spawn, 'Class', G_C)
    wire(po(xf), pi(spawn, 'SpawnTransform'))
    member = po(fcall(g, f'{KAL}:Array_Get', 1900, 420, TargetArray=mget(g, 'Lineup', 1700, 560), Index=po(e, 'Index')),
                'Item')
    setup = fcall(g, GSELF('Setup'), 2160, 0, self=po(spawn, 'ReturnValue'), InData=member,
                  InTier=mget(g, 'Tier', 1960, 560))
    add = fcall(g, f'{KAL}:Array_Add', 2460, 0, TargetArray=mget(g, 'Garments', 2260, 300),
                NewItem=po(spawn, 'ReturnValue'))
    nxt = fcall(g, SELF('SpawnFrom'), 2760, 0, Index=fcall(g, f'{KML}:Add_IntInt', 2560, 300, A=po(e, 'Index'), B=1))
    go(e, br)
    go(br, spawn)
    chain(spawn, setup, add, nxt)
    box(g, 'Spawn the line (index counter)', 'Member Index of Lineup gets a BP_Garment, SlotSpacing apart across the '
        'mound and facing the Nightmare; then the next index.', g.ed.list_all_nodes(), 'stage')

    # SpawnParty(): the leader in the middle of its party, then SpawnFrom(0)
    g, e, _ = new_function(BP, 'SpawnParty')
    g.at(e, 0, 0)
    clr = fcall(g, f'{KAL}:Array_Clear', 260, 0, TargetArray=mget(g, 'Garments', 60, 200))
    L = mget(g, 'Leader', 260, 340)
    setl = mset(g, 'Lineup', 520, 0, field(g, L, 'Party', OPP_C, 440, 340))
    half = fcall(g, f'{KML}:Divide_IntInt', 1000, 360,
                 A=fcall(g, f'{KAL}:Array_Length', 760, 380, TargetArray=mget(g, 'Lineup', 560, 460)), B=2)
    ins = fcall(g, f'{KAL}:Array_Insert', 1240, 0, TargetArray=mget(g, 'Lineup', 1040, 220), NewItem=L, Index=half)
    sp = fcall(g, SELF('SpawnFrom'), 1540, 0, Index=0)
    n = fcall(g, f'{KAL}:Array_Length', 1540, 260, TargetArray=mget(g, 'Garments', 1340, 260))
    sr = mset(g, 'Remaining', 1800, 0, n)
    stg = mset(g, 'Target', 2060, 0, fcall(g, f'{KML}:Divide_IntInt', 1800, 260, A=n, B=2))
    chain(e, clr, setl, ins, sp, sr, stg)
    box(g, 'Line-up', 'The leader stands in the middle of its Party (the socks end up at either end); all standing, '
        'the first target is the leader.', g.ed.list_all_nodes(), 'data')

    # ClearFrom(Index) / ClearParty()
    g, e, _ = new_function(BP, 'ClearFrom', [('Index', T('int'))])
    g.at(e, 0, 0)
    gars = mget(g, 'Garments', -200, 300)
    br = g.at(g.ed.add_branch_node(), 260, 0)
    wire(po(fcall(g, f'{KML}:Less_IntInt', 40, 300, A=po(e, 'Index'),
                  B=fcall(g, f'{KAL}:Array_Length', -160, 420, TargetArray=gars))), BEL.find_condition_pin(br))
    kill = fcall(g, '/Script/Engine.Actor:K2_DestroyActor', 560, 0,
                 self=po(fcall(g, f'{KAL}:Array_Get', 300, 300, TargetArray=gars, Index=po(e, 'Index')), 'Item'))
    nxt = fcall(g, SELF('ClearFrom'), 860, 0, Index=fcall(g, f'{KML}:Add_IntInt', 660, 260, A=po(e, 'Index'), B=1))
    go(e, br)
    go(br, kill)
    go(kill, nxt)
    box(g, 'Clear the line (index counter)', 'Destroy garment Index, then the next (worn ones are already hidden on '
        'the hero).', g.ed.list_all_nodes(), 'stage')

    g, e, _ = new_function(BP, 'ClearParty')
    g.at(e, 0, 0)
    cf = fcall(g, SELF('ClearFrom'), 260, 0, Index=0)
    clr = fcall(g, f'{KAL}:Array_Clear', 560, 0, TargetArray=mget(g, 'Garments', 360, 220))
    chain(e, cf, clr)
    box(g, 'Clear the line', 'Every garment actor, then the list.', g.ed.list_all_nodes(), 'stage')

    # DrawKeys(Remaining): recursive index counter: one random prompt key per call
    g, e, _ = new_function(BP, 'DrawKeys', [('Remaining', T('int'))])
    g.at(e, 0, 0)
    br = g.at(g.ed.add_branch_node(), 260, 0)
    wire(po(fcall(g, f'{KML}:Greater_IntInt', 40, 260, A=po(e, 'Remaining'), B=0)), BEL.find_condition_pin(br))
    rnd = fcall(g, f'{KAL}:Array_Random', 520, 260, TargetArray=mget(g, 'PromptKeys', 300, 360))
    addk = fcall(g, f'{KAL}:Array_Add', 820, 0, TargetArray=mget(g, 'InputKeys', 600, 160), NewItem=po(rnd, 'OutItem'))
    nxt = fcall(g, SELF('DrawKeys'), 1120, 0,
                Remaining=fcall(g, f'{KML}:Subtract_IntInt', 920, 260, A=po(e, 'Remaining'), B=1))
    go(e, br)
    go(br, rnd) if impure(rnd) else go(br, addk)
    seq(rnd, addk, nxt)
    box(g, 'Draw prompt keys (index counter)', 'One random key from PromptKeys per call until Remaining is 0.',
        g.ed.list_all_nodes(), 'input')

    g, e, _ = new_function(BP, 'BeginTimedInput', [('Move', move)])
    g.at(e, 0, 0)
    M = po(e, 'Move')
    s_h = mset(g, 'InputHits', 260, 0, 0)
    s_i = mset(g, 'InputIndex', 520, 0, 0)
    clr = fcall(g, f'{KAL}:Array_Clear', 780, 0, TargetArray=mget(g, 'InputKeys', 640, 200))
    draw = fcall(g, SELF('DrawKeys'), 1040, 0, Remaining=mget(g, 'KeyCount', 840, 200))
    X = 1400
    st = mget(g, 'Statuses', X, 260)
    boost = field(g, M, 'BoostedBy', MOVE_C, X, 380)
    has = fcall(g, f'{KAL}:Array_Contains', X + 260, 260, TargetArray=st, ItemToFind=boost)
    fac = fcall(g, f'{KML}:SelectFloat', X + 520, 200, A=mget(g, 'WidenFactor', X + 260, 140), B=1.0, bPickA=has)
    win = fcall(g, f'{KML}:Multiply_DoubleDouble', X + 780, 160, A=mget(g, 'KeyWindow', X + 520, 60), B=fac)
    s_w = mset(g, 'ActiveWindow', X + 1040, 0, win)
    rem = fcall(g, f'{KAL}:Array_RemoveItem', X + 1300, 0, TargetArray=st, Item=boost)
    chain(e, s_h, s_i, clr, draw, s_w, rem)
    box(g, 'Begin the timed input', 'Reset the run, draw KeyCount keys; the window is KeyWindow seconds per key, x '
        'WidenFactor while the BoostedBy status of the move is active (Find Armhole); the boost is spent.',
        g.ed.list_all_nodes(), 'input')

    # ApplyPlayerMove(Multiplier): the Nightmare, then the target garment
    g, e, _ = new_function(BP, 'ApplyPlayerMove', [('Multiplier', T('int'))])
    g.ed.add_local_variable('Hit', gar, '')
    g.at(e, 0, 0)
    pm = mget(g, 'PendingMove', 0, 300)
    app = fcall(g, SELF('ApplySelf'), 260, 0, Move=pm)
    seth = g.at(g.ed.add_set_local_variable_node('Hit'), 520, 0)
    feed(seth, Hit=po(fcall(g, SELF('TargetGarment'), 260, 300), 'Garment'))
    amount = fcall(g, f'{KML}:Multiply_IntInt', 520, 300, A=field(g, pm, 'ProgressDelta', MOVE_C, 260, 460),
                   B=po(e, 'Multiplier'))
    prog = fcall(g, GSELF('AddProgress'), 800, 0, self=po(seth), Delta=amount)
    br = g.at(g.ed.add_branch_node(), 1080, 0)
    wire(po(fcall(g, f'{KML}:NotEqual_IntInt', 800, 300, A=amount, B=0)), BEL.find_condition_pin(br))
    dmg = make(g, 1340, -120, 'Call', 'OnDamage')
    feed(dmg, Who=po(seth), Amount=amount)
    chain(e, app, seth, prog, br)
    go(br, dmg)
    X = 1700
    box(g, 'Act on the target', 'Stats and statuses first, then the move\'s progress (x the timed-input multiplier) '
        'lands on the target with a damage number.', band(g, -300, 900, x1=X - 100), 'turn')
    hit = lambda x, y: g.at(g.ed.add_get_local_variable_node('Hit'), x, y)  # noqa: E731
    stun_ok = fcall(g, f'{KML}:BooleanAND', X + 260, 300,
                    A=field(g, mget(g, 'PendingMove', X - 200, 300), 'bStuns', MOVE_C, X, 300),
                    B=po(fcall(g, GSELF('IsAlive'), X, 460, self=po(hit(X - 200, 460))), 'bAlive'))
    br2 = g.at(g.ed.add_branch_node(), X + 520, 0)
    wire(po(stun_ok), BEL.find_condition_pin(br2))
    stun = g.at(g.ed.add_set_member_variable_node('State', G_C), X + 780, -160)
    wire(po(hit(X + 580, -260)), pi(stun, 'self'))
    val(stun, 'State', 'Stunned')
    go(dmg, br2)
    go(br, br2, 'else')
    go(br2, stun)
    X3 = 2900
    box(g, 'Stun', 'Untwist the Leg and Loosen knock the garment off its next turn.', band(g, -300, 900, X - 240, X3 - 100),
        'turn')
    br3 = g.at(g.ed.add_branch_node(), X3, 0)
    wire(po(prog, 'bDefeated'), BEL.find_condition_pin(br3))
    dec = mset(g, 'Remaining', X3 + 260, -100, fcall(g, f'{KML}:Subtract_IntInt', X3 + 40, 200,
                                                     A=mget(g, 'Remaining', X3 - 160, 280), B=1))
    nar = mset(g, 'Narration', X3 + 520, -100,
               field(g, field(g, po(hit(X3 + 140, 380)), 'Data', G_C, X3 + 320, 380), 'WinLine', OPP_C, X3 + 520, 380))
    eqd = make(g, X3 + 780, -100, 'Call', 'OnGarmentEquipped')
    feed(eqd, Garment=po(hit(X3 + 640, 500)))
    eq = fcall(g, GSELF('Equip'), X3 + 1080, -100, self=po(hit(X3 + 880, 500)))
    burst = make(g, X3 + 1340, -100, 'Call', 'OnSandBurst')
    go(stun, br3)
    go(br2, br3, 'else')
    go(br3, dec)
    fx = sand_fx(g, X3 + 1340, -360, po(hit(X3 + 1100, -160)))
    chain(dec, nar, eqd, eq, burst)
    if fx:
        go(burst, fx)
        burst = fx
    if unreal.load_class(None, PLAYER_C):
        before = {x.get_name() for x in g.ed.list_all_nodes()}
        try:
            cast = make(g, X3 + 1600, -100, 'CastToBP_FoAPlayer')
            feed(cast, Object=fcall(g, f'{GS}:GetPlayerPawn', X3 + 1400, 160, PlayerIndex=0))
            wear = fcall(g, f'{PLAYER_C}:Equip', X3 + 1960, -100, self=as_pin(cast),
                         GarmentId=field(g, field(g, po(hit(X3 + 1600, 300)), 'Data', G_C, X3 + 1780, 300), 'GarmentId',
                                         OPP_C, X3 + 1960, 300))
            go(burst, cast)
            go(cast, wear)
        except Exception as err:  # the player lane hasn't added Equip yet: rebuild 'rules' when it lands
            print('BP_FoAPlayer.Equip skipped:', err)
            g.ed.remove_nodes([x for x in g.ed.list_all_nodes() if x.get_name() not in before])
    box(g, 'Worn', 'At full progress the garment is worn: it snaps onto the hero, BP_FoAPlayer.Equip(GarmentId) shows '
        'the layer, and its win line is narrated.', band(g, -300, 900, x0=X3 - 240), 'outcome')

    # FindTwin(Garment, Index) -> Twin: recursive index counter; another standing garment of the same row, or -1
    g, e, r = new_function(BP, 'FindTwin', [('Garment', gar), ('Index', T('int'))], [('Twin', T('int'))])
    g.at(e, 0, 0)
    gars = mget(g, 'Garments', -200, 300)
    br = g.at(g.ed.add_branch_node(), 260, 0)
    wire(po(fcall(g, f'{KML}:Less_IntInt', 40, 300, A=po(e, 'Index'),
                  B=fcall(g, f'{KAL}:Array_Length', -160, 420, TargetArray=gars))), BEL.find_condition_pin(br))
    el = po(fcall(g, f'{KAL}:Array_Get', 260, 420, TargetArray=gars, Index=po(e, 'Index')), 'Item')
    twin = fcall(g, f'{KML}:BooleanAND', 1000, 300,
                 A=fcall(g, f'{KML}:EqualEqual_ObjectObject', 760, 300, A=field(g, el, 'Data', G_C, 560, 300),
                         B=field(g, po(e, 'Garment'), 'Data', G_C, 560, 420)),
                 B=fcall(g, f'{KML}:BooleanAND', 760, 480,
                         A=fcall(g, f'{KML}:NotEqual_ObjectObject', 560, 560, A=el, B=po(e, 'Garment')),
                         B=po(fcall(g, GSELF('IsAlive'), 560, 680, self=el), 'bAlive')))
    br2 = g.at(g.ed.add_branch_node(), 1260, 0)
    wire(po(twin), BEL.find_condition_pin(br2))
    found = g.at(g.ed.add_return_node(), 1520, -160)
    wire(po(e, 'Index'), pi(found, 'Twin'))
    nxt = fcall(g, SELF('FindTwin'), 1520, 120, Garment=po(e, 'Garment'),
                Index=fcall(g, f'{KML}:Add_IntInt', 1320, 300, A=po(e, 'Index'), B=1))
    passed = g.at(g.ed.add_return_node(), 1840, 120)
    wire(po(nxt, 'Twin'), pi(passed, 'Twin'))
    g.at(r, 520, 260)
    val(r, 'Twin', -1)
    go(e, br)
    go(br, br2)
    go(br2, found)
    go(br2, nxt, 'else')
    go(nxt, passed)
    go(br, r, 'else')
    box(g, 'Find the twin (index counter)', 'Another standing garment made from the same row (the other sock), or -1.',
        g.ed.list_all_nodes(), 'data')

    # EnemyAct(Garment)
    g, e, _ = new_function(BP, 'EnemyAct', [('Garment', gar)])
    g.at(e, 0, 0)
    gm = po(e, 'Garment')
    intent = field(g, gm, 'Intent', G_C, 0, 300)
    app = fcall(g, SELF('ApplySelf'), 260, 0, Move=intent)
    selfp = fcall(g, GSELF('AddProgress'), 560, 0, self=gm, Delta=field(g, intent, 'ProgressDelta', MOVE_C, 260, 300))
    att = g.at(g.ed.add_set_member_variable_node('State', G_C), 860, 0)
    wire(gm, pi(att, 'self'))
    val(att, 'State', 'Attack')
    comp = field(g, intent, 'ComposureDelta', MOVE_C, 860, 300)
    br = g.at(g.ed.add_branch_node(), 1120, 0)
    wire(po(fcall(g, f'{KML}:NotEqual_IntInt', 1120, 260, A=comp, B=0)), BEL.find_condition_pin(br))
    dmg = make(g, 1380, -120, 'Call', 'OnDamage')
    feed(dmg, Who=fcall(g, f'{GS}:GetPlayerPawn', 1180, 420, PlayerIndex=0), Amount=comp)
    chain(e, app, selfp, att, br)
    go(br, dmg)
    X = 1800
    box(g, 'The garment acts', 'Its intent lands on the Nightmare (and on its own progress: Wrong Button undoes a '
        'button), with a damage number over the hero.', band(g, -300, 900, x1=X - 100), 'turn')
    # Swap Places: the sock trades spots (and line order) with its standing twin (same row), found by FindTwin
    brs = g.at(g.ed.add_branch_node(), X, 0)
    wire(po(field(g, intent, 'bSwapsTwin', MOVE_C, X - 60, 220)), BEL.find_condition_pin(brs))
    find = fcall(g, SELF('FindTwin'), X + 260, 0, Garment=gm, Index=0)
    twin_i = po(find, 'Twin')
    brf = g.at(g.ed.add_branch_node(), X + 560, 0)
    wire(po(fcall(g, f'{KML}:GreaterEqual_IntInt', X + 520, 260, A=twin_i, B=0)), BEL.find_condition_pin(brf))
    gars = mget(g, 'Garments', X + 600, 420)
    other = po(fcall(g, f'{KAL}:Array_Get', X + 820, 420, TargetArray=gars, Index=twin_i), 'Item')
    here = fcall(g, '/Script/Engine.Actor:K2_GetActorLocation', X + 1080, 300, self=gm)
    there = fcall(g, '/Script/Engine.Actor:K2_GetActorLocation', X + 1080, 440, self=other)
    m1 = fcall(g, '/Script/Engine.Actor:K2_SetActorLocation', X + 1340, 0, self=gm, NewLocation=there)
    m2 = fcall(g, '/Script/Engine.Actor:K2_SetActorLocation', X + 1640, 0, self=other, NewLocation=here)
    sw = fcall(g, f'{KAL}:Array_Swap', X + 1940, 0, TargetArray=gars, SecondIndex=twin_i,
               FirstIndex=fcall(g, f'{KAL}:Array_Find', X + 1940, 300, TargetArray=gars, ItemToFind=gm))
    go(dmg, brs)
    go(br, brs, 'else')
    go(brs, find)
    go(find, brf)
    go(brf, m1)
    chain(m1, m2, sw)
    box(g, 'Swap Places', 'The sock trades places and line order with its standing twin: the pair is mismatched again.',
        band(g, -300, 900, x0=X - 100), 'turn')

    # DreamPulse(Mode, Seconds) / DreamCycle(bStart): the pp lane's battle styles, skipped when the director is absent
    g, e, _ = new_function(BP, 'DreamPulse', [('Mode', T('int')), ('Seconds', T('real'))])
    g.at(e, 0, 0)
    print('dream director class:', bool(unreal.load_class(None, DREAM_C)))
    if unreal.load_class(None, DREAM_C):
        find = fcall(g, f'{GS}:GetActorOfClass', 0, 220, ActorClass=DREAM_C)
        ok = g.at(g.ed.add_branch_node(), 300, 0)
        wire(po(fcall(g, f'{KSL}:IsValid', 260, 220, Object=po(find))), BEL.find_condition_pin(ok))
        seq(e, find, ok)  # GetActorOfClass is impure: keep it on the exec path
        try:
            pulse = fcall(g, f'{DREAM_C}:PulseStyle', 600, 0, self=po(find), Mode=po(e, 'Mode'), Seconds=po(e, 'Seconds'))
            go(ok, pulse)
        except Exception as err:
            print('PulseStyle not there yet:', err)
    box(g, 'Style pulse', 'BP_DreamDirector.PulseStyle, when the post-process director is in the level.',
        g.ed.list_all_nodes(), 'stage')
    g, e, _ = new_function(BP, 'DreamCycle', [('bStart', T('bool'))])
    g.at(e, 0, 0)
    if unreal.load_class(None, DREAM_C):
        find = fcall(g, f'{GS}:GetActorOfClass', 0, 220, ActorClass=DREAM_C)
        ok = g.at(g.ed.add_branch_node(), 300, 0)
        wire(po(fcall(g, f'{KSL}:IsValid', 260, 220, Object=po(find))), BEL.find_condition_pin(ok))
        br = g.at(g.ed.add_branch_node(), 600, 0)
        wire(po(e, 'bStart'), BEL.find_condition_pin(br))
        seq(e, find, ok)  # GetActorOfClass is impure: keep it on the exec path
        go(ok, br)
        try:
            start = fcall(g, f'{DREAM_C}:StartStyleCycle', 900, -120, self=po(find), Interval=4.0)
            stop = fcall(g, f'{DREAM_C}:StopStyleCycle', 900, 120, self=po(find))
            real = fcall(g, f'{DREAM_C}:SetStyleMode', 1200, 120, self=po(find), Mode=0, BlendSeconds=1.0)
            go(br, start)
            go(br, stop, 'else')
            go(stop, real)
        except Exception as err:
            print('style cycle not there yet:', err)
    box(g, 'Style cycle', 'Start the battle style cycle (every 4 s), or stop it and blend back to real.',
        g.ed.list_all_nodes(), 'stage')
    print('rules ok')


# ---------------------------------------------------------------- stage
def stage():
    g, e, _ = new_function(BP, 'ShowEncounter')
    g.at(e, 0, 0)
    pc = fcall(g, f'{GS}:GetPlayerController', 0, 220, PlayerIndex=0)
    cw = make(g, 300, 0, 'CreateWidget')
    val(cw, 'Class', WBP_C)
    wire(po(pc), pi(cw, 'OwningPlayer'))
    wire(po(make(g, 60, 380, 'reference to self')), pi(cw, 'Encounter'))
    sw = mset(g, 'Widget', 760, 0, po(cw, 'ReturnValue'))
    add = fcall(g, '/Script/UMG.UserWidget:AddToViewport', 1020, 0, self=po(sw), ZOrder=10)
    im = fcall(g, f'{UWBL}:SetInputMode_GameAndUIEx', 1280, 0, PlayerController=pc, InWidgetToFocus=po(sw),
               bHideCursorDuringCapture='false')
    cur = fcall(g, f'{PC_P}:SetShowMouseCursor', 1580, 0, self=pc, bShowMouseCursor='true')
    nm = fcall(g, f'{CTL_P}:SetIgnoreMoveInput', 1840, 0, self=pc, bNewMoveInput='true')
    nl = fcall(g, f'{CTL_P}:SetIgnoreLookInput', 2100, 0, self=pc, bNewLookInput='true')
    chain(e, cw, sw, add, im, cur, nm, nl)
    X = 2440
    box(g, 'Menu and input', 'WBP_Encounter on screen with a cursor; the Nightmare stops walking and looking around.',
        band(g, -200, 900, x1=X - 100), 'stage')
    pawn = fcall(g, f'{GS}:GetPlayerPawn', X, 220, PlayerIndex=0)
    mark = mget(g, 'PlayerMark', X, 380)
    tp = fcall(g, '/Script/Engine.Actor:K2_SetActorLocationAndRotation', X + 600, 0, self=pawn,
               NewLocation=fcall(g, f'{SC}:K2_GetComponentLocation', X + 260, 300, self=mark),
               NewRotation=fcall(g, f'{SC}:K2_GetComponentRotation', X + 260, 440, self=mark), bTeleport='true')
    # The pawn is teleported first; blending its displaced follow camera sweeps through the room.
    vt = fcall(g, f'{PC_P}:SetViewTargetWithBlend', X + 960, 0, self=pc, BlendTime=0.0,
               NewViewTarget=make(g, X + 700, 380, 'reference to self'))
    go(nl, tp)
    go(tp, vt)
    box(g, 'Stage the duel', '',
        band(g, -200, 900, x0=X - 40), 'stage')

    g, e, _ = new_function(BP, 'CutTo', [('bHero', T('bool'))])
    g.at(e, 0, 0)
    a = fcall(g, '/Script/Engine.ActorComponent:SetActive', 300, 0, self=mget(g, 'HeroCam', 100, 200),
              bNewActive=po(e, 'bHero'))
    b = fcall(g, '/Script/Engine.ActorComponent:SetActive', 600, 0, self=mget(g, 'BattleCam', 400, 200),
              bNewActive=fcall(g, f'{KML}:Not_PreBool', 400, 320, A=po(e, 'bHero')))
    chain(e, a, b)
    box(g, 'Camera cut', 'The view target is this actor, so whichever camera is active is the shot: a hard cut.',
        g.ed.list_all_nodes(), 'stage')

    g, e, _ = new_function(BP, 'EndEncounter')
    g.at(e, 0, 0)
    pc = fcall(g, f'{GS}:GetPlayerController', 0, 220, PlayerIndex=0)
    rm = fcall(g, '/Script/UMG.Widget:RemoveFromParent', 300, 0, self=mget(g, 'Widget', 120, 380))
    im = fcall(g, f'{UWBL}:SetInputMode_GameOnly', 560, 0, PlayerController=pc)
    cur = fcall(g, f'{PC_P}:SetShowMouseCursor', 860, 0, self=pc, bShowMouseCursor='false')
    pawn = fcall(g, f'{GS}:GetPlayerPawn', 860, 420, PlayerIndex=0)
    player = make(g, 1120, 0, 'CastToBP_FoAPlayer')
    wire(po(pawn), pi(player, 'Object'))
    end_interaction = fcall(g, f'{PLAYER_C}:EndInteraction', 1440, -120, self=as_pin(player))
    rs = fcall(g, f'{CTL_P}:ResetIgnoreInputFlags', 1760, 0, self=pc)
    vt = fcall(g, f'{PC_P}:SetViewTargetWithBlend', 2080, 0, self=pc, BlendTime=1.0, NewViewTarget=pawn)
    chain(e, rm, im, cur, player, end_interaction, rs, vt)
    go(player, rs, 'CastFailed')
    X = 2440
    box(g, 'Give the morning back', 'Menu off, game input and cursor back, camera back on the Nightmare.',
        band(g, -200, 900, x1=X - 100), 'stage')
    cut = fcall(g, SELF('CutTo'), X, 0, bHero='false')
    clr = fcall(g, SELF('ClearParty'), X + 260, 0)
    hide = fcall(g, '/Script/Engine.Actor:SetActorHiddenInGame', X + 520, 0, bNewHidden='true')
    a = mset(g, 'bActive', X + 780, 0, 'false')
    t = mset(g, 'bPlayerTurn', X + 1040, 0, 'false')
    chain(vt, cut, clr, hide, a, t)
    box(g, 'Strike the set', 'Garments gone, mound hidden, so StartEncounter can run again on a new day.',
        band(g, -200, 900, x0=X - 40), 'stage')
    print('stage ok')


# ---------------------------------------------------------------- stubs + public entry points
def sigs():
    move, gar = move_t(), garment_t()
    I, B, N_, R = T('int'), T('bool'), T('name'), T('real')
    return {
        'MoveCost': ((('Move', move),), (('Cost', I),), True), 'CanUseMove': ((('Move', move),), (('bCan', B),), True),
        'MoveDetail': ((('Move', move),), (('Detail', T('text')),), True),
        'KnowsPattern': ((), (('bKnows', B),), False), 'TargetGarment': ((), (('Garment', gar),), True),
        'ApplySelf': ((('Move', move),), (), False),
        'SeekTarget': ((('Offset', I), ('Step', I), ('Tries', I)), (), False),
        'CycleTarget': ((('Direction', I),), (), False),
        'PickIntentsFrom': ((('Index', I), ('bOpening', B), ('bAny', B)), (('bTelegraph', B),), False),
        'PickIntents': ((('bOpening', B),), (('bTelegraph', B),), False), 'ResetStats': ((), (), False),
        'SpawnFrom': ((('Index', I),), (), False), 'SpawnParty': ((), (), False),
        'ClearFrom': ((('Index', I),), (), False), 'ClearParty': ((), (), False),
        'DrawKeys': ((('Remaining', I),), (), False), 'BeginTimedInput': ((('Move', move),), (), False),
        'ApplyPlayerMove': ((('Multiplier', I),), (), False),
        'FindTwin': ((('Garment', gar), ('Index', I)), (('Twin', I),), False),
        'EnemyAct': ((('Garment', gar),), (), False),
        'DreamPulse': ((('Mode', I), ('Seconds', R)), (), False), 'DreamCycle': ((('bStart', B),), (), False),
        'ShowEncounter': ((), (), False), 'CutTo': ((('bHero', B),), (), False), 'EndEncounter': ((), (), False),
        'SetState': ((('NewState', N_),), (), False), 'StartEncounter': ((('OpponentId', N_),), (), False),
        'ChooseMove': ((('Move', move),), (), False), 'Flee': ((), (), False), 'Items': ((), (), False),
        'SubmitKey': ((('Key', S(unreal.Key)),), (), False), 'HandleKey': ((('Key', S(unreal.Key)),), (), False),
    }


def stubs():
    """Every function graph (empty, with its parameters) and custom event, so one Hayba compile makes them all
    callable before the filling phases run."""
    unreal.get_editor_subsystem(unreal.EditorActorSubsystem).select_nothing()
    unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(unreal.load_asset(BP))
    stub_functions(BP, sigs())
    stub_events(BP, tuple(f'S_{s}' for s in STATES) + STEPS)
    print('encounter stubs ok: now Hayba blueprint_compile BP_Encounter')


def entries():
    move = move_t()

    g, e, _ = new_function(BP, 'SetState', [('NewState', T('name'))])
    g.at(e, 0, 0)
    s = mset(g, 'BattleState', 260, 0, po(e, 'NewState'))
    sc = make(g, 520, 0, 'Call', 'OnStateChanged')
    feed(sc, State=po(e, 'NewState'))
    ch = make(g, 820, 0, 'Call', 'OnChanged')
    fn = fcall(g, '/Script/Engine.KismetStringLibrary:Concat_StrStr', 820, 260, A='S_',
               B=fcall(g, '/Script/Engine.KismetStringLibrary:Conv_NameToString', 560, 300, InName=po(e, 'NewState')))
    tm = fcall(g, f'{KSL}:K2_SetTimer', 1100, 0, FunctionName=fn, Time=0.01, bLooping='false')
    chain(e, s, sc, ch, tm)
    box(g, 'SetState(NewState)', 'Each battle state is an event named S_<State>; it runs on the next tick, so the '
        'machine never recurses. OnStateChanged tells the UI and VFX.', g.ed.list_all_nodes(), 'entry')

    g, e, _ = new_function(BP, 'StartEncounter', [('OpponentId', T('name'))])
    g.at(e, 0, 0)
    br = g.at(g.ed.add_branch_node(), 300, 0)
    wire(po(fcall(g, f'{KML}:Not_PreBool', 100, 220, A=mget(g, 'bActive', -60, 240))), BEL.find_condition_pin(br))
    find = fcall(g, f'{BML}:Map_Find', 560, 260, TargetMap=mget(g, 'Opponents', 360, 260), Key=po(e, 'OpponentId'))
    br2 = g.at(g.ed.add_branch_node(), 860, 0)
    wire(po(find, 'ReturnValue'), BEL.find_condition_pin(br2))
    sl = mset(g, 'Leader', 1120, 0, po(find, 'Value'))
    act = mset(g, 'bActive', 1380, 0, 'true')
    rs = fcall(g, SELF('ResetStats'), 1640, 0)
    sp = fcall(g, SELF('SpawnParty'), 1900, 0)
    unhide = fcall(g, '/Script/Engine.Actor:SetActorHiddenInGame', 2160, 0, bNewHidden='false')
    st = fcall(g, SELF('SetState'), 2420, 0, NewState='Intro')
    go(e, br)
    go(br, br2)
    go(br2, sl)
    chain(sl, act, rs, sp, unhide, st)
    box(g, 'StartEncounter(OpponentId)', 'BP_BeatDirector calls this on T8 with "Shirt" (F8 in dev). Ignored while a '
        'fight is on or when the id is unknown.', g.ed.list_all_nodes(), 'entry')

    g, e, _ = new_function(BP, 'ChooseMove', [('Move', move)])
    g.at(e, 0, 0)
    ok = fcall(g, f'{KML}:BooleanAND', 320, 220, A=mget(g, 'bPlayerTurn', 60, 200),
               B=po(fcall(g, SELF('CanUseMove'), 60, 320, Move=po(e, 'Move')), 'bCan'))
    br = g.at(g.ed.add_branch_node(), 560, 0)
    wire(po(ok), BEL.find_condition_pin(br))
    off = mset(g, 'bPlayerTurn', 820, 0, 'false')
    pm = mset(g, 'PendingMove', 1080, 0, po(e, 'Move'))
    st = fcall(g, SELF('SetState'), 1340, 0, NewState='ResolvePlayerAction')
    go(e, br)
    go(br, off)
    chain(off, pm, st)
    box(g, 'ChooseMove(Move)', 'Act, Breathe and Mirror all end here: on the player\'s turn and only if usable.',
        g.ed.list_all_nodes(), 'entry')

    g, e, _ = new_function(BP, 'Flee')
    g.at(e, 0, 0)
    br = g.at(g.ed.add_branch_node(), 260, 0)
    wire(po(mget(g, 'bPlayerTurn', 60, 200)), BEL.find_condition_pin(br))
    off = mset(g, 'bPlayerTurn', 520, 0, 'false')
    pm = g.at(g.ed.add_set_member_variable_node('PendingMove', ''), 780, 0)
    nar = mset(g, 'Narration', 1040, 0, mget(g, 'FleeLine', 860, 200))
    st = fcall(g, SELF('SetState'), 1300, 0, NewState='ResolvePlayerAction')
    go(e, br)
    go(br, off)
    chain(off, pm, nar, st)
    box(g, 'Flee()', 'You can\'t run from getting dressed: the line plays and the turn is gone.', g.ed.list_all_nodes(),
        'entry')

    g, e, _ = new_function(BP, 'Items')
    g.at(e, 0, 0)
    nar = mset(g, 'Narration', 260, 0, mget(g, 'ItemsLine', 60, 200))
    ch = make(g, 520, 0, 'Call', 'OnChanged')
    chain(e, nar, ch)
    box(g, 'Items()', 'shortcut: no item has a battle effect yet, so this only narrates and keeps the turn; give items '
        'a move in DT_Items when one needs it.', g.ed.list_all_nodes(), 'entry')

    g, e, _ = new_function(BP, 'SubmitKey', [('Key', S(unreal.Key))])
    g.at(e, 0, 0)
    clr = fcall(g, f'{KSL}:K2_ClearAndInvalidateTimerHandle', 300, 0, Handle=mget(g, 'KeyTimer', 120, 220))
    want = fcall(g, f'{KAL}:Array_Get', 300, 320, TargetArray=mget(g, 'InputKeys', 80, 320),
                 Index=mget(g, 'InputIndex', 80, 420))
    hit = fcall(g, f'{KIL}:EqualEqual_KeyKey', 560, 320, A=po(e, 'Key'), B=po(want, 'Item'))
    one = fcall(g, f'{KML}:SelectInt', 800, 320, A=1, B=0, bPickA=hit)
    sh = mset(g, 'InputHits', 1280, 0, fcall(g, f'{KML}:Add_IntInt', 1040, 260, A=mget(g, 'InputHits', 800, 200), B=one))
    adv = fcall(g, SELF('AdvancePrompt'), 1540, 0)
    chain(e, clr, sh, adv)
    box(g, 'SubmitKey(Key)', 'Stop the window, count a hit if it is the prompted key, move on.', g.ed.list_all_nodes(),
        'input')

    g, e, _ = new_function(BP, 'HandleKey', [('Key', S(unreal.Key))])
    g.at(e, 0, 0)
    br = g.at(g.ed.add_branch_node(), 260, 0)
    wire(po(mget(g, 'bAwaitingKey', 60, 200)), BEL.find_condition_pin(br))
    sub = fcall(g, SELF('SubmitKey'), 520, -160, Key=po(e, 'Key'))
    br2 = g.at(g.ed.add_branch_node(), 520, 120)
    wire(po(mget(g, 'bPlayerTurn', 320, 300)), BEL.find_condition_pin(br2))
    k = po(e, 'Key')
    left = fcall(g, f'{KIL}:EqualEqual_KeyKey', 780, 420, A=k, B='(KeyName="Left")')
    right = fcall(g, f'{KIL}:EqualEqual_KeyKey', 780, 560, A=k, B='(KeyName="Right")')
    tab = fcall(g, f'{KIL}:EqualEqual_KeyKey', 780, 700, A=k, B='(KeyName="Tab")')
    dirn = fcall(g, f'{KML}:SelectInt', 1280, 420, A=-1,
                 B=fcall(g, f'{KML}:SelectInt', 1040, 560, A=1, B=0,
                         bPickA=fcall(g, f'{KML}:BooleanOR', 1040, 700, A=right, B=tab)), bPickA=left)
    br3 = g.at(g.ed.add_branch_node(), 1500, 120)
    wire(po(fcall(g, f'{KML}:NotEqual_IntInt', 1500, 420, A=dirn, B=0)), BEL.find_condition_pin(br3))
    cyc = fcall(g, SELF('CycleTarget'), 1780, 120, Direction=dirn)
    ch = make(g, 2040, 120, 'Call', 'OnChanged')
    go(e, br)
    go(br, sub)
    go(br, br2, 'else')
    go(br2, br3)
    go(br3, cyc)
    go(cyc, ch)
    box(g, 'HandleKey(Key)', 'Any key: the timed prompt when one is open, else Left, Right or Tab move the target on '
        'the player\'s turn.', g.ed.list_all_nodes(), 'input')
    print('entries ok')


# ---------------------------------------------------------------- the state machine (event graph)
def events():
    # Keep the compiled custom events (stubs) and clear everything else: removing an event and calling it in the
    # same run leaves call nodes without pins, because the skeleton class drops it at once.
    g = Graph(BP)
    for c in list(g.ed.list_comment_nodes()):
        g.ed.remove_comment_node(c)
    keep = set(f'S_{s}' for s in STATES) | set(STEPS)
    EV = {}
    for n in g.ed.list_all_nodes():
        by_key = {event_key(k): k for k in keep}
        title = by_key.get(event_name(n))
        if title and title not in EV:
            EV[title] = n
    g.ed.remove_nodes([n for n in g.ed.list_all_nodes() if n not in EV.values()])
    missing = keep - set(EV)
    assert not missing, f'run the stubs phase first: {missing}'

    def cev(name, x, y):
        return g.at(EV[name], x, y)
    ROW = 640

    def call(f, x, y, **k):
        return fcall(g, SELF(f), x, y, **k)

    def setstate(st, x, y):
        return call('SetState', x, y, NewState=st)

    def delay(x, y, d=None):
        return fcall(g, f'{KSL}:Delay', x, y, Duration=d if d is not None else mget(g, 'TurnPause', x - 200, y + 200))

    def thread(*nodes):
        """Exec-chain the nodes that exist (dream hooks are absent until the pp lane adds them)."""
        nodes = [n for n in nodes if n is not None]
        chain(*nodes)
        return nodes[-1]

    # Row 0: setup and keys
    bp_ev = g.event('ReceiveBeginPlay', 0, 0)
    hide = fcall(g, '/Script/Engine.Actor:SetActorHiddenInGame', 300, 0, bNewHidden='true')
    inp = fcall(g, '/Script/Engine.Actor:EnableInput', 600, 0,
                PlayerController=fcall(g, f'{GS}:GetPlayerController', 300, 220, PlayerIndex=0))
    chain(bp_ev, hide, inp)
    anyk = make(g, 1000, 0, 'Any Key')
    for prop in ('consume_input', 'bConsumeInput'):
        try:
            anyk.set_editor_property(prop, False)
            break
        except Exception:
            pass
    hk = call('HandleKey', 1320, 0, Key=po(anyk, 'Key'))
    go(anyk, hk, 'Pressed')
    f8 = make(g, 1000, 260, 'Keyboard', 'F8')
    start = call('StartEncounter', 1320, 260, OpponentId='Shirt')
    go(f8, start, 'Pressed')
    box(g, 'Setup and keys', 'Hidden until the fight. Every key goes to HandleKey (not consumed, so menus still get '
        'it); F8 starts the Shirt fight in dev.', band(g, -100, 500), 'entry')

    # Row 1: Intro, one entrance card per garment
    y = ROW
    ev = cev('S_Intro', 0, y)
    show = call('ShowEncounter', 300, y)
    cyc = call('DreamCycle', 560, y, bStart='true')
    st0 = mset(g, 'Step', 1000, y, 0)
    first = call('IntroStep', 1260, y)
    thread(ev, show, cyc, st0, first)
    istep = cev('IntroStep', 1700, y)
    n = fcall(g, f'{KAL}:Array_Length', 1700, y + 300, TargetArray=mget(g, 'Garments', 1500, y + 300))
    br = g.at(g.ed.add_branch_node(), 2000, y)
    wire(po(fcall(g, f'{KML}:Less_IntInt', 1940, y + 260, A=mget(g, 'Step', 1700, y + 180), B=n)),
         BEL.find_condition_pin(br))
    gm = fcall(g, f'{KAL}:Array_Get', 2200, y + 300, TargetArray=mget(g, 'Garments', 2000, y + 420),
               Index=mget(g, 'Step', 2000, y + 500))
    rise = fcall(g, GSELF('Rise'), 2300, y - 120, self=po(gm, 'Item'))
    nar = mset(g, 'Narration', 2600, y - 120, field(g, field(g, po(gm, 'Item'), 'Data', G_C, 2440, y + 300),
                                                    'IntroLine', OPP_C, 2620, y + 300))
    burst = make(g, 2860, y - 120, 'Call', 'OnSandBurst')
    ch = make(g, 3120, y - 120, 'Call', 'OnChanged')
    inc = mset(g, 'Step', 3380, y - 120, fcall(g, f'{KML}:Add_IntInt', 3180, y + 160, A=mget(g, 'Step', 2980, y + 160), B=1))
    dl = delay(3640, y - 120, 1.5)
    again = call('IntroStep', 3900, y - 120)
    picks = call('PickIntents', 2300, y + 160, bOpening=mget(g, 'bFreePreview', 2100, y + 600))
    nxt = setstate('PlayerCommand', 2600, y + 520)
    go(istep, br)
    go(br, rise)
    fx = sand_fx(g, 2860, y - 400, po(gm, 'Item'))
    chain(*[n for n in (rise, nar, burst, fx, ch, inc, dl) if n is not None])
    go(dl, again, 'Completed')
    go(br, picks, 'else')
    go(picks, nxt)
    box(g, 'Intro', 'The style cycle starts, then each garment rises out of the sand with its entrance card, 1.5 s '
        'apart; then they pick their first moves (the opening move on a known day).', band(g, y - 300, y + 640), 'stage')

    # Row 2: PlayerCommand
    y = 2 * ROW + 100
    ev = cev('S_PlayerCommand', 0, y)
    aim = call('CycleTarget', 300, y, Direction=0)
    on = mset(g, 'bPlayerTurn', 560, y, 'true')
    pulse = call('DreamPulse', 820, y, Mode=1, Seconds=0.5)  # turn change: a beat of pixel art
    ch = make(g, 1260, y, 'Call', 'OnChanged')
    thread(ev, aim, on, pulse, ch)
    box(g, 'PlayerCommand', 'Aim at a standing garment and wait for Act, Breathe, Mirror, Items or Flee from the '
        'command window (ChooseMove, Flee, Items).', band(g, y - 100, y + 500), 'entry')

    # Row 3: ResolvePlayerAction
    y = 3 * ROW + 300
    ev = cev('S_ResolvePlayerAction', 0, y)
    cut = call('CutTo', 300, y, bHero='true')
    br = g.at(g.ed.add_branch_node(), 560, y)
    wire(po(fcall(g, f'{KSL}:IsValid', 360, y + 220, Object=mget(g, 'PendingMove', 160, y + 220))),
         BEL.find_condition_pin(br))
    br2 = g.at(g.ed.add_branch_node(), 820, y - 140)
    wire(po(field(g, mget(g, 'PendingMove', 620, y + 120), 'bTimedInput', MOVE_C, 820, y + 120)),
         BEL.find_condition_pin(br2))
    bti = call('BeginTimedInput', 1080, y - 280, Move=mget(g, 'PendingMove', 880, y - 400))
    nxp = call('NextPrompt', 1380, y - 280)
    apm = call('ApplyPlayerMove', 1080, y - 40, Multiplier=1)
    done1 = call('PlayerActionDone', 1380, y - 40)
    ch = make(g, 1080, y + 300, 'Call', 'OnChanged')
    done2 = call('PlayerActionDone', 1380, y + 300)
    go(ev, cut)
    go(cut, br)
    go(br, br2)
    go(br2, bti)
    go(bti, nxp)
    go(br2, apm, 'else')
    go(apm, done1)
    go(br, ch, 'else')
    go(ch, done2)
    pad_ = cev('PlayerActionDone', 1800, y)
    ch2 = make(g, 2100, y, 'Call', 'OnChanged')
    dl = delay(2360, y)
    back = call('CutTo', 2620, y, bHero='false')
    after = mset(g, 'AfterCheck', 2880, y, 'EnemyPhase')
    chk = setstate('CheckEnd', 3140, y)
    chain(pad_, ch2, dl)
    go(dl, back, 'Completed')
    chain(back, after, chk)
    box(g, 'ResolvePlayerAction', 'Cut to the Nightmare. Timed moves run the key prompts first; the rest land at once. '
        'Flee has no move, only its line. Then on to the enemies.', band(g, y - 460, y + 520), 'turn')

    # Row 4: timed input
    y = 5 * ROW
    np_ = cev('NextPrompt', 0, y)
    n = fcall(g, f'{KAL}:Array_Length', 200, y + 300, TargetArray=mget(g, 'InputKeys', 0, y + 300))
    br = g.at(g.ed.add_branch_node(), 640, y)
    wire(po(fcall(g, f'{KML}:Less_IntInt', 440, y + 220, A=mget(g, 'InputIndex', 200, y + 180), B=n)),
         BEL.find_condition_pin(br))
    aw = mset(g, 'bAwaitingKey', 900, y - 140, 'true')
    tm = fcall(g, f'{KSL}:K2_SetTimer', 1160, y - 140, FunctionName='AdvancePrompt',
               Time=mget(g, 'ActiveWindow', 940, y + 60), bLooping='false')
    st = mset(g, 'KeyTimer', 1480, y - 140, po(tm, 'ReturnValue'))
    ch = make(g, 1740, y - 140, 'Call', 'OnChanged')
    hits = mget(g, 'InputHits', 900, y + 420)
    perfect = fcall(g, f'{KML}:GreaterEqual_IntInt', 1160, y + 420, A=hits, B=n)
    enough = fcall(g, f'{KML}:GreaterEqual_IntInt', 1160, y + 560, A=hits, B=mget(g, 'KeysToHit', 900, y + 560))
    mult = fcall(g, f'{KML}:SelectInt', 1640, y + 420, A=2,
                 B=fcall(g, f'{KML}:SelectInt', 1400, y + 520, A=1, B=0, bPickA=enough), bPickA=perfect)
    app = call('ApplyPlayerMove', 1900, y + 200, Multiplier=mult)
    fin = call('PlayerActionDone', 2200, y + 200)
    go(np_, br)
    go(br, aw)
    chain(aw, tm, st, ch)
    go(br, app, 'else')
    go(app, fin)
    box(g, 'Timed input', 'One prompt per key, open ActiveWindow seconds (the timer calls AdvancePrompt on a miss). '
        'KeysToHit hits land the move, a perfect run doubles it.', band(g, y - 300, y + 700, x1=2500), 'input')
    adv = cev('AdvancePrompt', 2600, y)
    off = mset(g, 'bAwaitingKey', 2900, y, 'false')
    si = mset(g, 'InputIndex', 3160, y, fcall(g, f'{KML}:Add_IntInt', 2940, y + 220,
                                              A=mget(g, 'InputIndex', 2740, y + 220), B=1))
    ch2 = make(g, 3420, y, 'Call', 'OnChanged')
    dl = delay(3680, y, 0.25)
    again = call('NextPrompt', 3940, y)
    chain(adv, off, si, ch2, dl)
    go(dl, again, 'Completed')
    box(g, 'AdvancePrompt', 'Close the window, step to the next key after a beat.', band(g, y - 300, y + 700, x0=2500),
        'input')

    # Row 5: EnemyPhase, one garment at a time
    y = 6 * ROW + 300
    ev = cev('S_EnemyPhase', 0, y)
    s0 = mset(g, 'Step', 300, y, 0)
    first = call('EnemyStep', 560, y)
    chain(ev, s0, first)
    es = cev('EnemyStep', 900, y)
    n = fcall(g, f'{KAL}:Array_Length', 900, y + 300, TargetArray=mget(g, 'Garments', 700, y + 300))
    br = g.at(g.ed.add_branch_node(), 1180, y)
    wire(po(fcall(g, f'{KML}:Less_IntInt', 1140, y + 260, A=mget(g, 'Step', 940, y + 180), B=n)),
         BEL.find_condition_pin(br))
    # Step - 1: every use of this pure Get runs after the Step += 1 below and re-reads Step (was one past the end)
    gm = fcall(g, f'{KAL}:Array_Get', 1180, y + 420, TargetArray=mget(g, 'Garments', 980, y + 500),
               Index=fcall(g, f'{KML}:Subtract_IntInt', 980, y + 600, A=mget(g, 'Step', 780, y + 600), B=1))
    G = po(gm, 'Item')
    inc = mset(g, 'Step', 1440, y - 140, fcall(g, f'{KML}:Add_IntInt', 1440, y + 300, A=mget(g, 'Step', 1240, y + 300), B=1))
    br_alive = g.at(g.ed.add_branch_node(), 1700, y - 140)
    wire(po(fcall(g, GSELF('IsAlive'), 1480, y + 440, self=G), 'bAlive'), BEL.find_condition_pin(br_alive))
    skip = call('EnemyStep', 1960, y + 120)
    br_stun = g.at(g.ed.add_branch_node(), 1960, y - 260)
    wire(po(fcall(g, f'{KML}:EqualEqual_NameName', 1760, y + 300, A=field(g, G, 'State', G_C, 1560, y + 580),
                  B='Stunned')), BEL.find_condition_pin(br_stun))
    recover = g.at(g.ed.add_set_member_variable_node('State', G_C), 2220, y - 460)
    wire(G, pi(recover, 'self'))
    val(recover, 'State', 'Idle')
    fmt = make(g, 2220, y - 200, 'Format Text')
    val(fmt, 'Format', "{Name} still can't steady itself.")  # reads right for The Trousers too
    wire(po(field(g, field(g, G, 'Data', G_C, 1980, y - 80), 'DisplayName', OPP_C, 2000, y + 20)), pi(fmt, 'Name'))
    snar = mset(g, 'Narration', 2500, y - 460, po(fmt))
    sch = make(g, 2760, y - 460, 'Call', 'OnChanged')
    sdl = delay(3020, y - 460)
    snext = call('EnemyStep', 3280, y - 460)
    act = call('EnemyAct', 2220, y + 120, Garment=G)
    lunge = fcall(g, GSELF('Lunge'), 2500, y + 120, self=G)
    ch = make(g, 2760, y + 120, 'Call', 'OnChanged')
    big = fcall(g, f'{KML}:LessEqual_IntInt', 2760, y + 400,
                A=field(g, field(g, G, 'Intent', G_C, 2380, y + 400), 'ComposureDelta', MOVE_C, 2560, y + 400), B=-8)
    brb = g.at(g.ed.add_branch_node(), 3020, y + 120)
    wire(po(big), BEL.find_condition_pin(brb))
    shake = call('Shake', 3280, y - 20)
    pulse = call('DreamPulse', 3540, y - 20, Mode=3, Seconds=0.4)  # big hit: CRT
    edl = delay(4000, y + 120)
    enext = call('EnemyStep', 4260, y + 120)
    go(es, br)
    go(br, inc)
    go(inc, br_alive)
    go(br_alive, br_stun)
    go(br_alive, skip, 'else')
    go(br_stun, recover)
    chain(recover, snar, sch, sdl)
    go(sdl, snext, 'Completed')
    go(br_stun, act, 'else')
    chain(act, lunge, ch, brb)
    go(brb, shake)
    go(thread(shake, pulse), edl)
    go(brb, edl, 'else')
    go(edl, enext, 'Completed')
    drain = fcall(g, f'{KML}:Max', 1440, y + 800,
                  A=fcall(g, f'{KML}:Subtract_IntInt', 1200, y + 800, A=mget(g, 'Composure', 1000, y + 800),
                          B=field(g, mget(g, 'Leader', 800, y + 920), 'DrainPerTurn', OPP_C, 1000, y + 920)), B=0)
    sc = mset(g, 'Composure', 1700, y + 680, drain)
    hide_rev = mset(g, 'bRevealed', 1960, y + 680, 'false')
    picks = call('PickIntents', 2220, y + 680, bOpening='false')
    brt = g.at(g.ed.add_branch_node(), 2480, y + 680)
    wire(po(picks, 'bTelegraph'), BEL.find_condition_pin(brt))
    tpulse = call('DreamPulse', 2740, y + 560, Mode=2, Seconds=0.6)  # a telegraph: dither
    after = mset(g, 'AfterCheck', 3300, y + 680, 'PlayerCommand')
    chk = setstate('CheckEnd', 3560, y + 680)
    go(br, sc, 'else')
    chain(sc, hide_rev, picks, brt)
    if tpulse:
        go(brt, tpulse)
        go(tpulse, after)
    else:
        go(brt, after)
    go(brt, after, 'else')
    chain(after, chk)
    box(g, 'EnemyPhase', 'Each standing garment in line order: stunned ones recover, the rest act and lunge; a big hit '
        'freezes, shakes and pulses the style. Then the drain, new intents, CheckEnd.', band(g, y - 560, y + 1040),
        'turn')

    # Row 6: CheckEnd, Victory, Defeat
    y = 9 * ROW
    ev = cev('S_CheckEnd', 0, y)
    br = g.at(g.ed.add_branch_node(), 300, y)
    wire(po(fcall(g, f'{KML}:LessEqual_IntInt', 100, y + 220, A=mget(g, 'Remaining', -100, y + 220), B=0)),
         BEL.find_condition_pin(br))
    v = setstate('Victory', 560, y - 140)
    br2 = g.at(g.ed.add_branch_node(), 560, y + 120)
    wire(po(fcall(g, f'{KML}:LessEqual_IntInt', 360, y + 340, A=mget(g, 'Composure', 160, y + 340), B=0)),
         BEL.find_condition_pin(br2))
    d = setstate('Defeat', 820, y)
    on = call('SetState', 820, y + 260, NewState=mget(g, 'AfterCheck', 620, y + 420))
    go(ev, br)
    go(br, v)
    go(br, br2, 'else')
    go(br2, d)
    go(br2, on, 'else')
    box(g, 'CheckEnd', 'Everything worn wins; no Composure left loses; otherwise on to AfterCheck.',
        band(g, y - 300, y + 620, x1=1300), 'turn')
    for i, (state, disp, line, report) in enumerate((('Victory', 'OnEncounterWon', 'VictoryLine', 'EncounterWon'),
                                                     ('Defeat', 'OnEncounterLost', 'LoseLine', None))):
        x0, yy = 1500, y + i * 460
        ev = cev(f'S_{state}', x0, yy)
        stop = call('DreamCycle', x0 + 260, yy, bStart='false')
        real = None
        dsp = make(g, x0 + 1140, yy, 'Call', disp)
        nar = mset(g, 'Narration', x0 + 1400, yy, field(g, mget(g, 'Leader', x0 + 1200, yy + 220), line, OPP_C,
                                                        x0 + 1400, yy + 220))
        ch = make(g, x0 + 1660, yy, 'Call', 'OnChanged')
        dl = delay(x0 + 1920, yy, 3.0)
        end = call('EndEncounter', x0 + 2180, yy)
        thread(ev, stop, real, dsp, nar, ch, dl)
        go(dl, end, 'Completed')
        if unreal.load_class(None, DIRECTOR_C):
            find = fcall(g, f'{GS}:GetActorOfClass', x0 + 2180, yy + 220, ActorClass=DIRECTOR_C)
            hand = fcall(g, f'{DIRECTOR_C}:ReportEvent', x0 + 2480, yy, self=po(find), Event=report) if report else \
                fcall(g, f'{DIRECTOR_C}:FailDay', x0 + 2480, yy, self=po(find))
            seq(end, find, hand)  # GetActorOfClass is impure: keep it on the exec path
        box(g, state, ('Everything is worn: on to the payoff (T9) with BP_BeatDirector.ReportEvent("EncounterWon").'
                       if report else 'Composure is gone: the day rolls over with BP_BeatDirector.FailDay().') +
            ' The style returns to real first.', band(g, yy - 120, yy + 420, x0=x0 - 40), 'outcome')

    # Shake: hit-stop, then a two-step bump of the battle camera (no shake asset needed)
    y = 10 * ROW + 400
    sh = cev('Shake', 0, y)
    slow = fcall(g, f'{GS}:SetGlobalTimeDilation', 300, y, TimeDilation=0.05)
    hold = delay(600, y, 0.004)
    norm = fcall(g, f'{GS}:SetGlobalTimeDilation', 900, y, TimeDilation=1.0)
    m1 = fcall(g, f'{KSL}:MoveComponentTo', 1200, y, Component=mget(g, 'BattleCam', 1000, y + 220),
               TargetRelativeLocation='(X=-480.0,Y=7.0,Z=194.0)', TargetRelativeRotation='(Pitch=-10.6,Yaw=0.4,Roll=0.6)',
               OverTime=0.05)
    m2 = fcall(g, f'{KSL}:MoveComponentTo', 1600, y, Component=mget(g, 'BattleCam', 1400, y + 220),
               TargetRelativeLocation='(X=-480.0,Y=0.0,Z=200.0)', TargetRelativeRotation='(Pitch=-10.0,Yaw=0.0,Roll=0.0)',
               bEaseOut='true', OverTime=0.2)
    chain(sh, slow, hold)
    go(hold, norm, 'Completed')
    wire(BEL.find_then_pin(norm), pi(m1, 'Move'))
    wire(po(m1, 'Completed'), pi(m2, 'Move'))
    box(g, 'Hit-stop and shake', 'Big hits freeze the world for a beat (time dilation 0.05), then bump the battle '
        'camera and let it settle.', band(g, y - 100, y + 500), 'stage')

    print('events ok: now Hayba blueprint_compile BP_Encounter and asset_save')


PHASES = {'skeleton': skeleton, 'rules': rules, 'stage': stage, 'stubs': stubs, 'entries': entries, 'events': events}
for _phase in PHASE.split(','):
    PHASES[_phase]()
