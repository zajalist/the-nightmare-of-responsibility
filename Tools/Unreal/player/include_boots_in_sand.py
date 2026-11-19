"""MakeArray pin-growth gap only; keep the existing transition/cache graphs intact."""
import unreal
P="/Game/FoA/Characters/Player/BP_FoAPlayer"
PARTS=("Body","Face","StartOutfit","Shirt","Trousers","Socks","Tie","Suit","BootsWornMesh","StartPants","StartSocks")
bp=unreal.load_asset(P)
unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(bp)
ed=unreal.BlueprintGraphEditor.get_graph_editor_by_name(bp,"SetSandTransition")
BEL=unreal.BlueprintEditorLibrary;PIN=unreal.BlueprintGraphPinLibrary
nodes=list(ed.list_all_nodes())
array=next(n for n in nodes if BEL.get_node_title(n).replace(" ","")=="MakeArray")
def inputs(node):return [p for p in BEL.list_all_pins(node) if PIN.get_pin_direction(p)==unreal.EdGraphPinDirection.EGPD_INPUT]
def named(node,name):return next(p for p in BEL.list_all_pins(node) if str(PIN.get_pin_name(p))==name)
while len(inputs(array))<len(PARTS):ed.add_node_pin(array)
for index,name in enumerate(PARTS):
    getter=next((n for n in nodes if BEL.get_node_title(n).replace(" ","") in (name,"Get"+name)),None)
    if not getter:
        getter=ed.add_get_member_variable_node(name,"");BEL.set_node_pos(getter,unreal.IntPoint(1120+224*index,768))
    pin=named(array,"["+str(index)+"]")
    PIN.break_pin_links(pin)
    assert PIN.try_create_connection(named(getter,name),pin),name
assert len(inputs(array))==len(PARTS)
assert unreal.EditorAssetLibrary.save_loaded_asset(bp,False)
print("SandParts includes every equipped and starter layer")
