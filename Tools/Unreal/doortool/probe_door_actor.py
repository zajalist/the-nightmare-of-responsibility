"""Door-tool lane: read-only, Door_Bedroom's components in the level (mesh, visible, hidden in game, transform)."""
import unreal

door = next(a for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors() if a.get_actor_label() == 'Door_Bedroom')
print('DOOR', door.get_actor_location(), door.get_actor_rotation())
rows = []
for c in door.get_components_by_class(unreal.SceneComponent):
    m = c.get_editor_property('static_mesh') if isinstance(c, unreal.StaticMeshComponent) else None
    rows.append('%s<%s> %s v%d h%d %s' % (c.get_name(), c.get_attach_parent().get_name() if c.get_attach_parent() else '-',
                m.get_name() if m else '', c.is_visible(), c.get_editor_property('hidden_in_game'),
                [round(x, 2) for x in c.get_editor_property('relative_location').to_tuple()]))
open('P:/FoA/Saved/QA/lanes/doortool/door_actor.txt', 'w').write('\n'.join(rows))
print('ROWS', len(rows))
