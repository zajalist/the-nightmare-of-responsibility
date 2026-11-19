"""Turn lean fix: KismetMaterialLibrary.GetScalarParameterValue (ReduceMotion) is impure, so it must sit on the exec
path or the compiler prunes it and Reduce Motion is ignored (editor-rules: impure nodes on the exec path)."""
import sys
sys.path[:0] = ['P:/FoA/Tools/Unreal', 'P:/FoA/Tools/Unreal/player']
from held_tool_graphs import Batch, inspect, find  # noqa: E402
P, F = '/Game/FoA/Characters/Player/BP_FoAPlayer', 'UpdateFirstPersonVisibility'
nodes, edges = inspect(P, F)
rm = find(nodes, 'GetScalarParameterValue')
setroll = find(nodes, 'Set CamRoll')
if any(e['to_node'] == rm and e['to_pin'] == 'execute' for e in edges):
    sys.exit('already on the exec path')
ins = [e for e in edges if e['to_node'] == setroll and e['to_pin'] == 'execute']  # the look branch has two
b = Batch(P, F)
for e in ins:
    b.cut(e['from_node'], e['from_pin'], setroll, 'execute'); b.link(e['from_node'], e['from_pin'], rm, 'execute')
b.link(rm, 'then', setroll, 'execute')
b.run()
