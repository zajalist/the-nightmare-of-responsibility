"""mech_flow step 3: BP_BeatDirector graphs. Run after build_flow_data.py and build_gi.py (idempotent, edits in place):
    ue_remote build_director.py FOA_STEP=declare  ->  Hayba blueprint_compile BP_BeatDirector
    ue_remote build_director.py FOA_STEP=funcs      (function graphs)
    ue_remote build_director.py FOA_STEP=events     (event graph; its custom events are kept, so calls stay bound)
    Hayba blueprint_compile BP_BeatDirector
    ue_remote build_director.py FOA_STEP=defaults   (errors report, class defaults, component values, save, no compile)
Compiles go through Hayba's C++ blueprint_compile, never BlueprintEditorLibrary, and CDO writes come last (editor-rules).
No loop macros (editor-rules 19:40): the staged actors are single references, and the two real loops (finding the beat
an event completes, resetting every BPI_Interactable) are small recursive functions with an index.
Other lanes' calls are wired only when their function resolves: ShowTier/PlayGlitch (pp's BP_DreamDirector),
StartShirtEncounter (mech_encounter), the Nightmare and player calls (player lane), the wake-up cinematic (wake-up lane).
Rerun both steps when those land."""
import os
exec(open('P:/FoA/Tools/Unreal/flow/flow_common.py').read())

STEP = os.environ.get('FOA_STEP', 'funcs')
EVENTS = ('FailDay', 'RestartDay', 'FadeToNextMorning', 'GallopMare', 'PlayWakeUp', 'EndLevel', 'WakeUpDone',
          'SkipWakeUp')  # custom events, kept across rebuilds
PDA_C, GI_C, DIR_C = cls_path(PDA), cls_path(GI), cls_path(DIR)
NAME, INT, BOOL = ptype('name'), ptype('int'), ptype('bool')
PC_, CTRL, ACTOR, SC = ('/Script/Engine.' + c for c in ('PlayerController', 'Controller', 'Actor', 'SceneComponent'))
PLAYER, NM = '/Game/FoA/Characters/Player/BP_FoAPlayer', '/Game/FoA/Characters/Player/BP_Nightmare'
WAKE = '/Game/FoA/Cinematics/BP_WakeUpCinematic'                                   # retired once LS_WakeUp plays here
LS = '/Game/FoA/Cinematics/LS_WakeUp'                                              # cine lane: binding tag Player
THRESHOLD = '/Game/FoA/Level2/Transition/BP_DreamThreshold'
HINT = '/Game/FoA/UI/Game/WBP_SkipHint'                                            # ui lane: hold-to-skip hint
INTERACTOR = '/Game/FoA/Gameplay/BPC_Interactor'                                     # mech_core: OnBeatEvent(Event)
BED_MPC = '/Game/FoA/Characters/Player/MPC_FoAPlayer'                                # player lane: duvet dent
BLACK = '(R=0.0,G=0.0,B=0.0,A=1.0)'
REMOVED = ('LearnAll', 'FindBeatFor')  # replaced by LearnFlag and the recursive FindBeatFrom


def can_call(path, *funcs):
    """The asset exists and every function resolves (a lane may save its asset before its API is in)."""
    if not exists(path):
        return False
    ed = GE.get_graph_editor_by_name(unreal.load_asset(DIR), 'EventGraph')
    for f in funcs:
        n = ed.add_call_function_node(f'{cls_path(path)}:{f}')
        if not n:
            return False
        ed.remove_nodes([n])
    return True


HAS_DREAM = can_call(DREAM, 'SetTier', 'TriggerGlitchBurst')
HAS_ENC = can_call(ENC, 'StartEncounter')
HAS_NM = can_call(NM, 'Appear', 'Vanish')
HAS_PLAYER = {f: can_call(PLAYER, f) for f in ('Equip', 'UnequipAll', 'SetTopDownView', 'SetCinematic', 'SetSandOverlay', 'SetSandTransition')}
FRONT = '/Game/FoA/UI/Framework/BP_FoAFrontEnd'  # UI lane
HAS_FE_END = can_call(FRONT, 'EndOfLevel')
HAS_ROLLOVER = can_call(FRONT, 'PlayDayRollover')  # ui lane (P13); its OnRolloverCovered starts the next morning
HAS_LETTERBOX = can_call(DREAM, 'SetLetterbox')
HAS_REVEAL = can_call(DREAM, 'SetColorReveal')
HAS_BPI = exists(BPI)
HAS_LS = exists(LS)  # the director plays LS_WakeUp itself; BP_WakeUpCinematic is only the fallback
HAS_WAKE = exists(WAKE) and not HAS_LS
HAS_BED = exists(BED_MPC)

SIGS = {  # name: (inputs, outputs, pure)
    'GetFoAGI': ((), (('GI', 'gi'),), True),
    'ResetTasks': ((), (), False), 'TickTask': ((('Task', INT),), (), False),
    'GetPhoneTasks': ((), (('Labels', 'texts'), ('Ticked', 'bools')), True),
    'LearnFlag': ((('Flag', NAME),), (), False), 'LearnFromFailure': ((), (), False),
    'FindBeatFrom': ((('Event', NAME), ('From', INT)), (('Index', INT),), False),
    'EnterBeat': ((('Index', INT),), (), False), 'RunBeatHooks': ((('Id', NAME),), (), False),
    'CompleteBeat': ((('Index', INT),), (), False), 'ReportEvent': ((('Event', NAME),), (), False),
    'BeginMorning': ((), (), False), 'StartMorningBeats': ((), (), False), 'OpenMorningPhone': ((), (), False), 'RaiseMorningPhone': ((), (), False),
    'CheckFirstSteps': ((), (), False),
    'EnterTopDown': ((), (), False), 'StageWrongWall': ((), (), False), 'ExitTopDown': ((), (), False),
    'ExitTopDownCut': ((), (), False),
    'PayoffShot': ((), (), False), 'PayoffShotOut': ((), (), False), 'PayoffShotCut': ((), (), False),
    'SetCeilingHidden': ((('Hidden', BOOL),), (), False), 'ShowCeiling': ((), (), False),
    'MoveDoor': ((), (), False), 'RestoreDoor': ((), (), False), 'RefillDrawer': ((), (), False),
    'OpenTheDoor': ((), (), False),
    'ResetHouse': ((), (), False), 'ResetToTitle': ((), (), False), 'FreezeForRollover': ((), (), False),
    'ReturnToBed': ((), (), False), 'StartNextMorning': ((), (), False),
    'SweepInteractables': ((), (), False), 'ResetFrom': ((('Actors', 'actors'), ('I', INT)), (), False),
    'ShowTier': ((('Tier', INT),), (), False), 'PlayGlitch': ((), (), False), 'StartShirtEncounter': ((), (), False),
    'StartWaking': ((), (), False), 'StartShirtFight': ((), (), False), 'SuitUp': ((), (), False),
    'ShowNightmare': ((('Spot', 'scene'),), (), False), 'HideNightmare': ((), (), False), 'RideNightmare': ((), (), False),
    'EquipSuit': ((), (), False), 'UndressPlayer': ((), (), False), 'PlayerTopDown': ((('Enable', BOOL),), (), False),
    'PlayerCinematic': ((('Enable', BOOL),), (), False), 'PayoffDone': ((), (), False), 'PayoffLook': ((('On', BOOL),), (), False), 'CheckWalkedOut': ((), (), False),
    'RevealShirt': ((), (), False),
    'BeginWardrobeTransition': ((), (), False), 'WardrobeSandTick': ((), (), False),
    'PlayerTransition': ((('Amount', ptype('real')), ('Enable', BOOL)), (), False),
    'WardrobeRattle': ((), (), False), 'SetOldWall': ((('Enable', BOOL),), (), False),
    'WardrobeVanish': ((), (), False), 'WardrobeReappear': ((), (), False),
    'FinishWardrobeTransition': ((), (), False), 'ResetWardrobeTransition': ((), (), False),
    'SetWardrobeBlockers': ((('Enable', BOOL),), (), False),
    'SetDoorHidden': ((('Hidden', BOOL),), (), False),
    'PlayerSand': ((('Amount', ptype('real')),), (), False),
    'WardrobeBodyBurst': ((), (), False),
    'SetWardrobeShot': ((('Enable', BOOL),), (), False),
    'SafeWakeExit': ((), (), False),
    'SetWardrobeEcho': ((('Enable', BOOL),), (), False),
}


def t(kind):
    if not isinstance(kind, str):
        return kind
    if kind == 'scene':
        return ptype(unreal.SceneComponent)
    if kind == 'gi':
        return ptype(unreal.load_class(None, GI_C))
    if kind == 'actors':
        return BEL.get_array_type(ptype(unreal.Actor))
    return BEL.get_array_type(ptype({'texts': 'text', 'bools': 'bool', 'names': 'name'}[kind]))


def me(f):
    return self_call(DIR, f)


def open_fn(name):
    g = FGraph.function(DIR, name)
    return g, g.at(entry_node(g), 0, 0)


def field(g, src, src_pin, var, x, y):
    n = g.get(var, x, y, class_path=PDA_C)
    g.link(src, src_pin, n, 'self')
    return n


def field_p(g, src_pin, var, x, y):
    n = g.get(var, x, y, class_path=PDA_C)
    con(src_pin, g.pin(n, 'self'))
    return n


def arr_get(g, x, y, arr_node, arr_pin, idx_node=None, idx_pin=None, index=None):
    """Array 'Get (a copy)'; its only data output carries the item (see item())."""
    n = pnode(g, x, y, 'Get(acopy)')
    ins = list(BEL.list_input_pins(n))
    con(_find_pin(arr_node, arr_pin, True), ins[0])
    if idx_node is not None:
        con(_find_pin(idx_node, idx_pin, True), ins[1])
    else:
        assert PIN.set_pin_value(ins[1], str(index))
    return n


def item(n):
    return list(BEL.list_output_pins(n))[0]


def gi_call(g, func, x, y, gi_x, gi_y, **defaults):
    """GI_FoA.<func> with the director's GetFoAGI as target."""
    gi = g.call(me('GetFoAGI'), gi_x, gi_y)
    c = g.call(f'{GI_C}:{func}', x, y, **defaults)
    g.link(gi, 'GI', c, 'self')
    return gi, c


def dispatch(g, name, x, y):
    return pnode(g, x, y, 'Call' + name)


def hear_rollover(g, after, x, y=0):
    '''after -> the front end -> Bind OnRolloverCovered to StartNextMorning (P13): the house resets under the card's
    black, then LS_WakeUp's own 3 s black hides the card's cut.'''
    fe = g.call(f'{GS}:GetActorOfClass', x, y, ActorClass=cls_path(FRONT))
    ok = g.call(f'{KSL}:IsValid', x + 256, y + 192); br = g.branch(x + 512, y)
    g.link(fe, 'ReturnValue', ok, 'Object'); g.link(ok, 'ReturnValue', br, 'Condition'); g.exec_chain(after, fe, br)
    bind, ev = bind_event(g, fe, 'ReturnValue', 'OnRolloverCovered', 'RolloverCovered', x + 800, y)
    g.link(br, 'True', bind, 'execute')
    nm = g.call(me('StartNextMorning'), x + 1184, y + 192)
    g.exec_chain(ev, nm)
    g.comment('Hear the rollover', '', [fe, ok, br, bind, ev, nm], C_DAY)


def pending(g, e, what, lane):
    g.comment('Waiting for ' + what, f'Empty until {what} exists ({lane} lane); rerun build_director.py then', [e], C_DEV)


def actor_check(g, path, after=None, x=256):
    """after -> GetActorOfClass (impure) -> Branch(IsValid); returns (find, valid, branch). Next free column: x + 832."""
    find = g.call(f'{GS}:GetActorOfClass', x, 0, ActorClass=cls_path(path))
    ok = g.call(f'{KSL}:IsValid', x + 320, 192); br = g.branch(x + 576, 0)
    g.link(find, 'ReturnValue', ok, 'Object'); g.link(ok, 'ReturnValue', br, 'Condition')
    g.exec_chain(after or entry_node(g), find, br)
    return find, ok, br


def dream_call(g, func, links, title, desc, **defaults):
    find, ok, br = actor_check(g, DREAM)
    call = g.call(f'{cls_path(DREAM)}:{func}', 1088, 0, **defaults)
    g.link(find, 'ReturnValue', call, 'self'); g.link(br, 'True', call, 'execute')
    nodes = [entry_node(g), find, ok, br, call]
    for pin_name, (src, src_pin) in links.items():
        g.link(src, src_pin, call, pin_name)
        nodes.append(src)
    g.comment(title, desc + ' (skipped if the level has no BP_DreamDirector)', nodes, C_VISUAL)
    return find, call, nodes


def custom_events(ed):
    """Custom event nodes in a graph, by name."""
    return {str(BEL.get_node_title(n)).split(chr(10))[0].replace(' ', ''): n  # title line 1 is the event name
            for n in ed.list_nodes_of_class(unreal.K2Node_CustomEvent)}


