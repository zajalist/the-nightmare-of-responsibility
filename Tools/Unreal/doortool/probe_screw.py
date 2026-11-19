"""Door-tool lane: read-only, Door_Bedroom's ToolScrew0 in the level: mesh bounds, relative rotation and scale."""
import unreal

door = next(a for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors() if a.get_actor_label() == 'Door_Bedroom')
rows = []
for c in door.get_components_by_class(unreal.StaticMeshComponent):
    if c.get_name() in ('ToolScrew0', 'ToolScrew3', 'ToolPlate'):
        m = c.get_editor_property('static_mesh')
        bb = m.get_bounding_box()
        rows.append('%s %s rot %s scale %s bounds %s %s mats %s' % (
            c.get_name(), m.get_path_name(), c.get_editor_property('relative_rotation'), c.get_editor_property('relative_scale3d').to_tuple(),
            [round(v, 3) for v in bb.min.to_tuple()], [round(v, 3) for v in bb.max.to_tuple()], [x.get_path_name() for x in c.get_materials()]))
open('P:/FoA/Saved/QA/lanes/doortool/screw.txt', 'w').write('\n'.join(rows))
print('ROWS', len(rows))
