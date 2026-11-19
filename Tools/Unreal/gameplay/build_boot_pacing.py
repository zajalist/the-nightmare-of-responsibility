"""Targeted boot contact, actual-state door prerequisite and existing-level reference.
Phases declare/body/prompt/flow/defaults/bind. Native compile/save after each graph phase.
No new flags duplicate the real boot actor's State and no Base->Player class reference is added.
"""
import json
import os
import unreal
exec(open('P:/FoA/Tools/Unreal/ui/bp_graph.py', encoding='utf-8').read())
BASE = '/Game/FoA/Gameplay/BP_Interactable'
BASE_C = BASE + '.BP_Interactable_C'
DIRECTOR = '/Game/FoA/Gameplay/BP_BeatDirector'
PLAYER = '/Game/FoA/Characters/Player/BP_FoAPlayer.BP_FoAPlayer_C'
K = '/Script/Engine.KismetMathLibrary:'
GS = '/Script/Engine.GameplayStatics:'
ROW = BEL.get_struct_type(unreal.load_asset('/Game/FoA/Gameplay/S_Interaction'))
phase = os.environ.get('FOA_PHASE', 'declare')


def palette(g, *words):
    norm = lambda s: str(s).replace(' ', '').replace('_', '').lower()
    found = [str(n) for n in g.ed.list_available_nodes([]) if all(norm(w) in norm(n) for w in words)]
    assert found, words
    return min(found, key=len)


def field(n, name):
    return next(str(PIN.get_pin_name(p)) for p in BEL.list_output_pins(n) if str(PIN.get_pin_name(p)).split('_')[0] == name)


def box(g, title, nodes):
    c = g.ed.add_comment_to_nodes(title, nodes, 48); BEL.set_comment_color(c, C_LOGIC); house_comment_flags(c)


if phase == 'declare':
    ensure_vars(BASE, [('BootProgressionSource', ptype(unreal.load_class(None, BASE_C)), '', 'Interaction', True)])
    if 'IsDressingBlocked' not in [str(n) for n in BEL.list_graph_names(unreal.load_asset(BASE))]:
        Graph.function(BASE, 'IsDressingBlocked', pure=True, inputs=[('Row', ROW)], outputs=[('Blocked', ptype('bool'))])
    g = Graph.function(BASE, 'GetInteractionState', pure=True, outputs=[('CurrentState', ptype('name'))])
    e = g.at(entry_node(g), 0, 0); value = g.get('State', 0, 250)
    results = list(g.ed.list_nodes_of_class(unreal.K2Node_FunctionResult))
    ret = g.at(results[0] if results else g.ed.add_return_node(), 300, 0)
    g.exec_chain(e, ret); g.link(value, 'State', ret, 'CurrentState')
    # A declaration rerun also removes any interrupted, unsaved body before native compile.
    Graph.function(BASE, 'IsDressingBlocked')
    compile_save(BASE)
elif phase == 'body':
    g = Graph.function(BASE, 'IsDressingBlocked'); e = g.at(entry_node(g), 0, 0)
    row = g.node(palette(g, 'Break', 'S_Interaction'), 0, 300); g.link(e, 'Row', row, 'S_Interaction')
    need = []
    for i, (name, value) in enumerate((('Interactable', 'Door'), ('NextState', 'KeyJammed'), ('Item', 'Key'))):
        n = g.call(K + 'EqualEqual_NameName', 300, 250 + i * 180, B=value)
        g.link(row, field(row, name), n, 'A'); need.append(n)
    both = g.call(K + 'BooleanAND', 600, 300)
    g.link(need[0], 'ReturnValue', both, 'A'); g.link(need[1], 'ReturnValue', both, 'B')
    keyrow = g.call(K + 'BooleanAND', 900, 300)
    g.link(both, 'ReturnValue', keyrow, 'A'); g.link(need[2], 'ReturnValue', keyrow, 'B')
    known = g.call(BASE_C + ':Knows', 600, 800, Flag='Knows.KeySnaps')
    first = g.call(K + 'Not_PreBool', 900, 800); g.link(known, 'bKnows', first, 'A')
    check = g.call(K + 'BooleanAND', 1200, 300)
    g.link(keyrow, 'ReturnValue', check, 'A'); g.link(first, 'ReturnValue', check, 'B')
    choose = g.branch(1500, 0); g.link(check, 'ReturnValue', choose, 'Condition'); g.exec_chain(e, choose)
    peer = g.get('BootProgressionSource', 1200, 1000)
    valid = g.call('/Script/Engine.KismetSystemLibrary:IsValid', 1500, 900); g.link(peer, 'BootProgressionSource', valid, 'Object')
    safe = g.branch(1800, 0); g.link(valid, 'ReturnValue', safe, 'Condition'); g.exec_chain(choose, safe)
    # Python's pin enumeration omits this hidden same-class target. The companion
    # native wire_boot_external_target.py connects it before compile/save.
    state = g.call(BASE_C + ':GetInteractionState', 1800, 500)
    unworn = g.call(K + 'NotEqual_NameName', 2100, 500, B='Worn'); g.link(state, 'CurrentState', unworn, 'A')
    results = list(g.ed.list_nodes_of_class(unreal.K2Node_FunctionResult))
    ret = g.at(results[0] if results else g.ed.add_return_node(), 2400, 0)
    g.exec_chain(safe, ret); g.link(unworn, 'ReturnValue', ret, 'Blocked')
    blocked = g.at(g.ed.add_return_node(), 2400, -250); g.default(blocked, 'Blocked', True); g.link(safe, 'else', blocked, 'execute')
    free = g.at(g.ed.add_return_node(), 1800, -250); g.default(free, 'Blocked', False); g.link(choose, 'else', free, 'execute')
    box(g, 'Read the boots actually worn this morning', list(g.ed.list_all_nodes())); compile_save(BASE)
