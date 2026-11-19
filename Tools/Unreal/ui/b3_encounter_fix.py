"""QA B3 (main granted WBP_Encounter for exactly these, 2026-11-09), in place with Hayba, idempotent:
  1. Victory hides the battle HUD: RefreshBattlePresentation starts with Branch(BattleState == Victory, the existing
     Equal node) -> SelfBox and EnemyPanel (the item card) Collapsed; else back to their defaults (SelfHitTestInvisible,
     Visible), so a reused widget shows them again next battle. Nothing else sets their visibility.
  2. LogPanel (the subtitle plate) auto-sizes to its text: anchor, alignment, position, padding and the plate stay.
  3. The Victory phase line (SelectString 413D372F, A 'You are dressed.') is empty: the subtitle carries the moment.
Holds an asset lease and releases only its own token (editor_lock.py release ui would free a running sweep's EXCLUSIVE).
  python Tools/Unreal/ui/b3_encounter_fix.py"""
import os
import sys

sys.path.insert(0, 'P:/FoA/Tools/Unreal')
import editor_lock  # noqa: E402
import hayba_call as hc  # noqa: E402

P = '/Game/FoA/Gameplay/Encounter/WBP_Encounter'
G = 'RefreshBattlePresentation'
VIS = '/Script/UMG.Widget:SetVisibility'
FILE = 'P:/FoA/Content/FoA/Gameplay/Encounter/WBP_Encounter.uasset'


def graph():
    nodes, edges, off = [], [], 0
    while off is not None:
        d = hc.call('blueprint_inspect_graph', {'path': P, 'graph_name': G, 'offset': off})['data']
        nodes += d['nodes']
        off = d['page']['nodes']['next_offset']
    off = 0
    while off is not None:
        d = hc.call('blueprint_inspect_graph', {'path': P, 'graph_name': G, 'edge_offset': off})['data']
        edges += d['edges']
        off = d['page']['edges']['next_offset']
    return nodes, edges


def pin(nodes, nid, name):
    return next(p.get('default_value') for n in nodes if n['node_id'] == nid for p in n['pins'] if p['name'] == name)


def report(tag, r):
    d = r.get('data') or {}
    print(tag, r.get('ok'), d.get('applied', ''), d.get('failed_index', ''), d.get('error') or r.get('error') or '')
    return r


