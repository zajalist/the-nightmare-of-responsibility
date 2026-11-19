"""Rig lane, editor world (read only): the geometry the hanger-use paths must respect.
  FOA_AREAS=Gameplay python Tools/Unreal/ue_remote.py Tools/Unreal/rig/hanger_geometry.py
Bed: frame and bedding bounds, the underside clearance (traces up from 2 cm above the floor on a grid under the bed),
the director's ClothingShirtSpot / ClothingShirtHome. Door: leaf bounds, the latch side edge, ToolContact.
-> Saved/RigShots/hanger_use/geometry.json"""
import json
from pathlib import Path

import unreal

OUT = Path('P:/FoA/Saved/RigShots/hanger_use/geometry.json')
OUT.parent.mkdir(parents=True, exist_ok=True)
w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
acts = {a.get_actor_label(): a for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()}


def r(v):
    return [round(v.x, 1), round(v.y, 1), round(v.z, 1)]


def bounds(c):
    o, e, _ = unreal.SystemLibrary.get_component_bounds(c)
    return dict(min=r(o - e), max=r(o + e))


def prop(o, n):
    try:
        v = o.get_editor_property(n)
    except Exception as exc:  # noqa: BLE001
        return repr(exc)[:80]
    if isinstance(v, unreal.Vector):
        return r(v)
    if isinstance(v, unreal.Transform):
        return dict(loc=r(v.translation), rot=str(v.rotation.rotator()))
    return v.get_name() if hasattr(v, 'get_name') else str(v)


out = {}
bed, door = acts['Bed'], acts['Door_Bedroom']
out['bed'] = {c.get_name(): bounds(c) for c in bed.get_components_by_class(unreal.StaticMeshComponent)}
out['bedding'] = bounds(acts['Bedding_Lux3D'].get_component_by_class(unreal.StaticMeshComponent))
out['door'] = {c.get_name(): bounds(c) for c in door.get_components_by_class(unreal.StaticMeshComponent)}
out['door_comps'] = {c.get_name(): r(c.get_world_location()) for c in door.get_components_by_class(unreal.SceneComponent)}
out['frame'] = bounds(acts['DoorFrame_Bedroom'].get_component_by_class(unreal.StaticMeshComponent))
d = next(a for a in acts.values() if a.get_class().get_name() == 'BP_BeatDirector_C')
out['director'] = {n: prop(d, n) for n in ('ClothingShirtSpot', 'ClothingShirtHome', 'SearchShirt', 'SearchBed')}
# underside clearance: first hit going up from 2 cm above the floor, on a 10 cm grid over the bed's footprint
b = out['bed']['Mesh']
grid = []
x = b['min'][0] - 10
while x <= b['max'][0] + 10:
    y = b['min'][1] - 10
    while y <= b['max'][1] + 10:
        hit = unreal.SystemLibrary.line_trace_single(w, unreal.Vector(x, y, 2), unreal.Vector(x, y, 120),
                                                     unreal.TraceTypeQuery.ECC_VISIBILITY, True, [], unreal.DrawDebugTrace.NONE, True)
        grid.append([x, y, round(hit.to_tuple()[4].z, 1) if hit and hit.to_tuple()[0] else None,
                     hit.to_tuple()[9].get_actor_label() if hit and hit.to_tuple()[0] and hit.to_tuple()[9] else None])
        y += 10
    x += 10
out['under_bed'] = grid
OUT.write_text(json.dumps(out, indent=1, default=str))
print('GEOM', json.dumps({k: out[k] for k in ('bed', 'bedding', 'door', 'frame', 'director')}, default=str)[:3000])
