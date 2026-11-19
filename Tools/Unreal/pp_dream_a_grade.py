"""atmosphere lane: Dream A's own grade. Dream A (L_L2_DreamTest, streamed at threshold_data.OFFSET (20000, -80000, 0))
is a bright, unlit splat world, and the exposure that reached it was the bedroom's: BP_ViewFill's GameplayExposure
component (priority 10, histogram clamped to EV100 -2.8..-1) outranks PP_DreamMono and the Dream map's own L2_Post, so
the colour path clipped to white in almost every frame (QA plan ATP lists the sources live in Dream A).
This places one bounded PostProcessVolume around Dream A in the persistent map (folder Lighting, priority 15, so it
outranks GameplayExposure only there). It overrides the exposure only (a histogram range brighter than the bedroom's, for the
splats) and the bloom (a soft glow on what now sits below white); PP_DreamMono's blendables and look still apply.
The exposure is a histogram range, not a fixed value: the colour path swings from the bright arched room to near-black
breath beats, so a fixed EV either clipped the room (EV 0) or sank the walk (EV 3.25: median 15/255 on QA plan DRM).
  FOA_AREAS=PostProcess FOA_ACTORS_NEW=PP_DreamA_ FOA_ACTORS=PP_DreamA_Grade python Tools/Unreal/ue_remote.py Tools/Unreal/pp_dream_a_grade.py
Idempotent: reuses the volume if it exists and only rewrites its settings. Calibrated by QA plans ATX and DRM."""
import unreal

LABEL = 'PP_DreamA_Grade'
CENTRE = unreal.Vector(20000.0, -80000.0, 0.0)  # threshold_data.OFFSET
HALF = 6000.0  # cm: Dream A and its colour exit sit well inside 60 m; the city (x 9000 near y 0) and the bedroom are far outside
BLOOM = 0.5
EV_MIN, EV_MAX, BIAS, SPEED = 1.5, 3.25, 0.75, 1.5  # brightest the room may get, darkest, a brighter-than-grey dream key, adapt rate


def run():
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    ppv = next((a for a in eas.get_all_level_actors() if a.get_actor_label() == LABEL), None)
    if ppv is None:
        ppv = eas.spawn_actor_from_class(unreal.PostProcessVolume, CENTRE)
        ppv.set_actor_label(LABEL)
        ppv.set_folder_path('Lighting')
    ppv.set_actor_scale3d(unreal.Vector(1.0, 1.0, 1.0))
    _, ext = ppv.get_actor_bounds(False)
    assert ext.x > 1.0, 'the volume has no brush'
    ppv.set_actor_scale3d(unreal.Vector(HALF / ext.x, HALF / ext.y, HALF / ext.z))
    ppv.set_actor_location(CENTRE, False, True)
    for k, v in (('unbound', False), ('priority', 15.0), ('blend_radius', 0.0), ('blend_weight', 1.0), ('enabled', True)):
        ppv.set_editor_property(k, v)
    s = ppv.get_editor_property('settings')
    for k, v in (('override_auto_exposure_method', True), ('auto_exposure_method', unreal.AutoExposureMethod.AEM_HISTOGRAM),
                 ('override_auto_exposure_min_brightness', True), ('auto_exposure_min_brightness', EV_MIN),
                 ('override_auto_exposure_max_brightness', True), ('auto_exposure_max_brightness', EV_MAX),
                 ('override_auto_exposure_bias', True), ('auto_exposure_bias', BIAS),
                 ('override_auto_exposure_speed_up', True), ('auto_exposure_speed_up', SPEED),
                 ('override_auto_exposure_speed_down', True), ('auto_exposure_speed_down', SPEED),
                 ('override_bloom_intensity', True), ('bloom_intensity', BLOOM)):
        s.set_editor_property(k, v)
    ppv.set_editor_property('settings', s)
    lo, ext = ppv.get_actor_bounds(False)
    got = ppv.get_editor_property('settings')
    print(LABEL, 'centre', [round(lo.x), round(lo.y), round(lo.z)], 'half', [round(ext.x), round(ext.y), round(ext.z)],
          'EV', got.get_editor_property('auto_exposure_min_brightness'), got.get_editor_property('auto_exposure_max_brightness'),
          'bias', got.get_editor_property('auto_exposure_bias'),
          'prio', ppv.get_editor_property('priority'))
    assert abs(ext.x - HALF) < HALF * 0.1 and abs(lo.x - CENTRE.x) < 10, 'volume brush missing or misplaced'


run()
