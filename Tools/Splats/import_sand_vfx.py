"""Imports one splat-mesh glTF from P:/FoA-Assets/splatmesh into /Game/FoA/VFX/Splats/Meshes, set up for M_SplatMesh.
One mesh per run keeps each editor call short (shared editor, crash-safety rule 5):

  python Tools/Unreal/ue_remote.py Tools/Splats/import_sand_vfx.py FOA_SPLAT_MESH=SM_SandStream

Setup (Tools/Splats/README.md): Nanite off (classic path for WPO on low-end), no lightmap UVs (all 8 UV channels carry
data), full-precision UVs (the seed encodes role + randomness and needs float32), no distance field, no recomputed
normals/tangents, and bounds padded by how far the material moves splats from their rest positions.

No rename/delete: deleting assets from editor Python while wrappers to them are alive crashed the shared editor
(python311.dll access violation, 22:27), so new meshes stay where Interchange puts them,
Meshes/<name>/<name>/StaticMeshes/<name> (the same layout as /Game/FoA/Procedural).
"""
import os

import unreal

SRC = "P:/FoA-Assets/splatmesh"
DST = "/Game/FoA/VFX/Splats/Meshes"
PAD = {  # (+x +y +z, -x -y -z) cm in mesh-local space
    "SM_SandStream": ((30, 30, 30), (30, 30, 10)),            # splash and dust beyond the pile, wisps above the lip
    "SM_SandMoundSplats_A": ((45, 45, 90), (45, 45, 5)),      # saltation downwind, wisps rising
    "SM_SandMoundSplats_B": ((45, 45, 90), (45, 45, 5)),
    "SM_SandMoundSplats_C": ((45, 45, 90), (45, 45, 5)),
    "fear_of_adulthood_clock": ((35, 35, 30), (35, 35, 20)),  # vents in the sand around and below the clock
    "SM_TheNightMare": ((40, 40, 40), (40, 80, 10)),         # leg swing, mane/tail tendrils trailing back, dissolve scatter
    "SM_SandBurst": ((160, 160, 160), (160, 160, 160)),       # grains fly up to ~1.5 m before they fade
    "SM_SandFaceDrift": ((30, 30, 30), (40, 30, 60)),         # flakes sink and trail behind the head
    "SM_AlarmClockSplats": ((40, 40, 20), (40, 40, 10)),      # crumbles onto the nightstand and spreads
    "SM_SandCrumbs_Path": ((20, 20, 10), (20, 20, 5)),       # loose grains creep a few cm along the boards
    "SM_SandMorph_Commode": ((30, 30, 45), (30, 30, 10)),   # the chain of objects rises out of the sand dome
    "SM_SandMorph_Desk": ((25, 25, 35), (25, 25, 10)),   # the chain of objects rises out of the sand dome
    "SM_SandMorph_Floor": ((45, 45, 75), (45, 45, 10)),   # the chain of objects rises out of the sand dome
    "SM_SandCrumbs_Hearth": ((20, 20, 10), (20, 20, 5)),       # loose grains creep a few cm along the boards
    "SM_SandCrumbs_Bay": ((20, 20, 10), (20, 20, 5)),       # loose grains creep a few cm along the boards
    "SM_SandShirtImprint": ((30, 30, 30), (30, 30, 5)),     # world lane: the T8 shirt as a floor imprint, crumbles outward
    "SM_SandSuit": ((40, 40, 20), (40, 40, 5)),             # world lane: the T9 suit standing in sand, falls to the floor
    "SM_SandHourglass": ((40, 40, 20), (40, 40, 10)),       # world lane: the time motif on the desk
    "SM_SandTrickle_Ceiling": ((20, 20, 10), (20, 20, 10)),  # world lane: a 3 m pour from the ceiling (make_trickle.py)
    "SM_SandTrickle_Clock": ((15, 15, 10), (15, 15, 10)),    # world lane: sand leaking out of the wall clock
}
DEST = {"SM_TheNightMare": "_import_SM_TheNightMare"}  # contract path Meshes/SM_TheNightMare: rename_sand_vfx.py moves it
EAL = unreal.EditorAssetLibrary
SMES = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)


def mesh_path(name):
    """Earlier imports were moved to Meshes/<name>; later ones stay in Interchange's layout."""
    for p in (f"{DST}/{name}", f"{DST}/{name}/{name}/StaticMeshes/{name}", f"{DST}/_import_{name}/{name}/StaticMeshes/{name}"):
        if EAL.does_asset_exist(p):
            return p
    return None


def run(name):
    full = mesh_path(name)
    if not full or os.environ.get("FOA_SPLAT_REIMPORT") == "1":           # reimport replaces the mesh in place
        task = unreal.AssetImportTask()
        for k, v in (("filename", f"{SRC}/{name}.gltf"), ("destination_path", f"{DST}/{DEST.get(name, name)}"), ("automated", True),
                     ("replace_existing", True), ("save", False)):
            task.set_editor_property(k, v)
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        full = mesh_path(name)
        if not full:
            print("IMPORT FAILED", name)
            return
    mesh = unreal.load_asset(full)
    ns = SMES.get_nanite_settings(mesh)
    ns.set_editor_property("enabled", False)
    SMES.set_nanite_settings(mesh, ns, True)
    bs = SMES.get_lod_build_settings(mesh, 0)
    for k, v in (("recompute_normals", False), ("recompute_tangents", False), ("generate_lightmap_u_vs", False),
                 ("use_full_precision_u_vs", True), ("distance_field_resolution_scale", 0.0), ("remove_degenerates", False)):
        bs.set_editor_property(k, v)
    SMES.set_lod_build_settings(mesh, 0, bs)
    pos, neg = PAD[name]
    mesh.set_editor_property("positive_bounds_extension", unreal.Vector(*pos))
    mesh.set_editor_property("negative_bounds_extension", unreal.Vector(*neg))
    EAL.save_asset(full, only_if_is_dirty=False)
    print(name, full, "verts", mesh.get_num_vertices(0), "tris", mesh.get_num_triangles(0),
          "uv channels", SMES.get_num_uv_channels(mesh, 0))


run(os.environ["FOA_SPLAT_MESH"])  # in a function: no asset wrappers left in the editor's shared globals
