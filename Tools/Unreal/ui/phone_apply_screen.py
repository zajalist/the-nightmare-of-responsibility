"""BP_Phone.ApplyScreen: the screen setup the class owns, run from the construction script AND BeginPlay (world 2026-11-10:
the placed Phone_Nightstand overrides its Screen, and PIE copies the editor actor without rerunning construction, so the
construction script alone never reached play). Screen on SM_Phone's Screen socket, 0.02 cm out of the glass,
M_UI_PhoneScreen, 540 x 1118, one-sided, scale 0.01222, custom depth + stencil 200; Mesh custom depth + stencil 200.
The construction script's inline copy is replaced by one ApplyScreen call. New function first, compiled; then the swaps.
  python Tools/Unreal/ui/phone_apply_screen.py"""
import sys

sys.path.insert(0, 'P:/FoA/Tools/Unreal')
import editor_lock  # noqa: E402
import hayba_call as hc  # noqa: E402

P = '/Game/FoA/UI/Game/BP_Phone'
PC = f'{P}.BP_Phone_C'
PRIM, WIDGET, SCENE = '/Script/Engine.PrimitiveComponent', '/Script/UMG.WidgetComponent', '/Script/Engine.SceneComponent'
MAT = '/Game/FoA/UI/Materials/M_UI_PhoneScreen.M_UI_PhoneScreen'
STEPS = [('scr', 'Screen', f'{SCENE}:K2_AttachToComponent', {'SocketName': 'Screen', 'LocationRule': 'SnapToTarget',
                                                             'RotationRule': 'SnapToTarget', 'ScaleRule': 'KeepRelative'}),
         ('scr', 'Screen', f'{SCENE}:SetRelativeScale3D', {'NewScale3D': '0.01222, 0.01222, 0.01222'}),
         ('scr', 'Screen', f'{SCENE}:K2_SetRelativeLocation', {'NewLocation': '0.02, 0, 0'}),
         ('scr', 'Screen', f'{PRIM}:SetMaterial', {'ElementIndex': '0', 'Material': MAT}),
         ('scr', 'Screen', f'{WIDGET}:SetDrawSize', {'Size': '(X=540,Y=1118)'}),
         ('scr', 'Screen', f'{WIDGET}:SetTwoSided', {'bWantTwoSided': 'false'}),
         ('scr', 'Screen', f'{PRIM}:SetRenderCustomDepth', {'bValue': 'true'}),
         ('scr', 'Screen', f'{PRIM}:SetCustomDepthStencilValue', {'Value': '200'}),
         ('mesh', 'Mesh', f'{PRIM}:SetRenderCustomDepth', {'bValue': 'true'}),
         ('mesh', 'Mesh', f'{PRIM}:SetCustomDepthStencilValue', {'Value': '200'})]


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
    c = hc.call('blueprint_compile', {'path': P}).get('data') or {}
    assert c.get('compiled') and not c.get('error_count'), c


assert not hc.call('editor_get_state', {})['data']['pie_running'], 'PIE running'
token = editor_lock.acquire('ui', wait_s=120, ttl=120, areas=[P])
try:
    if 'ApplyScreen' not in hc.call('blueprint_get_info', {'path': P})['data']['functions']:
        assert hc.call('blueprint_add_function', {'path': P, 'function_name': 'ApplyScreen'}).get('ok')
        compile_ok()
    nodes, _ = graph('ApplyScreen')
    if len(nodes) <= 1:
        e = nodes[0]['node_id']
        ops = [{'op': 'add_node', 'ref': 'scr', 'node_type': 'variable_get', 'variable_name': 'Screen', 'x': 200, 'y': 260},
               {'op': 'add_node', 'ref': 'mesh', 'node_type': 'variable_get', 'variable_name': 'Mesh', 'x': 200, 'y': 340},
               {'op': 'add_node', 'ref': 'mesh2', 'node_type': 'variable_get', 'variable_name': 'Mesh', 'x': 300, 'y': 180}]
        prev = e
        for k, (ref, var, fn, pins) in enumerate(STEPS):
            ops += [{'op': 'add_node', 'ref': f's{k}', 'node_type': 'call_function', 'function_name': fn, 'x': 420 + k * 260, 'y': 0},
                    {'op': 'connect', 'from_node': ref, 'from_pin': var, 'to_node': f's{k}', 'to_pin': 'self'},
                    {'op': 'connect', 'from_node': prev, 'from_pin': 'then', 'to_node': f's{k}', 'to_pin': 'execute'}]
            ops += [{'op': 'set_pin', 'node_id': f's{k}', 'pin_name': pn, 'value': v} for pn, v in pins.items()]
            prev = f's{k}'
        ops += [{'op': 'connect', 'from_node': 'mesh2', 'from_pin': 'Mesh', 'to_node': 's0', 'to_pin': 'Parent'},
                {'op': 'comment', 'title': 'Screen on the glass socket, stencil 200 on screen and body',
                 'node_ids': ['scr', 'mesh', 'mesh2'] + [f's{k}' for k in range(len(STEPS))], 'color': [0.10, 0.20, 0.35]}]
        batch('ApplyScreen', ops)
        compile_ok()
    # construction script: replace the inline nodes with one call
    nodes, edges = graph('UserConstructionScript')
    entry = next(n['node_id'] for n in nodes if n['title'] == 'Construction Script')
    if not any(n['title'].replace(' ', '').startswith('ApplyScreen') for n in nodes):
        rest = [n['node_id'] for n in nodes if n['node_id'] != entry]
        assert hc.call('blueprint_remove_nodes', {'path': P, 'graph_name': 'UserConstructionScript', 'node_ids': rest}).get('ok')
        batch('UserConstructionScript', [
            {'op': 'add_node', 'ref': 'ap', 'node_type': 'call_function', 'function_name': f'{PC}:ApplyScreen', 'x': 300, 'y': 0},
            {'op': 'connect', 'from_node': entry, 'from_pin': 'then', 'to_node': 'ap', 'to_pin': 'execute'}])
    # BeginPlay: PIE copies the editor actor without rerunning construction
    nodes, edges = graph('EventGraph')
    T = {n['node_id']: n['title'] for n in nodes}
    bp_ev = next(i for i, t in T.items() if t == 'Event BeginPlay')
    nxt = [e for e in edges if e['from_node'] == bp_ev and e['from_pin'] == 'then']
    if not (nxt and T[nxt[0]['to_node']].replace(' ', '').startswith('ApplyScreen')):
        ops = [{'op': 'add_node', 'ref': 'ap', 'node_type': 'call_function', 'function_name': f'{PC}:ApplyScreen', 'x': 0, 'y': -200}]
        if nxt:
            ops = [{'op': 'disconnect', 'node_id': bp_ev, 'pin_name': 'then', 'to_node': nxt[0]['to_node'], 'to_pin': 'execute'}] + ops + \
                  [{'op': 'connect', 'from_node': 'ap', 'from_pin': 'then', 'to_node': nxt[0]['to_node'], 'to_pin': 'execute'}]
        ops += [{'op': 'connect', 'from_node': bp_ev, 'from_pin': 'then', 'to_node': 'ap', 'to_pin': 'execute'}]
        batch('EventGraph', ops)
    compile_ok()
    print('save', (hc.call('asset_save', {'asset_paths': [P], 'force': True}).get('data') or {}).get('saved_count'))
finally:
    if token:
        hc.release('ui', token)
        editor_lock.forget('ui', token)
