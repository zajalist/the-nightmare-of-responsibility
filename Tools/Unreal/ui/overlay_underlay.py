"""Keys and pad inside an overlay must never reach the screen under it (audioprobe, 2026-11-10): the main menu's buttons
stay hit-testable under Settings (SButtons at x 79-514, y 359-455), so Down from Interface volume (y 344) found the
menu's button (y 359) before the Music slider (y 383). BP_FoAFrontEnd, in place (Hayba), idempotent:
  SetUnderlayHitTest(Active): the screen under overlays (PauseMenu in gameplay, else Screen, as CloseOverlay picks it)
  goes SelfHitTestInvisible when Active (every screen root's default), HitTestInvisible otherwise (drawn, not hit or
  navigated). OpenOverlay calls it with false after AddToViewport; CloseOverlay with true first.
  python Tools/Unreal/ui/overlay_underlay.py"""
import sys

sys.path.insert(0, 'P:/FoA/Tools/Unreal')
import editor_lock  # noqa: E402
import hayba_call as hc  # noqa: E402

FE = '/Game/FoA/UI/Framework/BP_FoAFrontEnd'
FEC = f'{FE}.BP_FoAFrontEnd_C'
VIS = '/Script/UMG.Widget:SetVisibility'


def graph(g):
    d = hc.call('blueprint_inspect_graph', {'path': FE, 'graph_name': g})['data']
    assert d['page']['nodes']['next_offset'] is None and d['page']['edges']['next_offset'] is None, g
    return d['nodes'], d['edges']


def batch(g, ops):
    r = hc.call('blueprint_graph_batch', {'path': FE, 'graph_name': g, 'ops': ops})
    d = r.get('data') or {}
    print(g, r.get('ok'), d.get('applied'), d.get('error') or r.get('error') or '')
    assert r.get('ok'), g


