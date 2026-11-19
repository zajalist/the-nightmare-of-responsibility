"""Story lane, read only: the notify events on the five interaction montages -> Saved/StoryShots/montage_notifies.json."""
import json, unreal
AL = unreal.AnimationLibrary
out = {}
for n in ('AM_FoA_PickUp_Floor', 'AM_FoA_PickUp_Table', 'AM_FoA_OpenDrawer', 'AM_FoA_TryLockedHandle', 'AM_FoA_KneelScrewdriver'):
    m = unreal.load_asset('/Game/FoA/Characters/Player/Montages/' + n)
    rows = []
    for e in AL.get_animation_notify_events(m):
        no = e.get_editor_property('notify')
        nm = str(no.get_editor_property('notify_name')) if isinstance(no, unreal.AnimNotify_PlayMontageNotify) else ''
        rows.append((no.get_class().get_name() if no else None, nm, round(AL.get_anim_notify_event_trigger_time(e), 3)))
    out[n] = dict(tracks=[str(t) for t in AL.get_animation_notify_track_names(m)], events=rows)
open('P:/FoA/Saved/StoryShots/montage_notifies.json', 'w').write(json.dumps(out, indent=1))
