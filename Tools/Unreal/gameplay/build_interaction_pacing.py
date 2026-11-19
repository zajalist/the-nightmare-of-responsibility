"""Targeted sequence/contact patch. Phases declare, flow, gate, contact. Never rebuilds unrelated graphs.
Apply each phase under its asset lease; replay queued Hayba compile/save before releasing the lease.
"""
import os
import sys
import unreal

exec(open('P:/FoA/Tools/Unreal/ui/bp_graph.py', encoding='utf-8').read())
BASE = '/Game/FoA/Gameplay/BP_Interactable'
GI = '/Game/FoA/Gameplay/GI_FoA'
DIRECTOR = '/Game/FoA/Gameplay/BP_BeatDirector'
ROW = BEL.get_struct_type(unreal.load_asset('/Game/FoA/Gameplay/S_Interaction'))
K = '/Script/Engine.KismetMathLibrary:'
GS = '/Script/Engine.GameplayStatics:'
phase = os.environ.get('FOA_PHASE', 'declare')


def result_node(g):
    nodes = list(g.ed.list_nodes_of_class(unreal.K2Node_FunctionResult))
    return nodes[0] if nodes else g.ed.add_return_node()


def cls(path):
    return path + '.' + path.rsplit('/', 1)[1] + '_C'


def palette(g, *parts):
    norm = lambda s: str(s).replace(' ', '').replace('_', '').lower()
    hits = [str(n) for n in g.ed.list_available_nodes([]) if all(norm(p) in norm(n) for p in parts)]
    assert hits, parts
    return min(hits, key=len)


def field(node, name):
    return next(str(PIN.get_pin_name(p)) for p in BEL.list_output_pins(node)
                if str(PIN.get_pin_name(p)).split('_')[0] == name)


def comment(g, title, nodes):
    c = g.ed.add_comment_to_nodes(title, nodes, 48)
    BEL.set_comment_color(c, C_LOGIC)
    house_comment_flags(c)


def prepend(g, first, last=None):
    e = entry_node(g)
    old = list(PIN.list_connected_pins(BEL.find_then_pin(e)))
    assert len(old) == 1, old
    PIN.break_pin_links(BEL.find_then_pin(e))
    g.exec_chain(e, first)
    assert PIN.try_create_connection(BEL.find_then_pin(last or first), old[0])


