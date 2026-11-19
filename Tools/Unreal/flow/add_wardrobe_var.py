"""Editor Python (ue_remote): BP_BeatDirector.WardrobeFallPlayer, a LevelSequencePlayer reference (Hayba's
blueprint_add_variable refuses object: types on 5.9, 2026-11-11). No compile here; patch_wardrobe_fall.py compiles."""
import unreal
BEL = unreal.BlueprintEditorLibrary
bp = unreal.load_asset('/Game/FoA/Gameplay/BP_BeatDirector')
have = [str(n) for n in BEL.list_member_variable_names(bp)]
if 'WardrobeFallPlayer' not in have:
    ed = unreal.BlueprintGraphEditor.get_graph_editor_by_name(bp, 'EventGraph')
    assert ed.add_member_variable('WardrobeFallPlayer', BEL.get_object_reference_type(unreal.LevelSequencePlayer), '')
BEL.set_blueprint_variable_category(bp, 'WardrobeFallPlayer', 'Story|Wardrobe')
print('WARDROBE_VAR ok', 'WardrobeFallPlayer' in [str(n) for n in BEL.list_member_variable_names(bp)])
