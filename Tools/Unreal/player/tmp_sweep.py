"""Destroys every TMP_anim_ actor in the editor level and lists what was removed (cleanup after a failed capture).
  python Tools/Unreal/ue_remote.py Tools/Unreal/player/tmp_sweep.py FOA_ACTORS_NEW=TMP_anim_"""
import unreal

EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
gone = []
for a in EAS.get_all_level_actors():
    if a.get_actor_label().startswith("TMP_anim_"):
        gone.append(a.get_actor_label())
        EAS.destroy_actor(a)
left = [a.get_actor_label() for a in EAS.get_all_level_actors() if a.get_actor_label().startswith("TMP_anim_")]
print("TMP_SWEEP removed", gone, "left", left)
