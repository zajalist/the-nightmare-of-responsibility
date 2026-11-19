"""Contact-driven shirt chase. Scoped Director graphs; no furniture or Player rebuild.

Prepare freely offline. Apply only in the coordinator's non-PIE asset window.
The table patch is a separate final commit after every graph compiles.
"""
import os,sys
sys.path.insert(0,'P:/FoA/Tools/Unreal')
sys.path.insert(0,'P:/FoA/Tools/Unreal/player')
from build_clothing_search import P,C,ROOM,BASE,INTER,INVENTORY,K,GS,KS,A,call,fresh,finish,build_handler,STEPS
from build_clothing_inspection import SC,PC,CTRL,PLAYER,timer,clear
from clothing_chase_contract import LANDINGS,EXTRACT_CLEAR,SNAG,PULL_DISTANCE,VASE_VIEW,VASE_FOCUS,BOSS_VIEW,BOSS_FOCUS,VASE_VIEW_EAST,BOSS_VIEW_EAST,SIDE_SPLIT_X
from held_tool_graphs import Batch,inspect,find
import hayba_call as h

FUNCS=['BeginClothingToss','EscapeClothingOne','EscapeClothingTwo','ReachClothingVase',
       'OnClothingCameraReady','TickClothingFlight','FinishClothingChaseShot',
       'AbortClothingChase','PlaceClothingLanding','ClothingBossFormed','FrameClothingBoss',
       'StartClothingHanger','UpdateClothingHanger','ClearClothingHanger']

def get_room(b,x=0):
    b.fn('room',GS+'GetActorOfClass',x,1000,ActorClass=ROOM)

def vector(v):return ','.join(map(str,v))

def state(b,ref,value,x=0):
    b.fn(ref,BASE+':SetState',x,0,NewState=value,bInstant='true');b.link('shirt','SearchShirt',ref,'self')

def stage_guard(b,e,stage):
    b.get('stage','ClothingSearchStage',0,300)
    b.fn('correct',K+'EqualEqual_IntInt',300,300,B=stage);b.link('stage','ClothingSearchStage','correct','A')
    b.node('guard','branch',300,0);b.link('correct','ReturnValue','guard','Condition');b.chain(e,'guard')
    return 'guard'

def marker(b,which,part,ref,x):
    name='Clue'+part+which;b.get(ref,name,x,1400,ROOM);b.link('room','ReturnValue',ref,'self')
    b.fn(ref+'pos',SC+'K2_GetComponentLocation',x+250,1400);b.link(ref,name,ref+'pos','self')
    return ref+'pos'

def side_camera(b,east,west,x):
    """viewpos: the east or west in-bay camera, on the same side as the player (he stays outside the view)."""
    b.fn('sidepawn',GS+'GetPlayerPawn',x,1700,PlayerIndex=0)
    b.fn('sideat',A+'K2_GetActorLocation',x+150,1700);b.link('sidepawn','ReturnValue','sideat','self')
    b.fn('sidex',K+'BreakVector',x+300,1700);b.link('sideat','ReturnValue','sidex','InVec')
    b.fn('eastside',K+'Greater_DoubleDouble',x+450,1700,B=SIDE_SPLIT_X);b.link('sidex','X','eastside','A')
    b.fn('east',K+'MakeVector',x+450,1500,**dict(zip('XYZ',east)))
    b.fn('west',K+'MakeVector',x+450,1350,**dict(zip('XYZ',west)))
    b.fn('viewpos',K+'SelectVector',x+600,1400);b.link('east','ReturnValue','viewpos','A');b.link('west','ReturnValue','viewpos','B')
    b.link('eastside','ReturnValue','viewpos','bPickA')

