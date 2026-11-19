"""Read-only: the engine and project APIs the jumpscare relies on, written to Saved/HorrorShots/probe_api.txt.
  FOA_AREAS=Gameplay python Tools/Unreal/ue_remote.py Tools/Unreal/horror/probe_api.py"""
import unreal


def main():
    out = []
    for n in ('LegacyCameraShake', 'CameraShakeBase', 'PerlinNoiseCameraShakePattern', 'WaveOscillatorCameraShakePattern'):
        out.append('class %s: %s' % (n, hasattr(unreal, n)))
    for p in ('/Game/FoA/Audio/MetaSounds/Ambience/S_Ambience_RoomTone_Loop_01', '/Game/FoA/Audio/MetaSounds/Dream/S_Dream_HeartbeatPanic',
              '/Game/FoA/Audio/SFX/Ambience/SFX_Ambience_RoomTone_Loop_01', '/Game/FoA/Audio/SFX/Dream/SFX_Dream_LowImpact_01'):
        a = unreal.load_asset(p)
        sc = a.get_editor_property('sound_class_object') if a else None
        out.append('sound %s: %s class=%s' % (p, a.get_class().get_name() if a else None, sc.get_path_name() if sc else None))
    mpc = unreal.load_asset('/Game/FoA/PostProcess/MPC_Dream')
    out.append('MPC_Dream scalars: ' + ', '.join(str(s.get_editor_property('parameter_name')) for s in mpc.get_editor_property('scalar_parameters')))
    for bp in ('/Game/FoA/PostProcess/BP_DreamDirector.BP_DreamDirector_C', '/Game/FoA/VFX/Sand/BPL_SandFX.BPL_SandFX_C',
               '/Game/FoA/Characters/Player/BP_FoAPlayer.BP_FoAPlayer_C'):
        c = unreal.load_class(None, bp)
        if not c:
            out.append('missing ' + bp)
            continue
        cdo = unreal.get_default_object(c)
        fns = [f for f in dir(cdo) if not f.startswith('_')]
        out.append('%s funcs: %s' % (bp.split('.')[-1], ', '.join(f for f in fns if f[0].isupper() or f.startswith('k2'))[:1500]))
    pc = unreal.load_class(None, '/Game/FoA/Characters/Player/BP_FoAPlayer.BP_FoAPlayer_C')
    if pc:
        for comp in unreal.get_default_object(pc).get_components_by_class(unreal.CameraComponent):
            out.append('player camera %s fov %.1f' % (comp.get_name(), comp.get_editor_property('field_of_view')))
        for comp in unreal.get_default_object(pc).get_components_by_class(unreal.SpringArmComponent):
            out.append('player arm %s len %.1f' % (comp.get_name(), comp.get_editor_property('target_arm_length')))
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    for a in eas.get_all_level_actors():
        if a.get_actor_label() in ('Amb_RoomTone', 'Amb_NightWind', 'Amb_ClockTick'):
            ac = a.get_component_by_class(unreal.AudioComponent)
            s = ac.get_editor_property('sound') if ac else None
            out.append('%s sound=%s vol=%.2f' % (a.get_actor_label(), s.get_path_name() if s else None, ac.get_editor_property('volume_multiplier')))
        if a.get_actor_label() == 'BeatDirector':
            beats = a.get_editor_property('Beats') or []
            out.append('beats: ' + ', '.join(str(b.get_editor_property('Id')) if b else 'None' for b in beats))
    with open('P:/FoA/Saved/HorrorShots/probe_api.txt', 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(out))
    print('lines', len(out))


main()
