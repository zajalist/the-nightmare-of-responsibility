"""Persistent, staged room takeover. Native Hayba only; no runtime Python or Tick.
Run with HAYBA_AGENT_ID=room-takeover, after user PIE ends. --selftest is offline.
"""
import math
import sys
sys.path.insert(0, 'P:/FoA/Tools/Unreal')
sys.path.insert(0, 'P:/FoA/Tools/Unreal/player')
import hayba_call as h
from held_tool_graphs import Batch, inspect, find

P = '/Game/FoA/Gameplay/Ambient/BP_RoomTakeover'
C = P + '.BP_RoomTakeover_C'
K = '/Script/Engine.KismetMathLibrary:'
KS = '/Script/Engine.KismetSystemLibrary:'
SC = '/Script/Engine.SceneComponent:'
AU = '/Script/Engine.AudioComponent:'
SPILL = '/Game/FoA/VFX/Sand/Spill/SM_SandSpill_{0}/SM_SandSpill_{0}/StaticMeshes/SM_SandSpill_{0}'
MOUND = '/Game/FoA/Procedural/SM_SandMound_A/SM_SandMound_A/StaticMeshes/SM_SandMound_A'
SUIT = '/Game/FoA/VFX/Splats/Meshes/SM_SandSuit/SM_SandSuit/StaticMeshes/SM_SandSuit'
# name, first stage, mesh, position, pitch/yaw/roll, first-stage full scale.
# Deposits remain at room edges; the eastern door approach (y40..135) stays clear.
PARTS = [
    ('WardrobeSpill', 1, SPILL.format('Pour'), (290,265,.3), (0,25,0), (1.1,.7,2)),
    ('WardrobeBank', 1, MOUND, (325,260,0), (0,-20,0), (.65,.7,.8)),
    ('BaySpill', 2, SPILL.format('Bay'), (-60,-350,.4), (0,0,0), (.9,.7,3)),
    ('BayBank', 2, MOUND, (-125,-340,0), (0,20,0), (.7,.65,1.15)),
    ('DeskSpill', 3, SPILL.format('Pour'), (-335,170,.5), (0,-70,0), (1.25,.65,3)),
    ('DeskBank', 3, MOUND, (-348,215,0), (0,0,0), (.55,1.1,1.8)),
    ('WardrobeClimb', 3, SPILL.format('Hearth'), (373,255,42), (0,90,90), (.65,.6,3)),
    ('SouthWestSpill', 4, SPILL.format('Hearth'), (-320,-220,.6), (0,-20,0), (.8,.65,4)),
    ('SouthWestBank', 4, MOUND, (-350,-250,0), (0,20,0), (.65,.8,2)),
    ('SouthEastSpill', 5, SPILL.format('Hearth'), (325,-230,.7), (0,20,0), (.7,.8,4)),
    ('SouthEastBank', 5, MOUND, (350,-260,0), (0,0,0), (.65,.7,2.4)),
    ('SouthWallClimb', 5, SPILL.format('Hearth'), (285,-296,55), (0,0,90), (.85,.85,4)),
]
SIGS = {
    'SetStage': [('NewStage','int')], 'Reset': [], 'Grow': [], 'ApplyStage': [],
    'ApplyDeposit': [('Part','object:/Script/Engine.StaticMeshComponent'),('FirstStage','float'),('Size','vector')],
    'PlayScare': [], 'EndScare': [],
}

def call(cmd, **p):
    r = h.call(cmd,p); assert r.get('ok'),r
    d = r.get('data',{}); assert d.get('ok',True),d
    assert not d.get('failed'),d
    return d

def fresh(name):
    ns,_=inspect(P,name); e=find(ns,name); b=Batch(P,name)
    old=[n['node_id'] for n in ns if n['node_id']!=e]
    if old:b.ops.append(dict(op='remove',node_ids=old))
    return b,e

def done(b,title):
    b.comment(title,[o['ref'] for o in b.ops if o.get('op')=='add_node']); b.run()

def timer(b,ref,fn,x,y,t,loop=False):
    return b.fn(ref,KS+'K2_SetTimer',x,y,FunctionName=fn,Time=t,bLooping=str(loop).lower())

def clear(b,ref,fn,x,y):
    return b.fn(ref,KS+'K2_ClearTimer',x,y,FunctionName=fn)

