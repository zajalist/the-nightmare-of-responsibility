"""World lane stills through a temporary SceneCapture2D (TMP_world_Capture, destroyed in the same run).
  $env:FOA_AREAS='VFX'; python Tools/Unreal/ue_remote.py Tools/Splats/world_capture.py WC_SHOTS="name=SPEC;name=SPEC"
SPEC is either  x,y,z,pitch,yaw[,fov]  or  @Actor[.Component][,dist[,up[,side[,fov]]]]  (aims at the component's
bounds centre from `dist` cm along the actor's -X (its front for the door) or from the room centre when the actor
has no clear front; side shifts the camera along the actor's Y). WC_SRC=base for unlit base colour.
Writes P:/FoA/Saved/WorldShots/<name>.png."""
import math
import os

import unreal

OUT = 'P:/FoA/Saved/WorldShots'
os.makedirs(OUT, exist_ok=True)
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
W, H = (int(v) for v in os.environ.get('WC_RES', '1280x720').split('x'))
WARM = int(os.environ.get('WC_WARM', '12'))
by = {a.get_actor_label(): a for a in EAS.get_all_level_actors()}


def aim(spec):
    parts = spec[1:].split(',')
    label, _, comp_name = parts[0].partition('.')
    nums = [float(v) for v in parts[1:]] + [None] * 4
    dist, up, side, fov = (nums[0] or 60.0), (nums[1] or 0.0), (nums[2] or 0.0), (nums[3] or 40.0)
    a = by[label]
    if comp_name:
        c = next(x for x in a.get_components_by_class(unreal.SceneComponent) if x.get_name() == comp_name)
        tgt = c.get_world_location() if not isinstance(c, unreal.PrimitiveComponent) else             unreal.SystemLibrary.get_component_bounds(c)[0]
    else:
        o, _e = a.get_actor_bounds(True)
        tgt = o
    fwd = a.get_actor_forward_vector() * -1.0 if os.environ.get('WC_FRONT', 'neg') == 'neg' else a.get_actor_forward_vector()
    if os.environ.get('WC_FROMCENTRE'):
        fwd = unreal.Vector(-tgt.x, -45.0 - tgt.y, 0.0)
        fwd = fwd * (1.0 / max(fwd.length(), 1e-3))
    right = a.get_actor_right_vector()
    cam = unreal.Vector(tgt.x + fwd.x * dist + right.x * side, tgt.y + fwd.y * dist + right.y * side, tgt.z + up)
    d = tgt - cam
    return cam, unreal.Rotator(roll=0.0, pitch=math.degrees(math.atan2(d.z, math.hypot(d.x, d.y))),
                               yaw=math.degrees(math.atan2(d.y, d.x))), fov


rt = unreal.RenderingLibrary.create_render_target2d(world, W, H, unreal.TextureRenderTargetFormat.RTF_RGBA8_SRGB)
cap = EAS.spawn_actor_from_class(unreal.SceneCapture2D, unreal.Vector(0.0, 0.0, 150.0))
cap.set_actor_label('TMP_world_Capture')
comp = cap.capture_component2d
pps = comp.get_editor_property('post_process_settings')  # captures default Lumen off; the game uses it
for flag, prop, value in (('override_dynamic_global_illumination_method', 'dynamic_global_illumination_method',
                           unreal.DynamicGlobalIlluminationMethod.LUMEN),
                          ('override_reflection_method', 'reflection_method', unreal.ReflectionMethod.LUMEN)):
    pps.set_editor_property(flag, True)
    pps.set_editor_property(prop, value)
flags = []
for name, on in (('DepthOfField', False), ('MotionBlur', False), ('EyeAdaptation', True)):
    f = unreal.EngineShowFlagsSetting()
    f.set_editor_property('show_flag_name', name)
    f.set_editor_property('enabled', on)
    flags.append(f)
for k, v in (('texture_target', rt), ('capture_every_frame', False), ('capture_on_movement', False),
             ('always_persist_rendering_state', True), ('post_process_settings', pps), ('show_flag_settings', flags),
             ('capture_source', unreal.SceneCaptureSource.SCS_BASE_COLOR if os.environ.get('WC_SRC') == 'base'
              else unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR)):
    comp.set_editor_property(k, v)
try:
    for item in [s for s in os.environ.get('WC_SHOTS', '').split(';') if s]:
        name, spec = item.split('=', 1)
        if spec.startswith('@'):
            loc, rot, fov = aim(spec)
        else:
            x, y, z, pitch, yaw, *f = (float(v) for v in spec.split(','))
            loc, rot, fov = unreal.Vector(x, y, z), unreal.Rotator(roll=0.0, pitch=pitch, yaw=yaw), (f[0] if f else 70.0)
        cap.set_actor_location_and_rotation(loc, rot, False, False)
        comp.set_editor_property('fov_angle', fov)
        for _ in range(WARM):  # TSR and Lumen history
            comp.capture_scene()
        unreal.RenderingLibrary.export_render_target(world, rt, OUT, name + '.png')
        print('shot', f'{OUT}/{name}.png', f'loc=({loc.x:.0f},{loc.y:.0f},{loc.z:.0f}) rot=({rot.pitch:.1f},{rot.yaw:.1f}) fov={fov}')
finally:
    cap.destroy_actor()
