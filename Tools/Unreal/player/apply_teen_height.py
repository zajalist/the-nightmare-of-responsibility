"""Uniform visual assembly + matching capsule, preserving ActorScale and every mesh asset."""
import json
from pathlib import Path
import unreal
assert not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
bp=unreal.load_asset('/Game/FoA/Characters/Player/BP_FoAPlayer')
sds=unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem);lib=unreal.SubobjectDataBlueprintFunctionLibrary
parents={};types={}
for handle in sds.k2_gather_subobject_data_for_blueprint(bp):
    data=lib.get_data(handle);name=str(lib.get_variable_name(data));obj=lib.get_object_for_blueprint(data,bp)
    parent=lib.get_parent_handle(data)
    try:parents[name]=str(lib.get_variable_name(lib.get_data(parent)))
    except Exception:parents[name]=''
    types[name]=obj.get_class().get_name() if obj else ''
for name,kind in types.items():
    if name=='Mesh' or kind not in ('SkeletalMeshComponent','GroomComponent'):continue
    chain=[];at=name
    for _ in range(40):
        at=parents.get(at,'');chain.append(at)
        if at in ('Mesh',''):break
    assert 'Mesh' in chain,(name,kind,chain)
cdo=unreal.get_default_object(bp.generated_class());mesh=cdo.get_editor_property('Mesh');capsule=cdo.get_editor_property('CapsuleComponent')
scale=170.0/180.0
old_half=capsule.get_editor_property('capsule_half_height');old_radius=capsule.get_editor_property('capsule_radius')
assert abs(old_half-90)<.01 or abs(old_half-85)<.01,old_half
capsule.set_editor_property('capsule_radius',old_radius*85.0/old_half)
capsule.set_editor_property('capsule_half_height',85.0)
mesh.set_editor_property('relative_scale3d',unreal.Vector(scale,scale,scale))
pos=mesh.get_editor_property('relative_location');mesh.set_editor_property('relative_location',unreal.Vector(pos.x,pos.y,-89.0*scale))
assert unreal.EditorAssetLibrary.save_loaded_asset(bp,False)
Path('P:/FoA/Saved/CharacterShots/teen_height_hierarchy.json').write_text(json.dumps(dict(scale=scale,parents=parents,types=types,capsule_half=85.0,capsule_radius=old_radius*85.0/old_half,mesh_z=-89.0*scale),indent=1))
print('Uniform teen hierarchy saved; ActorScale remains1; all visible mesh/groom descendants audited')
