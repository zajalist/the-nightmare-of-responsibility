"""Plain UV1 for the bedroom door and its frame (world lane, coordinator's grant 2026-11-10: UV only, no geometry).
M_PaintedWoodTrim samples its carving (T_TrimOrnament_N) with UV1; these two meshes had no UV1, so the carving fell
back to UV0 and stamped across them. Like the window casings, they get no carving: every vertex's UV1 lands in the
sheet's flat column (U = ORN_FLAT_U = 0.04, make_procedural_meshes.py).
  $env:FOA_AREAS='/Game/FoA/Props/Door/SM_Door_Bedroom,/Game/FoA/Props/Door/SM_DoorFrame_Bedroom'
  python Tools/Unreal/ue_remote.py Tools/Unreal/door_uv1_plain.py          (not during PIE: mesh edits refuse there)
How: add channel 1, then a planar projection whose tiling is 1e-4 and whose origin sits 400 mesh-heights away, so
U = 0.04 + (z / height) * 1e-4 (the engine's planar U = ((z - Pos.z + H/2) / H) * TilingX; StaticMeshOperations.cpp).
Proof that no geometry moved (anim's knob grip): a hash of every source vertex position before and after must match.
The Nanite fallback's vertex count may change (it is re-simplified with the new attribute); that is render data only."""
import hashlib

import unreal

MESHES = ('/Game/FoA/Props/Door/SM_Door_Bedroom', '/Game/FoA/Props/Door/SM_DoorFrame_Bedroom')
FLAT_U, TILE = 0.04, 1e-4
SMES = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)


def positions(m):
    d = m.get_static_mesh_description(0)
    h = hashlib.sha1()
    for i in range(d.get_vertex_count()):
        p = d.get_vertex_position(unreal.VertexID(i))
        h.update(f'{p.x:.4f},{p.y:.4f},{p.z:.4f};'.encode())
    return d.get_vertex_count(), h.hexdigest()[:16]


for path in MESHES:
    m = unreal.load_asset(path)
    if SMES.get_num_uv_channels(m, 0) >= 2:   # an earlier unsaved try: start again from the file on disk
        unreal.EditorLoadingAndSavingUtils.reload_packages([m.get_outermost()], unreal.ReloadPackagesInteractionMode.ASSUME_POSITIVE)
        m = unreal.load_asset(path)
    assert SMES.get_num_uv_channels(m, 0) == 1, f'{path}: expected one UV channel on disk'
    before = positions(m)
    assert SMES.add_uv_channel(m, 0), path
    h = m.get_bounding_box().max.z - m.get_bounding_box().min.z
    pos = unreal.Vector(0.0, 0.0, -(FLAT_U / TILE) * h + h / 2.0)   # 400 heights out
    assert SMES.generate_planar_uv_channel(m, 0, 1, pos, unreal.Rotator(0.0, 0.0, 0.0), unreal.Vector2D(TILE, TILE)), path
    after = positions(m)
    assert after == before, f'{path}: source vertices changed {before} -> {after}'
    unreal.EditorAssetLibrary.save_loaded_asset(m)
    print('DOOR UV1', path.rsplit('/', 1)[1], 'uv', SMES.get_num_uv_channels(m, 0), 'source verts + hash', before, 'unchanged')
