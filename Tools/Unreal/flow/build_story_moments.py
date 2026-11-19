"""Event-driven inner monologues and three brief, owned headache reactions."""
import sys
sys.path.insert(0, 'P:/FoA/Tools/Unreal')
sys.path.insert(0, 'P:/FoA/Tools/Unreal/player')
import hayba_call as h
from held_tool_graphs import Batch, inspect, find

P='/Game/FoA/Gameplay/BP_BeatDirector'; C=P+'.BP_BeatDirector_C'
PLAYER='/Game/FoA/Characters/Player/BP_FoAPlayer.BP_FoAPlayer_C'
FE='/Game/FoA/UI/Framework/BP_FoAFrontEnd.BP_FoAFrontEnd_C'
DREAM='/Game/FoA/PostProcess/BP_DreamDirector.BP_DreamDirector_C'
INTER='/Game/FoA/Gameplay/BPC_Interactor.BPC_Interactor_C'
K='/Script/Engine.KismetMathLibrary:'; GS='/Script/Engine.GameplayStatics:'; KS='/Script/Engine.KismetSystemLibrary:'
MONTAGE='/Game/FoA/Characters/Player/Montages/AM_FoA_Headache.AM_FoA_Headache'
sys.path.insert(0, 'P:/FoA/Tools/Unreal/flow')
from story_text import STORY_MOMENTS as LINES  # the approved script (docs/design/story/script.md)
HEADACHES={2,5,7}

def call(cmd,**params):
 r=h.call(cmd,params);assert r.get('ok'),r
 d=r.get('data',{});assert d.get('ok',True),d
 return d
def fresh(name):
 ns,_=inspect(P,name);e=find(ns,name);b=Batch(P,name)
 old=[n['node_id'] for n in ns if n['node_id']!=e]
 if old:b.ops.append(dict(op='remove',node_ids=old))
 return b,e
def timer(b,ref,fn,x,y,seconds,loop=False):
 return b.fn(ref,KS+'K2_SetTimer',x,y,FunctionName=fn,Time=seconds,bLooping=str(loop).lower())
def finish(b,title):
 refs=[o['ref'] for o in b.ops if o.get('op')=='add_node']
 b.comment(title,refs);b.run()
def prepend(graph,fn):
 ns,es=inspect(P,graph)
 if any(n['title']==fn for n in ns):return
 e=find(ns,graph) if graph!='EventGraph' else next(n['node_id'] for n in ns if n['title']=='Event BeginPlay')
 edge=next(x for x in es if x['from_node']==e and x['from_pin']=='then')
 b=Batch(P,graph);b.fn('story',C+':'+fn,0,-600)
 b.cut(e,'then',edge['to_node'],edge['to_pin']);b.chain(e,'story');b.link('story','then',edge['to_node'],edge['to_pin']);b.run()

