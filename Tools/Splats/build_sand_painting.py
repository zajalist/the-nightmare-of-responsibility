"""Two animated, existing painting canvases and one optional gaze scene on RoomTakeover.
Run after build_room_takeover.py. Originals, frames, camera and input remain untouched.
"""
import sys
sys.path.insert(0,'P:/FoA/Tools/Splats')
from build_room_takeover import P,C,K,KS,SC,AU,call,fresh,done,timer,clear,h,Batch,inspect
PR='/Script/Engine.PrimitiveComponent:'
GS='/Script/Engine.GameplayStatics:'
PCM='/Script/Engine.PlayerCameraManager:'
PLAYER='/Game/FoA/Characters/Player/BP_FoAPlayer.BP_FoAPlayer_C'
INTER='/Game/FoA/Gameplay/BPC_Interactor.BPC_Interactor_C'
M='/Game/FoA/Art/Materials/M_SandPainting'
MI='/Game/FoA/Art/Materials/MI_SandPainting_Lion'
CANVASES=('CanvasHorse','CanvasLion')

def assets():
    info=call('blueprint_get_info',path=P);have={c['name'] for c in info['components']}
    if not h.call('material_get_info',{'path':MI}).get('ok'):
        call('material_create_instance',parent_material_path=M,package_path=MI,name='MI_SandPainting_Lion')
    call('material_set_param',instance_path=MI,param_name='Art',value='/Game/FoA/Art/Textures/T_Art_StubbsLion')
    call('asset_save',asset_paths=[MI])
    parts=[('CanvasHorse','/Game/FoA/Props/fancy_picture_frame_02/fancy_picture_frame_02_1k/StaticMeshes/fancy_picture_frame_02_canvas',M,(-374.55,208,165.6),(0,-90,0),(1,1,1)),
           ('CanvasLion','/Game/FoA/Props/fancy_picture_frame_01/fancy_picture_frame_01_1k/StaticMeshes/fancy_picture_frame_01_canvas',MI,(374.7,-60,168),(2.5,90,0),(1.6,1.6,1.6)),
           ('PaintingLeak','/Game/FoA/VFX/Splats/Meshes/SM_SandTrickle_Clock/SM_SandTrickle_Clock/StaticMeshes/SM_SandTrickle_Clock',
            '/Game/FoA/VFX/Splats/Instances/MI_Sand_ClockDrip',(-372.5,208,140.2),(0,0,0),(.8,.8,1.4))]
    for n,mesh,mat,loc,rot,scale in parts:
        if n not in have:call('blueprint_add_component',path=P,component_class_path='/Script/Engine.StaticMeshComponent',component_name=n)
        call('object_set_property',path=C+':'+n+'_GEN_VARIABLE',properties={'StaticMesh':mesh,'OverrideMaterials':[mat],
            'RelativeLocation':dict(zip(('X','Y','Z'),loc)),'RelativeRotation':dict(zip(('Pitch','Yaw','Roll'),rot)),
            'RelativeScale3D':dict(zip(('X','Y','Z'),scale)),'bVisible':False,'CastShadow':False,'Mobility':'Movable',
            'bGenerateOverlapEvents':False,'BodyInstance':'(CollisionProfileName="NoCollision",CollisionEnabled=NoCollision)'})
    if 'PaintingSound' not in have:call('blueprint_add_component',path=P,component_class_path='/Script/Engine.AudioComponent',component_name='PaintingSound')
    call('object_set_property',path=C+':PaintingSound_GEN_VARIABLE',properties={'Sound':'/Game/FoA/Audio/MetaSounds/Sand/S_Sand_Shift','bAutoActivate':False,'VolumeMultiplier':.45})
    for name,typ,default in [('bPaintingSeen','bool','false'),('LookDwell','float','0')]:
        call('blueprint_add_variable',path=P,variable_name=name,variable_type=typ,default_value=default,category='Painting',update_existing=True)
    for fn in ('UpdatePainting','WatchPainting','InspectPainting','PaintingThought','EndPainting','ResetPainting'):
        if fn not in info['functions']:call('blueprint_add_function',path=P,function_name=fn)
    call('blueprint_compile',path=P);call('asset_save',asset_paths=[P])

