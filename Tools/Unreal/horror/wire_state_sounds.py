"""Audio lane: the interactables' state cues. BP_Interactable.PlayFeedback plays StateSounds[NewState] on a played state
change; this merges the audio pass's presets into each placed instance's map by InteractionKey (other entries kept).
Only StateSounds is written: no transform, mesh or other property of the user's placed actors.
  $env:FOA_ACTORS='<labels>'; python Tools/Unreal/ue_remote.py Tools/Unreal/horror/wire_state_sounds.py [FOA_STEP=list]"""
import os

import unreal

MS = '/Game/FoA/Audio/MetaSounds/'
CUES = {  # InteractionKey -> {State: preset}
    'Door': {'LatchFree': 'Door/S_Door_LatchSlide', 'HandleOff': 'Door/S_Door_HandleOff', 'Open': 'Door/S_Door_FinalOpen'},
    'Hanger': {'Taken': 'Props/S_Props_HangerRail'},
    'Shirt': {'Taken': 'Props/S_Props_ShirtPickup'},
    'Desk': {'Open': 'Drawer/S_Drawer_Slide', 'Closed': 'Drawer/S_Drawer_Stop', 'Searched': 'Props/S_Props_PaperRustle'},
}


def main():
    base = unreal.load_class(None, '/Game/FoA/Gameplay/BP_Interactable.BP_Interactable_C')
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    acts = [a for a in eas.get_all_level_actors() if unreal.MathLibrary.class_is_child_of(a.get_class(), base)]
    rows = []
    for a in acts:
        key = str(a.get_editor_property('InteractionKey'))
        sounds = a.get_editor_property('StateSounds') or {}
        cur = {str(k): (v.get_name() if v else None) for k, v in sounds.items()}
        if os.environ.get('FOA_STEP') != 'list' and key in CUES:
            new = {unreal.Name(k): v for k, v in sounds.items()}
            for state, rel in CUES[key].items():
                s = unreal.load_asset(MS + rel)
                assert s, rel
                new[unreal.Name(state)] = s
            a.set_editor_property('StateSounds', new)
            cur = {str(k): v.get_name() for k, v in new.items()}
        rows.append(f'{a.get_actor_label()}|{a.get_class().get_name()}|{key}|{cur}')
    with open('P:/FoA/Saved/HorrorShots/state_sounds.txt', 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(rows))
    print('interactables', len(rows))


main()
