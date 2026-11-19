"""Phone Today rows tick with progress (main 2026-11-10; QA B3 at T10 showed Wake up and Get dressed open). Two gaps:
the director ticks only on CompleteBeat by beat data (T9 ticks Wake up, T8 Get dressed; a beat entered any other way
ticks nothing), and the AAA pass's Img_Check circles were never filled. All typed nodes (Hayba's connect does not
resolve wildcard array pins; a first try with Array_Get/Array_Set left WBP_Phone failing until emptied):
  ByBeat(Index) -> Done        (Index == 0 AND BeatIndex >= 1) OR (Index == 1 AND BeatIndex >= 9)
  ShowCheck(Check, Done)       the circle's fill: ink when done, clear when open (the outline stays)
  ShowRowCheck(Index, Done)    Switch on Index -> ShowCheck(Img_Check<i>)
  ShowTask                     done = TaskTicked[Index] OR ByBeat(Index) drives the row dim (as before) and the check
New functions are built and compiled first; ShowTask is touched last in one small batch. Idempotent.
  python Tools/Unreal/ui/phone_today_checks.py"""
import sys

sys.path.insert(0, 'P:/FoA/Tools/Unreal')
import editor_lock  # noqa: E402
import hayba_call as hc  # noqa: E402

P = '/Game/FoA/UI/Game/WBP_Phone'
PC = f'{P}.WBP_Phone_C'
DIR_C = '/Game/FoA/Gameplay/BP_BeatDirector.BP_BeatDirector_C'
KML = '/Script/Engine.KismetMathLibrary'
INK, CLEAR = '(R=0.880000,G=0.880000,B=0.880000,A=1.000000)', '(R=0.000000,G=0.000000,B=0.000000,A=0.000000)'


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
    r = hc.call('blueprint_graph_batch', {'path': P, 'graph_name': g, 'ops': ops})
    d = r.get('data') or {}
    print(g, r.get('ok'), d.get('applied'), d.get('failed_index', ''), d.get('error') or r.get('error') or '')
    assert r.get('ok'), g


def compile_ok():
    d = hc.call('ui_compile_widget', {'widget_blueprint_path': P})['data']
    assert d.get('compiled_clean'), d.get('errors')


def fresh(g):
    nodes, edges = graph(g)
    keep = [n for n in nodes if n['title'] == g or n['title'].startswith('Return')]
    return nodes, edges, len(nodes) == len(keep)