def main():
 assert HEADACHES<=LINES.keys() and all(0<len(t)<140 for t in LINES.values())
 assert not call('editor_get_state')['pie_running']
 lease=h.lease_acquire(h.agent_id(),['asset:'+P],ttl_s=180,wait_s=30)
 try:
  for n,t,default in [('StoryLastBeat','int','-1'),('StoryPendingBeat','int','-1'),('bHeadacheActive','bool','false'),
   ('StoryEchoHome','float','0'),('StoryStarted','float','0'),('StoryPlayer','object:'+PLAYER,''),
   ('StoryController','object:/Script/Engine.PlayerController',''),('StoryDream','object:'+DREAM,'')]:
   call('blueprint_add_variable',path=P,variable_name=n,variable_type=t,default_value=default,category='Story',update_existing=True)
  for n in ('StartStoryMoments','PollStoryMoment','TryStoryMoment','StartHeadache','StepHeadache','EndHeadache','ResetStoryMoments'):
   if not h.call('blueprint_inspect_graph',dict(path=P,graph_name=n)).get('ok'):
    call('blueprint_add_function',path=P,function_name=n)

  b,e=fresh('StartStoryMoments');timer(b,'poll','PollStoryMoment',280,0,.25,True);b.chain(e,'poll');finish(b,'Watch story changes')
  b,e=fresh('PollStoryMoment')
  b.get('active','bHeadacheActive',0,200);b.node('idle','branch',250,0);b.link('active','bHeadacheActive','idle','Condition');b.chain(e,'idle')
  b.fn('frontend',GS+'GetActorOfClass',500,0,ActorClass=FE);b.link('idle','else','frontend','execute')
  b.get('game','bInGameplay',500,250,FE);b.link('frontend','ReturnValue','game','self')
  b.node('playing','branch',800,0);b.link('game','bInGameplay','playing','Condition');b.chain('frontend','playing')
  b.get('beat','BeatIndex',800,250);b.get('last','StoryLastBeat',800,400)
  b.fn('new',K+'NotEqual_IntInt',1050,250);b.link('beat','BeatIndex','new','A');b.link('last','StoryLastBeat','new','B')
  b.node('changed','branch',1300,0);b.link('new','ReturnValue','changed','Condition');b.chain('playing','changed')
  b.set('remember','StoryLastBeat',1550,0);b.set('pending','StoryPendingBeat',1800,0)
  for ref,var in [('remember','StoryLastBeat'),('pending','StoryPendingBeat')]:b.link('beat','BeatIndex',ref,var)
  timer(b,'defer','TryStoryMoment',2050,0,2.4,True);b.chain('changed','remember','pending','defer');finish(b,'Queue story beat')

  b,e=fresh('TryStoryMoment')
  b.fn('pawn',GS+'GetPlayerCharacter',0,250,PlayerIndex=0);b.node('cast','cast',260,0,class_path=PLAYER)
  b.link('pawn','ReturnValue','cast','Object');b.chain(e,'cast')
  b.fn('pc',GS+'GetPlayerController',260,500,PlayerIndex=0)
  conditions=[]
  for j,(var,cls,source,pin) in enumerate([('bCinematic',PLAYER,'cast','AsBP Fo APlayer'),('bInteractionLocked',PLAYER,'cast','AsBP Fo APlayer'),('bWardrobeTransition',None,None,None),('bRollingOver',None,None,None)]):
   ref='busy'+str(j);b.get(ref,var,600,j*160+300,cls)
   if source:b.link(source,pin,ref,'self')
   conditions.append((ref,var))
  b.fn('move','/Script/Engine.Controller:IsMoveInputIgnored',600,1000);b.link('pc','ReturnValue','move','self');conditions.append(('move','ReturnValue'))
  b.fn('view','/Script/Engine.PlayerController:GetViewTarget',600,1200);b.link('pc','ReturnValue','view','self')
  b.fn('away',K+'NotEqual_ObjectObject',900,1200);b.link('view','ReturnValue','away','A');b.link('pawn','ReturnValue','away','B');conditions.append(('away','ReturnValue'))
  b.get('movement','CharacterMovement',600,1400,'/Script/Engine.Character');b.link('pawn','ReturnValue','movement','self')
  b.fn('fall','/Script/Engine.CharacterMovementComponent:IsFalling',900,1400);b.link('movement','CharacterMovement','fall','self');conditions.append(('fall','ReturnValue'))
  b.get('pending','StoryPendingBeat',600,1650);b.get('current','BeatIndex',600,1800)
  b.fn('stale',K+'NotEqual_IntInt',900,1650);b.link('pending','StoryPendingBeat','stale','A');b.link('current','BeatIndex','stale','B');conditions.append(('stale','ReturnValue'))
  previous=conditions[0]
  for j,cond in enumerate(conditions[1:]):
   ref='or'+str(j);b.fn(ref,K+'BooleanOR',1200+j*220,350);b.link(*previous,ref,'A');b.link(*cond,ref,'B');previous=(ref,'ReturnValue')
  b.node('free','branch',2900,0);b.link(*previous,'free','Condition');b.chain('cast','free')
  b.fn('clear',KS+'K2_ClearTimer',3150,0,FunctionName='TryStoryMoment');b.link('free','else','clear','execute')
  b.set('player','StoryPlayer',3400,0);b.link('cast','AsBP Fo APlayer','player','StoryPlayer');b.chain('clear','player')
  b.fn('inter','/Script/Engine.Actor:GetComponentByClass',3400,450,ComponentClass=INTER);b.link('pawn','ReturnValue','inter','self')
  previous='player'
  for j,(beat,line) in enumerate(LINES.items()):
   x=3750+j*450;ref='case'+str(beat)
   b.fn(ref+'test',K+'EqualEqual_IntInt',x,300,B=beat);b.link('pending','StoryPendingBeat',ref+'test','A')
   b.node(ref,'branch',x,0);b.link(ref+'test','ReturnValue',ref,'Condition');b.link(previous,'then' if j==0 else 'else',ref,'execute')
   b.fn(ref+'text','/Script/Engine.KismetTextLibrary:Conv_StringToText',x,-300,InString=line)
   speak=b.fn(ref+'line',INTER+':Narrate',x,-500);b.link('inter','ReturnValue',speak,'self');b.link(ref+'text','ReturnValue',speak,'Line')
   if beat in HEADACHES:
    b.fn(ref+'ache',C+':StartHeadache',x,-750);b.chain(ref,ref+'ache',speak)
   else:b.chain(ref,speak)
   previous=ref
  finish(b,'Speak when free')

  b,e=fresh('StartHeadache');b.get('active','bHeadacheActive',0,250);b.node('once','branch',250,0);b.link('active','bHeadacheActive','once','Condition');b.chain(e,'once')
  b.set('own','bHeadacheActive',500,0);b.pin('own','bHeadacheActive','true');b.link('once','else','own','execute')
  b.get('player','StoryPlayer',500,300);b.fn('pc',GS+'GetPlayerController',750,300,PlayerIndex=0)
  b.set('cachepc','StoryController',750,0);b.link('pc','ReturnValue','cachepc','StoryController')
  b.fn('dream',GS+'GetActorOfClass',1000,0,ActorClass=DREAM);b.set('cachedream','StoryDream',1250,0);b.link('dream','ReturnValue','cachedream','StoryDream')
  b.get('echo','BaseEcho',1250,300,DREAM);b.link('dream','ReturnValue','echo','self');b.set('home','StoryEchoHome',1500,0);b.link('echo','BaseEcho','home','StoryEchoHome')
  b.fn('now',GS+'GetTimeSeconds',1500,400);b.set('start','StoryStarted',1750,0);b.link('now','ReturnValue','start','StoryStarted')
  # The line plays over gameplay: no input lock, no cinematic, the interactor stays live (QA B1, 2026-11-09).
  timer(b,'pulse','StepHeadache',3500,0,.033333,True);timer(b,'end','EndHeadache',3750,0,4.0)
  b.chain('own','cachepc','dream','cachedream','home','start','pulse','end')
  finish(b,'Brief headache reaction')

  b,e=fresh('StepHeadache');b.get('active','bHeadacheActive',0,200);b.node('guard','branch',260,0);b.link('active','bHeadacheActive','guard','Condition');b.chain(e,'guard')
  b.fn('now',GS+'GetTimeSeconds',0,400);b.get('start','StoryStarted',0,550)
  b.fn('elapsed',K+'Subtract_DoubleDouble',300,400);b.link('now','ReturnValue','elapsed','A');b.link('start','StoryStarted','elapsed','B')
  b.fn('u',K+'FClamp',550,400,Min=0,Max=4);b.link('elapsed','ReturnValue','u','Value')
  b.fn('angle',K+'Multiply_DoubleDouble',800,400,B=.78539816339);b.link('u','ReturnValue','angle','A')
  b.fn('sin',K+'Sin',1050,400);b.link('angle','ReturnValue','sin','A')
  b.fn('curve',K+'Multiply_DoubleDouble',1300,400);b.link('sin','ReturnValue','curve','A');b.link('sin','ReturnValue','curve','B')
  b.fn('motion','/Script/Engine.KismetMaterialLibrary:GetScalarParameterValue',550,0,Collection='/Game/FoA/PostProcess/MPC_Dream.MPC_Dream',ParameterName='ReduceMotion')
  b.fn('reduce',K+'Greater_DoubleDouble',800,700,B=.5);b.link('motion','ReturnValue','reduce','A')
  b.fn('amount',K+'SelectFloat',1050,700,A=0,B=.24);b.link('reduce','ReturnValue','amount','bPickA')
  b.fn('boost',K+'Multiply_DoubleDouble',1550,400);b.link('curve','ReturnValue','boost','A');b.link('amount','ReturnValue','boost','B')
  b.get('home','StoryEchoHome',1550,700);b.fn('sum',K+'Add_DoubleDouble',1800,400);b.link('home','StoryEchoHome','sum','A');b.link('boost','ReturnValue','sum','B')
  b.get('dream','StoryDream',1800,700);b.fn('apply',DREAM+':SetEchoStrength',2100,0);b.link('dream','StoryDream','apply','self');b.link('sum','ReturnValue','apply','Amount');b.chain('guard','motion','apply')
  finish(b,'Ease vision distortion')

  b,e=fresh('EndHeadache');b.get('active','bHeadacheActive',0,200);b.node('guard','branch',250,0);b.link('active','bHeadacheActive','guard','Condition');b.chain(e,'guard')
  b.set('off','bHeadacheActive',500,0);b.pin('off','bHeadacheActive','false')
  b.fn('clear',KS+'K2_ClearTimer',750,0,FunctionName='StepHeadache');b.fn('endtimer',KS+'K2_ClearTimer',1000,0,FunctionName='EndHeadache')
  b.get('dream','StoryDream',1000,300);b.get('echo','StoryEchoHome',1250,300)
  b.fn('restore',DREAM+':SetEchoStrength',1250,0);b.link('dream','StoryDream','restore','self');b.link('echo','StoryEchoHome','restore','Amount')
  b.chain('guard','off','clear','endtimer','restore');finish(b,'Release owned controls')

  b,e=fresh('ResetStoryMoments');b.fn('end',C+':EndHeadache',250,0);b.fn('clear',KS+'K2_ClearTimer',500,0,FunctionName='TryStoryMoment')
  b.set('last','StoryLastBeat',750,0);b.pin('last','StoryLastBeat',-1);b.set('pending','StoryPendingBeat',1000,0);b.pin('pending','StoryPendingBeat',-1)
  b.chain(e,'end','clear','last','pending');finish(b,'Reset story moments')
  prepend('EventGraph','StartStoryMoments');prepend('ResetHouse','ResetStoryMoments')
  print('Story moments compiled and saved. Runtime verification pending.')
 finally:h.release(h.agent_id(),lease)

if __name__=='__main__':
 main()
 import runpy
 from pathlib import Path
 runpy.run_path(str(Path(__file__).with_name('fix_headache_thought.py')),run_name='__main__')
 # build_headache_blink.py is retired: in-play headaches never close the eyelids (no letterbox look; QA 2026-11-09).
 runpy.run_path(str(Path(__file__).with_name('patch_headache_no_lids.py')),run_name='__main__')
