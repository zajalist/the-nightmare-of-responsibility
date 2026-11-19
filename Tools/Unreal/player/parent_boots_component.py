"""SCS parenting gap only. Native Hayba adds the component and compiles/saves after this short step."""
import json
import unreal

P = "/Game/FoA/Characters/Player/BP_FoAPlayer"
assert not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
bp = unreal.load_asset(P)
unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(bp)
unreal.get_editor_subsystem(unreal.EditorActorSubsystem).select_nothing()
sub = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
lib = unreal.SubobjectDataBlueprintFunctionLibrary
handles = {str(lib.get_variable_name(lib.get_data(h))): h for h in sub.k2_gather_subobject_data_for_blueprint(bp)}
assert "BootsWornMesh" in handles and "Body" in handles
assert sub.attach_subobject(handles["Body"], handles["BootsWornMesh"])
component = lib.get_object_for_blueprint(lib.get_data(handles["BootsWornMesh"]), bp)
body = lib.get_object_for_blueprint(lib.get_data(handles["Body"]), bp)
component.set_skeletal_mesh_asset(unreal.load_asset("/Game/FoA/Characters/Player/Clothing/SK_FoA_Boots_Worn"))
component.set_editor_property("relative_location", unreal.Vector())
component.set_editor_property("relative_rotation", unreal.Rotator())
component.set_editor_property("relative_scale3d", unreal.Vector(1, 1, 1))
component.set_editor_property("component_tags", ["BootsWorn"])
component.set_editor_property("use_bounds_from_leader_pose_component", True)
component.set_editor_property("lighting_channels", body.get_editor_property("lighting_channels"))
component.set_collision_profile_name("NoCollision")
component.set_visibility(False)
outfit = lib.get_object_for_blueprint(lib.get_data(handles["StartOutfit"]), bp).get_skeletal_mesh_asset()
materials = outfit.get_editor_property("materials")
def material_line(item):
    mi=item.get_editor_property("material_interface")
    names=[str(item.get_editor_property("material_slot_name"))]
    for _ in range(4):
        if not mi:break
        names.append(mi.get_path_name())
        mi=mi.get_editor_property("parent") if isinstance(mi,unreal.MaterialInstanceConstant) else None
    return " ".join(names)
lines=[material_line(item) for item in materials]
print("STARTER_SLOTS", list(enumerate(lines)))
slippers = [i for i, line in enumerate(lines) if "slipper" in line.lower()]
assert slippers, "Inspect starter footwear sections before changing coverage"
with open("P:/FoA/Saved/CharacterShots/boots_component.json", "w") as file:
    json.dump({"slippers_material": slippers[0], "slippers_materials": slippers, "source_materials": lines}, file)
print("Boots component parented to unchanged Body; starter slipper material", slippers[0])