def declaration():
    ensure_vars(GI, [('InteractionStage', ptype('int'), '-1', 'Interaction', False),
        ('InteractionEventStages', BEL.get_map_type(ptype('name'), ptype('int')),
         '((Searched,2),(LookedAtBed,2),(KeyTaken,3),(KeySnapped,4),(LatchFreed,5),(WardrobeFalling,6),(WardrobeLanded,6),(ShirtTaken,7))', 'Interaction', False),
        ('InteractionEventShortcuts', BEL.get_map_type(ptype('name'), ptype('name')),
         '((KeyTaken,Knows.KeyInBoot),(KeySnapped,Knows.KeySnaps),(LatchFreed,Knows.KeySnaps),(WardrobeFalling,Knows.WardrobeFalls),(WardrobeLanded,Knows.WardrobeFalls))', 'Interaction', False)])
    if 'CanReportInteractionEvent' not in [str(n) for n in BEL.list_graph_names(unreal.load_asset(GI))]:
        Graph.function(GI, 'CanReportInteractionEvent', inputs=[('Event', ptype('name'))], outputs=[('Allowed', ptype('bool'))], pure=True)
    compile_save(GI)
    ensure_vars(BASE, [('bPendingRow', ptype('bool'), 'false', 'Interaction', False),
                       ('PendingRow', ROW, '', 'Interaction', False),
                       ('PendingMontage', ptype(unreal.AnimMontage), '', 'Interaction', False),
                       ('ContactTimes', BEL.get_map_type(ptype('name'), ptype('real')), '', 'Interaction', False),
                       ('RequiredStages', BEL.get_map_type(ptype('name'), ptype('int')), '((KeyTaken,3),(KeySnapped,4),(LatchFreed,5),(ShirtTaken,7),(PlateOff,5),(HandleOff,6),(Worn,4),(BootsWorn,4))', 'Interaction', False),
                       ('ShortcutFlags', BEL.get_map_type(ptype('name'), ptype('name')), '((KeyTaken,Knows.KeyInBoot),(KeySnapped,Knows.KeySnaps),(LatchFreed,Knows.KeySnaps),(PlateOff,Knows.KeySnaps),(HandleOff,Knows.WardrobeFalls))', 'Interaction', False)])
    names = {str(n) for n in BEL.list_graph_names(unreal.load_asset(BASE))}
    for name, inputs, outputs, pure in (
            ('CanApplyProgressionRow', [('Row', ROW)], [('Allowed', ptype('bool'))], True),
            ('CommitInteractionRow', [('Row', ROW)], [], False),
            ('BeginPendingRow', [('Row', ROW)], [], False), ('FinishPendingRow', [], [], False),
            ('CancelPendingRow', [('bRestoreScan', ptype('bool'))], [], False)):
        if name not in names:
            Graph.function(BASE, name, inputs=inputs, outputs=outputs, pure=pure)
    contacts = {}
    for name, wanted in (('AM_FoA_PickUp_Floor', 'Grab'), ('AM_FoA_PickUp_Table', 'Grab'),
                         ('AM_FoA_OpenDrawer', 'Grip'), ('AM_FoA_TryLockedHandle', 'Locked'),
                         ('AM_FoA_KneelScrewdriver', 'WorkDone')):
        montage = unreal.load_asset('/Game/FoA/Characters/Player/Montages/' + name)
        for event in unreal.AnimationLibrary.get_animation_notify_events(montage):
            notify = event.get_editor_property('notify')
            if isinstance(notify,unreal.AnimNotify_PlayMontageNotify) and str(notify.get_editor_property('notify_name')) == wanted:
                contacts[name] = unreal.AnimationLibrary.get_anim_notify_event_trigger_time(event)
        assert name in contacts and contacts[name] > 0, (name, wanted)
    text = '(' + ','.join('(' + n + ',' + str(v) + ')' for n, v in contacts.items()) + ')'
    compile_save(BASE)
    # Typed Blueprint map defaults are not supported by the installed Hayba writers.
    # Apply contact_defaults only after the declaration has compiled.


def flow():
    for name in ('EnterBeat', 'ResetHouse'):
        g = Graph(DIRECTOR, name)
        if not any('InteractionStage' in BEL.get_node_title(n) for n in g.ed.list_all_nodes()):
            e = entry_node(g)
            gi = g.call(cls(DIRECTOR) + ':GetFoAGI', -500, 240)
            stage = g.set('InteractionStage', -320, 0, class_path=cls(GI))
            g.link(gi, 'GI', stage, 'self')
            if name == 'EnterBeat':
                g.link(e, 'Index', stage, 'InteractionStage')
            else:
                g.default(stage, 'InteractionStage', -1)
            prepend(g, stage)
            comment(g, 'Publish the current step', [gi, stage])
    compile_save(DIRECTOR)


