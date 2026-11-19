"""Lookdev cleanup check: destroy any leftover TMP_lookdev_* actor or unlabelled SceneCapture2D, and report.
  python Tools/Unreal/ue_remote.py Tools/LookDev/cleanup_check.py"""
import unreal


def main():
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    gone = []
    for a in eas.get_all_level_actors():
        lab = a.get_actor_label()
        if lab.startswith("TMP_lookdev") or (isinstance(a, unreal.SceneCapture2D) and lab.startswith("SceneCapture2D")):
            gone.append(lab)
            eas.destroy_actor(a)
    print("lookdev cleanup: removed", gone or "nothing")


main()
