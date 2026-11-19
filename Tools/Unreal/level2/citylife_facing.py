"""City life lane, read-only probe: which local axis the walker meshes face (foot to toe, ref pose), so the pooled
walkers walk forward. Spawns TMP_citylife_probe and destroys it in the same run (FOA_ACTORS_NEW=TMP_citylife_)."""
import unreal

eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
for name in ('Commuter', 'Faceless'):
    sk = unreal.EditorAssetLibrary.load_asset(f'/Game/FoA/Level2/CityLife/{name}/SK_Lux3D_{name}')
    probe = eas.spawn_actor_from_class(unreal.SkeletalMeshActor, unreal.Vector(0, 0, -5000), unreal.Rotator())
    try:
        probe.set_actor_label('TMP_citylife_probe')
        comp = probe.skeletal_mesh_component
        comp.set_skeletal_mesh_asset(sk)
        bones = [str(comp.get_bone_name(i)) for i in range(comp.get_num_bones())]
        foot = next(b for b in bones if b.endswith('LeftFoot'))
        toe = next(b for b in bones if b.endswith('LeftToeBase'))
        head = next(b for b in bones if b.endswith('Head'))
        f, t = comp.get_socket_location(foot), comp.get_socket_location(toe)
        h = comp.get_socket_location(head)
        print(f'{name}: bones={len(bones)} foot->toe=({t.x - f.x:.1f},{t.y - f.y:.1f},{t.z - f.z:.1f}) '
              f'head_z={h.z + 5000:.0f} feet_z={f.z + 5000:.0f} names={bones[:2]}')
    finally:
        eas.destroy_actor(probe)
