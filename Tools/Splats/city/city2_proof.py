"""Bounded, validity-guarded native 1080p angle comparisons and drift in our PIE."""
import json
import math
import os
from pathlib import Path
import time
import unreal
OUT=Path('P:/FoA/Saved/Codex/city2');OUT.mkdir(parents=True,exist_ok=True)
UES=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
valid=unreal.SystemLibrary.is_valid


def stop():
    s=getattr(unreal,'_city2_proof',None)
    if s and not s['done']:s['finish']('runner_stop')


def start():
    stop();w=UES.get_game_world();assert valid(w)
    old=os.environ.get('CITY2_OLD')=='1';name=os.environ['CITY2_VIEW'];suffix='before' if old else 'after'
    expected='L_L2_CityTest' if old else 'L_L2_CityTest2';assert expected in w.get_path_name()
    poses={'spadina':[15500,0,4937],'university':[80000,0,4937],'play_corner':[6000,-44000,4937],
           'overview':[70000,0,110000],'drift':[15500,0,4937]}
    pose=poses[name];pitches=[90] if name=='overview' else [70] if name=='drift' else [90,70,60]
    cam=next(a for a in unreal.GameplayStatics.get_all_actors_of_class(w,unreal.CameraActor)
             if a.get_actor_label()==('L2_Cam' if old else 'City2_Camera'))
    unreal.GameplayStatics.get_player_controller(w,0).set_view_target_with_blend(cam,0)
    transform=unreal.Transform(location=unreal.Vector(*pose))
    cap=unreal.GameplayStatics.begin_deferred_actor_spawn_from_class(w,unreal.SceneCapture2D,transform)
    cap=unreal.GameplayStatics.finish_spawning_actor(cap,transform);cap.set_actor_label('TMP_city2_capture')
    c=cap.capture_component2d
    rt=unreal.RenderingLibrary.create_render_target2d(w,1920,1080,unreal.TextureRenderTargetFormat.RTF_RGBA8_SRGB)
    for k,v in [('texture_target',rt),('capture_source',unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR),
                ('capture_every_frame',False),('capture_on_movement',False),('always_persist_rendering_state',True),('fov_angle',90.)]:
        c.set_editor_property(k,v,notify_mode=unreal.PropertyAccessChangeNotifyMode.NEVER)
    settings=unreal.get_default_object(unreal.EditorPerformanceSettings)
    old_throttle=settings.get_editor_property('throttle_cpu_when_not_foreground');settings.set_editor_property('throttle_cpu_when_not_foreground',False)
    gpu=unreal.SystemLibrary.get_console_variable_int_value('csv.GpuStatsEnabled')
    unreal.SystemLibrary.execute_console_command(w,'csv.GpuStatsEnabled 1');unreal.SystemLibrary.execute_console_command(w,'csvprofile start')
    s=dict(start=time.monotonic(),csv_start=time.time(),done=False,busy=False,handle=None,frames=[],name=name,suffix=suffix,angle=-1,angle_start=0)
    frames=OUT/'drift_frames';frames.mkdir(exist_ok=True)

    def alive():
        return valid(w) and UES.get_game_world()==w and all(valid(a) for a in [cam,cap,c])

    def finish(reason,error=None):
        if s['done']:return
        s['done']=True
        if s['handle'] is not None:unreal.unregister_slate_post_tick_callback(s['handle'])
        loaded=[]
        if alive():
            unreal.SystemLibrary.execute_console_command(w,'csvprofile stop')
            unreal.SystemLibrary.execute_console_command(w,'csv.GpuStatsEnabled '+str(gpu))
            settings.set_editor_property('throttle_cpu_when_not_foreground',old_throttle)
            loaded=[a.static_mesh_component.static_mesh.get_name() for a in unreal.GameplayStatics.get_all_actors_of_class(w,unreal.StaticMeshActor)
                    if valid(a) and a.static_mesh_component.static_mesh and a.static_mesh_component.static_mesh.get_name().startswith('SM_City2_')]
            cap.destroy_actor()
        result={k:s[k] for k in ['name','suffix','frames','csv_start']}
        result.update(reason=reason,error=error,csv_end=time.time(),loaded_meshes=loaded,pose=pose,elapsed=time.monotonic()-s['start'])
        (OUT/(name+'_'+suffix+'_proof.json')).write_text(json.dumps(result,indent=2))
        (OUT/'proof_done.json').write_text(json.dumps({'reason':reason,'name':name,'error':error}))
    s['finish']=finish;unreal._city2_proof=s

    def tick(dt):
        if s['busy'] or s['done']:return
        s['busy']=True
        try:
            if not alive():return finish('PIE world or capture replaced')
            elapsed=time.monotonic()-s['start']
            if elapsed>27:return finish('timeout')
            index=0 if name=='drift' else min(len(s['frames']),len(pitches)-1)
            pitch=pitches[index];pos=list(pose)
            if name not in ['overview','play_corner']:pos[1]+=5000/math.tan(math.radians(pitch))
            if name=='drift':
                t=elapsed-5
                if t>=12:return finish('passed')
                pos[0]+=max(0,t)*500
            else:t=elapsed
            if s['angle']!=index:
                s['angle']=index;s['angle_start']=elapsed
                rot=unreal.Rotator(pitch=-pitch,yaw=-90,roll=0)
                cam.set_actor_rotation(rot,False);cap.set_actor_rotation(rot,False)
            cam.set_actor_location(unreal.Vector(*pos),False,False);cap.set_actor_location(unreal.Vector(*pos),False,False)
            if elapsed<4:return
            if name=='drift' and s['frames'] and t-s['frames'][-1]['seconds']<.095:return
            c.capture_scene()
            if elapsed<5 or elapsed-s['angle_start']<.6:return
            directory=frames if name=='drift' else OUT
            file=f'frame_{len(s["frames"]):04}.png' if name=='drift' else f'{name}_p{pitch}_{suffix}.png'
            unreal.RenderingLibrary.export_render_target(w,rt,str(directory),file)
            s['frames'].append({'seconds':t,'file':str(directory/file),'camera_cm':pos,'pitch_degrees':pitch,'yaw_degrees':-90})
            if name!='drift' and len(s['frames'])==len(pitches):return finish('passed')
        except Exception as e:finish('failed',repr(e))
        finally:s['busy']=False
    s['handle']=unreal.register_slate_post_tick_callback(tick)
    print('CITY2 proof scheduled',name,suffix,pitches)


if os.environ.get('CITY2_PROOF')=='STOP':stop()
else:start()