def declare():
    bp = unreal.load_asset(DIR)
    unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(bp)
    have = [str(n) for n in BEL.list_graph_names(bp)]
    for old in REMOVED:  # one-time migration (structural: actors deselected and editors closed by flow_common)
        if old in have:
            FGraph.function(DIR, old)  # empties it through the graph editor first: it holds script-made macro nodes
            BEL.remove_function_graph(bp, old)
    ged = GE.get_graph_editor_by_name(bp, 'EventGraph')
    have_ev = custom_events(ged)
    if 'LastLearned' not in [str(n) for n in BEL.list_member_variable_names(bp, False)]:  # P13: the rollover card's line
        assert BEL.add_member_variable(bp, 'LastLearned', ptype('text'))
        BEL.set_blueprint_variable_category(bp, 'LastLearned', 'State')
    have_vars = [str(n) for n in BEL.list_member_variable_names(bp, False)]
    for vname, vtype in (('SeqPlayer', BEL.get_object_reference_type(unreal.LevelSequencePlayer)),
                         ('SkipHint', BEL.get_object_reference_type(unreal.UserWidget)), ('bWakeDone', BOOL),
                         ('Wardrobe', ptype(unreal.Actor)), ('bWardrobeTransition', BOOL),
                         ('WardrobeTransitionStart', ptype('real')), ('WardrobeCameraFOV', ptype('real')),
                         ('WardrobeCameraHome', BEL.get_struct_type(unreal.Transform.static_struct())),
                         ('WardrobeHUD', ptype(unreal.UserWidget)), ('WakeBed', ptype(unreal.Actor)),
                         ('WardrobeEchoHome', ptype('real')),
                         ('WardrobePivotHome', BEL.get_struct_type(unreal.Transform.static_struct())),
                         ('WardrobePivot', ptype(unreal.SceneComponent)), ('WardrobeLastBurst', ptype('real')),
                         ('WardrobeMoveTimeHome', ptype('real')),
                         ('WardrobeInteractor', ptype(unreal.load_class(None, '/Game/FoA/Gameplay/BP_Interactable.BP_Interactable_C'))),
                         ('WardrobeDream', ptype(unreal.load_class(None, cls_path(DREAM)))),
                         ('bTopDownCutPending', BOOL)):
        if vname not in have_vars:  # the wake-up cinematic (LS_WakeUp)
            assert BEL.add_member_variable(bp, vname, vtype)
            BEL.set_blueprint_variable_category(bp, vname, 'Wardrobe' if 'Wardrobe' in vname else 'Wake')
        if vname in ('Wardrobe', 'WakeBed'):
            BEL.set_blueprint_variable_instance_editable(bp, vname, True)
    if 'WardrobeHUDVisibility' not in have_vars:
        vis = ged.add_call_function_node('/Script/UMG.Widget:GetVisibility')
        assert BEL.add_member_variable(bp, 'WardrobeHUDVisibility', PIN.get_pin_type(Graph.pin(vis, 'ReturnValue', 'out')))
        ged.remove_nodes([vis])
    sds, lib, hs, by_name = subobjects(bp)
    for name, component_class in (('FallenWardrobeBlocker', unreal.BoxComponent), ('OldDoorBlocker', unreal.BoxComponent),
                                   ('WardrobeKeyLight', unreal.PointLightComponent), ('OldDoorWall', unreal.StaticMeshComponent)):
        if name not in by_name:
            h, fail = sds.add_new_subobject(unreal.AddNewSubobjectParams(
                parent_handle=by_name['Root'], new_class=component_class, blueprint_context=bp))
            assert not str(fail), fail
            sds.rename_subobject(h, name)
    del sds, lib, hs, by_name
    for name in EVENTS:  # functions and other events call these; build_events keeps them and lays them out
        if name not in have_ev:
            ged.add_custom_event_node(name)
    for name, (ins, outs, pure) in SIGS.items():
        FGraph.function(DIR, name, pure=pure, inputs=[(n, t(k)) for n, k in ins], outputs=[(n, t(k)) for n, k in outs])
    del ged, bp  # Hayba blueprint_compile follows (outside this script)


