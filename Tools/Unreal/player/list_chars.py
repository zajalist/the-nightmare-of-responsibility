"""Read-only: every level actor carrying a skeletal mesh or a character/MetaHuman class (stray figures in shots).
  python Tools/Unreal/ue_remote.py Tools/Unreal/player/list_chars.py FOA_AREAS=/Game/FoA/Characters/Player"""
import unreal

EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
out = []
for a in EAS.get_all_level_actors():
    sk = a.get_components_by_class(unreal.SkeletalMeshComponent)
    if sk or isinstance(a, unreal.Character) or "MHC" in a.get_class().get_name():
        l = a.get_actor_location()
        out.append(f"{a.get_actor_label()} [{a.get_class().get_name()}] at=({l.x:.0f},{l.y:.0f},{l.z:.0f})")
with open("P:/FoA/Saved/AnimShots/chars.txt", "w") as f:
    f.write("\n".join(out) + "\n")
print("CHARS", len(out), out)
