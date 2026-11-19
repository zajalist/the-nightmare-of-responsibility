"""Add the post-fall clothing search in place; native Hayba graph batches only.

Run after BP_RoomTakeover is declared, then configure_clothing_search.py under the actor/data leases.
"""
import sys
sys.path.insert(0, 'P:/FoA/Tools/Unreal')
sys.path.insert(0, 'P:/FoA/Tools/Unreal/player')
import hayba_call as h
from held_tool_graphs import Batch, inspect, find

P='/Game/FoA/Gameplay/BP_BeatDirector'; C=P+'.BP_BeatDirector_C'
BASE='/Game/FoA/Gameplay/BP_Interactable.BP_Interactable_C'
ROOM='/Game/FoA/Gameplay/Ambient/BP_RoomTakeover.BP_RoomTakeover_C'
INTER='/Game/FoA/Gameplay/BPC_Interactor.BPC_Interactor_C'
INVENTORY='/Game/FoA/Gameplay/BPC_Inventory.BPC_Inventory_C'
K='/Script/Engine.KismetMathLibrary:'; GS='/Script/Engine.GameplayStatics:'; KS='/Script/Engine.KismetSystemLibrary:'
A='/Script/Engine.Actor:'
STEPS=[('ClothingWardrobeSearched',1,'SearchWardrobeClue'),('ClothingDeskSearched',2,'SearchDeskClue'),
       ('ClothingBedSearched',3,'SearchBedClue'),('ClothingUnhooked',4,'FreeClothing'),
       ('ClothingTryUnhook',4,'TryClothingHanger')]
CHASE_STEPS=[('ClothingReachOne',5,'EscapeClothingOne'),('ClothingReachTwo',6,'EscapeClothingTwo'),
             ('ClothingReachFinal',7,'ReachClothingVase')]

def call(cmd,**params):
 r=h.call(cmd,params);assert r.get('ok'),r
 d=r.get('data',{});assert d.get('ok',True),d
 return d

def fresh(name):
 ns,_=inspect(P,name);e=find(ns,name);b=Batch(P,name)
 old=[n['node_id'] for n in ns if n['node_id']!=e and n['title']!='Return Node']
 if old:b.ops.append(dict(op='remove',node_ids=old))
 return b,e

def finish(b,title):
 b.comment(title,[o['ref'] for o in b.ops if o.get('op')=='add_node']);b.run()

def state(b,ref,var,value,x):
 b.get(ref+'actor',var,x,250)
 b.fn(ref,BASE+':SetState',x,0,NewState=value,bInstant='true')
 b.link(ref+'actor',var,ref,'self')
 return ref

def room(b,after,stage):
 b.fn('room',GS+'GetActorOfClass',4200,0,ActorClass=ROOM)
 b.fn('valid',KS+'IsValid',4200,250);b.link('room','ReturnValue','valid','Object')
 b.node('exists','branch',4500,0);b.link('valid','ReturnValue','exists','Condition')
 b.fn('takeover',ROOM+(':'+ 'Reset' if stage==0 else ':SetStage'),4800,0,**({} if stage==0 else {'NewStage':stage}))
 b.link('room','ReturnValue','takeover','self');b.chain(after,'room','exists','takeover')

def prepend(graph,fn,event=False):
 ns,es=inspect(P,graph)
 if any(n['title']==fn for n in ns):return
 e=find(ns,graph);edge=next(x for x in es if x['from_node']==e and x['from_pin']=='then')
 b=Batch(P,graph);b.fn('search',C+':'+fn,-650,-600)
 if event:b.link(e,'Event','search','Event')
 b.cut(e,'then',edge['to_node'],edge['to_pin']);b.chain(e,'search');b.link('search','then',edge['to_node'],edge['to_pin']);b.run()

def build_hanger():
  b,e=fresh('TryClothingHanger');b.get('bed','SearchBed',0,300)
  b.fn('inter',BASE+':GetInteractor',300,300);b.link('bed','SearchBed','inter','self')
  b.get('bag','Inventory',600,300,INTER);b.link('inter','Interactor','bag','self')
  b.fn('has',INVENTORY+':Has',900,300,Item='Hanger');b.link('bag','Inventory','has','self')
  b.node('owned','branch',900,0);b.link('has','bHas','owned','Condition');b.chain(e,'owned')
  b.fn('use',BASE+':Interact',1300,0,Verb='Use',HeldItem='Hanger');b.link('bed','SearchBed','use','self');b.chain('owned','use')
  b.fn('text','/Script/Engine.KismetTextLibrary:Conv_StringToText',900,-500,InString="Can't reach. The hanger on the coat rail might.")
  b.fn('hint',INTER+':Narrate',1250,-300);b.link('text','ReturnValue','hint','Line')
  b.link('inter','Interactor','hint','self');b.link('owned','else','hint','execute')
  finish(b,'Use the hanger already in the inventory')


