"""Door-tool lane: the screwdriver tip stays seated in the slot while the screw backs out. In RefreshDoorTool the
screw contact (MakeVector X = -1.17 cm, the screw head's face) becomes -1.17 - Out, the same Out that
PlaceSelectedToolScrew moves the screw by ("Back the screw out" group). The key's contact is untouched.
Idempotent. One Hayba batch, compiled 0/0, saved.
  $env:HAYBA_AGENT_ID='doortool'; python Tools/Unreal/doortool/tip_follows.py"""
import sys

sys.path[:0] = ['P:/FoA/Tools/Unreal', 'P:/FoA/Tools/Unreal/player']
from hayba_call import call  # noqa: E402
from held_tool_graphs import Batch, inspect, K  # noqa: E402

DOOR, G = '/Game/FoA/Gameplay/BP_Door', 'RefreshDoorTool'
nodes, edges = inspect(DOOR, G)
by = {n['node_id']: n for n in nodes}
face = [n['node_id'] for n in nodes if n['title'] in ('Make Vector', 'MakeVector') and any(
    p.get('name') == 'X' and str(p.get('default_value', '')).startswith('-1.17') for p in n.get('pins', []))]
assert len(face) == 1, face
if any(e['to_node'] == face[0] and e['to_pin'] == 'X' for e in edges):
    sys.exit(print('already follows'))
place = [n['node_id'] for n in nodes if n['title'] == 'PlaceSelectedToolScrew']
assert len(place) == 1, place
out = next(e for e in edges if e['to_node'] == place[0] and e['to_pin'] == 'Out')
b = Batch(DOOR, G)
b.fn('seated', K + 'Subtract_DoubleDouble', 600, 1250, A=-1.17)
b.link(out['from_node'], out['from_pin'], 'seated', 'B')
b.link('seated', 'ReturnValue', face[0], 'X')
b.run()
