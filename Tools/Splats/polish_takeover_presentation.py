"""Front-facing, framed sand reveal and restrained light for the physical clues."""
import sys,json
from pathlib import Path
sys.path.insert(0,'P:/FoA/Tools/Splats')
from build_vase_boss_scene import *
ACTOR='/Game/FoA/Maps/L_Tutorial_Bedroom.L_Tutorial_Bedroom:PersistentLevel.BP_RoomTakeover_C_1'
LIGHTS={'ClueWardrobeFill':((137.042809,-38.013222,137.963885),4,85),'ClueBedFill':((270,-102,15),3,150)}
assert not call('editor_get_state')['pie_running']
lease=h.lease_acquire('room-takeover',['asset:'+P,'asset:'+BOSS_MAT,'actor:'+ACTOR],ttl_s=100,wait_s=20)
try:
 assert not call('editor_get_state')['pie_running']
 if not h.call('material_get_info',{'path':BOSS_MAT}).get('ok'):
  call('material_create_instance',parent_material_path='/Game/FoA/VFX/Splats/Instances/MI_Sand_Suit',package_path=BOSS_MAT,name='MI_Sand_VaseBoss')
 call('material_set_param',instance_path=BOSS_MAT,param_name='Splat',value=[1.15,.9,1,.9])
 call('material_set_param',instance_path=BOSS_MAT,param_name='Glitch',value=.015)
 call('asset_save',asset_paths=[BOSS_MAT])
 props={'OverrideMaterials':[BOSS_MAT],'RelativeRotation':{'Pitch':0,'Yaw':BOSS_YAW,'Roll':0},'RelativeScale3D':dict(zip('XYZ',BOSS_SIZE))}
 for p in (C+':VaseSandBoss_GEN_VARIABLE',ACTOR+'.VaseSandBoss'):call('object_set_property',path=p,properties=props)
 ns,es=inspect(P,'StepVase');b=Batch(P,'StepVase')
 sizes=[n for n in ns if n['title']=='vector * float' and any(p.get('name')=='A' and p.get('default_value') in ('0.8,0.8,1.05','0.85,0.85,0.85') for p in n['pins'])]
 assert len(sizes)==1,sizes
 b.pin(sizes[0]['node_id'],'A',','.join(map(str,BOSS_SIZE)));b.run()
 for name,(loc,intensity,radius) in LIGHTS.items():
  if not h.call('object_get_property',{'path':C+':'+name+'_GEN_VARIABLE','names':['Intensity']}).get('ok'):
   call('blueprint_add_component',path=P,component_class_path='/Script/Engine.PointLightComponent',component_name=name)
  values={'RelativeLocation':dict(zip('XYZ',loc)),'Intensity':intensity,'IntensityUnits':'Lumens','AttenuationRadius':radius,'SourceRadius':10 if name=='ClueWardrobeFill' else 18,'CastShadows':False,'bVisible':False,'Mobility':'Movable'}
  for p in (C+':'+name+'_GEN_VARIABLE',ACTOR+'.'+name):call('object_set_property',path=p,properties=values)
 ns,es=inspect(P,'ApplyClothingClues')
 if not any(n['title']=='Get ClueBedFill' for n in ns):
  e=find(ns,'ApplyClothingClues');edge=next(x for x in es if x['from_node']==e and x['from_pin']=='then')
  b=Batch(P,'ApplyClothingClues');b.get('lightstage','Stage',0,-650)
  b.fn('wardready',K+'GreaterEqual_IntInt',300,-650,B=1);b.link('lightstage','Stage','wardready','A')
  b.fn('bedready',K+'GreaterEqual_IntInt',300,-850,B=3);b.link('lightstage','Stage','bedready','A')
  b.fn('bednotdone',K+'Less_IntInt',300,-1050,B=5);b.link('lightstage','Stage','bednotdone','A')
  b.fn('bedlit',K+'BooleanAND',650,-850);b.link('bedready','ReturnValue','bedlit','A');b.link('bednotdone','ReturnValue','bedlit','B')
  for i,(name,condition) in enumerate([('ClueWardrobeFill','wardready'),('ClueBedFill','bedlit')]):
   b.get(name,name,900+i*400,-650);b.fn('light'+str(i),SC+'SetVisibility',900+i*400,-350)
   b.link(name,name,'light'+str(i),'self');b.link(condition,'ReturnValue','light'+str(i),'bNewVisibility')
  b.cut(e,'then',edge['to_node'],edge['to_pin']);b.chain(e,'light0','light1');b.link('light1','then',edge['to_node'],edge['to_pin']);b.comment('Light the physical evidence',['lightstage','wardready','bedready','bednotdone','bedlit','ClueWardrobeFill','ClueBedFill','light0','light1']);b.run()
 result=call('blueprint_compile',path=P);call('asset_save',asset_paths=[P]);call('level_save')
 proof={'compile':result,'boss_size':BOSS_SIZE,'boss_yaw':BOSS_YAW,'lights':LIGHTS}
 for name in ('VaseSandBoss',*LIGHTS):proof[name]=call('object_get_property',path=ACTOR+'.'+name,names=['RelativeLocation','RelativeRotation','RelativeScale3D','bVisible'])
 Path('Saved/WorldShots/takeover_presentation_polish.json').write_text(json.dumps(proof,indent=1));print(result)
finally:h.release('room-takeover',lease)