def assets():
    info=h.call('blueprint_get_info',{'path':P})
    if not info.get('ok'):call('blueprint_create',name='BP_RoomTakeover',package_path=P,parent_class_path='/Script/Engine.Actor')
    info=call('blueprint_get_info',path=P)
    have={x['name'] for x in info['components']}
    if 'Root' not in have:call('blueprint_add_component',path=P,component_class_path='/Script/Engine.SceneComponent',component_name='Root')
    for name,stage,mesh,loc,rot,scale in PARTS + [('ScareSuit',0,SUIT,(100,240,0),(0,0,0),(1,1,1))]:
        if name not in have:call('blueprint_add_component',path=P,component_class_path='/Script/Engine.StaticMeshComponent',component_name=name)
        mat=('/Game/FoA/VFX/Splats/Instances/MI_Sand_Suit' if name=='ScareSuit' else
             '/Game/FoA/VFX/Sand/MI_SandSpill_Mound' if mesh==MOUND else '/Game/FoA/VFX/Sand/MI_SandSpill_Floor')
        call('object_set_property',path=C+':'+name+'_GEN_VARIABLE',properties={
            'StaticMesh':mesh,'OverrideMaterials':[mat], 'RelativeLocation':dict(zip(('X','Y','Z'),loc)),
            'RelativeRotation':dict(zip(('Pitch','Yaw','Roll'),rot)), 'RelativeScale3D':{'X':1,'Y':1,'Z':1},
            'bVisible':False,'CastShadow':False,'bGenerateOverlapEvents':False,'Mobility':'Movable',
            'bRenderCustomDepth':True,'CustomDepthStencilValue':5,
            'BodyInstance':'(CollisionProfileName="NoCollision",CollisionEnabled=NoCollision)'})
    for name,sound,vol in [('SandRise','/Game/FoA/Audio/MetaSounds/Sand/S_Sand_Pour',.38),
                           ('ScareImpact','/Game/FoA/Audio/SFX/Dream/SFX_Dream_LowImpact_01',.6)]:
        if name not in have:call('blueprint_add_component',path=P,component_class_path='/Script/Engine.AudioComponent',component_name=name)
        call('object_set_property',path=C+':'+name+'_GEN_VARIABLE',properties={'Sound':sound,'bAutoActivate':False,'VolumeMultiplier':vol})
    for n,t,v in [('Stage','int','0'),('StageProgress','float','0'),('GrowthFrom','float','0'),('GrowthAlpha','float','0'),('ScarePlays','int','0')]:
        call('blueprint_add_variable',path=P,variable_name=n,variable_type=t,default_value=v,category='Takeover',update_existing=True)
    for n,inputs in SIGS.items():
        if n not in info['functions']:call('blueprint_add_function',path=P,function_name=n,inputs=[{'name':k,'type':t} for k,t in inputs])
    call('blueprint_compile',path=P);call('asset_save',asset_paths=[P])

