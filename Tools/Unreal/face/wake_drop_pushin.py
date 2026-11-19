"""LS_WakeUp: hold the POV through the turn to the clock (user 2026-11-10: "we can now see his freaking head as it
turns to view the alarm clock"; main's option a). Patches ONLY the Camera Cut track in place, never a rebuild
(build_ls_wakeup.py stays untouched): the Cam_POV cut section is extended to end where the Cam_PushIn cut ended
(into the two-shot at the time shift) and the Cam_PushIn cut section is removed. The Cam_PushIn binding and its
tracks stay, unused. Every binding / track / section is dumped before and after; it saves only when the camera cut
sections are the only difference, else it reloads the package (nothing kept).
  python Tools/Unreal/ue_remote.py Tools/Unreal/face/wake_drop_pushin.py   (holding a lease on the sequence asset)
Writes Saved/FaceShots/wake_edit/{before,after}.json."""
import json
from pathlib import Path

import unreal

PATH = '/Game/FoA/Cinematics/LS_WakeUp'
OUT = Path('P:/FoA/Saved/FaceShots/wake_edit')
OUT.mkdir(parents=True, exist_ok=True)
seq = unreal.load_asset(PATH)
guid = lambda g: str(unreal.GuidLibrary.conv_guid_to_string(g))
names = {guid(b.get_id()): str(b.get_display_name()) for b in seq.get_bindings()}


def sec_row(s):
    row = dict(cls=s.get_class().get_name(), start=round(s.get_start_frame_seconds(), 4) if s.has_start_frame() else None,
               end=round(s.get_end_frame_seconds(), 4) if s.has_end_frame() else None)
    if isinstance(s, unreal.MovieSceneCameraCutSection):
        row['camera'] = names.get(guid(s.get_camera_binding_id().get_editor_property('guid')))
    return row


def dump():
    out = dict(playback=[round(seq.get_playback_start_seconds(), 4), round(seq.get_playback_end_seconds(), 4)], master=[], bindings=[])
    for t in seq.get_tracks():
        out['master'].append(dict(cls=t.get_class().get_name(), name=str(t.get_display_name()),
                                  sections=sorted((sec_row(s) for s in t.get_sections()), key=lambda r: (r['start'] or -1))))
    for b in seq.get_bindings():
        out['bindings'].append(dict(name=str(b.get_display_name()), id=guid(b.get_id()), tracks=[
            dict(cls=t.get_class().get_name(), name=str(t.get_display_name()),
                 sections=[sec_row(s) for s in t.get_sections()]) for t in b.get_tracks()]))
    return out


def cut_track():
    return next(t for t in seq.get_tracks() if t.get_class().get_name() == 'MovieSceneCameraCutTrack')


before = dump()
(OUT / 'before.json').write_text(json.dumps(before, indent=1))
cuts = {sec_row(s)['camera']: s for s in cut_track().get_sections()}
assert 'Cam_PushIn' in cuts and 'Cam_POV' in cuts, sorted(cuts)
pov, push = cuts['Cam_POV'], cuts['Cam_PushIn']
assert abs(pov.get_end_frame_seconds() - push.get_start_frame_seconds()) < 1e-3, 'POV no longer runs straight into the push-in'
push_end = push.get_end_frame_seconds()
cut_track().remove_section(push)
pov.set_end_frame_seconds(push_end)
after = dump()
(OUT / 'after.json').write_text(json.dumps(after, indent=1))

# Only the camera cut track may differ, and it must still cover the film without gaps or overlaps.
strip = lambda d: dict(playback=d['playback'], bindings=d['bindings'],
                       master=[m for m in d['master'] if m['cls'] != 'MovieSceneCameraCutTrack'])
cut_rows = next(m for m in after['master'] if m['cls'] == 'MovieSceneCameraCutTrack')['sections']
ok = strip(before) == strip(after) and [r['camera'] for r in cut_rows][:2] == ['Cam_POV', 'Cam_TwoShot'] and \
    all(abs(a['end'] - b['start']) < 1e-3 for a, b in zip(cut_rows, cut_rows[1:])) and \
    cut_rows[0]['start'] == 0.0 and abs(cut_rows[-1]['end'] - after['playback'][1]) < 1e-3
print('FOA_WAKE_CUTS', [(r['camera'], r['start'], r['end']) for r in cut_rows])
if ok:
    assert unreal.EditorAssetLibrary.save_loaded_asset(seq, False), 'save failed'
    print('FOA_WAKE_EDIT saved')
else:
    unreal.EditorLoadingAndSavingUtils.reload_packages([seq.get_outermost()])
    print('FOA_WAKE_EDIT diff outside the camera cuts or a gap: reloaded, nothing saved')
