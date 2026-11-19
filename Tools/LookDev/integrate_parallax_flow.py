"""Route the new actual-room parallax intro once per content version; mark seen only after finish/skip."""
import sys,json
from pathlib import Path
sys.path.insert(0,'P:/FoA/Tools/Unreal');sys.path.insert(0,'P:/FoA/Tools/Unreal/player')
import hayba_call as h
from held_tool_graphs import Batch,inspect,find
FE='/Game/FoA/UI/Framework/BP_FoAFrontEnd';SG='/Game/FoA/UI/Framework/SG_FoASettings';SGC=SG+'.SG_FoASettings_C'
LIB='/Game/FoA/UI/Framework/BPFL_FoASettings.BPFL_FoASettings_C:';W='/Game/FoA/UI/Intro/WBP_IntroStory'
VERSION=2
def c(n,**p):
 r=h.call(n,p);assert r.get('ok'),r
 d=r.get('data',{});assert d.get('ok',True) and not d.get('failed'),d
 return d
assert not c('editor_get_state')['pie_running'],'User PIE active'
owner=h.agent_id() or 'room-takeover';lease=h.lease_acquire(owner,['asset:'+FE,'asset:'+SG],ttl_s=90,wait_s=30)
try:
 c('blueprint_add_variable',path=SG,variable_name='IntroVersionSeen',variable_type='int',default_value='0',category='Progress',update_existing=True)
 c('blueprint_compile',path=SG);c('asset_save',asset_paths=[SG])
 ns,es=inspect(FE,'AfterWakeFade')
 if not any(n['title']=='Get IntroVersionSeen' for n in ns):
  old=find(ns,'Get bSeenIntro');inverse=find(ns,'NOT Boolean');mark=find(ns,'Set bSeenIntro');save=find(ns,'SaveSettings');load=find(ns,'LoadSettings');branch=find(ns,'Branch');create=find(ns,'Create Widget')
  use=next(e for e in es if e['from_node']==inverse and e['from_pin']=='ReturnValue')
  b=Batch(FE,'AfterWakeFade');b.get('version','IntroVersionSeen',300,650,SGC);b.link(load,'Settings','version','self')
  b.fn('new','/Script/Engine.KismetMathLibrary:Less_IntInt',620,650,B=VERSION);b.link('version','IntroVersionSeen','new','A')
  b.cut(use['from_node'],use['from_pin'],use['to_node'],use['to_pin']);b.link('new','ReturnValue',use['to_node'],use['to_pin'])
  b.cut(branch,'then',mark,'execute');b.cut(save,'then',create,'execute');b.chain(branch,create)
  b.ops.append(dict(op='remove',node_ids=[old,inverse,mark,save]));b.comment('Play the new room intro',['version','new']);b.run()
 ns,es=inspect(FE,'OnStoryFinished')
 if not any(n['title']=='Set IntroVersionSeen' for n in ns):
  e=find(ns,'OnStoryFinished');nextedge=next(edge for edge in es if edge['from_node']==e and edge['from_pin']=='then')
  b=Batch(FE,'OnStoryFinished');b.ops.append(dict(op='move',node_id=e,x=-1800,y=0))
  b.fn('settings',LIB+'LoadSettings',-1550,0)
  b.set('version','IntroVersionSeen',-1250,0,SGC);b.pin('version','IntroVersionSeen',VERSION);b.link('settings','Settings','version','self')
  b.set('seen','bSeenIntro',-950,0,SGC);b.pin('seen','bSeenIntro','true');b.link('settings','Settings','seen','self')
  b.fn('save',LIB+'SaveSettings',-650,0);b.link('settings','Settings','save','Settings')
  b.cut(e,'then',nextedge['to_node'],nextedge['to_pin']);b.chain(e,'settings','version','seen','save');b.link('save','then',nextedge['to_node'],nextedge['to_pin'])
  b.comment('Remember a finished intro',['settings','version','seen','save']);b.run()
 for graph,title,pin in [('AfterWakeFade','integer < integer','B'),('OnStoryFinished','Set IntroVersionSeen','IntroVersionSeen')]:
  ns,_=inspect(FE,graph);b=Batch(FE,graph);b.pin(find(ns,title),pin,VERSION);b.run()
 c('blueprint_set_defaults',path=FE,properties={'StoryClass':W+'.WBP_IntroStory_C'})
 result=c('blueprint_compile',path=FE);c('asset_save',asset_paths=[FE,SG])
 proof={'version':VERSION,'compile':result,'save_file_modified':False}
 for graph in ['AfterWakeFade','OnStoryFinished']:
  ns,es=inspect(FE,graph);proof[graph]={'nodes':ns,'edges':es}
 assert not any(n['title'] in ['Set bSeenIntro','SaveSettings'] for n in proof['AfterWakeFade']['nodes'])
 assert any(n['title']=='Set IntroVersionSeen' for n in proof['OnStoryFinished']['nodes'])
 Path('P:/FoA/Saved/LookDev/intro_restored/versioned_frontend_integration.json').write_text(json.dumps(proof,indent=1))
 print('New parallax version integrated; marks seen only after finish/skip; compile clean',result)
finally:h.release(owner,lease)
