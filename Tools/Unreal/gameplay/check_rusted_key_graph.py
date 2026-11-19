"""Offline execution of the exported Blueprint's numeric/branch wiring, not a PIE proof.

Consumes Saved/Integration/rusted_key_graph.json from native blueprint_inspect_graph.
Sound, refresh and commit calls are observed boundary effects rather than executed.
"""
import json
from pathlib import Path

graph = json.loads(Path('Saved/Integration/rusted_key_graph.json').read_text())
nodes = {n['node_id']: n for n in graph['nodes']}
incoming = {(e['to_node'], e['to_pin']): (e['from_node'], e['from_pin']) for e in graph['edges']}
outgoing = {(e['from_node'], e['from_pin']): e['to_node'] for e in graph['edges']
            if e['to_pin'] == 'execute'}
entry = next(k for k, n in nodes.items() if n['title'] == 'AdvanceDoorTool')

def initial(mode='Key'):
    return dict(bToolActive=True, bToolReady=True, ToolMode=mode, ToolAngle=0., ToolInputAngle=0.,
                ToolStepIndex=0, finished=0)

def advance(state, turn, dt):
    args = {'Turn': turn, 'DeltaSeconds': dt}

    def read(node, pin):
        if (node, pin) in incoming:return evaluate(*incoming[node, pin])
        p = next(p for p in nodes[node]['pins'] if p['name'] == pin)
        value = p.get('default_value', '')
        if p['type'] == 'real':return float(value or 0)
        if p['type'] == 'int':return int(value or 0)
        if p['type'] == 'bool':return value.lower() == 'true'
        return value

    def evaluate(node, pin):
        title = nodes[node]['title']
        r = lambda name: read(node, name)
        if node == entry:return args[pin]
        if title.startswith('Get '):return state[title[4:]]
        if title.startswith(('MakeLiteral', 'Make Literal')):return r('Value')
        if title == 'Clamp (Float)':return max(r('Min'), min(r('Max'), r('Value')))
        if title == 'Min (Float)':return min(r('A'), r('B'))
        if title == 'AND Boolean':return r('A') and r('B')
        if title.startswith('Equal ('):return r('A') == r('B')
        if ' * ' in title:return r('A') * r('B')
        if ' + ' in title:return r('A') + r('B')
        if ' >= ' in title:return r('A') >= r('B')
        if ' <= ' in title:return r('A') <= r('B')
        raise AssertionError((title, pin))

    node = outgoing[entry, 'then']
    for _ in range(50):
        title = nodes[node]['title']; output = 'then'
        if title == 'Branch':output = 'then' if read(node, 'Condition') else 'else'
        elif title.startswith('Set '):state[title[4:]] = read(node, title[4:])
        elif title == 'FinishDoorTool':
            state['finished'] += 1; state['bToolActive'] = False; return
        elif title not in ('PlaySoundAtLocation', 'RefreshDoorTool'):raise AssertionError(title)
        node = outgoing.get((node, output))
        if node is None:return
    raise AssertionError('Unexpected exec cycle')

for dt in (1/120, 1/30, .1):
    s = initial()
    for _ in range(int(30/dt)):advance(s, 1, dt)
    assert s['ToolStepIndex'] == 2 and s['ToolAngle'] == 42 and not s['finished'], s
    frozen = dict(s)
    for _ in range(100):advance(s, 0, dt)
    assert s == frozen, (s, frozen)
    s = initial(); elapsed = 0
    while not s['finished'] and elapsed < 20:
        advance(s, -1 if s['ToolStepIndex'] == 2 else 1, dt); elapsed += dt
    assert 10 <= elapsed <= 15 and s['finished'] == 1, (dt, elapsed, s)
    for _ in range(10):advance(s, 1, dt)
    assert s['finished'] == 1, s
    print(f'Graph wiring passed at {1/dt:.0f} Hz: active input {elapsed:.3f}s; mandatory reversal; idle and repeated finish safe')

s = initial('Screwdriver')
for _ in range(400):advance(s, 1, 1/30)
assert s['finished'] == 1 and s['ToolStepIndex'] == 4, s
print('Existing four-screw branch passed; no Unreal runtime or visual claim')
