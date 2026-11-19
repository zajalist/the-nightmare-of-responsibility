"""Read-only dump of LS_WakeUp: bindings, tracks, sections and key times, to Saved/AnimShots/wake_inspect.json.
  $env:HAYBA_AGENT_ID='anim'; $env:FOA_AREAS='Cinematics'; python Tools/Unreal/ue_remote.py Tools/Unreal/cine/inspect_wake.py"""
import json
import os

import unreal

seq = unreal.load_asset(os.environ.get('FOA_SEQ', '/Game/FoA/Cinematics/LS_WakeUp'))
fps = seq.get_display_rate()
tick = seq.get_tick_resolution()


def sec_row(s):
    r = dict(cls=s.get_class().get_name(),
             start=s.get_start_frame() if s.has_start_frame() else None,
             end=s.get_end_frame() if s.has_end_frame() else None, channels=[])
    if isinstance(s, unreal.MovieSceneSkeletalAnimationSection):
        p = s.get_editor_property('params')
        r['anim'] = p.animation.get_name() if p.animation else None
        r['params'] = p.export_text()[:400]
    if isinstance(s, unreal.MovieSceneCameraCutSection):
        try:
            r['camera'] = str(s.get_camera_binding_id().export_text())
        except Exception as e:
            r['camera'] = str(e)
    for c in s.get_all_channels():
        try:
            ks = c.get_keys()
        except Exception:
            ks = []
        times = [k.get_time().frame_number.value for k in ks]
        vals = []
        for k in ks[:40]:
            try:
                v = k.get_value()
                vals.append(round(v, 3) if isinstance(v, float) else str(v)[:30])
            except Exception:
                vals.append(None)
        r['channels'].append([str(c.channel_name), times[:60], vals, len(times)])
    return r


def track_row(t):
    r = dict(cls=t.get_class().get_name(), name=str(t.get_display_name()), sections=[sec_row(s) for s in t.get_sections()])
    try:
        r['prop'] = str(t.get_property_name())
    except Exception:
        pass
    return r


out = dict(name=seq.get_name(), fps=[fps.numerator, fps.denominator], tick=[tick.numerator, tick.denominator],
           playback=[seq.get_playback_start(), seq.get_playback_end()],
           master=[track_row(t) for t in seq.get_tracks()], bindings=[])
for b in seq.get_bindings():
    par = b.get_parent()
    out['bindings'].append(dict(name=str(b.get_display_name()), id=b.get_id().export_text(),
                                parent=str(par.get_display_name()) if par and par.get_id() != b.get_id() else None,
                                tracks=[track_row(t) for t in b.get_tracks()]))
path = 'P:/FoA/Saved/AnimShots/' + seq.get_name() + '_inspect.json'
with open(path, 'w') as f:
    json.dump(out, f, indent=1)
print('WAKE_INSPECT', path, len(out['bindings']), 'bindings', out['playback'])
