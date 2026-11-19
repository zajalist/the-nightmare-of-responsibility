"""Chair becomes an owned sand apparition, then returns exactly. Native Hayba graphs.
Stage>=4 plus painting seen triggers once; Stage0 and EndPlay restore/rearm.
The original chair's transform, mesh, material slots and collision are never written.
"""
import sys
sys.path.insert(0,'P:/FoA/Tools/Unreal')
sys.path.insert(0,'P:/FoA/Tools/Unreal/player')
import hayba_call as h
from held_tool_graphs import Batch,inspect,find

P='/Game/FoA/Gameplay/Ambient/BP_ChairNightmare';C=P+'.BP_ChairNightmare_C'
ROOM='/Game/FoA/Gameplay/Ambient/BP_RoomTakeover.BP_RoomTakeover_C'
K='/Script/Engine.KismetMathLibrary:';KS='/Script/Engine.KismetSystemLibrary:'
SC='/Script/Engine.SceneComponent:';MC='/Script/Engine.MeshComponent:';PC='/Script/Engine.PrimitiveComponent:'
MID='/Script/Engine.MaterialInstanceDynamic:';GS='/Script/Engine.GameplayStatics:'
SAND='/Game/FoA/VFX/Sand/M_SandOverlay.M_SandOverlay'
SUIT='/Game/FoA/VFX/Splats/Meshes/SM_SandSuit/SM_SandSuit/StaticMeshes/SM_SandSuit'
SND='/Game/FoA/Audio/MetaSounds/Sand/S_Sand_'
CHAIR='/Game/FoA/Props/painted_wooden_chair_01/painted_wooden_chair_01_1k/StaticMeshes/painted_wooden_chair_01_1k'

def call(cmd,**params):
    r=h.call(cmd,params);assert r.get('ok'),r
    d=r.get('data',{});assert d.get('ok',True) and not d.get('failed'),d
    return d
def graph(name):
    ns,_=inspect(P,name);e=find(ns,name);b=Batch(P,name)
    old=[n['node_id'] for n in ns if n['node_id']!=e]
    if old:b.ops.append(dict(op='remove',node_ids=old))
    return b,e
def done(b,title):b.comment(title,[o['ref'] for o in b.ops if o.get('op')=='add_node']);b.run()
def timer(b,ref,fn,x,y,t,loop=False):
    return b.fn(ref,KS+'K2_SetTimer',x,y,FunctionName=fn,Time=t,bLooping=str(loop).lower())
def clear(b,ref,fn,x,y):return b.fn(ref,KS+'K2_ClearTimer',x,y,FunctionName=fn)
def visible(b,ref,var,x,y,value=None):
    b.get(ref+'obj',var,x,y+200);b.fn(ref,SC+'SetVisibility',x,y)
    b.link(ref+'obj',var,ref,'self')
    if value is not None:b.pin(ref,'bNewVisibility',str(value).lower())
def suit_event(b,ref,x,y,forming,delay=0):
    b.get(ref+'suit','Apparition',x,y+220);b.fn(ref+'now',GS+'GetTimeSeconds',x,y+420)
    b.fn(ref+'time',K+'Add_DoubleDouble',x+240,y+420,B=delay);b.link(ref+'now','ReturnValue',ref+'time','A')
    b.fn(ref+'value',K+'MakeVector4',x+480,y+220,X=1 if forming else 0,Z=1.2 if forming else 1,W=0 if forming else 1)
    b.link(ref+'time','ReturnValue',ref+'value','Y')
    b.fn(ref,PC+'SetVectorParameterForCustomPrimitiveData',x+720,y,ParameterName='SandEvent')
    b.link(ref+'suit','Apparition',ref,'self');b.link(ref+'value','ReturnValue',ref,'Value')

