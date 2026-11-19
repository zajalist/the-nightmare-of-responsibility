"""Imports FoA's TTFs as Font Face assets (lazy-loaded) under /Game/FoA/UI/Fonts/Faces.
  python Tools/Unreal/ue_remote.py Tools/Unreal/import_fonts.py
Sources and licenses: P:/FoA-Assets/fonts/SOURCES.txt. Composite fonts are built by make_fonts.py."""
import os

import unreal

SRC = "P:/FoA-Assets/fonts"
DEST = "/Game/FoA/UI/Fonts/Faces"
FACES = {
    "DarkerGrotesque": ["Medium", "SemiBold", "ExtraBold"],  # the project typeface (500, 600, 800)
}

tasks = []
for fam, styles in FACES.items():
    for s in styles:
        name = f"FF_{fam}_{s}"
        if unreal.EditorAssetLibrary.does_asset_exist(f"{DEST}/{name}"):
            continue
        t = unreal.AssetImportTask()
        t.set_editor_property("filename", f"{SRC}/{fam}/{fam}-{s}.ttf")
        t.set_editor_property("destination_path", DEST)
        t.set_editor_property("destination_name", name)
        t.set_editor_property("automated", True)  # no "also create a Font asset?" dialog
        t.set_editor_property("save", False)
        tasks.append(t)
unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks(tasks)

for fam, styles in FACES.items():
    for s in styles:
        path = f"{DEST}/FF_{fam}_{s}"
        face = unreal.load_asset(path)
        assert isinstance(face, unreal.FontFace), f"import failed: {path} -> {face}"
        # LazyLoad: whole face loads into memory on first use; these are 0.1-1 MB so streaming buys nothing.
        face.set_editor_property("loading_policy", unreal.FontLoadingPolicy.LAZY_LOAD)
        face.set_editor_property("hinting", unreal.FontHinting.DEFAULT)
        unreal.EditorAssetLibrary.save_asset(path, only_if_is_dirty=False)
print("faces ok:", sum(len(v) for v in FACES.values()))
