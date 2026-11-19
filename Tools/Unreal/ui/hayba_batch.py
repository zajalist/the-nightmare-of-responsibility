"""Small Hayba graph-building kit for UI-lane builders (blueprint_graph_batch with typed nodes only).

    b = B(path, 'MyFunction')
    v = b.fn(KML + ':Add_DoubleDouble', A=b.get('T'), B=0.0167)   # pins: literal, node ref (its ReturnValue) or (ref, pin)
    b.chain(entry_id, b.set('T', v), ...)                          # exec: then -> execute; (ref, 'else') for a branch's False
    b.run()                                                        # one batch; exec row on top, data nodes below
"""
import json
import sys

sys.path.insert(0, 'P:/FoA/Tools/Unreal')
import hayba_call as hc  # noqa: E402


def ok(r, what):
    assert r.get('ok'), (what, r.get('error'), (r.get('data') or {}).get('error'))
    return r.get('data') or {}


def graph(path, g):
    nodes, edges, off = [], [], 0
    while off is not None:
        d = hc.call('blueprint_inspect_graph', {'path': path, 'graph_name': g, 'offset': off})['data']
        nodes += d['nodes']
        off = d['page']['nodes']['next_offset']
    off = 0
    while off is not None:
        d = hc.call('blueprint_inspect_graph', {'path': path, 'graph_name': g, 'edge_offset': off})['data']
        edges += d['edges']
        off = d['page']['edges']['next_offset']
    return nodes, edges


def entry_of(path, g):
    nodes, edges = graph(path, g)
    return next(n['node_id'] for n in nodes if n['title'].replace(' ', '') == g), nodes, edges


def is_empty(path, g):
    nodes, _ = graph(path, g)
    return not [n for n in nodes if n['title'].replace(' ', '') != g and not n['title'].startswith('Return') and n['title'] != 'Comment']


def compile_bp(path, widget=False):
    if widget:
        d = hc.call('ui_compile_widget', {'widget_blueprint_path': path})['data']
        assert d.get('compiled_clean'), (path, d.get('errors'))
    else:
        d = hc.call('blueprint_compile', {'path': path}).get('data') or {}
        assert d.get('compiled') and not d.get('error_count'), (path, d)


def save(path):
    return (hc.call('asset_save', {'asset_paths': [path], 'force': True}).get('data') or {}).get('saved_count')


class B:
    def __init__(s, path, g):
        s.path, s.g, s.ops, s.k, s.refs, s.execs = path, g, [], 0, set(), set()

    def _add(s, spec, pins):
        s.k += 1
        ref = f'n{s.k}'
        s.refs.add(ref)
        s.ops.append(dict(op='add_node', ref=ref, x=0, y=0, **spec))
        s._pins(ref, pins)
        return ref

    def _pins(s, ref, pins):
        for k, v in pins.items():
            if isinstance(v, tuple):
                s.link(v[0], v[1], ref, k)
            elif isinstance(v, str) and v in s.refs:
                s.link(v, 'ReturnValue', ref, k)
            elif v != '':  # an empty string is the pin's default already (set_pin refuses '')
                s.ops.append(dict(op='set_pin', node_id=ref, pin_name=k, value=str(v).lower() if isinstance(v, bool) else str(v)))

    def fn(s, func, **pins):
        return s._add(dict(node_type='call_function', function_name=func), pins)

    def node(s, kind, pins=None, **spec):
        return s._add(dict(node_type=kind, **spec), pins or {})

    def get(s, var, cls=None, target=None):
        ref = s._add(dict(node_type='variable_get', variable_name=var, **({'class_path': cls} if cls else {})),
                     {'self': target} if target else {})
        return (ref, var)

    def set(s, var, value=None, cls=None, target=None):
        pins = {} if value is None else {var: value}
        return s._add(dict(node_type='variable_set', variable_name=var, **({'class_path': cls} if cls else {})),
                      {**pins, **({'self': target} if target else {})})

    def link(s, a, ap, b, bp):
        s.ops.append(dict(op='connect', from_node=a, from_pin=ap, to_node=b, to_pin=bp))

    def chain(s, *refs):
        for a, b in zip(refs, refs[1:]):
            a, ap = a if isinstance(a, tuple) else (a, 'then')
            s.execs.update({a, b})
            s.link(a, ap, b, 'execute')

    def run(s):
        row = [o['ref'] for o in s.ops if o['op'] == 'add_node' and o['ref'] in s.execs]
        data = [o['ref'] for o in s.ops if o['op'] == 'add_node' and o['ref'] not in s.execs]
        for o in s.ops:
            if o['op'] == 'add_node':
                r = o['ref']
                o['x'], o['y'] = ((row.index(r) + 1) * 320, 0) if r in row else ((data.index(r) // 4 + 1) * 300, 260 + (data.index(r) % 4) * 140)
        r = hc.call('blueprint_graph_batch', {'path': s.path, 'graph_name': s.g, 'ops': s.ops})
        d = r.get('data') or {}
        print(s.g, r.get('ok'), d.get('applied'), d.get('failed_index', ''), d.get('error') or r.get('error') or '')
        assert r.get('ok'), (s.g, json.dumps(d)[:400])
        return d
