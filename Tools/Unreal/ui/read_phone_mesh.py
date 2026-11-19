"""Read-only: SM_Phone's material slots, bounds, and the screen section (slot 1) centre and normal, from LOD0 vertices.
Writes Saved/UIShots/aaa/phone_mesh.json (ue_remote truncates prints)."""
import json
import unreal

m = unreal.load_asset('/Game/FoA/UI/Game/BP_Phone')  # noqa: F841 (keeps the BP loaded with its mesh reference)
sm = None
for p in ('/Game/FoA/Props/Phone/SM_Phone', '/Game/FoA/UI/Game/SM_Phone'):
    if unreal.EditorAssetLibrary.does_asset_exist(p):
        sm = unreal.load_asset(p)
        break
if sm is None:
    reg = unreal.AssetRegistryHelpers.get_asset_registry()
    hits = [a for a in reg.get_assets_by_class(unreal.TopLevelAssetPath('/Script/Engine', 'StaticMesh'))
            if str(a.asset_name) == 'SM_Phone']
    sm = hits[0].get_asset() if hits else None
out = {'mesh': sm.get_path_name() if sm else None}
if sm:
    out['slots'] = [(i, str(s.material_slot_name), s.material_interface.get_path_name() if s.material_interface else None)
                    for i, s in enumerate(sm.static_materials)]
    b = sm.get_bounding_box()
    out['bounds'] = [[b.min.x, b.min.y, b.min.z], [b.max.x, b.max.y, b.max.z]]
    sub = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
    out['sections'] = sub.get_number_materials(sm) if hasattr(sub, 'get_number_materials') else None
    try:
        desc = sm.get_static_mesh_description(0)
        vs = {}
        for pid in range(desc.get_polygon_count()):
            poly = unreal.PolygonID(pid)
            g = desc.get_polygon_polygon_group(poly).id_value
            for vi in desc.get_polygon_vertex_instances(poly):
                v = desc.get_vertex_instance_vertex(vi)
                pos = desc.get_vertex_position(v)
                vs.setdefault(g, []).append((pos.x, pos.y, pos.z))
        for g, pts in vs.items():
            xs, ys, zs = zip(*pts)
            out.setdefault('groups', {})[g] = {'n': len(pts), 'min': [min(xs), min(ys), min(zs)], 'max': [max(xs), max(ys), max(zs)]}
    except Exception as e:  # noqa: BLE001 (read-only probe; report and continue)
        out['desc_error'] = repr(e)
open('P:/FoA/Saved/UIShots/aaa/phone_mesh.json', 'w').write(json.dumps(out, indent=1))
print('ok', out.get('mesh'))
