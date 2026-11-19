"""LS_WardrobeFall (story lane, the user's pick A, 2026-11-10): the wardrobe falls, first person, about 5.4 s, no
scatter, no vanish. Reuses build_battle_intro.py's track helpers. The wardrobe itself is not in the sequence: it falls by
its own row (Standing -> Falling on the door's Notify HandleOff, the director's 2 s rattle, the WardrobeBeginFall timer,
then the Pivot over 1.15 s), so the impact lands at 3.15 s and the cuts are timed to that (FALL0, IMPACT).
  0.0  first person at the door, the handle just came off in his hand; the creak rises behind him
  0.6  the view turns to the wardrobe (0.5 s): it leans, its doors chatter (the director's rattle)
  2.0  it tips toward him; he stumbles back (the view dips)
  2.3  low side shot from the bed's corner: it comes down across the way to the door, he scrambles clear, 3.15 impact
  3.8  first person on the floor by the door, looking at it lying there ("I'm fine. I'm fine. I'm fine." is its row line)
  4.8  he gets up; 5.4 control returns (the director's WardrobeFallDone)
  $env:HAYBA_AGENT_ID='story'; $env:FOA_AREAS='/Game/FoA/Cinematics/Wardrobe'
  python Tools/Unreal/ue_remote.py Tools/Unreal/flow/build_wardrobe_fall.py"""
_src = open('P:/FoA/Tools/Unreal/flow/build_battle_intro.py', encoding='utf-8').read().rsplit('\nmain()', 1)[0]
exec(_src)  # noqa: S102  helpers: camera, player, audio, cuts, lerp, yaw_to; main() is re-pointed below

FOLDER = '/Game/FoA/Cinematics/Wardrobe'
NAME = 'LS_WardrobeFall'
FALL0, IMPACT = 2.0, 3.15   # refine_wardrobe_scene.py: 2 s rattle, then MoveTime 1.15 s
END = 5.4                   # patch_wardrobe_fall.py times WardrobeFallDone to this
D0 = (330.0, 80.0, 92.0)    # where he pulls the door (the handle at (375, 60, 100))
EYE = (338.0, 80.0, 160.0)
HANDLE = (375.0, 62.0, 100.0)
TOP = (224.0, 236.0, 205.0)          # the wardrobe's upper front, standing
FALLEN_MID = (224.0, 63.0, 45.0)     # lying: pivot (224, 181, 0), the top lands near y -55
CLEAR = (352.0, 30.0, 92.0)          # where he scrambles to, by the door, clear of it
SIT_EYE = (356.0, 26.0, 105.0)


def wardrobe(seq):
    from wardrobe_camera_path import opening_keys
    fp = opening_keys()
    side_at, side_aim = (95.0, -150.0, 48.0), (290.0, 95.0, 85.0)
    cams = [camera(seq, '01_TheDoor', fp, 22.0, (0.0, FALL0 + 0.3)),
            camera(seq, '02_ItFalls', [(FALL0 + 0.3, side_at, side_aim), (IMPACT + 0.65, (100.0, -146.0, 46.0), side_aim)], 20.0,
                   (FALL0 + 0.3, IMPACT + 0.65)),
            camera(seq, '03_OnTheFloor', [(IMPACT + 0.65, SIT_EYE, FALLEN_MID), (4.7, (SIT_EYE[0], SIT_EYE[1], SIT_EYE[2] + 1.5), FALLEN_MID),
                                          (END, (CLEAR[0] - 4.0, CLEAR[1], 160.0), (224.0, 63.0, 80.0))], 24.0, (IMPACT + 0.65, END))]
    # level1 (2026-11-18): run Tools/Unreal/level1/wardrobe_fall_smooth.py after this builder; it re-keys the Player
    # binding (linear keys, the knockback once, then lying held) that these constant keys and clips made pop.
    face = yaw_to(D0, TOP)
    back = yaw_to(CLEAR, FALLEN_MID)
    player(seq, [(0.0, D0, (0.0, 0.0, 0.0)), (0.6, D0, (0.0, 0.0, 0.0)), (1.1, D0, (0.0, face, 0.0)), (FALL0, D0, (0.0, face, 0.0)),
                 (FALL0 + 0.4, lerp(D0, CLEAR, 0.4), (0.0, face, 0.0)), (IMPACT, CLEAR, (0.0, back, 0.0)), (END, CLEAR, (0.0, back, 0.0))],
           [('UAL_Idle_Loop', 0.0, FALL0), ('UAL_Hit_Knockback', FALL0, IMPACT + 0.25), ('UAL_Crouch_Idle_Loop', IMPACT + 0.25, 4.8),
            ('UAL_Idle_Loop', 4.8, END)])
    missing = audio(seq, [
        (MS + 'Breath/S_Breath_Effort', 0.1, 0.9, 0.6),
        (MS + 'Breath/S_Breath_Panic_Loop_01', FALL0, 1.6, 0.7),
        (MS + 'Footsteps/S_Footsteps_SocksWood', FALL0 + 0.2, 0.5, 0.9),
        (MS + 'Footsteps/S_Footsteps_SocksWood', FALL0 + 0.55, 0.5, 0.8),
        (MS + 'Breath/S_Breath_Effort', IMPACT + 0.5, 1.2, 0.7),
    ])
    return cams, missing


full = short = wardrobe
VERSION = 'full'
main()
