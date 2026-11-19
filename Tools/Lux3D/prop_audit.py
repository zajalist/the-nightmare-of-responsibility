"""Read-only audit of placeholder props in the open level (world lane, props art pass). Run via ue_remote.py:
  $env:FOA_AREAS='Level'; python Tools/Unreal/ue_remote.py Tools/Lux3D/prop_audit.py
Flags every visible mesh component whose mesh is an engine primitive, whose material is an engine default
(WorldGrid, DefaultMaterial, BasicShapeMaterial) or that samples no texture at all. Writes Saved/WorldShots/prop_audit.json.
"""
import json
import unreal

EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
MEL = unreal.MaterialEditingLibrary
ENGINE_MAT = ('WorldGridMaterial', 'DefaultMaterial', 'BasicShapeMaterial', 'DefaultDeferredDecalMaterial')
SKIP_FOLDERS = ('Room/Walls', 'Lighting', 'Audio')  # walls/lights are other lanes' surfaces; shown separately below


def used_textures(m):
    if not m:
        return 0
    try:
        return len(MEL.get_material_used_textures(m))
    except Exception:  # noqa: BLE001  older binding name
        return len(MEL.get_used_textures(m))


def flags_for(comp):
    out = []
    mesh = comp.get_editor_property('static_mesh') if isinstance(comp, unreal.StaticMeshComponent) else None
    mpath = mesh.get_path_name() if mesh else ''
    if mpath.startswith('/Engine/'):
        out.append('engine_mesh')
    mats = []
    for i in range(comp.get_num_materials()):
        m = comp.get_material(i)
        p = m.get_path_name() if m else 'None'
        tex = used_textures(m)
        mats.append({'slot': i, 'mat': p, 'textures': tex})
        if not m or any(k in p for k in ENGINE_MAT):
            out.append('engine_material')
        elif tex == 0:
            out.append('untextured')
    return mpath, mats, sorted(set(out))


rows = []
for a in EAS.get_all_level_actors():
    folder = str(a.get_folder_path())
    for comp in a.get_components_by_class(unreal.MeshComponent):
        if not comp.is_visible() or isinstance(comp, unreal.SkeletalMeshComponent) and not comp.get_editor_property('skeletal_mesh_asset'):
            continue
        mpath, mats, fl = flags_for(comp)
        if fl:
            o, e = a.get_actor_bounds(False)
            rows.append({'label': a.get_actor_label(), 'folder': folder, 'class': a.get_class().get_name(),
                         'comp': comp.get_name(), 'mesh': mpath, 'mats': mats, 'flags': fl,
                         'loc': [round(o.x), round(o.y), round(o.z)], 'ext': [round(e.x), round(e.y), round(e.z)]})
rows.sort(key=lambda r: (r['folder'], r['label']))
for r in rows:
    print(f"{r['folder']:<24} {r['label']:<36} {r['comp']:<22} {','.join(r['flags']):<28} {r['mesh'].rsplit('/', 1)[-1]:<34} "
          f"{[m['mat'].rsplit('/', 1)[-1] for m in r['mats']]} at {r['loc']} ext {r['ext']}")
with open('P:/FoA/Saved/WorldShots/prop_audit.json', 'w') as f:
    json.dump(rows, f, indent=1)
print('AUDIT rows', len(rows))
