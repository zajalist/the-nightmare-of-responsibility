"""16s camera-only comparison, existing real tool contact poses; coordinator owns PIE."""
import datetime,json,time,unreal
from pathlib import Path
scope={}
src=Path('P:/FoA/Tools/Unreal/gameplay/pie_door_tools_proof.py').read_text()
exec(compile(src.split("S['h'] = unreal.register_slate_post_tick_callback(tick)")[0],'<tool fixture helpers>','exec'),scope)
w,p,door,inv=(scope[k] for k in ('w','p','door','inv'))
cam=next(c for c in door.get_components_by_class(unreal.CameraComponent) if c.get_name()=='ToolCamera')
out=Path('P:/FoA/Saved/Integration/tool_camera_sweep')/datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d_%H%M%S')
out.mkdir(parents=True,exist_ok=True)
candidates=[('baseline',(-30,-144,102),(-7,-84,88),36),
 ('near_high',(-20,-80,100),(-2,-84,87),50),
 ('low_oblique',(-22,-100,74),(-2,-84,87),50),
 ('near_side',(-18,-110,90),(-2,-84,87),55)]
state=dict(start=time.time(),phase=0,index=0,at=0,rows=[],handle=None,done=False)
receipt=Path('P:/FoA/Saved/Integration/tool_camera_sweep.json')
def finish(reason):
    if state['done']:return
    state['done']=True
    unreal.unregister_slate_post_tick_callback(state['handle'])
    door.call_method('CancelDoorTool',())
    receipt.write_text(json.dumps(dict(status='complete',reason=reason,folder=str(out),rows=state['rows']),indent=1))
def tick(_dt):
    try:
        t=time.time()-state['start']
        if t>16:return finish('cap')
        if state['phase']==0:
            scope['tool_precondition']();scope['begin']();state['phase']=1
        elif state['phase'] in (1,4) and door.get_editor_property('bToolReady'):
            if state['phase']==1:
                for _ in range(5):door.call_method('AdvanceDoorTool',(1.0,.1))
            state['index']=0;state['phase']+=1;state['at']=t
        elif state['phase'] in (2,5) and t>=state['at']:
            name,xyz,target,fov=candidates[state['index']]
            pos=unreal.Vector(*xyz);aim=unreal.Vector(*target)
            cam.set_relative_location(pos,False,False)
            cam.set_relative_rotation(unreal.MathLibrary.find_look_at_rotation(pos,aim),False,False)
            cam.set_field_of_view(fov)
            state['phase']+=1;state['at']=t+.25
        elif state['phase'] in (3,6) and t>=state['at']:
            name,xyz,target,fov=candidates[state['index']]
            mode='key' if state['phase']==3 else 'screw'
            photo=out/(mode+'_'+name+'.png')
            unreal.SystemLibrary.execute_console_command(w,'Shot showui filename='+str(photo)+' -nosuffix',scope['pc'])
            state['rows'].append(dict(mode=mode,candidate=name,location=xyz,target=target,fov=fov,image=str(photo),angle=door.get_editor_property('ToolAngle'),camera=str(scope['pc'].player_camera_manager.get_camera_location())))
            receipt.write_text(json.dumps(dict(status='running',folder=str(out),rows=state['rows']),indent=1))
            state['index']+=1
            if state['index']<len(candidates):state['phase']-=1;state['at']=t+.4
            elif state['phase']==3:
                state['phase']=8;state['at']=t+.4
            else:state['phase']=9;state['at']=t+.4
        elif state['phase']==8 and t>=state['at']:
            for _ in range(7):door.call_method('AdvanceDoorTool',(1.0,.1))
            state['phase']=7
        elif state['phase']==9 and t>=state['at']:
            return finish('all_camera_candidates')
        elif state['phase']==7 and not door.get_editor_property('bToolReleasing'):
            assert str(door.get_editor_property('State'))=='KeyJammed'
            inv.call_method('Add',('Screwdriver',));scope['begin']();state['phase']=4
    except Exception as exc:
        state['rows'].append(dict(error=repr(exc)));finish('error')
state['handle']=unreal.register_slate_post_tick_callback(tick)
print('Tool camera sweep scheduled16s',out)