def assets():
    if not h.call('blueprint_get_info',{'path':P}).get('ok'):
        call('blueprint_create',name='BP_ChairNightmare',package_path=P,parent_class_path='/Script/Engine.Actor')
    info=call('blueprint_get_info',path=P);have={x['name'] for x in info['components']}
    for name,cls in [('Root','SceneComponent'),('ChairShell','StaticMeshComponent'),('Apparition','StaticMeshComponent')]:
        if name not in have:call('blueprint_add_component',path=P,component_name=name,component_class_path='/Script/Engine.'+cls)
    for name,mesh,mat in [('ChairShell',CHAIR,SAND),('Apparition',SUIT,'/Game/FoA/VFX/Splats/Instances/MI_Sand_Suit')]:
        call('object_set_property',path=C+':'+name+'_GEN_VARIABLE',properties={'StaticMesh':mesh,'OverrideMaterials':[mat],
            'bVisible':False,'CastShadow':False,'bGenerateOverlapEvents':False,'Mobility':'Movable',
            'bRenderCustomDepth':True,'CustomDepthStencilValue':5,
            'BodyInstance':'(CollisionProfileName="NoCollision",CollisionEnabled=NoCollision)'})
    variables=[('ChairMesh','object:/Script/Engine.StaticMeshComponent','',True),('Takeover','object:'+ROOM,'',True),
               ('OriginalOverlay','object:/Script/Engine.MaterialInterface','',False),
               ('GrainMID','object:/Script/Engine.MaterialInstanceDynamic','',False),
               ('OriginalVisible','bool','true',False),('bActive','bool','false',False),('bPlayed','bool','false',False),
               ('StartTime','float','0',False),('PlayCount','int','0',False),('PaintingSeenAt','float','-1',False)]
    for n,t,v,editable in variables:
        call('blueprint_add_variable',path=P,variable_name=n,variable_type=t,default_value=v,instance_editable=editable,
             update_existing=True,category='Chair vision')
    for fn in ('Poll','StartVision','Animate','Crumble','FinishVision','Reset'):
        if fn not in info['functions']:call('blueprint_add_function',path=P,function_name=fn)
    call('blueprint_compile',path=P);call('asset_save',asset_paths=[P])

def sound(b,ref,key,x,y):
    b.get(ref+'at','Apparition',x,y+220);b.fn(ref,GS+'SpawnSoundAttached',x,y,Sound=SND+key+'.S_Sand_'+key)
    b.link(ref+'at','Apparition',ref,'AttachToComponent')
