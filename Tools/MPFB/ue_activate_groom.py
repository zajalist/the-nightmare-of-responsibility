"""Refresh groom attachment setters unavailable through reflection; player and wake template only."""
import json,os
from pathlib import Path
import unreal
assert not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
root='/Game/FoA/Characters/Teen'
groom=unreal.load_asset(root+'/Hair/GR_Teen_Scalp')
binding=unreal.load_asset(root+'/Hair/GB_Teen_Scalp_Head')
skin=unreal.load_asset(root+'/Materials/MI_Teen_Skin_Groom')
hidden=unreal.load_asset(root+'/Hair/M_Teen_HideCards')
assert groom and binding and skin and hidden
assert binding.get_editor_property('target_skeletal_mesh')==unreal.load_asset(root+'/Mesh/SK_Teen_Head')
phase=os.environ['FOA_GROOM_PHASE']
bp=unreal.load_asset('/Game/FoA/Characters/Player/BP_FoAPlayer')
if phase=='blueprint':
    subsystem=unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    library=unreal.SubobjectDataBlueprintFunctionLibrary
    handles={str(library.get_variable_name(library.get_data(h))):h for h in subsystem.k2_gather_subobject_data_for_blueprint(bp)}
    assert subsystem.attach_subobject(handles['Face'],handles['Hair'])
    components={name:library.get_object_for_blueprint(library.get_data(handle),bp) for name,handle in handles.items()}
    asset=bp
else:
    asset=unreal.load_asset('/Game/FoA/Cinematics/LS_WakeUp')
    player=next(b for b in asset.get_bindings() if str(b.get_display_name())=='Player')
    template=unreal.MovieSceneBindingExtensions.get_object_template(player)
    components={c.get_name().removesuffix('_GEN_VARIABLE'):c for c in template.get_components_by_class(unreal.SceneComponent)}
    if 'Face' not in components:
        print('GROOM_SPAWNABLE_TEMPLATE',template.get_path_name(),template.get_class().get_name(),list(components))
        raise RuntimeError('Spawnable has no constructed Face component; refresh its class template')
face=components['Face'];hair=components['Hair'];body=components['Body']
before={'body':body.get_skinned_asset().get_path_name(),'body_transform':body.get_relative_transform().export_text(),
        'face':face.get_skinned_asset().get_path_name(),'face_transform':face.get_relative_transform().export_text(),
        'hair_asset':hair.get_editor_property('groom_asset').get_path_name() if hair.get_editor_property('groom_asset') else None,
        'face_materials':[face.get_material(i).get_path_name() for i in range(face.get_num_materials())]}
assert before['face']==root+'/Mesh/SK_Teen_Head.SK_Teen_Head'
if phase!='blueprint':
    hair.attach_to_component(face,'',unreal.AttachmentRule.KEEP_RELATIVE,unreal.AttachmentRule.KEEP_RELATIVE,unreal.AttachmentRule.KEEP_RELATIVE,False)
hair.set_relative_transform(unreal.Transform(),False,True)
rigid=all(l.get_editor_property('binding_type')==unreal.GroomBindingType.RIGID
          for g in groom.get_editor_property('hair_groups_lod') for l in g.get_editor_property('lods'))
hair.set_editor_property('attachment_name','head' if rigid else '')
hair.set_groom_asset(groom);hair.set_binding_asset(None if rigid else binding)
hair.set_editor_property('override_materials',[])
hair.set_material(0,unreal.load_asset(root+'/Hair/MI_Teen_Strands'))
hair.set_visibility(True);hair.set_hidden_in_game(False)
hair.set_editor_property('use_attach_parent_bound',True)
hair.set_render_custom_depth(True);hair.set_custom_depth_stencil_value(4)
face.set_material(0,skin)
slots=[str(m.material_slot_name) for m in face.get_skinned_asset().materials]
card_index=next(i for i,n in enumerate(slots) if 'short01' in n)
face.set_material(card_index,hidden)
assert body.get_relative_transform().export_text()==before['body_transform']
assert face.get_relative_transform().export_text()==before['face_transform']
assert body.get_skinned_asset().get_path_name()==before['body']
assert unreal.EditorAssetLibrary.save_loaded_asset(asset,False)
report={'phase':phase,'before':before,'groom':groom.get_path_name(),'binding':None if rigid else binding.get_path_name(),'attachment_name':'head' if rigid else '',
        'hair_relative':hair.get_relative_transform().export_text(),'card_slot':card_index,'face_materials':[face.get_material(i).get_path_name() for i in range(face.get_num_materials())]}
Path('P:/FoA/Saved/CharacterShots/mpfb/hair/groom_'+phase+'_activation.json').write_text(json.dumps(report,indent=2))
print('GROOM_ACTIVATED',json.dumps(report))
