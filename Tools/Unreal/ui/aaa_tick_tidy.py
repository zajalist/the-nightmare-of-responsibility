"""Tidy the widget Tick chains the AAA pass added (WBP_Pause, WBP_Settings, WBP_Phone EventGraph), Hayba only:
remove the batch-made comment boxes over the Tick chain (they nested and confused bp_layout), re-run bp_layout on the
asset so the chain becomes one exec row with its data nodes below-left, then put ONE title-only box around the chain.
  python Tools/Unreal/ui/aaa_tick_tidy.py"""
import subprocess
import sys

sys.path.insert(0, 'P:/FoA/Tools/Unreal')
import hayba_call as hc  # noqa: E402

JOBS = [('/Game/FoA/UI/Widgets/Menus/WBP_Pause', 'Pause motion',
         ('Pause clock', 'Frame tears, then settles', 'Header fades in', 'Words form from sand')),
        ('/Game/FoA/UI/Widgets/Menus/WBP_Settings', 'Settings motion', ('Settings clock', 'Rows rise in')),
        ('/Game/FoA/UI/Game/WBP_Phone', 'Lock screen motion', ('Lock clock', 'Unlock slides up'))]


def graph(bp):
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
    return nodes, edges


def tick_chain(nodes, edges):
    """Event Tick, every exec node after it, and every data node feeding them (recursively)."""
    tick = next(n['node_id'] for n in nodes if n['title'].startswith('Event Tick'))
    chain, todo = {tick}, [tick]
    while todo:
        cur = todo.pop()
        for e in edges:
            if e['from_node'] == cur and e['to_pin'] == 'execute' and e['to_node'] not in chain:
                chain.add(e['to_node'])
                todo.append(e['to_node'])
    todo = list(chain)
    while todo:
        cur = todo.pop()
        for e in edges:
            if e['to_node'] == cur and e['from_node'] not in chain and e['to_pin'] not in ('execute',):
                chain.add(e['from_node'])
                todo.append(e['from_node'])
    return sorted(chain)


assert not hc.call('editor_get_state', {})['data']['pie_running'], 'PIE running'
for bp, title, old in JOBS:
    nodes, edges = graph(bp)
    comments = [n['node_id'] for n in nodes if n['title'] in old]
    if comments:
        print(bp, 'remove boxes', len(comments), hc.call('blueprint_remove_nodes', {'path': bp, 'graph_name': 'EventGraph',
                                                                                   'node_ids': comments}).get('ok'))
    r = subprocess.run([sys.executable, 'P:/FoA/Tools/Unreal/bp_layout.py', '--apply', bp], capture_output=True, text=True, timeout=110)
    print([l for l in r.stdout.splitlines() if l.startswith('bp_layout')][-1:] or r.stderr[-300:])
    nodes, edges = graph(bp)
    if any(n['title'] == title for n in nodes):
        print(bp, 'box exists')
        continue
    ids = tick_chain(nodes, edges)
    r = hc.call('blueprint_add_comment', {'path': bp, 'graph_name': 'EventGraph', 'title': title, 'node_ids': ids,
                                          'color': [0.30, 0.22, 0.10], 'bubble': True})
    print(bp, title, len(ids), r.get('ok'), (r.get('data') or {}).get('rect'))
    print(hc.call('ui_compile_widget', {'widget_blueprint_path': bp})['data'].get('compiled_clean'),
          hc.call('ui_save_widget', {'widget_blueprint_path': bp})['data'].get('saved'))
