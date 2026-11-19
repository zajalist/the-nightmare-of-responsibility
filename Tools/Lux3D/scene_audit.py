"""Read-only scene audit for the AAA pass (world lane): every visible mesh actor's bounds, the gap under it (floating
check by a downward trace that ignores the actor itself), and a texel-density estimate per material slot.
  $env:FOA_AREAS='PostProcess'; python Tools/Unreal/ue_remote.py Tools/Lux3D/scene_audit.py
Writes Saved/WorldShots/scene_audit.json. Floating = more than 1.5 cm of air under the bounds' bottom centre and
under all four bottom corners (wall-hung things like clocks and frames are reported as 'wall' instead).
Texel density = largest base-colour texture width / the mesh's largest world extent (px per metre, a rough upper
bound: a 1 m prop with a 1024 texture reads 1024 px/m when its UVs fill the sheet)."""
import json

import unreal

EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
MEL = unreal.MaterialEditingLibrary
SKIP = ('Room/Walls', 'Room/Trim', 'Room/Windows', 'Lighting', 'Audio', 'Dev', 'FX/LightShafts')
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()


def gap_below(actor, x, y, z):
    hit = unreal.SystemLibrary.line_trace_single(world, unreal.Vector(x, y, z + 0.5), unreal.Vector(x, y, z - 300),
                                                 unreal.TraceTypeQuery.ECC_VISIBILITY, False, [actor],
                                                 unreal.DrawDebugTrace.NONE, True)
    if not hit:
        return None
    t = hit.to_tuple()   # (blocking, initial_overlap, time, distance, location, ...)
    return round(z - t[4].z, 1) if t[0] else None


def max_tex(m):
    if not m:
        return 0
    best = 0
    for t in MEL.get_material_used_textures(m):
        if isinstance(t, unreal.Texture2D):
            best = max(best, t.blueprint_get_size_x())
    return best


rows = []
for a in EAS.get_all_level_actors():
    folder = str(a.get_folder_path())
    if folder.startswith(SKIP) or a.is_hidden_ed():
        continue
    comps = [c for c in a.get_components_by_class(unreal.StaticMeshComponent) if c.is_visible() and c.get_editor_property('static_mesh')]
    if not comps:
        continue
    o, e = a.get_actor_bounds(True)
    if max(e.x, e.y, e.z) < 1:
        continue
    bot = o.z - e.z
    gaps = [gap_below(a, o.x + dx * e.x * 0.8, o.y + dy * e.y * 0.8, bot) for dx, dy in ((0, 0), (1, 1), (1, -1), (-1, 1), (-1, -1))]
    known = [g for g in gaps if g is not None]
    status = 'ok'
    if bot > 2 and known and min(known) > 1.5:
        status = 'floating'
    elif bot > 2 and not known:
        status = 'wall'
    size_m = max(e.x, e.y, e.z) * 2 / 100.0
    mats = []
    for c in comps[:3]:
        for i, m in enumerate(c.get_materials()[:4]):
            px = max_tex(m)
            mats.append({'mat': m.get_path_name() if m else None, 'tex_px': px, 'px_per_m': round(px / size_m) if px and size_m else 0})
    rows.append({'label': a.get_actor_label(), 'folder': folder, 'loc': [round(v) for v in o.to_tuple()],
                 'ext': [round(v, 1) for v in e.to_tuple()], 'bottom': round(bot, 1), 'gaps': gaps, 'status': status,
                 'mesh': comps[0].get_editor_property('static_mesh').get_path_name(), 'mats': mats})

with open('P:/FoA/Saved/WorldShots/scene_audit.json', 'w', encoding='utf-8') as fh:
    json.dump(rows, fh, indent=1)
print('audited', len(rows), 'floating', [r['label'] for r in rows if r['status'] == 'floating'])
print('low texel (<400 px/m)', sorted({r['label'] for r in rows for m in r['mats'] if 0 < m['px_per_m'] < 400}))
