"""Summarise a hayba blueprint_inspect_graph dump: node id, title, non-default literal pins, and edges."""
import json, sys
d = json.load(open(sys.argv[1]))['data']
ids = {}
for n in d['nodes']:
    ids[n['node_id']] = n['title'].replace('\n', ' ')
    lits = [f"{p['name']}={p.get('default_value', p.get('default'))}" for p in n.get('pins', [])
            if p.get('direction') == 'input' and p.get('type') != 'exec' and (p.get('default_value') or p.get('default')) not in (None, '')]
    print(n['node_id'][:8], ids[n['node_id']], ' '.join(lits))
print('edges', len(d.get('edges', [])), 'keys', [k for k in d if k not in ('nodes', 'edges')])
if len(sys.argv) > 2:
    for e in d.get('edges', []):
        print('  ', e)
