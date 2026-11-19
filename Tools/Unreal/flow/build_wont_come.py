"""LS_BattleIntro (and LS_BattleIntro_Short, the same cut) rebuilt as "It won't come" (the user's pick A, 2026-11-10):
the vase-to-battle transition, first person, no fade. Reuses build_battle_intro.py's track helpers.
  0.0  first person at the sill, his hands on the shirt: it pulls back twice (a sleeve caught on the sill vase)
  0.8  the vase tips and shatters (director cue BI_FX_Vase -> RoomTakeover.BreakVaseOnly, world's shatter and pour)
  0.95 black sand pours over the shirt and drags it off across the floor; the view whip-pans after it (no cut)
  2.2  the shirt sinks into the mound at Encounter_T8; cut to the room from behind the line's right, dollying out to
       the battle camera's own framing while he hurries after it to his mark
  3.2  BattleIntroDone: the encounter starts on that exact framing (a cut onto the same picture), the garments fly in
       from where he has seen them (BP_Encounter.IntroSources), then "Get dressed." / "Okay. Shirt first." (director
       timers; the short version, a replay, says "Again. Shirt first.")
The sequence holds its last frame 0.3 s longer than the cue, so the director stops it while it still owns the view.
  $env:HAYBA_AGENT_ID='story'; $env:FOA_AREAS='/Game/FoA/Cinematics/BattleIntro'
  python Tools/Unreal/ue_remote.py Tools/Unreal/flow/build_wont_come.py [FOA_VERSION=full|short]"""
import os

_src = open('P:/FoA/Tools/Unreal/flow/build_battle_intro.py', encoding='utf-8').read().rsplit('\nmain()', 1)[0]
exec(_src)  # noqa: S102  the helpers (camera, garment, player, mesh_actor, audio, cuts, main ...)

CUE = 3.2           # BattleIntroDone (patch_wont_come.py)
END = CUE + 0.3     # the last frame is held while the director hands over
NAME = 'LS_BattleIntro' if VERSION == 'full' else 'LS_BattleIntro_Short'
S0 = (-55.0, -335.0, 20.0)     # the shirt on the bay floor below the sill vase (clothing_chase_contract LANDINGS[2])
H = (-41.0, -263.0, 92.0)      # where he stands for the final grab (QA B2b, 2026-11-10)
EYE = (-46.0, -277.0, 158.0)   # his eye, 15 cm forward so the head stays out of the lens
MOUND_AT = (-200.0, -55.0, 0.0)
MARK = (60.0, -55.0, 92.0)
STEP0 = (-20.0, -215.0, 92.0)  # first step after the shirt
BATTLE_CAM = (275.0, -135.0, 180.0)   # BP_Encounter's battle camera as ShowEncounter frames it (battle_view.json)
BATTLE_AIM = (-120.0, -55.0, 110.0)   # 168.6 yaw, -9.9 pitch, 65 deg horizontal = 28.3 mm on 36 mm film
SHIRT_ANIM = 'SK_Garment_ShirtArmature_Idle_Anim'


def ease(t):
    return t * t * (3 - 2 * t)


def drag(t):
    """the shirt's place while the sand drags it, t in [0.95, 2.2]"""
    a = ease(min(1.0, max(0.0, (t - 0.95) / 1.25)))
    p = lerp(S0, (MOUND_AT[0] + 5.0, MOUND_AT[1] - 5.0, 15.0), a)
    return p


