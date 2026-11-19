"""Build/capture the current user reference through the existing Creator workflow."""
import importlib
import os
import sys
import unreal
import json

sys.path.insert(0, "P:/FoA/Tools/Unreal")
import mh_faces
importlib.reload(mh_faces)

assert not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world(), "Exit PIE first"
step = os.environ.get("FOA_STEP", "face")
face = os.environ.get("FOA_FACE", "N")
assert face in ("M", "N"), face
path = "/Game/FoA/Characters/Protagonist/Faces/MHC_Face_" + face
mh_faces.FACE = face
mh_faces.face_path = lambda _: path
os.environ["FOA_PRESERVE_BODY"] = "1"
assert abs(sum(mh_faces.DIRS[face]["mix"].values()) - 1.0) < 1e-6
if step == "face":
    if not unreal.EditorAssetLibrary.does_asset_exist(path):
        assert unreal.EditorAssetLibrary.duplicate_asset(mh_faces.SRC, path)
    mh_faces.step_face()
elif step == "body":
    ch = unreal.load_asset(path)
    assert ch
    if mh_faces.SUB.is_object_added_for_editing(ch):
        mh_faces.SUB.remove_object_to_edit(ch)
    mh_faces.edit(ch)
    try:
        targets = {"height": 170.0, "chest": 94.0, "underbust": 87.0, "waist": 80.0,
                   "hip": 94.0, "high_hip": 88.0, "neck_base": 37.5, "neck": 34.5,
                   "across_shoulder": 41.0, "bicep": 28.0, "forearm": 25.0,
                   "thigh": 53.0, "calf": 35.0, "wrist": 16.0}
        constraints = mh_faces.SUB.get_body_constraints(ch)
        before = {str(c.name): c.target_measurement for c in constraints if c.is_active}
        found = set()
        for index, c in enumerate(constraints):
            key = str(c.name).lower().replace(" ", "_")
            c.is_active = key in targets
            if c.is_active:
                c.target_measurement = targets[key]
                found.add(key)
            constraints[index] = c
        assert found == set(targets), (found, set(targets) - found)
        mh_faces.SUB.set_body_constraints(ch, constraints)
        mh_faces.SUB.commit_body_state(ch)
        applied = {str(c.name).lower().replace(" ", "_"): c.target_measurement
                   for c in mh_faces.SUB.get_body_constraints(ch) if c.is_active}
        assert set(applied) == set(targets) and all(abs(applied[k] - targets[k]) < 0.001 for k in targets), applied
        assert unreal.EditorAssetLibrary.save_loaded_asset(ch, False)
        with open("P:/FoA/Saved/CharacterShots/teen_body_refinement.json", "w") as f:
            json.dump({"source": path, "before": before, "targets": targets, "applied": applied,
                       "status": "source_saved_requires_visual_review"}, f, indent=2)
        print("TEEN body proportions committed; review profile before runtime replacement", targets)
    finally:
        mh_faces.done(ch)
elif step == "shoot":
    mh_faces.OUT = "P:/FoA/Saved/CharacterShots/reference_teen"
    mh_faces.WAIT = 8.0
    mh_faces.step_shoot()
else:
    raise ValueError(step)
