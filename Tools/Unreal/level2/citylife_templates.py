"""City life lane: BP_L2CityLife component templates (meshes, clips, movers, cull distance, flock instances).
Run through ue_remote inside the CityLife asset lease:
  $env:FOA_AREAS='/Game/FoA/Level2/CityLife'; python Tools/Unreal/ue_remote.py Tools/Unreal/level2/citylife_templates.py
Idempotent: flock instances are cleared and re-added, every other property is set to the same value again."""
import sys

import unreal

sys.path.insert(0, 'P:/FoA/Tools/Unreal/level2')
import importlib
import citylife_data as C
importlib.reload(C)

EAL = unreal.EditorAssetLibrary
ROOT = C.ROOT
WALKERS, HEIGHTS = C.WALKERS, C.HEIGHTS  # speeds come from C.WALK_SPEEDS by pair, in the same order


def asset(kind, name, suffix=''):
    return EAL.load_asset(f'{ROOT}/{name}/{kind}_Lux3D_{name}{suffix}')


def common(c, shadow):
    c.set_editor_property('mobility', unreal.ComponentMobility.MOVABLE)
    c.set_collision_profile_name('NoCollision')
    c.set_editor_property('cast_shadow', shadow)
    c.set_editor_property('ld_max_draw_distance', C.CULL)
    c.set_editor_property('visible', False)
    c.set_editor_property('receives_decals', False)


def mover(m, rate=None):
    m.set_editor_property('auto_register_updated_component', False)
    if rate is None:
        for k, v in (('projectile_gravity_scale', 0.0), ('initial_speed', 0.0), ('max_speed', 0.0),
                     ('rotation_follows_velocity', False), ('should_bounce', False)):
            m.set_editor_property(k, v)
    else:
        m.set_editor_property('rotation_rate', unreal.Rotator(pitch=0.0, yaw=rate, roll=0.0))
        m.set_editor_property('rotation_in_local_space', True)


def main():
    bp = EAL.load_asset(C.BP)
    unreal.get_editor_subsystem(unreal.EditorActorSubsystem).select_nothing()
    unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(bp)
    sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    lib = unreal.SubobjectDataBlueprintFunctionLibrary
    cs = {str(lib.get_variable_name(lib.get_data(h))): lib.get_object_for_blueprint(lib.get_data(h), bp)
          for h in sds.k2_gather_subobject_data_for_blueprint(bp)}
    for i, (who, clip) in enumerate(WALKERS):
        c = cs[f'WalkMesh{i}']
        sk = asset('SK', who)
        if sk:
            c.set_editor_property('skeletal_mesh_asset', sk)
            b = sk.get_bounds()
            s = HEIGHTS[who] / max(1.0, 2 * b.box_extent.z)
            c.set_editor_property('relative_scale3d', unreal.Vector(s, s, s))
        anim = asset('A', who, '_' + clip)
        c.set_editor_property('animation_mode', unreal.AnimationMode.ANIMATION_SINGLE_NODE)
        if anim:
            data = unreal.SingleAnimationPlayData()
            data.set_editor_property('anim_to_play', anim)
            data.set_editor_property('saved_looping', True)
            data.set_editor_property('saved_playing', True)
            data.set_editor_property('saved_position', (i * .37) % max(.1, anim.get_play_length()))  # out of step
            data.set_editor_property('saved_play_rate', 1.0)
            c.set_editor_property('animation_data', data)
        c.set_editor_property('visibility_based_anim_tick_option', unreal.VisibilityBasedAnimTickOption.ONLY_TICK_POSE_WHEN_RENDERED)
        c.set_editor_property('enable_update_rate_optimizations', True)
        common(c, True)
        mover(cs[f'WalkMove{i}'])
    chair_mesh, chair_scale, chair_spin = C.CHAIR
    for i in range(2):
        c = cs[f'ChairMesh{i}']
        sm = asset('SM', chair_mesh)
        if sm:
            c.set_static_mesh(sm)
        c.set_editor_property('relative_scale3d', unreal.Vector(chair_scale, chair_scale, chair_scale))
        common(c, True)
        mover(cs[f'ChairMove{i}'])
        mover(cs[f'ChairSpin{i}'], chair_spin * (1 if i == 0 else -1))
    for i, (mesh, count, radius, spread, scale, nose, bank, tumble, spin) in enumerate(C.FLOCKS):
        c = cs[f'Flock{i}']
        sm = asset('SM', mesh)
        if sm:
            c.set_static_mesh(sm)
        c.clear_instances()
        heading = nose + (0.0 if spin >= 0 else 180.0)
        for x, y, z, p, yw, r, s in C.flock_instances(count, radius, spread, scale, heading, bank, tumble, seed=i + 7):
            c.add_instance(unreal.Transform(location=[x, y, z], rotation=[r, p, yw], scale=[s, s, s]))
        c.set_editor_property('instance_end_cull_distance', int(C.CULL))
        common(c, False)
        mover(cs[f'FlockSpin{i}'], spin)
        print(f'Flock{i} {mesh}: {c.get_instance_count()} instances')
    mesh, scale, spin = C.PHONE
    c = cs['Phone']
    sm = asset('SM', mesh)
    if sm:
        c.set_static_mesh(sm)
    c.set_editor_property('relative_scale3d', unreal.Vector(scale, scale, scale))
    common(c, False)
    mover(cs['PhoneSpin'], spin)
    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    assert bp.get_editor_property('status') in (unreal.BlueprintStatus.BS_UP_TO_DATE, unreal.BlueprintStatus.BS_UP_TO_DATE_WITH_WARNINGS)
    EAL.save_loaded_asset(bp)
    print('BP_L2CityLife templates saved; walkers', [bool(cs[f'WalkMesh{i}'].get_editor_property('skeletal_mesh_asset'))
                                                     for i in range(8)])


main()
