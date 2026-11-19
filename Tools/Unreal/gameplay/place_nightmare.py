"""Places the one BP_Nightmare the director drives (GetActorOfClass -> Appear/Vanish at its NightmareT1/T7/T8 markers):
label Nightmare, outliner folder Gameplay, hidden in game until Appear. Idempotent.
  FOA_ACTORS_NEW=Nightmare python Tools/Unreal/ue_remote.py Tools/Unreal/gameplay/place_nightmare.py"""
import unreal

EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
acts = {a.get_actor_label(): a for a in EAS.get_all_level_actors()}
n = acts.get("Nightmare")
if not n:
    d = acts["BeatDirector"]
    mark = [c for c in d.get_components_by_class(unreal.ArrowComponent) if c.get_name() == "NightmareT1"]
    loc = mark[0].get_world_location() if mark else unreal.Vector(220.0, -40.0, 0.0)
    n = EAS.spawn_actor_from_class(unreal.load_class(None, "/Game/FoA/Characters/Player/BP_Nightmare.BP_Nightmare_C"),
                                   unreal.Vector(loc.x, loc.y, loc.z + 92.0), unreal.Rotator(roll=0.0, pitch=0.0, yaw=0.0))
    n.set_actor_label("Nightmare")
n.set_folder_path("Gameplay")
n.set_actor_hidden_in_game(True)
l = n.get_actor_location()
print("FOA_NIGHTMARE", n.get_actor_label(), n.get_folder_path(), round(l.x), round(l.y), round(l.z))
