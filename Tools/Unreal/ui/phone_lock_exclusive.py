"""Phone: lock OR home, never both (main, 2026-11-09; anim's phone5 frame and our lockproof f0506 showed the lock fading
over the Today page). WBP_Phone Tick, in place (Hayba), idempotent:
  Pages (the app pages) opacity = clamp((LockT - 1.35) / 0.15): hidden while the lock is up or sliding away (it is gone
  at LockT 1.35), then a 0.15 s fade in. The live window grows 1.5 -> 1.7 s so the fade always completes.
  fresh open = frame gap > 10.5 (was 2.5): the world-space widget redraws at 30 Hz, so above ~90 fps its ticks are
  3+ frames apart and the lock restarted every tick; a real put-away and raise is far more than 10 frames, a hitch is 1.
  python Tools/Unreal/ui/phone_lock_exclusive.py"""
import sys

sys.path.insert(0, 'P:/FoA/Tools/Unreal')
import editor_lock  # noqa: E402
import hayba_call as hc  # noqa: E402

P = '/Game/FoA/UI/Game/WBP_Phone'
KML = '/Script/Engine.KismetMathLibrary'


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


def pin(n, name):
    return next((p.get('default_value') for p in n['pins'] if p['name'] == name), None)


assert not hc.call('editor_get_state', {})['data']['pie_running'], 'PIE running'
token = editor_lock.acquire('ui', wait_s=300, ttl=120, areas=[P])
try:
    r = hc.call('ui_set_variable', {'widget_blueprint_path': P, 'widget_name': 'Pages', 'is_variable': True})
    assert r.get('ok'), r
    d = hc.call('ui_compile_widget', {'widget_blueprint_path': P})['data']
    assert d.get('compiled_clean'), d
    nodes, edges = graph('EventGraph')
    N = {n['node_id']: n for n in nodes}
    T = {n['node_id']: n['title'] for n in nodes}
    ops = []
    fresh = [n for n in nodes if n['title'] == 'float > float']
    fresh = [n for n in fresh if pin(n, 'B') in ('2.5', '2.500000', '10.5', '10.500000')]
    assert len(fresh) == 1, [(n['title'], pin(n, 'B')) for n in fresh]
    if not str(pin(fresh[0], 'B')).startswith('10.5'):
        ops.append({'op': 'set_pin', 'node_id': fresh[0]['node_id'], 'pin_name': 'B', 'value': '10.5'})
    live = [n for n in nodes if n['title'] == 'float <= float' and pin(n, 'B') in ('1.5', '1.500000', '1.7', '1.700000')]
    assert len(live) == 1, [(n['title'], pin(n, 'B')) for n in nodes if n['title'] == 'float <= float']
    if not str(pin(live[0], 'B')).startswith('1.7'):
        ops.append({'op': 'set_pin', 'node_id': live[0]['node_id'], 'pin_name': 'B', 'value': '1.7'})
    if not any(t == 'Get Pages' for t in T.values()):
        lock_get = {i for i, t in T.items() if t == 'Get Ovl_Lock'}
        lock_op = next(e['to_node'] for e in edges if e['from_node'] in lock_get and e['to_pin'] == 'self'
                       and T[e['to_node']].startswith('SetRenderOpacity'))
        assert not [e for e in edges if e['from_node'] == lock_op and e['from_pin'] == 'then'], 'lock opacity is not the tail'
        ops += [{'op': 'add_node', 'ref': 'lt', 'node_type': 'variable_get', 'variable_name': 'LockT', 'x': 2860, 'y': 3300},
                {'op': 'add_node', 'ref': 's', 'node_type': 'call_function', 'function_name': f'{KML}:Subtract_DoubleDouble', 'x': 3040, 'y': 3300},
                {'op': 'connect', 'from_node': 'lt', 'from_pin': 'LockT', 'to_node': 's', 'to_pin': 'A'},
                {'op': 'set_pin', 'node_id': 's', 'pin_name': 'B', 'value': '1.35'},
                {'op': 'add_node', 'ref': 'd', 'node_type': 'call_function', 'function_name': f'{KML}:Divide_DoubleDouble', 'x': 3220, 'y': 3300},
                {'op': 'connect', 'from_node': 's', 'from_pin': 'ReturnValue', 'to_node': 'd', 'to_pin': 'A'},
                {'op': 'set_pin', 'node_id': 'd', 'pin_name': 'B', 'value': '0.15'},
                {'op': 'add_node', 'ref': 'cl', 'node_type': 'call_function', 'function_name': f'{KML}:FClamp', 'x': 3400, 'y': 3300},
                {'op': 'connect', 'from_node': 'd', 'from_pin': 'ReturnValue', 'to_node': 'cl', 'to_pin': 'Value'},
                {'op': 'set_pin', 'node_id': 'cl', 'pin_name': 'Min', 'value': '0.0'},
                {'op': 'set_pin', 'node_id': 'cl', 'pin_name': 'Max', 'value': '1.0'},
                {'op': 'add_node', 'ref': 'pg', 'node_type': 'variable_get', 'variable_name': 'Pages', 'x': 3400, 'y': 3180},
                {'op': 'add_node', 'ref': 'po', 'node_type': 'call_function', 'function_name': '/Script/UMG.Widget:SetRenderOpacity', 'x': 3600, 'y': 3000},
                {'op': 'connect', 'from_node': 'pg', 'from_pin': 'Pages', 'to_node': 'po', 'to_pin': 'self'},
                {'op': 'connect', 'from_node': 'cl', 'from_pin': 'ReturnValue', 'to_node': 'po', 'to_pin': 'InOpacity'},
                {'op': 'connect', 'from_node': lock_op, 'from_pin': 'then', 'to_node': 'po', 'to_pin': 'execute'},
                {'op': 'comment', 'title': 'Home after the lock, never both', 'node_ids': ['lt', 's', 'd', 'cl', 'pg', 'po'],
                 'color': [0.30, 0.22, 0.10]}]
    if ops:
        r = hc.call('blueprint_graph_batch', {'path': P, 'graph_name': 'EventGraph', 'ops': ops})
        print('batch', r.get('ok'), (r.get('data') or {}).get('applied'), (r.get('data') or {}).get('error') or r.get('error') or '')
        assert r.get('ok')
    d = hc.call('ui_compile_widget', {'widget_blueprint_path': P})['data']
    print('compiled_clean', d.get('compiled_clean'), d.get('errors'), 'saved',
          hc.call('ui_save_widget', {'widget_blueprint_path': P})['data'].get('saved'))
finally:
    if token:
        hc.release('ui', token)
        editor_lock.forget('ui', token)
nodes, edges = graph('EventGraph')
print('fresh B', [pin(n, 'B') for n in nodes if n['title'] == 'float > float'], '| live B', [pin(n, 'B') for n in nodes if n['title'] == 'float <= float'],
      '| Pages opacity node', any(n['title'] == 'Get Pages' for n in nodes))
