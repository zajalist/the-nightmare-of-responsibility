"""Audio lane data: which waves each playable MetaSound preset randomises over, its class and attenuation.
Shared by audio_presets.py (builds them), import_waves.py (needed waves) and the wiring lists sent to the other lanes.
Pure data, no unreal import. Waves that don't exist yet are skipped by the builder with a warning.
Template (Mono/Stereo) is picked from the waves' channel count; *_Loop_* presets loop."""
MIX = '/Game/FoA/Audio/Mix/'
CLASS = {k: MIX + 'SC_' + k for k in ('SFX', 'Ambience', 'UI', 'Dialogue', 'Music')}
ATT = {'Near': MIX + 'ATT_SFX_Near', 'Room': MIX + 'ATT_SFX_Room'}


def takes(prefix, n, start=1):
    return [f'SFX_{prefix}_{i:02d}' for i in range(start, start + n)]


def one(name):
    return [f'SFX_{name}']


PRESETS = {
    # player: footsteps (BPL_FoAAudio.PlayFootstep picks one by surface and gear), foley, breathing
    'S_Footsteps_SocksWood': {'waves': takes('Footsteps_SocksWood', 3) + takes('Footsteps_WoodWalkSoft', 4), 'att': 'Near'},
    'S_Footsteps_BootsWood': {'waves': takes('Footsteps_BootsWood', 6), 'att': 'Near'},
    'S_Footsteps_DressShoeWood': {'waves': takes('Footsteps_DressShoeWood', 6), 'att': 'Near'},
    'S_Footsteps_SocksRug': {'waves': takes('Footsteps_SocksRug', 5), 'att': 'Near'},
    'S_Footsteps_BootsRug': {'waves': takes('Footsteps_BootsRug', 5), 'att': 'Near'},
    'S_Footsteps_WoodJog': {'waves': takes('Footsteps_WoodJog', 6), 'att': 'Near'},
    'S_Footsteps_WoodSneak': {'waves': takes('Footsteps_WoodSneak', 2), 'att': 'Near'},
    'S_Foley_ClothMove': {'waves': takes('Foley_ClothMove', 6), 'att': 'Near'},
    'S_Foley_ClothTurn': {'waves': takes('Foley_ClothTurn', 3), 'att': 'Near'},
    'S_Foley_Reach': {'waves': takes('Foley_Reach', 3), 'att': 'Near'},
    'S_Foley_Crouch': {'waves': takes('Foley_Crouch', 3), 'att': 'Near'},
    'S_Breath_TiredIdle_Loop_01': {'waves': one('Breath_TiredIdle_Loop_01'), 'att': 'Near'},
    'S_Breath_Effort': {'waves': takes('Breath_Effort', 5), 'att': 'Near'},
    'S_Breath_Panic_Loop_01': {'waves': one('Breath_Panic_Loop_01')},
    # interactions
    'S_Props_HangerRail': {'waves': takes('Props_HangerRail', 3), 'att': 'Near'},
    'S_Props_ScrewTurn': {'waves': takes('Props_ScrewTurn', 4), 'att': 'Near'},
    'S_Props_ScrewDrop': {'waves': takes('Props_ScrewDrop', 4), 'att': 'Near'},
    'S_Props_PaperRustle': {'waves': takes('Props_PaperRustle', 4) + takes('Props_BookPage', 3), 'att': 'Near'},
    'S_Props_ShirtPickup': {'waves': takes('Props_ShirtPickup', 2) + one('Bed_Sheets_01'), 'att': 'Near'},
    'S_Props_KeyDrop': {'waves': takes('Props_KeyDrop', 3), 'att': 'Near'},
    'S_Props_VaseBreak': {'waves': takes('Props_VaseBreak', 3), 'att': 'Room'},  # the vase-boss scene (world lane)
    # the key snapping (Door StateSounds KeyJammed): make_key_snap.py's layered takes; _01.._05 were thin clicks. 2D: the
    # door's PlayFeedback plays it at the actor origin (the floor hinge, 1.2 m from the keyhole), where the room
    # attenuation's occlusion muffled it; the key is in the player's hands, centred in front of the listener anyway
    'S_Door_KeySnap': {'waves': takes('Door_KeySnap', 3, start=6)},
    'S_Door_LatchSlide': {'waves': takes('Door_LatchSlide', 2), 'att': 'Near'},
    'S_Door_HandleOff': {'waves': takes('Door_HandleOff', 2), 'att': 'Near'},
    'S_Door_FinalOpen': {'waves': one('Door_FinalOpen_01'), 'att': 'Room'},
    'S_Door_Close': {'waves': takes('Door_Close', 5), 'att': 'Room'},
    'S_Drawer_Open': {'waves': takes('Drawer_Open', 2) + ['SFX_Drawer_Slide_01', 'SFX_Drawer_Slide_03', 'SFX_Drawer_Slide_05'],
                      'att': 'Near'},
    'S_Drawer_Close': {'waves': takes('Drawer_Close', 2) + takes('Drawer_Small', 2), 'att': 'Near'},
    'S_Drawer_Slide': {'waves': takes('Drawer_Slide', 6), 'att': 'Near'},
    'S_Drawer_Stop': {'waves': takes('Drawer_Small', 3), 'att': 'Near'},
    'S_Wardrobe_Rattle': {'waves': takes('Wardrobe_Rattle', 2) + one('Wardrobe_Wobble_01'), 'att': 'Room'},
    'S_Wardrobe_Creak': {'waves': one('Wardrobe_DoorCreak_01'), 'att': 'Room'},
    'S_Wardrobe_Debris': {'waves': takes('Wardrobe_Debris', 3), 'att': 'Room'},
    # the T0 alarm: the phone buzzing against the nightstand top (story plays it at the phone, ~0.5 s before it rises)
    'S_Phone_NightstandBuzz': {'waves': takes('Phone_NightstandBuzz', 2), 'att': 'Room'},
    'S_Door_Move': {'waves': takes('Creaks_Groan', 3), 'att': 'Room'},  # T7: the door frame dragged to the west wall
    # room ambience
    'S_Ambience_RainOnGlass_Loop_01': {'waves': one('Ambience_RainOnGlass_Loop_01'), 'cls': 'Ambience', 'att': 'Room'},
    'S_Ambience_DistantCity_Loop_01': {'waves': one('Ambience_DistantCity_Loop_01'), 'cls': 'Ambience', 'att': 'Room'},
    'S_Ambience_Radiator_Loop_01': {'waves': one('Ambience_Radiator_Loop_01'), 'cls': 'Ambience', 'att': 'Near'},
    'S_Ambience_Outside_Loop_01': {'waves': one('Ambience_Outside_Loop_01'), 'cls': 'Ambience', 'att': 'Room'},
    'S_Creaks_Settle': {'waves': takes('Creaks_Settle', 3) + takes('Creaks_Groan', 3) + takes('Creaks_Board', 3)
                        + takes('Creaks_Wood', 4), 'cls': 'Ambience', 'att': 'Room'},
    'S_Creaks_Floor': {'waves': takes('Creaks_Floor', 5), 'att': 'Near'},
    'S_Clock_TickFast_Loop_01': {'waves': one('Clock_TickFast_Loop_01'), 'att': 'Room'},
    # sand and the Nightmare
    'S_Sand_Hiss_Loop_01': {'waves': one('Sand_Hiss_Loop_01'), 'att': 'Room'},
    'S_Sand_Trickle_Loop_01': {'waves': one('Sand_Trickle_Loop_01'), 'att': 'Room'},
    'S_Sand_Crumble': {'waves': takes('Sand_Crumble', 2), 'att': 'Near'},
    'S_Sand_Shift': {'waves': takes('Sand_Shift', 5), 'att': 'Room'},
    'S_Sand_Pour': {'waves': takes('Sand_Pour', 4), 'att': 'Room'},
    'S_Sand_Burst': {'waves': takes('Sand_Burst', 3), 'att': 'Room'},
    'S_Sand_Footstep': {'waves': takes('Sand_Footstep', 6), 'att': 'Near'},  # BPL_SandFX.SpawnSandStep (sand lane)
    'S_Horror_Presence_Loop_01': {'waves': one('Horror_Presence_Loop_01'), 'att': 'Room'},
    # story moments (2D)
    'S_Story_HeadPressure': {'waves': one('Story_HeadPressure_01')},
    'S_Story_HeadRing': {'waves': one('Story_HeadRing_01')},
    'S_Story_TimeShift': {'waves': takes('Story_TimeShift', 2)},
    'S_Story_SuitTone': {'waves': one('Story_SuitTone_01')},
    'S_Dream_Heartbeat_Loop_01': {'waves': one('Dream_Heartbeat_Loop_01')},
    'S_Dream_Gasp': {'waves': one('Dream_Gasp_01'), 'att': 'Near'},  # the startle (AM_FoA_Startle) and the jumpscare release
    'S_Dream_ReverseSwell': {'waves': takes('Dream_ReverseSwell', 4)},
    'S_Dream_TapeStop': {'waves': takes('Dream_TapeStop', 2)},
    # battle (2D)
    'S_Battle_ClothSnap': {'waves': takes('Battle_ClothSnap', 4)},
    'S_Battle_Button': {'waves': takes('Battle_Button', 4)},
    'S_Battle_Zipper': {'waves': takes('Battle_Zipper', 3)},
    'S_Battle_FabricWhoosh': {'waves': takes('Battle_FabricWhoosh', 4)},
    # the fight's hit set (make_battle_sfx.py, CC0/PD): 2D like the rest of the battle cues
    'S_Battle_GarmentHit': {'waves': takes('Battle_GarmentHit', 4)},
    'S_Battle_PlayerHit': {'waves': takes('Battle_PlayerHit', 4)},
    'S_Battle_TelegraphCloth': {'waves': takes('Battle_TelegraphCloth', 2)},
    'S_Battle_TelegraphElastic': {'waves': takes('Battle_TelegraphElastic', 2)},
    'S_Battle_TelegraphKnot': {'waves': takes('Battle_TelegraphKnot', 2)},
    'S_Battle_Stun': {'waves': takes('Battle_Stun', 2)},
    'S_Battle_Defeat': {'waves': takes('Battle_Defeat', 2)},
    'S_Battle_Victory': {'waves': takes('Battle_Victory', 1)},
    'S_Battle_Worn': {'waves': takes('Battle_Worn', 2)},
    'S_Battle_SwordClash': {'waves': takes('Battle_SwordClash', 4)},  # the user's Plevne march (their pick)
    'S_Battle_Select': {'waves': takes('Battle_Select', 2), 'cls': 'UI'},
    'S_Battle_Confirm': {'waves': takes('Battle_Confirm', 2), 'cls': 'UI'},
    'S_Battle_ComposureLow_Loop_01': {'waves': one('Battle_ComposureLow_Loop_01')},
}


def all_waves():
    return sorted({w for spec in PRESETS.values() for w in spec['waves']})
