"""Phone_Nightstand's ScreenLight back to BP_Phone's own values (world lane, 2026-11-10, the "glowing band" hunt).
The placed phone kept the RectLight it was born with (5000 unitless, 10 m reach, shadows, 88 deg barn doors) while
BP_Phone's template says 2.5 cd, 55 cm, no shadows, 70 deg (aaa_phone_hold.py 'glass'): class edits don't reach a
placed actor's overridden components (editor-rules). A rect light lights only its front half-space, so that 5000-unit
light drew a hard straight edge across his face, the battle shirt and the walls at the phone's height.
  $env:FOA_ACTORS='Phone_Nightstand'; python Tools/Unreal/ue_remote.py Tools/Unreal/fix_phone_screen_light.py
then: python Tools/Unreal/editor_lock.py save_level world"""
import unreal

TEMPLATE = '/Game/FoA/UI/Game/BP_Phone.BP_Phone_C:ScreenLight_GEN_VARIABLE'
PROPS = ('intensity_units', 'intensity', 'attenuation_radius', 'cast_shadows', 'barn_door_angle', 'barn_door_length',
         'source_width', 'source_height', 'light_color', 'lighting_channels')
tpl = unreal.load_object(None, TEMPLATE)
assert tpl and tpl.get_editor_property('intensity') < 10.0, 'BP_Phone template changed: re-check before copying'
KEYS = ('intensity_units', 'intensity', 'attenuation_radius', 'cast_shadows')


def light(actor):   # fetched fresh each time: a notified set re-runs the construction script and trashes the component
    return next(c for c in actor.get_components_by_class(unreal.RectLightComponent) if not c.get_name().startswith('TRASH'))


for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
    if a.get_class().get_name() != 'BP_Phone_C':
        continue
    before = {p: str(light(a).get_editor_property(p)) for p in KEYS}
    for p in PROPS:
        light(a).set_editor_property(p, tpl.get_editor_property(p))
    c = light(a)
    after = {p: str(c.get_editor_property(p)) for p in KEYS}
    assert all(str(c.get_editor_property(p)) == str(tpl.get_editor_property(p)) for p in KEYS), (a.get_actor_label(), after)
    print('PHONE LIGHT', a.get_actor_label(), c.get_name(), 'before', before, 'after', after)
