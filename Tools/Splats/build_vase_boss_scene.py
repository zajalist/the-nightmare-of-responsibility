"""Owned ceramic break and sand formation on RoomTakeover. Native BP-only runtime.

Director owns the camera/input. It calls BreakVaseThenBoss at the final reach,
then receives ClothingBossFormed after 3.8 seconds. Reset cancels the scene.
BreakVaseOnly (2026-11-10, the user's "It won't come"): the same tip, break, shards and sand pile, with no sand figure
and no ClothingBossFormed callback (story's LS_BattleIntro calls it at 0.8 s).
"""
import json,math,sys,re
from pathlib import Path
sys.path.insert(0,'P:/FoA/Tools/Splats')
from build_room_takeover import P,C,K,KS,SC,AU,call,h,Batch,inspect,find,fresh,done,timer,clear
from build_sand_painting import append
GS='/Script/Engine.GameplayStatics:'
PR='/Script/Engine.PrimitiveComponent:'
D='/Game/FoA/Gameplay/BP_BeatDirector.BP_BeatDirector_C'
MOUND='/Game/FoA/Procedural/SM_SandMound_A/SM_SandMound_A/StaticMeshes/SM_SandMound_A'
SUIT='/Game/FoA/VFX/Splats/Meshes/SM_SandSuit/SM_SandSuit/StaticMeshes/SM_SandSuit'
BOSS_MAT='/Game/FoA/VFX/Splats/Instances/MI_Sand_VaseBoss'
BOSS_SIZE=(.85,.85,.85)
BOSS_YAW=-56.0 # Original Lux3D front is +Y; face the authored reveal camera ClueViewBoss (170,-220) from FLOOR.
POT='/Game/FoA/Props/potted_plant_02/potted_plant_02_1k/StaticMeshes/potted_plant_02_pot'
CERAMIC='/Game/FoA/Props/potted_plant_02/potted_plant_02_1k/Materials/potted_plant_02_pot'
# The vase stands on a surface (VASE, its base) and falls to the floor (FLOOR, where it shatters and the sand boss
# rises). Both are RoomTakeover-relative (the actor sits at the origin). Old single anchor: both (-100,-20,.35).
# 2026-11-09 (the user: "put that vase ... in a more natural spot"): on the bay windowsill (Sill_window_4_0 top z 85.5,
# right of the sill plant and clear of the radiator, x -91.5..-28.5), in the moonbeam. Grabbing the shirt beside it knocks
# it off the sill; it shatters on the bay floor, on the bay sand, and the boss rises in the moonbeam where Ev_Suit's
# foreshadowing suit stands.
VASE=(-15,-379,85.6)
FLOOR=(-15,-345,.35)
TIP=11   # cm the falling vase's pivot sits above FLOOR at impact (tipped on its side)
VIEW_VASE=(-20,-230,125)   # the reveal camera's eye for the vase beat: 1.5 m into the room, looking at the sill
FRAG=json.loads(Path('P:/FoA-Assets/procedural/vase_fragments/fragments.json').read_text())
def vector(v):return ','.join(str(x) for x in v)
def show(b,ref,name,value,x,y=0):
 b.get(ref+'part',name,x,y+180);b.fn(ref,SC+'SetVisibility',x,y,bNewVisibility=str(value).lower());b.link(ref+'part',name,ref,'self');return ref
def asset_parts():
 rows=[('VaseIntact',POT,CERAMIC,VASE,(.45,.45,.95),True),
  ('VaseSandPile',MOUND,'/Game/FoA/VFX/Sand/MI_SandSpill_Mound',FLOOR,(.6,.6,.6),False),
  ('VaseSandBoss',SUIT,BOSS_MAT,FLOOR,BOSS_SIZE,False)]
 rows += [('VaseShard'+str(i+1),'/Game/FoA/Props/VaseFragments/'+r['name'],CERAMIC,FLOOR,(1,1,1),False) for i,r in enumerate(FRAG)]
 return rows
