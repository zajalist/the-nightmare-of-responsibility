"""Wires the audio lane's MetaSounds into the level (the audio lane is idle; gameplay owns integration):
  1. BP_Interactable.StateSounds (State -> sound) and BurstStates (State -> sand burst scale), played by PlayFeedback on a
     played state change, per InteractionKey
  2. room ambience: AmbientSound actors Amb_RoomTone (whole room), Amb_NightWind (bay window), Amb_ClockTick (wall clock)
Idempotent (sets the maps, spawns an ambience actor only if its label is missing). FOA_STEP=list prints the
interactables without changing anything.
  FOA_ACTORS=<labels> FOA_ACTORS_NEW=Amb_ python Tools/Unreal/ue_remote.py Tools/Unreal/gameplay/wire_sounds.py [FOA_STEP=list]"""
import os

import unreal

A = "/Game/FoA/Audio/MetaSounds/"
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
BY_KEY = {  # InteractionKey -> {State: sound}
    "Door": {"KeyJammed": "Door/S_Door_KeySnap", "PlateOff": "Props/S_Props_ScrewdriverRatchet",
             "LatchFree": "Door/S_Door_Unlock", "HandleOff": "Door/S_Door_Handle", "Open": "Door/S_Door_Open"},
    "CommodeDrawer": {"Open": "Drawer/S_Drawer_Open", "Closed": "Drawer/S_Drawer_Close"},
    "WardrobeDoor": {"Open": "Wardrobe/S_Wardrobe_DoorOpen", "Closed": "Wardrobe/S_Wardrobe_DoorClose"},
    "Wardrobe": {"Falling": "Wardrobe/S_Wardrobe_Fall", "Fallen": "Wardrobe/S_Wardrobe_Impact",
                 "SearchWardrobeChecked": "Wardrobe/S_Wardrobe_Creak"},  # level1 2026-11-17: the T7 clues (t7_clue_sounds.py)
    "Desk": {"Open": "Drawer/S_Drawer_Slide", "Closed": "Drawer/S_Drawer_Stop", "Searched": "Props/S_Props_PaperRustle",
             "SearchDeskChecked": "Props/S_Props_PaperRustle"},
    "Bed": {"ClothingSnag": "Foley/S_Foley_Reach", "ClothingFreed": "Props/S_Props_HangerRail"},
    "Boot_L": {"Searched": "Props/S_Props_BootPickup", "Worn": "Props/S_Props_BootPickup"},
    "Key": {"Taken": "Props/S_Props_KeyPickup"},
    "Screwdriver": {"Taken": "Props/S_Props_Screwdriver"},
    "Hanger": {"Taken": "Props/S_Props_KeyPickup"},
    "Shirt": {"Taken": "Props/S_Props_ShirtPickup", "ChaseMoving": "Foley/S_Foley_ClothTurn"},
}
BURSTS = {  # InteractionKey -> {State: sand burst scale} (look's BPL_SandFX.SpawnSandBurst, via PlayFeedback)
    "Wardrobe": {"Fallen": 1.6}, "Door": {"KeyJammed": 0.5, "HandleOff": 0.8},
    "Key": {"Taken": 0.4}, "Hanger": {"Taken": 0.4}, "Shirt": {"Taken": 1.0},
}
AMBIENCE = {  # label -> (sound, location, attenuate). Room tone is 2D (no attenuation); the others sit at their source.
    "Amb_RoomTone": ("Ambience/S_Ambience_RoomTone_Loop_01", unreal.Vector(0, 0, 150), False),
    "Amb_NightWind": ("Ambience/S_Ambience_NightWind_Loop_01", unreal.Vector(-60, -380, 150), True),
    "Amb_ClockTick": ("Clock/S_Clock_Tick_Loop_01", None, True),  # at WallClock
}


def snd(rel):
    s = unreal.load_asset(A + rel)
    assert s, rel
    return s


def interactables():
    base = unreal.load_class(None, "/Game/FoA/Gameplay/BP_Interactable.BP_Interactable_C")
    return [a for a in EAS.get_all_level_actors() if unreal.MathLibrary.class_is_child_of(a.get_class(), base)]


def main():
    acts = interactables()
    if os.environ.get("FOA_STEP") == "list":
        for a in acts:
            print("IA", a.get_actor_label(), str(a.get_editor_property("InteractionKey")), str(a.get_editor_property("State")))
        return
    done = []
    for a in acts:
        key = str(a.get_editor_property("InteractionKey"))
        if key in BY_KEY:
            a.set_editor_property("StateSounds", {unreal.Name(k): snd(v) for k, v in BY_KEY[key].items()})
            done.append(a.get_actor_label())
        if key in BURSTS:
            a.set_editor_property("BurstStates", {unreal.Name(k): v for k, v in BURSTS[key].items()})
    labels = {a.get_actor_label(): a for a in EAS.get_all_level_actors()}
    for label, (rel, loc, attenuate) in AMBIENCE.items():
        if label in labels:
            continue
        if loc is None:
            loc = labels["WallClock"].get_actor_location()
        amb = EAS.spawn_actor_from_class(unreal.AmbientSound, loc, unreal.Rotator(0, 0, 0))
        amb.set_actor_label(label)
        amb.set_folder_path("Audio")
        c = amb.audio_component
        c.set_editor_property("sound", snd(rel))
        c.set_editor_property("auto_activate", True)
        c.set_editor_property("allow_spatialization", attenuate)
        if attenuate:
            c.set_editor_property("attenuation_settings", unreal.load_asset("/Game/FoA/Audio/Mix/ATT_SFX_Room"))
        done.append(label)
    print("FOA_SOUNDS", done)


main()