def start():
    b,e=graph('StartVision')
    b.get('chair','ChairMesh',0,240);b.get('active','bActive',0,400)
    b.fn('notActive',K+'Not_PreBool',250,400);b.link('active','bActive','notActive','A')
    b.node('guard','branch',500,0);b.link('notActive','ReturnValue','guard','Condition')
    b.fn('overlay',MC+'GetOverlayMaterial',500,240);b.link('chair','ChairMesh','overlay','self')
    b.set('cacheOverlay','OriginalOverlay',750,0);b.link('overlay','ReturnValue','cacheOverlay','OriginalOverlay')
    b.fn('isVisible',SC+'IsVisible',750,240);b.link('chair','ChairMesh','isVisible','self')
    b.set('cacheVisible','OriginalVisible',1000,0);b.link('isVisible','ReturnValue','cacheVisible','OriginalVisible')
    b.fn('make','/Script/Engine.KismetMaterialLibrary:CreateDynamicMaterialInstance',1250,0,Parent=SAND)
    b.set('cacheMID','GrainMID',1500,0);b.link('make','ReturnValue','cacheMID','GrainMID')
    b.fn('stable',MID+'SetScalarParameterValue',1750,0,ParameterName='Transition',Value=1);b.link('make','ReturnValue','stable','self')
    b.fn('zero',MID+'SetScalarParameterValue',2000,0,ParameterName='Amount',Value=0);b.link('make','ReturnValue','zero','self')
    b.fn('coat',MC+'SetOverlayMaterial',2250,0);b.link('chair','ChairMesh','coat','self');b.link('make','ReturnValue','coat','NewOverlayMaterial')
    b.get('shell','ChairShell',2500,240)
    b.fn('shellmat',PC+'SetMaterial',2500,0,ElementIndex=0);b.link('shell','ChairShell','shellmat','self');b.link('make','ReturnValue','shellmat','Material')
    b.fn('transform',SC+'K2_GetComponentToWorld',2750,240);b.link('chair','ChairMesh','transform','self')
    b.fn('align',SC+'K2_SetWorldTransform',2750,0);b.link('shell','ChairShell','align','self');b.link('transform','ReturnValue','align','NewTransform')
    b.fn('position',SC+'K2_GetComponentLocation',3000,240);b.link('chair','ChairMesh','position','self')
    b.get('suit','Apparition',3000,400);b.fn('moveSuit',SC+'K2_SetWorldLocation',3250,0)
    b.link('suit','Apparition','moveSuit','self');b.link('position','ReturnValue','moveSuit','NewLocation')
    b.fn('rotation',SC+'K2_GetComponentRotation',3250,240);b.link('chair','ChairMesh','rotation','self')
    b.fn('turnSuit',SC+'K2_SetWorldRotation',3500,0);b.link('suit','Apparition','turnSuit','self');b.link('rotation','ReturnValue','turnSuit','NewRotation')
    b.fn('now',GS+'GetTimeSeconds',3500,400);b.set('time','StartTime',3750,0);b.link('now','ReturnValue','time','StartTime')
    b.set('on','bActive',4000,0);b.pin('on','bActive','true');b.set('played','bPlayed',4250,0);b.pin('played','bPlayed','true')
    b.get('count','PlayCount',4250,240);b.fn('plus',K+'Add_IntInt',4500,240,B=1);b.link('count','PlayCount','plus','A')
    b.set('savecount','PlayCount',4500,0);b.link('plus','ReturnValue','savecount','PlayCount')
    suit_event(b,'form',4750,0,True,.65)
    sound(b,'pour','Pour',5500,0)
    timer(b,'animate','Animate',5750,0,.05,True);timer(b,'crumble','Crumble',6000,0,4);timer(b,'finish','FinishVision',6250,0,6.65)
    b.chain(e,'guard','cacheOverlay','cacheVisible','make','cacheMID','stable','zero','coat','shellmat','align','moveSuit','turnSuit','time','on','played','savecount','form','pour','animate','crumble','finish')
    done(b,'Remember the chair and form an apparition')

