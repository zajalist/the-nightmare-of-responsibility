"""Editor-world look-dev for BP_SandAmbience events (world lane): copies of the event parts as TMP_world_ actors at
their sites, each SandEvent set to a chosen moment of its life, shot lit through a TMP_world_Capture SceneCapture2D
from a camera dist cm toward the room centre and h cm up; everything is destroyed in the same run.
  $env:FOA_ACTORS_NEW='TMP_world_'; python Tools/Unreal/ue_remote.py Tools/Splats/preview_events.py PE=creep,pile_hearth [PE_LIFE=0.5]
-> Saved/WorldShots/pe_<name>.png"""
import math
import os

import unreal

V = '/Game/FoA/VFX/Splats'
MI = f'{V}/Instances/'
M = {'mound': f'{V}/Meshes/SM_SandMoundSplats_B',
     'stream': f'{V}/Meshes/SM_SandTrickle_Ceiling/SM_SandTrickle_Ceiling/StaticMeshes/SM_SandTrickle_Ceiling',
     'clock': f'{V}/Meshes/SM_SandTrickle_Clock/SM_SandTrickle_Clock/StaticMeshes/SM_SandTrickle_Clock',
     'drift': f'{V}/Meshes/SM_SandFaceDrift/SM_SandFaceDrift/StaticMeshes/SM_SandFaceDrift',
     'shirt': f'{V}/Meshes/SM_SandShirtImprint/SM_SandShirtImprint/StaticMeshes/SM_SandShirtImprint',
     'suit': f'{V}/Meshes/SM_SandSuit/SM_SandSuit/StaticMeshes/SM_SandSuit',
     'hourglass': f'{V}/Meshes/SM_SandHourglass/SM_SandHourglass/StaticMeshes/SM_SandHourglass'}
# name: (mesh, MI, site xyz, yaw, scale, event (x, seconds, w) or None, camera (dist, height, fov))
EV = {'creep_door': ('mound', 'MI_Sand_Bloom', (370, 88, 0.3), 0, 0.6, (1.6, 11, 0), (230, 140, 50)),
      'creep_wardrobe': ('mound', 'MI_Sand_Bloom', (224, 205, 0.3), 0, 0.7, (1.6, 11, 0), (230, 140, 50)),
      'pile_hearth': ('mound', 'MI_Sand_Bloom', (-300, 30, 3.3), 0, 0.5, (0.7, 10, 1), (200, 130, 50)),
      'pile_desk': ('mound', 'MI_Sand_Bloom', (-240, 110, 0.3), 0, 0.6, (0.7, 10, 1), (200, 130, 50)),
      'pile_bay': ('mound', 'MI_Sand_Bloom', (-110, -235, 0.3), 0, 0.7, (0.7, 10, 1), (200, 130, 50)),
      'trickle_bay': ('stream', 'MI_Sand_Trickle', (-50, -245, 299), 90, 1.0, None, (330, 150, 70)),
      'trickle_chimney': ('stream', 'MI_Sand_Trickle', (-275, -110, 299), 0, 1.0, None, (330, 150, 70)),
      'drift': ('drift', 'MI_Sand_ShaftDrift', (-60, -285, 95), 90, 4.0, None, (220, 120, 60)),
      'clockdrip': ('clock', 'MI_Sand_ClockDrip', (-322, 0, 183), 0, 1.0, None, (170, 160, 45)),
      'shirt': ('shirt', 'MI_Sand_Imprint', (-70, -215, 0.3), 75, 1.0, (1, 1.6, 0), (180, 190, 55)),
      'suit': ('suit', 'MI_Sand_Suit', (-60, -335, 0), 0, 1.0, (1, 2.2, 0), (330, 160, 60)),
      'hourglass': ('hourglass', 'MI_Sand_Hourglass', (-318, -48, 125.2), 0, 0.45, (1, 1.6, 0), (120, 150, 40))}
