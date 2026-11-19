"""Lets ABP_FoAPlayer and every SK_Mannequin clip drive a mesh on another Manny-hierarchy skeleton (SK_Hero for the
Nightmare, the MetaHuman body for the player): adds SK_Mannequin to that skeleton's Compatible Skeletons.
  python Tools/Unreal/ue_remote.py Tools/Unreal/player/compat_skeleton.py FOA_SKELETON=/Game/FoA/Characters/Hero/SK_Hero_Skeleton"""
import os

import unreal

MANNY = "/Game/Characters/Mannequins/Meshes/SK_Mannequin"


def run():
    sk_path = os.environ.get("FOA_SKELETON")
    target = unreal.load_asset(sk_path) if sk_path else unreal.load_asset(os.environ["FOA_MESH"]).get_editor_property("skeleton")
    manny = unreal.load_asset(MANNY)
    assert isinstance(target, unreal.Skeleton), f"not a skeleton: {sk_path or os.environ.get('FOA_MESH')}"
    have = list(target.get_editor_property("compatible_skeletons"))
    if not any(str(s).endswith("SK_Mannequin.SK_Mannequin") or s == manny for s in have):
        have.append(manny)
        target.set_editor_property("compatible_skeletons", have)
        unreal.EditorAssetLibrary.save_loaded_asset(target, False)
    print(target.get_name(), "compatible with:", [str(s) for s in target.get_editor_property("compatible_skeletons")])
    mesh_path = os.environ.get("FOA_MESH")  # optional: generate the missing physics asset (the 5.8 FBX import skipped it)
    if mesh_path and os.environ.get("FOA_PHYSICS") == "1":
        mesh = unreal.load_asset(mesh_path)
        if not mesh.get_editor_property("physics_asset"):
            pa = unreal.get_editor_subsystem(unreal.SkeletalMeshEditorSubsystem).create_physics_asset(mesh, True)
            unreal.EditorAssetLibrary.save_loaded_asset(mesh, False)
            print("physics asset:", pa.get_path_name() if pa else None)


run()