assert not hc.call('editor_get_state', {})['data']['pie_running'], 'PIE running'
token = editor_lock.acquire('ui', wait_s=120, ttl=120, areas=[P])
try:
    for k in range(4):
        assert hc.call('ui_set_variable', {'widget_blueprint_path': P, 'widget_name': f'Img_Check{k}', 'is_variable': True}).get('ok')
    funcs = hc.call('blueprint_get_info', {'path': P})['data']['functions']
    specs = {'ByBeat': dict(inputs=[{'name': 'Index', 'type': 'int'}], outputs=[{'name': 'Done', 'type': 'bool'}], pure=True, const=True),
             'ShowCheck': dict(inputs=[{'name': 'Check', 'type': 'object:/Script/UMG.Image'}, {'name': 'Done', 'type': 'bool'}]),
             'ShowRowCheck': dict(inputs=[{'name': 'Index', 'type': 'int'}, {'name': 'Done', 'type': 'bool'}])}
    for name, spec in specs.items():
        if name not in funcs:
            r = hc.call('blueprint_add_function', {'path': P, 'function_name': name, **spec})
            assert r.get('ok'), (name, r.get('error'))
    compile_ok()

    nodes, edges, empty = fresh('ByBeat')
    if empty:
        e = next(n['node_id'] for n in nodes if n['title'] == 'ByBeat')
        ret = next(n['node_id'] for n in nodes if n['title'].startswith('Return'))
        ops = [] if [x for x in edges if x['from_node'] == e and x['to_node'] == ret] else \
            [{'op': 'connect', 'from_node': e, 'from_pin': 'then', 'to_node': ret, 'to_pin': 'execute'}]
        ops += [{'op': 'add_node', 'ref': 'dir', 'node_type': 'variable_get', 'variable_name': 'Director', 'x': 200, 'y': 300},
                {'op': 'add_node', 'ref': 'ok', 'node_type': 'call_function', 'function_name': '/Script/Engine.KismetSystemLibrary:IsValid', 'x': 400, 'y': 380},
                {'op': 'connect', 'from_node': 'dir', 'from_pin': 'Director', 'to_node': 'ok', 'to_pin': 'Object'},
                {'op': 'add_node', 'ref': 'bi', 'node_type': 'variable_get', 'variable_name': 'BeatIndex', 'class_path': DIR_C, 'x': 400, 'y': 260},
                {'op': 'connect', 'from_node': 'dir', 'from_pin': 'Director', 'to_node': 'bi', 'to_pin': 'self'},
                {'op': 'add_node', 'ref': 'beat', 'node_type': 'call_function', 'function_name': f'{KML}:SelectInt', 'x': 600, 'y': 300},
                {'op': 'connect', 'from_node': 'bi', 'from_pin': 'BeatIndex', 'to_node': 'beat', 'to_pin': 'A'},
                {'op': 'set_pin', 'node_id': 'beat', 'pin_name': 'B', 'value': '0'},
                {'op': 'connect', 'from_node': 'ok', 'from_pin': 'ReturnValue', 'to_node': 'beat', 'to_pin': 'bPickA'}]
        for k, (task, first) in enumerate(((0, 1), (1, 9))):
            ops += [{'op': 'add_node', 'ref': f'eq{k}', 'node_type': 'call_function', 'function_name': f'{KML}:EqualEqual_IntInt', 'x': 820, 'y': k * 200},
                    {'op': 'connect', 'from_node': e, 'from_pin': 'Index', 'to_node': f'eq{k}', 'to_pin': 'A'},
                    {'op': 'set_pin', 'node_id': f'eq{k}', 'pin_name': 'B', 'value': str(task)},
                    {'op': 'add_node', 'ref': f'ge{k}', 'node_type': 'call_function', 'function_name': f'{KML}:GreaterEqual_IntInt', 'x': 820, 'y': k * 200 + 90},
                    {'op': 'connect', 'from_node': 'beat', 'from_pin': 'ReturnValue', 'to_node': f'ge{k}', 'to_pin': 'A'},
                    {'op': 'set_pin', 'node_id': f'ge{k}', 'pin_name': 'B', 'value': str(first)},
                    {'op': 'add_node', 'ref': f'and{k}', 'node_type': 'call_function', 'function_name': f'{KML}:BooleanAND', 'x': 1040, 'y': k * 200 + 40},
                    {'op': 'connect', 'from_node': f'eq{k}', 'from_pin': 'ReturnValue', 'to_node': f'and{k}', 'to_pin': 'A'},
                    {'op': 'connect', 'from_node': f'ge{k}', 'from_pin': 'ReturnValue', 'to_node': f'and{k}', 'to_pin': 'B'}]
        ops += [{'op': 'add_node', 'ref': 'or', 'node_type': 'call_function', 'function_name': f'{KML}:BooleanOR', 'x': 1240, 'y': 120},
                {'op': 'connect', 'from_node': 'and0', 'from_pin': 'ReturnValue', 'to_node': 'or', 'to_pin': 'A'},
                {'op': 'connect', 'from_node': 'and1', 'from_pin': 'ReturnValue', 'to_node': 'or', 'to_pin': 'B'},
                {'op': 'connect', 'from_node': 'or', 'from_pin': 'ReturnValue', 'to_node': ret, 'to_pin': 'Done'},
                {'op': 'comment', 'title': 'Done by beat: Wake up from T1, Get dressed from T9', 'node_ids': ['dir', 'ok', 'bi', 'beat', 'eq0', 'ge0', 'and0', 'eq1', 'ge1', 'and1', 'or'],
                 'color': [0.12, 0.26, 0.16]}]
        batch('ByBeat', ops)
        compile_ok()

    nodes, edges, empty = fresh('ShowCheck')
    if empty:
        e = nodes[0]['node_id'] if nodes[0]['title'] == 'ShowCheck' else next(n['node_id'] for n in nodes if n['title'] == 'ShowCheck')
        batch('ShowCheck', [
            {'op': 'add_node', 'ref': 'sel', 'node_type': 'call_function', 'function_name': f'{KML}:SelectColor', 'x': 300, 'y': 200},
            {'op': 'set_pin', 'node_id': 'sel', 'pin_name': 'A', 'value': INK},
            {'op': 'set_pin', 'node_id': 'sel', 'pin_name': 'B', 'value': CLEAR},
            {'op': 'connect', 'from_node': e, 'from_pin': 'Done', 'to_node': 'sel', 'to_pin': 'bPickA'},
            {'op': 'add_node', 'ref': 'mk', 'node_type': 'make_struct', 'struct_path': '/Script/SlateCore.SlateColor', 'x': 520, 'y': 200},
            {'op': 'connect', 'from_node': 'sel', 'from_pin': 'ReturnValue', 'to_node': 'mk', 'to_pin': 'SpecifiedColor'},
            {'op': 'add_node', 'ref': 'tint', 'node_type': 'call_function', 'function_name': '/Script/UMG.Image:SetBrushTintColor', 'x': 760, 'y': 0},
            {'op': 'connect', 'from_node': e, 'from_pin': 'Check', 'to_node': 'tint', 'to_pin': 'self'},
            {'op': 'connect', 'from_node': 'mk', 'from_pin': 'SlateColor', 'to_node': 'tint', 'to_pin': 'TintColor'},
            {'op': 'connect', 'from_node': e, 'from_pin': 'then', 'to_node': 'tint', 'to_pin': 'execute'},
            {'op': 'comment', 'title': 'Fill the circle when done', 'node_ids': ['sel', 'mk', 'tint'], 'color': [0.12, 0.26, 0.16]}])
        compile_ok()

    nodes, edges, empty = fresh('ShowRowCheck')
    if empty:
        # a Branch chain on Index (Hayba's switch_int came back with no case pins)
        e = next(n['node_id'] for n in nodes if n['title'] == 'ShowRowCheck')
        ops, prev, prev_pin = [], e, 'then'
        for k in range(4):
            ops += [{'op': 'add_node', 'ref': f'img{k}', 'node_type': 'variable_get', 'variable_name': f'Img_Check{k}', 'x': 560 + k * 300, 'y': 260},
                    {'op': 'add_node', 'ref': f'sc{k}', 'node_type': 'call_function', 'function_name': f'{PC}:ShowCheck', 'x': 600 + k * 300, 'y': 120},
                    {'op': 'connect', 'from_node': f'img{k}', 'from_pin': f'Img_Check{k}', 'to_node': f'sc{k}', 'to_pin': 'Check'},
                    {'op': 'connect', 'from_node': e, 'from_pin': 'Done', 'to_node': f'sc{k}', 'to_pin': 'Done'}]
            if k < 3:
                ops += [{'op': 'add_node', 'ref': f'eq{k}', 'node_type': 'call_function', 'function_name': f'{KML}:EqualEqual_IntInt', 'x': 300 + k * 300, 'y': -120},
                        {'op': 'connect', 'from_node': e, 'from_pin': 'Index', 'to_node': f'eq{k}', 'to_pin': 'A'},
                        {'op': 'set_pin', 'node_id': f'eq{k}', 'pin_name': 'B', 'value': str(k)},
                        {'op': 'add_node', 'ref': f'br{k}', 'node_type': 'branch', 'x': 360 + k * 300, 'y': 0},
                        {'op': 'connect', 'from_node': f'eq{k}', 'from_pin': 'ReturnValue', 'to_node': f'br{k}', 'to_pin': 'Condition'},
                        {'op': 'connect', 'from_node': prev, 'from_pin': prev_pin, 'to_node': f'br{k}', 'to_pin': 'execute'},
                        {'op': 'connect', 'from_node': f'br{k}', 'from_pin': 'then', 'to_node': f'sc{k}', 'to_pin': 'execute'}]
                prev, prev_pin = f'br{k}', 'else'
            else:
                ops += [{'op': 'connect', 'from_node': prev, 'from_pin': prev_pin, 'to_node': f'sc{k}', 'to_pin': 'execute'}]
        ops += [{'op': 'comment', 'title': "The row's check", 'node_ids': [o['ref'] for o in ops if o['op'] == 'add_node'],
                 'color': [0.12, 0.26, 0.16]}]
        batch('ShowRowCheck', ops)
        compile_ok()

    # ShowTask: done = Get(TaskTicked)[Index] OR ByBeat(Index) -> the row dim and the check
    nodes, edges = graph('ShowTask')
    T = {n['node_id']: n['title'] for n in nodes}
    if not any(t.startswith('ByBeat') or t.startswith('By Beat') for t in T.values()):
        entry = next(i for i, t in T.items() if t == 'ShowTask')
        sf = next(i for i, t in T.items() if t.startswith('SelectFloat'))
        link = next(x for x in edges if x['to_node'] == sf and x['to_pin'] == 'bPickA')
        opn = next(i for i, t in T.items() if t.startswith('SetRenderOpacity'))
        assert not [x for x in edges if x['from_node'] == opn and x['from_pin'] == 'then'], 'SetRenderOpacity is not the tail'
        batch('ShowTask', [
            {'op': 'disconnect', 'node_id': link['from_node'], 'pin_name': link['from_pin'], 'to_node': sf, 'to_pin': 'bPickA'},
            {'op': 'add_node', 'ref': 'bb', 'node_type': 'call_function', 'function_name': f'{PC}:ByBeat', 'x': 300, 'y': 420},
            {'op': 'connect', 'from_node': entry, 'from_pin': 'Index', 'to_node': 'bb', 'to_pin': 'Index'},
            {'op': 'add_node', 'ref': 'or', 'node_type': 'call_function', 'function_name': f'{KML}:BooleanOR', 'x': 520, 'y': 360},
            {'op': 'connect', 'from_node': link['from_node'], 'from_pin': link['from_pin'], 'to_node': 'or', 'to_pin': 'A'},
            {'op': 'connect', 'from_node': 'bb', 'from_pin': 'Done', 'to_node': 'or', 'to_pin': 'B'},
            {'op': 'connect', 'from_node': 'or', 'from_pin': 'ReturnValue', 'to_node': sf, 'to_pin': 'bPickA'},
            {'op': 'add_node', 'ref': 'rc', 'node_type': 'call_function', 'function_name': f'{PC}:ShowRowCheck', 'x': 1100, 'y': 0},
            {'op': 'connect', 'from_node': entry, 'from_pin': 'Index', 'to_node': 'rc', 'to_pin': 'Index'},
            {'op': 'connect', 'from_node': 'or', 'from_pin': 'ReturnValue', 'to_node': 'rc', 'to_pin': 'Done'},
            {'op': 'connect', 'from_node': opn, 'from_pin': 'then', 'to_node': 'rc', 'to_pin': 'execute'}])
    compile_ok()
    s = hc.call('asset_save', {'asset_paths': [P], 'force': True}).get('data') or {}
    print('compiled_clean True | saved', s.get('saved_count'))
finally:
    if token:
        hc.release('ui', token)
        editor_lock.forget('ui', token)
