"""Keep unreachable bare-hand rows unstarted; native gate preserves retry, tools and progress."""
import json,sys,datetime,shutil
from pathlib import Path
sys.path[:0]=['P:/FoA/Tools/Unreal','P:/FoA/Tools/Unreal/player']
import hayba_call as h,environment_contact_graphs as g
from held_tool_graphs import Batch,inspect,find
BASE='/Game/FoA/Gameplay/BP_Interactable';BC=BASE+'.BP_Interactable_C';INTER='/Game/FoA/Gameplay/BPC_Interactor.BPC_Interactor_C'
assert not h.call('editor_get_state')['data']['pie_running']
owner=h.agent_id();lease=h.lease_acquire(owner,['asset:'+g.P,'asset:'+g.M,'asset:'+BASE],ttl_s=100,wait_s=5)
def call(name,**kw):
 r=h.call(name,kw,owner=owner,lease=lease,timeout=30);assert r.get('ok'),r;return r['data']
def cancel_cleanup():
 nodes,edges=inspect(g.P,'EndInteraction')
 timer=any('Clear Timer' in n['title'] and any(p.get('name')=='FunctionName' and p.get('default_value')=='EndInteraction' for p in n.get('pins',[])) for n in nodes)
 if not timer:
  e=find(nodes,'EndInteraction');old=next(x for x in edges if x['from_node']==e and x['from_pin']=='then')
  b=Batch(g.P,'EndInteraction');b.fn('timer',g.SYS+'K2_ClearTimer',150,-250,FunctionName='EndInteraction');b.cut(e,'then',old['to_node'],old['to_pin']);b.chain(e,'timer');b.link('timer','then',old['to_node'],old['to_pin']);b.comment('Cancel the release timer',['timer']);b.run()
 nodes,edges=inspect(BASE,'CancelPendingRow')
 if any('EnvironmentContactMesh' in n['title'].replace(' ','') for n in nodes):return
 e=find(nodes,'CancelPendingRow');old=next(x for x in edges if x['from_node']==e and x['from_pin']=='then')
 b=Batch(BASE,'CancelPendingRow');b.fn('pawn','/Script/Engine.GameplayStatics:GetPlayerCharacter',-1800,450,PlayerIndex=0)
 b.node('cast','cast',-1800,0,class_path=g.PC);b.link('pawn','ReturnValue','cast','Object');b.cut(e,'then',old['to_node'],old['to_pin']);b.link(e,'then','cast','execute');b.link('cast','CastFailed',old['to_node'],old['to_pin'])
 b.get('owned','EnvironmentContactMesh',-1500,450,g.PC);b.link('cast','AsBP Fo APlayer','owned','self');b.get('mesh','Mesh',-1500,650)
 b.fn('same',g.K+'EqualEqual_ObjectObject',-1200,450);b.link('owned','EnvironmentContactMesh','same','A');b.link('mesh','Mesh','same','B');b.node('guard','branch',-1200,0);b.chain('cast','guard');b.link('same','ReturnValue','guard','Condition');b.link('guard','else',old['to_node'],old['to_pin'])
 b.fn('stop','/Script/Engine.Character:StopAnimMontage',-900,0);b.link('cast','AsBP Fo APlayer','stop','self');b.link('guard','then','stop','execute')
 b.fn('end',g.PC+':EndInteraction',-600,0);b.link('cast','AsBP Fo APlayer','end','self');b.chain('stop','end');b.link('end','then',old['to_node'],old['to_pin'])
 b.comment('Release our cancelled grasp',['pawn','cast','owned','mesh','same','guard','stop','end']);b.run()