def assets():
 info=call('blueprint_get_info',path=P);have={x['name'] for x in info['components']}
 if info.get('_truncated'): # the component list is cut on this big BP: probe each template instead
  names=[r[0] for r in asset_parts()]+['ClueFocusVase','ClueViewVase','ClueFocusBoss','ClueViewBoss','VaseBreakSound','VaseSandSound']
  have|={n for n in names if h.call('object_get_property',{'path':C+':'+n+'_GEN_VARIABLE','names':['RelativeLocation']}).get('ok')}
 if not h.call('material_get_info',{'path':BOSS_MAT}).get('ok'):
  call('material_create_instance',parent_material_path='/Game/FoA/VFX/Splats/Instances/MI_Sand_Suit',package_path=BOSS_MAT,name='MI_Sand_VaseBoss')
 call('material_set_param',instance_path=BOSS_MAT,param_name='Splat',value=[1.15,.9,1,.9])
 call('material_set_param',instance_path=BOSS_MAT,param_name='Glitch',value=.015)
 call('asset_save',asset_paths=[BOSS_MAT])
 for row in FRAG:
  bounds=call('object_get_property',path='/Game/FoA/Props/VaseFragments/'+row['name'],names=['ExtendedBounds'])['properties']['ExtendedBounds']
  xyz=[float(v) for v in re.findall(r'[XYZ]=(-?[\d.]+)',bounds)]
  assert 10<xyz[5]<20,(row['name'],'Fragment scale is not centimetres',bounds)
 for name,mesh,mat,loc,scale,visible in asset_parts():
  if name not in have:call('blueprint_add_component',path=P,component_class_path='/Script/Engine.StaticMeshComponent',component_name=name)
  call('object_set_property',path=C+':'+name+'_GEN_VARIABLE',properties={'StaticMesh':mesh,'OverrideMaterials':[mat],
   'RelativeLocation':dict(zip('XYZ',loc)),'RelativeScale3D':dict(zip('XYZ',scale)),
   'RelativeRotation':{'Pitch':0,'Yaw':BOSS_YAW if name=='VaseSandBoss' else 0,'Roll':0},
   'bVisible':visible,'CastShadow':name=='VaseIntact' or name.startswith('VaseShard'),'Mobility':'Movable',
   'bGenerateOverlapEvents':False,'BodyInstance':'(CollisionProfileName="NoCollision",CollisionEnabled=NoCollision)'})
 for name,loc in {'ClueFocusVase':(VASE[0],VASE[1],VASE[2]+24),'ClueViewVase':VIEW_VASE,'ClueFocusBoss':(FLOOR[0],FLOOR[1],FLOOR[2]+85),'ClueViewBoss':(170,-220,165)}.items():
  if name not in have:call('blueprint_add_component',path=P,component_class_path='/Script/Engine.SceneComponent',component_name=name)
  call('object_set_property',path=C+':'+name+'_GEN_VARIABLE',properties={'RelativeLocation':dict(zip('XYZ',loc))})
 for name,sound,vol in [('VaseBreakSound','/Game/FoA/Audio/SFX/Props/SFX_Props_GlassDrop_01',.8),('VaseSandSound','/Game/FoA/Audio/MetaSounds/Sand/S_Sand_Pour',.7)]:
  if name not in have:call('blueprint_add_component',path=P,component_class_path='/Script/Engine.AudioComponent',component_name=name)
  call('object_set_property',path=C+':'+name+'_GEN_VARIABLE',properties={'Sound':sound,'VolumeMultiplier':vol,'bAutoActivate':False})
 for name,typ,default in [('bVaseSceneActive','bool','false'),('bVaseBroken','bool','false'),('VaseStarted','float','0'),('bVaseOnly','bool','false')]:
  call('blueprint_add_variable',path=P,variable_name=name,variable_type=typ,default_value=default,category='Vase scene',update_existing=True)
 sigs={n:[] for n in ('ResetVase','CancelVaseFormation','BreakVaseThenBoss','BreakVaseOnly','ShatterVase','StepVase','FinishVaseBoss')}
 sigs['ApplyVaseShard']=[('Part','object:/Script/Engine.StaticMeshComponent'),('Start','vector'),('End','vector'),('EndRotation','rotator'),('Alpha','float')]
 for fn,inputs in sigs.items():
  if fn not in info['functions']:call('blueprint_add_function',path=P,function_name=fn,inputs=[dict(name=n,type=t) for n,t in inputs])
 call('blueprint_compile',path=P);call('asset_save',asset_paths=[P])
