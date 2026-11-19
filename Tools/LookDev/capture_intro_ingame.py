"""Editor-only real-room stills. Temporary capture is always destroyed; no room or viewport edits.

Native render_camera is flagged unsafe in this editor. This uses the established
SceneCapture2D export gap, one shot per short ue_remote call. INTRO_SHOT selects it.
"""
import json
import math
import os
from pathlib import Path
import unreal

SHOTS = {
    'Game02_BedFoot': ([75,-105,96], [175,-191,48], 68),
    'Game03_Clock': ([-200,-40,197], [-328,0,200], 35),
    'Game04_Desk': ([-145,80,135], [-325,180,70], 58),
    'Game05_Chores': ([100,12,77], [151,-80,22], 50),
    'Game06_Wardrobe': ([60,-25,140], [225,210,125], 60),
    'Game07_Door': ([205,-15,125], [375,88,110], 50),
    'Game08_Window': ([10,10,150], [-65,-335,155], 65),
}


def run():
    assert not unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).is_in_play_in_editor()
    name = os.environ['INTRO_SHOT']
    origin, target, fov = SHOTS[name]
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    delta = [b-a for a,b in zip(origin,target)]
    rot = unreal.Rotator(pitch=math.degrees(math.atan2(delta[2],math.hypot(*delta[:2]))),
                         yaw=math.degrees(math.atan2(delta[1],delta[0])),roll=0)
    cap = eas.spawn_actor_from_class(unreal.SceneCapture2D,unreal.Vector(*origin),rot)
    cap.set_actor_label('TMP_intro_Capture')
    try:
        comp = cap.capture_component2d
        rt = unreal.RenderingLibrary.create_render_target2d(world,1920,1080,unreal.TextureRenderTargetFormat.RTF_RGBA8_SRGB)
        settings = comp.get_editor_property('post_process_settings')
        for k,v in [('override_dynamic_global_illumination_method',True),
                    ('dynamic_global_illumination_method',unreal.DynamicGlobalIlluminationMethod.LUMEN),
                    ('override_reflection_method',True),('reflection_method',unreal.ReflectionMethod.LUMEN)]:
            settings.set_editor_property(k,v)
        flags = [unreal.EngineShowFlagsSetting(show_flag_name=n,enabled=False)
                 for n in ('DepthOfField','MotionBlur')]
        for k,v in [('texture_target',rt),('capture_every_frame',False),('capture_on_movement',False),
                    ('always_persist_rendering_state',True),('fov_angle',fov),('post_process_settings',settings),
                    ('show_flag_settings',flags),('capture_source',unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR)]:
            comp.set_editor_property(k,v)
        for _ in range(24):
            comp.capture_scene()
        out=Path('P:/FoA/Saved/LookDev/intro_ingame')
        out.mkdir(parents=True,exist_ok=True)
        unreal.RenderingLibrary.export_render_target(world,rt,str(out),name+'.png')
        (out/(name+'_source.json')).write_text(json.dumps(dict(map=world.get_path_name(),camera=origin,
            target=target,fov=fov,source='SceneCapture2D SCS_FINAL_COLOR_LDR',size=[1920,1080]),indent=2))
        print('INTRO_GAME_CAPTURE',name)
    finally:
        eas.destroy_actor(cap)


run()
