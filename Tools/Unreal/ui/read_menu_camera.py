"""Read-only: BP_MenuCamera's post-process (CDO and the placed instance): blend weight, blendables, exposure overrides."""
import unreal


def dump(tag, c):
    pp = c.get_editor_property('post_process_settings')
    print(tag, c.get_path_name(), 'weight', c.get_editor_property('post_process_blend_weight'),
          'blendables', [(b.weight, b.object.get_path_name() if b.object else None) for b in pp.weighted_blendables.array],
          'aeb', pp.get_editor_property('override_auto_exposure_bias'), pp.get_editor_property('auto_exposure_bias'))
    print(tag, 'overrides', [p for p in dir(pp) if p.startswith('override_') and pp.get_editor_property(p)])


def main():
    bp = unreal.load_asset('/Game/FoA/UI/Framework/BP_MenuCamera.BP_MenuCamera')
    dump('CDO', unreal.get_default_object(bp.generated_class()).get_cine_camera_component())
    for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
        if a.get_actor_label() == 'BP_MenuCamera':
            dump('LEVEL', a.get_cine_camera_component())


main()