def build_functions():
    # ---- GetFoAGI -> GI (pure)
    g, e = open_fn('GetFoAGI')
    gi, c = gi_ref(g, 256, 0)
    ret = g.at(result_node(g), 864, 0)
    g.exec_chain(e, c); g.link(c, 'then', ret, 'execute'); g.link(c, 'AsGI_FoA', ret, 'GI')
    g.comment('Game instance', 'GI_FoA holds the day count, the knowledge flags and the notebook', [e, gi, c, ret], C_DATA)

    # ---- ResetTasks
    g, e = open_fn('ResetTasks')
    tt = g.get('TasksTicked', 32, 192); pt = g.get('PhoneTasks', 32, 304)
    clr = g.call(f'{ARR}:Array_Clear', 288, 0); ln = g.call(f'{ARR}:Array_Length', 320, 288)
    rs = g.call(f'{ARR}:Array_Resize', 608, 0)
    g.link(tt, 'TasksTicked', clr, 'TargetArray'); g.link(tt, 'TasksTicked', rs, 'TargetArray')
    g.link(pt, 'PhoneTasks', ln, 'TargetArray'); g.link(ln, 'ReturnValue', rs, 'Size'); g.exec_chain(e, clr, rs)
    g.comment('Phone tasks', 'Every task starts the morning unticked, one flag per PhoneTasks line', [e, tt, pt, clr, ln, rs], C_FLOW)

    # ---- TickTask(Task)
    g, e = open_fn('TickTask')
    tt = g.get('TasksTicked', 32, 192)
    st = g.call(f'{ARR}:Array_Set', 288, 0)
    op = dispatch(g, 'OnPhoneChanged', 672, 0)
    g.link(tt, 'TasksTicked', st, 'TargetArray'); g.link(e, 'Task', st, 'Index'); g.exec_chain(e, st, op)
    g.default(st, 'Item', 'true'); g.default(st, 'bSizeToFit', 'true')  # the wildcard Item takes a literal once typed
    g.comment('Tick a phone task', 'Marks one PhoneTasks line done and tells WBP_Phone to re-read', [e, tt, st, op], C_FLOW)

    # ---- GetPhoneTasks -> Labels, Ticked (pure)
    g, e = open_fn('GetPhoneTasks')
    ret = g.at(result_node(g), 448, 0)
    pt = g.get('PhoneTasks', 128, 176); tt = g.get('TasksTicked', 128, 256)
    g.exec_chain(e, ret); g.link(pt, 'PhoneTasks', ret, 'Labels'); g.link(tt, 'TasksTicked', ret, 'Ticked')
    g.comment('Phone data', 'Task labels and their ticks, same order, for WBP_Phone', [e, ret, pt, tt], C_FLOW)

    # ---- LearnFlag(Flag)
    g, e = open_fn('LearnFlag')
    gi, ln = gi_call(g, 'Learn', 512, 0, 256, 192)
    op = dispatch(g, 'OnPhoneChanged', 832, 0)
    g.link(e, 'Flag', ln, 'Flag'); g.exec_chain(e, ln, op)
    g.comment('Learn a flag', 'GI_FoA keeps it (saved at once, None ignored); the phone notebook re-reads', [e, gi, ln, op], C_DATA)

    # ---- LearnFromFailure: beats whose knowledge comes from the attempt itself (T7 door, T8 shirt)
    # LastLearned = the notebook line this failure taught (empty if nothing new): the rollover card shows it
    g, e = open_fn('LearnFromFailure')
    clr = g.set('LastLearned', 256, 0)
    b = g.get('Beat', 32, 192)
    lf = field(g, b, 'Beat', 'bLearnOnFail', 256, 160); lr = field(g, b, 'Beat', 'Learns', 256, 256)
    gi = g.call(me('GetFoAGI'), 256, 384)
    kn = g.call(f'{GI_C}:HasKnowledge', 544, 352); nk = g.call(f'{KML}:Not_PreBool', 800, 352)
    both = g.call(f'{KML}:BooleanAND', 1024, 224)
    br = g.branch(1280, 0); la = g.call(me('LearnFlag'), 1536, 0)
    nl = g.get('NotebookLines', 1536, 224, class_path=GI_C); fd = g.call(f'{MAP}:Map_Find', 1792, 224)
    st = g.set('LastLearned', 2048, 0)
    g.link(gi, 'GI', kn, 'self'); g.link(lr, 'Learns', kn, 'Flag'); g.link(kn, 'Known', nk, 'A')
    g.link(lf, 'bLearnOnFail', both, 'A'); g.link(nk, 'ReturnValue', both, 'B'); g.link(both, 'ReturnValue', br, 'Condition')
    g.link(lr, 'Learns', la, 'Flag'); g.link(gi, 'GI', nl, 'self'); g.link(nl, 'NotebookLines', fd, 'TargetMap')
    g.link(lr, 'Learns', fd, 'Key'); g.link(fd, 'Value', st, 'LastLearned')
    bok = g.call(f'{KSL}:IsValid', 512, 160); bv = g.branch(512, 0)  # no beat (a fail at the title): nothing to learn
    g.link(b, 'Beat', bok, 'Object'); g.link(bok, 'ReturnValue', bv, 'Condition')
    g.exec_chain(e, clr, bv); g.link(bv, 'True', br, 'execute'); g.link(br, 'True', la, 'execute'); g.exec_chain(la, st)
    g.comment('Learn from failure', 'A failed T7 or T8 still teaches its flag, so the next morning is shorter',
              [e, clr, b, bok, bv, lf, lr, gi, kn, nk, both, br, la, nl, fd, st], C_DATA)

    # ---- FindBeatFrom(Event, From) -> Index: recursive search forward from a beat (no loop macro)
    g, e = open_fn('FindBeatFrom')
    beats = g.get('Beats', 32, 224)
    last = g.call(f'{ARR}:Array_LastIndex', 256, 224)
    past = g.call(f'{KML}:Greater_IntInt', 544, 192)
    b1 = g.branch(800, 0)
    miss = g.at(g.ed.add_return_node(), 1088, -192); g.default(miss, 'Index', -1)
    bt = arr_get(g, 832, 320, beats, 'Beats', e, 'From')
    adv = g.get('AdvanceOn', 1056, 384, class_path=PDA_C); con(item(bt), g.pin(adv, 'self'))
    has = g.call(f'{ARR}:Array_Contains', 1312, 288)
    b2 = g.branch(1376, 0)
    hit = g.at(result_node(g), 1664, -192)
    nx = g.call(f'{KML}:Add_IntInt', 1408, 448, B=1)
    rec = g.call(me('FindBeatFrom'), 1664, 0)
    ret = g.at(g.ed.add_return_node(), 2016, 0)
    g.link(beats, 'Beats', last, 'TargetArray'); g.link(e, 'From', past, 'A'); g.link(last, 'ReturnValue', past, 'B')
    g.link(past, 'ReturnValue', b1, 'Condition'); g.link(adv, 'AdvanceOn', has, 'TargetArray'); g.link(e, 'Event', has, 'ItemToFind')
    g.link(has, 'ReturnValue', b2, 'Condition'); g.link(e, 'From', hit, 'Index'); g.link(e, 'From', nx, 'A')
    g.link(e, 'Event', rec, 'Event'); g.link(nx, 'ReturnValue', rec, 'From'); g.link(rec, 'Index', ret, 'Index')
    g.exec_chain(e, b1); g.link(b1, 'True', miss, 'execute'); g.link(b1, 'False', b2, 'execute')
    g.link(b2, 'True', hit, 'execute'); g.link(b2, 'False', rec, 'execute'); g.exec_chain(rec, ret)
    g.comment('Find the completed beat', 'Beat From lists the event: that beat. Otherwise ask From + 1; past the '
              'last beat: -1. Searching forward lets a known shortcut skip beats',
              [e, beats, last, past, b1, miss, bt, adv, has, b2, hit, nx, rec, ret], C_FLOW)

    # ---- EnterBeat(Index)
    g, e = open_fn('EnterBeat')
    si = g.set('BeatIndex', 288, 0); beats = g.get('Beats', 288, 224)
    bt = arr_get(g, 512, 224, beats, 'Beats', e, 'Index')
    sb = g.set('Beat', 608, 0); con(item(bt), _find_pin(sb, 'Beat', False))
    tier = field_p(g, item(bt), 'Tier', 896, 224)
    st = g.call(me('ShowTier'), 928, 0)
    bc = dispatch(g, 'OnBeatChanged', 1248, 0)
    bid = field_p(g, item(bt), 'Id', 1056, 352); obj = field_p(g, item(bt), 'Objective', 1056, 432)
    ph = field_p(g, item(bt), 'bShowPhone', 1056, 512)
    hk = g.call(me('RunBeatHooks'), 1632, 0)
    g.link(e, 'Index', si, 'BeatIndex'); g.exec_chain(e, si, sb, st, bc, hk)
    g.link(tier, 'Tier', st, 'Tier'); g.link(bid, 'Id', bc, 'Beat'); g.link(obj, 'Objective', bc, 'Objective')
    g.link(ph, 'bShowPhone', bc, 'ShowPhone'); g.link(bid, 'Id', hk, 'Id')
    g.comment('Enter a beat', 'Current beat from Beats, dream tier, then OnBeatChanged for the HUD and phone, then its hook',
              [e, si, beats, bt, sb, tier, st, bc, bid, obj, ph, hk], C_FLOW)

    # ---- RunBeatHooks(Id): the few beats that start something
    g, e = open_fn('RunBeatHooks')
    sw = pnode(g, 288, 0, 'SwitchonName')
    cases = (('T1', 'StartWaking'), ('T2', 'HideNightmare'), ('T7', 'BeginWardrobeTransition'), ('T8', 'StartShirtFight'),
             ('T9', 'SuitUp'), ('T10', 'OpenTheDoor'))
    sw.set_editor_property('pin_names', [unreal.Name(c) for c, _ in cases])
    g.link(e, 'Id', sw, 'Selection'); g.exec_chain(e, sw)
    hooks = []
    for i, (case, func) in enumerate(cases):
        hooks.append(g.call(me(func), 640, i * 128))
        g.link(sw, case, hooks[-1], 'execute')
    g.comment('Beat hooks', 'T1 wakes (first steps, the Nightmare in the corner), T2 it is gone, T7 top-down, T8 the shirt '
              'fight, T9 the suit, T10 the door opens', [e, sw] + hooks, C_FLOW)

    # ---- Hook bodies
    g, e = open_fn('StartWaking')
    tm = g.call(f'{KSL}:K2_SetTimer', 256, 0, FunctionName='CheckFirstSteps', Time=0.2, bLooping='true')
    sp = g.get('NightmareT1', 448, 288); sn = g.call(me('ShowNightmare'), 704, 0)
    g.link(sp, 'NightmareT1', sn, 'Spot'); g.exec_chain(e, tm, sn)
    g.comment('T1 waking', 'Watch for first steps; the Nightmare is glimpsed in the corner by the wardrobe until they come',
              [e, tm, sp, sn], C_FLOW)
    g, e = open_fn('StartShirtFight')
    # The shirt can be taken during T7's top-down hold: leave top-down first, or its ExitTopDown timer would later
    # pull the view off the battle camera and hide the T8 Nightmare (ExitTopDown is guarded by bTopDown, so it no-ops then)
    active = g.get('bWardrobeTransition', 32, -224); transition = g.branch(256, -416)
    stage = g.call(me('StageWrongWall'), 544, -416)
    reform = g.call(me('WardrobeReappear'), 832, -416)
    finish = g.call(me('FinishWardrobeTransition'), 1120, -416)
    ex = g.call(me('ExitTopDown'), 256, 0); xc = g.call(me('ExitTopDownCut'), 384, 160)  # finish its cut now, not 0.2 s later
    se = g.call(me('StartShirtEncounter'), 512, 0)
    sp = g.get('NightmareT8', 576, 160); sn = g.call(me('ShowNightmare'), 832, 0)
    g.link(active, 'bWardrobeTransition', transition, 'Condition'); g.exec_chain(e, transition)
    g.link(transition, 'True', stage, 'execute'); g.exec_chain(stage, reform, finish, ex, xc, se, sn)
    g.link(transition, 'False', ex, 'execute'); g.link(sp, 'NightmareT8', sn, 'Spot')
    g.comment('T8 the shirt fights back', 'Start the encounter; the Nightmare watches from the bay alcove, it never fights',
              [e, active, transition, stage, reform, finish, ex, xc, se, sp, sn], C_FLOW)
    g, e = open_fn('SuitUp')
    ct = g.call(f'{KSL}:K2_ClearTimer', 256, 0, FunctionName='FailDay')
    sh = g.call(me('PayoffShot'), 420, -200)
    eq = g.call(me('EquipSuit'), 576, 0); hn = g.call(me('HideNightmare'), 864, 0)
    lb = g.call(me('PayoffLook'), 1152, 0, On='true')
    tm = g.call(f'{KSL}:K2_SetTimer', 1440, 0, FunctionName='PayoffShotOut', Time=2.5, bLooping='false')
    g.exec_chain(e, ct, sh, eq, hn, lb, tm)
    g.comment('T9 the suit lands', 'The alarm stops; cut to the hero shot (PayoffCam); the suit goes on, the Nightmare '
              'dissolves, letterbox and full colour; back to first person in 2.5 s', [e, ct, sh, eq, hn, lb, tm], C_FLOW)
    # PayoffShot (the level's CineCameraActor tagged PayoffCam, placed by place_payoff_cam.py, moved from the pawn's
    # transform, cut to, PlayerCinematic after the cut so the face shows): its body is built by
    # Tools/Unreal/flow/patch_payoff_shot.py (Hayba, idempotent). Run it after a rebuild.
    g, e = open_fn('PayoffShotOut')
    cm = g.call(f'{GS}:GetPlayerCameraManager', 256, 224, PlayerIndex=0)
    dn = g.call('/Script/Engine.PlayerCameraManager:StartCameraFade', 256, 0, FromAlpha=0.0, ToAlpha=1.0, Duration=0.2,
                Color=BLACK, bHoldWhenFinished='true')
    tc = g.call(f'{KSL}:K2_SetTimer', 608, 0, FunctionName='PayoffShotCut', Time=0.2, bLooping='false')
    g.link(cm, 'ReturnValue', dn, 'self'); g.exec_chain(e, dn, tc)
    g.comment('Dip out of the hero shot', '', [e, cm, dn, tc], C_CAM)
    g, e = open_fn('PayoffShotCut')
    pc = g.call(f'{GS}:GetPlayerController', 256, 224, PlayerIndex=0)
    pw = g.call(f'{GS}:GetPlayerPawn', 256, 352, PlayerIndex=0)
    vt = g.call(f'{PC_}:SetViewTargetWithBlend', 544, 0, BlendTime=0.0)
    ci = g.call(me('PlayerCinematic'), 832, 0, Enable='false')
    mv = g.call(f'{CTRL}:SetIgnoreMoveInput', 1120, 0, bNewMoveInput='false')
    lk = g.call(f'{CTRL}:SetIgnoreLookInput', 1408, 0, bNewLookInput='false')
    pd = g.call(f'{KSL}:K2_SetTimer', 1696, 0, FunctionName='PayoffDone', Time=0.5, bLooping='false')  # after the fade-up: T10's phone blends from first person
    g.link(pc, 'ReturnValue', vt, 'self'); g.link(pw, 'ReturnValue', vt, 'NewViewTarget')
    g.link(pc, 'ReturnValue', mv, 'self'); g.link(pc, 'ReturnValue', lk, 'self')
    g.exec_chain(e, vt, ci, mv, lk, pd)
    nodes = [e, pc, pw, vt, ci, mv, lk, pd]
    ca = g.cast(cls_path(PLAYER), 1984, 0) if hasattr(g, 'cast') else None
    if ca:
        up = g.call(f'{cls_path(PLAYER)}:HandoffFadeUp', 2272, -96)
        g.link(pw, 'ReturnValue', ca, 'Object'); g.exec_chain(pd, ca); g.link(ca, 'then', up, 'execute')
        nodes += [ca, up]
    g.comment('Back to first person under black', 'Then, 0.5 s later, PayoffDone: colour drains, letterbox out, PayoffEnded', nodes, C_CAM)
    g, e = open_fn('PayoffDone')
    lb = g.call(me('PayoffLook'), 256, 0, On='false')
    rp = g.call(me('ReportEvent'), 544, 0, Event='PayoffEnded')
    g.exec_chain(e, lb, rp)
    g.comment('Payoff ends', 'Colour drains, letterbox out, PayoffEnded moves T9 on to T10 (unconditional)', [e, lb, rp], C_FLOW)
    # PayoffLook(On): pp's payoff timings. In: letterbox 0.8 s, colour to 1 over 1.5 s. Out: colour to 0 over 2 s, letterbox 1 s
    g, e = open_fn('PayoffLook')
    if HAS_LETTERBOX or HAS_REVEAL:
        find, ok, br = actor_check(g, DREAM)
        nodes, prev, x = [e, find, ok, br], None, 1088
        for func, has, vals in (('SetLetterbox', HAS_LETTERBOX, ('On', (0.8, 1.0))),
                                ('SetColorReveal', HAS_REVEAL, ((1.0, 0.0), (1.5, 2.0)))):
            if not has:
                continue
            call = g.call(f'{cls_path(DREAM)}:{func}', x, 0)
            ins = [p for p in BEL.list_input_pins(call) if str(PIN.get_pin_name(p)) not in ('execute', 'self')]
            for k, (pin, v) in enumerate(zip(ins, vals)):
                if v == 'On':
                    con(_find_pin(e, 'On', True), pin)
                else:  # (value when On, value when off) through one Select
                    sel = g.call(f'{KML}:SelectFloat', x - 64, 224 + 128 * k, A=v[0], B=v[1])
                    g.link(e, 'On', sel, 'bPickA'); con(_find_pin(sel, 'ReturnValue', True), pin); nodes.append(sel)
            g.link(find, 'ReturnValue', call, 'self')
            if prev is None:
                g.link(br, 'True', call, 'execute')
            else:
                g.exec_chain(prev, call)
            nodes.append(call); prev, x = call, x + 384
        g.comment('Payoff look', 'BP_DreamDirector letterbox and colour reveal in or out (skipped if absent)', nodes, C_VISUAL)
    else:
        pending(g, e, 'PostProcess/BP_DreamDirector.SetLetterbox', 'pp')

    # ---- CompleteBeat(Index): learn, tick, enter the next beat
    g, e = open_fn('CompleteBeat')
    beats = g.get('Beats', 0, 192)
    bt = arr_get(g, 192, 192, beats, 'Beats', e, 'Index')
    lr = g.get('Learns', 448, 256, class_path=PDA_C); con(item(bt), g.pin(lr, 'self'))
    tk = g.get('TickTask', 640, 352, class_path=PDA_C); con(item(bt), g.pin(tk, 'self'))
    la = g.call(me('LearnFlag'), 608, 0)
    ge = g.call(f'{KML}:GreaterEqual_IntInt', 896, 224, B=0)
    b1 = g.branch(1120, 0)
    tt = g.call(me('TickTask'), 1376, 0)
    nx = g.call(f'{KML}:Add_IntInt', 1408, 224, B=1); ln = g.call(f'{ARR}:Array_Length', 1408, 480)
    lt = g.call(f'{KML}:Less_IntInt', 1696, 288)
    b2 = g.branch(1728, 0)
    eb = g.call(me('EnterBeat'), 1984, 0)
    el = g.call(me('EndLevel'), 1984, 160)
    g.link(lr, 'Learns', la, 'Flag'); g.link(tk, 'TickTask', ge, 'A'); g.link(ge, 'ReturnValue', b1, 'Condition')
    g.link(tk, 'TickTask', tt, 'Task'); g.link(e, 'Index', nx, 'A'); g.link(beats, 'Beats', ln, 'TargetArray')
    g.link(nx, 'ReturnValue', lt, 'A'); g.link(ln, 'ReturnValue', lt, 'B'); g.link(lt, 'ReturnValue', b2, 'Condition')
    g.link(nx, 'ReturnValue', eb, 'Index')
    g.exec_chain(e, la, b1); g.link(b1, 'True', tt, 'execute'); g.link(b1, 'False', b2, 'execute'); g.exec_chain(tt, b2)
    g.link(b2, 'True', eb, 'execute'); g.link(b2, 'False', el, 'execute')
    g.comment('Complete a beat', 'Its flag is learned, its phone task ticked, then the next beat starts; after T10 the level '
              'ends', [e, beats, bt, lr, tk, la, ge, b1, tt, nx, ln, lt, b2, eb, el], C_FLOW)

    # ---- ReportEvent(Event): the one entry point for interactables, the phone and the encounter
    g, e = open_fn('ReportEvent')
    falling = g.call(f'{KML}:EqualEqual_NameName', 32, -352, B='WardrobeFalling')
    fs = g.branch(288, -192); begin = g.call(me('BeginWardrobeTransition'), 576, -192)
    g.link(e, 'Event', falling, 'A'); g.link(falling, 'ReturnValue', fs, 'Condition')
    ro = g.get('bRollingOver', 64, 192)
    b1 = g.branch(288, 0)
    bi = g.get('BeatIndex', 320, 224); mx = g.call(f'{KML}:Max', 544, 224, B=0)
    fb = g.call(me('FindBeatFrom'), 832, 0)
    ge = g.call(f'{KML}:GreaterEqual_IntInt', 1120, 224, B=0)
    b2 = g.branch(1376, 0)
    cb = g.call(me('CompleteBeat'), 1632, 0)
    g.link(ro, 'bRollingOver', b1, 'Condition'); g.link(e, 'Event', fb, 'Event'); g.link(bi, 'BeatIndex', mx, 'A')
    g.link(mx, 'ReturnValue', fb, 'From'); g.link(fb, 'Index', ge, 'A')
    g.link(ge, 'ReturnValue', b2, 'Condition'); g.link(fb, 'Index', cb, 'Index')
    if can_call(DIR, 'HandleClothingSearch'):
        search = g.call(me('HandleClothingSearch'), -256, -640)
        g.link(e, 'Event', search, 'Event'); g.exec_chain(e, search)
        e = search
    if can_call(DIR, 'CanReportClothingEvent'):
        allowed = g.call(me('CanReportClothingEvent'), -256, -384)
        g.link(entry_node(g), 'Event', allowed, 'Event')
        gate = g.branch(-256, 0); g.link(allowed, 'Allowed', gate, 'Condition')
        g.exec_chain(e, gate); e = gate
    g.exec_chain(e, b1); g.link(b1, 'False', fs, 'execute'); g.link(fs, 'True', begin, 'execute')
    g.link(fs, 'False', fb, 'execute'); g.exec_chain(fb, b2); g.link(b2, 'True', cb, 'execute')
    g.comment('Report an event', 'Ignored during a rollover; otherwise completes the beat it belongs to, searching from the '
              'current beat (contract.md lists the events)', [e, falling, fs, begin, ro, b1, bi, mx, fb, ge, b2, cb], C_EVENT)

    # ---- BeginMorning: the main menu's Wake Up, and every new day; the wake-up cinematic plays first
    g, e = open_fn('BeginMorning')
    if can_call(DIR, 'CancelClothingInspection'):
        cancel_inspection = g.call(me('CancelClothingInspection'), -320, 0)
        g.exec_chain(e, cancel_inspection); e = cancel_inspection
    pw = g.call(me('PlayWakeUp'), 288, 0)
    if can_call(DIR, 'ResetMorningInventory'):
        reset_inventory = g.call(me('ResetMorningInventory'), 0, -320)
        g.exec_chain(e, reset_inventory, pw)
    else:
        g.exec_chain(e, pw)
    g.comment('Begin the morning', 'The wake-up cinematic (event graph) ends in StartMorningBeats: T0 and the phone',
              [e, pw], C_FLOW)

    # ---- StartMorningBeats: the film completed waking. The room first (the fade-up, then free look), 2.7 s later the phone
    # buzzes (OpenMorningPhone), 0.5 s later T0 starts and the phone rises on the list (RaiseMorningPhone; T0 is entered
    # late because ShowPhone opens the phone at once). T0 completes on its Wake up (PhoneWakeUp). Then the optional alarm.
    g, e = open_fn('StartMorningBeats')
    # The player's BPC_Interactor broadcasts OnBeatEvent; bound here each morning, not at BeginPlay (the pawn's component
    # was not there yet: Accessed None). Bind Event adds unique, so a rebind is a no-op. A dispatcher: no load cycle.
    eb = g.call(f'{KSL}:K2_SetTimer', 960, 0, FunctionName='OpenMorningPhone', Time=2.7, bLooping='false')  # fade-up, then the room
    nodes = [e, eb]
    if exists(INTERACTOR):
        pw = g.call(f'{GS}:GetPlayerPawn', 32, 352, PlayerIndex=0)
        gc = g.call(f'{ACTOR}:GetComponentByClass', 288, 352, ComponentClass=cls_path(INTERACTOR))
        ok = g.call(f'{KSL}:IsValid', 576, 352); bi = g.branch(288, 0)
        g.link(pw, 'ReturnValue', gc, 'self'); g.link(gc, 'ReturnValue', ok, 'Object'); g.link(ok, 'ReturnValue', bi, 'Condition')
        bind, mk = bind_function(g, gc, 'ReturnValue', 'OnBeatEvent', 'ReportEvent', 576, 0)
        g.exec_chain(e, bi); g.link(bi, 'True', bind, 'execute'); g.exec_chain(bind, eb); g.link(bi, 'False', eb, 'execute')
        nodes += [pw, gc, ok, bi, bind, mk]
    else:
        g.exec_chain(e, eb)
    al = g.get('bAlarmClockFail', 1024, 192)
    br = g.branch(1280, 0)
    secs = g.get('AlarmClockSeconds', 1280, 256)
    tm = g.call(f'{KSL}:K2_SetTimer', 1568, 0, FunctionName='FailDay')
    g.link(al, 'bAlarmClockFail', br, 'Condition'); g.link(secs, 'AlarmClockSeconds', tm, 'Time')
    g.exec_chain(eb, br); g.link(br, 'True', tm, 'execute')
    g.comment('The morning starts', '', nodes + [al, br, secs, tm], C_FLOW)

    # ---- OpenMorningPhone: the phone buzzes on the nightstand; RaiseMorningPhone 0.5 s later. Only before any beat.
    g, e = open_fn('OpenMorningPhone')
    bx = g.get('BeatIndex', 0, 224); early = g.call(f'{KML}:Less_IntInt', 224, 224, B=0); b0 = g.branch(480, 0)
    ph = g.call(f'{GS}:GetActorOfClass', 736, 0, ActorClass='/Game/FoA/UI/Game/BP_Phone.BP_Phone_C')
    ok = g.call(f'{KSL}:IsValid', 992, 224); hv = g.branch(1248, 0); loc = g.call(f'{ACTOR}:K2_GetActorLocation', 1248, 288)
    bz = g.call(f'{GS}:PlaySoundAtLocation', 1504, -96, Sound='/Game/FoA/Audio/MetaSounds/Phone/S_Phone_NightstandBuzz.S_Phone_NightstandBuzz')
    rt = g.call(f'{KSL}:K2_SetTimer', 1824, 0, FunctionName='RaiseMorningPhone', Time=0.5, bLooping='false')
    g.link(bx, 'BeatIndex', early, 'A'); g.link(early, 'ReturnValue', b0, 'Condition'); g.exec_chain(e, b0); g.link(b0, 'True', ph, 'execute')
    g.link(ph, 'ReturnValue', ok, 'Object'); g.link(ok, 'ReturnValue', hv, 'Condition'); g.exec_chain(ph, hv)
    g.link(ph, 'ReturnValue', loc, 'self'); g.link(loc, 'ReturnValue', bz, 'Location'); g.link(hv, 'True', bz, 'execute')
    g.exec_chain(bz, rt); g.link(hv, 'False', rt, 'execute')
    g.comment('The phone buzzes on the nightstand', '', [e, bx, early, b0, ph, ok, hv, loc, bz, rt], C_FLOW)

    # ---- RaiseMorningPhone: T0 starts (ShowPhone raises the phone on the list); no front end: T0 finishes by itself
    g, e = open_fn('RaiseMorningPhone')
    bx = g.get('BeatIndex', 0, 224); early = g.call(f'{KML}:Less_IntInt', 224, 224, B=0); b0 = g.branch(480, 0)
    en = g.call(me('EnterBeat'), 736, 0, Index=0)
    fe = g.call(f'{GS}:GetActorOfClass', 992, 0, ActorClass=cls_path(FRONT)); ok = g.call(f'{KSL}:IsValid', 1248, 224)
    hv = g.branch(1504, 0); op = g.call(f'{cls_path(FRONT)}:OpenPhone', 1760, -128); cb = g.call(me('CompleteBeat'), 1760, 128, Index=0)
    g.link(bx, 'BeatIndex', early, 'A'); g.link(early, 'ReturnValue', b0, 'Condition'); g.exec_chain(e, b0); g.link(b0, 'True', en, 'execute')
    g.exec_chain(en, fe); g.link(fe, 'ReturnValue', ok, 'Object'); g.link(ok, 'ReturnValue', hv, 'Condition'); g.exec_chain(fe, hv)
    g.link(fe, 'ReturnValue', op, 'self'); g.link(hv, 'True', op, 'execute'); g.link(hv, 'False', cb, 'execute')
    g.comment('T0: the phone rises on the list', '', [e, bx, early, b0, en, fe, ok, hv, op, cb], C_FLOW)

    # ---- CheckFirstSteps: looping 0.2 s timer during T1 (no Tick)
    g, e = open_fn('CheckFirstSteps')
    pw = g.call(f'{GS}:GetPlayerPawn', 0, 192, PlayerIndex=0)
    vel = g.call(f'{ACTOR}:GetVelocity', 256, 192); vs = g.call(f'{KML}:VSize', 480, 192)
    gt = g.call(f'{KML}:Greater_DoubleDouble', 672, 192, B=30.0)
    br = g.branch(928, 0)
    ct = g.call(f'{KSL}:K2_ClearTimer', 1184, 0, FunctionName='CheckFirstSteps')
    rp = g.call(me('ReportEvent'), 1504, 0, Event='FirstSteps')
    g.link(pw, 'ReturnValue', vel, 'self'); g.link(vel, 'ReturnValue', vs, 'A'); g.link(vs, 'ReturnValue', gt, 'A')
    g.link(gt, 'ReturnValue', br, 'Condition'); g.exec_chain(e, br); g.link(br, 'True', ct, 'execute'); g.exec_chain(ct, rp)
    g.comment('First steps', 'T1 ends once the Nightmare walks faster than 30 cm/s', [e, pw, vel, vs, gt, br, ct, rp], C_FLOW)

    # ---- EnterTopDown: blend to the room-wide camera, stick-up = screen-up
    g, e = open_fn('EnterTopDown')
    on = g.set('bTopDown', 256, 0); g.default(on, 'bTopDown', 'true')
    pc = g.call(f'{GS}:GetPlayerController', 352, 224, PlayerIndex=0)
    me_ = pnode(g, 352, 352, 'referencetoself'); bl = g.get('TopDownBlend', 352, 432)
    vt = g.call(f'{PC_}:SetViewTargetWithBlend', 640, 0, BlendFunc='VTBlend_EaseInOut', BlendExp=2.0)
    active = g.get('bWardrobeTransition', 32, 576)
    entry_blend = g.call(f'{KML}:SelectFloat', 352, 576, A=0.35)
    ig = g.call(f'{CTRL}:SetIgnoreLookInput', 1024, 0, bNewLookInput='true')
    cam = g.get('TopDownCamera', 1024, 224)
    rot = g.call(f'{SC}:K2_GetComponentRotation', 1248, 224)
    brk = g.call(f'{KML}:BreakRotator', 1536, 224)
    mk = g.call(f'{KML}:MakeRotator', 1792, 224)
    cr = g.call(f'{CTRL}:SetControlRotation', 2048, 0)
    tm = g.call(f'{KSL}:K2_SetTimer', 2400, 0, FunctionName='StageWrongWall'); bl2 = g.get('TopDownBlend', 2144, 288)
    hc = g.call(me('SetCeilingHidden'), 2720, 0, Hidden='true')
    g.link(pc, 'ReturnValue', vt, 'self'); g.link(me_, 'self', vt, 'NewViewTarget')
    g.link(active, 'bWardrobeTransition', entry_blend, 'bPickA'); g.link(bl, 'TopDownBlend', entry_blend, 'B')
    g.link(entry_blend, 'ReturnValue', vt, 'BlendTime')
    g.link(pc, 'ReturnValue', ig, 'self'); g.link(pc, 'ReturnValue', cr, 'self'); g.link(cam, 'TopDownCamera', rot, 'self')
    g.link(rot, 'ReturnValue', brk, 'InRot'); g.link(brk, 'Yaw', mk, 'Yaw'); g.link(mk, 'ReturnValue', cr, 'NewRotation')
    stage_delay = g.call(f'{KML}:SelectFloat', 2144, 576, A=5.0)
    g.link(active, 'bWardrobeTransition', stage_delay, 'bPickA'); g.link(bl2, 'TopDownBlend', stage_delay, 'B')
    g.link(stage_delay, 'ReturnValue', tm, 'Time')
    g.exec_chain(e, on, vt, ig, cr, tm, hc)
    g.comment('Top-down camera in', 'Blend to TopDownCamera; look input off and control yaw = camera yaw so stick-up is '
              'screen-up; stage the room once the blend lands; the ceiling hides',
              [e, on, pc, me_, bl, active, entry_blend, vt, ig, cam, rot, brk, mk, cr, tm, bl2, hc], C_CAM)

    # ---- StageWrongWall: while top-down, the door moves and the drawer fills again
    g, e = open_fn('StageWrongWall')
    td = g.get('bTopDown', 32, 192)
    br = g.branch(288, 0)
    md = g.call(me('MoveDoor'), 544, 0); rf = g.call(me('RefillDrawer'), 864, 0)
    rs = g.call(me('StartClothingSearch') if can_call(DIR, 'StartClothingSearch') else me('RevealShirt'), 1152, -128)
    pt = g.call(me('PlayerTopDown'), 1152, 0, Enable='true')
    sp = g.get('NightmareT7', 1216, 160); sn = g.call(me('ShowNightmare'), 1472, 0)
    gi, hk = gi_call(g, 'HasKnowledge', 1568, 352, 1312, 352, Flag='Knows.DoorMoves')
    hn = g.get('TopDownHoldKnown', 1568, 512); hl = g.get('TopDownHold', 1568, 592)
    sel = g.call(f'{KML}:SelectFloat', 1856, 352)
    tm = g.call(f'{KSL}:K2_SetTimer', 2112, 0, FunctionName='ExitTopDown')
    g.link(td, 'bTopDown', br, 'Condition'); g.link(hn, 'TopDownHoldKnown', sel, 'A'); g.link(hl, 'TopDownHold', sel, 'B')
    g.link(hk, 'Known', sel, 'bPickA'); g.link(sel, 'ReturnValue', tm, 'Time'); g.link(sp, 'NightmareT7', sn, 'Spot')
    g.exec_chain(e, br); g.link(br, 'True', md, 'execute'); g.exec_chain(md, rf, rs, pt, sn, tm)
    g.comment('Wrong wall (T7)', 'Only while top-down: move the door, refill the drawer, hold the view (shorter once '
              'Knows.DoorMoves); the Nightmare stands where the door was',
              [e, td, br, md, rf, rs, pt, sp, sn, gi, hk, hn, hl, sel, tm], C_CAM)

    # ---- MoveDoor: the frame lands on MovedDoorSpot, the door keeps its offset from the frame
    g, e = open_fn('MoveDoor')
    gi, hk = gi_call(g, 'HasKnowledge', 448, 192, 192, 192, Flag='Knows.DoorMoves')
    lt = g.get('UnderDoorLight', 480, 352)
    vis = g.call(f'{SC}:SetVisibility', 768, 0)
    spot = g.get('MovedDoorSpot', 768, 288); sw = g.call(f'{SC}:K2_GetComponentToWorld', 992, 288)
    fr = g.get('DoorFrame', 1088, 448)
    mf = g.call(f'{ACTOR}:K2_SetActorTransform', 1344, 0, bTeleport='true')
    dh = g.get('DoorHome', 1344, 448); fh = g.get('FrameHome', 1344, 528)
    rel = g.call(f'{KML}:MakeRelativeTransform', 1600, 448)
    comp = g.call(f'{KML}:ComposeTransforms', 1888, 384)
    dr = g.get('Door', 1920, 544)
    md = g.call(f'{ACTOR}:K2_SetActorTransform', 2176, 0, bTeleport='true')
    g.link(lt, 'UnderDoorLight', vis, 'self'); g.link(hk, 'Known', vis, 'bNewVisibility')
    g.link(spot, 'MovedDoorSpot', sw, 'self'); g.link(fr, 'DoorFrame', mf, 'self'); g.link(sw, 'ReturnValue', mf, 'NewTransform')
    g.link(dh, 'DoorHome', rel, 'A'); g.link(fh, 'FrameHome', rel, 'RelativeTo'); g.link(rel, 'ReturnValue', comp, 'A')
    g.link(sw, 'ReturnValue', comp, 'B'); g.link(dr, 'Door', md, 'self'); g.link(comp, 'ReturnValue', md, 'NewTransform')
    show = g.call(me('SetDoorHidden'), 2528, 0, Hidden='false')
    wall = g.call(me('SetOldWall'), 2848, 0, Enable='true')
    g.exec_chain(e, vis, mf, md, show, wall)
    g.comment('Move the door', 'Lit from under once the player knows it moves; the frame lands on MovedDoorSpot and the '
              'door keeps its place in the frame', [e, gi, hk, lt, vis, spot, sw, fr, mf, dh, fh, rel, comp, dr, md, show], C_CAM)

    # ---- RestoreDoor
    g, e = open_fn('RestoreDoor')
    lt = g.get('UnderDoorLight', 256, 192)
    vis = g.call(f'{SC}:SetVisibility', 448, 0, bNewVisibility='false')
    fr = g.get('DoorFrame', 704, 224); fh = g.get('FrameHome', 704, 304)
    mf = g.call(f'{ACTOR}:K2_SetActorTransform', 960, 0, bTeleport='true')
    dr = g.get('Door', 1216, 224); dh = g.get('DoorHome', 1216, 304)
    md = g.call(f'{ACTOR}:K2_SetActorTransform', 1472, 0, bTeleport='true')
    g.link(lt, 'UnderDoorLight', vis, 'self'); g.link(fr, 'DoorFrame', mf, 'self'); g.link(fh, 'FrameHome', mf, 'NewTransform')
    wall = g.call(me('SetOldWall'), 1792, 0, Enable='false')
    g.link(dr, 'Door', md, 'self'); g.link(dh, 'DoorHome', md, 'NewTransform'); g.exec_chain(e, vis, mf, md, wall)
    g.comment('Put the door back', 'New day: the light goes out; frame and door return to where BeginPlay found them',
              [e, lt, vis, fr, fh, mf, dr, dh, md], C_CAM)

    # ---- ExitTopDown: fade down 0.2 s (held), then ExitTopDownCut cuts under black. A camera blend swept from above into
    # the head and showed the player's own body for about a second (QA bug 4b, 2026-11-09).
    g, e = open_fn('ExitTopDown')
    td = g.get('bTopDown', 32, 192)
    br = g.branch(288, 0)
    off = g.set('bTopDown', 544, 0)
    cm = g.call(f'{GS}:GetPlayerCameraManager', 832, 224, PlayerIndex=0)
    dn = g.call('/Script/Engine.PlayerCameraManager:StartCameraFade', 832, 0, FromAlpha=0.0, ToAlpha=1.0, Duration=0.2,
                Color=BLACK, bHoldWhenFinished='true')
    tc = g.call(f'{KSL}:K2_SetTimer', 1184, 0, FunctionName='ExitTopDownCut', Time=0.2, bLooping='false')
    pn = g.set('bTopDownCutPending', 688, -160); g.default(pn, 'bTopDownCutPending', 'true')
    g.link(td, 'bTopDown', br, 'Condition'); g.exec_chain(e, br); g.link(br, 'True', off, 'execute')
    g.link(cm, 'ReturnValue', dn, 'self'); g.exec_chain(off, pn, dn, tc)
    g.comment('Top-down camera out', 'Fade, then cut (only if top-down); callers that move on at once call '
              'ExitTopDownCut themselves', [e, td, br, off, pn, cm, dn, tc], C_CAM)

    # Layered by idempotent Hayba patches, re-run after a rebuild (2026-11-10): patch_camera_cuts.py
    # (SetGameCameraCutThisFrame at every story cut), patch_chase_cutaway.py (SetStoryHUDHidden, the cutaway dip),
    # patch_t7_hanger_drop.py (DropCoatRailHanger in StageWrongWall, its restore in ResetHouse), patch_hanger_line.py
    # (SayHangerFell after ExitTopDownCut), patch_hanger_glance.py (the view glances at the dropped hanger with that line).
    # ---- ExitTopDownCut: under black, the player camera back, look input back, the ceiling back, then the player's
    # own single-owner fade-up (BP_FoAPlayer.HandoffFadeUp); the Nightmare is gone
    g, e = open_fn('ExitTopDownCut')
    pt = g.call(me('PlayerTopDown'), 256, 0, Enable='false'); hn = g.call(me('HideNightmare'), 544, 0)
    pc = g.call(f'{GS}:GetPlayerController', 544, 224, PlayerIndex=0)
    pw = g.call(f'{GS}:GetPlayerPawn', 544, 352, PlayerIndex=0)
    vt = g.call(f'{PC_}:SetViewTargetWithBlend', 832, 0, BlendTime=0.0)
    ig = g.call(f'{CTRL}:SetIgnoreLookInput', 1120, 0, bNewLookInput='false')
    sc = g.call(me('ShowCeiling'), 1408, 0)
    ca = g.cast(cls_path(PLAYER), 1696, 0) if hasattr(g, 'cast') else None
    g.link(pc, 'ReturnValue', vt, 'self'); g.link(pw, 'ReturnValue', vt, 'NewViewTarget'); g.link(pc, 'ReturnValue', ig, 'self')
    gp = g.get('bTopDownCutPending', 32, -192); gb = g.branch(128, -96)
    gd = g.set('bTopDownCutPending', 192, -224); g.default(gd, 'bTopDownCutPending', 'false')
    g.link(gp, 'bTopDownCutPending', gb, 'Condition'); g.exec_chain(e, gb); g.link(gb, 'True', gd, 'execute')
    g.exec_chain(gd, pt, hn, vt, ig, sc)  # once per exit: the late timer no-ops after a caller finished the cut
    nodes = [e, gp, gb, gd, pt, hn, pc, pw, vt, ig, sc]
    if ca:
        up = g.call(f'{cls_path(PLAYER)}:HandoffFadeUp', 1984, -96)
        g.link(pw, 'ReturnValue', ca, 'Object'); g.exec_chain(sc, ca); g.link(ca, 'then', up, 'execute')
        nodes += [ca, up]
    g.comment('Cut back under black', '', nodes, C_CAM)

    # ---- CheckWalkedOut: looping 0.2 s timer during T10. Frame-local +X is the hallway side; after T7 the frame stands
    # 10 cm proud of the solid west wall, so "out" means stepping into the doorway (local X > -60, |Y| < 55), not past it.
    g, e = open_fn('CheckWalkedOut')
    pw = g.call(f'{GS}:GetPlayerPawn', 0, 192, PlayerIndex=0)
    loc = g.call(f'{ACTOR}:K2_GetActorLocation', 224, 192)
    fr = g.get('DoorFrame', 224, 320); ft = g.call(f'{ACTOR}:GetTransform', 416, 320)
    inv = g.call(f'{KML}:InverseTransformLocation', 640, 192)
    brk = g.call(f'{KML}:BreakVector', 896, 192)
    near = g.call(f'{KML}:Greater_DoubleDouble', 1120, 128, B=-60.0)
    ay = g.call(f'{KML}:Abs', 1120, 320)
    mid = g.call(f'{KML}:Less_DoubleDouble', 1312, 320, B=55.0)
    both = g.call(f'{KML}:BooleanAND', 1536, 192)
    br = g.branch(1760, 0)
    ct = g.call(f'{KSL}:K2_ClearTimer', 2016, 0, FunctionName='CheckWalkedOut')
    rp = g.call(me('ReportEvent'), 2336, 0, Event='WalkedOut')
    g.link(pw, 'ReturnValue', loc, 'self'); g.link(fr, 'DoorFrame', ft, 'self'); g.link(ft, 'ReturnValue', inv, 'T')
    g.link(loc, 'ReturnValue', inv, 'Location'); g.link(inv, 'ReturnValue', brk, 'InVec')
    g.link(brk, 'X', near, 'A'); g.link(brk, 'Y', ay, 'A'); g.link(ay, 'ReturnValue', mid, 'A')
    g.link(near, 'ReturnValue', both, 'A'); g.link(mid, 'ReturnValue', both, 'B'); g.link(both, 'ReturnValue', br, 'Condition')
    g.exec_chain(e, br); g.link(br, 'True', ct, 'execute'); g.exec_chain(ct, rp)
    g.comment('Walked out', 'T10 ends when the player steps into the open doorway, wherever the frame now stands',
              [e, pw, loc, fr, ft, inv, brk, near, ay, mid, both, br, ct, rp], C_FLOW)

    # ---- SetCeilingHidden(Hidden) / ShowCeiling: the Ceiling is in the way of the top-down view
    g, e = open_fn('SetCeilingHidden')
    cl = g.get('Ceiling', 256, 192)
    hid = g.call(f'{ACTOR}:SetActorHiddenInGame', 448, 0)
    g.link(cl, 'Ceiling', hid, 'self'); g.link(e, 'Hidden', hid, 'bNewHidden'); g.exec_chain(e, hid)
    g.comment('Ceiling for top-down', 'Hides or shows the Ceiling actor', [e, cl, hid], C_CAM)
    g, e = open_fn('ShowCeiling')
    sh = g.call(me('SetCeilingHidden'), 288, 0, Hidden='false')
    g.exec_chain(e, sh)
    g.comment('Ceiling back', 'Timer target after the blend out of top-down', [e, sh], C_CAM)

    # ---- RefillDrawer / OpenTheDoor (mech_core's BPI_Interactable)
    g, e = open_fn('RefillDrawer')
    if HAS_BPI:
        ra = g.get('RefillActor', 256, 192)
        rs = pnode(g, 448, 0, 'ResetForNewDay', 'Message')
        g.link(ra, 'RefillActor', rs, 'self'); g.exec_chain(e, rs)
        g.comment('Refill the drawer', 'T7, while top-down: what the player took (RefillActor, the screwdriver) is back in '
                  'its morning place', [e, ra, rs], C_CAM)
    else:
        pending(g, e, 'Gameplay/BPI_Interactable', 'mech_core')
    g, e = open_fn('OpenTheDoor')
    find = g.call(f'{GS}:GetActorOfClass', 256, 0, ActorClass=cls_path(THRESHOLD))
    ok = g.call(f'{KSL}:IsValid', 512, 192); br = g.branch(768, 0)
    sp = pnode(g, 1024, 160, 'SpawnActorfromClass')
    g.default(sp, 'Class', cls_path(THRESHOLD))
    tf = g.call(f'{KML}:MakeTransform', 768, 384)
    g.link(tf, 'ReturnValue', sp, 'SpawnTransform')
    g.link(find, 'ReturnValue', ok, 'Object'); g.link(ok, 'ReturnValue', br, 'Condition')
    g.exec_chain(e, find, br); g.link(br, 'False', sp, 'execute')
    g.comment('Prepare the dream threshold', 'The threshold watches for the player and owns the door timing.',
              [e, find, ok, br, tf, sp], C_FLOW)

    g, e = open_fn('RevealShirt')
    if HAS_BPI:
        sa = g.get('ShirtActor', 256, 192)
        op = pnode(g, 448, 0, 'Interact', 'Message')
        g.default(op, 'Verb', 'Notify'); g.default(op, 'HeldItem', 'Open')
        g.link(sa, 'ShirtActor', op, 'self'); g.exec_chain(e, op)
        g.comment('Reveal the shirt', 'T7: the hidden Shirt pickup appears (mech_core: Notify Open); taking it reports ShirtTaken',
                  [e, sa, op], C_CAM)
    else:
        pending(g, e, 'Gameplay/BPI_Interactable', 'mech_core')

    # ---- SweepInteractables / ResetFrom(Actors, I): every BPI_Interactable back to its morning state
    g, e = open_fn('SweepInteractables')
    if HAS_BPI:
        ga = g.call(f'{GS}:GetAllActorsWithInterface', 256, 0, Interface=cls_path(BPI))
        rf = g.call(me('ResetFrom'), 640, 0, I=0)
        g.link(ga, 'OutActors', rf, 'Actors'); g.exec_chain(e, ga, rf)
        g.comment('Morning state', 'ResetForNewDay on every BPI_Interactable in the level', [e, ga, rf], C_DAY)
    else:
        pending(g, e, 'Gameplay/BPI_Interactable', 'mech_core')
    g, e = open_fn('ResetFrom')
    if HAS_BPI:
        ln = g.call(f'{ARR}:Array_Length', 256, 192)
        lt = g.call(f'{KML}:Less_IntInt', 480, 160)
        br = g.branch(736, 0)
        it = arr_get(g, 768, 256, e, 'Actors', e, 'I')
        rs = pnode(g, 992, 0, 'ResetForNewDay', 'Message'); con(item(it), g.pin(rs, 'self'))
        nx = g.call(f'{KML}:Add_IntInt', 1056, 288, B=1)
        rec = g.call(me('ResetFrom'), 1344, 0)
        g.link(e, 'Actors', ln, 'TargetArray'); g.link(e, 'I', lt, 'A'); g.link(ln, 'ReturnValue', lt, 'B')
        g.link(lt, 'ReturnValue', br, 'Condition'); g.link(e, 'I', nx, 'A'); g.link(e, 'Actors', rec, 'Actors')
        g.link(nx, 'ReturnValue', rec, 'I')
        g.exec_chain(e, br); g.link(br, 'True', rs, 'execute'); g.exec_chain(rs, rec)
        g.comment('Reset from index I', 'Actor I resets, then I + 1 (recursion instead of a loop macro); stops past the end',
                  [e, ln, lt, br, it, rs, nx, rec], C_DAY)
    else:
        pending(g, e, 'Gameplay/BPI_Interactable', 'mech_core')

    # ---- ResetHouse: the house goes back to its morning state; knowledge stays (shared by rollover and title)
    g, e = open_fn('ResetHouse')
    if can_call(DIR, 'ResetClothingSearch'):
        search = g.call(me('ResetClothingSearch'), -256, -896)
        g.exec_chain(e, search)
        e = search
    if can_call(DIR, 'ResetStoryMoments'):
        story = g.call(me('ResetStoryMoments'), 128, -896)
        g.exec_chain(e, story)
        e = story
    reset = g.call(me('ResetWardrobeTransition'), 256, -192)
    enc_nodes = []
    if HAS_ENC and can_call(ENC, 'EndEncounter'):
        enc = g.call(f'{GS}:GetActorOfClass', 256, -640, ActorClass=cls_path(ENC))
        valid = g.call(f'{KSL}:IsValid', 544, -448); ev = g.branch(832, -640)
        active = g.get('bActive', 1088, -448, class_path=cls_path(ENC)); ea = g.branch(1376, -640)
        end = g.call(f'{cls_path(ENC)}:EndEncounter', 1664, -640)
        g.link(enc, 'ReturnValue', valid, 'Object'); g.link(valid, 'ReturnValue', ev, 'Condition')
        g.link(enc, 'ReturnValue', active, 'self'); g.link(active, 'bActive', ea, 'Condition')
        g.link(enc, 'ReturnValue', end, 'self'); g.exec_chain(e, enc, ev)
        g.link(ev, 'True', ea, 'execute'); g.link(ev, 'False', reset, 'execute')
        g.link(ea, 'True', end, 'execute'); g.link(ea, 'False', reset, 'execute'); g.exec_chain(end, reset)
        enc_nodes = [enc, valid, ev, active, ea, end]
    else:
        g.exec_chain(e, reset)
    ex = g.call(me('ExitTopDown'), 256, 0); xc = g.call(me('ExitTopDownCut'), 384, 160)
    c1 = g.call(f'{KSL}:K2_ClearTimer', 544, 0, FunctionName='CheckFirstSteps')
    c2 = g.call(f'{KSL}:K2_ClearTimer', 864, 0, FunctionName='FailDay')
    c3 = g.call(f'{KSL}:K2_ClearTimer', 1184, 0, FunctionName='PayoffDone')
    c3a = g.call(f'{KSL}:K2_ClearTimer', 1184, 160, FunctionName='PayoffShotOut')
    c3b = g.call(f'{KSL}:K2_ClearTimer', 1344, 160, FunctionName='PayoffShotCut')
    c4 = g.call(f'{KSL}:K2_ClearTimer', 1504, 0, FunctionName='CheckWalkedOut')
    rd = g.call(me('RestoreDoor'), 1824, 0); sw = g.call(me('SweepInteractables'), 2112, 0)
    rt = g.call(me('ResetTasks'), 2432, 0)
    nm = g.get('NightMare', 2464, 192); hide = g.call(f'{SC}:SetVisibility', 2720, 0, bNewVisibility='false')
    hn = g.call(me('HideNightmare'), 3040, 0); up = g.call(me('UndressPlayer'), 3328, 0)
    op = dispatch(g, 'OnPhoneChanged', 3616, 0)
    g.link(nm, 'NightMare', hide, 'self'); g.exec_chain(reset, ex, xc, c1, c2, c3, c3a, c3b, c4, rd, sw, rt, hide, hn, up, op)
    g.comment('Reset the house', 'Camera and door back, beat timers and the alarm stopped, every BPI_Interactable to its '
              'morning state, tasks unticked, the mare and the Nightmare gone, the player bare; knowledge stays in GI_FoA',
              [e, reset, ex, xc, c1, c2, c3, c3a, c3b, c4, rd, sw, rt, nm, hide, hn, up, op] + enc_nodes, C_DAY)

    # ---- ResetToTitle: pause menu "Quit to Title"; back to before T0, same day, no rollover
    g, e = open_fn('ResetToTitle')
    rh = g.call(me('ResetHouse'), 256, 0); rb = g.call(me('ReturnToBed'), 544, 0)
    si = g.set('BeatIndex', 832, 0); g.default(si, 'BeatIndex', -1)
    sb = g.set('Beat', 1120, 0)
    ro = g.set('bRollingOver', 1408, 0)
    g.exec_chain(e, rh, rb, si, sb, ro)
    g.comment('Reset for the title', 'No new day: the house and beat state go back to before T0, so the title can call '
              'BeginMorning again', [e, rh, rb, si, sb, ro], C_DAY)

    # ---- FreezeForRollover: start of FailDay and RestartDay
    g, e = open_fn('FreezeForRollover')
    if can_call(DIR, 'CancelClothingInspection'):
        cancel_inspection = g.call(me('CancelClothingInspection'), -320, 0)
        g.exec_chain(e, cancel_inspection); e = cancel_inspection
    reset = g.call(me('FinishWardrobeTransition'), 256, -192)
    on = g.set('bRollingOver', 256, 0); g.default(on, 'bRollingOver', 'true')
    pw = g.call(f'{GS}:GetPlayerPawn', 256, 192, PlayerIndex=0); pc = g.call(f'{GS}:GetPlayerController', 256, 320, PlayerIndex=0)
    di = g.call(f'{ACTOR}:DisableInput', 576, 0)
    g.link(pw, 'ReturnValue', di, 'self'); g.link(pc, 'ReturnValue', di, 'PlayerController'); g.exec_chain(e, reset, on, di)
    g.comment('Freeze for the rollover', 'Events are ignored and the player stops until the new morning fades in',
              [e, reset, on, pw, pc, di], C_DAY)

    # ---- ReturnToBed: wake-up spot, and the duvet dent back for the wake-up cinematic (player lane's MPC)
    g, e = open_fn('ReturnToBed')
    pw = g.call(f'{GS}:GetPlayerPawn', 32, 192, PlayerIndex=0); ws = g.get('WakeUpStart', 64, 336)
    loc = g.call(f'{ACTOR}:K2_GetActorLocation', 320, 288); rot = g.call(f'{ACTOR}:K2_GetActorRotation', 320, 400)
    tp = g.call(f'{ACTOR}:K2_TeleportTo', 640, 0)
    pc = g.call(f'{GS}:GetPlayerController', 640, 256, PlayerIndex=0)
    cr = g.call(f'{CTRL}:SetControlRotation', 992, 0)
    g.link(ws, 'WakeUpStart', loc, 'self'); g.link(ws, 'WakeUpStart', rot, 'self'); g.link(pw, 'ReturnValue', tp, 'self')
    g.link(loc, 'ReturnValue', tp, 'DestLocation'); g.link(rot, 'ReturnValue', tp, 'DestRotation')
    g.link(pc, 'ReturnValue', cr, 'self'); g.link(rot, 'ReturnValue', cr, 'NewRotation'); g.exec_chain(e, tp, cr)
    nodes = [e, pw, ws, loc, rot, tp, pc, cr]
    if HAS_BED:
        dent = g.call('/Script/Engine.KismetMaterialLibrary:SetScalarParameterValue', 1312, 0,
                      Collection=f'{BED_MPC}.MPC_FoAPlayer', ParameterName='BedSettleStart', ParameterValue=1e7)
        g.exec_chain(cr, dent); nodes.append(dent)
    g.comment('Back to bed', 'WakeUpStart (PlayerStart_WakeUp), facing its way; the body dent goes back in the duvet '
              '(MPC_FoAPlayer.BedSettleStart, released by the wake-up cinematic)', nodes, C_DAY)

    # ---- StartNextMorning: second half of the rollover, under the black
    g, e = open_fn('StartNextMorning')
    gi, nd = gi_call(g, 'StartNewDay', 256, 0, 0, 192)
    rd = g.call(me('ResetHouse'), 576, 0); rb = g.call(me('ReturnToBed'), 864, 0)
    # before T0 again, like ResetToTitle: the T0 phone only opens while BeatIndex < 0 (QA #18, 2026-11-10)
    si = g.set('BeatIndex', 1000, -220); g.default(si, 'BeatIndex', -1); sb = g.set('Beat', 1150, -220)
    off = g.set('bRollingOver', 1152, 0)
    bm = g.call(me('BeginMorning'), 1440, 0)
    pw = g.call(f'{GS}:GetPlayerPawn', 1856, 288, PlayerIndex=0); pc = g.call(f'{GS}:GetPlayerController', 1856, 416, PlayerIndex=0)
    en = g.call(f'{ACTOR}:EnableInput', 2176, 0)
    g.link(pw, 'ReturnValue', en, 'self'); g.link(pc, 'ReturnValue', en, 'PlayerController')
    nodes = [e, gi, nd, rd, rb, si, sb, off, bm, pw, pc, en]
    if HAS_WAKE or HAS_LS:  # LS_WakeUp fades in through its own Fade track; a second camera fade flickers
        g.exec_chain(e, nd, rd, rb, si, sb, off, bm, en)
        tail = 'the wake-up cinematic fades in'
    else:
        cm = g.call(f'{GS}:GetPlayerCameraManager', 1472, 192, PlayerIndex=0)
        fi = g.call('/Script/Engine.PlayerCameraManager:StartCameraFade', 1760, 0, FromAlpha=1.0, ToAlpha=0.0, Duration=1.2,
                    Color=BLACK)
        g.link(cm, 'ReturnValue', fi, 'self'); g.exec_chain(e, nd, rd, rb, si, sb, off, bm, fi, en)
        nodes += [cm, fi]
        tail = 'fade in (until the wake-up cinematic exists)'
    g.comment('A new morning', 'One more crossed-out day (saved), the house resets, back to bed, the morning begins again, '
              + tail, nodes, C_DAY)

    # ---- Cross-lane calls (each stays empty until its owner's function exists)
    g, e = open_fn('ShowTier')
    if HAS_DREAM:
        find, tier, _ = dream_call(g, 'SetTier', {'Tier': (e, 'Tier')}, 'Dream tier', 'BP_DreamDirector shows the tier this beat asks for')
        if can_call(DREAM, 'SetHueDrift'):  # the art direction's slight hue drift over the story: 0 at T0, 0.6 at T10
            bi = g.get('BeatIndex', 1088, 256)
            amt = g.call(f'{KML}:Multiply_DoubleDouble', 1376, 256)
            cv = g.call(f'{KML}:Conv_IntToDouble', 1216, 352)
            g.link(bi, 'BeatIndex', cv, 'InInt'); g.link(cv, 'ReturnValue', amt, 'A'); g.default(amt, 'B', 0.06)
            hue = g.call(f'{cls_path(DREAM)}:SetHueDrift', 1664, 0)
            g.link(find, 'ReturnValue', hue, 'self'); g.link(amt, 'ReturnValue', hue, 'Amount'); g.exec_chain(tier, hue)
    else:
        pending(g, e, 'PostProcess/BP_DreamDirector', 'pp')
    g, e = open_fn('PlayGlitch')
    if HAS_DREAM:
        dream_call(g, 'TriggerGlitchBurst', {'Seconds': (g.get('RolloverSeconds', 832, 224), 'RolloverSeconds')},
                   'Rollover glitch', 'Full-strength glitch burst for the length of the rollover', Strength=1.0)
    else:
        pending(g, e, 'PostProcess/BP_DreamDirector', 'pp')
    g, e = open_fn('StartShirtEncounter')
    if HAS_ENC:
        find, ok, br = actor_check(g, ENC)
        st = g.call(f'{cls_path(ENC)}:StartEncounter', 1088, 0, OpponentId='Shirt')
        g.link(find, 'ReturnValue', st, 'self'); g.link(br, 'True', st, 'execute')
        g.comment('Start the shirt', 'T8: BP_Encounter fights "Shirt"; it reports EncounterWon or calls FailDay',
                  [e, find, ok, br, st], C_FLOW)
    else:
        pending(g, e, 'Gameplay/Encounter/BP_Encounter.StartEncounter', 'mech_encounter')

    # ---- The Nightmare (player lane's BP_Nightmare): staged, never fights
    g, e = open_fn('ShowNightmare')
    if HAS_NM:
        find, ok, br = actor_check(g, NM)
        loc = g.call(f'{SC}:K2_GetComponentLocation', 1088, 224); rot = g.call(f'{SC}:K2_GetComponentRotation', 1088, 352)
        brk = g.call(f'{KML}:BreakRotator', 1376, 352)
        ap = g.call(f'{cls_path(NM)}:Appear', 1632, 0)
        for n in (loc, rot):
            g.link(e, 'Spot', n, 'self')
        g.link(rot, 'ReturnValue', brk, 'InRot'); g.link(find, 'ReturnValue', ap, 'self')
        g.link(loc, 'ReturnValue', ap, 'Location'); g.link(brk, 'Yaw', ap, 'Yaw'); g.link(br, 'True', ap, 'execute')
        g.comment('Show the Nightmare', 'Appears through black sand at the Spot marker, facing its arrow',
                  [e, find, ok, br, loc, rot, brk, ap], C_VISUAL)
    else:
        pending(g, e, 'Characters/Player/BP_Nightmare', 'player')
    g, e = open_fn('HideNightmare')
    if HAS_NM:
        find, ok, br = actor_check(g, NM)
        dt = g.call(f'{ACTOR}:K2_DetachFromActor', 1088, 0); vn = g.call(f'{cls_path(NM)}:Vanish', 1440, 0)
        g.link(find, 'ReturnValue', dt, 'self'); g.link(find, 'ReturnValue', vn, 'self')
        g.link(br, 'True', dt, 'execute'); g.exec_chain(dt, vn)
        g.comment('Hide the Nightmare', 'Off the mare if it was riding, then it vanishes into sand', [e, find, ok, br, dt, vn], C_VISUAL)
    else:
        pending(g, e, 'Characters/Player/BP_Nightmare', 'player')
    g, e = open_fn('RideNightmare')
    if HAS_NM:
        sp = g.get('NightmareRide', 64, 192)
        sn = g.call(me('ShowNightmare'), 256, 0)
        g.exec_chain(e, sn)
        find, ok, br = actor_check(g, NM, after=sn, x=576)
        at = g.call(f'{ACTOR}:K2_AttachToComponent', 1408, 0, LocationRule='SnapToTarget', RotationRule='SnapToTarget',
                    ScaleRule='KeepWorld')
        g.link(sp, 'NightmareRide', sn, 'Spot'); g.link(sp, 'NightmareRide', at, 'Parent')
        g.link(find, 'ReturnValue', at, 'self'); g.link(br, 'True', at, 'execute')
        g.comment('The Nightmare rides the mare', "Rollover: it appears on the mare's back and gallops through with it",
                  [e, sp, sn, find, ok, br, at], C_VISUAL)
    else:
        pending(g, e, 'Characters/Player/BP_Nightmare', 'player')

    # ---- The player (player lane's BP_FoAPlayer); skipped for any other pawn
    for name, func, title, desc, extra in (
            ('EquipSuit', 'Equip', 'Suit on', 'T9: BP_FoAPlayer.Equip("Suit") with its black-sand burst', {'GarmentId': 'Suit'}),
            ('UndressPlayer', 'UnequipAll', 'Bare again', 'New day: back to the bare mannequin', {}),
            ('PlayerTopDown', 'SetTopDownView', 'Player top-down mode', "Movement screen-relative while the director's "
             'top-down camera is live', None),
            ('PlayerCinematic', 'SetCinematic', 'Player cinematic', 'LS_WakeUp drives the body: look-at and foot IK off',
             None)):
        g, e = open_fn(name)
        if not HAS_PLAYER[func]:
            pending(g, e, 'Characters/Player/BP_FoAPlayer.' + func, 'player')
            continue
        pw = g.call(f'{GS}:GetPlayerPawn', 256, 160, PlayerIndex=0)
        c = cast_to(g, 'BP_FoAPlayer', 544, 0)
        call = g.call(f'{cls_path(PLAYER)}:{func}', 864, 0, **(extra or {}))
        g.link(pw, 'ReturnValue', c, 'Object'); g.link(c, 'AsBP_FoAPlayer', call, 'self'); g.exec_chain(e, c)
        g.link(c, 'then', call, 'execute')
        if extra is None:
            g.link(e, 'Enable', call, 'bEnable')
        g.comment(title, desc, [e, pw, c, call], C_VISUAL)

    exec(open('P:/FoA/Tools/Unreal/flow/build_wardrobe_transition.py').read(), globals())
    build_wardrobe_transition()
    exec(open('P:/FoA/Tools/Unreal/flow/refine_wardrobe_scene.py').read(), globals())
    refine_wardrobe_scene()
    exec(open('P:/FoA/Tools/Unreal/flow/build_wake_exit.py').read(), globals())
    build_wake_exit()


