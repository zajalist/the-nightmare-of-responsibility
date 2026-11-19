"""Extract Creator topology for a local body sculpt, then apply the reviewed vertex target."""
import json
import os
from pathlib import Path
import unreal

assert not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world(), "Exit PIE first"
sub = unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)
ch = unreal.load_asset("/Game/FoA/Characters/Protagonist/Faces/MHC_Face_N")
root = "/Game/FoA/Characters/Protagonist/Teen/Built_N"
out = Path("P:/FoA/Saved/CharacterShots/natural_teen_clay")
if not sub.is_object_added_for_editing(ch):
    assert sub.try_add_object_to_edit(ch)
try:
    if os.environ.get("FOA_STEP", "extract") == "extract":
        result, vertices = sub.get_mesh_for_body_conforming_from_template(
            ch, unreal.load_asset(root + "/Body/MHC_Face_N_Body"),
            unreal.load_asset(root + "/MHC_Face_N_Head"), True)
        assert result == unreal.ImportErrorCode.SUCCESS, result
        points = [[v.x, v.y, v.z] for v in vertices]
        assert len(points) > 20000 and all(all(abs(x) < 200 for x in v) for v in points)
        (out / "creator_vertices_before.json").write_text(json.dumps(points))
        print("BODY SCULPT extracted", len(points), "vertices", str(out))
    else:
        assert os.environ["FOA_STEP"] == "apply"
        original = json.loads((out / "creator_vertices_before.json").read_text())
        target = json.loads((out / "creator_vertices_target.json").read_text())
        assert len(original) == len(target)
        shifts = [sum((a-b)**2 for a,b in zip(p,q))**0.5 for p,q in zip(original,target)]
        assert 0.1 < max(shifts) <= 5.0, max(shifts)
        assert all(p == q for p,q in zip(original,target) if p[2] < 120 or p[2] > 151), "Sculpt escaped upper back/neck"
        vertices = [unreal.Vector3f(*p) for p in target]
        assert sub.set_body_mesh(ch, vertices, False), "Creator rejected sculpt topology"
        assert unreal.EditorAssetLibrary.save_loaded_asset(ch, False)
        print("BODY SCULPT committed", sum(d > 0.001 for d in shifts), "vertices; max cm", max(shifts), "regenerate rig before export")
finally:
    sub.remove_object_to_edit(ch)