try:
 cancel_cleanup()
 g.alignment()
 existing,_=inspect(BASE,'BeginPendingRow')
 norm=lambda title:title.replace(' ','').replace('_','').lower()
 installed=any(norm(n['title'])=='beginenvironmentcontact' for n in existing)
 if installed and '--refresh' not in sys.argv:
  assert not any(norm(n['title'])=='beginenvironmentcontact' for n in inspect(g.P,'EventGraph')[0]),'Legacy tool hook remains'
  print('Bare-hand gate already installed; no graph changes')
  sys.exit(0)
 backup=Path('Saved/Backups/environment_contact_gate')/datetime.datetime.now().strftime('%Y%m%d_%H%M%S');backup.mkdir(parents=True)
 for path in (g.P,BASE):shutil.copy2(Path('Content')/(path.removeprefix('/Game/')+'.uasset'),backup/(path.rsplit('/',1)[1]+'.uasset'))
 call('blueprint_add_variable',path=g.P,variable_name='EnvironmentContactReachable',variable_type='bool',default_value='true',category='Environment contact',update_existing=True)
 call('blueprint_add_variable',path=g.M,variable_name='EnvironmentForearmRotation',variable_type='rotator',category='Environment contact',update_existing=True)
 call('blueprint_add_variable',path=g.M,variable_name='EnvironmentUpperarmRotation',variable_type='rotator',category='Environment contact',update_existing=True)
 call('blueprint_add_variable',path=g.P,variable_name='EnvironmentContactUpperarmTwist',variable_type='float',category='Environment contact',update_existing=True)
 call('python_exec_file',path='P:/FoA/Tools/Unreal/player/add_environment_pronation.py',env={},resources=['asset:'+g.M])
 call('blueprint_compile',path=g.M);call('asset_save',asset_paths=[g.M])
 for name,fn in [('BeginEnvironmentContact',g.begin),('ClearEnvironmentContact',g.clear),('UpdateEnvironmentContact',g.update)]:
  nodes,edges=inspect(g.P,name);keep=find(nodes,name);remove=[n['node_id'] for n in nodes if n['node_id']!=keep]
  if remove:call('blueprint_remove_nodes',path=g.P,graph_name=name,node_ids=remove)
  fn()
 nodes,edges=inspect(g.P,'EventGraph');b=Batch(g.P,'EventGraph')
 legacy=[n['node_id'] for n in nodes if norm(n['title'])=='beginenvironmentcontact']
 for node in legacy:
  before=next(e for e in edges if e['to_node']==node and e['to_pin']=='execute');after=next(e for e in edges if e['from_node']==node and e['from_pin']=='then')
  b.cut(before['from_node'],before['from_pin'],node,'execute');b.cut(node,'then',after['to_node'],after['to_pin']);b.link(before['from_node'],before['from_pin'],after['to_node'],after['to_pin']);b.ops.append(dict(op='remove',node_ids=[node]))
 if b.ops:b.run()
 if installed:
  print('Refreshed owned contact functions; existing row gate preserved')
  sys.exit(0)
 nodes,edges=inspect(BASE,'BeginPendingRow');e=find(nodes,'BeginPendingRow');old=next(x for x in edges if x['from_node']==e and x['from_pin']=='then')
 br=next(n for n in nodes if any(p['name'].startswith('Item_') for p in n.get('pins',[])) and any(p['name'].startswith('Verb_') for p in n.get('pins',[])))
 item=next(p['name'] for p in br['pins'] if p['name'].startswith('Item_'));verb=next(p['name'] for p in br['pins'] if p['name'].startswith('Verb_'))
 b=Batch(BASE,'BeginPendingRow');b.fn('bare',g.K+'EqualEqual_NameName',-2100,300,B='None');b.link(br['node_id'],item,'bare','A')
 b.fn('use',g.K+'EqualEqual_NameName',-2100,500,B='Use');b.link(br['node_id'],verb,'use','A')
 b.fn('both',g.K+'BooleanAND',-1800,300);b.link('bare','ReturnValue','both','A');b.link('use','ReturnValue','both','B')
 b.node('rowkind','branch',-1500,0);b.link('both','ReturnValue','rowkind','Condition');b.cut(e,'then',old['to_node'],old['to_pin']);b.link(e,'then','rowkind','execute');b.link('rowkind','else',old['to_node'],old['to_pin'])
 b.fn('pawn','/Script/Engine.GameplayStatics:GetPlayerCharacter',-1500,650,PlayerIndex=0);b.node('cast','cast',-1200,0,class_path=g.PC);b.link('pawn','ReturnValue','cast','Object');b.link('rowkind','then','cast','execute');b.link('cast','CastFailed',old['to_node'],old['to_pin'])
 b.node('self','self',-1200,650);b.fn('prepare',g.PC+':BeginEnvironmentContact',-900,0,Seconds=0);b.link('cast','AsBP Fo APlayer','prepare','self');b.link('self','self','prepare','Target');b.chain('cast','prepare')
 b.get('reachable','EnvironmentContactReachable',-900,400,g.PC);b.link('cast','AsBP Fo APlayer','reachable','self');b.node('range','branch',-600,0);b.link('reachable','EnvironmentContactReachable','range','Condition');b.chain('prepare','range');b.link('range','then',old['to_node'],old['to_pin'])
 b.fn('clear',g.PC+':ClearEnvironmentContact',-300,-450);b.link('cast','AsBP Fo APlayer','clear','self');b.link('range','else','clear','execute')
 b.fn('inter',BC+':GetInteractor',-300,-200);b.fn('say',INTER+':Narrate',0,-450);b.link('inter','Interactor','say','self');b.chain('clear','say')
 b.fn('hint','/Script/Engine.KismetTextLibrary:Conv_StringToText',-300,-700,InString='Move closer to reach it.');b.link('hint','ReturnValue','say','Line')
 b.comment('Bare hands only',['bare','use','both','rowkind']);b.comment('Check reach before starting',['pawn','cast','self','prepare','reachable','range']);b.comment('Keep controls and retry',['clear','inter','say','hint']);b.run()
 print('Bare-hand reach gate and wrist basis saved',backup)
finally:h.release(owner,lease)