def play_wake_up(g, ev, y=3520):
    """PlayWakeUp plays LS_WakeUp on the real pawn (contract, cine): movement, collision and look-at off and the pawn as
    view target BEFORE Play; the Player tag binds it. WakeUpDone (OnFinished, or a skip) gives it back once.
    Hold Space or gamepad A for 0.8 s to skip: Pressed starts a SkipWakeUp timer, Released clears it. The key nodes
    don't consume input, so Jump still works; outside the wake-up SkipWakeUp finds bWakeDone set and does nothing."""
    wake, done, skip = g.at(ev['PlayWakeUp'], 0, y), g.at(ev['WakeUpDone'], 0, y + 640), g.at(ev['SkipWakeUp'], 0, y + 1088)
    chr_ = '/Script/Engine.Character'
    # take the pawn, play
    s0 = g.set('bWakeDone', 256, y); g.default(s0, 'bWakeDone', 'false')
    pc = g.call(f'{GS}:GetPlayerCharacter', 288, y + 224, PlayerIndex=0)
    cm = g.get('CharacterMovement', 544, y + 224, class_path=chr_)
    dm = g.call('/Script/Engine.CharacterMovementComponent:DisableMovement', 544, y)
    col = g.call(f'{ACTOR}:SetActorEnableCollision', 832, y, bNewActorEnableCollision='false')
    cin = g.call(me('PlayerCinematic'), 1120, y, Enable='true')
    ctl = g.call(f'{GS}:GetPlayerController', 1120, y + 224, PlayerIndex=0)
    vt = g.call('/Script/Engine.PlayerController:SetViewTargetWithBlend', 1408, y, BlendTime=0.0)
    mk = g.call('/Script/LevelSequence.LevelSequencePlayer:CreateLevelSequencePlayer', 1728, y,
                Settings='(bDisableMovementInput=True,bDisableLookAtInput=True,bHideHud=True)')
    g.default(mk, 'LevelSequence', f'{LS}.LS_WakeUp')
    sp = g.set('SeqPlayer', 2112, y)
    tag = g.call('/Script/LevelSequence.LevelSequenceActor:SetBindingByTag', 2432, y, BindingTag='Player',
                 bAllowBindingsFromAsset='false')
    arr = pnode(g, 2176, y + 224, 'MakeArray')
    g.link(arr, 'Array', tag, 'Actors')
    bind, mkev = bind_function(g, sp, 'Output_Get', 'OnFinished', 'WakeUpDone', 2816, y)
    play = g.call('/Script/MovieScene.MovieSceneSequencePlayer:Play', 3136, y)
    g.link(pc, 'ReturnValue', cm, 'self'); g.link(cm, 'CharacterMovement', dm, 'self'); g.link(pc, 'ReturnValue', col, 'self')
    g.link(ctl, 'ReturnValue', vt, 'self'); g.link(pc, 'ReturnValue', vt, 'NewViewTarget')
    g.link(mk, 'ReturnValue', sp, 'SeqPlayer'); g.link(mk, 'OutActor', tag, 'self'); g.link(pc, 'ReturnValue', arr, '[0]')
    g.link(sp, 'Output_Get', play, 'self')
    g.exec_chain(wake, s0, dm, col, cin, vt, mk, sp, tag, bind, play)
    nodes, last = [wake, s0, pc, cm, dm, col, cin, ctl, vt, mk, sp, tag, arr, bind, mkev, play], play
    if HAS_BED:  # the duvet relaxes when he lifts off, 9.37 s in (LS_WakeUp retimed to 19.1 s, 2026-11-09)
        now = g.call(f'{GS}:GetTimeSeconds', 3392, y + 224)
        add = g.call(f'{KML}:Add_DoubleDouble', 3648, y + 224); g.default(add, 'B', 9.37)
        bed = g.call('/Script/Engine.KismetMaterialLibrary:SetScalarParameterValue', 3904, y,
                     Collection=f'{BED_MPC}.MPC_FoAPlayer', ParameterName='BedSettleStart')
        g.link(now, 'ReturnValue', add, 'A'); g.link(add, 'ReturnValue', bed, 'ParameterValue'); g.exec_chain(last, bed)
        nodes += [now, add, bed]; last = bed
    if exists(HINT):
        cw = pnode(g, 4224, y, 'UserInterface', 'CreateWidget'); g.default(cw, 'Class', f'{HINT}.WBP_SkipHint_C')
        sh = g.set('SkipHint', 4608, y)  # created hidden: no UI over the cinematic; it shows only while skip is held
        g.link(ctl, 'ReturnValue', cw, 'OwningPlayer'); g.link(cw, 'ReturnValue', sh, 'SkipHint')
        g.exec_chain(last, cw, sh); nodes += [cw, sh]
    g.comment('Play the wake-up', '', nodes, C_FLOW)
    # give the pawn back, once
    y2 = y + 640
    dn = g.get('bWakeDone', 256, y2 + 192); br = g.branch(256, y2)
    s1 = g.set('bWakeDone', 512, y2); g.default(s1, 'bWakeDone', 'true')
    pc2 = g.call(f'{GS}:GetPlayerCharacter', 544, y2 + 224, PlayerIndex=0)
    cm2 = g.get('CharacterMovement', 800, y2 + 224, class_path=chr_)
    walk = g.call('/Script/Engine.CharacterMovementComponent:SetMovementMode', 800, y2, NewMovementMode='MOVE_Walking')
    col2 = g.call(f'{ACTOR}:SetActorEnableCollision', 1120, y2, bNewActorEnableCollision='true')
    safe = g.call(me('SafeWakeExit'), 1120, y2 - 192)
    ctl2 = g.call(f'{GS}:GetPlayerController', 1120, y2 + 224, PlayerIndex=0)
    cr = g.call(f'{CTRL}:SetControlRotation', 1408, y2)
    rot = g.call(f'{KML}:MakeRotator', 1408, y2 + 224, Roll=0.0, Pitch=-10.0, Yaw=195.0)  # room-facing hand-off (anim lane, 2026-11-09); by-ref pin: no literal default
    g.link(rot, 'ReturnValue', cr, 'NewRotation')
    cin2 = g.call(me('PlayerCinematic'), 1728, y2, Enable='false')
    g.link(dn, 'bWakeDone', br, 'Condition'); g.link(pc2, 'ReturnValue', cm2, 'self'); g.link(cm2, 'CharacterMovement', walk, 'self')
    g.link(pc2, 'ReturnValue', col2, 'self'); g.link(ctl2, 'ReturnValue', cr, 'self')
    g.exec_chain(done, br); g.link(br, 'False', s1, 'execute'); g.exec_chain(s1, walk, col2, safe, cr, cin2)
    nodes, last = [done, dn, br, s1, pc2, cm2, walk, col2, safe, ctl2, cr, rot, cin2], cin2
    if exists(HINT):
        hv = g.get('SkipHint', 2016, y2 + 224); ok = g.call(f'{KSL}:IsValid', 2272, y2 + 224); b2 = g.branch(2016, y2)
        rm = g.call('/Script/UMG.Widget:RemoveFromParent', 2528, y2)
        g.link(hv, 'SkipHint', ok, 'Object'); g.link(ok, 'ReturnValue', b2, 'Condition'); g.link(hv, 'SkipHint', rm, 'self')
        g.exec_chain(last, b2); g.link(b2, 'True', rm, 'execute')
        smb = g.call(me('StartMorningBeats'), 2848, y2)
        g.exec_chain(rm, smb); g.link(b2, 'False', smb, 'execute')
        nodes += [hv, ok, b2, rm, smb]
    else:
        smb = g.call(me('StartMorningBeats'), 2016, y2); g.exec_chain(last, smb); nodes.append(smb)
    g.comment('Wake-up done', '', nodes, C_FLOW)
    # skip: jump to the end (Stop never fires OnFinished), relax the duvet now, give the pawn back. The post-wake fade
    # (hold black 0.15 s, then fade up 0.5 s, normal end and skip alike) has one owner: BP_FoAPlayer (anim lane, 2026-11-09).
    y3 = y + 1088
    dn3 = g.get('bWakeDone', 256, y3 + 192); b3 = g.branch(256, y3)
    sp3 = g.get('SeqPlayer', 512, y3 + 224)
    end = g.call('/Script/MovieScene.MovieSceneSequencePlayer:GoToEndAndStop', 544, y3)
    wd = g.call(me('WakeUpDone'), 1184, y3)
    g.link(dn3, 'bWakeDone', b3, 'Condition'); g.link(sp3, 'SeqPlayer', end, 'self')
    g.exec_chain(skip, b3); g.link(b3, 'False', end, 'execute')
    nodes, last = [skip, dn3, b3, sp3, end, wd], end
    if HAS_BED:
        now2 = g.call(f'{GS}:GetTimeSeconds', 832, y3 + 224)
        bed2 = g.call('/Script/Engine.KismetMaterialLibrary:SetScalarParameterValue', 864, y3,
                      Collection=f'{BED_MPC}.MPC_FoAPlayer', ParameterName='BedSettleStart')
        g.link(now2, 'ReturnValue', bed2, 'ParameterValue'); g.exec_chain(end, bed2); nodes += [now2, bed2]; last = bed2
    g.exec_chain(last, wd)
    keys = [pnode(g, 0, y3 + 448, 'KeyboardEvents', 'SpaceBar'), pnode(g, 0, y3 + 704, 'GamepadEvents', 'FaceButtonBottom')]
    st = g.call(f'{KSL}:K2_SetTimer', 384, y3 + 448, FunctionName='SkipWakeUp', Time=0.8, bLooping='false')
    ct = g.call(f'{KSL}:K2_ClearTimer', 384, y3 + 704, FunctionName='SkipWakeUp')
    for k in keys:
        k.set_editor_property('consume_input', False)  # Space is also Jump
        g.link(k, 'Pressed', st, 'execute'); g.link(k, 'Released', ct, 'execute')
    hint = []
    if exists(HINT):  # the hint is on screen only while the skip key is held during a wake-up
        dn4 = g.get('bWakeDone', 704, y3 + 640); b4 = g.branch(704, y3 + 448)
        h1 = g.get('SkipHint', 960, y3 + 640); av = g.call('/Script/UMG.UserWidget:AddToViewport', 960, y3 + 448, ZOrder=50)
        h2 = g.get('SkipHint', 704, y3 + 896); ok4 = g.call(f'{KSL}:IsValid', 960, y3 + 896); b5 = g.branch(960, y3 + 704)
        rm = g.call('/Script/UMG.Widget:RemoveFromParent', 1216, y3 + 704)
        g.link(dn4, 'bWakeDone', b4, 'Condition'); g.link(h1, 'SkipHint', av, 'self'); g.exec_chain(st, b4)
        g.link(b4, 'False', av, 'execute')
        g.link(h2, 'SkipHint', ok4, 'Object'); g.link(ok4, 'ReturnValue', b5, 'Condition'); g.link(h2, 'SkipHint', rm, 'self')
        g.exec_chain(ct, b5); g.link(b5, 'True', rm, 'execute')
        hint = [dn4, b4, h1, av, h2, ok4, b5, rm]
    g.comment('Skip the wake-up', '', nodes + keys + [st, ct] + hint, C_FLOW)