def write_queue(name,required,stage,mode):
    b,e=fresh(name);guard=stage_guard(b,e,required)
    b.get('shirt','SearchShirt',0,800)
    b.fn('cancel',C+':CancelClothingInspection',600,0);b.chain(guard,'cancel')
    get_room(b,900);b.chain('cancel','room')
    b.set('stageout','ClothingSearchStage',1200,0);b.pin('stageout','ClothingSearchStage',stage)
    b.set('active','bClothingChaseActive',1500,0);b.pin('active','bClothingChaseActive','true')
    b.set('mode','ClothingChaseMode',1800,0);b.pin('mode','ClothingChaseMode',mode)
    b.set('flightduration','ClothingFlightDuration',1950,0);b.pin('flightduration','ClothingFlightDuration',{1:2.65,2:.95,3:.95,4:0}[mode])
    b.chain('room','stageout','active','mode','flightduration')
    b.fn('from',A+'GetTransform',1200,600);b.link('shirt','SearchShirt','from','self')
    start='from'
    if mode==1:
        # Match the already visible under-bed shirt mesh exactly before hiding its duplicate.
        b.get('visual','Mesh',1500,700,BASE);b.link('shirt','SearchShirt','visual','self')
        b.fn('relative',SC+'GetRelativeTransform',1800,700);b.link('visual','Mesh','relative','self')
        b.fn('inverse',K+'InvertTransform',2100,700);b.link('relative','ReturnValue','inverse','T')
        b.get('snag','ClueSnaggedShirt',1500,1000,ROOM);b.link('room','ReturnValue','snag','self')
        b.fn('snagworld',SC+'K2_GetComponentToWorld',1800,1000);b.link('snag','ClueSnaggedShirt','snagworld','self')
        b.fn('start',K+'ComposeTransforms',2400,700);b.link('inverse','ReturnValue','start','A');b.link('snagworld','ReturnValue','start','B');start='start'
    b.set('savefrom','ClothingFlightFrom',2100,0);b.link(start,'ReturnValue','savefrom','ClothingFlightFrom')
    b.get('home','ClothingShirtHome',2400,1000);b.fn('homeparts',K+'BreakTransform',2700,1000);b.link('home','ClothingShirtHome','homeparts','InTransform')
    b.fn('goal',K+'MakeTransform',3000,700,Location=vector(LANDINGS[stage-5 if stage<=7 else 2]))
    b.link('homeparts','Rotation','goal','Rotation');b.link('homeparts','Scale','goal','Scale')
    b.set('saveto','ClothingFlightTo',2400,0);b.link('goal','ReturnValue','saveto','ClothingFlightTo')
    b.fn('place',A+'K2_SetActorTransform',2700,0,bSweep='false',bTeleport='true');b.link('shirt','SearchShirt','place','self');b.link(start,'ReturnValue','place','NewTransform')
    state(b,'moving','ChaseMoving',3000)
    b.fn('collision',A+'SetActorEnableCollision',3300,0,bNewActorEnableCollision='false');b.link('shirt','SearchShirt','collision','self')
    b.fn('roomstage',ROOM+':SetStage',3600,0,NewStage=5);b.link('room','ReturnValue','roomstage','self')
    b.chain('flightduration','savefrom','saveto','place','moving','collision','roomstage')
    if mode==1:
        focus=marker(b,'Bed','Focus','focusmarker',3600)
        # Verified reverse view under the bed: the cloth and wire precede the
        # kneeling body, with the real rail visible above the hand.
        b.fn('extractview',K+'Add_VectorVector',3900,1600,B='0,-55,-1');b.link(focus,'ReturnValue','extractview','A')
        b.fn('extractfocus',K+'Add_VectorVector',4200,1600,B='8,20,5');b.link(focus,'ReturnValue','extractfocus','A')
        view,focus='extractview','extractfocus'
    elif mode==4:
        # In the bay, inside the closed curtain: the room's ClueViewVase marker looked at the sill through the curtain
        # (main's decision (b), 2026-11-09). Explicit view and focus from clothing_chase_contract.
        # QA B2 audit (2026-11-10): the camera stands on HIS side of the bay (east when he reaches from x > -90, else
        # west) and looks across at the sill, so his body stays outside the view wherever he reached from.
        side_camera(b,VASE_VIEW_EAST,VASE_VIEW,3000)
        b.fn('focuspos',K+'MakeVector',3600,1400,**dict(zip('XYZ',VASE_FOCUS)))
        view,focus='viewpos','focuspos'
    elif mode==3:
        # escape two lands in the bay: look in through the curtains' moonlit gap from the room side, 2 m out (the shirt
        # reads at under a fifth of the frame); he caught it at the first-landing side, behind this camera
        b.fn('viewpos',K+'MakeVector',3300,1400,X=-50,Y=-130,Z=150)
        b.fn('focuspos',K+'MakeVector',3600,1400,X=LANDINGS[2][0],Y=LANDINGS[2][1],Z=55)
        view,focus='viewpos','focuspos'
    else:
        # escape one (QA B2 readability, 2026-11-10): high over the landing (2.45 m, under the 2.8 m ceiling), 0.3 of his
        # distance back toward him (at most 0.8 m) and 0.2 m to the side nearer the room's middle, looking down at it with
        # the escapes' 55 deg lens. Every sampled catch spot at the first landing stays outside the view cone (the closest
        # by 3 deg); the shirt drops in from the frame edge at 1.45 m or more and lands mid-frame on the moonlit floor.
        land=LANDINGS[stage-5]
        b.fn('chasepawn',GS+'GetPlayerPawn',3000,1600,PlayerIndex=0)
        b.fn('chaseat',A+'K2_GetActorLocation',3150,1600);b.link('chasepawn','ReturnValue','chaseat','self')
        b.fn('landpos',K+'MakeVector',3150,1800,X=land[0],Y=land[1],Z=land[2])
        b.fn('toward',K+'Subtract_VectorVector',3300,1600);b.link('landpos','ReturnValue','toward','A');b.link('chaseat','ReturnValue','toward','B')
        b.fn('flat',K+'Multiply_VectorVector',3450,1600,B='1,1,0');b.link('toward','ReturnValue','flat','A')
        b.fn('dir',K+'Normal',3600,1600);b.link('flat','ReturnValue','dir','A')
        b.fn('dist',K+'VSizeXY',3600,1400);b.link('toward','ReturnValue','dist','A')
        b.fn('part',K+'Multiply_DoubleDouble',3750,1400,B=-0.3);b.link('dist','ReturnValue','part','A')
        b.fn('backlen',K+'FMax',3900,1400,B=-80.0);b.link('part','ReturnValue','backlen','A')
        b.fn('back',K+'Multiply_VectorFloat',3750,1600);b.link('dir','ReturnValue','back','A');b.link('backlen','ReturnValue','back','B')
        b.fn('dirxy',K+'BreakVector',3750,1800);b.link('dir','ReturnValue','dirxy','InVec')
        b.fn('negy',K+'Multiply_DoubleDouble',3900,1800,B=-1.0);b.link('dirxy','Y','negy','A')
        b.fn('perp',K+'MakeVector',4050,1800,Z=0.0);b.link('negy','ReturnValue','perp','X');b.link('dirxy','X','perp','Y')
        b.fn('side',K+'Multiply_VectorFloat',4200,1800,B=20.0);b.link('perp','ReturnValue','side','A')
        b.fn('base',K+'Add_VectorVector',3900,1600,B='0,0,206.5');b.link('landpos','ReturnValue','base','A')
        b.fn('behind',K+'Add_VectorVector',4050,1600);b.link('base','ReturnValue','behind','A');b.link('back','ReturnValue','behind','B')
        b.fn('left',K+'Add_VectorVector',4350,1600);b.link('behind','ReturnValue','left','A');b.link('side','ReturnValue','left','B')
        b.fn('right',K+'Subtract_VectorVector',4350,1800);b.link('behind','ReturnValue','right','A');b.link('side','ReturnValue','right','B')
        b.fn('middle',K+'MakeVector',4350,2000,X=55.0,Y=-35.0,Z=200.0)
        b.fn('dl',K+'Vector_Distance',4500,1700);b.link('left','ReturnValue','dl','V1');b.link('middle','ReturnValue','dl','V2')
        b.fn('dr',K+'Vector_Distance',4500,1900);b.link('right','ReturnValue','dr','V1');b.link('middle','ReturnValue','dr','V2')
        b.fn('leftin',K+'Less_DoubleDouble',4650,1800);b.link('dl','ReturnValue','leftin','A');b.link('dr','ReturnValue','leftin','B')
        b.fn('viewpos',K+'SelectVector',4800,1600);b.link('left','ReturnValue','viewpos','A');b.link('right','ReturnValue','viewpos','B');b.link('leftin','ReturnValue','viewpos','bPickA')
        b.fn('focuspos',K+'Add_VectorVector',4800,1800,B='0,0,10');b.link('landpos','ReturnValue','focuspos','A')
        view,focus='viewpos','focuspos'
    b.set('view','ClothingInspectionView',3900,0);b.link(view,'ReturnValue','view','ClothingInspectionView')
    b.set('focus','ClothingInspectionFocus',4200,0);b.link(focus,'ReturnValue','focus','ClothingInspectionFocus')
    b.set('duration','ClothingInspectionDuration',4500,0);b.pin('duration','ClothingInspectionDuration',{1:3.25,2:1.35,3:1.35,4:4.5}[mode])
    b.set('allow','bClothingContactShot',4800,0);b.pin('allow','bClothingContactShot','true')
    b.set('attempts','ClothingInspectionAttempts',5100,0);b.pin('attempts','ClothingInspectionAttempts',0)
    b.set('line','ClothingInspectionLine',5400,0)
    timer(b,'wait','TryClothingInspection',.1,True,5700)
    b.fn('now',C+':TryClothingInspection',6000,0)
    b.chain('roomstage','view','focus','duration','allow','attempts','line','wait','now')
    finish(b,'Real contact starts this chase beat')

