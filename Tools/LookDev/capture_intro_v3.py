"""Intro v3 source passes (story lane). One shot per run, in the editor world, never during PIE:
  $env:FOA_AREAS='/Game/FoA/UI/Intro'; $env:FOA_ACTORS_NEW='TMP_story_'
  python Tools/Unreal/ue_remote.py Tools/LookDev/capture_intro_v3.py INTRO_SHOT=Watcher
Spawns the shot's temporary props and a SceneCapture2D (all TMP_story_*), waits about a second of editor ticks so the
posed meshes and Lumen settle, writes color (the game's own grade, LDR, fixed exposure INTRO_EV in EV100), depth (cm) and, when the shot has one,
a lit pass with a temporary practical light, to Saved/StoryShots/intro/src/<shot>_<pass>.exr. A bounded tick callback
destroys every temporary actor, also on error and on PIE start. No level actor is moved or edited.
Offline: Tools/LookDev/intro_plates.py turns these into the plate textures."""
import json
import math
import os
import time

import unreal

OUT = 'P:/FoA/Saved/StoryShots/intro/src'
W, H = 2560, 1440
SHIRT = '/Game/FoA/Characters/Garments/SK_Garment_Shirt'
SHIRT_SM = '/Game/FoA/Lux3D/the_shirt_enemy/SM_Lux3D_ShirtEnemy'  # the shirt the player fights
SHIRT_ANIM = '/Game/FoA/Characters/Garments/SK_Garment_ShirtArmature_Lash'
MANNY = '/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple'
IDLE = '/Game/Characters/Mannequins/Anims/Unarmed/MM_Idle'
BLACK = '/Game/FoA/Materials/MI_DarkSand_Black'
EYE = (352.0, -191.0, 92.0)  # his eyes on the pillow (Saved/WakeUp/placement.json lay.head + 10 cm up)
# name: camera (x, y, z), aim (x, y, z), horizontal fov, props [(kind, asset, anim, anim_t, loc, (pitch, yaw, roll), scale)],
#       lit light (loc, (pitch, yaw, roll), intensity cd, width, height) or None, level actors hidden in the shot
SHOTS = {
    'Room': ((-300, 230, 250), (250, -185, 75), 65.5, [], None, ['Nightmare'], None),
    'Phone': ((316, -114, 112), (338, -53, 81), 26.0, [], None, ['Nightmare', 'SandClock_WakeUp'], ['Phone_Nightstand']),
    'Shirt': ((-25, 95, 105), (-60, -205, 92), 46.0,  # yaw 0: the shirt's front (collar, buttons) faces the camera
              [('static', SHIRT_SM, None, 0, (-60, -205, 48), (0, 0, 0), 1.6)],
              ((-35, -110, 140), (-11.5, -104.7, 0), float(os.environ.get('INTRO_FILL', '2')), 60.0, 60.0), ['Nightmare'], ['figure']),
    'Watcher': (EYE, (150, -191, 150), 52.0,
                [('skel', MANNY, IDLE, 0.4, (150, -191, 0), (0, -90, 0), 1.08)], None, ['Nightmare'], ['figure']),  # Manny faces actor +Y
    'Lunge': (EYE, (322, -158, 172), 72.0,
              [('skel', MANNY, IDLE, 0.4, (286, -112, 0), (0, -142, 18), 1.08)], None, ['Nightmare'], ['figure']),  # roll leans it at him
}
EV = {}  # per-shot overrides; the room reads at about EV100 -2 since the 13:40 restart (it was -8 before)
NAME = os.environ['INTRO_SHOT']
cam_loc, aim, fov, props, lit, hide, matte = SHOTS[NAME]
assert not unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).is_in_play_in_editor(), 'PIE running'
os.makedirs(OUT, exist_ok=True)
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
level = {a.get_actor_label(): a for a in eas.get_all_level_actors()}
temps = []


def spawn(cls, loc, rot=(0, 0, 0), label='Prop'):
    a = eas.spawn_actor_from_class(cls, unreal.Vector(*loc), unreal.Rotator(pitch=rot[0], yaw=rot[1], roll=rot[2]))
    a.set_actor_label('TMP_story_' + label)
    temps.append(a)
    return a


d = [b - a for a, b in zip(cam_loc, aim)]
cam = spawn(unreal.SceneCapture2D, cam_loc,
            (math.degrees(math.atan2(d[2], math.hypot(d[0], d[1]))), math.degrees(math.atan2(d[1], d[0])), 0), 'Capture')
comp = cam.capture_component2d
flags = []
for n in ('Grain', 'Vignette', 'LensFlares', 'SceneColorFringe', 'MotionBlur', 'DepthOfField'):  # the game's grade stays
    f = unreal.EngineShowFlagsSetting()
    f.set_editor_property('show_flag_name', n)
    f.set_editor_property('enabled', False)
    flags.append(f)
for k, v in (('capture_every_frame', False), ('capture_on_movement', False), ('fov_angle', fov),
             ('always_persist_rendering_state', True), ('show_flag_settings', flags)):
    comp.set_editor_property(k, v)
# Fixed exposure (a capture's eye adaptation never converges inside one call): min = max brightness, in EV100.
ev = float(os.environ.get('INTRO_EV', EV.get(NAME, -2.0)))
pp = comp.get_editor_property('post_process_settings')
for k, v in (('override_auto_exposure_min_brightness', True), ('auto_exposure_min_brightness', ev),
             ('override_auto_exposure_max_brightness', True), ('auto_exposure_max_brightness', ev),
             ('override_auto_exposure_bias', True), ('auto_exposure_bias', 0.0)):
    pp.set_editor_property(k, v)
