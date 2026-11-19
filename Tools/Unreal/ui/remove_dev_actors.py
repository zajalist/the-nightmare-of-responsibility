"""Deletes the UI lane's leftover test actors (Dev_MenuCam_B, anything labelled TMP_ui_*). Run via ue_remote.py."""
import unreal


def main():
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    gone = []
    for a in eas.get_all_level_actors():
        lab = a.get_actor_label()
        if lab == 'Dev_MenuCam_B' or lab.startswith('TMP_ui_'):
            gone.append(lab)
            eas.destroy_actor(a)
    print('removed', gone)


main()
