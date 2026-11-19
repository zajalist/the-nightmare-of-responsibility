"""Read-only: the editor world's name and every actor whose label starts with TMP_ (leftovers from lane runs)."""
import unreal
w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
print("FOA_WORLD", w.get_path_name() if w else None,
      "TMP", sorted(a.get_actor_label() for a in eas.get_all_level_actors() if a.get_actor_label().startswith("TMP_")))