def build_events():
    bp = unreal.load_asset(DIR)
    unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(bp)
    g = FGraph(DIR)
    ev = {k: n for k, n in custom_events(g.ed).items() if k in EVENTS}  # kept, so calls stay bound; orphans go
    for c in list(g.ed.list_comment_nodes()):
        g.ed.remove_comment_node(c)
    rest = [n for n in g.ed.list_all_nodes() if n not in ev.values()]
    if rest:
        g.ed.remove_nodes(rest)
    fail, restart = g.at(ev['FailDay'], 0, 480), g.at(ev['RestartDay'], 0, 800)
    fade, gallop = g.at(ev['FadeToNextMorning'], 1408, 800), g.at(ev['GallopMare'], 0, 1216)
    wake = g.at(ev['PlayWakeUp'], 0, 1696)
    endl = g.at(ev['EndLevel'], 0, 2048)

    # Begin play
    bpn = g.event('ReceiveBeginPlay', 0, 0)
    start = bpn
    if can_call(DIR, 'StartStoryMoments'):
        start = g.call(me('StartStoryMoments'), 128, -192)
        g.exec_chain(bpn, start)
    rt = g.call(me('ResetTasks'), 288, 0)
    fr = g.get('DoorFrame', 352, 192); ftr = g.call(f'{ACTOR}:GetTransform', 544, 192)
    sf = g.set('FrameHome', 832, 0)
    dr = g.get('Door', 864, 192); dtr = g.call(f'{ACTOR}:GetTransform', 1056, 192)
    sd = g.set('DoorHome', 1344, 0)
    g.link(fr, 'DoorFrame', ftr, 'self'); g.link(ftr, 'ReturnValue', sf, 'FrameHome')
    g.link(dr, 'Door', dtr, 'self'); g.link(dtr, 'ReturnValue', sd, 'DoorHome'); g.exec_chain(start, rt, sf, sd)
    g.comment('Begin play', 'Tasks start unticked; remember where the door frame and door belong. The morning waits for '
              'BeginMorning (main menu Wake Up)', [bpn, rt, fr, ftr, sf, dr, dtr, sd], C_EVENT)
    if HAS_ROLLOVER:
        hear_rollover(g, sd, 1760)

    # FailDay: the dream breaks. RestartDay (pause menu) is the same new day without the fail. Both end in FadeToNextMorning.
    ro = g.get('bRollingOver', 64, 640)
    b1 = g.branch(288, 480)
    fz = g.call(me('FreezeForRollover'), 544, 480)
    lf = g.call(me('LearnFromFailure'), 864, 480)
    gl = g.call(me('PlayGlitch'), 1184, 480)
    gm = g.call(me('GallopMare'), 1472, 480)
    rs = g.get('RolloverSeconds', 1504, 640)
    d1 = g.call(f'{KSL}:Delay', 1760, 480)
    f1 = g.call(me('FadeToNextMorning'), 2048, 480)
    g.link(ro, 'bRollingOver', b1, 'Condition'); g.exec_chain(fail, b1); g.link(b1, 'False', fz, 'execute')
    g.link(rs, 'RolloverSeconds', d1, 'Duration'); g.exec_chain(fz, lf, gl, gm, d1)
    fail_nodes = [fail, ro, b1, fz, lf, gl, gm, rs, d1, f1]
    if HAS_ROLLOVER:  # P13: the front end's rollover card; OnRolloverCovered (bound at BeginPlay) starts the morning
        fe = g.call(f'{GS}:GetActorOfClass', 2048, 480, ActorClass=cls_path(FRONT))
        ok = g.call(f'{KSL}:IsValid', 2304, 640); b3 = g.branch(2560, 480)
        gi = g.call(me('GetFoAGI'), 2560, 360); dc = g.get('DayCount', 2816, 360, class_path=GI_C)
        nd = g.call(f'{KML}:Add_IntInt', 3072, 360, B=1); ll = g.get('LastLearned', 3104, 640)
        roll = g.call(f'{cls_path(FRONT)}:PlayDayRollover', 3328, 480)
        g.link(fe, 'ReturnValue', ok, 'Object'); g.link(ok, 'ReturnValue', b3, 'Condition')
        g.link(fe, 'ReturnValue', roll, 'self'); g.link(gi, 'GI', dc, 'self'); g.link(dc, 'DayCount', nd, 'A')
        g.link(nd, 'ReturnValue', roll, 'NewDay'); g.link(ll, 'LastLearned', roll, 'Learned')
        g.exec_chain(d1, fe, b3); g.link(b3, 'True', roll, 'execute'); g.link(b3, 'False', f1, 'execute')
        g.at(f1, 2816, 640)
        fail_nodes += [fe, ok, b3, gi, dc, nd, ll, roll]
    else:
        g.exec_chain(d1, f1)
    g.comment('Fail: the day rolls over', 'Encounter loss (or the optional alarm): freeze, learn from the attempt, '
              'glitch and night mare, then a new morning', fail_nodes, C_DAY)

    ro2 = g.get('bRollingOver', 64, 944)
    b2 = g.branch(288, 800)
    fz2 = g.call(me('FreezeForRollover'), 544, 800)
    f2 = g.call(me('FadeToNextMorning'), 864, 800)
    g.link(ro2, 'bRollingOver', b2, 'Condition'); g.exec_chain(restart, b2); g.link(b2, 'False', fz2, 'execute')
    g.exec_chain(fz2, f2)
    g.comment('Restart the day', 'Pause menu: a deliberate new day, no glitch, no mare, nothing learned (unpause first: '
              'the fade waits on game time)', [restart, ro2, b2, fz2, f2], C_DAY)

    cm = g.call(f'{GS}:GetPlayerCameraManager', 1408, 944, PlayerIndex=0)
    fo = g.call('/Script/Engine.PlayerCameraManager:StartCameraFade', 1696, 800, FromAlpha=0.0, ToAlpha=1.0, Duration=0.4,
                Color=BLACK, bHoldWhenFinished='true')
    d2 = g.call(f'{KSL}:Delay', 2080, 800, Duration=0.5)
    nm = g.call(me('StartNextMorning'), 2368, 800)
    g.link(cm, 'ReturnValue', fo, 'self'); g.exec_chain(fade, fo, d2, nm)
    g.comment('Fade to the next morning', 'Black in 0.4 s, then StartNextMorning resets the house under the black',
              [fade, cm, fo, d2, nm], C_DAY)

    # GallopMare: placeholder night mare (sandvfx lane's splat), skipped while the mesh doesn't exist
    mp = g.get('NightMareMesh', 32, 1376)
    sr = g.call(f'{KSL}:Conv_SoftObjPathToSoftObjRef', 288, 1376)
    ld = g.call(f'{KSL}:LoadAsset_Blocking', 576, 1216)
    c = cast_to(g, 'StaticMesh', 896, 1216)
    mare = g.get('NightMare', 1024, 1408)
    sm = g.call('/Script/Engine.StaticMeshComponent:SetStaticMesh', 1248, 1216)
    rl = g.call(f'{SC}:K2_SetRelativeLocation', 1600, 1216, NewLocation='(X=0.0,Y=-520.0,Z=0.0)')
    sv = g.call(f'{SC}:SetVisibility', 1952, 1216, bNewVisibility='true')
    rn = g.call(me('RideNightmare'), 2304, 1216)
    rs2 = g.get('RolloverSeconds', 2368, 1472)
    mv = g.call(f'{KSL}:MoveComponentTo', 2624, 1216, TargetRelativeLocation='(X=0.0,Y=520.0,Z=0.0)')
    g.link(mp, 'NightMareMesh', sr, 'SoftObjectPath'); g.link(sr, 'ReturnValue', ld, 'Asset'); g.link(ld, 'ReturnValue', c, 'Object')
    g.exec_chain(gallop, ld); g.link(ld, 'then', c, 'execute'); g.link(c, 'then', sm, 'execute'); g.exec_chain(sm, rl, sv, rn)
    g.link(c, 'AsStaticMesh', sm, 'NewMesh')
    for n in (sm, rl, sv):
        g.link(mare, 'NightMare', n, 'self')
    g.link(mare, 'NightMare', mv, 'Component'); g.link(rs2, 'RolloverSeconds', mv, 'OverTime'); g.link(rn, 'then', mv, 'Move')
    g.comment('Night mare (placeholder)', 'The black-sand mare gallops across the room with the Nightmare on its back; '
              'nothing happens until SM_TheNightMare is imported', [gallop, mp, sr, ld, c, mare, sm, rl, sv, rn, rs2, mv],
              C_VISUAL)

    # PlayWakeUp: LS_WakeUp played here (play_wake_up); BP_WakeUpCinematic, then straight to T0, are fallbacks only
    if HAS_LS:
        play_wake_up(g, ev)
    else:
        smb = g.call(me('StartMorningBeats'), 1472, 1696)
        nodes = [wake, smb]
        if HAS_WAKE:
            sp = pnode(g, 288, 1696, 'SpawnActorfromClass')
            g.default(sp, 'Class', cls_path(WAKE))
            tf = g.call(f'{KML}:MakeTransform', 32, 1888)  # identity: the cinematic places itself from the level
            g.link(tf, 'ReturnValue', sp, 'SpawnTransform'); nodes.append(tf)
            g.exec_chain(wake, sp)
            bind, done = bind_event(g, sp, 'ReturnValue', 'OnWakeUpFinished', 'WakeUpFinished', 768, 1696)
            g.exec_chain(sp, bind); g.exec_chain(done, smb)
            nodes += [sp, bind, done]
            desc = 'Spawns BP_WakeUpCinematic (it destroys itself); OnWakeUpFinished starts T0 with the player standing'
        else:
            g.exec_chain(wake, smb)
            desc = 'Straight to T0 until /Game/FoA/Cinematics/BP_WakeUpCinematic exists (wake-up lane); rerun the build then'
        g.comment('Wake-up cinematic', desc, nodes, C_FLOW)

    op = g.call(me('OpenTheDoor'), 256, 2048)
    find = g.call(f'{GS}:GetActorOfClass', 512, 2048, ActorClass=cls_path(THRESHOLD))
    start = g.call(f'{cls_path(THRESHOLD)}:StartThreshold', 800, 2048)
    g.link(find, 'ReturnValue', start, 'self'); g.exec_chain(endl, op, find, start)
    g.comment('Continue into the dream', 'The same pawn crosses into Level 2.', [endl, op, find, start], C_FLOW)

    # F9 is reserved for the frontend read-only diagnostic overlay.
    f10 = pnode(g, 0, 3008, 'Keyboard', 'F10')
    pk = g.call(f'{KSL}:IsPackagedForDistribution', 32, 3168)
    guard = g.branch(320, 3008)
    fd = g.call(me('FailDay'), 608, 3008)
    g.link(f10, 'Pressed', guard, 'execute'); g.link(pk, 'ReturnValue', guard, 'Condition')
    g.link(guard, 'False', fd, 'execute')
    g.comment('Development failure key', 'Development-only failure shortcut', [f10, pk, guard, fd], C_DEV)
    del bp  # Hayba blueprint_compile follows (outside this script)