assert not hc.call('editor_get_state', {})['data']['pie_running'], 'PIE running'
before = os.path.getmtime(FILE)
token = editor_lock.acquire('ui', wait_s=300, ttl=120, areas=[P])
try:
    # The hide reads SelfBox and EnemyPanel: make them variables FIRST. blueprint_graph_batch is not atomic: at 22:55 a
    # batch that failed on the missing variable kept its first ops, leaving the entry on a Branch with no outputs.
    for w in ('SelfBox', 'EnemyPanel'):
        report(f'{w} is variable', hc.call('ui_set_variable', {'widget_blueprint_path': P, 'widget_name': w, 'is_variable': True}))
    c = hc.call('ui_compile_widget', {'widget_blueprint_path': P})['data']
    assert c.get('compiled_clean'), c
    nodes, edges = graph()
    T = {n['node_id']: n['title'] for n in nodes}
    entry = next(n['node_id'] for n in nodes if n['title'] == G)
    victory = next(n['node_id'] for n in nodes if n['title'].startswith('Equal (Name)') and pin(nodes, n['node_id'], 'B') == 'Victory')
    sel = next(n['node_id'] for n in nodes if n['node_id'].startswith('413D372F'))
    help_get = {n['node_id'] for n in nodes if n['title'] == 'Get Txt_BattleHelp'}
    nxt = next(e['to_node'] for e in edges if e['from_node'] in help_get and e['to_pin'] == 'self' and T[e['to_node']].startswith('SetText'))
    first = [e['to_node'] for e in edges if e['from_node'] == entry and e['from_pin'] == 'then']
    ops = []
    if not any(n['title'] == 'Get SelfBox' for n in nodes):
        if first and T[first[0]] == 'Branch':  # the 22:55 partial batch: reuse its Branch (Condition already = Victory)
            br = first[0]
            assert not [e for e in edges if e['from_node'] == br and e['from_pin'] in ('then', 'else')], 'Branch already wired'
        else:
            assert first == [nxt], (first, nxt)
            ops += [{'op': 'disconnect', 'node_id': entry, 'pin_name': 'then', 'to_node': nxt, 'to_pin': 'execute'},
                    {'op': 'add_node', 'ref': 'br', 'node_type': 'branch', 'x': 240, 'y': -420},
                    {'op': 'connect', 'from_node': victory, 'from_pin': 'ReturnValue', 'to_node': 'br', 'to_pin': 'Condition'},
                    {'op': 'connect', 'from_node': entry, 'from_pin': 'then', 'to_node': 'br', 'to_pin': 'execute'}]
            br = 'br'
        ops += [{'op': 'add_node', 'ref': 'self', 'node_type': 'variable_get', 'variable_name': 'SelfBox', 'x': 420, 'y': -240},
                {'op': 'add_node', 'ref': 'enemy', 'node_type': 'variable_get', 'variable_name': 'EnemyPanel', 'x': 420, 'y': -160}]
        chains = {'then': (('self', 'Collapsed'), ('enemy', 'Collapsed')),
                  'else': (('self', 'SelfHitTestInvisible'), ('enemy', 'Visible'))}
        for row, (branch_pin, steps) in enumerate(chains.items()):
            prev, prev_pin = br, branch_pin
            for col, (target, vis) in enumerate(steps):
                ref = f'v{row}{col}'
                ops += [{'op': 'add_node', 'ref': ref, 'node_type': 'call_function', 'function_name': VIS,
                         'x': 640 + col * 320, 'y': -520 + row * 200},
                        {'op': 'set_pin', 'node_id': ref, 'pin_name': 'InVisibility', 'value': vis},
                        {'op': 'connect', 'from_node': target, 'from_pin': 'SelfBox' if target == 'self' else 'EnemyPanel',
                         'to_node': ref, 'to_pin': 'self'},
                        {'op': 'connect', 'from_node': prev, 'from_pin': prev_pin, 'to_node': ref, 'to_pin': 'execute'}]
                prev, prev_pin = ref, 'then'
            ops += [{'op': 'connect', 'from_node': prev, 'from_pin': 'then', 'to_node': nxt, 'to_pin': 'execute'}]
        ops += [{'op': 'comment', 'title': 'Victory hides the battle HUD',
                 'node_ids': [br, 'self', 'enemy', 'v00', 'v01', 'v10', 'v11'], 'color': [0.12, 0.26, 0.16]}]
    if pin(nodes, sel, 'A'):
        ops += [{'op': 'set_pin', 'node_id': sel, 'pin_name': 'A', 'value': ''}]
    if ops:
        report('graph', hc.call('blueprint_graph_batch', {'path': P, 'graph_name': G, 'ops': ops}))
    report('LogPanel auto size', hc.call('ui_set_widget_properties', {'widget_blueprint_path': P, 'widget_name': 'LogPanel',
                                                                      'slot_props': {'auto_size': True}}))
    c = hc.call('ui_compile_widget', {'widget_blueprint_path': P})['data']
    s = hc.call('ui_save_widget', {'widget_blueprint_path': P})['data']
    print('compiled_clean', c.get('compiled_clean'), 'errors', c.get('errors'), 'warnings', c.get('warnings'), 'saved', s.get('saved'))
finally:
    if token:
        hc.release('ui', token)
        editor_lock.forget('ui', token)
# verify from the editor and on disk (story: asset_save can skip a Python-edited asset as "not dirty")
nodes, edges = graph()
slot = (hc.call('object_get_property', {'path': f'{P}.WBP_Encounter:WidgetTree.LogPanel', 'properties': ['Slot']}).get('data') or {}).get('properties', {}).get('Slot', '')
auto = (hc.call('object_get_property', {'path': str(slot).split("'")[1]}).get('data') or {}).get('properties', {}).get('bAutoSize')
vis = sorted(pin(nodes, n['node_id'], 'InVisibility') for n in nodes if n['title'] == 'SetVisibility' and
             any(e['to_node'] == n['node_id'] and e['to_pin'] == 'self' and e['from_node'] in
                 {m['node_id'] for m in nodes if m['title'] in ('Get SelfBox', 'Get EnemyPanel')} for e in edges))
print('victory line', repr(pin(nodes, sel, 'A')), '| LogPanel bAutoSize', auto, '| hide/show', vis,
      '| uasset rewritten', os.path.getmtime(FILE) > before)
br = [e['to_node'] for e in edges if e['from_node'] == entry and e['from_pin'] == 'then']
arms = {e['from_pin'] for e in edges if br and e['from_node'] == br[0] and e['from_pin'] in ('then', 'else')}
print('entry ->', [n['title'] for n in nodes if n['node_id'] in br], '| arms wired', sorted(arms))
assert not pin(nodes, sel, 'A') and str(auto) == 'True' and len(vis) == 4 and arms == {'then', 'else'} and \
    os.path.getmtime(FILE) > before
