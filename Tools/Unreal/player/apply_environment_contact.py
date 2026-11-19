"""Install the narrowly gated left-hand contact graphs under the Player/visible-ABP leases."""
import datetime,json,os,shutil,sys,runpy
from pathlib import Path
sys.path[:0]=['P:/FoA/Tools/Unreal','P:/FoA/Tools/Unreal/player']
import hayba_call as h
import environment_contact_graphs as g
from held_tool_graphs import Batch,inspect,find
assert not h.call('editor_get_state')['data']['pie_running']
owner=h.agent_id();lease=h.lease_acquire(owner,['asset:'+g.P,'asset:'+g.M],ttl_s=180,wait_s=5)
def call(name,**kw):
 r=h.call(name,kw,owner=owner,lease=lease,timeout=30);assert r.get('ok'),r;return r.get('data',{})
try:
 backup=Path('Saved/Backups/environment_contact')/datetime.datetime.now().strftime('%Y%m%d_%H%M%S');backup.mkdir(parents=True)
 for path in (g.P,g.M):shutil.copy2(Path('Content')/(path.removeprefix('/Game/')+'.uasset'),backup/(path.rsplit('/',1)[1]+'.uasset'))
 for path,values in [(g.M,[('EnvironmentHandTarget','vector'),('EnvironmentElbowTarget','vector'),('EnvironmentHandRotation','rotator'),('EnvironmentForearmRotation','rotator'),('EnvironmentUpperarmRotation','rotator'),('EnvironmentHandWeight','float')]),(g.P,[('EnvironmentContactMesh','object:/Script/Engine.StaticMeshComponent'),('EnvironmentContactLocal','vector'),('EnvironmentContactRotation','rotator'),('EnvironmentContactStarted','float'),('EnvironmentContactAim','vector'),('EnvironmentContactReachable','bool'),('EnvironmentContactUpperarmTwist','float')])]:
  for name,typ in values:call('blueprint_add_variable',path=path,variable_name=name,variable_type=typ,category='Environment contact',update_existing=True)
 for name,inputs in [('BeginEnvironmentContact',[{'name':'Target','type':'object:/Script/Engine.Actor'},{'name':'Seconds','type':'float'}]),('ClearEnvironmentContact',[]),('UpdateEnvironmentContact',[])]:
  r=h.call('blueprint_inspect_graph',dict(path=g.P,graph_name=name),owner=owner,lease=lease)
  if not r.get('ok'):call('blueprint_add_function',path=g.P,function_name=name,inputs=inputs)
 for name,fn in [('ClearEnvironmentContact',g.clear),('BeginEnvironmentContact',g.begin),('UpdateEnvironmentContact',g.update)]:
  if len(inspect(g.P,name)[0])<=2:fn()
 if not any(n['title'].replace(' ','')=='GetEnvironmentHandTarget' for n in inspect(g.M,'AnimGraph')[0]):
  call('python_exec_file',path='P:/FoA/Tools/Unreal/player/add_environment_hand_ik.py',env={},resources=['asset:'+g.M])
 call('blueprint_compile',path=g.M);call('asset_save',asset_paths=[g.M])
 nodes,edges=inspect(g.P,'EventGraph');b=Batch(g.P,'EventGraph')
 norm=lambda s:s.replace(' ','').replace('_','').lower()
 lock=next(n['node_id'] for n in nodes if 'eventlockforinteraction' in norm(n['title']))
 tick=next(n['node_id'] for n in nodes if norm(n['title'])=='eventtick')
 for source,ref,func,x,y in [(tick,'update',g.PC+':UpdateEnvironmentContact',-300,-500)]:
  if any(norm(n['title'])==norm(func.rsplit(':',1)[1]) for n in nodes):continue
  after=[e for e in edges if e['from_node']==source and e['from_pin']=='then'];assert len(after)==1,after
  old=after[0];b.fn(ref,func,x,y);b.cut(source,'then',old['to_node'],old['to_pin']);b.link(source,'then',ref,'execute');b.link(ref,'then',old['to_node'],old['to_pin'])
 # Keep the existing alignment, but aim at the handle instead of a floor-level hinge.
 if not any(norm(n['title'])=='getenvironmentcontactaim' for n in nodes):
  look=next(n['node_id'] for n in nodes if norm(n['title'])=='findlookatrotation' and any(e['to_node']==n['node_id'] and e['to_pin']=='Target' and any(x['from_node']==lock and x['from_pin']=='Target' and x['to_node']==e['from_node'] for x in edges) for e in edges))
  old=next(e for e in edges if e['to_node']==look and e['to_pin']=='Target')
  b.get('envmesh','EnvironmentContactMesh',1100,3400);b.fn('validenv',g.SYS+'IsValid',1400,3400);b.link('envmesh','EnvironmentContactMesh','validenv','Object')
  b.get('aim','EnvironmentContactAim',1100,3600);b.fn('aimpick',g.K+'SelectVector',1700,3400);b.link('aim','EnvironmentContactAim','aimpick','A');b.link('validenv','ReturnValue','aimpick','bPickA')
  b.cut(old['from_node'],old['from_pin'],look,'Target');b.link(old['from_node'],old['from_pin'],'aimpick','B');b.link('aimpick','ReturnValue',look,'Target')
  b.comment('Face the handle',['envmesh','validenv','aim','aimpick'])
 if b.ops:b.run()
 nodes,edges=inspect(g.P,'EndInteraction');e=find(nodes,'EndInteraction');old=next(x for x in edges if x['from_node']==e and x['from_pin']=='then')
 if not any(norm(n['title'])=='clearenvironmentcontact' for n in nodes):
  b=Batch(g.P,'EndInteraction');b.fn('clear',g.PC+':ClearEnvironmentContact',300,0);b.cut(e,'then',old['to_node'],old['to_pin']);b.chain(e,'clear');b.link('clear','then',old['to_node'],old['to_pin']);b.comment('Release the grasp',['clear']);b.run()
 print('Environment contact installed; bounded visual/contact proof pending',backup)
finally:h.release(owner,lease)
runpy.run_path('P:/FoA/Tools/Unreal/player/gate_environment_contact.py',run_name='__main__')

