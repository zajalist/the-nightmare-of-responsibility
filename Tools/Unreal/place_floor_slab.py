"""The bedroom Floor follows the room outline (world lane, approved 2026-11-10): Floor was the engine cube scaled to
810 x 750, so its corners showed through the bay's angled windows (3 and 5). Same actor, label, material and folder;
only its mesh and transform change. Mesh: make_procedural_meshes.floor_slab() (P:/FoA-Assets/procedural/floor).
  $env:FOA_AREAS='/Game/FoA/Procedural/SM_FloorSlab'; python Tools/Unreal/ue_remote.py Tools/Unreal/place_floor_slab.py FOA_FLOOR_STEP=import
  $env:FOA_ACTORS='Floor'; python Tools/Unreal/ue_remote.py Tools/Unreal/place_floor_slab.py FOA_FLOOR_STEP=place
then (only when every dirty change in the bedroom is attributable): python Tools/Unreal/editor_lock.py save_level world"""
import os

import unreal

SRC, DEST = 'P:/FoA-Assets/procedural/floor/SM_FloorSlab.gltf', '/Game/FoA/Procedural/SM_FloorSlab'
EAL = unreal.EditorAssetLibrary
SMES = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)


def mesh():
    for p in EAL.list_assets(DEST, recursive=True, include_folder=False):
        a = EAL.load_asset(p)
        if isinstance(a, unreal.StaticMesh):
            return a
    return None


def do_import():
    t = unreal.AssetImportTask()
    for k, v in (('filename', SRC), ('destination_path', DEST), ('automated', True), ('replace_existing', True), ('save', False)):
        t.set_editor_property(k, v)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([t])
    m = mesh()
    assert m, 'import failed'
    ns = SMES.get_nanite_settings(m)
    ns.set_editor_property('enabled', False)
    SMES.set_nanite_settings(m, ns, True)
    # the player walks on it: exact collision (the bay corners are angled, a box would be wrong)
    m.get_editor_property('body_setup').set_editor_property('collision_trace_flag', unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
    EAL.save_loaded_asset(m)
    bb = m.get_bounding_box()
    print('FLOOR import', m.get_path_name(), 'tris', m.get_num_triangles(0), 'bounds', bb.min, bb.max)


def do_place():
    floor = [a for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors() if a.get_actor_label() == 'Floor']
    assert len(floor) == 1, len(floor)
    a = floor[0]
    c = a.static_mesh_component
    a.modify()   # mark the level dirty: plain Python sets do not, so a save would skip the change
    c.modify()
    mat, profile = c.get_material(0), c.get_collision_profile_name()
    c.set_static_mesh(mesh())
    c.set_material(0, mat)
    a.set_actor_location(unreal.Vector(0.0, 0.0, 0.0), False, False)
    a.set_actor_scale3d(unreal.Vector(1.0, 1.0, 1.0))
    c.set_collision_profile_name(profile)
    o, e = a.get_actor_bounds(False)
    print('FLOOR placed', a.get_actor_label(), str(a.get_folder_path()), mat.get_name(), profile,
          f'x {o.x - e.x:.0f}..{o.x + e.x:.0f} y {o.y - e.y:.0f}..{o.y + e.y:.0f} z {o.z - e.z:.0f}..{o.z + e.z:.0f}')


{'import': do_import, 'place': do_place}[os.environ['FOA_FLOOR_STEP']]()
