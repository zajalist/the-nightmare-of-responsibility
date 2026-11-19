"""Replace only the encounter's helper sphere, preserving its exact local bounds."""
import json,re,sys
from pathlib import Path
sys.path.insert(0,'P:/FoA/Tools/Unreal');import hayba_call as h
P='/Game/FoA/Gameplay/Encounter/BP_Encounter'
C=P+'.BP_Encounter_C'
A='/Game/FoA/Maps/L_Tutorial_Bedroom.L_Tutorial_Bedroom:PersistentLevel.BP_Encounter_C_0'
M='/Game/FoA/Procedural/SM_SandMound_A/SM_SandMound_A/StaticMeshes/SM_SandMound_A'
def c(n,**kw):
 r=h.call(n,kw);assert r.get('ok'),r
 d=r.get('data',{});assert d.get('ok',True),d
 return d
assert not c('editor_get_state')['pie_running']
owner='room-takeover';lease=h.lease_acquire(owner,['asset:'+P,'actor:/Game/FoA/Maps/L_Tutorial_Bedroom.Encounter_T8'],ttl_s=80,wait_s=15)
try:
 assert not c('editor_get_state')['pie_running']
 bounds=c('object_get_property',path=M,names=['ExtendedBounds'])['properties']['ExtendedBounds']
 values=[float(v) for v in re.findall(r'[XYZ]=(-?[\d.]+)',bounds)];origin=values[:3];extent=values[3:6]
 scales=[v/e for v,e in zip((120,290,25),extent)]
 location=[v-o*s for v,o,s in zip((20,0,-14),origin,scales)]
 props={'StaticMesh':M,'OverrideMaterials':['/Game/FoA/VFX/Sand/MI_SandSpill_Mound'],
  'RelativeScale3D':dict(zip('XYZ',scales)),'RelativeLocation':dict(zip('XYZ',location))}
 guards={n:c('object_get_property',path=A+'.'+n,names=['RelativeLocation','RelativeRotation','RelativeScale3D'])['properties'] for n in ('BattleCam','HeroCam','PlayerMark','SandBurst')}
 before=c('object_get_property',path=A+'.Mound',names=['StaticMesh','OverrideMaterials','RelativeLocation','RelativeScale3D'])
 for path in (C+':Mound_GEN_VARIABLE',A+'.Mound'):c('object_set_property',path=path,properties=props)
 compiled=c('blueprint_compile',path=P);c('asset_save',asset_paths=[P])
 for n,expected in guards.items():assert c('object_get_property',path=A+'.'+n,names=list(expected))['properties']==expected,n
 after=c('object_get_property',path=A+'.Mound',names=list(before['properties']))
 Path('P:/FoA/Saved/WorldShots/encounter_mound_fixed.json').write_text(json.dumps({'before':before,'after':after,'compile':compiled,'preserved_battle_components':guards,'local_bounds_center':[20,0,-14],'local_bounds_extent':[120,290,25]},indent=1))
 print('Authored encounter mound saved; exact local footprint and battle components preserved')
finally:h.release(owner,lease)
