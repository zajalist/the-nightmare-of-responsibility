"""Second pass on the widget Tick chains (Hayba only): delete every comment box holding chain nodes except the largest
(the one aaa_tick_tidy.py added), place the chain as one exec row with each exec node's data inputs stacked below-left
(depth columns), pack with real sizes, refit the box.
  python Tools/Unreal/ui/aaa_tick_tidy2.py"""
import sys

sys.path.insert(0, 'P:/FoA/Tools/Unreal')
import hayba_call as hc  # noqa: E402
exec(open('P:/FoA/Tools/Unreal/ui/aaa_tick_tidy.py', encoding='utf-8').read().split("assert not hc.call")[0])  # JOBS, graph, tick_chain

X0, Y0, COL, GAP = 0, 9000, 300, 90
assert not hc.call('editor_get_state', {})['data']['pie_running'], 'PIE running'
for bp, title, _ in JOBS:
    nodes, edges = graph(bp)
    chain = set(tick_chain(nodes, edges))
    meas, off = [], 0
    while off is not None:  # measure is paged like inspect
        d = hc.call('blueprint_measure_nodes', {'path': bp, 'graph_name': 'EventGraph', 'offset': off})['data']
        meas += d['nodes']
        nxt = (d.get('page') or {}).get('next_offset')
        off = nxt if nxt and nxt > off else None
    rect = {m['node_id']: m['rect'] for m in meas}
    boxes = {m['node_id'] for m in meas if m.get('comment')}
    holding = {m['in_comment'] for m in meas if m['node_id'] in chain and m.get('in_comment')}
    keep = max(holding, key=lambda b: rect[b][2] * rect[b][3]) if holding else None
    drop = sorted(holding - {keep})
    if drop:
        print(bp, 'drop boxes', len(drop), hc.call('blueprint_remove_nodes', {'path': bp, 'graph_name': 'EventGraph', 'node_ids': drop}).get('ok'))
    others = [rect[m] for m in rect if m not in chain and m not in boxes]
    Y0 = (max(r[1] + r[3] for r in others) + 700) if others else 0  # below everything else in the graph
    X0 = min(r[0] for r in others) if others else 0
    execs = {n['node_id'] for n in nodes if any(p['type'] == 'exec' for p in n['pins'])}
    tick = next(n['node_id'] for n in nodes if n['title'].startswith('Event Tick'))
    row, cur, seen = [tick], tick, {tick}
    while True:
        nxt = [e['to_node'] for e in edges if e['from_node'] == cur and e['from_pin'] == 'then' and e['to_pin'] == 'execute']
        if not nxt or nxt[0] in seen:
            break
        cur = nxt[0]
        row.append(cur)
        seen.add(cur)
    rest = [n for n in chain if n in execs and n not in seen]  # branch side exits (e.g. Clear Timer) go on a second row
    moves, placed, x = [], set(), X0
    for i, ex in enumerate(row + rest):
        y_row = Y0 if ex in row else Y0 - 260
        # data feeders by depth (pure nodes only)
        depth, frontier = {}, [ex]
        for d in range(1, 6):
            nxt = []
            for f in frontier:
                for e in edges:
                    s = e['from_node']
                    if e['to_node'] == f and s in chain and s not in execs and s not in placed and s not in depth:
                        depth[s] = d
                        nxt.append(s)
            frontier = nxt
        maxd = max(depth.values(), default=0)
        x_ex = x + maxd * COL
        moves.append({'node_id': ex, 'x': x_ex, 'y': y_row})
        placed.add(ex)
        for d in range(1, maxd + 1):
            col = [n for n, dd in depth.items() if dd == d]
            yy = y_row + 200
            for n in col:
                moves.append({'node_id': n, 'x': x_ex - d * COL, 'y': yy})
                placed.add(n)
                yy += rect.get(n, [0, 0, 0, 100])[3] + 40
        x = x_ex + rect.get(ex, [0, 0, 240, 0])[2] + GAP
    r = hc.call('blueprint_move_nodes', {'path': bp, 'graph_name': 'EventGraph', 'moves': moves, 'pack': True, 'gap': 32,
                                         'fit_comments': True})
    d = r.get('data') or {}
    print(bp, r.get('ok'), d.get('moved'), [(f['title'], f['rect']) for f in (d.get('fit') or {}).get('fitted', []) if f['node_id'] == keep])
    print(hc.call('ui_compile_widget', {'widget_blueprint_path': bp})['data'].get('compiled_clean'),
          hc.call('ui_save_widget', {'widget_blueprint_path': bp})['data'].get('saved'))
