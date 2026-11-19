"""List level actors whose label matches FOA_KEYS (comma separated, case-insensitive), with bounds centre and extent.
  python Tools/Unreal/ue_remote.py Tools/LookDev/probe_props.py FOA_KEYS=bed,phone,clock"""
import os

import unreal


def main():
    keys = [k.lower() for k in os.environ.pop("FOA_KEYS", "").split(",") if k]
    for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
        lab = a.get_actor_label()
        if any(k in lab.lower() for k in keys):
            o, e = a.get_actor_bounds(False)
            print(f"{lab} | {a.get_class().get_name()} | {a.get_folder_path()} | c=({o.x:.0f},{o.y:.0f},{o.z:.0f}) "
                  f"e=({e.x:.0f},{e.y:.0f},{e.z:.0f}) hidden={a.is_hidden_ed()}")


main()