comp.set_editor_property('post_process_settings', pp)
# The glitter splats only go black under the live game's sand pass; the intro draws its own black sand.
for label, a in level.items():
    if label in hide or label.startswith(('SandSplats_', 'SandSpill_', 'SandStream_')):
        comp.hide_actor_components(a, True)
bounds = {}
for i, (kind, asset, anim, t, loc, rot, scale) in enumerate(props):
    if kind == 'static':
        a = spawn(unreal.StaticMeshActor, loc, rot, 'Figure%d' % i)
        a.set_actor_scale3d(unreal.Vector(scale, scale, scale))
        a.static_mesh_component.set_static_mesh(unreal.load_asset(asset))
        o, e = a.get_actor_bounds(False)
        bounds[a.get_actor_label()] = [round(o.z - e.z), round(o.z + e.z)]
        continue
    a = spawn(unreal.SkeletalMeshActor, loc, rot, 'Figure%d' % i)
    a.set_actor_scale3d(unreal.Vector(scale, scale, scale))
    sk = a.skeletal_mesh_component
    sk.set_skeletal_mesh_asset(unreal.load_asset(asset))
    if asset == MANNY:
        mi = unreal.load_asset(BLACK)
        for slot in range(sk.get_num_materials()):
            sk.set_material(slot, mi)
    sk.set_update_animation_in_editor(True)
    sk.override_animation_data(unreal.load_asset(anim), False, False, t, 0.0)
    o, e = a.get_actor_bounds(False)
    bounds[a.get_actor_label()] = [round(o.z - e.z), round(o.z + e.z)]
F, S = unreal.TextureRenderTargetFormat, unreal.SceneCaptureSource
TAG = os.environ.get('INTRO_TAG', '')
passes = [('color' + TAG, F.RTF_RGBA8, S.SCS_FINAL_COLOR_LDR, 48)]
if not TAG:
    passes.append(('depth', F.RTF_RGBA32F, S.SCS_SCENE_DEPTH, 2))
if matte and not TAG:  # show-only pass: alpha is the inverse coverage of the matte actors
    passes.append(('matte', F.RTF_RGBA16F, S.SCS_SCENE_COLOR_HDR, 2))
if lit:
    passes.append(('lit' + TAG, F.RTF_RGBA8, S.SCS_FINAL_COLOR_LDR, 48))
ST = {'t0': time.time(), 'i': 0, 'done': False, 'handle': None, 'log': []}


def finish(error=None):
    if ST['done']:
        return
    ST['done'] = True
    if ST['handle'] is not None:
        unreal.unregister_slate_post_tick_callback(ST['handle'])
    for a in temps:
        if unreal.SystemLibrary.is_valid(a):
            eas.destroy_actor(a)
    with open(f'{OUT}/{NAME}.json', 'w') as fh:
        json.dump(dict(shot=NAME, camera=cam_loc, aim=aim, fov=fov, size=[W, H], props=[list(p[:2]) for p in props],
                       prop_bounds_z=bounds, error=error, passes=ST['log']), fh, indent=1)
    unreal.log('Intro v3 capture %s %s' % (NAME, error or 'complete'))


def tick(dt):
    try:
        if ST['done']:
            return
        if unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).is_in_play_in_editor():
            finish('PIE began')
            return
        if time.time() - ST['t0'] > 40:
            finish('timeout')
            return
        if time.time() - ST['t0'] < 1.2:  # posed meshes tick in the editor world before any capture
            return
        name, fmt, source, settle = passes[ST['i']]
        if name.startswith('lit') and not any(a.get_actor_label() == 'TMP_story_Practical' for a in temps):
            loc, rot, cd, w, h = lit
            light = spawn(unreal.RectLight, loc, rot, 'Practical')
            lc = light.rect_light_component
            lc.set_editor_property('intensity_units', unreal.LightUnits.CANDELAS)
            lc.set_editor_property('intensity', cd)
            lc.set_editor_property('source_width', w)
            lc.set_editor_property('source_height', h)
            lc.set_editor_property('attenuation_radius', 160.0)
            lc.set_editor_property('cast_shadows', True)
            return  # one tick for the light to register
        if name == 'matte':
            comp.clear_show_only_components()
            for label in matte:
                for a in ([t for t in temps if t.get_actor_label().startswith('TMP_story_Figure')] if label == 'figure' else [level[label]]):
                    comp.show_only_actor_components(a, True)
            comp.set_editor_property('primitive_render_mode', unreal.SceneCapturePrimitiveRenderMode.PRM_USE_SHOW_ONLY_LIST)
        rt = unreal.RenderingLibrary.create_render_target2d(world, W, H, fmt)
        comp.set_editor_property('texture_target', rt)
        comp.set_editor_property('capture_source', source)
        for _ in range(settle):
            comp.capture_scene()
        unreal.RenderingLibrary.export_render_target(world, rt, OUT, f'{NAME}_{name}' + ('.exr' if name in ('depth', 'matte') else '.png'))
        ST['log'].append(name)
        ST['i'] += 1
        if ST['i'] == len(passes):
            finish()
    except Exception as e:  # noqa: BLE001  (always clean the temporary actors)
        finish(str(e))


ST['handle'] = unreal.register_slate_post_tick_callback(tick)
print('capture scheduled', NAME, bounds)
