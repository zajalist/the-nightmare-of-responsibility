"""mech_core: comment boxes keep only their title line (the user's rule, 21:20: no description sentences on graphs).
Position-neutral; touches only comment text on BPC_Inventory, BPC_Interactor and BP_Interactable, then saves."""
import unreal

BEL, GE = unreal.BlueprintEditorLibrary, unreal.BlueprintGraphEditor
for path in ("/Game/FoA/Gameplay/BPC_Inventory", "/Game/FoA/Gameplay/BPC_Interactor", "/Game/FoA/Gameplay/BP_Interactable"):
    bp = unreal.load_asset(path)
    unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(bp)
    changed = 0
    for name in [str(g) for g in BEL.list_graph_names(bp)]:
        ed = GE.get_graph_editor_by_name(bp, name)
        if not ed:
            continue
        for c in ed.list_comment_nodes():
            text = str(BEL.get_comment_text(c))
            title = text.splitlines()[0] if text else text
            if title != text:
                BEL.set_comment_text(c, title)
                changed += 1
    print(path, "titles only:", changed, "saved", unreal.EditorAssetLibrary.save_loaded_asset(bp, False))
