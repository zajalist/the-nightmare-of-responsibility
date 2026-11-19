"""The held phone's screen must write stencil 200 (world 2026-11-10: a light-shaft card 1-2 m behind the phone drew over the
screen; the CustomStencil view showed no 200 on it). BP_Phone's template had it, but the placed Phone_Nightstand overrides
its Screen (custom depth off, stencil 0, no material override, 540 x 1201). The construction script runs after instance
values, so it now sets them itself, after the socket attach: Screen custom depth + stencil 200, M_UI_PhoneScreen,
540 x 1118, one-sided, scale 0.01222; Mesh custom depth + stencil 200 (the lens and the shafts skip the body too).
The Mesh template gets the same stencil. Idempotent.
  python Tools/Unreal/ui/phone_screen_authority.py"""
import sys

sys.path.insert(0, 'P:/FoA/Tools/Unreal')
import editor_lock  # noqa: E402
import hayba_call as hc  # noqa: E402

P = '/Game/FoA/UI/Game/BP_Phone'
PRIM, WIDGET, SCENE = '/Script/Engine.PrimitiveComponent', '/Script/UMG.WidgetComponent', '/Script/Engine.SceneComponent'
MAT = "/Game/FoA/UI/Materials/M_UI_PhoneScreen.M_UI_PhoneScreen"


def graph(g):
    d = hc.call('blueprint_inspect_graph', {'path': P, 'graph_name': g})['data']
    return d['nodes'], d['edges']


assert not hc.call('editor_get_state', {})['data']['pie_running'], 'PIE running'
token = editor_lock.acquire('ui', wait_s=120, ttl=120, areas=[P])
try:
    print('mesh template', hc.call('object_set_property', {'path': f'{P}.BP_Phone_C:Mesh_GEN_VARIABLE', 'properties': {
        'bRenderCustomDepth': True, 'CustomDepthStencilValue': 200}}).get('data'))
    nodes, edges = graph('UserConstructionScript')
    T = {n['node_id']: n['title'] for n in nodes}
    if not any('Stencil' in t for t in T.values()):
        tail = next(i for i, t in T.items() if t == 'Set Relative Location')
        assert not [e for e in edges if e['from_node'] == tail and e['from_pin'] == 'then'], 'Set Relative Location is not the tail'
        steps = [('scr', 'Screen', f'{PRIM}:SetRenderCustomDepth', {'bValue': 'true'}),
                 ('scr', 'Screen', f'{PRIM}:SetCustomDepthStencilValue', {'Value': '200'}),
                 ('scr', 'Screen', f'{PRIM}:SetMaterial', {'ElementIndex': '0', 'Material': MAT}),
                 ('scr', 'Screen', f'{WIDGET}:SetDrawSize', {'Size': '(X=540,Y=1118)'}),
                 ('scr', 'Screen', f'{WIDGET}:SetTwoSided', {'bWantTwoSided': 'false'}),
                 ('scr', 'Screen', f'{SCENE}:SetRelativeScale3D', {'NewScale3D': '0.01222, 0.01222, 0.01222'}),
                 ('mesh', 'Mesh', f'{PRIM}:SetRenderCustomDepth', {'bValue': 'true'}),
                 ('mesh', 'Mesh', f'{PRIM}:SetCustomDepthStencilValue', {'Value': '200'})]
        ops = [{'op': 'add_node', 'ref': 'scr', 'node_type': 'variable_get', 'variable_name': 'Screen', 'x': 1100, 'y': 260},
               {'op': 'add_node', 'ref': 'mesh', 'node_type': 'variable_get', 'variable_name': 'Mesh', 'x': 1100, 'y': 340}]
        prev = tail
        for k, (ref, var, fn, pins) in enumerate(steps):
            ops += [{'op': 'add_node', 'ref': f's{k}', 'node_type': 'call_function', 'function_name': fn, 'x': 1300 + k * 260, 'y': 0},
                    {'op': 'connect', 'from_node': ref, 'from_pin': var, 'to_node': f's{k}', 'to_pin': 'self'},
                    {'op': 'connect', 'from_node': prev, 'from_pin': 'then', 'to_node': f's{k}', 'to_pin': 'execute'}]
            ops += [{'op': 'set_pin', 'node_id': f's{k}', 'pin_name': pn, 'value': v} for pn, v in pins.items()]
            prev = f's{k}'
        ops += [{'op': 'comment', 'title': 'The class sets the screen (placed phones override it)', 'node_ids': ['scr', 'mesh'] + [f's{k}' for k in range(len(steps))],
                 'color': [0.10, 0.20, 0.35]}]
        r = hc.call('blueprint_graph_batch', {'path': P, 'graph_name': 'UserConstructionScript', 'ops': ops})
        d = r.get('data') or {}
        print('construction script', r.get('ok'), d.get('applied'), d.get('failed_index', ''), d.get('error') or r.get('error') or '')
        assert r.get('ok')
    c = hc.call('blueprint_compile', {'path': P}).get('data') or {}
    print('compile', c.get('compiled'), 'errors', c.get('error_count'), 'warnings', c.get('warning_count'))
    assert c.get('compiled') and not c.get('error_count')
    print('save', (hc.call('asset_save', {'asset_paths': [P], 'force': True}).get('data') or {}).get('saved_count'))
finally:
    if token:
        hc.release('ui', token)
        editor_lock.forget('ui', token)
