"""Assign typed SkeletalMaterial slots (generic Hayba reflection does not support this struct array)."""
import unreal

P = "/Game/FoA/Characters/Player/Clothing"
suit = unreal.load_asset(P + "/SK_FoA_Suit")
slots = suit.get_editor_property("materials")
for i, slot in enumerate(slots):
    name = str(slot.get_editor_property("material_slot_name"))
    instance = "MI_Suit_Cloth" if "uniform_1001" in name else "MI_Suit_ButtonGreen" if (
        "Button_1062" in name or name == "blinn6SG") else "MI_Suit_ButtonDark"
    material = unreal.load_asset(P + "/" + instance)
    assert material, instance
    slot.set_editor_property("material_interface", material)
    slots[i] = slot
suit.set_editor_property("materials", slots)
assert all(s.get_editor_property("material_interface") for s in suit.get_editor_property("materials"))
unreal.EditorAssetLibrary.save_loaded_asset(suit, False)
print("Suit materials", [(str(s.material_slot_name), s.material_interface.get_name()) for s in slots])