def reset():
 b,e=fresh('ResetVase');clear(b,'stop','StepVase',200,0);b.set('active','bVaseSceneActive',500,0);b.pin('active','bVaseSceneActive','false')
 b.set('broken','bVaseBroken',800,0);b.pin('broken','bVaseBroken','false')
 b.set('only','bVaseOnly',1000,-200);b.pin('only','bVaseOnly','false');b.chain(e,'stop','active','broken','only');prev='only'
 for i,(name,*_) in enumerate(asset_parts()):
  ref='visible'+str(i);show(b,ref,name,name=='VaseIntact',1100+(i%4)*330,(i//4)*500);b.chain(prev,ref);prev=ref
 b.get('vase','VaseIntact',1100,1800);b.fn('home',SC+'K2_SetRelativeLocation',1400,1500,NewLocation=vector(VASE));b.link('vase','VaseIntact','home','self')
 b.fn('upright',SC+'K2_SetRelativeRotation',1700,1500,NewRotation='0,0,0');b.link('vase','VaseIntact','upright','self');b.chain(prev,'home','upright');prev='upright'
 for i,name in enumerate(('VaseBreakSound','VaseSandSound')):
  b.get('sound'+str(i),name,2000+i*350,1800);b.fn('quiet'+str(i),AU+'Stop',2000+i*350,1500);b.link('sound'+str(i),name,'quiet'+str(i),'self');b.chain(prev,'quiet'+str(i));prev='quiet'+str(i)
 done(b,'Restore the unbroken vase')
 b,e=fresh('CancelVaseFormation');b.fn('restore',C+':ResetVase',300,0);b.chain(e,'restore');done(b,'Cancel only this scene')
def begin():
 b,e=fresh('BreakVaseThenBoss');b.get('active','bVaseSceneActive',0,250);b.get('broken','bVaseBroken',0,400)
 b.fn('busy',K+'BooleanOR',300,300);b.link('active','bVaseSceneActive','busy','A');b.link('broken','bVaseBroken','busy','B')
 b.node('once','branch',600,0);b.link('busy','ReturnValue','once','Condition');b.chain(e,'once')
 b.set('start','bVaseSceneActive',900,0);b.pin('start','bVaseSceneActive','true');b.link('once','else','start','execute')
 b.fn('now',GS+'GetTimeSeconds',900,300);b.set('clock','VaseStarted',1200,0);b.link('now','ReturnValue','clock','VaseStarted')
 timer(b,'animate','StepVase',1500,0,.05,True);b.chain('start','clock','animate');done(b,'Begin at hand contact')
def only():
 b,e=fresh('BreakVaseOnly');b.set('only','bVaseOnly',250,0);b.pin('only','bVaseOnly','true')
 b.fn('go',C+':BreakVaseThenBoss',550,0);b.chain(e,'only','go');done(b,'Break without the figure')
def shatter():
 b,e=fresh('ShatterVase');b.set('broken','bVaseBroken',250,0);b.pin('broken','bVaseBroken','true');b.chain(e,'broken');prev='broken'
 for i,(name,*_) in enumerate(asset_parts()):
  ref='show'+str(i);show(b,ref,name,name!='VaseIntact',600+(i%4)*330,(i//4)*500);b.chain(prev,ref);prev=ref
 b.fn('now',GS+'GetTimeSeconds',600,1900);b.fn('event',K+'MakeVector4',900,1900,X=1,Z=2.5,W=0);b.link('now','ReturnValue','event','Y')
 b.get('boss','VaseSandBoss',1200,1900);b.fn('flow',PR+'SetVectorParameterForCustomPrimitiveData',1200,1500,ParameterName='SandEvent');b.link('boss','VaseSandBoss','flow','self');b.link('event','ReturnValue','flow','Value')
 b.get('vonly','bVaseOnly',1000,1300);b.node('figure','branch',1000,1100);b.link('vonly','bVaseOnly','figure','Condition');b.chain(prev,'figure')
 show(b,'nofig','VaseSandBoss',False,1200,1100);b.link('figure','then','nofig','execute');b.link('figure','else','flow','execute')
 prev=None
 for i,name in enumerate(('VaseBreakSound','VaseSandSound')):
  b.get('snd'+str(i),name,1550+i*350,1900);b.fn('play'+str(i),AU+'Play',1550+i*350,1500,StartTime=0);b.link('snd'+str(i),name,'play'+str(i),'self')
  if prev:b.chain(prev,'play'+str(i))
  else:b.chain('flow','play0');b.chain('nofig','play0')
  prev='play'+str(i)
 done(b,'Ceramic breaks into sand')
def shard():
 b,e=fresh('ApplyVaseShard');b.fn('mix',K+'VLerp',300,350);b.link(e,'Start','mix','A');b.link(e,'End','mix','B');b.link(e,'Alpha','mix','Alpha')
 b.fn('angle',K+'Multiply_DoubleDouble',0,650,B=math.pi);b.link(e,'Alpha','angle','A')
 b.fn('sin',K+'Sin',300,650);b.link('angle','ReturnValue','sin','A')
 b.fn('height',K+'Multiply_DoubleDouble',600,650,B=24);b.link('sin','ReturnValue','height','A')
 b.fn('arc',K+'MakeVector',900,650,X=0,Y=0);b.link('height','ReturnValue','arc','Z')
 b.fn('point',K+'Add_VectorVector',1200,350);b.link('mix','ReturnValue','point','A');b.link('arc','ReturnValue','point','B')
 b.fn('rot',K+'RLerp',1200,650,A='0,0,80',bShortestPath='true');b.link(e,'EndRotation','rot','B');b.link(e,'Alpha','rot','Alpha')
 b.fn('move',SC+'K2_SetRelativeLocation',1550,0);b.link(e,'Part','move','self');b.link('point','ReturnValue','move','NewLocation')
 b.fn('turn',SC+'K2_SetRelativeRotation',1900,0);b.link(e,'Part','turn','self');b.link('rot','ReturnValue','turn','NewRotation');b.chain(e,'move','turn');done(b,'Six short fragment arcs')
def finish_scene():
 b,e=fresh('FinishVaseBoss');clear(b,'stop','StepVase',250,0);b.set('active','bVaseSceneActive',550,0);b.pin('active','bVaseSceneActive','false');b.chain(e,'stop','active')
 show(b,'hide','VaseSandBoss',False,850);b.chain('active','hide')
 b.get('sound','VaseSandSound',1150,300);b.fn('quiet',AU+'Stop',1150,0);b.link('sound','VaseSandSound','quiet','self');b.chain('hide','quiet')
 b.fn('director',GS+'GetActorOfClass',1450,0,ActorClass=D);b.chain('quiet','director')
 b.fn('valid',KS+'IsValid',1450,300);b.link('director','ReturnValue','valid','Object');b.node('guard','branch',1750,0)
 b.get('vonly','bVaseOnly',1450,500);b.fn('nofig',K+'Not_PreBool',1600,500);b.link('vonly','bVaseOnly','nofig','A')
 b.fn('call',K+'BooleanAND',1650,300);b.link('valid','ReturnValue','call','A');b.link('nofig','ReturnValue','call','B')
 b.link('call','ReturnValue','guard','Condition');b.chain('director','guard')
 b.fn('fight',D+':ClothingBossFormed',2050,0);b.link('director','ReturnValue','fight','self');b.chain('guard','fight');done(b,'Hand off the formed boss')
def step():
 b,e=fresh('StepVase');b.get('active','bVaseSceneActive',0,250);b.node('gate','branch',250,0);b.link('active','bVaseSceneActive','gate','Condition');b.chain(e,'gate')
 b.fn('now',GS+'GetTimeSeconds',0,550);b.get('started','VaseStarted',0,700);b.fn('time',K+'Subtract_DoubleDouble',300,550);b.link('now','ReturnValue','time','A');b.link('started','VaseStarted','time','B')
 b.fn('tipTime',K+'Divide_DoubleDouble',600,550,B=.65);b.link('time','ReturnValue','tipTime','A');b.fn('tip',K+'FClamp',900,550,Min=0,Max=1);b.link('tipTime','ReturnValue','tip','Value')
 b.fn('roll',K+'Multiply_DoubleDouble',1200,550,B=80);b.link('tip','ReturnValue','roll','A');b.fn('rotation',K+'MakeRotator',1500,550);b.link('roll','ReturnValue','rotation','Roll')
 b.fn('fall',K+'Multiply_DoubleDouble',1050,800);b.link('tip','ReturnValue','fall','A');b.link('tip','ReturnValue','fall','B')
 b.fn('position',K+'VLerp',1500,800,A=vector(VASE),B=vector((FLOOR[0],FLOOR[1],FLOOR[2]+TIP)));b.link('fall','ReturnValue','position','Alpha')
 b.get('vase','VaseIntact',1500,1050);b.fn('move',SC+'K2_SetRelativeLocation',1800,0);b.link('vase','VaseIntact','move','self');b.link('position','ReturnValue','move','NewLocation')
 b.fn('turn',SC+'K2_SetRelativeRotation',2100,0);b.link('vase','VaseIntact','turn','self');b.link('rotation','ReturnValue','turn','NewRotation');b.chain('gate','move','turn')
 b.get('broken','bVaseBroken',1800,550);b.fn('not',K+'Not_PreBool',2100,550);b.link('broken','bVaseBroken','not','A')
 b.fn('impact',K+'GreaterEqual_DoubleDouble',1800,800,B=.65);b.link('time','ReturnValue','impact','A');b.fn('first',K+'BooleanAND',2400,550);b.link('not','ReturnValue','first','A');b.link('impact','ReturnValue','first','B')
 b.node('break','branch',2400,0);b.link('first','ReturnValue','break','Condition');b.fn('shatter',C+':ShatterVase',2700,-250);b.chain('turn','break','shatter')
 b.fn('elapsed',K+'Subtract_DoubleDouble',0,1600,B=.65);b.link('time','ReturnValue','elapsed','A')
 b.fn('ratio',K+'Divide_DoubleDouble',300,1600,B=.9);b.link('elapsed','ReturnValue','ratio','A');b.fn('alpha',K+'FClamp',600,1600,Min=0,Max=1);b.link('ratio','ReturnValue','alpha','Value')
 prev=None
 for i,row in enumerate(FRAG):
  x=1100+(i%3)*550;y=1450+(i//3)*600;name='VaseShard'+str(i+1);centre=row['center_cm'];angle=math.radians(i*60+18)
  # Intact tip at 80 degrees. Fragments land in a small ring around the impact.
  r=math.radians(80);start=(FLOOR[0]+centre[0],FLOOR[1]+centre[1]*math.cos(r)+centre[2]*math.sin(r),FLOOR[2]+TIP-centre[1]*math.sin(r)+centre[2]*math.cos(r))
  end=(FLOOR[0]+math.cos(angle)*(26+i*2),FLOOR[1]+17+math.sin(angle)*(24+i*2),FLOOR[2]+9)
  b.get(name,name,x,y+280);b.fn('fragment'+str(i),C+':ApplyVaseShard',x,y,Start=vector(start),End=vector(end),EndRotation=vector((15-i*6,i*61,80-i*7)))
  b.link(name,name,'fragment'+str(i),'Part');b.link('alpha','ReturnValue','fragment'+str(i),'Alpha')
  if prev:b.chain(prev,'fragment'+str(i))
  else:b.chain('shatter','fragment0');b.link('break','else','fragment0','execute')
  prev='fragment'+str(i)
 b.fn('formtime',K+'Subtract_DoubleDouble',0,2850,B=.8);b.link('time','ReturnValue','formtime','A')
 b.fn('formratio',K+'Divide_DoubleDouble',300,2850,B=2.5);b.link('formtime','ReturnValue','formratio','A');b.fn('formclamp',K+'FClamp',600,2850,Min=0,Max=1);b.link('formratio','ReturnValue','formclamp','Value')
 b.fn('form',K+'FInterpEaseInOut',900,2850,A=0,B=1,Exponent=2);b.link('formclamp','ReturnValue','form','Alpha')
 for i,(name,base) in enumerate([('VaseSandPile',(.65,.65,.65)),('VaseSandBoss',BOSS_SIZE)]):
  x=1200+i*650;b.fn('size'+str(i),K+'Multiply_VectorFloat',x,3000,A=vector(base));b.link('form','ReturnValue','size'+str(i),'B')
  b.get(name,name,x,3200);b.fn('grow'+str(i),SC+'SetRelativeScale3D',x,2600);b.link(name,name,'grow'+str(i),'self');b.link('size'+str(i),'ReturnValue','grow'+str(i),'NewScale3D');b.chain(prev,'grow'+str(i));prev='grow'+str(i)
 b.fn('ended',K+'GreaterEqual_DoubleDouble',2500,2850,B=3.8);b.link('time','ReturnValue','ended','A');b.node('end','branch',2500,2600);b.link('ended','ReturnValue','end','Condition')
 b.fn('finish',C+':FinishVaseBoss',2850,2600);b.chain(prev,'end','finish')
 # Separate comments keep the time, ceramic, fragments and sand sections legible.
 refs=[o['ref'] for o in b.ops if o.get('op')=='add_node']
 b.comment('Tip before the impact',refs[:refs.index('elapsed')]);b.comment('Scatter real ceramic',refs[refs.index('elapsed'):refs.index('formtime')]);b.comment('Sand takes a shape',refs[refs.index('formtime'):]);b.run()
def main():
 assert not call('editor_get_state')['pie_running']
 owner='room-takeover';lease=h.lease_acquire(owner,['asset:'+P],ttl_s=240,wait_s=20)
 try:
  assert not call('editor_get_state')['pie_running']
  assets();shard();reset();begin();only();shatter();finish_scene();step();append('Reset','ResetVase','Restore the ceramic vase')
  result=call('blueprint_compile',path=P);call('asset_save',asset_paths=[P])
  proof={'compile':result,'duration':3.8,'shatter_at':.65,'callback':'ClothingBossFormed','parts':asset_parts()}
  for name in ('ResetVase','CancelVaseFormation','BreakVaseThenBoss','BreakVaseOnly','ShatterVase','ApplyVaseShard','StepVase','FinishVaseBoss'):
   ns,es=inspect(P,name);proof[name]={'nodes':ns,'edges':es}
  Path('P:/FoA/Saved/WorldShots/vase_boss_scene_applied.json').write_text(json.dumps(proof,indent=1))
  print('Vase scene compiled and saved; actual fracture/formation runtime proof still pending')
 finally:h.release(owner,lease)
if __name__=='__main__':main()