assert not hc.call('editor_get_state', {})['data']['pie_running'], 'PIE running'
have = {v.get('name') for v in hc.call('blueprint_get_info', {'path': FE})['data']['variables']}
assert {'bInGameplay', 'PauseMenu', 'Screen'} <= have, have  # batch precheck
token = editor_lock.acquire('ui', wait_s=300, ttl=120, areas=[FE])
try:
    if 'SetUnderlayHitTest' not in hc.call('blueprint_get_info', {'path': FE})['data']['functions']:
        r = hc.call('blueprint_add_function', {'path': FE, 'function_name': 'SetUnderlayHitTest', 'inputs': [{'name': 'Active', 'type': 'bool'}]})
        assert r.get('ok'), r
        c = hc.call('blueprint_compile', {'path': FE}).get('data') or {}
        assert c.get('compiled') and not c.get('error_count'), c
    nodes, _ = graph('SetUnderlayHitTest')
    if len(nodes) <= 1:
        entry = nodes[0]['node_id']
        ops = [{'op': 'add_node', 'ref': 'ig', 'node_type': 'variable_get', 'variable_name': 'bInGameplay', 'x': 200, 'y': 200},
               {'op': 'add_node', 'ref': 'which', 'node_type': 'branch', 'x': 400, 'y': 0},
               {'op': 'connect', 'from_node': 'ig', 'from_pin': 'bInGameplay', 'to_node': 'which', 'to_pin': 'Condition'},
               {'op': 'connect', 'from_node': entry, 'from_pin': 'then', 'to_node': 'which', 'to_pin': 'execute'}]
        for row, (arm, var) in enumerate((('then', 'PauseMenu'), ('else', 'Screen'))):
            y = row * 420
            ops += [{'op': 'add_node', 'ref': f'w{row}', 'node_type': 'variable_get', 'variable_name': var, 'x': 600, 'y': y + 200},
                    {'op': 'add_node', 'ref': f'ok{row}', 'node_type': 'call_function', 'function_name': '/Script/Engine.KismetSystemLibrary:IsValid', 'x': 780, 'y': y + 260},
                    {'op': 'connect', 'from_node': f'w{row}', 'from_pin': var, 'to_node': f'ok{row}', 'to_pin': 'Object'},
                    {'op': 'add_node', 'ref': f'v{row}', 'node_type': 'branch', 'x': 960, 'y': y},
                    {'op': 'connect', 'from_node': f'ok{row}', 'from_pin': 'ReturnValue', 'to_node': f'v{row}', 'to_pin': 'Condition'},
                    {'op': 'connect', 'from_node': 'which', 'from_pin': arm, 'to_node': f'v{row}', 'to_pin': 'execute'},
                    {'op': 'add_node', 'ref': f'a{row}', 'node_type': 'branch', 'x': 1160, 'y': y},
                    {'op': 'connect', 'from_node': entry, 'from_pin': 'Active', 'to_node': f'a{row}', 'to_pin': 'Condition'},
                    {'op': 'connect', 'from_node': f'v{row}', 'from_pin': 'then', 'to_node': f'a{row}', 'to_pin': 'execute'}]
            for k, (apin, vis) in enumerate((('then', 'SelfHitTestInvisible'), ('else', 'HitTestInvisible'))):
                ops += [{'op': 'add_node', 'ref': f's{row}{k}', 'node_type': 'call_function', 'function_name': VIS, 'x': 1400, 'y': y + k * 160},
                        {'op': 'connect', 'from_node': f'w{row}', 'from_pin': var, 'to_node': f's{row}{k}', 'to_pin': 'self'},
                        {'op': 'set_pin', 'node_id': f's{row}{k}', 'pin_name': 'InVisibility', 'value': vis},
                        {'op': 'connect', 'from_node': f'a{row}', 'from_pin': apin, 'to_node': f's{row}{k}', 'to_pin': 'execute'}]
        ops += [{'op': 'comment', 'title': 'Screen under an overlay is not hit or navigated',
                 'node_ids': [o['ref'] for o in ops if o['op'] == 'add_node'], 'color': [0.12, 0.26, 0.16]}, {'op': 'fit_comments'}]
        batch('SetUnderlayHitTest', ops)
        c = hc.call('blueprint_compile', {'path': FE}).get('data') or {}
        assert c.get('compiled') and not c.get('error_count'), c
    # OpenOverlay: AddToViewport -> SetUnderlayHitTest(false) -> FocusUI
    nodes, edges = graph('OpenOverlay')
    T = {n['node_id']: n['title'] for n in nodes}
    if not any('SetUnderlayHitTest' in t or 'Set Underlay Hit Test' in t for t in T.values()):
        add = next(i for i, t in T.items() if t.startswith('AddToViewport') or t.startswith('Add to Viewport'))
        nxt = [e for e in edges if e['from_node'] == add and e['from_pin'] == 'then']
        assert len(nxt) == 1, nxt
        batch('OpenOverlay', [{'op': 'disconnect', 'node_id': add, 'pin_name': 'then', 'to_node': nxt[0]['to_node'], 'to_pin': 'execute'},
                              {'op': 'add_node', 'ref': 'u', 'node_type': 'call_function', 'function_name': f'{FEC}:SetUnderlayHitTest', 'x': 1500, 'y': -160},
                              {'op': 'set_pin', 'node_id': 'u', 'pin_name': 'Active', 'value': 'false'},
                              {'op': 'connect', 'from_node': add, 'from_pin': 'then', 'to_node': 'u', 'to_pin': 'execute'},
                              {'op': 'connect', 'from_node': 'u', 'from_pin': 'then', 'to_node': nxt[0]['to_node'], 'to_pin': 'execute'}])
    # CloseOverlay: entry -> SetUnderlayHitTest(true) -> the rest
    nodes, edges = graph('CloseOverlay')
    T = {n['node_id']: n['title'] for n in nodes}
    if not any('SetUnderlayHitTest' in t or 'Set Underlay Hit Test' in t for t in T.values()):
        entry = next(i for i, t in T.items() if t == 'CloseOverlay')
        nxt = [e for e in edges if e['from_node'] == entry and e['from_pin'] == 'then']
        assert len(nxt) == 1, nxt
        batch('CloseOverlay', [{'op': 'disconnect', 'node_id': entry, 'pin_name': 'then', 'to_node': nxt[0]['to_node'], 'to_pin': 'execute'},
                               {'op': 'add_node', 'ref': 'u', 'node_type': 'call_function', 'function_name': f'{FEC}:SetUnderlayHitTest', 'x': 200, 'y': -160},
                               {'op': 'set_pin', 'node_id': 'u', 'pin_name': 'Active', 'value': 'true'},
                               {'op': 'connect', 'from_node': entry, 'from_pin': 'then', 'to_node': 'u', 'to_pin': 'execute'},
                               {'op': 'connect', 'from_node': 'u', 'from_pin': 'then', 'to_node': nxt[0]['to_node'], 'to_pin': 'execute'}])
    c = hc.call('blueprint_compile', {'path': FE}).get('data') or {}
    print('compile', c.get('compiled'), 'errors', c.get('error_count'), 'warnings', c.get('warning_count'))
    assert c.get('compiled') and not c.get('error_count')
    print('save', (hc.call('asset_save', {'asset_paths': [FE]}).get('data') or {}).get('saved_count'))
finally:
    if token:
        hc.release('ui', token)
        editor_lock.forget('ui', token)