def set_templates(bp):
    """Component template values, after the compile; each template wrapper is dropped as soon as it's set.
    Placed at the world origin, so these relative transforms are world transforms (editor-rules room coordinates)."""
    sds, lib, hs, by_name = subobjects(bp)
    rot = lambda yaw, pitch=0.0: unreal.Rotator(roll=0.0, pitch=pitch, yaw=yaw)  # noqa: E731
    marker = {'arrow_color': unreal.Color(r=40, g=40, b=40, a=255)}
    values = {
        'TopDownCamera': {  # the whole room from above, like the TopDown pose; screen-up = +X
            'relative_location': unreal.Vector(0, -45, 1500), 'relative_rotation': rot(0, -89.9),
            'field_of_view': 55.0, 'auto_activate': True},
        'MovedDoorSpot': {  # where the door frame lands at T7: west wall, south of the chimney, facing into the room
            'relative_location': unreal.Vector(-365, -190, 0), 'relative_rotation': rot(180), 'arrow_size': 2.0},
        'UnderDoorLight': {  # light spilling from under the moved door (Knows.DoorMoves); frame-local -X is the room
            'relative_location': unreal.Vector(-6, 0, 2), 'relative_rotation': rot(180),
            'source_width': 90.0, 'source_height': 2.0, 'barn_door_angle': 70.0, 'barn_door_length': 8.0,
            'intensity': 12.0, 'attenuation_radius': 260.0, 'cast_shadows': True, 'visible': False},
        'NightMare': {  # mesh comes from NightMareMesh (sandvfx lane's splat) at rollover; hidden until then
            'visible': False, 'cast_shadow': False, 'relative_location': unreal.Vector(0, -520, 0),
            'relative_scale3d': unreal.Vector(1.2, 1.2, 1.2)},
        # Where BP_Nightmare (player lane) shows itself: T1 in the corner by the wardrobe, in view of the wake-up spot;
        # T7 in the empty doorway the door left; T8 in the bay alcove at the edge of the fight; riding the mare at rollover.
        'NightmareT1': dict(marker, relative_location=unreal.Vector(335, 265, 0), relative_rotation=rot(-125)),
        'NightmareT7': dict(marker, relative_location=unreal.Vector(392, 87.5, 0), relative_rotation=rot(180)),
        'NightmareT8': dict(marker, relative_location=unreal.Vector(-60, -350, 0), relative_rotation=rot(80)),
        'NightmareRide': dict(marker, relative_location=unreal.Vector(0, -20, 130), relative_rotation=rot(90)),
        'WardrobeKeyLight': {'relative_location': unreal.Vector(195, 70, 240), 'visible': False,
                             'intensity_units': unreal.LightUnits.LUMENS, 'intensity': 100.0,
                             'attenuation_radius': 350.0, 'use_inverse_squared_falloff': True, 'cast_shadows': False},
    }
    for name, props in values.items():
        tpl = lib.get_object_for_blueprint(lib.get_data(by_name[name]), bp)
        for k, v in props.items():
            tpl.set_editor_property(k, v)
        if name == 'NightMare':
            tpl.set_collision_profile_name('NoCollision')
        del tpl
    for name in ('FallenWardrobeBlocker', 'OldDoorBlocker'):
        tpl = lib.get_object_for_blueprint(lib.get_data(by_name[name]), bp)
        tpl.set_collision_profile_name('BlockAll')
        tpl.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
        tpl.set_editor_property('hidden_in_game', True)
        tpl.set_editor_property('generate_overlap_events', False)
        if name == 'OldDoorBlocker':
            tpl.set_editor_property('box_extent', unreal.Vector(20, 58, 150))
        del tpl


