"""atmosphere lane: keep the bedroom's room tone in the bedroom. Amb_RoomTone (S_Ambience_RoomTone_Loop_01, 2D) had no
attenuation, so it kept playing under Dream A (800 m away) and the Level 2 street. It stays non-spatial (a bed) but
now fades with distance: full inside 20 m of the room origin (the room, the hallway, the T7 top-down camera at 15 m),
silent past 45 m.
  FOA_AREAS=Audio FOA_ACTORS=Amb_RoomTone python Tools/Unreal/ue_remote.py Tools/Unreal/horror/room_tone_bounds.py"""
import unreal

INNER, FALLOFF = 2000.0, 2500.0


def run():
    a = next(x for x in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
             if x.get_actor_label() == 'Amb_RoomTone')
    ac = a.get_editor_property('audio_component')
    s = ac.get_editor_property('attenuation_overrides')
    s.set_editor_property('attenuate', True)
    s.set_editor_property('spatialize', False)
    s.set_editor_property('attenuation_shape', unreal.AttenuationShape.SPHERE)
    s.set_editor_property('attenuation_shape_extents', unreal.Vector(INNER, 0.0, 0.0))
    s.set_editor_property('falloff_distance', FALLOFF)
    a.modify()
    ac.set_editor_property('attenuation_overrides', s)
    ac.set_editor_property('override_attenuation', True)
    r = ac.get_editor_property('attenuation_overrides')
    got = (ac.get_editor_property('override_attenuation'), r.get_editor_property('attenuate'), r.get_editor_property('spatialize'),
           r.get_editor_property('attenuation_shape_extents').x, r.get_editor_property('falloff_distance'))
    assert got == (True, True, False, INNER, FALLOFF), got
    print('Amb_RoomTone attenuation', got)


run()
