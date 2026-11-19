"""Title-only comment boxes (the user's rule) on ABP_FoAPlayer: the template's sentence-long EventGraph comments become
short titles; every box gets the bubble flags. Re-runnable.
  python Tools/Unreal/ue_remote.py Tools/Unreal/player/abp_titles.py FOA_AREAS=/Game/FoA/Characters/Player"""
import unreal

BEL = unreal.BlueprintEditorLibrary
TITLES = {  # template sentence prefix -> title
    "Set references to owning character": "Cache character",
    "Only update values if the character is valid": "Valid character only",
    "Set velocity and ground speed": "Velocity and speed",
    "Set Should Move": "Should move",
    "Set Is Falling": "Is falling",
    "Calculate direction": "Direction",
}
a = unreal.load_asset("/Game/FoA/Characters/Player/ABP_FoAPlayer")
unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(a)
changed = []
for g in BEL.list_graphs(a):
    try:
        ed = unreal.BlueprintGraphEditor.get_graph_editor(g)
    except Exception:
        continue
    for c in ed.list_comment_nodes():
        text = BEL.get_comment_text(c)
        new = next((t for k, t in TITLES.items() if text.startswith(k)), None)
        if new is None and len(text.split()) > 5:
            new = " ".join(text.split()[:4]).rstrip(".,:")
        if new and new != text:
            BEL.set_comment_text(c, new)
            changed.append((g.get_name(), new))
        for prop in ("comment_bubble_visible_in_details_panel", "color_comment_bubble"):
            c.set_editor_property(prop, True)
unreal.EditorAssetLibrary.save_loaded_asset(a, False)
print("titles:", changed)