def gate():
    g = Graph.function(BASE, 'CanApplyProgressionRow', inputs=[('Row', ROW)], outputs=[('Allowed', ptype('bool'))], pure=True)
    e = g.at(entry_node(g), 0, 0)
    b = g.node(palette(g, 'Break', 'S_Interaction'), 0, 240)
    g.link(e, 'Row', b, 'S_Interaction')
    gi = g.call(GS + 'GetGameInstance', 0, -300)
    cast = g.node(palette(g, 'CastToGI_FoA'), 300, 0)
    g.link(gi, 'ReturnValue', cast, 'Object'); g.exec_chain(e, cast)
    stage = g.get('InteractionStage', 300, 240, class_path=cls(GI))
    g.link(cast, 'AsGI_FoA', stage, 'self')
    noevent = g.call(K + 'EqualEqual_NameName', 300, 440, B='None')
    g.link(b, field(b, 'Event'), noevent, 'A')
    key = g.call(K + 'SelectName', 600, 440)
    g.link(b, field(b, 'NextState'), key, 'A'); g.link(b, field(b, 'Event'), key, 'B')
    g.link(noevent, 'ReturnValue', key, 'bPickA')
    def map_find(var, y):
        src = g.get(var, 600, y + 140)
        n = g.call('/Script/Engine.BlueprintMapLibrary:Map_Find', 900, y)
        g.link(src, var, n, 'TargetMap'); g.link(key, 'ReturnValue', n, 'Key')
        return n
    required = map_find('RequiredStages', 240)
    level = g.call(K + 'SelectInt', 1200, 240, B=2)
    g.link(required, 'Value', level, 'A'); g.link(required, 'ReturnValue', level, 'bPickA')
    enough = g.call(K + 'GreaterEqual_IntInt', 1500, 240)
    g.link(stage, 'InteractionStage', enough, 'A'); g.link(level, 'ReturnValue', enough, 'B')
    flag = map_find('ShortcutFlags', 640)
    known = g.call(cls(BASE) + ':Knows', 1200, 640)
    g.link(flag, 'Value', known, 'Flag')
    shortcut = g.call(K + 'BooleanAND', 1500, 640)
    g.link(flag, 'ReturnValue', shortcut, 'A'); g.link(known, 'bKnows', shortcut, 'B')
    permitted = g.call(K + 'BooleanOR', 1800, 240)
    g.link(enough, 'ReturnValue', permitted, 'A'); g.link(shortcut, 'ReturnValue', permitted, 'B')
    morning = g.call(K + 'GreaterEqual_IntInt', 1200, 980, B=2)
    g.link(stage, 'InteractionStage', morning, 'A')
    pending = g.get('bPendingRow', 600, 1160)
    free = g.call(K + 'Not_PreBool', 900, 1160); g.link(pending, 'bPendingRow', free, 'A')
    ready = g.call(K + 'BooleanAND', 1500, 980)
    g.link(morning, 'ReturnValue', ready, 'A'); g.link(free, 'ReturnValue', ready, 'B')
    allowed = g.call(K + 'BooleanAND', 1800, 640)
    g.link(permitted, 'ReturnValue', allowed, 'A'); g.link(ready, 'ReturnValue', allowed, 'B')
    look = g.call(K + 'EqualEqual_NameName', 600, 1440, B='Look')
    notify = g.call(K + 'EqualEqual_NameName', 600, 1600, B='Notify')
    g.link(b, field(b, 'Verb'), look, 'A'); g.link(b, field(b, 'Verb'), notify, 'A')
    bypass = g.call(K + 'BooleanOR', 900, 1440)
    g.link(look, 'ReturnValue', bypass, 'A'); g.link(notify, 'ReturnValue', bypass, 'B')
    owner = g.call(cls(BASE) + ':GetInteractor', 1200, 1800)
    bag = g.get('Inventory', 1500, 1800, class_path='/Game/FoA/Gameplay/BPC_Interactor.BPC_Interactor_C')
    g.link(owner, 'Interactor', bag, 'self')
    full = g.call('/Game/FoA/Gameplay/BPC_Inventory.BPC_Inventory_C:IsFull', 1800, 1800); g.link(bag, 'Inventory', full, 'self')
    space = g.call(K + 'Not_PreBool', 2100, 1800); g.link(full, 'bFull', space, 'A')
    noitem = g.call(K + 'EqualEqual_NameName', 1500, 2100, B='None'); g.link(b, field(b, 'Give'), noitem, 'A')
    capacity = g.call(K + 'BooleanOR', 2400, 1800)
    g.link(space, 'ReturnValue', capacity, 'A'); g.link(noitem, 'ReturnValue', capacity, 'B')
    safe = g.call(K + 'BooleanAND', 2400, 640)
    g.link(capacity, 'ReturnValue', safe, 'A'); g.link(allowed, 'ReturnValue', safe, 'B')
    final = g.call(K + 'BooleanOR', 2700, 240)
    g.link(bypass, 'ReturnValue', final, 'A')
    if 'IsDressingBlocked' in [str(n) for n in BEL.list_graph_names(unreal.load_asset(BASE))]:
        dressing = g.call(cls(BASE) + ':IsDressingBlocked', 2100, 2400); g.link(e, 'Row', dressing, 'Row')
        dressed = g.call(K + 'Not_PreBool', 2400, 2400); g.link(dressing, 'Blocked', dressed, 'A')
        permitted_dressing = g.call(K + 'BooleanAND', 2700, 2100)
        g.link(dressed, 'ReturnValue', permitted_dressing, 'A'); g.link(safe, 'ReturnValue', permitted_dressing, 'B')
        g.link(permitted_dressing, 'ReturnValue', final, 'B')
        comment(g, 'Dress before the first key attempt', [dressing, dressed, permitted_dressing])
    else:
        g.link(safe, 'ReturnValue', final, 'B')
    ret = g.at(result_node(g), 3000, 0)
    g.exec_chain(cast, ret); g.link(final, 'ReturnValue', ret, 'Allowed')
    fail = g.at(g.ed.add_return_node(), 3000, -200)
    g.link(cast, 'CastFailed', fail, 'execute'); g.link(bypass, 'ReturnValue', fail, 'Allowed')
    comment(g, 'Choose the required step', [b, noevent, key, required, level, flag, known, enough, shortcut, permitted])
    comment(g, 'Preserve look and notifications', [look, notify, bypass, pending, free, morning, ready, allowed, final])
    compile_save(BASE)


