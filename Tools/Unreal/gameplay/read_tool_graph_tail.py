"""Read-only gap: native inspect truncates graph arrays after 50 entries."""
import json,re,unreal
from pathlib import Path
bp=unreal.load_asset('/Game/FoA/Gameplay/BP_Door')
ed=unreal.BlueprintGraphEditor.get_graph_editor_by_name(bp,'RefreshDoorTool')
bel=unreal.BlueprintEditorLibrary;pin=unreal.BlueprintGraphPinLibrary
export=unreal.FoAGraphToolsLibrary.export_nodes_text(bp,'RefreshDoorTool')
ids={re.search(r'Name="([^"]+)"',block).group(1):re.search(r'NodeGuid=([A-F0-9]+)',block).group(1) for block in export.split('Begin Object ')[1:] if 'NodeGuid=' in block}
def guid(n):return ids[n.get_name()]
nodes=[];edges=[]
for n in ed.list_all_nodes():
    nodes.append(dict(node_id=guid(n),title=bel.get_node_title(n).splitlines()[0],pins={str(pin.get_pin_name(p)):str(pin.get_pin_value(p)) for p in bel.list_all_pins(n)}))
    for p in bel.list_output_pins(n):
        for q in pin.list_connected_pins(p):
            edges.append(dict(from_node=guid(n),from_pin=str(pin.get_pin_name(p)),to_node=guid(pin.get_owning_node(q)),to_pin=str(pin.get_pin_name(q))))
sub=unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem);lib=unreal.SubobjectDataBlueprintFunctionLibrary
camera=next(lib.get_object_for_blueprint(lib.get_data(h),bp) for h in sub.k2_gather_subobject_data_for_blueprint(bp) if str(lib.get_variable_name(lib.get_data(h)))=='ToolCamera')
Path('P:/FoA/Saved/Integration/tool_refresh_untruncated.json').write_text(json.dumps(dict(nodes=nodes,edges=edges,camera=camera.get_path_name()),indent=1))
print('Read full graph and camera path')
