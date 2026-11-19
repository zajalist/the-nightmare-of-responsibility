"""level1 lane, sweep (2026-11-18): in LS_BattleIntro's first-person shot (01_WontCome, a camera at his eye 15 cm in
front of his head) the view whip-pans back over his shoulder after the dragged shirt, so from 1.0 s to the cut at
2.2 s the lens looks through his own head, arm and shirt (run_20261118_1517 L1S8, frames 52 to 60). A Visibility
track on the Player binding hides him only for that stretch (visible 0 to 1.0 s, hidden 1.0 to 2.2 s, visible from the
cut to the room); RESTORE_STATE, so a stopped or skipped intro leaves him visible. Both LS_BattleIntro and
LS_BattleIntro_Short (the same cut). Idempotent (replaces its own track each run).
  $env:FOA_AREAS='/Game/FoA/Cinematics/BattleIntro'; python Tools/Unreal/ue_remote.py Tools/Unreal/level1/intro_hide_in_whip.py"""
import unreal

HIDE0, HIDE1 = 1.0, 2.2
out = []
for name in ('LS_BattleIntro', 'LS_BattleIntro_Short'):
    seq = unreal.load_asset('/Game/FoA/Cinematics/BattleIntro/' + name)
    unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(seq)
    r = seq.get_tick_resolution()
    tps = r.numerator / r.denominator
    b = next(x for x in seq.get_bindings() if str(x.get_display_name()) == 'Player')
    for t in list(b.get_tracks()):
        if t.get_class().get_name() == 'MovieSceneVisibilityTrack':
            b.remove_track(t)
    sec = b.add_track(unreal.MovieSceneVisibilityTrack).add_section()
    sec.set_range_seconds(0.0, seq.get_playback_end_seconds())
    sec.set_completion_mode(unreal.MovieSceneCompletionMode.RESTORE_STATE)
    ch = sec.get_all_channels()[0]
    for t, visible in ((0.0, True), (HIDE0, False), (HIDE1, True)):
        ch.add_key(unreal.FrameNumber(int(round(t * tps))), visible, 0.0, unreal.MovieSceneTimeUnit.TICK_RESOLUTION)
    assert unreal.EditorAssetLibrary.save_loaded_asset(seq, False)
    out.append((name, round(seq.get_playback_end_seconds(), 2), len(ch.get_keys())))
print('INTRO_HIDE', out)
