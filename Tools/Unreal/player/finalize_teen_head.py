"""Persist the supported head-only export and its exact preview groom bindings; does not edit the player."""
import json
import unreal

ROOT = "/Game/FoA/Characters/Protagonist/Teen/Built_N"
EAL = unreal.EditorAssetLibrary
AT = unreal.AssetToolsHelpers.get_asset_tools()
SUB = unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)
assert not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
ch = unreal.load_asset("/Game/FoA/Characters/Protagonist/Faces/MHC_Face_N")
head = unreal.load_asset(ROOT + "/MHC_Face_N_Head")
original = unreal.load_asset("/Game/FoA/Characters/Protagonist/Built/MHC_Protagonist/Face/SKM_MHC_Protagonist_FaceMesh")
assert ch and head and original
if not SUB.is_object_added_for_editing(ch):
    assert SUB.try_add_object_to_edit(ch)


def persist(obj, folder, name):
    path = ROOT + "/" + folder + "/" + name
    result = unreal.load_asset(path) if EAL.does_asset_exist(path) else AT.duplicate_asset(name, ROOT + "/" + folder, obj)
    assert result, path
    return result


def material(source, name):
    assert source
    if isinstance(source, unreal.MaterialInstanceDynamic):
        path = ROOT + "/Grooms/" + name
        target = unreal.load_asset(path) if EAL.does_asset_exist(path) else AT.create_asset(
            name, ROOT + "/Grooms", unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
        parent = source.get_editor_property("parent")
        assert parent and "/Transient" not in parent.get_path_name()
        unreal.MaterialEditingLibrary.set_material_instance_parent(target, parent)
        for values in ("scalar_parameter_values", "vector_parameter_values", "texture_parameter_values"):
            target.set_editor_property(values, source.get_editor_property(values))
    else:
        target = persist(source, "Grooms", name)
    for item in target.get_editor_property("texture_parameter_values"):
        texture = item.get_editor_property("parameter_value")
        assert not texture or "/Transient" not in texture.get_path_name(), texture
    assert EAL.save_loaded_asset(target, False)
    return target


actor = SUB.spawn_meta_human_actor(ch, True)
actor.set_actor_label("TMP_character_TeenRuntime")
result = {"head": head.get_path_name(), "grooms": {}}
try:
    SUB.assemble_for_preview(character=ch)
    face = next(c for c in actor.get_components_by_class(unreal.SkeletalMeshComponent) if c.get_name() == "Face")
    source_head = face.get_editor_property("skeletal_mesh_asset")
    slots = source_head.get_editor_property("materials")
    assert len(slots) == len(head.get_editor_property("materials")), "Export topology/material slots changed"
    for i, slot in enumerate(slots):
        mi = slot.get_editor_property("material_interface")
        assert mi
        if isinstance(mi, unreal.MaterialInstanceDynamic):
            parent = mi.get_editor_property("parent")
            print("TEEN face material", str(slot.get_editor_property("material_slot_name")), mi.get_path_name(),
                  "parent", parent.get_path_name() if parent else None)
            mi = parent if parent and parent.get_path_name().startswith(ROOT) else material(mi, "MI_Teen_Face_" + str(i))
            slot.set_editor_property("material_interface", mi)
            slots[i] = slot
        assert "/Transient" not in mi.get_path_name(), "Exported face materials must be persistent"
    head.set_editor_property("materials", slots)
    assert head.get_editor_property("skeleton") == original.get_editor_property("skeleton"), "Native skeleton assignment required"
    assert head.get_editor_property("post_process_anim_blueprint") == original.get_editor_property("post_process_anim_blueprint")
    assert head.get_editor_property("asset_user_data"), "New face DNA is required"
    assert EAL.save_loaded_asset(head, False)
    for component in actor.get_components_by_class(unreal.GroomComponent):
        name = component.get_name()
        if name not in ("Hair", "Eyebrows"):
            continue
        groom = component.get_editor_property("groom_asset")
        binding = component.get_editor_property("binding_asset")
        assert groom and binding, name
        new_groom = persist(groom, "Grooms", "GR_Teen_" + name)
        new_binding = persist(binding, "Grooms", "GB_Teen_" + name)
        new_binding.set_editor_property("groom", new_groom)
        new_binding.set_editor_property("target_skeletal_mesh", head)
        source_mesh = binding.get_editor_property("source_skeletal_mesh")
        assert not source_mesh or "/Transient" not in source_mesh.get_path_name(), "Persist groom source before saving"
        new_binding.set_editor_property("source_skeletal_mesh", source_mesh)
        mats = [material(mi, "MI_Teen_" + name + "_" + str(i))
                for i, mi in enumerate(component.get_editor_property("override_materials"))]
        assert EAL.save_loaded_asset(new_groom, False)
        assert EAL.save_loaded_asset(new_binding, False)
        result["grooms"][name] = {"groom": new_groom.get_path_name(), "binding": new_binding.get_path_name(),
                                  "materials": [m.get_path_name() for m in mats],
                                  "attachment_name": str(component.get_editor_property("attachment_name"))}
    assert set(result["grooms"]) == {"Hair", "Eyebrows"}
    assert EAL.save_directory(ROOT, False, True)
    with open("P:/FoA/Saved/CharacterShots/teen_runtime_assets.json", "w") as file:
        json.dump(result, file, indent=2)
    print("TEEN head/materials/groom bindings persisted; player unchanged", result)
finally:
    unreal.get_editor_subsystem(unreal.EditorActorSubsystem).destroy_actor(actor)