def build_motion():
    b,e=fresh('OnClothingCameraReady');b.get('active','bClothingChaseActive',0,300)
    b.node('owned','branch',300,0);b.link('active','bClothingChaseActive','owned','Condition');b.chain(e,'owned')
    b.get('mode','ClothingChaseMode',300,400);b.fn('final',K+'EqualEqual_IntInt',600,400,B=4);b.link('mode','ClothingChaseMode','final','A')
    b.node('which','branch',600,0);b.link('final','ReturnValue','which','Condition');b.chain('owned','which')
    get_room(b,900);b.chain('which','room')
    b.fn('break',ROOM+':BreakVaseThenBoss',1200,0);b.link('room','ReturnValue','break','self')
    timer(b,'wide','FrameClothingBoss',.9,False,1500);b.chain('room','break','wide')
    b.fn('time',GS+'GetTimeSeconds',900,700)
    b.set('start','ClothingFlightStarted',900,-400);b.link('time','ReturnValue','start','ClothingFlightStarted')
    b.set('flight','bClothingFlight',1200,-400);b.pin('flight','bClothingFlight','true')
    b.link('which','else','start','execute');b.chain('start','flight')
    b.fn('toss',K+'EqualEqual_IntInt',1500,700,B=1);b.link('mode','ClothingChaseMode','toss','A')
    b.node('hanger','branch',1500,-400);b.link('toss','ReturnValue','hanger','Condition');b.chain('flight','hanger')
    b.fn('start_hanger',C+':StartClothingHanger',1800,-600)
    timer(b,'tick','TickClothingFlight',1/60,True,2100)
    b.get('stillactive','bClothingFlight',1800,900);b.node('placementguard','branch',2000,-600);b.link('stillactive','bClothingFlight','placementguard','Condition')
    b.get('camera','TopDownCamera',1800,1100)
    b.fn('widefov','/Script/Engine.CameraComponent:SetFieldOfView',1950,-200,InFieldOfView=55)  # the escapes' lens
    b.link('camera','TopDownCamera','widefov','self')
    b.chain('hanger','start_hanger','placementguard','tick');b.link('hanger','else','widefov','execute');b.chain('widefov','tick')
    finish(b,'Move only after the authored camera owns the view')

    b,e=fresh('TickClothingFlight');b.get('active','bClothingFlight',0,300)
    b.node('owned','branch',300,0);b.link('active','bClothingFlight','owned','Condition');b.chain(e,'owned')
    b.fn('now',GS+'GetTimeSeconds',0,500);b.get('started','ClothingFlightStarted',0,700)
    b.fn('elapsed',K+'Subtract_DoubleDouble',300,500);b.link('now','ReturnValue','elapsed','A');b.link('started','ClothingFlightStarted','elapsed','B')
    b.get('mode','ClothingChaseMode',300,900);b.fn('toss',K+'EqualEqual_IntInt',600,900,B=1);b.link('mode','ClothingChaseMode','toss','A')
    b.get('from','ClothingFlightFrom',600,400);b.get('to','ClothingFlightTo',600,600)
    b.fn('parts',K+'BreakTransform',900,400);b.link('from','ClothingFlightFrom','parts','InTransform')
    b.fn('clearpoint',K+'Add_VectorVector',1200,400,B=vector((0,PULL_DISTANCE,12)));b.link('parts','Location','clearpoint','A')
    b.fn('clearxf',K+'MakeTransform',1500,400);b.link('clearpoint','ReturnValue','clearxf','Location');b.link('parts','Rotation','clearxf','Rotation');b.link('parts','Scale','clearxf','Scale')
    b.fn('pulltime',K+'Subtract_DoubleDouble',900,900,B=.6);b.link('elapsed','ReturnValue','pulltime','A')
    b.fn('pullalpha',K+'Divide_DoubleDouble',1200,900,B=1.2);b.link('pulltime','ReturnValue','pullalpha','A')
    b.fn('pullclamp',K+'FClamp',1500,900,Min=0,Max=1);b.link('pullalpha','ReturnValue','pullclamp','Value')
    b.fn('pull',K+'TLerp',1800,400);b.link('from','ClothingFlightFrom','pull','A');b.link('clearxf','ReturnValue','pull','B');b.link('pullclamp','ReturnValue','pull','Alpha')
    b.fn('airtime',K+'Subtract_DoubleDouble',900,1200,B=1.8);b.link('elapsed','ReturnValue','airtime','A')
    b.fn('when',K+'SelectFloat',1200,1200);b.link('airtime','ReturnValue','when','A');b.link('elapsed','ReturnValue','when','B');b.link('toss','ReturnValue','when','bPickA')
    b.fn('length',K+'SelectFloat',1200,1400,A=.85,B=.95);b.link('toss','ReturnValue','length','bPickA')
    b.fn('alpha',K+'Divide_DoubleDouble',1500,1200);b.link('when','ReturnValue','alpha','A');b.link('length','ReturnValue','alpha','B')
    b.fn('clamp',K+'FClamp',1800,1200,Min=0,Max=1);b.link('alpha','ReturnValue','clamp','Value')
    b.fn('airfrom',K+'SelectTransform',1800,700);b.link('clearxf','ReturnValue','airfrom','A');b.link('from','ClothingFlightFrom','airfrom','B');b.link('toss','ReturnValue','airfrom','bPickA')
    b.fn('air',K+'TLerp',2100,400);b.link('airfrom','ReturnValue','air','A');b.link('to','ClothingFlightTo','air','B');b.link('clamp','ReturnValue','air','Alpha')
    b.fn('remain',K+'Subtract_DoubleDouble',2100,1200,A=1);b.link('clamp','ReturnValue','remain','B')
    b.fn('parabola',K+'Multiply_DoubleDouble',2400,1200);b.link('remain','ReturnValue','parabola','A');b.link('clamp','ReturnValue','parabola','B')
    b.fn('height',K+'Multiply_DoubleDouble',2700,1200,B=240);b.link('parabola','ReturnValue','height','A')
    b.fn('lift',K+'MakeVector',3000,1200);b.link('height','ReturnValue','lift','Z')
    b.fn('airparts',K+'BreakTransform',2400,400);b.link('air','ReturnValue','airparts','InTransform')
    b.fn('airpoint',K+'Add_VectorVector',2700,400);b.link('airparts','Location','airpoint','A');b.link('lift','ReturnValue','airpoint','B')
    b.fn('airxf',K+'MakeTransform',3000,400);b.link('airpoint','ReturnValue','airxf','Location');b.link('airparts','Rotation','airxf','Rotation');b.link('airparts','Scale','airxf','Scale')
    b.fn('early',K+'Less_DoubleDouble',2400,1500,B=1.8);b.link('elapsed','ReturnValue','early','A')
    b.fn('pulling',K+'BooleanAND',2700,1500);b.link('early','ReturnValue','pulling','A');b.link('toss','ReturnValue','pulling','B')
    b.fn('pose',K+'SelectTransform',3300,400);b.link('pull','ReturnValue','pose','A');b.link('airxf','ReturnValue','pose','B');b.link('pulling','ReturnValue','pose','bPickA')
    b.get('shirt','SearchShirt',3300,800);b.fn('move',A+'K2_SetActorTransform',3600,0,bSweep='false',bTeleport='true');b.link('shirt','SearchShirt','move','self');b.link('pose','ReturnValue','move','NewTransform')
    b.fn('hand',C+':UpdateClothingHanger',3900,0);b.chain('owned','move','hand')
    # The wide shot starts only once the garment is clear of the bed frame.
    b.node('wideguard','branch',4200,0);b.link('toss','ReturnValue','wideguard','Condition');b.chain('hand','wideguard')
    b.get('camera','TopDownCamera',4200,700)
    # A cut at the physical release preserves the continuous garment arc without
    # moving the camera through the mattress/teen between these two clear views.
    b.fn('widealpha',K+'SelectFloat',4500,1500,A=0,B=1);b.link('early','ReturnValue','widealpha','bPickA')
    b.get('view','ClothingInspectionView',4200,1000)
    b.fn('viewpoint',K+'VLerp',4500,700,B='40,-20,175')  # level1: from the room's west side over the fallen wardrobe's end (150,-40,140 sat on its back)
    b.link('view','ClothingInspectionView','viewpoint','A');b.link('widealpha','ReturnValue','viewpoint','Alpha')
    b.get('focus','ClothingInspectionFocus',4200,1200)
    b.fn('focuspoint',K+'VLerp',4500,1200,B='180,-100,45');b.link('focus','ClothingInspectionFocus','focuspoint','A');b.link('widealpha','ReturnValue','focuspoint','Alpha')
    b.fn('look',K+'FindLookAtRotation',4800,700);b.link('viewpoint','ReturnValue','look','Start');b.link('focuspoint','ReturnValue','look','Target')
    b.fn('fovvalue',K+'SelectFloat',4800,1700,A=50,B=70);b.link('early','ReturnValue','fovvalue','bPickA')
    b.fn('zoom','/Script/Engine.CameraComponent:SetFieldOfView',4900,0);b.link('camera','TopDownCamera','zoom','self');b.link('fovvalue','ReturnValue','zoom','InFieldOfView')
    b.fn('viewmove',SC+'K2_SetWorldLocationAndRotation',5100,0,bSweep='false',bTeleport='true');b.link('camera','TopDownCamera','viewmove','self');b.link('viewpoint','ReturnValue','viewmove','NewLocation');b.link('look','ReturnValue','viewmove','NewRotation');b.chain('wideguard','zoom','viewmove')
    b.get('duration','ClothingFlightDuration',5100,1400);b.fn('arrived',K+'GreaterEqual_DoubleDouble',5400,1400);b.link('elapsed','ReturnValue','arrived','A');b.link('duration','ClothingFlightDuration','arrived','B')
    b.node('done','branch',5400,0);b.link('arrived','ReturnValue','done','Condition');b.chain('viewmove','done');b.link('wideguard','else','done','execute')
    b.set('off','bClothingFlight',5700,0);b.pin('off','bClothingFlight','false');clear(b,'stop','TickClothingFlight',6000);b.chain('done','off','stop')
    finish(b,'A continuous under-bed pull followed by a visible airborne arc')

