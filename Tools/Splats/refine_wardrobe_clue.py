"""Owned clue only: tiny splinter, fine short thread, wider frame and local fill."""
import json,sys,shutil,tempfile,os
from pathlib import Path
sys.path.insert(0,'P:/FoA/Tools/Splats')
from build_clothing_clues import *
ACTOR='/Game/FoA/Maps/L_Tutorial_Bedroom.L_Tutorial_Bedroom:PersistentLevel.BP_RoomTakeover_C_1'
OWNER='room-takeover'
os.environ['HAYBA_AGENT_ID']=OWNER
MARKERS=('ClueFocusWardrobe','ClueViewWardrobe','ClueFocusBed','ClueViewBed')
def transform(item):
 return {'StaticMesh':item['mesh'],'OverrideMaterials':[item['mat']],
  'RelativeLocation':dict(zip('XYZ',item['loc'])),'RelativeRotation':dict(zip(('Pitch','Yaw','Roll'),item['rot'])),
  'RelativeScale3D':dict(zip('XYZ',item['size'])),'CastShadow':True,'Mobility':'Movable',
  'bGenerateOverlapEvents':False,'BodyInstance':'(CollisionProfileName="NoCollision",CollisionEnabled=NoCollision)'}
assert not call('editor_get_state')['pie_running']
lease=h.lease_acquire(OWNER,['asset:'+P,'asset:/Game/FoA/Props/Clues','actor:'+ACTOR],ttl_s=90,wait_s=10)
try:
 assert not call('editor_get_state')['pie_running']
 if not Path('P:/FoA/Content/FoA/Props/Clues/SM_WardrobeSplinter.uasset').exists():
  cache=Path(tempfile.gettempdir())/'hayba-asset-connectors'/'FoA'/'clothing_clues';cache.mkdir(parents=True,exist_ok=True)
  target=cache/'SM_WardrobeSplinter.fbx';shutil.copyfile('P:/FoA-Assets/procedural/wardrobe_splinter/SM_WardrobeSplinter.fbx',target)
  call('asset_import',source_file=str(target),destination_path='/Game/FoA/Props/Clues',asset_type='static_mesh')
 parts,marks=layout(json.loads((OUT/'clothing_clue_surfaces.json').read_text()))
 parts=[p for p in parts if p['group']==1]
 exists=h.call('object_get_property',{'path':C+':ClueWoodSplinter_GEN_VARIABLE','names':['StaticMesh']})
 if not exists.get('ok'):
  call('blueprint_add_component',path=P,component_class_path='/Script/Engine.StaticMeshComponent',component_name='ClueWoodSplinter')
 for part in parts:
  values=transform(part);values['bVisible']=False
  call('object_set_property',path=C+':'+part['name']+'_GEN_VARIABLE',properties=values)
 ns,es=inspect(P,'ApplyClothingClues')
 if not any(n['title']=='Get ClueWoodSplinter' for n in ns):
  thread=find(ns,'Get ClueThread0')
  setter=next(e['to_node'] for e in es if e['from_node']==thread and e['to_pin']=='self')
  visible=next(e for e in es if e['to_node']==setter and e['to_pin']=='bNewVisibility')
  tail=next(n['node_id'] for n in ns if n['title']=='SetVisibility' and not any(e['from_node']==n['node_id'] and e['from_pin']=='then' for e in es))
  b=Batch(P,'ApplyClothingClues');b.get('wood','ClueWoodSplinter',2850,4900);b.fn('showwood',SC+'SetVisibility',2850,4650)
  b.link('wood','ClueWoodSplinter','showwood','self');b.link(visible['from_node'],visible['from_pin'],'showwood','bNewVisibility');b.chain(tail,'showwood');b.comment('Thread caught on splinter',['wood','showwood']);b.run()
 for name in MARKERS:
  call('object_set_property',path=C+':'+name+'_GEN_VARIABLE',properties={'RelativeLocation':dict(zip('XYZ',marks[name]))})
 focus=marks['ClueFocusWardrobe'];light={'RelativeLocation':dict(zip('XYZ',(focus[0]-8,focus[1]-18,focus[2]+26))),'Intensity':4.,'SourceRadius':10.,'AttenuationRadius':85.}
 call('object_set_property',path=C+':ClueWardrobeFill_GEN_VARIABLE',properties=light)
 compiled=call('blueprint_compile',path=P);assert compiled.get('error_count',0)==0,compiled
 # Explicitly sync the existing placed instance; new SCS defaults do not propagate reliably.
 for part in parts:call('object_set_property',path=ACTOR+'.'+part['name'],properties=transform(part))
 for name in MARKERS:call('object_set_property',path=ACTOR+'.'+name,properties={'RelativeLocation':dict(zip('XYZ',marks[name]))})
 call('object_set_property',path=ACTOR+'.ClueWardrobeFill',properties=light)
 call('asset_save',asset_paths=[P,SPLINTER]);call('level_save')
 mesh_bounds=h.call('object_get_property',{'path':SPLINTER,'names':['ExtendedBounds','ImportedBounds']})
 report={'compile':compiled,'parts':parts,'markers':{n:marks[n] for n in MARKERS},'light':light,'mesh_bounds':mesh_bounds,'runtime_verified':False}
 (OUT/'wardrobe_clue_refined.json').write_text(json.dumps(report,indent=1))
 print(json.dumps({'parts':len(parts),'compile':compiled,'light':light}))
finally:h.release(OWNER,lease)
