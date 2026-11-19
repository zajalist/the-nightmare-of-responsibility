"""Repair: PhoneTap's Mesh getter must be a self member (no class_path), then compile and save BP_FoAPlayer."""
import sys
sys.path[:0] = ['P:/FoA/Tools/Unreal', 'P:/FoA/Tools/Unreal/player']
import hayba_call as h
from held_tool_graphs import Batch, inspect, find
P = '/Game/FoA/Characters/Player/BP_FoAPlayer'
assert not h.call('editor_get_state')['data']['pie_running'], 'PIE running'
nodes, edges = inspect(P, 'PhoneTap')
bad = [n['node_id'] for n in nodes if n['title'] == 'Get Mesh']
outs = [e for e in edges if e['from_node'] in bad]
b = Batch(P, 'PhoneTap')
b.ops.append(dict(op='remove', node_ids=bad))
b.get('mesh2', 'Mesh', 0, 300)
for e in outs:
    b.link('mesh2', 'Mesh', e['to_node'], e['to_pin'])
b.run()
