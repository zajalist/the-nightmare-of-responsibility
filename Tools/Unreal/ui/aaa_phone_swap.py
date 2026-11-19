"""BP_Phone swap onto anim's hold (main's GO 2026-11-10 after anim's phone6), in one quiet slot, in order:
  WBP_Phone.ResetLock (LockT = 0), hold (+ OpenPhone -> ResetLock), nocam (Python), taps, glass (one drawer on the Screen
  socket, one-sided), mouse (Python), asset_save force, verify, asset_save force; the .uasset timestamps must move.
Holds one asset lease by token (never `editor_lock.py release ui`: it would cancel the lane's queued sweep).
  python Tools/Unreal/ui/aaa_phone_swap.py"""
import os
import subprocess
import sys

sys.path.insert(0, 'P:/FoA/Tools/Unreal')
import editor_lock  # noqa: E402
import hayba_call as hc  # noqa: E402

BP = '/Game/FoA/UI/Game/BP_Phone'
WP = '/Game/FoA/UI/Game/WBP_Phone'
FILES = {BP: 'P:/FoA/Content/FoA/UI/Game/BP_Phone.uasset', WP: 'P:/FoA/Content/FoA/UI/Game/WBP_Phone.uasset'}
PY = sys.executable
ENV = dict(os.environ, FOA_AGENT='ui', HAYBA_AGENT_ID='ui', MSYS_NO_PATHCONV='1')


def run(*args):
    r = subprocess.run([PY, *args], env=ENV, capture_output=True, text=True, timeout=110)
    out = (r.stdout + r.stderr).strip()
    print('>>', ' '.join(a.split('/')[-1] for a in args), 'rc', r.returncode)
    print('   ' + '\n   '.join(out.splitlines()[-8:]))
    assert r.returncode == 0, args
    return out


def save_force():
    for path in (BP, WP):
        r = hc.call('asset_save', {'asset_paths': [path], 'force': True})
        print('asset_save force', path.split('/')[-1], (r.get('data') or {}).get('saved_count'), (r.get('data') or {}).get('skipped') or '', r.get('error') or '')


