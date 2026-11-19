"""level1 lane (the user: "the animation with the wardrobe falling is still broken, the main character is glitching and
moving about the whole time, at one point he falls then he is back up"). Measured per frame in PIE (plan L1WF,
run_20261118_1320): LS_WardrobeFall's Player binding used CONSTANT keys (a 124 deg turn in one frame, then 22 cm and
33 cm jumps), its 0.83 s knockback ran in a 1.4 s section so it looped (down, up, down), and every clip section was
RESTORE_STATE, so when the director stops the sequence at the impact (WardrobeFallDone, 3.15 s) he snapped up to the
AnimBP's standing idle. This re-keys only the Player binding (cameras, audio and the rest are untouched):
  transform  LINEAR at tick resolution: the turn to the wardrobe takes 0.5 s, then while the knockback throws him
             (2.05 to 2.35 s, the airborne frames) he slides 30 cm and twists to lie along the door wall (yaw 90),
             clear of the fallen wardrobe, the nightstand and the door.
  clips      idle, then UAL_Hit_Knockback (0.83 s, he lands on his back; 0.1 s ease from the idle), then
             UAL_LayToIdle's first frame held (the knockback's last frame and that frame match within 5 cm). All
             KEEP_STATE, so he stays down after the stop; the director's WardrobeVanish (4.15 s, hidden) hands the mesh
             back to the AnimBP and plays AM_FoA_WakeUp (wardrobe_fall_getup.py): he re-forms lying and gets up.
Idempotent (re-keys and re-clips each run).
  $env:FOA_AREAS='/Game/FoA/Cinematics/Wardrobe'; python Tools/Unreal/ue_remote.py Tools/Unreal/level1/wardrobe_fall_smooth.py"""
import unreal

_src = open('P:/FoA/Tools/Unreal/flow/build_battle_intro.py', encoding='utf-8').read().rsplit('\nmain()', 1)[0]
exec(_src)  # noqa: S102  transform_track, yaw_to, LIN, UAL (the builder's own helpers)
END = 5.4                                    # transform_track reads END for the section range
FALL0, THROW0, THROW1, DOWN = 2.0, 2.05, 2.35, 2.83   # the knockback clip is 0.83 s; frames 2..10 are airborne
# z 87.15 is his measured standing height (the old 92 floated him 5 cm). He lands with his head about 90 cm behind the
# root, at (342, 18): 36 cm short of the nightstand and, from the side camera, no longer behind its corner.
D0, LAND = (330.0, 80.0, 87.15), (342.0, 108.0, 87.15)
TOP = (224.0, 236.0, 205.0)
EASE = 0.1

seq = unreal.load_asset('/Game/FoA/Cinematics/Wardrobe/LS_WardrobeFall')
unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(seq)
_r = seq.get_tick_resolution()
TPS = _r.numerator / _r.denominator


def key(ch, t, v, interp=LIN):  # transform_track calls this; tick keys so nearby times never share a frame
    ch.add_key(unreal.FrameNumber(int(round(t * TPS))), v, 0.0, unreal.MovieSceneTimeUnit.TICK_RESOLUTION, interp)


def ease(sec, t_in, t_out):  # durations in tick-resolution frames (the section's own unit)
    sec.set_ease_in_duration(int(round(t_in * TPS)))
    sec.set_ease_out_duration(int(round(t_out * TPS)))


face = yaw_to(D0, TOP)
b = next(x for x in seq.get_bindings() if str(x.get_display_name()) == 'Player')
transform_track(b, [(0.0, D0, (0.0, 0.0, 0.0)), (0.6, D0, (0.0, 0.0, 0.0)), (1.1, D0, (0.0, face, 0.0)),
                    (THROW0, D0, (0.0, face, 0.0)), (THROW1, LAND, (0.0, 90.0, 0.0)), (END, LAND, (0.0, 90.0, 0.0))],
                LIN, keep=True)
mesh = next(c for c in seq.get_bindings() if c.get_parent().is_valid() and c.get_parent().get_id() == b.get_id()
            and any(t.get_class().get_name() == 'MovieSceneSkeletalAnimationTrack' for t in c.get_tracks()))
track = next(t for t in mesh.get_tracks() if t.get_class().get_name() == 'MovieSceneSkeletalAnimationTrack')
for sec in list(track.get_sections()):
    track.remove_section(sec)
for row, (clip, t0, t1, rate, e_in, e_out) in enumerate((
        ('UAL_Idle_Loop', 0.0, FALL0 + EASE, 1.0, 0, EASE),
        ('UAL_Hit_Knockback', FALL0, DOWN, 1.0, EASE, 0),
        ('UAL_LayToIdle', DOWN, END, 0.001, 0, 0))):      # rate 0.001: its first frame, held
    sec = track.add_section()
    sec.set_row_index(row)
    prm = sec.get_editor_property('params')
    prm.set_editor_property('animation', unreal.load_asset(UAL + clip))
    prm.set_editor_property('force_custom_mode', True)
    pr = prm.get_editor_property('play_rate')  # 5.5+: a MovieSceneTimeWarpVariant, not a float
    pr.set_fixed_play_rate(rate)
    prm.set_editor_property('play_rate', pr)
    sec.set_editor_property('params', prm)
    sec.set_range_seconds(t0, t1)
    ease(sec, e_in, e_out)
    sec.set_completion_mode(unreal.MovieSceneCompletionMode.KEEP_STATE)
assert unreal.EditorAssetLibrary.save_loaded_asset(seq, False)
got = [(s.get_editor_property('params').get_editor_property('animation').get_name(), round(s.get_start_frame_seconds(), 2),
        round(s.get_end_frame_seconds(), 2), str(s.get_completion_mode()).split(':')[0]) for s in track.get_sections()]
got.sort(key=lambda g: g[1])
assert [g[0] for g in got] == ['UAL_Idle_Loop', 'UAL_Hit_Knockback', 'UAL_LayToIdle'], got
print('FALL_SMOOTH', got)