def build_handoff():
    b,e=fresh('PlaceClothingLanding');b.get('shirt','SearchShirt',0,300);b.get('to','ClothingFlightTo',0,500)
    b.fn('place',A+'K2_SetActorTransform',300,0,bSweep='false',bTeleport='true');b.link('shirt','SearchShirt','place','self');b.link('to','ClothingFlightTo','place','NewTransform')
    b.get('stage','ClothingSearchStage',300,500)
    b.fn('second',K+'EqualEqual_IntInt',600,500,B=6);b.link('stage','ClothingSearchStage','second','A')
    b.fn('final',K+'GreaterEqual_IntInt',600,700,B=7);b.link('stage','ClothingSearchStage','final','A')
    b.fn('state12',K+'SelectName',900,500,A='ChaseTwo',B='ChaseOne');b.link('second','ReturnValue','state12','bPickA')
    b.fn('state3',K+'SelectName',1200,500,A='ChaseFinal');b.link('state12','ReturnValue','state3','B');b.link('final','ReturnValue','state3','bPickA')
    b.fn('ready',BASE+':SetState',600,0,bInstant='true');b.link('shirt','SearchShirt','ready','self');b.link('state3','ReturnValue','ready','NewState')
    b.fn('collision',A+'SetActorEnableCollision',900,0,bNewActorEnableCollision='true');b.link('shirt','SearchShirt','collision','self')
    b.set('flight','bClothingFlight',1200,0);b.pin('flight','bClothingFlight','false')
    clear(b,'tick','TickClothingFlight',1500);b.chain(e,'place','ready','collision','flight','tick')
    finish(b,'Only a stationary reachable shirt offers a catch interaction')

    b,e=fresh('AbortClothingChase');b.get('active','bClothingChaseActive',0,300)
    b.node('owned','branch',300,0);b.link('active','bClothingChaseActive','owned','Condition');b.chain(e,'owned')
    clear(b,'tick','TickClothingFlight',600);clear(b,'wide','FrameClothingBoss',900)
    b.fn('hands',C+':ClearClothingHanger',1200,0)
    b.get('stage','ClothingSearchStage',1200,500);b.fn('vase',K+'EqualEqual_IntInt',1500,500,B=8);b.link('stage','ClothingSearchStage','vase','A')
    b.node('final','branch',1500,0);b.link('vase','ReturnValue','final','Condition')
    b.chain('owned','tick','wide','hands','final')
    b.set('stage7','ClothingSearchStage',1800,-200);b.pin('stage7','ClothingSearchStage',7)
    get_room(b,2100);b.fn('restorevase',ROOM+':CancelVaseFormation',2400,-200);b.link('room','ReturnValue','restorevase','self')
    b.chain('final','stage7','room','restorevase')
    b.fn('land',C+':PlaceClothingLanding',2700,0);b.link('final','else','land','execute');b.chain('restorevase','land')
    b.set('off','bClothingChaseActive',3000,0);b.pin('off','bClothingChaseActive','false');b.chain('land','off')
    finish(b,'Abort without spending the shirt or leaving a moving target')

    b,e=fresh('FinishClothingChaseShot');b.get('active','bClothingChaseActive',0,300)
    b.node('owned','branch',300,0);b.link('active','bClothingChaseActive','owned','Condition');b.chain(e,'owned')
    b.get('mode','ClothingChaseMode',300,500);b.fn('vase',K+'EqualEqual_IntInt',600,500,B=4);b.link('mode','ClothingChaseMode','vase','A')
    b.node('which','branch',600,0);b.link('vase','ReturnValue','which','Condition');b.chain('owned','which')
    # Reaching this watchdog means the formation callback did not arrive. Restore
    # a retryable final reach rather than handing out the shirt or trapping input.
    b.fn('abort',C+':AbortClothingChase',900,-300);b.chain('which','abort')
    b.fn('land',C+':PlaceClothingLanding',900,0);b.link('which','else','land','execute')
    b.fn('hands',C+':ClearClothingHanger',1200,0)
    b.set('off','bClothingChaseActive',1500,0);b.pin('off','bClothingChaseActive','false')
    b.fn('release',C+':CancelClothingInspection',1800,0);b.chain('land','hands','off','release');b.chain('abort','release')
    finish(b,'Release the player to follow the next stationary shirt')

    frame_boss()
    boss_formed()