assert not hc.call('editor_get_state', {})['data']['pie_running'], 'PIE running'
before = {p: os.path.getmtime(f) for p, f in FILES.items()}
token = editor_lock.acquire('ui', wait_s=300, ttl=120, areas=[BP, WP])
try:
    # WBP_Phone.ResetLock: the open itself restarts the lock (main's plan), the Tick's frame-gap check is the fallback
    if 'ResetLock' not in hc.call('blueprint_get_info', {'path': WP})['data']['functions']:
        assert hc.call('blueprint_add_function', {'path': WP, 'function_name': 'ResetLock'}).get('ok')
        assert hc.call('ui_compile_widget', {'widget_blueprint_path': WP})['data'].get('compiled_clean')
        nodes = hc.call('blueprint_inspect_graph', {'path': WP, 'graph_name': 'ResetLock'})['data']['nodes']
        e = nodes[0]['node_id']
        r = hc.call('blueprint_graph_batch', {'path': WP, 'graph_name': 'ResetLock', 'ops': [
            {'op': 'add_node', 'ref': 's', 'node_type': 'variable_set', 'variable_name': 'LockT', 'x': 300, 'y': 0},
            {'op': 'set_pin', 'node_id': 's', 'pin_name': 'LockT', 'value': '0.0'},
            {'op': 'connect', 'from_node': e, 'from_pin': 'then', 'to_node': 's', 'to_pin': 'execute'}]})
        assert r.get('ok'), r
        d = hc.call('ui_compile_widget', {'widget_blueprint_path': WP})['data']
        assert d.get('compiled_clean'), d
    run('P:/FoA/Tools/Unreal/ui/aaa_phone_hold.py', 'hold')
    # OpenPhone: RefreshScreen -> Screen.GetUserWidgetObject -> Cast To WBP_Phone -> ResetLock
    d = hc.call('blueprint_inspect_graph', {'path': BP, 'graph_name': 'OpenPhone'})['data']
    T = {n['node_id']: n['title'] for n in d['nodes']}
    if not any(t.startswith('ResetLock') or t.startswith('Reset Lock') for t in T.values()):
        rs = next(i for i, t in T.items() if t.startswith('RefreshScreen') or t.startswith('Refresh Screen'))
        assert not [e for e in d['edges'] if e['from_node'] == rs and e['from_pin'] == 'then'], 'RefreshScreen is not the tail'
        r = hc.call('blueprint_graph_batch', {'path': BP, 'graph_name': 'OpenPhone', 'ops': [
            {'op': 'add_node', 'ref': 'scr', 'node_type': 'variable_get', 'variable_name': 'Screen', 'x': 3000, 'y': 200},
            {'op': 'add_node', 'ref': 'uw', 'node_type': 'call_function', 'function_name': '/Script/UMG.WidgetComponent:GetUserWidgetObject', 'x': 3180, 'y': 200},
            {'op': 'connect', 'from_node': 'scr', 'from_pin': 'Screen', 'to_node': 'uw', 'to_pin': 'self'},
            {'op': 'add_node', 'ref': 'cast', 'node_type': 'cast', 'class_path': f'{WP}.WBP_Phone_C', 'x': 3400, 'y': 0},
            {'op': 'connect', 'from_node': 'uw', 'from_pin': 'ReturnValue', 'to_node': 'cast', 'to_pin': 'Object'},
            {'op': 'connect', 'from_node': rs, 'from_pin': 'then', 'to_node': 'cast', 'to_pin': 'execute'}]})
        assert r.get('ok'), r
        d = hc.call('blueprint_inspect_graph', {'path': BP, 'graph_name': 'OpenPhone'})['data']
        cast = next(n for n in d['nodes'] if n['title'].startswith('Cast To WBP_Phone'))
        out = next(p['name'] for p in cast['pins'] if p['direction'] == 'output' and p['type'] == 'object')
        r = hc.call('blueprint_graph_batch', {'path': BP, 'graph_name': 'OpenPhone', 'ops': [
            {'op': 'add_node', 'ref': 'rl', 'node_type': 'call_function', 'function_name': f'{WP}.WBP_Phone_C:ResetLock', 'x': 3700, 'y': 0},
            {'op': 'connect', 'from_node': cast['node_id'], 'from_pin': out, 'to_node': 'rl', 'to_pin': 'self'},
            {'op': 'connect', 'from_node': cast['node_id'], 'from_pin': 'then', 'to_node': 'rl', 'to_pin': 'execute'},
            {'op': 'comment', 'title': 'The open restarts the lock', 'node_ids': [cast['node_id'], 'rl'], 'color': [0.10, 0.20, 0.35]}]})
        assert r.get('ok'), r
    run('P:/FoA/Tools/Unreal/ue_remote.py', 'P:/FoA/Tools/Unreal/ui/aaa_phone_hold.py', f'FOA_AREAS={BP}', 'FOA_STEP=nocam')
    save_force()
    run('P:/FoA/Tools/Unreal/ui/aaa_phone_hold.py', 'taps')
    run('P:/FoA/Tools/Unreal/ui/aaa_phone_hold.py', 'glass')
    run('P:/FoA/Tools/Unreal/ue_remote.py', 'P:/FoA/Tools/Unreal/ui/aaa_phone_mouse.py', f'FOA_AREAS={BP}', 'FOA_STEP=add')
    save_force()
    run('P:/FoA/Tools/Unreal/ui/aaa_phone_hold.py', 'verify')
    d = hc.call('ui_compile_widget', {'widget_blueprint_path': WP})['data']
    print('WBP_Phone compiled_clean', d.get('compiled_clean'), d.get('errors'))
    save_force()
finally:
    if token:
        hc.release('ui', token)
        editor_lock.forget('ui', token)
moved = {p.split('/')[-1]: os.path.getmtime(f) > before[p] for p, f in FILES.items()}
print('uasset rewritten', moved)
assert all(moved.values()), moved
