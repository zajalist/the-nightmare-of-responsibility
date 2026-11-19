"""Apply native mesh/animation setters and attachment transforms to player templates and the wake spawnable.
Hayba reflection does not run component transform setters; this narrow fallback refreshes their actual transforms.
The old assets are retained in the pre-swap snapshot.
"""
import json
from pathlib import Path
import unreal
P='/Game/FoA/Characters/Player'
T='/Game/FoA/Characters/Teen'
E=unreal.EditorAssetLibrary
BEL=unreal.BlueprintEditorLibrary
bp=unreal.load_asset(P+'/BP_FoAPlayer')
unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(bp)
unreal.get_editor_subsystem(unreal.EditorActorSubsystem).select_nothing()
sds=unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem);lib=unreal.SubobjectDataBlueprintFunctionLibrary
handles={str(lib.get_variable_name(lib.get_data(h))):h for h in sds.k2_gather_subobject_data_for_blueprint(bp)}
for n in ('StartPants','StartSocks'):
    assert n in handles, 'Create starter components with Hayba before this phase'
    sds.attach_subobject(handles['Body'],handles[n])
comps={n:lib.get_object_for_blueprint(lib.get_data(h),bp) for n,h in handles.items()}
head_class=E.load_blueprint_class(T+'/Anim/ABP_FoA_TeenHead')
body_class=E.load_blueprint_class(P+'/ABP_FoAPlayer_MH')
pieces={'Body':'Body','Face':'Head','StartOutfit':'Polo','StartPants':'Pants','StartSocks':'Socks','Shirt':'Polo','Trousers':'Pants','Socks':'Socks','Suit':'Suit','BootsWornMesh':'Shoes'}

def apply(parts):
    teen_groom=any(isinstance(c,unreal.GroomComponent) and c.get_editor_property('groom_asset')
        and '/Teen/Hair/' in c.get_editor_property('groom_asset').get_path_name() for c in parts.values())
    for n,part in pieces.items():
        comp=parts[n];mesh=unreal.load_asset(T+'/Mesh/SK_Teen_'+part)
        assert mesh
        comp.set_skeletal_mesh_asset(mesh)
        if n!='Face' or not teen_groom:comp.set_editor_property('override_materials', [])
        comp.set_relative_transform(unreal.Transform(),False,True)
        comp.set_visibility(n in ('Body','Face','StartOutfit','StartPants','StartSocks'))
        comp.set_hidden_in_game(False)
        comp.set_collision_profile_name('NoCollision')
        if n in ('Body','Face'):
            comp.set_anim_instance_class(body_class if n=='Body' else head_class)
        else:
            comp.set_leader_pose_component(parts['Body'],True)
            comp.set_editor_property('use_attach_parent_bound',True)
    parts['Face'].set_render_custom_depth(True);parts['Face'].set_custom_depth_stencil_value(4)
    for comp in parts.values():
        if isinstance(comp,unreal.GroomComponent) and (not comp.get_editor_property('groom_asset') or '/Protagonist/' in comp.get_editor_property('groom_asset').get_path_name()):
            comp.set_groom_asset(None);comp.set_binding_asset(None);comp.set_visibility(False)
            comp.set_editor_property('override_materials', [])
    if 'Tie' in parts:
        parts['Tie'].set_skeletal_mesh_asset(None);parts['Tie'].set_visibility(False)

apply(comps)
assert E.save_loaded_asset(bp,False)
# The spawnable carries serialized copies; update existing mesh components after player compilation.
seq=unreal.load_asset('/Game/FoA/Cinematics/LS_WakeUp')
binding=next(b for b in seq.get_bindings() if str(b.get_display_name())=='Player')
template=unreal.MovieSceneBindingExtensions.get_object_template(binding)
parts={c.get_name():c for c in template.get_components_by_class(unreal.SkeletalMeshComponent)}
if all(n in parts for n in pieces):
    apply(parts)
else:
    print('Spawnable missing new components:',[n for n in pieces if n not in parts])
    for n,part in pieces.items():
        if n in parts:
            parts[n].set_skeletal_mesh_asset(unreal.load_asset(T+'/Mesh/SK_Teen_'+part))
            parts[n].set_editor_property('override_materials',[])
            if n in ('Body','Face'):
                parts[n].set_anim_instance_class(body_class if n=='Body' else head_class)
    for comp in template.get_components_by_class(unreal.GroomComponent):
        groom=comp.get_editor_property("groom_asset")
        if groom and "/Teen/Hair/" in groom.get_path_name():continue
        comp.set_groom_asset(None);comp.set_binding_asset(None);comp.set_visibility(False)
assert E.save_loaded_asset(seq,False)
print('Teen components assigned; compile player, then refresh spawnable template before proof')
