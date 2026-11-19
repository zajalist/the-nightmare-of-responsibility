"""Story lane, read only: print a Blueprint graph as nodes (with non-default pins) and exec/data links.
  python Tools/Unreal/flow/dump_graph.py /Game/FoA/Gameplay/Encounter/BP_Encounter EndEncounter [more graphs...]   (Git Bash: export MSYS_NO_PATHCONV=1)"""
import os
import sys

sys.path[:0] = ['P:/FoA/Tools/Unreal', 'P:/FoA/Tools/Unreal/player']
os.environ.setdefault('HAYBA_AGENT_ID', 'story')
from held_tool_graphs import inspect  # noqa: E402

SKIP = (None, '', '0', '0.0', '0.000000', 'false', 'None', '(X=0.000000,Y=0.000000,Z=0.000000)')
path = sys.argv[1]
for graph in sys.argv[2:]:
    ns, es = inspect(path, graph)
    by = {n['node_id']: '%s#%s' % (n['title'], n['node_id'][:4]) for n in ns}
    print('==', graph, len(ns), 'nodes')
    for n in ns:
        if n['title'] == 'Comment':
            continue
        dv = {p['name']: p.get('default_value') for p in n['pins']
              if p.get('direction') == 'input' and p.get('default_value') not in SKIP and p['name'] not in ('self',)}
        print('  ', by[n['node_id']], dv or '')
    for e in es:
        print('     ', by.get(e['from_node']), e['from_pin'], '->', by.get(e['to_node']), e['to_pin'])
