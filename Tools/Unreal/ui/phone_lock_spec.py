"""Phone lock screen to story's spec (script.md section 3 "Lock screen", main 2026-11-09), WBP_Phone in place (Hayba):
  clock    6:40 at the first open each morning, then 6:40 + whole REAL minutes since that open, capped at 9:59. A new
           morning (BeatIndex going backwards: a new or restarted day) starts again at 6:40. Txt_Clock and the status
           bar's Txt_StatusTime show the same time. ClockDebugMin (default 0) is a proof-only offset (pie_call PHONEMIN).
  previews MessagePreview(Index) is the one source for the inbox rows (Txt_Sender0/1) and the lock banners
           (Txt_Notif0/1Head/Body): BeatIndex >= 3 switches both at once, Mom first (the newest).
  dates    "Day 18" / "17 days crossed out" are untouched.
Order matters: blueprint_graph_batch is not atomic, so every variable and function a batch reads is made and compiled
first. Idempotent.
  python Tools/Unreal/ui/phone_lock_spec.py"""
import sys

sys.path.insert(0, 'P:/FoA/Tools/Unreal')
import editor_lock  # noqa: E402
import hayba_call as hc  # noqa: E402

P = '/Game/FoA/UI/Game/WBP_Phone'
PC = f'{P}.WBP_Phone_C'
DIR_C = '/Game/FoA/Gameplay/BP_BeatDirector.BP_BeatDirector_C'
KSL, KML, KTL = '/Script/Engine.KismetSystemLibrary', '/Script/Engine.KismetMathLibrary', '/Script/Engine.KismetTextLibrary'
SETTEXT = '/Script/UMG.TextBlock:SetText'
EARLY = ("Your shirt's in the wardrobe", 'Reminder: today')
LATE = ("Call me when you're out", 'Drop in any weekday, 9 to 4')
WIDGET_VARS = ('Txt_Notif0Head', 'Txt_Notif0Body', 'Txt_Notif1Head', 'Txt_Notif1Body', 'Txt_Sender0', 'Txt_Sender1',
               'Txt_Clock', 'Txt_StatusTime')


def c(cmd, **p):
    r = hc.call(cmd, p)
    d = r.get('data') or {}
    ok = r.get('ok')
    print(cmd, p.get('graph_name') or p.get('function_name') or p.get('variable_name') or '', ok, d.get('applied', ''),
          d.get('failed_index', ''), d.get('error') or r.get('error') or '')
    return r


def graph(g):
    nodes, edges, off = [], [], 0
    while off is not None:
        d = hc.call('blueprint_inspect_graph', {'path': P, 'graph_name': g, 'offset': off})['data']
        nodes += d['nodes']
        off = d['page']['nodes']['next_offset']
    off = 0
    while off is not None:
        d = hc.call('blueprint_inspect_graph', {'path': P, 'graph_name': g, 'edge_offset': off})['data']
        edges += d['edges']
        off = d['page']['edges']['next_offset']
    return nodes, edges


def batch(g, ops):
    # precheck (blueprint_graph_batch is not atomic): every variable this batch reads must already exist
    have = {v.get('name') for v in hc.call('blueprint_get_info', {'path': P})['data'].get('variables', [])}
    widgets = set(WIDGET_VARS)  # flagged as variables below (ui_query's widget list is cut at 50 entries)
    missing = sorted({o['variable_name'] for o in ops if o.get('node_type') in ('variable_get', 'variable_set') and not o.get('class_path')}
                     - have - widgets)
    assert not missing, f'{g}: missing variables {missing}'
    r = c('blueprint_graph_batch', path=P, graph_name=g, ops=ops)
    assert r.get('ok'), f'{g} batch failed: inspect before anything else'


def compile_ok():
    d = hc.call('ui_compile_widget', {'widget_blueprint_path': P})['data']
    assert d.get('compiled_clean'), d
    return d


