"""Story lane, read only: the coat-rail hanger's mesh extents and its components, to lay it flat on the floor."""
import json
import unreal
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
h = next(a for a in eas.get_all_level_actors() if a.get_actor_label() == 'Hanger_CoatRail')
out = dict(actor_rot=h.get_actor_rotation().to_tuple(), comps=[])
for c in h.get_components_by_class(unreal.StaticMeshComponent):
    m = c.get_editor_property('static_mesh')
    b = m.get_bounds() if m else None
    out['comps'].append(dict(name=c.get_name(), mesh=m.get_name() if m else None, rel_loc=c.get_editor_property('relative_location').to_tuple(),
                             rel_rot=c.get_editor_property('relative_rotation').to_tuple(), scale=c.get_editor_property('relative_scale3d').to_tuple(),
                             mesh_origin=b.origin.to_tuple() if b else None, mesh_extent=b.box_extent.to_tuple() if b else None,
                             world_bounds=[v.to_tuple() for v in unreal.SystemLibrary.get_component_bounds(c)[:2]]))
open('P:/FoA/Saved/StoryShots/hanger_mesh.json', 'w').write(json.dumps(out, indent=1, default=str))
