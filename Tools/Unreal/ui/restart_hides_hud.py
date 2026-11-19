"""QA #17 (run 1517 D2, 16.7 s / 17.7 s): after Restart Day the HUD (objective, key hints) stayed up over the black and
the new morning's wake-up film. The first morning enters the film with the HUD at opacity 0 (FinishWake) and the day
rollover does the same (RolloverCovered); the HUD's own FadeInStep brings it back when the morning's beats start
(HandleBeatChanged). BP_FoAFrontEnd.RestartDay now hides it the same way right after Resume, before the director's
RestartDay (FreezeForRollover, FadeToNextMorning, the film). Idempotent.
  python Tools/Unreal/ui/restart_hides_hud.py"""
import sys

sys.path.insert(0, 'P:/FoA/Tools/Unreal')
import editor_lock  # noqa: E402
import hayba_call as hc  # noqa: E402

FE = '/Game/FoA/UI/Framework/BP_FoAFrontEnd'
assert not hc.call('editor_get_state', {})['data']['pie_running'], 'PIE running'
assert 'HUD' in {v.get('name') for v in hc.call('blueprint_get_info', {'path': FE})['data']['variables']}  # batch precheck
token = editor_lock.acquire('ui', wait_s=300, ttl=120, areas=[FE])
try:
    d = hc.call('blueprint_inspect_graph', {'path': FE, 'graph_name': 'RestartDay'})['data']
    T = {n['node_id']: n['title'] for n in d['nodes']}
    if not any(t == 'Get HUD' for t in T.values()):
        resume = next(i for i, t in T.items() if t == 'Resume')
        nxt = [e for e in d['edges'] if e['from_node'] == resume and e['from_pin'] == 'then']
        assert len(nxt) == 1, nxt
        n = nxt[0]['to_node']
        ops = [{'op': 'disconnect', 'node_id': resume, 'pin_name': 'then', 'to_node': n, 'to_pin': 'execute'},
               {'op': 'add_node', 'ref': 'hud', 'node_type': 'variable_get', 'variable_name': 'HUD', 'x': 300, 'y': 200},
               {'op': 'add_node', 'ref': 'ok', 'node_type': 'call_function', 'function_name': '/Script/Engine.KismetSystemLibrary:IsValid', 'x': 480, 'y': 260},
               {'op': 'connect', 'from_node': 'hud', 'from_pin': 'HUD', 'to_node': 'ok', 'to_pin': 'Object'},
               {'op': 'add_node', 'ref': 'br', 'node_type': 'branch', 'x': 660, 'y': 0},
               {'op': 'connect', 'from_node': 'ok', 'from_pin': 'ReturnValue', 'to_node': 'br', 'to_pin': 'Condition'},
               {'op': 'connect', 'from_node': resume, 'from_pin': 'then', 'to_node': 'br', 'to_pin': 'execute'},
               {'op': 'add_node', 'ref': 'op', 'node_type': 'call_function', 'function_name': '/Script/UMG.Widget:SetRenderOpacity', 'x': 880, 'y': 0},
               {'op': 'connect', 'from_node': 'hud', 'from_pin': 'HUD', 'to_node': 'op', 'to_pin': 'self'},
               {'op': 'set_pin', 'node_id': 'op', 'pin_name': 'InOpacity', 'value': '0.0'},
               {'op': 'connect', 'from_node': 'br', 'from_pin': 'then', 'to_node': 'op', 'to_pin': 'execute'},
               {'op': 'connect', 'from_node': 'op', 'from_pin': 'then', 'to_node': n, 'to_pin': 'execute'},
               {'op': 'connect', 'from_node': 'br', 'from_pin': 'else', 'to_node': n, 'to_pin': 'execute'},
               {'op': 'comment', 'title': 'Hide the HUD for the new morning', 'node_ids': ['hud', 'ok', 'br', 'op'], 'color': [0.12, 0.26, 0.16]}]
        r = hc.call('blueprint_graph_batch', {'path': FE, 'graph_name': 'RestartDay', 'ops': ops})
        print('batch', r.get('ok'), (r.get('data') or {}).get('applied'), (r.get('data') or {}).get('error') or r.get('error') or '')
        assert r.get('ok')
    c = hc.call('blueprint_compile', {'path': FE}).get('data') or {}
    print('compile', c.get('compiled'), 'errors', c.get('error_count'), 'warnings', c.get('warning_count'))
    print('save', (hc.call('asset_save', {'asset_paths': [FE]}).get('data') or {}).get('saved_count'))
finally:
    if token:
        hc.release('ui', token)
        editor_lock.forget('ui', token)
d = hc.call('blueprint_inspect_graph', {'path': FE, 'graph_name': 'RestartDay'})['data']
T = {n['node_id']: n['title'] for n in d['nodes']}
print('RestartDay exec:', [(T[e['from_node']], e['from_pin'], T[e['to_node']]) for e in d['edges'] if e['to_pin'] == 'execute'])
