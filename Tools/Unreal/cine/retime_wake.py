"""Tighten LS_WakeUp in place by ripple-cutting time ranges (no rebuild: the user's pose edits and hand-set
flags such as the cut track's bCanBlend survive).
  $env:HAYBA_AGENT_ID='anim'; $env:FOA_AREAS='Cinematics'
  python Tools/Unreal/ue_remote.py Tools/Unreal/cine/retime_wake.py FOA_SEQ=/Game/FoA/Cinematics/LS_WakeUp
Rules per cut [a, b) (display frames, applied from the last cut to the first):
- keys in [a, b] collapse to a (the latest original key wins), keys after b move back by b - a;
- section edges map the same way, sections that end up empty are removed;
- a skeletal section that spans a cut is split, the right part's StartFrameOffset skips the cut clip time, and the two
  parts cross-fade over 4 frames. Loops/holds (AS_FoA_Wake_Lying, MM_Idle) shrink instead, so they stay continuous;
- MPC parameter keys were authored at tick numbers equal to display frames (all inside the first 0.05 s); they are
  re-keyed at those intended display frames.
Then: Cam_Wide, L3_BedKick and Cam_HandBack bindings are removed (the wide and the over-shoulder hand-back are cut),
the eyes open for the push-in with one slow blink, and the playback range ends at the new length.
Hand-off to first person: the stand shot holds, then a 6-frame blink to black ends the film (Fade Keep State 1.0) and
the Player's bHandoffFadeIn turns true; BP_FoAPlayer.SetCinematic(false) clears it and fades the head camera up, so
the camera never travels into his head (no camera-cut blend: the cut track's bCanBlend is turned off). Writes Saved/AnimShots/wake_retime.json."""
import json
import os
import shutil
import datetime
from pathlib import Path

import unreal

SEQ = os.environ.get('FOA_SEQ', '/Game/FoA/Cinematics/LS_WakeUp')
DU = unreal.MovieSceneTimeUnit.DISPLAY_RATE
TU = unreal.MovieSceneTimeUnit.TICK_RESOLUTION
# Old display frames (30 fps). See docs/cinematics/wakeup_shotlist.md (v4) for what each cut removes.
CUTS = [(6, 51), (165, 192), (258, 426), (460, 530), (612, 687), (835, 852), (975, 1092)]
CONTINUOUS = ('AS_FoA_Wake_Lying', 'MM_Idle')
XFADE = 4

seq = unreal.load_asset(SEQ)
assert seq, SEQ
assert unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world() is None, 'PIE running'
assert seq.get_playback_end() == 1092, ('already retimed?', seq.get_playback_end())
tick = seq.get_tick_resolution()
TPF = tick.numerator // tick.denominator // 30  # ticks per display frame (800)
log = dict(seq=SEQ, cuts=CUTS, splits=[], removed_sections=[], mpc=[], removed_bindings=[])


def mapf(f, a, b):
    if f < a:
        return f
    if f <= b:
        return a
    return f - (b - a)


def all_tracks():
    for t in seq.get_tracks():
        yield None, t
    for bnd in seq.get_bindings():
        for t in bnd.get_tracks():
            yield bnd, t


def channel_keys(sec, c, mpc):
    out = []
    for k in c.get_keys():
        f = k.get_time(TU).frame_number.value if mpc else k.get_time(DU).frame_number.value
        out.append((f, k))
    return out


def cut_keys(sec, a, b, mpc):
    for c in sec.get_all_channels():
        try:
            ks = channel_keys(sec, c, mpc)
        except Exception:
            continue
        landed = {}
        for f, k in sorted(ks, key=lambda x: x[0]):
            nf = mapf(f, a, b)
            if nf in landed:
                c.remove_key(landed[nf])
            landed[nf] = k
            if nf != f:
                k.set_time(unreal.FrameNumber(nf), 0.0, TU if mpc else DU)


def easing(sec):
    return sec.get_editor_property('easing').export_text()


