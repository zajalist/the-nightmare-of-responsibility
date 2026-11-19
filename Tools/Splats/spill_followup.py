"""Spill follow-ups (sand direction page, Nov 5 review): dimmer, finer grain with a third of the glints; the commode
mound and the pour's pile on the same procedural material (no tiled texture left on any sand); the Path spill moved so
it crosses the real moonlight pool (the hero read), never re-aiming the moon.
  python Tools/Unreal/ue_remote.py Tools/Splats/spill_followup.py FOA_FOLLOW=look
  python Tools/Unreal/ue_remote.py Tools/Splats/spill_followup.py FOA_FOLLOW=move FOA_PATH_XY=x,y   (then Hayba level_save)"""
import os

import unreal

MEL, EAL = unreal.MaterialEditingLibrary, unreal.EditorAssetLibrary
D = "/Game/FoA/VFX/Sand"


def look():
    for name, spill in (("MI_SandSpill_Floor", (0.015, 0.003, 0.5, 0.9)), ("MI_SandSpill_Mound", (0.015, 0.003, 0.45, 0.9))):
        mi = unreal.load_asset(f"{D}/{name}")
        MEL.set_material_instance_vector_parameter_value(mi, "Spill", unreal.LinearColor(*spill))
        MEL.update_material_instance(mi)
        EAL.save_asset(f"{D}/{name}", only_if_is_dirty=False)
    mound = unreal.load_asset(f"{D}/MI_SandSpill_Mound")
    for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
        if a.get_actor_label() in ("SandMound_OnCommode", "SandSpill_Pile"):
            a.get_component_by_class(unreal.StaticMeshComponent).set_material(0, mound)
            print("mound material", a.get_actor_label())


def move():
    x, y = (float(v) for v in os.environ["FOA_PATH_XY"].split(","))
    for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
        if a.get_actor_label() in ("SandMound_Path", "SandSplats_Path"):
            z = a.get_actor_location().z
            a.set_actor_location(unreal.Vector(x, y, z), False, False)
            print("moved", a.get_actor_label(), x, y)


{"look": look, "move": move}[os.environ.get("FOA_FOLLOW", "look")]()