def wont_come(seq):
    gy = yaw_to(S0, MOUND_AT) - 90.0
    # first person: on the shirt, the vase, then after the shirt
    fp = [(0.0, EYE, S0), (0.75, EYE, (-45.0, -350.0, 45.0)), (0.9, EYE, (-30.0, -368.0, 70.0)), (1.0, EYE, drag(1.0))]
    fp += [(t, EYE, drag(t)) for t in (1.25, 1.5, 1.75, 2.0, 2.2)]
    cams = [camera(seq, '01_WontCome', fp, 24.0, (0.0, 2.2)),
            camera(seq, '02_IntoTheLine', [(2.2, (215.0, -118.0, 176.0), BATTLE_AIM), (CUE, BATTLE_CAM, BATTLE_AIM),
                                           (END, BATTLE_CAM, BATTLE_AIM)], 28.3, (2.2, END))]
    tug = [(0.0, S0), (0.25, (-50.0, -318.0, 26.0)), (0.45, S0), (0.65, (-51.0, -321.0, 25.0)), (0.8, S0), (0.95, S0)]
    keys = [(t, p, (0.0, gy, 0.0)) for t, p in tug]
    keys += [(t, drag(t), (0.0, gy, 0.0)) for t in (1.2, 1.5, 1.8, 2.05)]
    keys += [(2.25, (MOUND_AT[0], MOUND_AT[1], -45.0), (0.0, gy, 0.0))]
    garment(seq, 'Shirt', 'SK_Garment_Shirt', SHIRT_ANIM, keys, [(0.0, (1.2, 1.2, 1.2))], 0.0, 2.3)
    for i, (a, b0, t0) in enumerate(((0.0, 0.35, 0.95), (0.35, 0.7, 1.3), (0.7, 1.0, 1.65))):
        pa, pb = drag(0.95 + 1.25 * a), drag(0.95 + 1.25 * b0)
        mid = lerp(pa, pb, 0.5)
        mesh_actor(seq, 'Stream%d' % (i + 1), PATH_SPILL, MOUND_MI,
                   [(t0, (mid[0], mid[1], 0.5), (0.0, yaw_to(pa, pb), 0.0)), (END, (mid[0], mid[1], 0.5), (0.0, yaw_to(pa, pb), 0.0))],
                   [(t0, (0.05, 0.3, 0.2)), (t0 + 0.4, (1.0, 0.7, 1.4))], t0, END)
    mesh_actor(seq, 'Mound', MOUND, MOUND_MI, [(1.5, MOUND_AT, (0.0, 90.0, 0.0)), (END, MOUND_AT, (0.0, 90.0, 0.0))],
               [(1.5, (0.15, 0.15, 0.05)), (2.4, (0.6, 0.8, 0.4))], 1.5, END)
    face = yaw_to(H, S0)
    walk = yaw_to(STEP0, MARK)
    # level1 2026-11-18: these CONSTANT keys pop him 20 cm every 0.1 s (the user's pre-boss "teleports"). After this
    # builder, run Tools/Unreal/level1/intro_smooth_walk.py: it re-keys this track LINEAR (hold, one step under the
    # cut, a continuous walk to the mark).
    player(seq, [(0.0, H, (0.0, face, 0.0)), (2.2, STEP0, (0.0, walk, 0.0))] +
           [(2.2 + 0.1 * i, lerp(STEP0, MARK, i / 9.0), (0.0, walk if i < 8 else 180.0, 0.0)) for i in range(10)],
           [('UAL_Idle_Loop', 0.0, 2.2), ('UAL_Walk_Formal_Loop', 2.2, 3.1), ('UAL_Idle_Loop', 3.1, END)])
    missing = audio(seq, [
        (MS + 'Breath/S_Breath_Effort', 0.15, 1.0, 0.8),
        (MS + 'Battle/S_Battle_ClothSnap', 0.25, 0.6, 0.8),
        (MS + 'Battle/S_Battle_ClothSnap', 0.65, 0.6, 1.0),
        (MS + 'Sand/S_Sand_Pour', 0.9, 1.6, 1.0),
        (MS + 'Battle/S_Battle_FabricWhoosh', 1.0, 1.0, 1.0),
        (MS + 'Sand/S_Sand_Hiss_Loop_01', 1.0, END - 1.0, 0.7),
        (MS + 'Horror/S_Horror_Presence_Loop_01', 1.2, END - 1.2, 0.5),
        (MS + 'Sand/S_Sand_Shift', 2.0, 1.2, 0.8),
        (MS + 'Footsteps/S_Footsteps_SocksWood', 2.4, 0.5, 0.8),
        (MS + 'Footsteps/S_Footsteps_SocksWood', 2.75, 0.5, 0.8),
    ])
    return cams, missing


full = short = wont_come  # the replay is the same cut; only the director's line differs
main()