elif phase == 'prompt':
    g = Graph(BASE, 'GetPrompt')
    if not any(BEL.get_node_title(n).splitlines()[0] == 'IsDressingBlocked' for n in g.ed.list_all_nodes()):
        ret = next(n for n in g.ed.list_nodes_of_class(unreal.K2Node_FunctionResult) if PIN.list_connected_pins(Graph.pin(n, 'Prompt', 'in')))
        original = list(PIN.list_connected_pins(Graph.pin(ret, 'Prompt', 'in'))); assert len(original) == 1
        held = next(n for n in g.ed.list_all_nodes() if BEL.get_node_title(n).splitlines()[0] == 'GetHeld')
        row = g.call(BASE_C + ':Resolve', 1300, 650, Verb='Use'); g.link(held, 'Item', row, 'Held')
        block = g.call(BASE_C + ':IsDressingBlocked', 1600, 650); g.link(row, 'Row', block, 'Row')
        choose = g.call(K + 'SelectText', 1900, 500, A='Put on the boots before trying the key.')
        g.link(block, 'Blocked', choose, 'bPickA')
        assert PIN.try_create_connection(original[0], Graph.pin(choose, 'B', 'in'))
        PIN.break_pin_links(Graph.pin(ret, 'Prompt', 'in')); g.link(choose, 'ReturnValue', ret, 'Prompt')
        box(g, 'Explain the missing step', [row, block, choose])
    compile_save(BASE)
elif phase == 'flow':
    g = Graph(DIRECTOR, 'ReportEvent')
    if not any(BEL.get_node_title(n).splitlines()[0] == 'SetBootsWorn' for n in g.ed.list_all_nodes()):
        e = entry_node(g); old = list(PIN.list_connected_pins(BEL.find_then_pin(e))); assert len(old) == 1
        iswear = g.call(K + 'EqualEqual_NameName', -1200, 300, B='BootsWorn'); g.link(e, 'Event', iswear, 'A')
        branch = g.branch(-900, 0); g.link(iswear, 'ReturnValue', branch, 'Condition')
        pawn = g.call(GS + 'GetPlayerCharacter', -900, 600, PlayerIndex=0)
        cast = g.node(palette(g, 'CastToBP_FoAPlayer'), -600, -250); g.link(pawn, 'ReturnValue', cast, 'Object')
        wear = g.call(PLAYER + ':SetBootsWorn', -300, -250, bEnable=True); g.link(cast, 'AsBP_FoAPlayer', wear, 'self')
        PIN.break_pin_links(BEL.find_then_pin(e)); g.exec_chain(e, branch, cast, wear)
        assert PIN.try_create_connection(Graph.pin(branch, 'else', 'out'), old[0])
        box(g, 'Wear only after dressing contact', [iswear, branch, pawn, cast, wear])
    compile_save(DIRECTOR)
elif phase == 'defaults':
    # Preserve every existing row name, icon, unrelated row and map entry.
    table = unreal.load_asset('/Game/FoA/Gameplay/DT_Interactions')
    rows = json.loads(unreal.DataTableFunctionLibrary.export_data_table_to_json_string(table))
    import sys
    sys.path.insert(0, 'P:/FoA/Tools/Unreal/gameplay')
    import importlib, data_rows
    importlib.reload(data_rows)
    source = [r for r in data_rows.INTERACTIONS if r['Interactable'] == 'Boot_L']
    for wanted in source:
        found = [r for r in rows if all(str(r[k]) == wanted[k] for k in ('Interactable', 'State', 'Verb', 'Item'))]
        assert len(found) <= 1, wanted
        if found:
            found[0].update(wanted)
        else:
            rows.append(dict(wanted, Name='BootWear_' + wanted['State'] + '_' + wanted['Verb']))
    assert unreal.DataTableFunctionLibrary.fill_data_table_from_json_string(table, json.dumps(rows))
    assert unreal.EditorAssetLibrary.save_loaded_asset(table, False)
    bp = unreal.load_asset(BASE); cdo = unreal.get_default_object(bp.generated_class())
    stages = dict(cdo.get_editor_property('RequiredStages')); stages[unreal.Name('BootsWorn')] = 4
    cdo.set_editor_property('RequiredStages', stages)
    assert unreal.EditorAssetLibrary.save_loaded_asset(bp, False)
elif phase == 'bind':
    base = unreal.load_class(None, BASE_C)
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    actors = unreal.GameplayStatics.get_all_actors_of_class(world, base)
    found = {}
    for a in actors:
        key = str(a.get_editor_property('InteractionKey'))
        if key in ('Boot_L', 'Door'):
            assert key not in found, key
            found[key] = a
    assert set(found) == {'Boot_L', 'Door'}, found
    found['Door'].set_editor_property('BootProgressionSource', found['Boot_L'])
    assert found['Door'].get_editor_property('BootProgressionSource') == found['Boot_L']
    assert unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    print('Door prerequisite bound to actual Boot_L state')
else:
    raise ValueError(phase)