def build_handler():
  b,e=fresh('HandleClothingSearch');b.get('stage','ClothingSearchStage',0,300);b.get('rolling','bRollingOver',0,500)
  b.node('active','branch',250,0);b.link('rolling','bRollingOver','active','Condition');b.chain(e,'active')
  previous='active'
  steps=STEPS+([s for s in CHASE_STEPS] if h.call('blueprint_inspect_graph',dict(path=P,graph_name='BeginClothingToss')).get('ok') else [])
  for j,(event,stage,fn) in enumerate(steps):
   x=600+j*800;ref='s'+str(j)
   b.fn(ref+'event',K+'EqualEqual_NameName',x,300,B=event);b.link(e,'Event',ref+'event','A')
   b.fn(ref+'stage',K+'EqualEqual_IntInt',x,500,B=stage);b.link('stage','ClothingSearchStage',ref+'stage','A')
   b.fn(ref+'both',K+'BooleanAND',x+250,300);b.link(ref+'event','ReturnValue',ref+'both','A');b.link(ref+'stage','ReturnValue',ref+'both','B')
   b.node(ref,'branch',x+250,0);b.link(ref+'both','ReturnValue',ref,'Condition');b.link(previous,'else',ref,'execute')
   b.fn(ref+'advance',C+':'+fn,x+500,-250);b.chain(ref,ref+'advance');previous=ref
  finish(b,'Advance each clue once')