def update():
    b,e=fresh('UpdatePainting');b.get('stage','StageProgress',0,300)
    b.fn('alive',K+'Greater_DoubleDouble',250,300,B=.001);b.link('stage','StageProgress','alive','A');prev=e
    for i,n in enumerate(CANVASES):
        x=500+i*650;b.get(n,n,x,300)
        b.fn('set'+n,PR+'SetScalarParameterForCustomPrimitiveData',x,0,ParameterName='PaintingStage');b.link(n,n,'set'+n,'self');b.link('stage','StageProgress','set'+n,'Value')
        b.fn('show'+n,SC+'SetVisibility',x+300,0);b.link(n,n,'show'+n,'self');b.link('alive','ReturnValue','show'+n,'bNewVisibility')
        b.chain(prev,'set'+n,'show'+n);prev='show'+n
    done(b,'The paintings fill slowly')
    b,e=fresh('EndPainting');b.get('leak','PaintingLeak',0,300);b.fn('hide',SC+'SetVisibility',300,0,bNewVisibility='false');b.link('leak','PaintingLeak','hide','self')
    b.get('snd','PaintingSound',300,300);b.fn('stop',AU+'Stop',600,0);b.link('snd','PaintingSound','stop','self');b.chain(e,'hide','stop');done(b,'The frame falls silent')
    b,e=fresh('ResetPainting');clear(b,'thought','PaintingThought',150,0);clear(b,'clear','EndPainting',300,0);b.fn('end',C+':EndPainting',600,0)
    b.set('seen','bPaintingSeen',900,0);b.pin('seen','bPaintingSeen','false');b.set('dwell','LookDwell',1200,0);b.pin('dwell','LookDwell',0);prev='dwell'
    b.chain(e,'thought','clear','end','seen','dwell')
    for i,n in enumerate(CANVASES):
        x=1500+i*400;b.get(n,n,x,250);b.fn('pulse'+n,PR+'SetScalarParameterForCustomPrimitiveData',x,0,ParameterName='PaintingPulse',Value=-100)
        b.link(n,n,'pulse'+n,'self');b.chain(prev,'pulse'+n);prev='pulse'+n
    timer(b,'watch','WatchPainting',2300,0,.2,True);b.chain(prev,'watch');done(b,'Let tomorrow be still')

def scene():
    b,e=fresh('InspectPainting');b.get('seen','bPaintingSeen',0,300);b.node('once','branch',300,0);b.link('seen','bPaintingSeen','once','Condition');b.chain(e,'once')
    b.set('remember','bPaintingSeen',600,0);b.pin('remember','bPaintingSeen','true');b.link('once','else','remember','execute')
    b.fn('now',GS+'GetTimeSeconds',600,300);prev='remember'
    for i,n in enumerate(CANVASES):
        x=900+i*400;b.get(n,n,x,300);b.fn('pulse'+n,PR+'SetScalarParameterForCustomPrimitiveData',x,0,ParameterName='PaintingPulse')
        b.link(n,n,'pulse'+n,'self');b.link('now','ReturnValue','pulse'+n,'Value');b.chain(prev,'pulse'+n);prev='pulse'+n
    b.get('leak','PaintingLeak',1700,300);b.fn('show',SC+'SetVisibility',1700,0,bNewVisibility='true');b.link('leak','PaintingLeak','show','self')
    b.fn('v4',K+'MakeVector4',1900,400,X=1,Z=4,W=0);b.link('now','ReturnValue','v4','Y')
    b.fn('event',PR+'SetVectorParameterForCustomPrimitiveData',2000,0,ParameterName='SandEvent');b.link('leak','PaintingLeak','event','self');b.link('v4','ReturnValue','event','Value')
    b.get('snd','PaintingSound',2300,300);b.fn('play',AU+'Play',2300,0,StartTime=0);b.link('snd','PaintingSound','play','self')
    timer(b,'end','EndPainting',2600,0,4)
    timer(b,'thought','PaintingThought',2900,0,1.2)
    b.chain(prev,'show','event','play','end','thought');done(b,'See the image move first')
    b,e=fresh('PaintingThought')
    b.fn('pawn',GS+'GetPlayerPawn',2600,400,PlayerIndex=0)
    b.fn('inter','/Script/Engine.Actor:GetComponentByClass',2900,400,ComponentClass=INTER);b.link('pawn','ReturnValue','inter','self')
    b.fn('valid',KS+'IsValid',3200,400);b.link('inter','ReturnValue','valid','Object');b.node('speak','branch',3200,0);b.link('valid','ReturnValue','speak','Condition')
    b.fn('text','/Script/Engine.KismetTextLibrary:Conv_StringToText',3500,400,InString='It moved. I saw it move.')
    b.fn('line',INTER+':Narrate',3500,0);b.link('inter','ReturnValue','line','self');b.link('text','ReturnValue','line','Line')
    b.chain(e,'speak','line');done(b,'Only then the thought')