names = [n for n in os.environ.get('PE', ','.join(EV)).split(',') if n in EV]
LIFE = float(os.environ.get('PE_LIFE', '0.45'))
CLOCK = os.environ.get('PE_CLOCK', 'game')   # read now: ue_remote drops KEY=VALUE env vars when the run returns
WARM = int(os.environ.get('PE_WARM', '50'))
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
rt = unreal.RenderingLibrary.create_render_target2d(world, 1280, 720, unreal.TextureRenderTargetFormat.RTF_RGBA8_SRGB)
cap = EAS.spawn_actor_from_class(unreal.SceneCapture2D, unreal.Vector(0, 0, 150))
cap.set_actor_label('TMP_world_Capture')
cc = cap.capture_component2d
pps = cc.get_editor_property('post_process_settings')
for flag, prop, value in (('override_dynamic_global_illumination_method', 'dynamic_global_illumination_method',
                           unreal.DynamicGlobalIlluminationMethod.LUMEN),
                          ('override_reflection_method', 'reflection_method', unreal.ReflectionMethod.LUMEN)):
    pps.set_editor_property(flag, True)
    pps.set_editor_property(prop, value)
for k, v in (('texture_target', rt), ('capture_every_frame', False), ('capture_on_movement', False),
             ('always_persist_rendering_state', True), ('post_process_settings', pps),
             ('capture_source', unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR)):
    cc.set_editor_property(k, v)
st = {'i': 0, 'phase': 'spawn', 'a': None, 'h': None, 'wait': 0}


def done():
    unreal.unregister_slate_post_tick_callback(st['h'])
    if st['a']:
        st['a'].destroy_actor()
    cap.destroy_actor()
    unreal.log('[world] preview_events done')


def tick(_dt):
    """One event per few ticks: spawn and start its SandEvent, let two frames pass (custom primitive data reaches
    the renderer at the end of a frame), then shoot."""
    try:
        if st['i'] >= len(names):
            return done()
        n = names[st['i']]
        mesh, mi, loc, yaw, s, ev, (dist, h, fov) = EV[n]
        if st['phase'] == 'spawn':
            a = EAS.spawn_actor_from_object(unreal.load_asset(M[mesh]), unreal.Vector(*loc), unreal.Rotator(0, 0, yaw))
            a.set_actor_label(f'TMP_world_{n}')
            a.set_actor_scale3d(unreal.Vector(s, s, s))
            c = a.static_mesh_component
            c.set_material(0, unreal.load_asset(MI + mi))
            c.set_collision_profile_name('NoCollision')
            c.set_editor_property('cast_shadow', False)
            c.set_editor_property('bounds_scale', 3.0)
            clock = CLOCK  # which clock the material's Time node follows in editor captures
            now = {'game': unreal.GameplayStatics.get_time_seconds, 'real': unreal.GameplayStatics.get_real_time_seconds,
                   'audio': unreal.GameplayStatics.get_audio_time_seconds}[clock](world)
            unreal.log(f'[world] pe clock {clock} now={now:.2f} game={unreal.GameplayStatics.get_time_seconds(world):.2f} real={unreal.GameplayStatics.get_real_time_seconds(world):.2f}')
            if ev and mesh == 'mound':
                x, secs, w = ev
                c.set_vector_parameter_for_custom_primitive_data('SandEvent', unreal.Vector4(x, now - LIFE * secs, secs, w))
            st.update(a=a, phase='wait', wait=3)
            return
        if st['phase'] == 'wait':
            st['wait'] -= 1
            if st['wait'] <= 0:
                st['phase'] = 'shoot'
            return
        t = unreal.Vector(loc[0], loc[1], loc[2] + (-120 if mesh == 'stream' and loc[2] > 250 else 0) + (80 if mesh == 'suit' else 0))
        fx, fy = -t.x, -45.0 - t.y
        L = max(math.hypot(fx, fy), 1.0)
        camp = unreal.Vector(t.x + fx / L * dist, t.y + fy / L * dist, h)
        d = t - camp
        cap.set_actor_location_and_rotation(camp, unreal.Rotator(roll=0, pitch=math.degrees(math.atan2(d.z, math.hypot(d.x, d.y))),
                                                               yaw=math.degrees(math.atan2(d.y, d.x))), False, False)
        cc.set_editor_property('fov_angle', fov)
        for _ in range(WARM):
            cc.capture_scene()
        unreal.RenderingLibrary.export_render_target(world, rt, 'P:/FoA/Saved/WorldShots', f'pe_{n}.png')
        unreal.log(f'[world] pe {n} cam=({camp.x:.0f},{camp.y:.0f},{camp.z:.0f})')
        st['a'].destroy_actor()
        st.update(a=None, phase='spawn', i=st['i'] + 1)
    except Exception as e:  # end cleanly
        unreal.log_error(f'[world] preview_events failed: {e}')
        done()


st['h'] = unreal.register_slate_post_tick_callback(tick)
print('preview scheduled', names)
