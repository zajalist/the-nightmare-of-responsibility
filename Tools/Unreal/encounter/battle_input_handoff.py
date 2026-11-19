"""Fix proven pause/resume ownership: UI releases its own lock, then returns to the existing battle widget.

Short asset leases; run stubs, Hayba compile both assets, encounter, frontend, then Hayba compile/save both.
Edits the existing FocusUI/Resume/EnterGameplay links in place; never rebuilds menus or stages a new encounter.
"""
import os

import unreal

exec(open('P:/FoA/Tools/Unreal/encounter/enc_graph.py', encoding='utf-8').read())
BP = f'{ENC}/BP_Encounter'
BC = BP + '.BP_Encounter_C'
FE = '/Game/FoA/UI/Framework/BP_FoAFrontEnd'
WB = f'{ENC}/WBP_Encounter'
WC = WB + '.WBP_Encounter_C'
T = BEL.get_basic_type_by_name
PHASE = os.environ.get('FOA_PHASE', 'stubs')


def find(g, title):
    nodes = [n for n in g.ed.list_all_nodes()
             if event_key(BEL.get_node_title(n).splitlines()[0]) == event_key(title)]
    assert len(nodes) == 1, (title, [BEL.get_node_title(n) for n in nodes])
    return nodes[0]


def replace(g, old, new):
    incoming = list(PIN.list_connected_pins(BEL.find_execute_pin(old)))
    outgoing = list(PIN.list_connected_pins(BEL.find_then_pin(old)))
    assert len(incoming) == 1
    PIN.break_pin_links(BEL.find_execute_pin(old))
    PIN.break_pin_links(BEL.find_then_pin(old))
    wire(incoming[0], BEL.find_execute_pin(new))
    for pin in outgoing:
        wire(BEL.find_then_pin(new), pin)
    g.ed.remove_nodes([old])


def save(path):
    assert unreal.EditorAssetLibrary.save_asset(path, only_if_is_dirty=False), path


for path in (BP, FE):
    unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(unreal.load_asset(path))
unreal.get_editor_subsystem(unreal.EditorActorSubsystem).select_nothing()

if PHASE == 'stubs':
    ensure_vars_nc(FE, [('bUIOwnsInputLocks', T('bool'), 'false', 'Front End|State', False)])
    stub_functions(FE, {name: ((), (), False) for name in ('AcquireUIInput', 'ReleaseUIInput', 'RestoreGameplayOwner')})
    stub_functions(BP, {'RestoreBattleInput': ((), (), False)})
    save(BP)
    save(FE)
    print('input ownership stubs saved; compile both through Hayba')

elif PHASE == 'encounter':
    g, e, _ = new_function(BP, 'RestoreBattleInput')
    g.at(e, 0, 0)
    widget = mget(g, 'Widget', 0, 260)
    valid = fcall(g, f'{KSL}:IsValid', 220, 300, Object=widget)
    active = fcall(g, f'{KML}:BooleanAND', 460, 300, A=mget(g, 'bActive', 220, 500), B=valid)
    br = g.at(g.ed.add_branch_node(), 700, 0)
    wire(po(active), BEL.find_condition_pin(br))
    pc = fcall(g, f'{GS}:GetPlayerController', 700, 420, PlayerIndex=0)
    mode = fcall(g, f'{UWBL}:SetInputMode_GameAndUIEx', 1000, 0, PlayerController=pc,
                 InWidgetToFocus=widget, bHideCursorDuringCapture='false')
    cursor = fcall(g, '/Script/Engine.PlayerController:SetShowMouseCursor', 1320, 0, self=pc, bShowMouseCursor='true')
    cast = make(g, 1640, 0, 'CastToWBP_Encounter')
    wire(po(widget), pi(cast, 'Object'))
    focus = g.at(g.ed.add_set_member_variable_node('bCommandFocus', WC), 1960, 0)
    feed(focus, self=as_pin(cast), bCommandFocus='false')
    redraw = fcall(g, f'{WC}:RefreshBattlePresentation', 2280, 0, self=as_pin(cast))
    chain(e, br, mode, cursor, cast, focus, redraw)
    box(g, 'Resume the existing battle', '', g.ed.list_all_nodes(), 'stage')
    save(BP)
    print('RestoreBattleInput: existing widget/focus only; no counter changes, no staging')