def guard():
    g = Graph(BASE, 'ApplyRow')
    if not any(BEL.get_node_title(n).splitlines()[0] == 'CanApplyProgressionRow' for n in g.ed.list_all_nodes()):
        e = entry_node(g)
        allow = g.call(cls(BASE) + ':CanApplyProgressionRow', -520, 220)
        g.link(e, 'Row', allow, 'Row')
        branch = g.branch(-260, 0)
        g.link(allow, 'Allowed', branch, 'Condition')
        prepend(g, branch)
        inter = g.call(cls(BASE) + ':GetInteractor', -520, -420)
        say = g.call('/Game/FoA/Gameplay/BPC_Interactor.BPC_Interactor_C:Narrate', -260, -300,
                     Line='One thing at a time. Look around first.')
        g.link(inter, 'Interactor', say, 'self'); g.link(branch, 'else', say, 'execute')
        comment(g, 'Check before changing anything', [allow, branch, inter, say])
    g = Graph(BASE, 'CanInteract')
    if not any(BEL.get_node_title(n).splitlines()[0] == 'CanApplyProgressionRow' for n in g.ed.list_all_nodes()):
        resolve = next(n for n in g.ed.list_all_nodes() if BEL.get_node_title(n).splitlines()[0] == 'Resolve')
        ret = result_node(g)
        original = list(PIN.list_connected_pins(Graph.pin(ret, 'bCanInteract', 'in')))
        assert len(original) == 1
        allow = g.call(cls(BASE) + ':CanApplyProgressionRow', 520, 260)
        both = g.call(K + 'BooleanAND', 800, 220)
        g.link(resolve, 'Row', allow, 'Row')
        PIN.break_pin_links(Graph.pin(ret, 'bCanInteract', 'in'))
        assert PIN.try_create_connection(original[0], Graph.pin(both, 'A', 'in'))
        g.link(allow, 'Allowed', both, 'B'); g.link(both, 'ReturnValue', ret, 'bCanInteract')
        comment(g, 'Offer only available actions', [allow, both])
    compile_save(BASE)


