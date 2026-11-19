"""Synchronous framing check: renders each named camera actor through a temporary SceneCapture2D and exports a PNG
to Saved/UIShots/cam_<label>.png. No tick callbacks (safe under ue_remote's private namespace). Run via ue_remote.py
with FOA_CAMS=BP_MenuCamera,Dev_MenuCam_B."""
import math
import os
import unreal


def main():
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    actors = {a.get_actor_label(): a for a in eas.get_all_level_actors()}
    rt = unreal.RenderingLibrary.create_render_target2d(world, 1280, 720, unreal.TextureRenderTargetFormat.RTF_RGBA8_SRGB)
    out_dir = os.path.join(unreal.Paths.project_saved_dir(), 'UIShots')
    for label in [s for s in os.environ.get('FOA_CAMS', 'BP_MenuCamera').split(',') if s]:
        cam = actors[label]
        cine = cam.get_cine_camera_component()
        fb = cine.get_editor_property('filmback')
        fov = math.degrees(2 * math.atan(fb.get_editor_property('sensor_width') /
                                         (2 * cine.get_editor_property('current_focal_length'))))
        cap = eas.spawn_actor_from_class(unreal.SceneCapture2D, cam.get_actor_location(), cam.get_actor_rotation())
        comp = cap.get_editor_property('capture_component2d')
        comp.set_editor_property('fov_angle', fov)
        comp.set_editor_property('capture_source', unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
        comp.set_editor_property('texture_target', rt)
        comp.set_editor_property('capture_every_frame', False)
        comp.capture_scene()
        unreal.RenderingLibrary.export_render_target(world, rt, out_dir, f'cam_{label}.png')
        eas.destroy_actor(cap)
        print('captured', label, f'fov {fov:.1f}')


main()