def animate():
    b,e=graph('Animate');b.get('active','bActive',0,250);b.node('guard','branch',250,0);b.link('active','bActive','guard','Condition')
    b.fn('now',GS+'GetTimeSeconds',0,450);b.get('start','StartTime',0,600)
    b.fn('t',K+'Subtract_DoubleDouble',250,450);b.link('now','ReturnValue','t','A');b.link('start','StartTime','t','B')
    # Coverage rises, erodes, reforms, then uncovers the real chair.
    operations=[('a',K+'Divide_DoubleDouble','A',.65),('b',K+'Subtract_DoubleDouble','B',1.65),
                ('c',K+'Subtract_DoubleDouble','A',5),('d',K+'Subtract_DoubleDouble','B',6.65)]
    for i,(ref,fn,inputpin,const) in enumerate(operations):
        x=550+i*330;b.fn(ref,fn,x,450,**({'B':const} if inputpin=='A' else {'A':const}));b.link('t','ReturnValue',ref,inputpin)
        src=ref
        if ref=='d':b.fn('ddivide',K+'Divide_DoubleDouble',x,650,B=.65);b.link(ref,'ReturnValue','ddivide','A');src='ddivide'
        b.fn(ref+'clamp',K+'FClamp',x,850,Min=0,Max=1);b.link(src,'ReturnValue',ref+'clamp','Value')
    for ref,a,c,x in [('first','a','b',750),('last','c','d',1400)]:
        b.fn(ref,K+'Multiply_DoubleDouble',x,1100);b.link(a+'clamp','ReturnValue',ref,'A');b.link(c+'clamp','ReturnValue',ref,'B')
    b.fn('coverage',K+'Add_DoubleDouble',1800,850);b.link('first','ReturnValue','coverage','A');b.link('last','ReturnValue','coverage','B')
    b.get('mid','GrainMID',1800,300);b.fn('amount',MID+'SetScalarParameterValue',2050,0,ParameterName='Amount')
    b.link('mid','GrainMID','amount','self');b.link('coverage','ReturnValue','amount','Value')
    for ref,fn,n,y in [('early','Less_DoubleDouble',.65,450),('late','GreaterEqual_DoubleDouble',6,650),('suitAfter','GreaterEqual_DoubleDouble',.65,1050),('suitBefore','Less_DoubleDouble',5,1250)]:
        b.fn(ref,K+fn,2300,y,B=n);b.link('t','ReturnValue',ref,'A')
    b.fn('real',K+'BooleanOR',2600,450);b.link('early','ReturnValue','real','A');b.link('late','ReturnValue','real','B')
    b.get('original','OriginalVisible',2600,650);b.fn('showReal',K+'BooleanAND',2850,450);b.link('real','ReturnValue','showReal','A');b.link('original','OriginalVisible','showReal','B')
    visible(b,'chair','ChairMesh',3100,0);b.link('showReal','ReturnValue','chair','bNewVisibility')
    b.fn('notreal',K+'Not_PreBool',2850,850);b.link('real','ReturnValue','notreal','A')
    visible(b,'shell','ChairShell',3400,0);b.link('notreal','ReturnValue','shell','bNewVisibility')
    b.fn('showSuit',K+'BooleanAND',2850,1100);b.link('suitAfter','ReturnValue','showSuit','A');b.link('suitBefore','ReturnValue','showSuit','B')
    visible(b,'suit','Apparition',3700,0);b.link('showSuit','ReturnValue','suit','bNewVisibility')
    b.chain(e,'guard','amount','chair','shell','suit');done(b,'Grains replace and restore the chair')

def finish():
    b,e=graph('Crumble');suit_event(b,'fall',300,0,False);sound(b,'crumbleSnd','Crumble',1100,0);b.chain(e,'fall','crumbleSnd');done(b,'Return the silhouette to black sand')
    b,e=graph('FinishVision');b.get('active','bActive',0,250);b.node('guard','branch',250,0);b.link('active','bActive','guard','Condition')
    clear(b,'clear','Animate',500,0);clear(b,'clearCrumble','Crumble',750,0);clear(b,'clearFinish','FinishVision',1000,0)
    b.get('chair','ChairMesh',1000,250);b.get('old','OriginalOverlay',1250,250)
    b.fn('restore',MC+'SetOverlayMaterial',1250,0);b.link('chair','ChairMesh','restore','self');b.link('old','OriginalOverlay','restore','NewOverlayMaterial')
    b.get('shown','OriginalVisible',1500,250);b.fn('visible',SC+'SetVisibility',1500,0);b.link('chair','ChairMesh','visible','self');b.link('shown','OriginalVisible','visible','bNewVisibility')
    visible(b,'shell','ChairShell',1800,0,False);visible(b,'suit','Apparition',2100,0,False)
    b.set('off','bActive',2400,0);b.pin('off','bActive','false')
    b.chain(e,'guard','clear','clearCrumble','clearFinish','restore','visible','shell','suit','off');done(b,'Restore the exact chair overlay and visibility')
    b,e=graph('Reset');b.fn('restore',C+':FinishVision',300,0);b.set('rearm','bPlayed',600,0);b.pin('rearm','bPlayed','false')
    b.chain(e,'restore','rearm');done(b,'Restore and rearm on room reset')