def frame_boss():
    # The rising figure, framed from inside the bay too (the ClueViewBoss marker sat behind the closed curtain).
    b,e=fresh('FrameClothingBoss');guard=stage_guard(b,e,8);get_room(b,600);b.chain(guard,'room')
    side_camera(b,BOSS_VIEW_EAST,BOSS_VIEW,600)
    b.fn('focuspos',K+'MakeVector',1200,1400,**dict(zip('XYZ',BOSS_FOCUS)))
    view,focus='viewpos','focuspos'
    b.fn('look',K+'FindLookAtRotation',1500,1400);b.link(view,'ReturnValue','look','Start');b.link(focus,'ReturnValue','look','Target')
    b.get('camera','TopDownCamera',1800,1000)
    b.fn('move',SC+'K2_SetWorldLocationAndRotation',2100,0,bSweep='false',bTeleport='true')
    b.link('camera','TopDownCamera','move','self');b.link(view,'ReturnValue','move','NewLocation');b.link('look','ReturnValue','move','NewRotation');b.chain('room','move')
    finish(b,'The shattered vase gives way to the rising sand figure')

def boss_formed():
    b,e=fresh('ClothingBossFormed');guard=stage_guard(b,e,8)
    b.set('off','bClothingChaseActive',600,0);b.pin('off','bClothingChaseActive','false')
    b.fn('release',C+':CancelClothingInspection',900,0)
    b.set('stage9','ClothingSearchStage',1200,0);b.pin('stage9','ClothingSearchStage',9)
    b.get('shirt','SearchShirt',1200,400);state(b,'taken','Taken',1500)
    b.fn('inter',BASE+':GetInteractor',1500,700);b.link('shirt','SearchShirt','inter','self')
    b.get('bag','Inventory',1800,700,INTER);b.link('inter','Interactor','bag','self')
    b.fn('has',INVENTORY+':Has',2100,700,Item='Shirt');b.link('bag','Inventory','has','self')
    b.node('existing','branch',1800,0);b.link('has','bHas','existing','Condition')
    b.fn('add',INVENTORY+':Add',2100,200,Item='Shirt');b.link('bag','Inventory','add','self')  # the carried set never refuses (2026-11-10)
    b.fn('report',C+':ReportEvent',2400,0,Event='ShirtTaken')
    b.chain(guard,'existing','off','release','stage9','taken','report')
    b.link('existing','else','add','execute');b.chain('add','off')
    finish(b,'Only the completed formation hands off to the existing encounter')

