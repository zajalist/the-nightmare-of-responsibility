"""LS_WakeUp's timeline and audio cues, shared by the builders (through wake_common) and mux_audio.py. Engine-free.
v2 pacing (user feedback "too quick, too abrupt"): every beat is held, every move starts and ends on a hold.
Each cue: (SFX path under Audio/SFX without extension, start s, end s or None for the whole sound, volume, loop)."""

T = {
    "alarm_click": 2.2, "alarm": 2.3,
    "pov": 2.5,             # eyes open over about 2.7 s (blink, close, slow open)
    "pov_turn": 7.0,        # lantern held until here, then an eased head turn to the clock
    "pov_turn_end": 8.8,
    "bed": 9.8,             # held establishing beat: he lies still
    "situp": 11.3, "situp_end": 13.3,
    "edge": 19.7,           # v3 (cine): time shift under black into the bed-edge two-shot
    "edge_hold": 4.1, "edge_reach": 3.5, "edge_breath": 2.1, "exit_rate": 0.6,  # anticipation23.8, contact25.3, rest27.3, stand29.4
    "stand_pause": 1.5, "glide": 3.0, "handoff_blend": 1.5,
}


def times(edge_len):
    """Derived beat times for an edge clip of edge_len seconds."""
    t_stand = T["edge"] + T["edge_hold"] + T["edge_reach"] + T["edge_breath"]
    t_up = T["edge"] + edge_len
    t_glide = t_up + T["stand_pause"]
    t_settle = t_glide + T["glide"]
    return {"stand": t_stand, "up": t_up, "glide": t_glide, "settle": t_settle, "end": t_settle + T["handoff_blend"]}


def cues(T, grab_t, t_stand):
    return [("Clock/SFX_Clock_Tick_Loop_01", 0.0, T["alarm_click"], 0.35, True),
            ("Bed/SFX_Bed_Sheets_01", 1.2, None, 0.35, False),
            ("Clock/SFX_Clock_AlarmMechanism_01", T["alarm_click"], None, 0.8, False),
            ("Clock/SFX_Clock_AlarmRing_Loop_01", T["alarm"], grab_t, 0.9, True),
            ("Bed/SFX_Bed_Sheets_02", T["situp"] + 0.1, None, 0.6, False),
            ("Bed/SFX_Bed_Creak_02", T["situp"] + 0.05, None, 0.7, False),
            ("Dream/SFX_Dream_Whoosh_03", T["edge"] - 0.3, None, 0.6, False),
            ("Dream/SFX_Dream_TapeScrub_01", T["edge"] - 0.25, None, 0.35, False),
            ("Bed/SFX_Bed_Sit_01", T["edge"] + 0.02, None, 0.5, False),
            ("Sand/SFX_Sand_Pour_01", grab_t, None, 0.8, False),
            ("Sand/SFX_Sand_Shift_02", grab_t + 0.1, None, 0.5, False),
            ("Dream/SFX_Dream_Breath_Loop_01", t_stand - T["edge_breath"] + 0.3, t_stand, 0.4, False),
            ("Bed/SFX_Bed_GetUp_01", t_stand, None, 0.7, False),
            ("Creaks/SFX_Creaks_Floor_02", t_stand + 0.9, None, 0.4, False)]


def cues_v3(grab_t, edge_t=19.7, end=36.4):
    """LS_WakeUp v3's audio track (docs/cinematics/wakeup_shotlist.md, Sound), shared by build_ls_wakeup.py and
    mux_audio.py --v3. Each cue: (path, start, end or None, volume, loop, (fade-out start, fade-out end) or None)."""
    # The alarm rings until his palm lands on it (grab_t), then the clock is sand: the bell and the tick stop dead
    return [("Clock/SFX_Clock_Tick_Loop_01", 2.3, grab_t, 0.3, True, None),
            ("Clock/SFX_Clock_AlarmMechanism_01", 2.2, None, 0.8, False, None),
            ("Clock/SFX_Clock_AlarmRing_Loop_01", 2.3, grab_t, 0.7, True, None),
            ("UI_FrontEnd/SFX_FE_Eyelids_01", 3.0, None, 0.7, False, None),
            ("UI_FrontEnd/SFX_FE_Eyelids_02", 4.3, None, 0.6, False, None),
            ("Bed/SFX_Bed_Sheets_02", 6.4, None, 0.4, False, None),
            ("Dream/SFX_Dream_Whoosh_03", edge_t - 0.4, None, 0.6, False, None),
            ("Dream/SFX_Dream_TapeScrub_01", edge_t - 0.35, None, 0.35, False, None),
            ("Bed/SFX_Bed_Sit_01", edge_t + 0.02, None, 0.5, False, None),
            ("Sand/SFX_Sand_Pour_01", grab_t, None, 0.8, False, None),
            ("Sand/SFX_Sand_Shift_02", grab_t + 0.1, None, 0.5, False, None),
            ("Dream/SFX_Dream_Breath_Loop_01", 26.9, 29.4, 0.4, False, None),
            ("Bed/SFX_Bed_GetUp_01", 29.4, None, 0.7, False, None),
            ("Creaks/SFX_Creaks_Floor_02", 30.3, None, 0.4, False, None)]
