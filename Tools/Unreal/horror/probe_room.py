"""Read-only: writes labels, classes, folders and bounds of the room's actors to Saved/HorrorShots/probe_room.txt.
  FOA_AREAS=Gameplay python Tools/Unreal/ue_remote.py Tools/Unreal/horror/probe_room.py [FOA_MATCH=regex]"""
import os
import re

import unreal


def main():
    pat = re.compile(os.environ.get('FOA_MATCH', '.'), re.I)
    rows = []
    for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
        lab = a.get_actor_label()
        if not pat.search(lab):
            continue
        o, e = a.get_actor_bounds(False)
        rows.append('%s|%s|%s|%d,%d,%d|%d,%d,%d|yaw %d' % (lab, a.get_class().get_name(), a.get_folder_path(), o.x, o.y, o.z,
                                                          e.x, e.y, e.z, a.get_actor_rotation().yaw))
    with open('P:/FoA/Saved/HorrorShots/probe_room.txt', 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(rows))
    print('rows', len(rows))


main()