def write_defaults():
    """Class defaults and component values, after the events step's compile; then a save WITHOUT a compile."""
    set_defaults(DIR, {
        'Beats': [unreal.load_asset(f'{BEATS}/DA_Beat_{b}') for b in BEAT_IDS],
        'PhoneTasks': [unreal.Text(t) for t in PHONE_TASKS],
        'RolloverSeconds': 2.4, 'AlarmClockSeconds': 720.0, 'TopDownBlend': 1.5, 'TopDownHold': 8.0,
        'TopDownHoldKnown': 4.0, 'BeatIndex': -1, 'bAlarmClockFail': False, 'bWakeDone': True,  # no wake-up running
        'NightMareMesh': unreal.SoftObjectPath('/Game/FoA/VFX/Splats/Meshes/SM_TheNightMare.SM_TheNightMare'),
        'auto_receive_input': unreal.AutoReceiveInput.PLAYER0})  # dev F10 (distribution builds ignore it)
    set_templates(unreal.load_asset(DIR))


if STEP == 'declare':
    declare()
elif STEP == 'funcs':
    build_functions()
    if 'InteractionStage' in [str(n) for n in BEL.list_member_variable_names(unreal.load_asset(GI))]:
        import runpy
        previous_phase = os.environ.get('FOA_PHASE')
        try:
            os.environ['FOA_PHASE'] = 'flow'
            runpy.run_path('P:/FoA/Tools/Unreal/gameplay/build_interaction_pacing.py', run_name='__main__')
            if can_call(PLAYER, 'SetBootsWorn'):
                os.environ['FOA_PHASE'] = 'flow'
                runpy.run_path('P:/FoA/Tools/Unreal/gameplay/build_boot_pacing.py', run_name='__main__')
        finally:
            if previous_phase is None:
                os.environ.pop('FOA_PHASE', None)
            else:
                os.environ['FOA_PHASE'] = previous_phase
elif STEP == 'wardrobe':
    # Narrow refresh preserves other lanes' EnterBeat progression and encounter hooks.
    exec(open('P:/FoA/Tools/Unreal/flow/build_wardrobe_transition.py').read(), globals())
    build_wardrobe_transition()
    exec(open('P:/FoA/Tools/Unreal/flow/refine_wardrobe_scene.py').read(), globals())
    refine_wardrobe_scene()
elif STEP == 'events':
    build_events()
elif STEP == 'defaults':  # after the last Hayba compile of BP_BeatDirector this session (crash safety)
    report(DIR)
    write_defaults()
    save_nocompile(DIR)
print('done', STEP, 'rollover', HAS_ROLLOVER, 'dream', HAS_DREAM, 'bpi', HAS_BPI, 'enc', HAS_ENC, 'player', HAS_PLAYER, 'fe_end', HAS_FE_END, 'letterbox', HAS_LETTERBOX, 'reveal', HAS_REVEAL, 'nightmare', HAS_NM,
      'wake', HAS_WAKE, 'bed', HAS_BED)