def watch():
    b,e=fresh('WatchPainting');b.get('seen','bPaintingSeen',0,200);b.get('stage','Stage',0,350)
    b.fn('not',K+'Not_PreBool',250,200);b.link('seen','bPaintingSeen','not','A')
    b.fn('ready',K+'GreaterEqual_IntInt',250,350,B=2);b.link('stage','Stage','ready','A')
    b.fn('allow',K+'BooleanAND',500,250);b.link('not','ReturnValue','allow','A');b.link('ready','ReturnValue','allow','B')
    b.node('gate','branch',750,0);b.link('allow','ReturnValue','gate','Condition');b.chain(e,'gate')
    b.fn('pawn',GS+'GetPlayerPawn',750,500,PlayerIndex=0)
    b.node('cast','cast',1000,0,class_path=PLAYER);b.link('pawn','ReturnValue','cast','Object');b.chain('gate','cast')
    b.get('cinematic','bCinematic',1000,650,PLAYER);b.link('cast','AsBP Fo APlayer','cinematic','self')
    b.get('locked','bInteractionLocked',1000,800,PLAYER);b.link('cast','AsBP Fo APlayer','locked','self')
    b.fn('busy',K+'BooleanOR',1300,700);b.link('cinematic','bCinematic','busy','A');b.link('locked','bInteractionLocked','busy','B')
    b.fn('free',K+'Not_PreBool',1550,700);b.link('busy','ReturnValue','free','A')
    b.fn('pc',GS+'GetPlayerController',1000,1000,PlayerIndex=0);b.fn('view','/Script/Engine.PlayerController:GetViewTarget',1300,1000);b.link('pc','ReturnValue','view','self')
    b.fn('own',K+'EqualEqual_ObjectObject',1550,1000);b.link('view','ReturnValue','own','A');b.link('pawn','ReturnValue','own','B')
    b.fn('cam',GS+'GetPlayerCameraManager',1000,1300,PlayerIndex=0)
    b.fn('loc',PCM+'GetCameraLocation',1300,1250);b.link('cam','ReturnValue','loc','self')
    b.fn('rot',PCM+'GetCameraRotation',1300,1400);b.link('cam','ReturnValue','rot','self')
    b.fn('fwd',K+'GetForwardVector',1550,1400);b.link('rot','ReturnValue','fwd','InRot')
    b.fn('delta',K+'Subtract_VectorVector',1550,1200,A='-373.6,208,165.2');b.link('loc','ReturnValue','delta','B')
    b.fn('normal',K+'Normal',1800,1200);b.link('delta','ReturnValue','normal','A')
    b.fn('dot',K+'Dot_VectorVector',2050,1250);b.link('normal','ReturnValue','dot','A');b.link('fwd','ReturnValue','dot','B')
    b.fn('facing',K+'Greater_DoubleDouble',2300,1250,B=.995);b.link('dot','ReturnValue','facing','A')
    b.fn('dist',K+'VSize',1800,1550);b.link('delta','ReturnValue','dist','A')
    b.fn('near',K+'Less_DoubleDouble',2050,1550,B=240);b.link('dist','ReturnValue','near','A')
    prev=('free','ReturnValue')
    for i,pair in enumerate([('own','ReturnValue'),('facing','ReturnValue'),('near','ReturnValue')]):
        r='and'+str(i);b.fn(r,K+'BooleanAND',2500+i*250,750);b.link(*prev,r,'A');b.link(*pair,r,'B');prev=(r,'ReturnValue')
    b.node('looking','branch',3300,0);b.link(*prev,'looking','Condition');b.chain('cast','looking')
    b.get('dwell','LookDwell',3300,300);b.fn('plus',K+'Add_DoubleDouble',3550,300,B=.2);b.link('dwell','LookDwell','plus','A')
    b.set('save','LookDwell',3550,0);b.link('plus','ReturnValue','save','LookDwell')
    b.fn('enough',K+'GreaterEqual_DoubleDouble',3800,300,B=.8);b.link('save','Output_Get','enough','A')
    b.node('hold','branch',4050,0);b.link('enough','ReturnValue','hold','Condition');b.fn('inspect',C+':InspectPainting',4350,0)
    b.chain('looking','save','hold','inspect')
    b.set('zero','LookDwell',3550,-350);b.pin('zero','LookDwell',0);b.link('looking','else','zero','execute');b.link('gate','else','zero','execute')
    done(b,'Hold your gaze briefly')

def append(graph,function,title):
    ns,es=inspect(P,graph)
    if any(n['title']==function for n in ns):return
    outgoing={e['from_node'] for e in es if e['from_pin']=='then'}
    incoming={e['to_node'] for e in es if e['to_pin']=='execute'}
    ends=[n for n in ns if n['node_id'] in incoming and n['node_id'] not in outgoing]
    assert len(ends)==1,(graph,ends)
    b=Batch(P,graph);b.fn('painting',C+':'+function,2000,2000);b.chain(ends[0]['node_id'],'painting');b.comment(title,['painting']);b.run()

if __name__=='__main__':
    assert not call('editor_get_state')['pie_running']
    lease=h.lease_acquire(h.agent_id(),['asset:'+P,'asset:'+MI],ttl_s=180,wait_s=30)
    try:
        assets();update();scene();watch()
        append('ApplyStage','UpdatePainting','Sand inside the frames')
        append('Reset','ResetPainting','Reset the painting scene')
    finally:h.release(h.agent_id(),lease)
