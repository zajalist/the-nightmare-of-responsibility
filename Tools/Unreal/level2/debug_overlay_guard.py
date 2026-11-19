"""WBP_Debug (the ui lane's read-only diagnostic overlay) reads GetPlayerCharacter every 0.25 s in RefreshInteraction
and RefreshInventory; while the player drives, the pawn is BP_L2Car, the character is None, and the cooked game logged
"Accessed None ... CallFunc_GetPlayerCharacter_ReturnValue" 90 times (perf lane, Shipping smoke 11-18 04:12).
This puts an IsValid(GetPlayerCharacter) branch in front of each function's existing first node; the rest is untouched.
Idempotent (a graph whose entry already leads to the guard is skipped). Drive lane, asked by the coordinator.
  python -B Tools/Unreal/level2/debug_overlay_guard.py"""
import os
import sys

sys.path[:0] = ['P:/FoA/Tools/Unreal', 'P:/FoA/Tools/Unreal/ui']
import editor_lock  # noqa: E402
import hayba_call as hc  # noqa: E402
from hayba_batch import B  # noqa: E402

P = '/Game/FoA/UI/Game/WBP_Debug'
OWNER = os.environ.get('HAYBA_AGENT_ID', 'drive')


def guard(graph):
    d = hc.call('blueprint_inspect_graph', {'path': P, 'graph_name': graph})['data']
    nodes = {n['node_id']: n for n in d['nodes']}
    entry = next(n['node_id'] for n in d['nodes'] if n['title'].replace(' ', '') == graph)
    first = next(e['to_node'] for e in d['edges'] if e['from_node'] == entry and e['from_pin'] == 'then')
    pawn = next(i for i, n in nodes.items() if n['title'].replace(' ', '') == 'GetPlayerCharacter')
    guarded = any(e['from_node'] == pawn and nodes[e['to_node']]['title'].replace(' ', '').startswith('IsValid')
                  for e in d['edges'])
    if guarded:
        print(graph, 'already guarded')
        return
    b = B(P, graph)
    valid = b.fn('/Script/Engine.KismetSystemLibrary:IsValid', Object=(pawn, 'ReturnValue'))
    br = b.node('branch', {'Condition': (valid, 'ReturnValue')})
    b.ops.append(dict(op='disconnect', node_id=entry, pin_name='then'))
    b.link(entry, 'then', br, 'execute')
    b.link(br, 'then', first, 'execute')
    b.run()


editor_lock.acquire(OWNER, wait_s=600, ttl=120, areas=[P])
try:
    for name in ('RefreshInteraction', 'RefreshInventory'):
        guard(name)
finally:
    print('compile', hc.call('ui_compile_widget', {'widget_blueprint_path': P}).get('ok'),
          'save', hc.call('ui_save_widget', {'widget_blueprint_path': P}).get('ok'))
    editor_lock.release(OWNER)
