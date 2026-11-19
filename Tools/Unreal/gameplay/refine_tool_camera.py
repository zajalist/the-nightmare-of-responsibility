"""Restore the verified baseline on the camera template and placed instance."""
import json,math,sys
from pathlib import Path
sys.path.insert(0,'P:/FoA/Tools/Unreal')
import hayba_call as h
owner='door-mechanics';asset='/Game/FoA/Gameplay/BP_Door';token=None
def call(cmd,**args):
    r=h.call(cmd,args,owner=owner,lease=token);assert r.get('ok'),r
    d=r.get('data',{});assert d.get('ok',True),d;return d
assert not call('editor_get_state')['pie_running']
token=h.lease_acquire(owner,['asset:'+asset,'world:/Game/FoA/Maps/L_Tutorial_Bedroom'],ttl_s=30,wait_s=5)
try:
    path=json.loads(Path('P:/FoA/Saved/Integration/tool_refresh_untruncated.json').read_text())['camera']
    xyz=(-30,-144,102);target=(-7,-84,88);dx,dy,dz=[b-a for a,b in zip(xyz,target)]
    props={'RelativeLocation':{'X':xyz[0],'Y':xyz[1],'Z':xyz[2]},'RelativeRotation':{'Pitch':math.degrees(math.atan2(dz,math.hypot(dx,dy))),'Yaw':math.degrees(math.atan2(dy,dx)),'Roll':0},'FieldOfView':36}
    applied=call('object_set_property',path=path,properties=props)
    placed=json.loads(Path('P:/FoA/Saved/Integration/outcome_handoff/door_camera_instances.json').read_text())
    assert len(placed)==1,placed
    instance_path=placed[0]['camera']
    instance_applied=call('object_set_property',path=instance_path,properties=props)
    readback=call('object_get_property',path=instance_path,names=list(props))
    compiled=call('blueprint_compile',path=asset,save=True)
    assert compiled['error_count']==0 and compiled['warning_count']==0 and compiled['saved'],compiled
    saved=call('level_save')
    assert saved.get('saved'),saved
    Path('P:/FoA/Saved/Integration/door_camera_fix.json').write_text(json.dumps(dict(path=path,requested=props,applied=applied,instance_path=instance_path,instance_applied=instance_applied,readback=readback,compile=compiled,level=saved),indent=1))
    print('Baseline ToolCamera restored on template and placed door; saved with readback')
finally:h.release(owner,token)
