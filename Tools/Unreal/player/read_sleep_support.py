"""Read the unchanged bedding surface below the actual last captured skin and joints."""
import json,sys
from pathlib import Path
import unreal
sys.path.insert(0,'P:/FoA/Tools/Unreal/wakeup')
import wake_common as W
assert not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
bed=next(a for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
         if a.get_actor_label()=='Bedding_Lux3D')
material=bed.get_component_by_class(unreal.StaticMeshComponent).get_material(0)
matinfo=dict(path=material.get_path_name(),class_name=material.get_class().get_name())
if isinstance(material,unreal.Material):
    matinfo['DentDepth']=unreal.MaterialEditingLibrary.get_material_default_scalar_parameter_value(material,'DentDepth')
    matinfo['BodyCenter']=str(unreal.MaterialEditingLibrary.get_material_default_vector_parameter_value(material,'BodyCenter'))
    matinfo['BodyHalfSize']=str(unreal.MaterialEditingLibrary.get_material_default_vector_parameter_value(material,'BodyHalfSize'))
elif isinstance(material,unreal.MaterialInstance):
    matinfo['DentDepth']=unreal.MaterialEditingLibrary.get_material_instance_scalar_parameter_value(material,'DentDepth')
print('Bedding material',matinfo)
Path('P:/FoA/Saved/CharacterShots/bedding_support_material.json').write_text(json.dumps(matinfo,indent=1))
out={}
for name,x,y in [('pelvis',261,-191),('heel_l',188,-178),('heel_r',185,-201),
                 ('head',326,-191),('neck',315,-191),('shoulders',302,-191),
                 ('pillow_inner',335,-191),('pillow_outer',345,-191)]:
    out[name]=dict(x=x,y=y,surface_z=W.trace_down(x,y))
Path('P:/FoA/Saved/CharacterShots/sleep_support.json').write_text(json.dumps(out,indent=1))
print(json.dumps(out))
for y in (-100,-89,-80,-70,-60,-50):
    z=W.trace_down(270,y);out['exit_y_'+str(y)]=dict(x=270,y=y,surface_z=z)
    print('wake exit surface',270,y,z)
Path('P:/FoA/Saved/CharacterShots/sleep_support.json').write_text(json.dumps(out,indent=1))
folder=Path(json.loads(Path('P:/FoA/Saved/CharacterShots/sleep_side/latest.json').read_text())['folder'])
probes=folder/'support_probes.json'
if probes.exists():
    samples=json.loads(probes.read_text())
    for sample in samples:
        x,y,z=sample['skin']
        r=unreal.SystemLibrary.line_trace_single(W.world(),unreal.Vector(x,y,250),unreal.Vector(x,y,-5),
            unreal.TraceTypeQuery.TRACE_TYPE_QUERY1,True,[],unreal.DrawDebugTrace.NONE,True)
        hit=r[1] if isinstance(r,tuple) else r
        values=hit.to_tuple() if hit else None
        sample['surface_z']=values[5].z if values and values[0] else None
        sample['normal_z']=values[7].z if values and values[0] else None
        sample['clearance']=z-sample['surface_z'] if sample['surface_z'] is not None else None
        if sample['surface_z'] is not None and 'BeddingSettle' in matinfo['path']:
            footprint=max(0,1-((x-270)/85)**2-((y+191)/30)**2)**2
            sample['rendered_dent_cm']=footprint*max(0,min(1,sample['normal_z']))*matinfo['DentDepth']
            sample['rendered_clearance']=sample['clearance']+sample['rendered_dent_cm']
    (folder/'support_clearance.json').write_text(json.dumps(samples,indent=1))
    for region in sorted(set(s['region'] for s in samples)):
        ss=[s for s in samples if s['region']==region and s['clearance'] is not None]
        worst=min(ss,key=lambda s:s['clearance'])
        print(region,'worst skin clearance cm',worst)