def poll():
    b,e=graph('Poll');b.get('room','Takeover',0,250);b.get('chair','ChairMesh',0,450)
    for ref,var,y in [('roomValid','room',250),('chairValid','chair',450)]:
        b.fn(ref,KS+'IsValid',250,y);b.link(var,'Takeover' if var=='room' else 'ChairMesh',ref,'Object')
    b.fn('both',K+'BooleanAND',500,350);b.link('roomValid','ReturnValue','both','A');b.link('chairValid','ReturnValue','both','B')
    b.node('valid','branch',750,0);b.link('both','ReturnValue','valid','Condition')
    b.get('stage','Stage',750,250,ROOM);b.link('room','Takeover','stage','self')
    b.fn('zero',K+'EqualEqual_IntInt',1000,250,B=0);b.link('stage','Stage','zero','A')
    b.node('reset','branch',1250,0);b.link('zero','ReturnValue','reset','Condition');b.fn('restore',C+':Reset',1500,-180)
    b.fn('late',K+'GreaterEqual_IntInt',1000,500,B=4);b.link('stage','Stage','late','A')
    b.get('seen','bPaintingSeen',1250,650,ROOM);b.link('room','Takeover','seen','self')
    b.get('played','bPlayed',1250,850);b.fn('fresh',K+'Not_PreBool',1500,850);b.link('played','bPlayed','fresh','A')
    b.fn('now',GS+'GetTimeSeconds',700,1100);b.get('seenAt','PaintingSeenAt',700,1300)
    b.fn('recorded',K+'GreaterEqual_DoubleDouble',1000,1300,B=0);b.link('seenAt','PaintingSeenAt','recorded','A')
    b.fn('firstSeen',K+'SelectFloat',1250,1300);b.link('recorded','ReturnValue','firstSeen','bPickA');b.link('seenAt','PaintingSeenAt','firstSeen','A');b.link('now','ReturnValue','firstSeen','B')
    b.fn('observed',K+'SelectFloat',1500,1300,B=-1);b.link('seen','bPaintingSeen','observed','bPickA');b.link('firstSeen','ReturnValue','observed','A')
    b.set('rememberSeen','PaintingSeenAt',1000,0);b.link('observed','ReturnValue','rememberSeen','PaintingSeenAt')
    b.fn('age',K+'Subtract_DoubleDouble',1750,1300);b.link('now','ReturnValue','age','A');b.link('observed','ReturnValue','age','B')
    b.fn('quiet',K+'GreaterEqual_DoubleDouble',2000,1300,B=4.2);b.link('age','ReturnValue','quiet','A')
    b.fn('seenAndQuiet',K+'BooleanAND',1750,850);b.link('seen','bPaintingSeen','seenAndQuiet','A');b.link('quiet','ReturnValue','seenAndQuiet','B')
    b.fn('ready',K+'BooleanAND',1500,500);b.link('late','ReturnValue','ready','A');b.link('seenAndQuiet','ReturnValue','ready','B')
    b.fn('once',K+'BooleanAND',1750,500);b.link('ready','ReturnValue','once','A');b.link('fresh','ReturnValue','once','B')
    b.node('play','branch',2000,180);b.link('once','ReturnValue','play','Condition');b.fn('start',C+':StartVision',2250,180)
    b.chain(e,'valid','rememberSeen','reset','restore');b.link('reset','else','play','execute');b.chain('play','start');done(b,'Wait for the painting scene to finish')
    b=Batch(P,'EventGraph');ns,_=inspect(P,'EventGraph')
    if ns:b.ops.append(dict(op='remove',node_ids=[n['node_id'] for n in ns]))
    b.ops.append(dict(op='add_event',ref='begin',event_name='ReceiveBeginPlay',x=0,y=0));timer(b,'poll','Poll',300,0,.2,True);b.chain('begin','poll')
    b.ops.append(dict(op='add_event',ref='end',event_name='ReceiveEndPlay',x=0,y=450));b.fn('restore',C+':Reset',300,450);b.chain('end','restore')
    done(b,'Observe the room and leave the chair untouched')

if __name__=='__main__':
    assert not call('editor_get_state')['pie_running'],'Wait for PIE'
    lease=h.lease_acquire(h.agent_id(),['asset:'+P],ttl_s=180,wait_s=30)
    try:
        for step in (assets,start,animate,finish,poll):step()
    finally:h.release(h.agent_id(),lease)