def report_gate():
    g = Graph.function(GI, 'CanReportInteractionEvent', inputs=[('Event', ptype('name'))], outputs=[('Allowed', ptype('bool'))], pure=True)
    e = g.at(entry_node(g), 0, 0)
    stage = g.get('InteractionStage', 0, 220)
    needed = g.get('InteractionEventStages', 0, 440)
    threshold = g.call('/Script/Engine.BlueprintMapLibrary:Map_Find', 300, 440)
    g.link(needed, 'InteractionEventStages', threshold, 'TargetMap'); g.link(e, 'Event', threshold, 'Key')
    enough = g.call(K + 'GreaterEqual_IntInt', 600, 220)
    g.link(stage, 'InteractionStage', enough, 'A'); g.link(threshold, 'Value', enough, 'B')
    flags = g.get('InteractionEventShortcuts', 0, 800)
    flag = g.call('/Script/Engine.BlueprintMapLibrary:Map_Find', 300, 800)
    g.link(flags, 'InteractionEventShortcuts', flag, 'TargetMap'); g.link(e, 'Event', flag, 'Key')
    known = g.call(cls(GI) + ':HasKnowledge', 600, 800); g.link(flag, 'Value', known, 'Flag')
    shortcut = g.call(K + 'BooleanAND', 900, 800)
    g.link(flag, 'ReturnValue', shortcut, 'A'); g.link(known, 'Known', shortcut, 'B')
    morning = g.call(K + 'GreaterEqual_IntInt', 600, 1100, B=2); g.link(stage, 'InteractionStage', morning, 'A')
    legalshortcut = g.call(K + 'BooleanAND', 1200, 800)
    g.link(shortcut, 'ReturnValue', legalshortcut, 'A'); g.link(morning, 'ReturnValue', legalshortcut, 'B')
    progress = g.call(K + 'BooleanOR', 1500, 440)
    g.link(enough, 'ReturnValue', progress, 'A'); g.link(legalshortcut, 'ReturnValue', progress, 'B')
    unknown = g.call(K + 'Not_PreBool', 900, 440); g.link(threshold, 'ReturnValue', unknown, 'A')
    allowed = g.call(K + 'BooleanOR', 1800, 220)
    g.link(progress, 'ReturnValue', allowed, 'A'); g.link(unknown, 'ReturnValue', allowed, 'B')
    ret = g.at(result_node(g), 2100, 0); g.exec_chain(e, ret); g.link(allowed, 'ReturnValue', ret, 'Allowed')
    comment(g, 'Knowledge permits the shortcut', list(g.ed.list_all_nodes()))
    compile_save(GI)


def report_hook():
    inter = '/Game/FoA/Gameplay/BPC_Interactor'
    g = Graph(inter, 'Report')
    if not any(BEL.get_node_title(n).splitlines()[0] == 'CanReportInteractionEvent' for n in g.ed.list_all_nodes()):
        gi = g.call(GS + 'GetGameInstance', -900, 350)
        cast = g.node(palette(g, 'CastToGI_FoA'), -600, 0); g.link(gi, 'ReturnValue', cast, 'Object')
        allow = g.call(cls(GI) + ':CanReportInteractionEvent', -300, 350)
        g.link(cast, 'AsGI_FoA', allow, 'self'); g.link(entry_node(g), 'Event', allow, 'Event')
        branch = g.branch(-300, 0); g.link(allow, 'Allowed', branch, 'Condition')
        prepend(g, cast, branch); g.exec_chain(cast, branch)
        comment(g, 'Report the action in order', [gi, cast, allow, branch])
    compile_save(inter)