def main():
 assert not call('editor_get_state')['pie_running']
 if '--hanger' in sys.argv:
  lease=h.lease_acquire(h.agent_id(),['asset:'+P],ttl_s=120,wait_s=30)
  try:build_hanger();build_handler()
  finally:h.release(h.agent_id(),lease)
  return
 lease=h.lease_acquire(h.agent_id(),['asset:'+P],ttl_s=240,wait_s=30)
 try:
  for n,t,v in [('ClothingSearchStage','int','0'),('SearchWardrobe','object:'+BASE,''),('SearchDesk','object:'+BASE,''),
               ('SearchBed','object:'+BASE,''),('SearchShirt','object:'+BASE,''),('ClothingShirtHome','transform',''),
               ('ClothingShirtSpot','vector','')]:
   call('blueprint_add_variable',path=P,variable_name=n,variable_type=t,default_value=v,category='Clothing search',update_existing=True,
        instance_editable=n.startswith('Search') or n=='ClothingShirtSpot')
  for n in ['StartClothingSearch','ResetClothingSearch']+[s[2] for s in STEPS]+['HandleClothingSearch','CanReportClothingEvent']:
   if not h.call('blueprint_inspect_graph',dict(path=P,graph_name=n)).get('ok'):
    kw={'inputs':[dict(name='Event',type='name')]} if n in ('HandleClothingSearch','CanReportClothingEvent') else {}
    if n=='CanReportClothingEvent':kw.update(outputs=[dict(name='Allowed',type='bool')],pure=True)
    call('blueprint_add_function',path=P,function_name=n,**kw)

  b,e=fresh('StartClothingSearch');b.get('stage','ClothingSearchStage',0,250)
  b.fn('zero',K+'EqualEqual_IntInt',250,250,B=0);b.link('stage','ClothingSearchStage','zero','A')
  b.node('once','branch',250,0);b.link('zero','ReturnValue','once','Condition');b.chain(e,'once')
  b.get('shirt','SearchShirt',500,400);b.fn('home',A+'GetTransform',750,400);b.link('shirt','SearchShirt','home','self')
  b.set('remember','ClothingShirtHome',500,0);b.link('home','ReturnValue','remember','ClothingShirtHome')
  b.set('stage1','ClothingSearchStage',800,0);b.pin('stage1','ClothingSearchStage',1)
  state(b,'hide','SearchShirt','Hidden',1100);state(b,'wardrobe','SearchWardrobe','SearchWardrobe',1500)
  state(b,'desk','SearchDesk','SearchWaiting',1900);state(b,'bed','SearchBed','SearchWaiting',2300)
  b.chain('once','remember','stage1','hide','wardrobe','desk','bed');room(b,'bed',1);finish(b,'Begin the clothing search')

  for name,stage,var,value,flag in [('SearchWardrobeClue',2,'SearchDesk','SearchDesk','Knows.ClothingThread'),
    ('SearchDeskClue',3,'SearchBed','SearchBed','Knows.ClothingTrail'),
    ('SearchBedClue',4,'SearchBed','ClothingSnag','Knows.ClothingSnag')]:
   b,e=fresh(name);b.set('stage','ClothingSearchStage',300,0);b.pin('stage','ClothingSearchStage',stage)
   state(b,'next',var,value,650)
   b.fn('learn',C+':LearnFlag',1000,0,Flag=flag);b.chain(e,'stage','next','learn');room(b,'learn',stage)
   inspection={'SearchWardrobeClue':'QueueClothingWardrobe','SearchDeskClue':'QueueClothingDesk','SearchBedClue':'QueueClothingBed'}[name]
   if h.call('blueprint_inspect_graph',dict(path=P,graph_name=inspection)).get('ok'):
    b.fn('inspect',C+':'+inspection,5100,0);b.chain('takeover','inspect')
   finish(b,'Follow the next clue')

  b,e=fresh('FreeClothing')
  chase=h.call('blueprint_inspect_graph',dict(path=P,graph_name='BeginClothingToss')).get('ok')
  if chase:
   b.fn('toss',C+':BeginClothingToss',300,0);b.chain(e,'toss');finish(b,'Pull the shirt free with the hanger')
  else:
   b.set('stage','ClothingSearchStage',300,0);b.pin('stage','ClothingSearchStage',5)
   b.get('shirt','SearchShirt',400,300);b.get('spot','ClothingShirtSpot',700,300)
   b.fn('place',A+'K2_SetActorLocation',700,0,bSweep='false',bTeleport='true')
   b.link('shirt','SearchShirt','place','self');b.link('spot','ClothingShirtSpot','place','NewLocation')
   b.fn('reveal',C+':RevealShirt',1100,0);b.chain(e,'stage','place','reveal');room(b,'reveal',5);finish(b,'Unhook the real shirt')

  build_hanger();build_handler()

  b,e=fresh('CanReportClothingEvent');ns,_=inspect(P,'CanReportClothingEvent');ret=find(ns,'Return Node')
  b.fn('other',K+'NotEqual_NameName',300,200,B='ShirtTaken');b.link(e,'Event','other','A')
  b.get('stage','ClothingSearchStage',0,450);b.fn('ready',K+'EqualEqual_IntInt',300,450,B=9 if chase else 5);b.link('stage','ClothingSearchStage','ready','A')
  b.fn('allowed',K+'BooleanOR',600,200);b.link('other','ReturnValue','allowed','A');b.link('ready','ReturnValue','allowed','B')
  b.link('allowed','ReturnValue',ret,'Allowed');b.chain(e,ret);finish(b,'Only the freed shirt starts battle')

  b,e=fresh('ResetClothingSearch');b.get('stage','ClothingSearchStage',0,250);b.fn('active',K+'Greater_IntInt',300,250,B=0)
  b.link('stage','ClothingSearchStage','active','A');b.node('guard','branch',300,0);b.link('active','ReturnValue','guard','Condition');b.chain(e,'guard')
  b.get('shirt','SearchShirt',600,250);b.get('home','ClothingShirtHome',900,250)
  b.fn('restore',A+'K2_SetActorTransform',900,0,bSweep='false',bTeleport='true');b.link('shirt','SearchShirt','restore','self');b.link('home','ClothingShirtHome','restore','NewTransform')
  b.set('zero','ClothingSearchStage',1250,0);b.pin('zero','ClothingSearchStage',0);b.chain('guard','restore','zero')
  room(b,'zero',0);finish(b,'Restore the morning search state')
  if h.call('blueprint_inspect_graph',dict(path=P,graph_name='CancelClothingInspection')).get('ok'):
   prepend('ResetClothingSearch','CancelClothingInspection')

  prepend('ReportEvent','HandleClothingSearch',True);prepend('ResetHouse','ResetClothingSearch')
  ns,es=inspect(P,'StageWrongWall')
  if not any(n['title']=='StartClothingSearch' for n in ns):
   old=find(ns,'RevealShirt');before=next(x for x in es if x['to_node']==old and x['to_pin']=='execute');after=next(x for x in es if x['from_node']==old and x['from_pin']=='then')
   b=Batch(P,'StageWrongWall');b.ops.append(dict(op='remove',node_ids=[old]));b.fn('search',C+':StartClothingSearch',1152,-128)
   b.link(before['from_node'],before['from_pin'],'search','execute');b.link('search','then',after['to_node'],after['to_pin']);b.run()
  ns,es=inspect(P,'ReportEvent')
  if not any(n['title']=='CanReportClothingEvent' for n in ns):
   e=find(ns,'ReportEvent');handler=find(ns,'HandleClothingSearch');edge=next(x for x in es if x['from_node']==handler and x['from_pin']=='then')
   b=Batch(P,'ReportEvent');b.fn('allowed',C+':CanReportClothingEvent',-600,-300);b.link(e,'Event','allowed','Event')
   b.node('guard','branch',-300,-300);b.link('allowed','Allowed','guard','Condition');b.cut(handler,'then',edge['to_node'],edge['to_pin'])
   b.chain(handler,'guard');b.link('guard','then',edge['to_node'],edge['to_pin']);b.run()
  print('Clothing search compiled and saved; configure references and priority table rows before PIE.')
 finally:h.release(h.agent_id(),lease)

if __name__=='__main__':main()
