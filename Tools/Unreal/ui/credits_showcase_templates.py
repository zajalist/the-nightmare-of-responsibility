"""Credits lane: BP_CreditsShowcase component template settings that Hayba's object_set_property can't import
(arrays of structs, the post-process struct). The lights' LightingChannels (channel 1 only, which no map directional
light uses) are set through Hayba object_set_property, as Python can't write that struct. Edits only this lane's Blueprint; idempotent. Run inside the lane's hold:
  python Tools/Unreal/ue_remote.py Tools/Unreal/ui/credits_showcase_templates.py [FOA_KEY=<cd>] [FOA_RIM=<cd>]"""
import os

import unreal

BP = '/Game/FoA/UI/Credits/BP_CreditsShowcase'
C = BP + '.BP_CreditsShowcase_C:'
MESHES = os.environ.get('FOA_MESHES', '')


def template(name):
    t = unreal.find_object(None, C + name + '_GEN_VARIABLE')
    assert t, name
    return t


def run():
    bp = unreal.load_asset(BP)
    cap = template('Capture')
    cap.set_editor_property('show_flag_settings', [unreal.EngineShowFlagsSetting(show_flag_name=n, enabled=False) for n in (
        'Fog', 'Atmosphere', 'VolumetricFog', 'Cloud', 'Decals', 'LightShafts', 'SkyLighting',
        # GPU profile 11-17: per-view costs a mesh lit only by two lights never uses (NaniteMeshes stays on: the key and
        # hanger are Nanite and vanish without it, PIE 11-18 00:19)
        'DistanceFieldAO', 'AmbientOcclusion', 'ContactShadows', 'ScreenSpaceReflections')])
    pps = cap.get_editor_property('post_process_settings')
    for prop, value in (('dynamic_global_illumination_method', unreal.DynamicGlobalIlluminationMethod.NONE),
                        ('reflection_method', unreal.ReflectionMethod.NONE)):
        pps.set_editor_property('override_' + prop, True)
        pps.set_editor_property(prop, value)
    cap.set_editor_property('post_process_settings', pps)
    cap.set_editor_property('post_process_blend_weight', 1.0)
    for name, loc, rot, size, intensity, shadows in (
            ('Key', (-140, -260, 160), (-28.5, 61.7), (70, 70), float(os.environ.get('FOA_KEY', '60')), False),  # no shadows: 2+ ms of VSM for a mesh that turns every frame (PIE 11-18 00:39), look kept (Saved/Credits/key_shadows_compare.png)
            ('Rim', (200, 190, 90), (-18.1, -136.5), (40, 120), float(os.environ.get('FOA_RIM', '140')), False)):
        t = template(name)
        t.set_editor_property('relative_location', unreal.Vector(*loc))
        t.set_editor_property('relative_rotation', unreal.Rotator(pitch=rot[0], yaw=rot[1], roll=0))
        t.set_editor_property('source_width', size[0])
        t.set_editor_property('source_height', size[1])
        t.set_editor_property('attenuation_radius', 700.0)
        t.set_editor_property('intensity_units', unreal.LightUnits.CANDELAS)
        t.set_editor_property('intensity', intensity)
        t.set_editor_property('cast_shadows', shadows)
        t.set_editor_property('cast_volumetric_shadow', False)
        t.set_editor_property('volumetric_scattering_intensity', 0.0)
        t.set_editor_property('indirect_lighting_intensity', 0.0)
    cdo = unreal.get_default_object(unreal.load_object(None, BP + '.BP_CreditsShowcase_C'))
    tick = cdo.get_editor_property('primary_actor_tick')
    tick.set_editor_property('tick_even_when_paused', True)  # tear down even if the title pauses the game
    cdo.set_editor_property('primary_actor_tick', tick)
    if MESHES:
        cdo.set_editor_property('Meshes', [unreal.load_asset(p) for p in MESHES.split(',')])
    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    unreal.EditorAssetLibrary.save_asset(BP, only_if_is_dirty=False)
    cdo = unreal.get_default_object(unreal.load_object(None, BP + '.BP_CreditsShowcase_C'))
    print('templates set; meshes', len(cdo.get_editor_property('Meshes')), 'tick when paused',
          cdo.get_editor_property('primary_actor_tick').get_editor_property('tick_even_when_paused'),
          'flags', [f.show_flag_name for f in template('Capture').get_editor_property('show_flag_settings')])


run()