def contact():
    inter = '/Game/FoA/Gameplay/BPC_Interactor.BPC_Interactor_C'
    inv = '/Game/FoA/Gameplay/BPC_Inventory.BPC_Inventory_C'
    actor = '/Script/Engine.Actor:'
    ksl = '/Script/Engine.KismetSystemLibrary:'
    notify_contact = (unreal.load_asset('/Game/FoA/Gameplay/AN_FoA_InteractionContact') is not None and
                      'OnPendingContact' in [str(n) for n in BEL.list_graph_names(unreal.load_asset(BASE))])

    def build(name):
        g = Graph.function(BASE, name)
        e = g.at(entry_node(g), 0, 0)
        return g, e

    def row_break(g, node, pin='Row', x=0, y=240):
        b = g.node(palette(g, 'Break', 'S_Interaction'), x, y)
        g.link(node, pin, b, 'S_Interaction')
        return b

    def pending_row(g, x, y):
        return g.get('PendingRow', x, y)

    # The original transaction, with animation removed because it has already reached its contact point.
    g, e = build('CommitInteractionRow')
    b = row_break(g, e)
    who = g.call(cls(BASE) + ':GetInteractor', 0, 1000)
    state = g.call(cls(BASE) + ':SetState', 360, 0, bInstant=False)
    g.link(b, field(b, 'NextState'), state, 'NewState')
    say = g.call(inter + ':Narrate', 660, 0); g.link(who, 'Interactor', say, 'self')
    g.link(b, field(b, 'Line'), say, 'Line')
    bag = g.get('Inventory', 660, 800, class_path=inter); g.link(who, 'Interactor', bag, 'self')
    give = g.call(inv + ':Add', 960, 0); g.link(bag, 'Inventory', give, 'self'); g.link(b, field(b, 'Give'), give, 'Item')
    use = g.call(inv + ':UseUp', 1260, 0); g.link(bag, 'Inventory', use, 'self'); g.link(b, field(b, 'Item'), use, 'Item')
    report = g.call(inter + ':Report', 1560, 0); g.link(who, 'Interactor', report, 'self')
    g.link(b, field(b, 'Event'), report, 'Event')
    used = g.node(palette(g, 'Call', 'OnUsed'), 1860, 0)
    selfnode = g.node(palette(g, 'Get a reference to self'), 1560, 1000)
    out = next(str(PIN.get_pin_name(p)) for p in BEL.list_output_pins(selfnode))
    g.link(selfnode, out, used, 'Interactable'); g.link(b, field(b, 'Verb'), used, 'Verb')
    current = g.get('State', 1560, 800); g.link(current, 'State', used, 'NewState')
    g.exec_chain(e, state, say, give, use, report, used)
    comment(g, 'Commit at the contact', list(g.ed.list_all_nodes()))
    compile_save(BASE)

    # Start the original row montage first; pause interaction scanning while its hands are occupied.
    g, e = build('BeginPendingRow')
    b = row_break(g, e)
    row = g.set('PendingRow', 300, 0); g.link(e, 'Row', row, 'PendingRow')
    active = g.set('bPendingRow', 600, 0); g.default(active, 'bPendingRow', True)
    who = g.call(cls(BASE) + ':GetInteractor', 600, 900)
    suspend = g.call(inter + ':SetSuspended', 900, 0, bSuspended=True); g.link(who, 'Interactor', suspend, 'self')
    load = g.call(ksl + 'LoadAsset_Blocking', 1200, 0); g.link(b, field(b, 'Montage'), load, 'Asset')
    cast = g.node(palette(g, 'CastToAnimMontage'), 1500, 0); g.link(load, 'ReturnValue', cast, 'Object')
    montage = g.set('PendingMontage', 1800, 0); g.link(cast, 'AsAnimMontage', montage, 'PendingMontage')
    play = g.call(inter + ':PlayRowMontage', 2100, 0); g.link(who, 'Interactor', play, 'self')
    g.link(b, field(b, 'Montage'), play, 'Montage')
    name = g.call(ksl + 'GetObjectName', 1800, 600); g.link(cast, 'AsAnimMontage', name, 'Object')
    asname = g.call('/Script/Engine.KismetStringLibrary:Conv_StringToName', 2100, 600)
    g.link(name, 'ReturnValue', asname, 'InString')
    timings = g.get('ContactTimes', 1800, 1000)
    find = g.call('/Script/Engine.BlueprintMapLibrary:Map_Find', 2400, 600)
    g.link(timings, 'ContactTimes', find, 'TargetMap'); g.link(asname, 'ReturnValue', find, 'Key')
    duration = g.call('/Script/Engine.AnimSequenceBase:GetPlayLength', 2100, 1000)
    g.link(cast, 'AsAnimMontage', duration, 'self')
    fallback = g.call(K + 'Multiply_DoubleDouble', 2400, 1000, B=0.85); g.link(duration, 'ReturnValue', fallback, 'A')
    seconds = g.call(K + 'SelectFloat', 2700, 600)
    g.link(find, 'Value', seconds, 'A'); g.link(fallback, 'ReturnValue', seconds, 'B')
    g.link(find, 'ReturnValue', seconds, 'bPickA')
    timer = g.call(ksl + 'K2_SetTimer', 3000, 0, FunctionName='FinishPendingRow', bLooping=False)
    if notify_contact:
        watchdog = g.call(K + 'Add_DoubleDouble',2700,1300,B=.2)
        g.link(duration,'ReturnValue',watchdog,'A');g.link(watchdog,'ReturnValue',timer,'Time')
    else:g.link(seconds, 'ReturnValue', timer, 'Time')
    cancel = g.call(cls(BASE) + ':CancelPendingRow', 1800, -300, bRestoreScan=True)
    if notify_contact:
        owner = g.set('PendingContactActor',750,0,class_path=inter);g.link(who,'Interactor',owner,'self')
        selfnode = g.node(palette(g,'Get a reference to self'),750,1250)
        selfpin = next(str(PIN.get_pin_name(p)) for p in BEL.list_output_pins(selfnode))
        g.link(selfnode,selfpin,owner,'PendingContactActor')
        g.exec_chain(e,row,active,owner,load,cast,montage,play,suspend,timer)
    else:g.exec_chain(e, row, active, load, cast, montage, play, suspend, timer)
    g.link(cast, 'CastFailed', cancel, 'execute')
    comment(g, 'Reach before taking anything', [row, active, who, suspend, load, cast, montage, play, cancel])
    comment(g, 'Use the authored contact', [name, asname, timings, find, duration, fallback, seconds, timer])
    compile_save(BASE)

    g, e = build('FinishPendingRow')
    active = g.get('bPendingRow', 0, 240); branch = g.branch(300, 0)
    g.link(active, 'bPendingRow', branch, 'Condition'); g.exec_chain(e, branch)
    pawn = g.call(GS + 'GetPlayerCharacter', 300, 400, PlayerIndex=0)
    current = g.call('/Script/Engine.Character:GetCurrentMontage', 600, 400); g.link(pawn, 'ReturnValue', current, 'self')
    expected = g.get('PendingMontage', 600, 600)
    same = g.call(K + 'EqualEqual_ObjectObject', 900, 400)
    g.link(current, 'ReturnValue', same, 'A'); g.link(expected, 'PendingMontage', same, 'B')
    reached = g.branch(1200, 0); g.link(same, 'ReturnValue', reached, 'Condition')
    g.link(branch, 'then', reached, 'execute')
    off = g.set('bPendingRow', 1500, 0); g.default(off, 'bPendingRow', False)
    who = g.call(cls(BASE) + ':GetInteractor', 1500, 600)
    resume = g.call(inter + ':SetSuspended', 1800, 0, bSuspended=False); g.link(who, 'Interactor', resume, 'self')
    commit = g.call(cls(BASE) + ':CommitInteractionRow', 2100, 0)
    pr = pending_row(g, 1800, 600); g.link(pr, 'PendingRow', commit, 'Row')
    cancel = g.call(cls(BASE) + ':CancelPendingRow', 1500, -300, bRestoreScan=True)
    g.exec_chain(reached, off, resume, commit); g.link(reached, 'else', cancel, 'execute')
    comment(g, 'Interrupted means nothing taken', list(g.ed.list_all_nodes()))
    compile_save(BASE)
    if notify_contact:
        # Actual animation notification owns commit; this is cleanup only.
        g,e=build('FinishPendingRow')
        cancel=g.call(cls(BASE)+':CancelPendingRow',300,0,bRestoreScan=True)
        g.exec_chain(e,cancel);compile_save(BASE)

    g, e = build('CancelPendingRow')
    active = g.get('bPendingRow', 0, 200); branch = g.branch(300, 0)
    g.link(active, 'bPendingRow', branch, 'Condition'); g.exec_chain(e, branch)
    clear = g.call(ksl + 'K2_ClearTimer', 600, 0, FunctionName='FinishPendingRow')
    off = g.set('bPendingRow', 900, 0); g.default(off, 'bPendingRow', False)
    restore = g.branch(1200, 0); g.link(e, 'bRestoreScan', restore, 'Condition')
    who = g.call(cls(BASE) + ':GetInteractor', 1200, 500)
    resume = g.call(inter + ':SetSuspended', 1500, 0, bSuspended=False); g.link(who, 'Interactor', resume, 'self')
    if notify_contact:
        owner=g.set('PendingContactActor',1000,0,class_path=inter);g.link(who,'Interactor',owner,'self')
        g.exec_chain(branch,clear,off,owner,restore,resume)
    else:g.exec_chain(branch, clear, off, restore, resume)
    comment(g, 'Cancel the uncommitted row', list(g.ed.list_all_nodes()))
    compile_save(BASE)

    # Replace only this function. Look/Notify/no-animation rows remain immediate.
    g, e = build('ApplyRow')
    b = row_break(g, e)
    allow = g.call(cls(BASE) + ':CanApplyProgressionRow', 300, 240); g.link(e, 'Row', allow, 'Row')
    permitted = g.branch(600, 0); g.link(allow, 'Allowed', permitted, 'Condition'); g.exec_chain(e, permitted)
    valid = g.call(ksl + 'IsValidSoftObjectReference', 900, 240); g.link(b, field(b, 'Montage'), valid, 'SoftObjectReference')
    look = g.call(K + 'EqualEqual_NameName', 900, 440, B='Look'); g.link(b, field(b, 'Verb'), look, 'A')
    notify = g.call(K + 'EqualEqual_NameName', 900, 600, B='Notify'); g.link(b, field(b, 'Verb'), notify, 'A')
    bypass = g.call(K + 'BooleanOR', 1200, 440)
    g.link(look, 'ReturnValue', bypass, 'A'); g.link(notify, 'ReturnValue', bypass, 'B')
    work = g.call(K + 'Not_PreBool', 1500, 440); g.link(bypass, 'ReturnValue', work, 'A')
    timed = g.call(K + 'BooleanAND', 1800, 240)
    g.link(valid, 'ReturnValue', timed, 'A'); g.link(work, 'ReturnValue', timed, 'B')
    hasmontage = g.branch(2100, 0); g.link(timed, 'ReturnValue', hasmontage, 'Condition')
    begin = g.call(cls(BASE) + ':BeginPendingRow', 2400, 0); g.link(e, 'Row', begin, 'Row')
    commit = g.call(cls(BASE) + ':CommitInteractionRow', 2400, -300); g.link(e, 'Row', commit, 'Row')
    g.exec_chain(permitted, hasmontage, begin); g.link(hasmontage, 'else', commit, 'execute')
    comment(g, 'Animation before the result', list(g.ed.list_all_nodes()))
    # Retain every wardrobe/reset hook already installed by another lane.
    g = Graph(BASE)
    if not any(BEL.get_node_title(n).splitlines()[0] == 'CancelPendingRow' for n in g.ed.list_all_nodes()):
        reset = next(n for n in g.ed.list_all_nodes() if 'ResetForNewDay' in BEL.get_node_title(n).replace(' ', ''))
        old = list(PIN.list_connected_pins(BEL.find_then_pin(reset))); assert len(old) == 1
        cancel = g.call(cls(BASE) + ':CancelPendingRow', -320, 1000, bRestoreScan=False)
        PIN.break_pin_links(BEL.find_then_pin(reset)); g.exec_chain(reset, cancel)
        assert PIN.try_create_connection(BEL.find_then_pin(cancel), old[0])
    compile_save(BASE)


