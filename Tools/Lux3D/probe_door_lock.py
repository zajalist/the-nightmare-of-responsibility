"""Read-only: Door_Bedroom's lock components (mesh, material, relative transform, visibility)."""
import unreal

door = next(a for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
            if a.get_actor_label() == 'Door_Bedroom')
for c in door.get_components_by_class(unreal.StaticMeshComponent):
    if c.get_name().startswith(('Tool', 'TRASH')) or c.get_name() == 'Mesh':
        m = c.get_editor_property('static_mesh')
        l, r, s = c.get_editor_property('relative_location'), c.get_editor_property('relative_rotation'), c.get_editor_property('relative_scale3d')
        print(c.get_name(), m.get_path_name().rsplit('/', 3)[-3] if m else None, c.get_material(0).get_name() if c.get_material(0) else None,
              f'loc=({l.x:.3f},{l.y:.2f},{l.z:.2f}) yaw={r.yaw:.0f} pitch={r.pitch:.0f} scale=({s.x:.4f},{s.y:.4f},{s.z:.4f}) vis={c.is_visible()}')