def main():
    os.environ['HAYBA_AGENT_ID']='clothing_search';assert not call('editor_get_state')['pie_running']
    token=h.lease_acquire('clothing_search',['asset:'+P],ttl_s=240,wait_s=3)
    try:
        for n,t,v in [('bClothingChaseActive','bool','false'),('bClothingFlight','bool','false'),('bClothingHangerOwned','bool','false'),
            ('ClothingChaseMode','int','0'),('ClothingFlightFrom','transform',''),('ClothingFlightTo','transform',''),
            ('ClothingFlightStarted','float','0'),('ClothingFlightDuration','float','0'),
            ('ClothingHangerMontage','object:/Script/Engine.AnimMontage','')]:
            call('blueprint_add_variable',path=P,variable_name=n,variable_type=t,default_value=v,category='Clothing chase',update_existing=True)
        for n,t,v in [('ClothingHangerHome','transform',''),('ClothingHangerRadius','float','42')]:
            call('blueprint_add_variable',path=P,variable_name=n,variable_type=t,default_value=v,category='Clothing chase',update_existing=True)
        for n in FUNCS:
            if not h.call('blueprint_inspect_graph',dict(path=P,graph_name=n)).get('ok'):
                call('blueprint_add_function',path=P,function_name=n)
        # Inspection declares shared camera fields before any chase body references them.
        for n,t,v in [('ClothingInspectionDuration','float','1.6'),('bClothingContactShot','bool','false')]:
            call('blueprint_add_variable',path=P,variable_name=n,variable_type=t,default_value=v,category='Clothing discovery',update_existing=True)
        for row in [('BeginClothingToss',4,5,1),('EscapeClothingOne',5,6,2),('EscapeClothingTwo',6,7,3),('ReachClothingVase',7,8,4)]:write_queue(*row)
        build_motion()
        build_handoff()
        from clothing_hanger_graphs import build as build_hanger
        build_hanger()
        ns,es=inspect(P,'TryClothingInspection')
        if not any(n['title']=='Branch' and n.get('node_id') in {x['to_node'] for x in es if x['from_node']==find(ns,'OnClothingCameraReady')} for n in ns):
            action=find(ns,'OnClothingCameraReady')
            edge=next(x for x in es if x['from_node']==action and x['from_pin']=='then')
            b=Batch(P,'TryClothingInspection')
            b.cut(action,'then',edge['to_node'],edge['to_pin'])
            b.get('stillactive','bClothingInspection',5250,900)
            b.node('actionguard','branch',5350,0);b.link('stillactive','bClothingInspection','actionguard','Condition')
            b.chain(action,'actionguard');b.link('actionguard','then',edge['to_node'],edge['to_pin']);b.run()
        if '--prepare' not in sys.argv:
            # Commit handlers only after every cleanup and hand function is compiled.
            build_handler()
            b,e=fresh('FreeClothing');b.fn('toss',C+':BeginClothingToss',300,0);b.chain(e,'toss');finish(b,'A real hanger extraction starts the chase')
            ns,_=inspect(P,'CanReportClothingEvent')
            candidates=[n for n in ns if n['title'] in ('Equal (Integer)','Equal (Int)','EqualEqual_IntInt')]
            if not candidates:
                candidates=[n for n in ns if any(p['name']=='B' and p.get('type')=='int' for p in n.get('pins',[]))]
            assert len(candidates)==1,candidates
            b=Batch(P,'CanReportClothingEvent');b.pin(candidates[0]['node_id'],'B',9);b.run()
        print('Chase graph batch saved. Rebuild inspection integration, then commit targeted chase rows before PIE.')
    finally:h.release('clothing_search',token)

if __name__=='__main__':main()
