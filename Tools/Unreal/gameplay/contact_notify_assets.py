"""Only declare the notify override or add markers; never rebuild animation data."""
import json,os
from pathlib import Path
import unreal
AN='/Game/FoA/Gameplay/AN_FoA_InteractionContact'
assert not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
if os.environ['FOA_CONTACT_PHASE']=='declare':
    bp=unreal.load_asset(AN)
    if not bp:
        factory=unreal.BlueprintFactory();factory.set_editor_property('parent_class',unreal.AnimNotify)
        bp=unreal.AssetToolsHelpers.get_asset_tools().create_asset('AN_FoA_InteractionContact','/Game/FoA/Gameplay',unreal.Blueprint,factory)
    if 'Received_Notify' not in [str(n) for n in unreal.BlueprintEditorLibrary.list_graph_names(bp)]:
        unreal.BlueprintEditorLibrary.add_function_override(bp,'Received_Notify')
else:
    cls=unreal.load_class(None,AN+'.AN_FoA_InteractionContact_C');assert cls
    rows=[]
    for name,wanted in [('AM_FoA_PickUp_Floor','Grab'),('AM_FoA_PickUp_Table','Grab'),
        ('AM_FoA_OpenDrawer','Grip'),('AM_FoA_TryLockedHandle','Locked'),('AM_FoA_KneelScrewdriver','WorkDone')]:
        montage=unreal.load_asset('/Game/FoA/Characters/Player/Montages/'+name)
        length=montage.get_play_length()
        segments=[t.export_text() for t in montage.get_editor_property('slot_anim_tracks')]
        contacts=[]
        existing=[]
        for event in unreal.AnimationLibrary.get_animation_notify_events(montage):
            notify=event.get_editor_property('notify')
            if not notify:continue
            if notify.get_class()==cls:existing.append(event)
            elif isinstance(notify,unreal.AnimNotify_PlayMontageNotify) and str(notify.get_editor_property('notify_name'))==wanted:
                contacts.append(unreal.AnimationLibrary.get_anim_notify_event_trigger_time(event))
        assert len(contacts)==1,(name,contacts)
        if not existing:
            if 'InteractionContact' not in [str(t) for t in unreal.AnimationLibrary.get_animation_notify_track_names(montage)]:
                unreal.AnimationLibrary.add_animation_notify_track(montage,'InteractionContact')
            unreal.AnimationLibrary.add_animation_notify_event(montage,'InteractionContact',contacts[0],cls)
        else:
            assert len(existing)==1 and abs(unreal.AnimationLibrary.get_anim_notify_event_trigger_time(existing[0])-contacts[0])<.001
        assert length==montage.get_play_length()
        assert segments==[t.export_text() for t in montage.get_editor_property('slot_anim_tracks')]
        rows.append(dict(montage=montage.get_path_name(),contact=contacts[0],length=length,segments_unchanged=True))
    Path('P:/FoA/Saved/Integration/contact_notify_markers.json').write_text(json.dumps(rows,indent=1))
    print('Contact markers prepared; native save required',rows)
