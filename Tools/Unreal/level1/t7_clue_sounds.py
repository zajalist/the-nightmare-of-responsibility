"""level1 lane: feedback sounds for row-driven states that changed silently (sound_audit, 2026-11-17): the T7
clothing search, and the T4 boots going on.
Merges into each placed interactable's StateSounds (keeps every existing entry). Idempotent.
  FOA_ACTORS=Bed,Desk,Wardrobe,Shirt_T7,Boot_L python Tools/Unreal/ue_remote.py Tools/Unreal/level1/t7_clue_sounds.py"""
import unreal

A = '/Game/FoA/Audio/MetaSounds/'
ADD = {
    'Bed': {'ClothingSnag': 'Foley/S_Foley_Reach', 'ClothingFreed': 'Props/S_Props_HangerRail'},  # finds it; the wire yanks it out
    'Desk': {'SearchDeskChecked': 'Props/S_Props_PaperRustle'},  # the button under the papers
    'Wardrobe': {'SearchWardrobeChecked': 'Wardrobe/S_Wardrobe_Creak'},  # he leans on the fallen wardrobe's broken wood
    'Shirt_T7': {'ChaseMoving': 'Foley/S_Foley_ClothTurn'},  # each time it whips away
    'Boot_L': {'Worn': 'Props/S_Props_BootPickup'},  # T4: the boots go on (was silent)
}
acts = {a.get_actor_label(): a for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()}
for label, add in ADD.items():
    a = acts[label]
    m = dict(a.get_editor_property('StateSounds'))
    for state, rel in add.items():
        s = unreal.load_asset(A + rel)
        assert s, rel
        m[unreal.Name(state)] = s
    a.modify()
    a.set_editor_property('StateSounds', m)
    got = {str(k): v.get_name() for k, v in dict(a.get_editor_property('StateSounds')).items()}
    assert all(got.get(k) == v.rsplit('/', 1)[1] for k, v in add.items()), (label, got)
    print('SOUNDS', label, got)