def deposit():
    b,e=fresh('ApplyDeposit')
    b.get('p','StageProgress',0,300)
    b.fn('offset',K+'Subtract_DoubleDouble',250,300);b.link('p','StageProgress','offset','A');b.link(e,'FirstStage','offset','B')
    b.fn('age',K+'FClamp',500,450,Min=0,Max=4);b.link('offset','ReturnValue','age','Value')
    b.fn('plus',K+'Add_DoubleDouble',500,250,B=1);b.link('offset','ReturnValue','plus','A')
    b.fn('clamp',K+'FClamp',750,250,Min=0,Max=1);b.link('plus','ReturnValue','clamp','Value')
    b.fn('ease',K+'FInterpEaseInOut',1000,250,A=0,B=1,Exponent=2);b.link('clamp','ReturnValue','ease','Alpha')
    for ref,factor,y in [('wide',.1,450),('high',.4,650)]:
        b.fn(ref+'mul',K+'Multiply_DoubleDouble',750,y,B=factor);b.link('age','ReturnValue',ref+'mul','A')
        b.fn(ref+'add',K+'Add_DoubleDouble',1000,y,B=1);b.link(ref+'mul','ReturnValue',ref+'add','A')
        b.fn(ref,K+'Multiply_DoubleDouble',1250,y);b.link(ref+'add','ReturnValue',ref,'A');b.link('ease','ReturnValue',ref,'B')
    b.fn('split',K+'BreakVector',1250,850);b.link(e,'Size','split','InVec')
    b.fn('vec',K+'MakeVector',1800,450)
    for j,axis in enumerate('XYZ'):
        ref='size'+axis;b.fn(ref,K+'Multiply_DoubleDouble',1550,350+j*180)
        b.link('split',axis,ref,'A');b.link('high' if axis=='Z' else 'wide','ReturnValue',ref,'B');b.link(ref,'ReturnValue','vec',axis)
    b.fn('scale',SC+'SetRelativeScale3D',2050,0);b.link(e,'Part','scale','self');b.link('vec','ReturnValue','scale','NewScale3D')
    b.fn('visible',K+'Greater_DoubleDouble',2050,300,B=.001);b.link('clamp','ReturnValue','visible','A')
    b.fn('show',SC+'SetVisibility',2350,0);b.link(e,'Part','show','self');b.link('visible','ReturnValue','show','bNewVisibility')
    b.chain(e,'scale','show');done(b,'Grow each deposit')
    b,e=fresh('ApplyStage');prev=e
    for i,(name,stage,mesh,loc,rot,size) in enumerate(PARTS):
        x=300+(i%4)*400;y=(i//4)*550
        b.get(name,name,x,y+200);b.fn('apply'+str(i),C+':ApplyDeposit',x,y,FirstStage=stage,Size=','.join(map(str,size)))
        b.link(name,name,'apply'+str(i),'Part');b.chain(prev,'apply'+str(i));prev='apply'+str(i)
    done(b,'Spread along room edges')

def growth():
    b,e=fresh('Grow');b.get('alpha','GrowthAlpha',0,300)
    b.fn('add',K+'Add_DoubleDouble',250,300,B=1/60);b.link('alpha','GrowthAlpha','add','A')
    b.fn('clamp',K+'FClamp',500,300,Min=0,Max=1);b.link('add','ReturnValue','clamp','Value')
    b.set('saveAlpha','GrowthAlpha',750,0);b.link('clamp','ReturnValue','saveAlpha','GrowthAlpha')
    b.fn('ease',K+'FInterpEaseInOut',750,300,A=0,B=1,Exponent=2);b.link('saveAlpha','Output_Get','ease','Alpha')
    b.get('from','GrowthFrom',750,550);b.get('stage','Stage',750,700)
    b.fn('float',K+'Conv_IntToDouble',1000,700);b.link('stage','Stage','float','InInt')
    b.fn('lerp',K+'Lerp',1250,350);b.link('from','GrowthFrom','lerp','A');b.link('float','ReturnValue','lerp','B');b.link('ease','ReturnValue','lerp','Alpha')
    b.set('progress','StageProgress',1250,0);b.link('lerp','ReturnValue','progress','StageProgress')
    b.fn('apply',C+':ApplyStage',1550,0);b.fn('full',K+'GreaterEqual_DoubleDouble',1550,300,B=1);b.link('saveAlpha','Output_Get','full','A')
    b.node('stop','branch',1850,0);b.link('full','ReturnValue','stop','Condition');clear(b,'clear','Grow',2150,0)
    b.get('sound','SandRise',2150,300);b.fn('quiet',AU+'Stop',2450,0);b.link('sound','SandRise','quiet','self')
    b.chain(e,'saveAlpha','progress','apply','stop','clear','quiet');done(b,'Three second encroachment')

def scares():
    b,e=fresh('EndScare');b.get('suit','ScareSuit',0,200);b.fn('hide',SC+'SetVisibility',300,0,bNewVisibility='false');b.link('suit','ScareSuit','hide','self')
    b.get('sound','ScareImpact',300,300);b.fn('stop',AU+'Stop',600,0);b.link('sound','ScareImpact','stop','self');b.chain(e,'hide','stop');done(b,'Release the apparition')
    b,e=fresh('PlayScare');b.get('stage','Stage',0,300)
    b.fn('two',K+'EqualEqual_IntInt',250,300,B=2);b.link('stage','Stage','two','A')
    b.fn('four',K+'EqualEqual_IntInt',250,450,B=4);b.link('stage','Stage','four','A')
    b.fn('either',K+'BooleanOR',500,300);b.link('two','ReturnValue','either','A');b.link('four','ReturnValue','either','B')
    b.node('guard','branch',750,0);b.link('either','ReturnValue','guard','Condition')
    b.fn('site',K+'SelectVector',750,300,A='120,235,0',B='-75,-305,0');b.link('two','ReturnValue','site','bPickA')
    b.get('suit','ScareSuit',1000,500);b.fn('move',SC+'K2_SetRelativeLocation',1000,0);b.link('suit','ScareSuit','move','self');b.link('site','ReturnValue','move','NewLocation')
    b.fn('show',SC+'SetVisibility',1300,0,bNewVisibility='true');b.link('suit','ScareSuit','show','self')
    b.fn('now','/Script/Engine.GameplayStatics:GetTimeSeconds',1300,500)
    b.fn('v4',K+'MakeVector4',1550,400,X=1,Y=0,Z=.12,W=0);b.link('now','ReturnValue','v4','Y')
    b.fn('event','/Script/Engine.PrimitiveComponent:SetVectorParameterForCustomPrimitiveData',1600,0,ParameterName='SandEvent');b.link('suit','ScareSuit','event','self');b.link('v4','ReturnValue','event','Value')
    b.get('sound','ScareImpact',1900,300);b.fn('play',AU+'Play',1900,0,StartTime=0);b.link('sound','ScareImpact','play','self')
    b.get('count','ScarePlays',1900,500);b.fn('inc',K+'Add_IntInt',2150,500,B=1);b.link('count','ScarePlays','inc','A')
    b.set('save','ScarePlays',2200,0);b.link('inc','ReturnValue','save','ScarePlays')
    timer(b,'end','EndScare',2500,0,.75)
    b.chain(e,'guard','move','show','event','play','save','end');done(b,'A brief clothed silhouette')

def api():
    b,e=fresh('Reset');prev=e
    for i,n in enumerate(('Grow','PlayScare','EndScare')):clear(b,'clear'+str(i),n,300+i*300,0);b.chain(prev,'clear'+str(i));prev='clear'+str(i)
    for i,n in enumerate(('Stage','StageProgress','GrowthFrom','GrowthAlpha','ScarePlays')):
        r='reset'+n;b.set(r,n,1200+i*300,0);b.pin(r,n,0);b.chain(prev,r);prev=r
    b.fn('apply',C+':ApplyStage',2700,0);b.fn('end',C+':EndScare',3000,0)
    b.get('sound','SandRise',3000,300);b.fn('stop',AU+'Stop',3300,0);b.link('sound','SandRise','stop','self')
    b.chain(prev,'apply','end','stop');done(b,'Restore a clean room')
    b,e=fresh('SetStage');b.fn('clamp',K+'Clamp',0,300,Min=0,Max=5);b.link(e,'NewStage','clamp','Value')
    b.get('stage','Stage',0,500);b.fn('new',K+'Greater_IntInt',300,300);b.link('clamp','ReturnValue','new','A');b.link('stage','Stage','new','B')
    b.node('advance','branch',600,0);b.link('new','ReturnValue','advance','Condition')
    clear(b,'clear','PlayScare',900,0);clear(b,'clearEnd','EndScare',1200,0);b.fn('end',C+':EndScare',1500,0)
    b.set('save','Stage',1800,0);b.link('clamp','ReturnValue','save','Stage')
    b.get('p','StageProgress',1800,300);b.set('from','GrowthFrom',2100,0);b.link('p','StageProgress','from','GrowthFrom')
    b.set('alpha','GrowthAlpha',2400,0);b.pin('alpha','GrowthAlpha',0)
    timer(b,'grow','Grow',2700,0,.05,True)
    b.get('sound','SandRise',2700,300);b.fn('play',AU+'Play',3000,0,StartTime=0);b.link('sound','SandRise','play','self')
    b.fn('two',K+'EqualEqual_IntInt',3000,400,B=2);b.link('save','Output_Get','two','A')
    b.fn('four',K+'EqualEqual_IntInt',3000,600,B=4);b.link('save','Output_Get','four','A')
    b.fn('either',K+'BooleanOR',3300,400);b.link('two','ReturnValue','either','A');b.pin('either','B','false')
    b.node('scare','branch',3500,0);b.link('either','ReturnValue','scare','Condition');timer(b,'wait','PlayScare',3800,0,1.4)
    b.chain(e,'advance','clear','clearEnd','end','save','from','alpha','grow','play','scare','wait');done(b,'Advance once per discovery')
    b=Batch(P,'EventGraph');ns,_=inspect(P,'EventGraph')
    if ns:b.ops.append(dict(op='remove',node_ids=[n['node_id'] for n in ns]))
    b.ops.append(dict(op='add_event',ref='begin',event_name='ReceiveBeginPlay',x=0,y=0));b.fn('reset',C+':Reset',300,0);b.chain('begin','reset');done(b,'Start with clear edges')

def selftest():
    assert len({p[0] for p in PARTS})==len(PARTS)
    assert {p[1] for p in PARTS}==set(range(1,6))
    for n,s,m,l,r,z in PARTS:
        assert not (l[0]>200 and 40<=l[1]<=135),n
        assert all(v>0 for v in z)
    # Exact math used by ApplyDeposit: no pre-stage visibility, monotone growth, heavier late stages.
    for first in range(1,6):
        old=(0,0)
        for step in range(301):
            p=step/60; a=max(0,min(1,p-first+1)); ease=2*a*a if a<.5 else 1-2*(1-a)**2
            age=max(0,min(4,p-first)); scales=(ease*(1+.1*age),ease*(1+.4*age))
            assert scales[0]>=old[0]-1e-9 and scales[1]>=old[1]-1e-9
            if p<=first-1:assert scales==(0,0)
            old=scales
    assert math.isclose(60*.05,3)
    print('room takeover selftest ok: five stages, clear exit, monotonic persistent growth')

if __name__=='__main__':
    if '--selftest' in sys.argv:selftest()
    else:
        assert not call('editor_get_state')['pie_running'],'Do not edit during user PIE'
        lease=h.lease_acquire(h.agent_id(),['asset:'+P],ttl_s=180,wait_s=30)
        try:
            for f in (assets,deposit,growth,scares,api):f()
        finally:h.release(h.agent_id(),lease)
