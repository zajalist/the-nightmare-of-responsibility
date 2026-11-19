"""Imports the Quaternius Universal Animation Library packs (CC0) as their own skeletons, ready for IK retargeting.
  python Tools/Unreal/ue_remote.py Tools/Unreal/player/import_ual.py
Sources + licenses: P:/FoA-Assets/animation/SOURCES.txt. Quaternius' own setup notes: skeleton None, keep the T pose,
bake at 30 Hz (the clips are 30 fps)."""
import unreal

SRC = "P:/FoA-Assets/animation"
DEST = "/Game/FoA/Characters/Player/Source"
PACKS = {
    "UAL1": SRC + "/quaternius_ual1/Animation Library[Standard]/Unreal Engine/AL_Standard.fbx",
    "UAL2": SRC + "/quaternius_ual2/Universal Animation Library 2 [Standard]/Unreal-Godot/UAL2_Standard.glb",
}
EAL = unreal.EditorAssetLibrary

tasks = []
for pack, path in PACKS.items():
    if EAL.does_directory_exist(f"{DEST}/{pack}") and EAL.list_assets(f"{DEST}/{pack}"):
        print("SKIP already imported", pack)
        continue
    pipe = unreal.InterchangeGenericAssetsPipeline()
    anim = pipe.get_editor_property("animation_pipeline")
    anim.set_editor_property("import_animations", True)
    anim.set_editor_property("use30_hz_to_bake_bone_animation", True)
    t = unreal.AssetImportTask()
    for k, v in (("filename", path), ("destination_path", f"{DEST}/{pack}"), ("automated", True),
                 ("replace_existing", True), ("save", True), ("options", pipe)):
        t.set_editor_property(k, v)
    tasks.append((pack, t))
unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([t for _, t in tasks])
for pack in PACKS:
    assets = EAL.list_assets(f"{DEST}/{pack}", recursive=True, include_folder=False)
    kinds = {}
    for a in assets:
        cls = unreal.EditorAssetLibrary.find_asset_data(a).asset_class_path.asset_name
        kinds.setdefault(str(cls), []).append(a.split("/")[-1].split(".")[0])
    for cls, names in kinds.items():
        print(pack, cls, len(names), names[:6] if cls == "AnimSequence" else names)