if phase == 'declare':
    declaration()
elif phase == 'flow':
    flow()
elif phase == 'gate':
    gate()
elif phase == 'guard':
    guard()
elif phase == 'contact':
    contact()
elif phase == 'report_gate':
    report_gate()
elif phase == 'report_hook':
    report_hook()
elif phase == 'contact_defaults':
    contacts = {}
    for name, wanted in (('AM_FoA_PickUp_Floor', 'Grab'), ('AM_FoA_PickUp_Table', 'Grab'),
                         ('AM_FoA_OpenDrawer', 'Grip'), ('AM_FoA_TryLockedHandle', 'Locked'),
                         ('AM_FoA_KneelScrewdriver', 'WorkDone')):
        montage = unreal.load_asset('/Game/FoA/Characters/Player/Montages/' + name)
        for event in unreal.AnimationLibrary.get_animation_notify_events(montage):
            notify = event.get_editor_property('notify')
            if isinstance(notify,unreal.AnimNotify_PlayMontageNotify) and str(notify.get_editor_property('notify_name')) == wanted:
                contacts[unreal.Name(name)] = unreal.AnimationLibrary.get_anim_notify_event_trigger_time(event)
    assert len(contacts) == 5
    bp = unreal.load_asset(BASE)
    unreal.get_default_object(bp.generated_class()).set_editor_property('ContactTimes', contacts)
    assert unreal.EditorAssetLibrary.save_loaded_asset(bp, False)
    print('Five authored contact times saved', contacts)
else:
    raise ValueError(phase)
