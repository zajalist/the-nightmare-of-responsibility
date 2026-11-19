"""mech_core: list palette entries for the S_Item / S_Interaction struct nodes (diagnostic)."""
import unreal

bp = unreal.load_asset("/Game/FoA/Gameplay/BPC_Inventory")
ed = unreal.BlueprintGraphEditor.get_graph_editor_by_name(bp, "UseUp")
allnodes = [str(a) for a in ed.list_available_nodes([])]
print(len(allnodes), [a for a in allnodes if "S_Item" in a or "S_Interaction" in a][:20])
print([a for a in allnodes if "break" in a.lower() and "struct" in a.lower()][:10])
print([a for a in allnodes if a.lower().startswith("utilities|struct")][:10])