assert not hc.call('editor_get_state', {})['data']['pie_running'], 'PIE running'
token = editor_lock.acquire('ui', wait_s=300, ttl=120, areas=[P])
try:
    # 1. variables and empty functions, compiled before any batch reads them
    for name, typ, dv in (('ClockOpenT', 'real', '-1.0'), ('ClockLastBeat', 'int', '0'), ('ClockDebugMin', 'real', '0.0')):
        c('blueprint_add_variable', path=P, variable_name=name, variable_type=typ, default_value=dv, category='Phone|Clock',
          update_existing=True)
    funcs = hc.call('blueprint_get_info', {'path': P})['data']['functions']
    if 'MessagePreview' not in funcs:
        c('blueprint_add_function', path=P, function_name='MessagePreview', inputs=[{'name': 'Index', 'type': 'int'}],
          outputs=[{'name': 'Sender', 'type': 'string'}, {'name': 'Preview', 'type': 'string'}], pure=True, const=True)
    for f in ('RefreshPreviews', 'UpdateClock'):
        if f not in funcs:
            c('blueprint_add_function', path=P, function_name=f)
    # the text widgets the functions write must be variables (Txt_Notif* were not: the 23:44 batch stopped there)
    for w in WIDGET_VARS:
        r = c('ui_set_variable', widget_blueprint_path=P, widget_name=w, is_variable=True)
        assert r.get('ok'), w
    compile_ok()

    def fresh(g):
        """The function's nodes; a partial build (nodes but the entry wired to nothing) is cleared first."""
        nodes, edges = graph(g)
        entry = next(n['node_id'] for n in nodes if n['title'] == g)
        extra = [n['node_id'] for n in nodes if n['node_id'] != entry and not n['title'].startswith('Return')]
        if extra and not [e for e in edges if e['from_node'] == entry and e['from_pin'] == 'then']:
            c('blueprint_remove_nodes', path=P, graph_name=g, node_ids=extra)
            nodes, edges = graph(g)
        return nodes

    # 2. MessagePreview: Index 0 Mom, 1 Career Center; the preview switches with BeatIndex >= 3 (the inbox switch)
    nodes, _ = graph('MessagePreview')
    if len(nodes) <= 2:
        entry = next(n['node_id'] for n in nodes if n['title'] == 'MessagePreview')
        ret = next(n['node_id'] for n in nodes if n['title'].startswith('Return'))
        ops = [{'op': 'add_node', 'ref': 'dir', 'node_type': 'variable_get', 'variable_name': 'Director', 'x': 200, 'y': 300},
               {'op': 'add_node', 'ref': 'ok', 'node_type': 'call_function', 'function_name': f'{KSL}:IsValid', 'x': 420, 'y': 380},
               {'op': 'connect', 'from_node': 'dir', 'from_pin': 'Director', 'to_node': 'ok', 'to_pin': 'Object'},
               {'op': 'add_node', 'ref': 'bi', 'node_type': 'variable_get', 'variable_name': 'BeatIndex', 'class_path': DIR_C, 'x': 420, 'y': 260},
               {'op': 'connect', 'from_node': 'dir', 'from_pin': 'Director', 'to_node': 'bi', 'to_pin': 'self'},
               {'op': 'add_node', 'ref': 'ge', 'node_type': 'call_function', 'function_name': f'{KML}:GreaterEqual_IntInt', 'x': 640, 'y': 260},
               {'op': 'connect', 'from_node': 'bi', 'from_pin': 'BeatIndex', 'to_node': 'ge', 'to_pin': 'A'},
               {'op': 'set_pin', 'node_id': 'ge', 'pin_name': 'B', 'value': '3'},
               {'op': 'add_node', 'ref': 'late', 'node_type': 'call_function', 'function_name': f'{KML}:BooleanAND', 'x': 860, 'y': 300},
               {'op': 'connect', 'from_node': 'ok', 'from_pin': 'ReturnValue', 'to_node': 'late', 'to_pin': 'A'},
               {'op': 'connect', 'from_node': 'ge', 'from_pin': 'ReturnValue', 'to_node': 'late', 'to_pin': 'B'},
               {'op': 'add_node', 'ref': 'is0', 'node_type': 'call_function', 'function_name': f'{KML}:EqualEqual_IntInt', 'x': 640, 'y': 0},
               {'op': 'connect', 'from_node': entry, 'from_pin': 'Index', 'to_node': 'is0', 'to_pin': 'A'},
               {'op': 'set_pin', 'node_id': 'is0', 'pin_name': 'B', 'value': '0'},
               {'op': 'add_node', 'ref': 'snd', 'node_type': 'call_function', 'function_name': f'{KML}:SelectString', 'x': 1100, 'y': -120},
               {'op': 'set_pin', 'node_id': 'snd', 'pin_name': 'A', 'value': 'Mom'},
               {'op': 'set_pin', 'node_id': 'snd', 'pin_name': 'B', 'value': 'Career Center'},
               {'op': 'connect', 'from_node': 'is0', 'from_pin': 'ReturnValue', 'to_node': 'snd', 'to_pin': 'bPickA'}]
        for i, (early, late) in enumerate(zip(EARLY, LATE)):
            ops += [{'op': 'add_node', 'ref': f'p{i}', 'node_type': 'call_function', 'function_name': f'{KML}:SelectString', 'x': 1100, 'y': 120 + i * 180},
                    {'op': 'set_pin', 'node_id': f'p{i}', 'pin_name': 'A', 'value': late},
                    {'op': 'set_pin', 'node_id': f'p{i}', 'pin_name': 'B', 'value': early},
                    {'op': 'connect', 'from_node': 'late', 'from_pin': 'ReturnValue', 'to_node': f'p{i}', 'to_pin': 'bPickA'}]
        ops += [{'op': 'add_node', 'ref': 'pv', 'node_type': 'call_function', 'function_name': f'{KML}:SelectString', 'x': 1360, 'y': 200},
                {'op': 'connect', 'from_node': 'p0', 'from_pin': 'ReturnValue', 'to_node': 'pv', 'to_pin': 'A'},
                {'op': 'connect', 'from_node': 'p1', 'from_pin': 'ReturnValue', 'to_node': 'pv', 'to_pin': 'B'},
                {'op': 'connect', 'from_node': 'is0', 'from_pin': 'ReturnValue', 'to_node': 'pv', 'to_pin': 'bPickA'},
                {'op': 'connect', 'from_node': 'snd', 'from_pin': 'ReturnValue', 'to_node': ret, 'to_pin': 'Sender'},
                {'op': 'connect', 'from_node': 'pv', 'from_pin': 'ReturnValue', 'to_node': ret, 'to_pin': 'Preview'},
                {'op': 'comment', 'title': 'Inbox previews, early and from beat 3', 'node_ids': ['dir', 'ok', 'bi', 'ge', 'late', 'is0', 'snd', 'p0', 'p1', 'pv'],
                 'color': [0.12, 0.26, 0.16]},
                {'op': 'fit_comments'}]
        batch('MessagePreview', ops)
        compile_ok()

    # 3. RefreshPreviews: both inbox rows and both lock banners from MessagePreview
    nodes = fresh('RefreshPreviews')
    if len(nodes) <= 1:
        entry = next(n['node_id'] for n in nodes if n['title'] == 'RefreshPreviews')
        ops, prev, x = [], entry, 240
        for i in (0, 1):
            ops += [{'op': 'add_node', 'ref': f'mp{i}', 'node_type': 'call_function', 'function_name': f'{PC}:MessagePreview', 'x': x, 'y': 260},
                    {'op': 'set_pin', 'node_id': f'mp{i}', 'pin_name': 'Index', 'value': str(i)}]
            for k, (widget, pin) in enumerate(((f'Txt_Notif{i}Head', 'Sender'), (f'Txt_Notif{i}Body', 'Preview'))):
                ops += [{'op': 'add_node', 'ref': f'g{i}{k}', 'node_type': 'variable_get', 'variable_name': widget, 'x': x + 200, 'y': 160 + k * 60},
                        {'op': 'add_node', 'ref': f't{i}{k}', 'node_type': 'call_function', 'function_name': f'{KTL}:Conv_StringToText', 'x': x + 200, 'y': 320 + k * 60},
                        {'op': 'connect', 'from_node': f'mp{i}', 'from_pin': pin, 'to_node': f't{i}{k}', 'to_pin': 'InString'},
                        {'op': 'add_node', 'ref': f's{i}{k}', 'node_type': 'call_function', 'function_name': SETTEXT, 'x': x + 420, 'y': 0},
                        {'op': 'connect', 'from_node': f'g{i}{k}', 'from_pin': widget, 'to_node': f's{i}{k}', 'to_pin': 'self'},
                        {'op': 'connect', 'from_node': f't{i}{k}', 'from_pin': 'ReturnValue', 'to_node': f's{i}{k}', 'to_pin': 'InText'},
                        {'op': 'connect', 'from_node': prev, 'from_pin': 'then', 'to_node': f's{i}{k}', 'to_pin': 'execute'}]
                prev, x = f's{i}{k}', x + 320
            # the inbox row: sender on line 1, preview on line 2 (as built)
            ops += [{'op': 'add_node', 'ref': f'row{i}', 'node_type': 'variable_get', 'variable_name': f'Txt_Sender{i}', 'x': x + 200, 'y': 160},
                    {'op': 'add_node', 'ref': f'j{i}', 'node_type': 'call_function', 'function_name': '/Script/Engine.KismetStringLibrary:Concat_StrStr', 'x': x + 200, 'y': 320},
                    {'op': 'add_node', 'ref': f'jn{i}', 'node_type': 'call_function', 'function_name': '/Script/Engine.KismetStringLibrary:Concat_StrStr', 'x': x + 200, 'y': 420},
                    {'op': 'connect', 'from_node': f'mp{i}', 'from_pin': 'Sender', 'to_node': f'jn{i}', 'to_pin': 'A'},
                    {'op': 'set_pin', 'node_id': f'jn{i}', 'pin_name': 'B', 'value': '\n'},
                    {'op': 'connect', 'from_node': f'jn{i}', 'from_pin': 'ReturnValue', 'to_node': f'j{i}', 'to_pin': 'A'},
                    {'op': 'connect', 'from_node': f'mp{i}', 'from_pin': 'Preview', 'to_node': f'j{i}', 'to_pin': 'B'},
                    {'op': 'add_node', 'ref': f'jt{i}', 'node_type': 'call_function', 'function_name': f'{KTL}:Conv_StringToText', 'x': x + 420, 'y': 320},
                    {'op': 'connect', 'from_node': f'j{i}', 'from_pin': 'ReturnValue', 'to_node': f'jt{i}', 'to_pin': 'InString'},
                    {'op': 'add_node', 'ref': f'rs{i}', 'node_type': 'call_function', 'function_name': SETTEXT, 'x': x + 420, 'y': 0},
                    {'op': 'connect', 'from_node': f'row{i}', 'from_pin': f'Txt_Sender{i}', 'to_node': f'rs{i}', 'to_pin': 'self'},
                    {'op': 'connect', 'from_node': f'jt{i}', 'from_pin': 'ReturnValue', 'to_node': f'rs{i}', 'to_pin': 'InText'},
                    {'op': 'connect', 'from_node': prev, 'from_pin': 'then', 'to_node': f'rs{i}', 'to_pin': 'execute'}]
            prev, x = f'rs{i}', x + 640
        ops += [{'op': 'comment', 'title': 'Lock banners and inbox rows from one source', 'node_ids': [o['ref'] for o in ops if o['op'] == 'add_node'],
                 'color': [0.12, 0.26, 0.16]}, {'op': 'fit_comments'}]
        batch('RefreshPreviews', ops)
        compile_ok()

    # 4. UpdateClock: stamp the morning's first open, then 6:40 + whole real minutes, capped at 9:59
    nodes = fresh('UpdateClock')
    if len(nodes) <= 1:
        entry = next(n['node_id'] for n in nodes if n['title'] == 'UpdateClock')
        ops = [{'op': 'add_node', 'ref': 'now', 'node_type': 'call_function', 'function_name': '/Script/Engine.GameplayStatics:GetRealTimeSeconds', 'x': 200, 'y': 300},
               {'op': 'add_node', 'ref': 'dir', 'node_type': 'variable_get', 'variable_name': 'Director', 'x': 200, 'y': 460},
               {'op': 'add_node', 'ref': 'ok', 'node_type': 'call_function', 'function_name': f'{KSL}:IsValid', 'x': 420, 'y': 520},
               {'op': 'connect', 'from_node': 'dir', 'from_pin': 'Director', 'to_node': 'ok', 'to_pin': 'Object'},
               {'op': 'add_node', 'ref': 'bi', 'node_type': 'variable_get', 'variable_name': 'BeatIndex', 'class_path': DIR_C, 'x': 420, 'y': 440},
               {'op': 'connect', 'from_node': 'dir', 'from_pin': 'Director', 'to_node': 'bi', 'to_pin': 'self'},
               {'op': 'add_node', 'ref': 'beat', 'node_type': 'call_function', 'function_name': f'{KML}:SelectInt', 'x': 640, 'y': 460},
               {'op': 'connect', 'from_node': 'bi', 'from_pin': 'BeatIndex', 'to_node': 'beat', 'to_pin': 'A'},
               {'op': 'set_pin', 'node_id': 'beat', 'pin_name': 'B', 'value': '0'},
               {'op': 'connect', 'from_node': 'ok', 'from_pin': 'ReturnValue', 'to_node': 'beat', 'to_pin': 'bPickA'},
               {'op': 'add_node', 'ref': 'ot', 'node_type': 'variable_get', 'variable_name': 'ClockOpenT', 'x': 420, 'y': 200},
               {'op': 'add_node', 'ref': 'unset', 'node_type': 'call_function', 'function_name': f'{KML}:Less_DoubleDouble', 'x': 640, 'y': 200},
               {'op': 'connect', 'from_node': 'ot', 'from_pin': 'ClockOpenT', 'to_node': 'unset', 'to_pin': 'A'},
               {'op': 'set_pin', 'node_id': 'unset', 'pin_name': 'B', 'value': '0.0'},
               {'op': 'add_node', 'ref': 'lb', 'node_type': 'variable_get', 'variable_name': 'ClockLastBeat', 'x': 640, 'y': 560},
               {'op': 'add_node', 'ref': 'back', 'node_type': 'call_function', 'function_name': f'{KML}:Less_IntInt', 'x': 860, 'y': 480},
               {'op': 'connect', 'from_node': 'beat', 'from_pin': 'ReturnValue', 'to_node': 'back', 'to_pin': 'A'},
               {'op': 'connect', 'from_node': 'lb', 'from_pin': 'ClockLastBeat', 'to_node': 'back', 'to_pin': 'B'},
               {'op': 'add_node', 'ref': 'new', 'node_type': 'call_function', 'function_name': f'{KML}:BooleanOR', 'x': 1080, 'y': 300},
               {'op': 'connect', 'from_node': 'unset', 'from_pin': 'ReturnValue', 'to_node': 'new', 'to_pin': 'A'},
               {'op': 'connect', 'from_node': 'back', 'from_pin': 'ReturnValue', 'to_node': 'new', 'to_pin': 'B'},
               {'op': 'add_node', 'ref': 'br', 'node_type': 'branch', 'x': 1300, 'y': 0},
               {'op': 'connect', 'from_node': 'new', 'from_pin': 'ReturnValue', 'to_node': 'br', 'to_pin': 'Condition'},
               {'op': 'connect', 'from_node': entry, 'from_pin': 'then', 'to_node': 'br', 'to_pin': 'execute'},
               {'op': 'add_node', 'ref': 'stamp', 'node_type': 'variable_set', 'variable_name': 'ClockOpenT', 'x': 1540, 'y': -120},
               {'op': 'connect', 'from_node': 'now', 'from_pin': 'ReturnValue', 'to_node': 'stamp', 'to_pin': 'ClockOpenT'},
               {'op': 'connect', 'from_node': 'br', 'from_pin': 'then', 'to_node': 'stamp', 'to_pin': 'execute'},
               {'op': 'add_node', 'ref': 'setlb', 'node_type': 'variable_set', 'variable_name': 'ClockLastBeat', 'x': 1800, 'y': 0},
               {'op': 'connect', 'from_node': 'beat', 'from_pin': 'ReturnValue', 'to_node': 'setlb', 'to_pin': 'ClockLastBeat'},
               {'op': 'connect', 'from_node': 'stamp', 'from_pin': 'then', 'to_node': 'setlb', 'to_pin': 'execute'},
               {'op': 'connect', 'from_node': 'br', 'from_pin': 'else', 'to_node': 'setlb', 'to_pin': 'execute'},
               # minutes = floor((now - ClockOpenT) / 60 + ClockDebugMin); total = min(400 + minutes, 599)
               {'op': 'add_node', 'ref': 'ot2', 'node_type': 'variable_get', 'variable_name': 'ClockOpenT', 'x': 1800, 'y': 300},
               {'op': 'add_node', 'ref': 'el', 'node_type': 'call_function', 'function_name': f'{KML}:Subtract_DoubleDouble', 'x': 2000, 'y': 260},
               {'op': 'connect', 'from_node': 'now', 'from_pin': 'ReturnValue', 'to_node': 'el', 'to_pin': 'A'},
               {'op': 'connect', 'from_node': 'ot2', 'from_pin': 'ClockOpenT', 'to_node': 'el', 'to_pin': 'B'},
               {'op': 'add_node', 'ref': 'per', 'node_type': 'call_function', 'function_name': f'{KML}:Divide_DoubleDouble', 'x': 2200, 'y': 260},
               {'op': 'connect', 'from_node': 'el', 'from_pin': 'ReturnValue', 'to_node': 'per', 'to_pin': 'A'},
               {'op': 'set_pin', 'node_id': 'per', 'pin_name': 'B', 'value': '60.0'},
               {'op': 'add_node', 'ref': 'dbg', 'node_type': 'variable_get', 'variable_name': 'ClockDebugMin', 'x': 2200, 'y': 400},
               {'op': 'add_node', 'ref': 'addm', 'node_type': 'call_function', 'function_name': f'{KML}:Add_DoubleDouble', 'x': 2400, 'y': 300},
               {'op': 'connect', 'from_node': 'per', 'from_pin': 'ReturnValue', 'to_node': 'addm', 'to_pin': 'A'},
               {'op': 'connect', 'from_node': 'dbg', 'from_pin': 'ClockDebugMin', 'to_node': 'addm', 'to_pin': 'B'},
               {'op': 'add_node', 'ref': 'fl', 'node_type': 'call_function', 'function_name': f'{KML}:FFloor', 'x': 2600, 'y': 300},
               {'op': 'connect', 'from_node': 'addm', 'from_pin': 'ReturnValue', 'to_node': 'fl', 'to_pin': 'A'},
               {'op': 'add_node', 'ref': 'tot', 'node_type': 'call_function', 'function_name': f'{KML}:Add_IntInt', 'x': 2800, 'y': 300},
               {'op': 'connect', 'from_node': 'fl', 'from_pin': 'ReturnValue', 'to_node': 'tot', 'to_pin': 'A'},
               {'op': 'set_pin', 'node_id': 'tot', 'pin_name': 'B', 'value': '400'},
               {'op': 'add_node', 'ref': 'cap', 'node_type': 'call_function', 'function_name': f'{KML}:Min', 'x': 3000, 'y': 300},
               {'op': 'connect', 'from_node': 'tot', 'from_pin': 'ReturnValue', 'to_node': 'cap', 'to_pin': 'A'},
               {'op': 'set_pin', 'node_id': 'cap', 'pin_name': 'B', 'value': '599'},
               {'op': 'add_node', 'ref': 'hh', 'node_type': 'call_function', 'function_name': f'{KML}:Divide_IntInt', 'x': 3200, 'y': 220},
               {'op': 'connect', 'from_node': 'cap', 'from_pin': 'ReturnValue', 'to_node': 'hh', 'to_pin': 'A'},
               {'op': 'set_pin', 'node_id': 'hh', 'pin_name': 'B', 'value': '60'},
               {'op': 'add_node', 'ref': 'mm', 'node_type': 'call_function', 'function_name': f'{KML}:Percent_IntInt', 'x': 3200, 'y': 380},
               {'op': 'connect', 'from_node': 'cap', 'from_pin': 'ReturnValue', 'to_node': 'mm', 'to_pin': 'A'},
               {'op': 'set_pin', 'node_id': 'mm', 'pin_name': 'B', 'value': '60'},
               {'op': 'add_node', 'ref': 'ht', 'node_type': 'call_function', 'function_name': f'{KTL}:Conv_IntToText', 'x': 3400, 'y': 220},
               {'op': 'connect', 'from_node': 'hh', 'from_pin': 'ReturnValue', 'to_node': 'ht', 'to_pin': 'Value'},
               {'op': 'set_pin', 'node_id': 'ht', 'pin_name': 'bUseGrouping', 'value': 'false'},
               {'op': 'add_node', 'ref': 'mt', 'node_type': 'call_function', 'function_name': f'{KTL}:Conv_IntToText', 'x': 3400, 'y': 380},
               {'op': 'connect', 'from_node': 'mm', 'from_pin': 'ReturnValue', 'to_node': 'mt', 'to_pin': 'Value'},
               {'op': 'set_pin', 'node_id': 'mt', 'pin_name': 'MinimumIntegralDigits', 'value': '2'},
               {'op': 'set_pin', 'node_id': 'mt', 'pin_name': 'bUseGrouping', 'value': 'false'},
               {'op': 'add_node', 'ref': 'hs', 'node_type': 'call_function', 'function_name': f'{KTL}:Conv_TextToString', 'x': 3600, 'y': 220},
               {'op': 'connect', 'from_node': 'ht', 'from_pin': 'ReturnValue', 'to_node': 'hs', 'to_pin': 'InText'},
               {'op': 'add_node', 'ref': 'ms', 'node_type': 'call_function', 'function_name': f'{KTL}:Conv_TextToString', 'x': 3600, 'y': 380},
               {'op': 'connect', 'from_node': 'mt', 'from_pin': 'ReturnValue', 'to_node': 'ms', 'to_pin': 'InText'},
               {'op': 'add_node', 'ref': 'hc', 'node_type': 'call_function', 'function_name': '/Script/Engine.KismetStringLibrary:Concat_StrStr', 'x': 3800, 'y': 220},
               {'op': 'connect', 'from_node': 'hs', 'from_pin': 'ReturnValue', 'to_node': 'hc', 'to_pin': 'A'},
               {'op': 'set_pin', 'node_id': 'hc', 'pin_name': 'B', 'value': ':'},
               {'op': 'add_node', 'ref': 'all', 'node_type': 'call_function', 'function_name': '/Script/Engine.KismetStringLibrary:Concat_StrStr', 'x': 4000, 'y': 300},
               {'op': 'connect', 'from_node': 'hc', 'from_pin': 'ReturnValue', 'to_node': 'all', 'to_pin': 'A'},
               {'op': 'connect', 'from_node': 'ms', 'from_pin': 'ReturnValue', 'to_node': 'all', 'to_pin': 'B'},
               {'op': 'add_node', 'ref': 'txt', 'node_type': 'call_function', 'function_name': f'{KTL}:Conv_StringToText', 'x': 4200, 'y': 300}]
        ops += [{'op': 'connect', 'from_node': 'all', 'from_pin': 'ReturnValue', 'to_node': 'txt', 'to_pin': 'InString'}]
        prev = 'setlb'
        for k, w in enumerate(('Txt_Clock', 'Txt_StatusTime')):
            ops += [{'op': 'add_node', 'ref': f'w{k}', 'node_type': 'variable_get', 'variable_name': w, 'x': 4200, 'y': -80 + k * 60},
                    {'op': 'add_node', 'ref': f'st{k}', 'node_type': 'call_function', 'function_name': SETTEXT, 'x': 4420 + k * 260, 'y': 0},
                    {'op': 'connect', 'from_node': f'w{k}', 'from_pin': w, 'to_node': f'st{k}', 'to_pin': 'self'},
                    {'op': 'connect', 'from_node': 'txt', 'from_pin': 'ReturnValue', 'to_node': f'st{k}', 'to_pin': 'InText'},
                    {'op': 'connect', 'from_node': prev, 'from_pin': 'then', 'to_node': f'st{k}', 'to_pin': 'execute'}]
            prev = f'st{k}'
        ops += [{'op': 'comment', 'title': 'Lock clock: 6:40 plus real minutes', 'node_ids': [o['ref'] for o in ops if o['op'] == 'add_node'],
                 'color': [0.10, 0.20, 0.35]}, {'op': 'fit_comments'}]
        batch('UpdateClock', ops)
        compile_ok()

    # 5. wire: Refresh's tail -> RefreshPreviews; Tick: Set LockLast -> UpdateClock -> (the lock slide Branch)
    nodes, edges = graph('Refresh')
    T = {n['node_id']: n['title'] for n in nodes}
    if not any(t.startswith('RefreshPreviews') or t.startswith('Refresh Previews') for t in T.values()):
        tail = next(n for n, t in T.items() if t.startswith('RefreshNotebook') or t.startswith('Refresh Notebook'))
        assert not [e for e in edges if e['from_node'] == tail and e['from_pin'] == 'then'], 'RefreshNotebook is not the tail'
        batch('Refresh', [{'op': 'add_node', 'ref': 'rp', 'node_type': 'call_function', 'function_name': f'{PC}:RefreshPreviews', 'x': 3400, 'y': 0},
                          {'op': 'connect', 'from_node': tail, 'from_pin': 'then', 'to_node': 'rp', 'to_pin': 'execute'}])
    nodes, edges = graph('EventGraph')
    T = {n['node_id']: n['title'] for n in nodes}
    if not any(t.startswith('UpdateClock') or t.startswith('Update Clock') for t in T.values()):
        setlast = next(n for n, t in T.items() if t == 'Set LockLast')
        nxt = [e for e in edges if e['from_node'] == setlast and e['from_pin'] == 'then']
        assert len(nxt) == 1, nxt
        batch('EventGraph', [{'op': 'disconnect', 'node_id': setlast, 'pin_name': 'then', 'to_node': nxt[0]['to_node'], 'to_pin': 'execute'},
                             {'op': 'add_node', 'ref': 'uc', 'node_type': 'call_function', 'function_name': f'{PC}:UpdateClock', 'x': 1400, 'y': 3160},
                             {'op': 'connect', 'from_node': setlast, 'from_pin': 'then', 'to_node': 'uc', 'to_pin': 'execute'},
                             {'op': 'connect', 'from_node': 'uc', 'from_pin': 'then', 'to_node': nxt[0]['to_node'], 'to_pin': 'execute'}])
    d = compile_ok()
    print('compiled_clean', d.get('compiled_clean'), d.get('errors'), d.get('warnings'),
          'saved', hc.call('ui_save_widget', {'widget_blueprint_path': P})['data'].get('saved'))
finally:
    if token:
        hc.release('ui', token)
        editor_lock.forget('ui', token)
