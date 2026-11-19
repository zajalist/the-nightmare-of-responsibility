"""Narrow measured screwdriver stance + palm-frame scale correction, never in PIE.

No animation rebuild, manual sequence edits, or Player graph compile.
"""
import json, os, re, sys
from pathlib import Path
sys.path.insert(0,'P:/FoA/Tools/Unreal')
sys.path.insert(0,'P:/FoA/Tools/Unreal/player')
import hayba_call as h
from held_tool_graphs import Batch, inspect, find, K

owner='clothing_search';os.environ['HAYBA_AGENT_ID']=owner
door='/Game/FoA/Gameplay/BP_Door';player='/Game/FoA/Characters/Player/BP_FoAPlayer'
cdo=player+'.Default__BP_FoAPlayer_C'
token=h.lease_acquire(owner,['asset:'+door,'asset:'+player],ttl_s=45,wait_s=3)
log=[]
def call(name,**args):
    r=h.call(name,args,owner=owner,lease=token);log.append([name,r]);assert r.get('ok'),r
    d=r.get('data',{});assert d.get('ok',True),d;return d
try:
    assert not call('editor_get_state')['pie_running'],'User PIE active'
    measured=json.loads(Path('Saved/Integration/screwdriver_contact_measured.json').read_text())
    assert 15 < measured['proposed_additional_setback_cm'] < 35
    nodes,edges=inspect(door,'SetDoorToolPresentation')
    stand=next(n for n in nodes if n['title'].replace(' ','')=='MakeVector' and
               any(p['name']=='Y' and abs(float(p.get('default_value','0'))+84)<.001 for p in n['pins']))
    b=Batch(door,'SetDoorToolPresentation')
    incoming=[e for e in edges if e['to_node']==stand['node_id'] and e['to_pin']=='X']
    if not incoming:
        b.get('mode','ToolMode',2700,1250)
        b.fn('driver',K+'EqualEqual_NameName',3000,1250,B='Screwdriver');b.link('mode','ToolMode','driver','A')
        b.fn('setback',K+'SelectFloat',3300,1250,A=measured['proposed_local_stand_x'],B=-50.0)
        b.link('driver','ReturnValue','setback','bPickA');b.link('setback','ReturnValue',stand['node_id'],'X')
        b.comment('Reach the screw with a relaxed elbow',['mode','driver','setback']);b.run()
    else:
        source=next(n for n in nodes if n['node_id']==incoming[0]['from_node'])
        assert source['title'].replace(' ','')=='SelectFloat',source
        assert abs(float(next(p['default_value'] for p in source['pins'] if p['name']=='A'))-measured['proposed_local_stand_x'])<.001
    assert not call('editor_get_state')['pie_running'],'User PIE started before palm correction'
    old=call('object_get_property',path=cdo,names=['ToolGripOffset'])['properties']['ToolGripOffset']
    replacement='Scale3D=(X=%.9f,Y=%.9f,Z=%.9f)'%tuple(measured['reciprocal_grip_scale'])
    new=re.sub(r'Scale3D=\([^)]*\)',replacement,old)
    assert new!=old or replacement in old
    call('object_set_property',path=cdo,properties={'ToolGripOffset':new})
    call('asset_save',asset_paths=[player])
    readback=call('object_get_property',path=cdo,names=['ToolGripOffset'])
    print('Measured tool corrections saved',readback)
finally:
    h.release(owner,token)
    Path('Saved/Integration/measured_tool_contact_apply.json').write_text(json.dumps(log,indent=1))
