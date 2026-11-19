"""Framing candidates for BP_MenuCamera: one temporary SceneCapture2D (TMP_ui_Cap) renders each pose with the menu
camera's lens and its own post-process (M_PP_MenuV31, exposure), exports Saved/UIShots/pose_<name>.png, and is destroyed.
Run via ue_remote.py with FOA_ACTORS=BP_MenuCamera FOA_ACTORS_NEW=TMP_ui_ and
  FOA_POSES="A:-230,170,150,-6,-50;B:..."   (name:x,y,z,pitch,yaw)"""
import math
import os
import unreal


def main():
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    cam = next(a for a in eas.get_all_level_actors() if a.get_actor_label() == 'BP_MenuCamera')
    cine = cam.get_cine_camera_component()
    fb = cine.get_editor_property('filmback')
    fov = math.degrees(2 * math.atan(fb.get_editor_property('sensor_width') / (2 * cine.get_editor_property('current_focal_length'))))
    rt = unreal.RenderingLibrary.create_render_target2d(world, 1280, 720, unreal.TextureRenderTargetFormat.RTF_RGBA8_SRGB)
    out_dir = os.path.join(unreal.Paths.project_saved_dir(), 'UIShots')
    cap = eas.spawn_actor_from_class(unreal.SceneCapture2D, cam.get_actor_location(), cam.get_actor_rotation())
    cap.set_actor_label('TMP_ui_Cap')
    try:
        comp = cap.get_editor_property('capture_component2d')
        comp.set_editor_property('fov_angle', fov)
        comp.set_editor_property('capture_source', unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
        comp.set_editor_property('texture_target', rt)
        comp.set_editor_property('capture_every_frame', False)
        if os.environ.get('FOA_NOPP') != '1':  # FOA_NOPP=1: the scene without the menu look (is a detail ours or the scene's?)
            comp.set_editor_property('post_process_settings', cine.get_editor_property('post_process_settings'))
        comp.set_editor_property('post_process_blend_weight', 1.0)
        for item in [s for s in os.environ.get('FOA_POSES', '').split(';') if ':' in s]:
            name, vals = item.split(':')
            x, y, z, p, yaw = (float(v) for v in vals.split(','))
            cap.set_actor_location_and_rotation(unreal.Vector(x, y, z), unreal.Rotator(roll=0.0, pitch=p, yaw=yaw), False, False)
            comp.capture_scene()
            unreal.RenderingLibrary.export_render_target(world, rt, out_dir, f'pose_{name}.png')
            print('pose', name, x, y, z, p, yaw)
    finally:
        eas.destroy_actor(cap)  # never leave capture clutter in the level
    print('fov', round(fov, 1))


main()
