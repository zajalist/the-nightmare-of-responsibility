"""Set-dressing fix-ups Hayba can't do, run INSIDE the open editor (idempotent; touches only Dress_* actors):
  python Tools/Unreal/ue_remote.py Tools/Unreal/finalize_dressing.py [FOA_SAVE=1]

- Collision: floor props block (with a box primitive added to meshes that have no simple collision); rugs, wall pieces
  and small clutter get NoCollision.
- Lantern: the bulb slot gets MI_Lantern_Bulb_Off (emissive 0), so the ceiling light reads as switched off.
- Candles: the flame cards get M_Dress_Hidden (masked, opacity 0), so the candles are unlit.
- Creates (once) Dress_Light_CeilingLantern at 0 lm. No persistent shot cameras: shoot from poses (shoot_dream_post.py).
- Prints each Dress_* actor's world bounds, so floating or sunken props show up as numbers.
"""
import os

import unreal

EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
EAL = unreal.EditorAssetLibrary
MEL = unreal.MaterialEditingLibrary
SML = unreal.EditorStaticMeshLibrary
DRESS = "/Game/FoA/Dressing"
BLOCKING = ("Dress_Plant_Bay", "Dress_Plant_Corner", "Dress_Chest_BedFoot", "Dress_Basket_Corner", "Dress_Radiator_Bay")


def hidden_material():
    path = f"{DRESS}/Materials/M_Dress_Hidden"
    if EAL.does_asset_exist(path):
        return unreal.load_asset(path)
    m = unreal.AssetToolsHelpers.get_asset_tools().create_asset("M_Dress_Hidden", f"{DRESS}/Materials",
                                                                unreal.Material, unreal.MaterialFactoryNew())
    m.set_editor_property("blend_mode", unreal.BlendMode.BLEND_MASKED)
    zero = MEL.create_material_expression(m, unreal.MaterialExpressionConstant, -300, 0)
    zero.set_editor_property("r", 0.0)
    MEL.connect_material_property(zero, "", unreal.MaterialProperty.MP_OPACITY_MASK)
    MEL.recompile_material(m)
    EAL.save_loaded_asset(m)
    return m


def bulb_off(lamp_mat):
    """An instance of the lantern's bulb material with every emissive input zeroed."""
    path = f"{DRESS}/Materials/MI_Lantern_Bulb_Off"
    if EAL.does_asset_exist(path):
        return unreal.load_asset(path)
    mi = unreal.AssetToolsHelpers.get_asset_tools().create_asset("MI_Lantern_Bulb_Off", f"{DRESS}/Materials",
                                                                 unreal.MaterialInstanceConstant,
                                                                 unreal.MaterialInstanceConstantFactoryNew())
    MEL.set_material_instance_parent(mi, lamp_mat)
    for name in MEL.get_scalar_parameter_names(lamp_mat):
        if "emissive" in str(name).lower():
            MEL.set_material_instance_scalar_parameter_value(mi, name, 0.0)
    for name in MEL.get_vector_parameter_names(lamp_mat):
        if "emissive" in str(name).lower():
            MEL.set_material_instance_vector_parameter_value(mi, name, unreal.LinearColor(0, 0, 0, 1))
    MEL.update_material_instance(mi)
    EAL.save_loaded_asset(mi)
    print("bulb params:", [str(n) for n in MEL.get_scalar_parameter_names(lamp_mat)],
          [str(n) for n in MEL.get_vector_parameter_names(lamp_mat)])
    return mi


def ensure(label, cls, loc, rot=None, folder="Room/Dressing"):
    found = [a for a in EAS.get_all_level_actors() if a.get_actor_label() == label]
    if found:
        return found[0], False
    a = EAS.spawn_actor_from_class(cls, unreal.Vector(*loc), rot or unreal.Rotator())
    a.set_actor_label(label)
    a.set_folder_path(folder)
    return a, True


def lights():
    # the lantern's bulb light, present but at 0 lm so a later beat can switch it on
    light, new = ensure("Dress_Light_CeilingLantern", unreal.PointLight, (0.0, 0.0, 252.0))
    if new:
        c = light.get_editor_property("point_light_component")
        c.set_mobility(unreal.ComponentMobility.MOVABLE)
        c.set_editor_property("intensity_units", unreal.LightUnits.LUMENS)
        c.set_editor_property("intensity", 0.0)
        c.set_editor_property("use_temperature", True)
        c.set_editor_property("temperature", 2700.0)
        c.set_editor_property("attenuation_radius", 800.0)
        c.set_editor_property("source_radius", 3.0)


def main():
    lights()
    actors = [a for a in EAS.get_all_level_actors() if a.get_actor_label().startswith("Dress_")]
    for a in sorted(actors, key=lambda x: x.get_actor_label()):
        label = a.get_actor_label()
        comp = a.get_component_by_class(unreal.StaticMeshComponent)
        if comp is None:
            continue
        mesh = comp.static_mesh
        if mesh and label in BLOCKING:
            if SML.get_simple_collision_count(mesh) == 0:
                SML.add_simple_collisions(mesh, unreal.ScriptCollisionShapeType.BOX)
                EAL.save_loaded_asset(mesh)
            comp.set_collision_profile_name("BlockAll")
        else:
            comp.set_collision_profile_name("NoCollision")
        for i, slot in enumerate(mesh.static_materials if mesh else []):
            name = str(slot.get_editor_property("material_slot_name"))
            if name.endswith("_flame"):
                comp.set_material(i, hidden_material())
            elif name == "lantern_chandelier_01_lamp":
                comp.set_material(i, bulb_off(slot.get_editor_property("material_interface")))
        o, e = a.get_actor_bounds(False)
        print(f"{label:<34} {str(a.get_folder_path()):<14} {comp.get_collision_profile_name()!s:<12} "
              f"min=({o.x - e.x:.1f},{o.y - e.y:.1f},{o.z - e.z:.2f}) max=({o.x + e.x:.1f},{o.y + e.y:.1f},{o.z + e.z:.2f})")
    if os.environ.get("FOA_SAVE") == "1":
        unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
        print("level saved")


main()