elif PHASE == 'frontend':
    for name, acquire in (('AcquireUIInput', True), ('ReleaseUIInput', False)):
        g, e, _ = new_function(FE, name)
        g.at(e, 0, 0)
        owned = mget(g, 'bUIOwnsInputLocks', 0, 280)
        condition = fcall(g, f'{KML}:Not_PreBool', 220, 280, A=owned) if acquire else owned
        br = g.at(g.ed.add_branch_node(), 460, 0)
        wire(po(condition), BEL.find_condition_pin(br))
        pc = fcall(g, f'{GS}:GetPlayerController', 460, 360, PlayerIndex=0)
        move = fcall(g, '/Script/Engine.Controller:SetIgnoreMoveInput', 780, 0, self=pc,
                     bNewMoveInput=str(acquire).lower())
        look = fcall(g, '/Script/Engine.Controller:SetIgnoreLookInput', 1100, 0, self=pc,
                     bNewLookInput=str(acquire).lower())
        flag = mset(g, 'bUIOwnsInputLocks', 1420, 0, str(acquire).lower())
        chain(e, br, move, look, flag)
        box(g, 'UI owns one lock', '', g.ed.list_all_nodes(), 'entry')

    g, e, _ = new_function(FE, 'RestoreGameplayOwner')
    g.at(e, 0, 0)
    enc = fcall(g, f'{GS}:GetActorOfClass', 300, 0, ActorClass=BC)
    valid = g.at(g.ed.add_branch_node(), 620, 0)
    wire(po(fcall(g, f'{KSL}:IsValid', 400, 300, Object=enc)), BEL.find_condition_pin(valid))
    active = g.at(g.ed.add_branch_node(), 940, 0)
    wire(po(field(g, enc, 'bActive', BC, 700, 360)), BEL.find_condition_pin(active))
    restore = fcall(g, f'{BC}:RestoreBattleInput', 1260, 0, self=enc)
    seq(e, enc, valid)
    chain(valid, active, restore)
    box(g, 'Return to the input owner', '', g.ed.list_all_nodes(), 'stage')

    g = Graph(FE, 'FocusUI')
    if not any(event_key(BEL.get_node_title(n).splitlines()[0]) == 'acquireuiinput' for n in g.ed.list_all_nodes()):
        move, look = find(g, 'SetIgnoreMoveInput'), find(g, 'SetIgnoreLookInput')
        incoming = list(PIN.list_connected_pins(BEL.find_execute_pin(move)))
        outgoing = list(PIN.list_connected_pins(BEL.find_then_pin(look)))
        assert len(incoming) == 1
        pos = BEL.get_node_pos(move)
        own = fcall(g, self_call(FE, 'AcquireUIInput'), pos.x, pos.y)
        PIN.break_pin_links(BEL.find_execute_pin(move))
        PIN.break_pin_links(BEL.find_then_pin(look))
        wire(incoming[0], BEL.find_execute_pin(own))
        for pin in outgoing:
            wire(BEL.find_then_pin(own), pin)
        g.ed.remove_nodes([move, look])
    for name in ('EnterGameplay', 'Resume'):
        g = Graph(FE, name)
        old = [n for n in g.ed.list_all_nodes() if event_key(BEL.get_node_title(n).splitlines()[0]) == 'resetignoreinputflags']
        if old:
            assert len(old) == 1
            pos = BEL.get_node_pos(old[0])
            release = fcall(g, self_call(FE, 'ReleaseUIInput'), pos.x, pos.y)
            replace(g, old[0], release)
    g = Graph(FE, 'Resume')
    if not any(event_key(BEL.get_node_title(n).splitlines()[0]) == 'restoregameplayowner' for n in g.ed.list_all_nodes()):
        sound = find(g, 'PlayUISound')
        assert not PIN.list_connected_pins(BEL.find_then_pin(sound)), 'Resume tail changed; inspect before appending'
        pos = BEL.get_node_pos(sound)
        restore = fcall(g, self_call(FE, 'RestoreGameplayOwner'), pos.x + 340, pos.y)
        go(sound, restore)
        box(g, 'Restore battle focus', '', [restore], 'stage')
    save(FE)
    print('Front end input: one owned lock; release only UI count; restore active battle widget on Resume')
else:
    raise AssertionError(PHASE)
