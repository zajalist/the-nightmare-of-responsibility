"""World lane preview: spawn TMP_world_ preview actors (LUX_PREVIEW=mesh@x,y,z,pitch,yaw,roll,scale[@mat0|mat1..];...)
or destroy every TMP_world_ actor (LUX_PREVIEW=clear). Pair with Tools/Splats/world_capture.py. Splat materials
show their object whole here: custom primitive data SandEvent defaults to zeros (no event = dissolve 0)."""
import os
import unreal

EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
spec = os.environ.get('LUX_PREVIEW', 'clear')
if spec == 'clear':
    for a in EAS.get_all_level_actors():
        if a.get_actor_label().startswith('TMP_world_'):
            print('destroy', a.get_actor_label())
            a.destroy_actor()
else:
    for i, item in enumerate(spec.split(';')):
        path, nums, *mat = item.split('@')
        x, y, z, p, yw, r, s = (float(v) for v in nums.split(','))
        a = EAS.spawn_actor_from_object(unreal.load_asset(path), unreal.Vector(x, y, z), unreal.Rotator(roll=r, pitch=p, yaw=yw))
        a.set_actor_scale3d(unreal.Vector(s, s, s))
        a.set_actor_label(f'TMP_world_Preview{i}')
        if mat:  # one material per slot, '|' separated
            c = a.get_component_by_class(unreal.StaticMeshComponent)
            for k, m in enumerate(mat[0].split('|')):
                c.set_material(k, unreal.load_asset(m))
            c.set_collision_profile_name('NoCollision')
        print('spawned', a.get_actor_label(), path)
