"""Real room render layers, warmed across real editor ticks, with actor-only opacity mattes.
INTRO_SHOTS is a comma-separated subset; default all seven. No original actor is changed.
Outputs Full/BG/Matte PNGs. A bounded callback destroys the single temporary capture.
"""
import json
import math
import os
from pathlib import Path
import time
import unreal

OUT=Path('P:/FoA/Saved/LookDev/intro_ingame')
SHOTS={
 'Game02_BedFoot':([75,-105,96],[175,-191,48],68,['Bed','Bedding_Lux3D']),
 'Game03_Clock':([-200,-40,197],[-328,0,200],35,['WallClock','WallClock_wall_clock_hours_hand','WallClock_wall_clock_minute_hand','WallClock_wall_clock_second_hand']),
 'Game04_Desk':([-145,80,135],[-325,180,70],58,['Chair','DeskLamp']),
 'Game05_Chores':([100,12,77],[151,-80,22],50,['Boot_L','Boot_R']),
 'Game06_Wardrobe':([60,-25,140],[225,210,125],60,['Wardrobe','Wardrobe_GothicCabinet_01_door1','Wardrobe_GothicCabinet_01_door2','Wardrobe_GothicCabinet_01_door3','Wardrobe_GothicCabinet_01_door4']),
 'Game07_Door':([205,-15,125],[375,88,110],50,['Door_Bedroom','DoorFrame_Bedroom']),
 'Game08_Window':([10,10,150],[-65,-335,155],65,['Dress_Curtains_Bay']),
}
assert not unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).is_in_play_in_editor()
world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
eas=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
by={a.get_actor_label():a for a in eas.get_all_level_actors()}
names=os.environ.get('INTRO_SHOTS',','.join(SHOTS)).split(',')
tasks=[(n,mode) for n in names for mode in ('Full','BG','Matte')]
cap=eas.spawn_actor_from_class(unreal.SceneCapture2D,unreal.Vector())
cap.set_actor_label('TMP_intro_Layers')
comp=cap.capture_component2d
rt=unreal.RenderingLibrary.create_render_target2d(world,1920,1080,unreal.TextureRenderTargetFormat.RTF_RGBA8)
settings=comp.get_editor_property('post_process_settings')
for k,v in [('override_dynamic_global_illumination_method',True),('dynamic_global_illumination_method',unreal.DynamicGlobalIlluminationMethod.LUMEN),
            ('override_reflection_method',True),('reflection_method',unreal.ReflectionMethod.LUMEN),
            ('override_auto_exposure_bias',True),('auto_exposure_bias',float(os.environ.get('INTRO_EXPOSURE','1.5')))]:
    settings.set_editor_property(k,v)
comp.set_editor_property('texture_target',rt)
comp.set_editor_property('capture_every_frame',True)
comp.set_editor_property('capture_on_movement',False)
comp.set_editor_property('always_persist_rendering_state',True)
comp.set_editor_property('post_process_settings',settings)
comp.set_editor_property('show_flag_settings',[unreal.EngineShowFlagsSetting(show_flag_name=n,enabled=False) for n in ('DepthOfField','MotionBlur')])
S={'start':time.time(),'changed':0,'index':0,'handle':None,'log':[],'done':False}

def select():
    name,mode=tasks[S['index']];origin,target,fov,labels=SHOTS[name]
    d=[b-a for a,b in zip(origin,target)]
    rot=unreal.Rotator(pitch=math.degrees(math.atan2(d[2],math.hypot(*d[:2]))),yaw=math.degrees(math.atan2(d[1],d[0])),roll=0)
    cap.set_actor_location_and_rotation(unreal.Vector(*origin),rot,False,False)
    comp.set_editor_property('fov_angle',fov)
    # The unlit corners need their own photographic exposure, not a room lighting edit.
    settings.set_editor_property('auto_exposure_bias',7.5 if name in ('Game02_BedFoot','Game05_Chores','Game06_Wardrobe','Game07_Door') else 1.5)
    comp.set_editor_property('post_process_settings',settings)
    foreground=[by[n] for n in labels if n in by]
    assert foreground,(name,labels)
    comp.clear_hidden_components()
    comp.clear_show_only_components()
    for actor in foreground:
        if mode=='BG':comp.hide_actor_components(actor,True)
        if mode=='Matte':comp.show_only_actor_components(actor,True)
    comp.set_editor_property('primitive_render_mode',unreal.SceneCapturePrimitiveRenderMode.PRM_USE_SHOW_ONLY_LIST if mode=='Matte' else unreal.SceneCapturePrimitiveRenderMode.PRM_RENDER_SCENE_PRIMITIVES)
    comp.set_editor_property('capture_source',unreal.SceneCaptureSource.SCS_SCENE_COLOR_HDR if mode=='Matte' else unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
    S['changed']=time.time()

def finish(error=None):
    if S['done']:return
    S['done']=True
    if S['handle'] is not None:unreal.unregister_slate_post_tick_callback(S['handle'])
    eas.destroy_actor(cap)
    previous=json.loads((OUT/'layers_capture.json').read_text()).get('shots',[]) if (OUT/'layers_capture.json').exists() else []
    keep=[row for row in previous if row['name'] not in names]
    (OUT/'layers_capture.json').write_text(json.dumps({'error':error,'shots':keep+S['log']},indent=1))
    unreal.log('Intro real render layers '+str(error or 'complete'))

def tick(dt):
    try:
        if S['done']:return
        if unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).is_in_play_in_editor():
            finish('PIE began during editor capture');return
        if time.time()-S['start']>55:finish('timeout');return
        if time.time()-S['changed']<1.5:return
        name,mode=tasks[S['index']]
        unreal.RenderingLibrary.export_render_target(world,rt,str(OUT),name+'_'+mode+'.png')
        origin,target,fov,labels=SHOTS[name]
        S['log'].append(dict(name=name,mode=mode,map=world.get_path_name(),origin=origin,target=target,fov=fov,foreground=labels,warm_seconds=1.5,exposure_bias=settings.auto_exposure_bias))
        S['index']+=1
        if S['index']==len(tasks):finish()
        else:select()
    except Exception as e:finish(str(e))

try:
    select()
    S['handle']=unreal.register_slate_post_tick_callback(tick)
except Exception as error:
    finish(str(error))
    raise
