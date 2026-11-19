"""Read an optimized MetaHuman assembly and stage its exact runtime asset contract.
Set FOA_ASSEMBLED_BP to the finished supported build. This script never changes assets.
"""
import json,os
from pathlib import Path
import unreal
assert not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
source_path=os.environ.get('FOA_ASSEMBLED_BP');assert source_path, 'Provide the completed optimized assembly Blueprint'
source=unreal.load_asset(source_path);assert source,source_path
player=unreal.load_asset('/Game/FoA/Characters/Player/BP_FoAPlayer')
sds=unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem);lib=unreal.SubobjectDataBlueprintFunctionLibrary
def components(bp):
    out={}
    for h in sds.k2_gather_subobject_data_for_blueprint(bp):
        d=lib.get_data(h);out.setdefault(str(lib.get_variable_name(d)),lib.get_object_for_blueprint(d,bp))
    return out
def path(obj):return obj.get_path_name() if obj else None
def mesh_info(component):
    mesh=component.get_skeletal_mesh_asset();assert mesh
    return dict(mesh=path(mesh),skeleton=path(mesh.get_editor_property('skeleton')),
        post_process=path(mesh.get_editor_property('post_process_anim_blueprint')),
        physics=path(mesh.get_editor_property('physics_asset')),
        dna=[path(d.get_editor_property('dna_asset')) for d in mesh.get_editor_property('asset_user_data')
             if d.get_class().get_name()=='DNAAssetUserData'],anim_class=path(component.get_editor_property('anim_class')))
old,new=components(player),components(source)
assert {'Body','Face'}<=new.keys(),new.keys()
before={n:mesh_info(old[n]) for n in ('Body','Face','StartOutfit')}
assembly={n:mesh_info(new[n]) for n in ('Body','Face')}
if 'SkeletalMesh' in new and new['SkeletalMesh'].get_skeletal_mesh_asset():
    assembly['StartOutfit']=mesh_info(new['SkeletalMesh'])
for n in ('Body','Face'):
    m=assembly[n]
    assert m['dna'] and all(m['dna']), ('Missing generated DNA',n)
    assert m['post_process'], ('Missing generated post process',n)
    assert m['physics'] and not m['physics'].startswith('/MetaHumanCharacter/Body/IdentityTemplate/'), ('Template body physics is not a finished assembly',n)
grooms={}
for name,c in new.items():
    if not isinstance(c,unreal.GroomComponent) or not c.get_editor_property('groom_asset'):continue
    binding=c.get_editor_property('binding_asset');assert binding, name
    target=path(binding.get_editor_property('target_skeletal_mesh'))
    assert target==assembly['Face']['mesh'], ('Groom target does not match assembled face',name,target)
    grooms[name]=dict(groom=path(c.get_editor_property('groom_asset')),binding=path(binding),
        target=target,materials=[path(m) for m in c.get_editor_property('override_materials')],
        attachment_name=str(c.get_editor_property('attachment_name')))
scale=unreal.get_default_object(player.generated_class()).get_editor_property('Mesh').get_editor_property('relative_scale3d')
result=dict(source_blueprint=source_path,before=before,assembly=assembly,grooms=grooms,
    skeleton_matches={n:before[n]['skeleton']==assembly[n]['skeleton'] for n in ('Body','Face')},
    preserve_anim_classes={n:before[n]['anim_class'] for n in ('Body','Face')},
    current_source_scale=[scale.x,scale.y,scale.z],native_height_runtime=dict(source_scale=1.0,capsule_half=85.0,
        capsule_radius=33.0555555556,mesh_z=-84.0555555556),
    reset_body_reference=dict(graph='SetSuitedBody',branch=False,new_mesh=assembly['Body']['mesh']),
    readiness='Read-only plan; clothing fit, skin contact and runtime retarget stride still require final-body verification')
Path('P:/FoA/Saved/CharacterShots/native_teen_integration_plan.json').write_text(json.dumps(result,indent=1))
print('Staged exact assembled asset contract; runtime unchanged',result['skeleton_matches'])
