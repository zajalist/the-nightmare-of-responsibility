"""Editor side of the garment material A/B (editor Python; Hayba's actor_find is policy-blocked and actor_spawn can't
set a skeletal mesh): FOA_OP=spawn puts one TMP_face_Garment_<Name> SkeletalMeshActor per battle garment in a row at
the PlayerStart, 160 cm apart, facing +X; FOA_OP=shoot FOA_TAG=before|after shoots each one lit and unlit (base colour)
with a temporary scene capture into Saved/FaceShots/garments_ab/; FOA_OP=delete removes every TMP_face_Garment_* actor
again. Never saved.
  python Tools/Unreal/ue_remote.py Tools/Unreal/face/garments_ab_editor.py FOA_OP=spawn FOA_ACTORS_NEW=TMP_face_"""
import os

import unreal

NAMES = ('Shirt', 'Trousers', 'Sock', 'Tie')
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
tmp = [a for a in eas.get_all_level_actors() if a.get_actor_label().startswith('TMP_face_Garment_') and isinstance(a, unreal.SkeletalMeshActor)]
cams = [a for a in eas.get_all_level_actors() if a.get_actor_label() == 'TMP_face_Garment_Cam']
if os.environ.get('FOA_OP') == 'shoot':  # the editor viewport captures black here, so a scene capture does the stills
    tag = os.environ['FOA_TAG']
    for c in cams:  # a capture left by a failed run
        eas.destroy_actor(c)
    w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    rt = unreal.RenderingLibrary.create_render_target2d(w, 900, 900, unreal.TextureRenderTargetFormat.RTF_RGBA8)
    cam = eas.spawn_actor_from_class(unreal.SceneCapture2D, unreal.Vector(0, 0, 0), unreal.Rotator(0, 0, 0))
    cam.set_actor_label('TMP_face_Garment_Cam')
    cc = cam.capture_component2d
    cc.set_editor_property('texture_target', rt)
    cc.set_editor_property('fov_angle', 40.0)
    cc.set_editor_property('capture_every_frame', False)
    cc.set_editor_property('capture_on_movement', False)
    cc.set_editor_property('primitive_render_mode', unreal.SceneCapturePrimitiveRenderMode.PRM_USE_SHOW_ONLY_LIST)
    pp = cc.get_editor_property('post_process_settings')  # no eye adaptation in a capture: fixed exposure, same for A and B
    pp.set_editor_property('override_auto_exposure_method', True)
    pp.set_editor_property('auto_exposure_method', unreal.AutoExposureMethod.AEM_MANUAL)
    pp.set_editor_property('override_auto_exposure_bias', True)
    pp.set_editor_property('auto_exposure_bias', float(os.environ.get('FOA_EV', '4')))
    cc.set_editor_property('post_process_settings', pp)
    for a in tmp:
        name = a.get_actor_label()[len('TMP_face_Garment_'):]
        centre, ext = a.get_actor_bounds(False)
        d = unreal.Vector(1.0, -0.3, 0.35)
        d.normalize()
        eye = centre + d * (ext.length() / 0.34 * 1.15)  # bounds sphere fills about 85% of a 40 degree view
        cam.set_actor_location_and_rotation(eye, unreal.MathLibrary.find_look_at_rotation(eye, centre), False, True)
        cc.clear_show_only_components()
        cc.show_only_actor_components(a)  # only this garment, on black: no furniture in the way
        for mode, src in (('lit', unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR), ('unlit', unreal.SceneCaptureSource.SCS_BASE_COLOR)):
            cc.set_editor_property('capture_source', src)
            cc.capture_scene()
            unreal.RenderingLibrary.export_render_target(w, rt, 'P:/FoA/Saved/FaceShots/garments_ab', f'{tag}_{mode}_{name}.png')
            print('FOA_GARMENT_AB shot', tag, mode, name)
    eas.destroy_actor(cam)
elif os.environ.get('FOA_OP') == 'delete':
    for a in tmp + cams:
        eas.destroy_actor(a)
    print('FOA_GARMENT_AB deleted', len(tmp + cams))
else:
    assert not tmp, 'TMP_face_Garment_* already there: run FOA_OP=delete first'
    start = next(a for a in eas.get_all_level_actors() if isinstance(a, unreal.PlayerStart)).get_actor_location()
    for i, name in enumerate(NAMES):
        loc = start + unreal.Vector(0, (i - 1.5) * 160, 0)
        a = eas.spawn_actor_from_class(unreal.SkeletalMeshActor, loc, unreal.Rotator(0, 0, 0))
        a.set_actor_label(f'TMP_face_Garment_{name}')
        a.skeletal_mesh_component.set_skeletal_mesh_asset(unreal.load_asset(f'/Game/FoA/Characters/Garments/SK_Garment_{name}'))
        print('FOA_GARMENT_AB', a.get_actor_label(), [round(v) for v in (loc.x, loc.y, loc.z)])