def set_ease(sec, side, frames):
    es = sec.get_editor_property('easing')
    cap = 'In' if side == 'in' else 'Out'
    es.import_text('(bManualEase%s=True,ManualEase%sDuration=%d)' % (cap, cap, frames * TPF))
    sec.set_editor_property('easing', es)


def cut_section(track, sec, a, b):
    if not (sec.has_start_frame() and sec.has_end_frame()):
        return
    s, e = sec.get_start_frame(), sec.get_end_frame()
    skel = isinstance(sec, unreal.MovieSceneSkeletalAnimationSection)
    anim = sec.get_editor_property('params').animation.get_name() if skel else None
    ns, ne = mapf(s, a, b), mapf(e, a, b)
    if skel and s < a and e > b and anim not in CONTINUOUS:
        # split: left keeps [s, a), right plays from clip time (b - s) at sequence frame a
        p = sec.get_editor_property('params')
        off = p.get_editor_property('start_frame_offset').value
        right = track.add_section()
        right.set_row_index(sec.get_row_index())
        right.set_completion_mode(sec.get_completion_mode())
        rp = unreal.MovieSceneSkeletalAnimationParams()  # a fresh struct: params from get_editor_property alias the section's
        rp.import_text(p.export_text())
        rp.set_editor_property('start_frame_offset', unreal.FrameNumber(off + (b - s - XFADE // 2) * TPF))
        right.set_editor_property('params', rp)
        right.set_editor_property('easing', sec.get_editor_property('easing'))
        right.set_range(a - XFADE // 2, e - (b - a))
        set_ease(right, 'in', XFADE)
        sec.set_range(s, a + XFADE // 2)
        set_ease(sec, 'out', XFADE)
        log['splits'].append(dict(anim=anim, left=[s, a + XFADE // 2], right=[a - XFADE // 2, e - (b - a)],
                                  right_offset_frames=off / TPF + b - s - XFADE // 2))
        return
    if ne <= ns:
        log['removed_sections'].append(dict(cls=sec.get_class().get_name(), range=[s, e]))
        track.remove_section(sec)
        return
    if skel and a <= s < b:  # starts inside the cut: skip the cut clip time
        p = sec.get_editor_property('params')
        off = p.get_editor_property('start_frame_offset').value
        p.set_editor_property('start_frame_offset', unreal.FrameNumber(off + (b - s) * TPF))
        sec.set_editor_property('params', p)
    sec.set_range(ns, ne)


def apply_cut(a, b):
    for bnd, t in list(all_tracks()):
        for sec in list(t.get_sections()):
            cut_keys(sec, a, b, False)  # MPC keys are already display-rate (to_display_mpc runs first)
            cut_section(t, sec, a, b)


def to_display_mpc():
    """MPC keys sit at tick == intended display frame; move each to its intended display frame."""
    for t in seq.get_tracks():
        if t.get_class().get_name() != 'MovieSceneMaterialParameterCollectionTrack':
            continue
        for sec in t.get_sections():
            for c in sec.get_all_channels():
                ks = sorted(((k.get_time(TU).frame_number.value, k) for k in c.get_keys()), key=lambda x: -x[0])
                for f, k in ks:  # latest first, so a key never lands on one still to be moved
                    k.set_time(unreal.FrameNumber(f), 0.0, DU)
                log['mpc'].append([str(t.get_display_name()), str(c.channel_name),
                                   [(f, round(k.get_value(), 3)) for f, k in sorted(ks, key=lambda x: x[0])]])


def remove_binding(name):
    for bnd in list(seq.get_bindings()):
        par = bnd.get_parent()
        if str(bnd.get_display_name()) == name or (par and par.get_id() != bnd.get_id() and str(par.get_display_name()) == name):
            log['removed_bindings'].append(str(bnd.get_display_name()) + ('<' + name if str(bnd.get_display_name()) != name else ''))
    kids = [bd for bd in seq.get_bindings() if bd.get_parent() and bd.get_parent().get_id() != bd.get_id()
            and str(bd.get_parent().get_display_name()) == name]
    for bd in kids:
        bd.remove()
    for bd in list(seq.get_bindings()):
        if str(bd.get_display_name()) == name:
            bd.remove()


def eyes():
    """Push-in: heavy-lidded but open (0.2), one slow blink; closed again under the dip, open after the sit."""
    pl = next(bd for bd in seq.get_bindings() if str(bd.get_display_name()) == 'Player')
    tr = next(t for t in pl.get_tracks() if t.get_class().get_name() == 'MovieSceneFloatTrack'
              and str(t.get_property_name()) == 'SleepEyeClosure')
    c = tr.get_sections()[0].get_all_channels()[0]
    for k in list(c.get_keys()):
        c.remove_key(k)
    for f, v in [(0, 1.0), (185, 1.0), (186, 0.2), (222, 0.2), (226, 1.0), (231, 1.0), (240, 0.2), (268, 0.2),
                 (281, 1.0), (302, 0.0)]:
        c.add_key(unreal.FrameNumber(f), v, 0.0, DU, unreal.MovieSceneKeyInterpolation.AUTO)


def handoff(end):
    fade = next(t for t in seq.get_tracks() if t.get_class().get_name() == 'MovieSceneFadeTrack')
    c = fade.get_sections()[0].get_all_channels()[0]
    for k in list(c.get_keys()):
        if k.get_time(DU).frame_number.value >= end - 6:
            c.remove_key(k)
    c.add_key(unreal.FrameNumber(end - 6), 0.0, 0.0, DU, unreal.MovieSceneKeyInterpolation.AUTO)
    c.add_key(unreal.FrameNumber(end), 1.0, 0.0, DU, unreal.MovieSceneKeyInterpolation.AUTO)
    fade.get_sections()[0].set_completion_mode(unreal.MovieSceneCompletionMode.KEEP_STATE)
    pl = next(bd for bd in seq.get_bindings() if str(bd.get_display_name()) == 'Player')
    for t in list(pl.get_tracks()):
        if t.get_class().get_name() == 'MovieSceneBoolTrack' and str(t.get_property_name()) == 'bHandoffFadeIn':
            pl.remove_track(t)
    tr = pl.add_track(unreal.MovieSceneBoolTrack)
    tr.set_property_name_and_path('bHandoffFadeIn', 'bHandoffFadeIn')
    sec = tr.add_section()
    sec.set_range(0, end)
    sec.set_completion_mode(unreal.MovieSceneCompletionMode.KEEP_STATE)
    ch = sec.get_all_channels()[0]
    ch.set_default(False)
    ch.add_key(unreal.FrameNumber(end - 1), True, 0.0, DU)
    cut = next(t for t in seq.get_tracks() if t.get_class().get_name() == 'MovieSceneCameraCutTrack')
    # bCanBlend has no Python access: set it afterwards with Hayba object_set_property on this path
    log['handoff'] = dict(fade=[end - 6, end], flag=end - 1, cut_track=cut.get_path_name())


stamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
if SEQ.endswith('/LS_WakeUp'):
    src = Path('P:/FoA/Content/FoA/Cinematics/LS_WakeUp.uasset')
    bk = Path('P:/FoA/Saved/Backups/wake_retime') / stamp
    bk.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, bk / src.name)
    log['backup'] = str(bk)
to_display_mpc()
for a, b in sorted(CUTS, reverse=True):
    apply_cut(a, b)
end = 1092 - sum(b - a for a, b in CUTS)
seq.set_playback_end(end)
seq.set_work_range_end(end / 30.0)
seq.set_view_range_end(end / 30.0)
remove_binding('Cam_Wide')
remove_binding('L3_BedKick')
remove_binding('Cam_HandBack')
eyes()
handoff(end)
log['end'] = end
unreal.EditorAssetLibrary.save_loaded_asset(seq, False)
Path('P:/FoA/Saved/AnimShots/wake_retime.json').write_text(json.dumps(log, indent=1))
print('WAKE_RETIMED', SEQ, 'cut track', log['handoff']['cut_track'], 'end', end, 'splits', len(log['splits']), 'removed', len(log['removed_sections']))
