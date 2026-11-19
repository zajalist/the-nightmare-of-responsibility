"""Regroup WBP_IntroStory's graphs under short title-only comments (intro lane), then lay them out with bp_layout.
  python Tools/Unreal/editor_lock.py acquire intro --assets /Game/FoA/UI/Intro
  python Tools/LookDev/intro_v4/graphs_tidy.py            every graph: drop all comments, add one per group
  python Tools/Unreal/bp_layout.py --apply /Game/FoA/UI/Intro/WBP_IntroStory
Each group's nodes are first staged in their own band (comments own nodes by position). Exec nodes start a group by rule (title, plus a pin test where a title repeats) and otherwise inherit their exec
predecessor's; a data node joins the group of the first exec node it feeds. Idempotent: rerunning regroups the same."""
import sys

sys.path[:0] = ['P:/FoA/Tools/Unreal', 'P:/FoA/Tools/Unreal/ui']
import hayba_call as hc  # noqa: E402
from hayba_batch import compile_bp, graph, save  # noqa: E402

W = '/Game/FoA/UI/Intro/WBP_IntroStory'
COLOR = [0.12, 0.16, 0.19]


def pinv(n, name):
    return next((p.get('default_value') or p.get('default_object') for p in n['pins'] if p['name'] == name), None)


def fed_by(n, nodes, edges, pin, title):
    src = next((e['from_node'] for e in edges if e['to_node'] == n['node_id'] and e['to_pin'] == pin), None)
    return src is not None and nodes[src]['title'] == title


# graph: [(group title, rule(node, nodes, edges) -> bool)], first match starts that group
RULES = {
    'EventGraph': [('Start the story', lambda n, N, E: n['title'] == 'Event Construct'),
                   ('Skip any time', lambda n, N, E: n['title'] == 'SkipClicked'),
                   ('Frame clock', lambda n, N, E: n['title'] == 'Event Tick'),
                   ('Clear the timers', lambda n, N, E: n['title'] == 'Event Destruct')],
    'NextPanel': [('Advance or finish', lambda n, N, E: n['title'] == 'NextPanel'),
                  ('Plate and line', lambda n, N, E: n['title'] == 'Set PanelTime'),
                  ('Sound and timing', lambda n, N, E: n['title'] == 'Branch' and fed_by(n, N, E, 'Condition', 'IsValid'))],
    'UpdateFrame': [('Panel clock', lambda n, N, E: n['title'] == 'UpdateFrame'),
                    ('Accessible motion', lambda n, N, E: n['title'] == 'GetScalarParameterValue'),
                    ('Plate clock', lambda n, N, E: n['title'] == 'ApplyLayer')],
    'Finish': [('Complete once', lambda n, N, E: n['title'] == 'Finish'),
               ('Back to the morning', lambda n, N, E: n['title'] == 'Branch' and fed_by(n, N, E, 'Condition', 'IsValid'))],
    'FocusSkip': [('Focus the skip', lambda n, N, E: n['title'] == 'FocusSkip')],
    'ApplyLayer': [('Place the plate', lambda n, N, E: n['title'] == 'ApplyLayer')],
    'EnsureInkMaterials': [('Plate material', lambda n, N, E: n['title'] == 'EnsureInkMaterials')],
    'UpdateInkReveal': [('Plate parameters', lambda n, N, E: n['title'] == 'UpdateInkReveal')],
    'PlayLine': [('Sand line', lambda n, N, E: n['title'] == 'PlayLine')],
    'DismissLine': [('Sand line', lambda n, N, E: n['title'] == 'DismissLine')],
}


def groups(g):
    ns, es = graph(W, g)
    N = {n['node_id']: n for n in ns if n['title'] != 'Comment'}
    exe = {i for i, n in N.items() if any(p.get('type') == 'exec' for p in n['pins'])}
    nxt = {}
    for e in es:
        if e['from_node'] in exe and e['to_node'] in exe and N.get(e['from_node']) and any(
                p['name'] == e['from_pin'] and p.get('type') == 'exec' for p in N[e['from_node']]['pins']):
            nxt.setdefault(e['from_node'], []).append(e['to_node'])
    grp, order = {}, []
    roots = [i for i in exe if not any(e['to_node'] == i and e['from_node'] in exe and e['to_pin'] == 'execute' for e in es)]
    for r in sorted(roots, key=lambda i: N[i]['title']):
        stack = [(r, None)]
        while stack:
            i, inherited = stack.pop()
            if i in grp:
                continue
            g_ = next((t for t, rule in RULES[g] if rule(N[i], N, es)), inherited)
            grp[i] = g_
            order.append(i)
            stack += [(j, g_) for j in reversed(nxt.get(i, []))]
    rank = {i: k for k, i in enumerate(order)}
    for i in N:  # data nodes: the earliest exec node they feed, through other data nodes
        if i in grp:
            continue
        seen, frontier, best = set(), [i], None
        while frontier:
            j = frontier.pop()
            for e in es:
                if e['from_node'] == j and e['to_node'] in N and e['to_node'] not in seen:
                    seen.add(e['to_node'])
                    if e['to_node'] in grp and e['to_node'] in rank:
                        best = e['to_node'] if best is None or rank[e['to_node']] < rank[best] else best
                    elif e['to_node'] not in exe:
                        frontier.append(e['to_node'])
        grp[i] = grp[best] if best else None
    comments = [n['node_id'] for n in ns if n['title'] == 'Comment']
    return comments, grp


def main():
    assert not hc.call('editor_get_state', {})['data']['pie_running'], 'PIE running'
    for g in RULES:
        comments, grp = groups(g)
        missing = [i for i, t in grp.items() if t is None]
        assert not missing, (g, 'ungrouped nodes', missing)
        ops = [dict(op='remove', node_ids=comments)] if comments else []
        # comments own nodes by position: stage each group in its own band first, so no box swallows another's nodes
        for k, title in enumerate(dict.fromkeys(grp.values())):
            for j, i in enumerate(i for i, t in grp.items() if t == title):
                ops.append(dict(op='move', node_id=i, x=420 * (j % 12), y=8000 * k + 360 * (j // 12)))
        for title in dict.fromkeys(grp.values()):
            ops.append(dict(op='comment', title=title, node_ids=[i for i, t in grp.items() if t == title], color=COLOR))
        r = hc.call('blueprint_graph_batch', {'path': W, 'graph_name': g, 'ops': ops})
        d = r.get('data') or {}
        assert r.get('ok') and d.get('applied') == len(ops), (g, d)
        print(g, sorted(set(grp.values())))
    compile_bp(W, widget=True)
    print('tidy comments', save(W))


if __name__ == '__main__':
    main()
