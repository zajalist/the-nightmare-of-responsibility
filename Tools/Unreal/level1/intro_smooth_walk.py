"""level1 lane (the user: "stutter before boss battle level 1, the player just teleports many times"): LS_BattleIntro
and LS_BattleIntro_Short move him with CONSTANT keys: a 52 cm pop at 2.2 s, then ten 20 cm pops every 0.1 s from
STEP0 to his mark (measured per tick in PIE, plan L1T3: ten moves with zero velocity). His Player track is re-keyed
LINEAR: he holds at the sill (H) until 2.2 s, takes the one unavoidable step to STEP0 on the same frame as the cut to
the room (hidden by the cut), then walks continuously to MARK by 3.1 s, turning onto the mark's yaw in the last 0.15 s.
Everything else in the sequences is untouched. Idempotent (re-keys the track each run).
  $env:FOA_AREAS='/Game/FoA/Cinematics/BattleIntro'; python Tools/Unreal/ue_remote.py Tools/Unreal/level1/intro_smooth_walk.py"""
import unreal

_src = open('P:/FoA/Tools/Unreal/flow/build_battle_intro.py', encoding='utf-8').read().rsplit('\nmain()', 1)[0]
exec(_src)  # noqa: S102  transform_track, lerp, yaw_to, LIN (the builder's own helpers)
END = 3.5   # build_wont_come.py: CUE 3.2 + 0.3
H, STEP0, MARK, S0 = (-41.0, -263.0, 92.0), (-20.0, -215.0, 92.0), (60.0, -55.0, 92.0), (-55.0, -335.0, 20.0)


def smooth_keys():
    face, walk = yaw_to(H, S0), yaw_to(STEP0, MARK)
    return [(0.0, H, (0.0, face, 0.0)), (2.2, H, (0.0, face, 0.0)),          # hold at the sill until the cut
            (2.2042, STEP0, (0.0, walk, 0.0)),                               # one step inside the cut's first 4 ms
            (2.95, lerp(STEP0, MARK, 0.85), (0.0, walk, 0.0)),               # walk, continuous
            (3.1, MARK, (0.0, 180.0, 0.0)), (END, MARK, (0.0, 180.0, 0.0))]  # onto the mark, facing the fight


def tick_key(ch, t, v, interp=LIN, _tr=[None]):  # noqa: B006  keys finer than the 30 fps display frames
    ch.add_key(unreal.FrameNumber(int(round(t * _tr[0]))), v, 0.0, unreal.MovieSceneTimeUnit.TICK_RESOLUTION, interp)


key = tick_key  # transform_track calls key(); the builder's own key() rounds to display frames (2.199 s == 2.2 s)
for name in ('LS_BattleIntro', 'LS_BattleIntro_Short'):
    seq = unreal.load_asset('/Game/FoA/Cinematics/BattleIntro/' + name)
    assert seq, name
    unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(seq)
    r = seq.get_tick_resolution()
    tick_key.__defaults__[1][0] = r.numerator / r.denominator
    b = next(x for x in seq.get_bindings() if str(x.get_display_name()) == 'Player')
    sec = transform_track(b, smooth_keys(), LIN, keep=True)
    xs = [k.get_time().frame_number.value for k in sec.get_all_channels()[0].get_keys()]
    assert unreal.EditorAssetLibrary.save_loaded_asset(seq, False), name
    print('SMOOTH', name, 'location X keys', len(xs))
