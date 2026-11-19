"""The widget Ticks (pause tear, settings rise, phone lock) restarted their motion on any real-time gap: an editor or
game hitch over 0.25 s re-fired the pause tear mid-pause (rec_hud_r1 f0465/f0475). They now measure the gap in FRAMES
(GetFrameCount): a widget that was not drawn skips frames, a hitch is one long frame. Fresh = gap > 2.5 frames.
  python Tools/Unreal/ui/aaa_tick_frames.py"""
import sys

sys.path.insert(0, 'P:/FoA/Tools/Unreal')
import hayba_call as hc  # noqa: E402

KSL = '/Script/Engine.KismetSystemLibrary'
KML = '/Script/Engine.KismetMathLibrary'
JOBS = ['/Game/FoA/UI/Widgets/Menus/WBP_Pause', '/Game/FoA/UI/Widgets/Menus/WBP_Settings', '/Game/FoA/UI/Game/WBP_Phone']
assert not hc.call('editor_get_state', {})['data']['pie_running'], 'PIE running'
for bp in JOBS:
    nodes, edges, off = [], [], 0
    while off is not None:
        d = hc.call('blueprint_inspect_graph', {'path': bp, 'graph_name': 'EventGraph', 'offset': off})['data']
        nodes += d['nodes']
        off = d['page']['nodes']['next_offset']
    off = 0
    while off is not None:
        d = hc.call('blueprint_inspect_graph', {'path': bp, 'graph_name': 'EventGraph', 'edge_offset': off})['data']
        edges += d['edges']
        off = d['page']['edges']['next_offset']
    now = [n['node_id'] for n in nodes if n['title'].startswith('GetRealTimeSeconds')]
    if not now:
        print(bp, 'already frame-based')
        continue
    assert len(now) == 1, (bp, len(now))
    fcs = [n['node_id'] for n in nodes if n['title'].startswith('Get Frame Count') or n['title'].startswith('GetFrameCount')]
    cvs = [n['node_id'] for n in nodes if any(p['name'] == 'InInt' for p in n['pins']) and n['node_id'] not in
           {e['to_node'] for e in edges if e['to_pin'] == 'InInt'}]
    now = now[0]
    outs = [e for e in edges if e['from_node'] == now]
    # the 'fresh' comparison: Greater_DoubleDouble fed (through the gap subtract) by now
    gap = next(e['to_node'] for e in outs if e['to_pin'] == 'A' and any(
        n['node_id'] == e['to_node'] and n['title'].startswith('float - float') for n in nodes))
    fresh = next(e['to_node'] for e in edges if e['from_node'] == gap)
    if fcs and cvs:  # left by a first attempt that stopped at the pin name
        ops, fc, cv = [], fcs[0], cvs[0]
    else:
        ops, fc, cv = [{'op': 'add_node', 'ref': 'fc', 'node_type': 'call_function', 'function_name': f'{KSL}:GetFrameCount', 'x': 0, 'y': 0},
                       {'op': 'add_node', 'ref': 'cv', 'node_type': 'call_function', 'function_name': f'{KML}:Conv_Int64ToDouble', 'x': 0, 'y': 0}], 'fc', 'cv'
    ops += [{'op': 'connect', 'from_node': fc, 'from_pin': 'ReturnValue', 'to_node': cv, 'to_pin': 'InInt'}]
    ops += [{'op': 'connect', 'from_node': cv, 'from_pin': 'ReturnValue', 'to_node': e['to_node'], 'to_pin': e['to_pin']} for e in outs]
    ops += [{'op': 'set_pin', 'node_id': fresh, 'pin_name': 'B', 'value': '2.5'}]
    r = hc.call('blueprint_graph_batch', {'path': bp, 'graph_name': 'EventGraph', 'ops': ops})
    d = r.get('data') or {}
    print(bp, r.get('ok'), d.get('applied'), d.get('failed_index'), d.get('error') or r.get('error') or '')
    if r.get('ok'):
        print(' remove old clock', hc.call('blueprint_remove_nodes', {'path': bp, 'graph_name': 'EventGraph', 'node_ids': [now]}).get('ok'))
    c = hc.call('ui_compile_widget', {'widget_blueprint_path': bp})['data']
    print(' compiled_clean', c.get('compiled_clean'), c.get('errors'), hc.call('ui_save_widget', {'widget_blueprint_path': bp})['data'].get('saved'))
