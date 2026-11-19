"""Audio pass, anim lane, asset side (docs/design/horror/audio_wiring.md). Editor Python for what Hayba cannot do
(an AnimNotify override, notify events on montages, an attached component template).
The graph side is audio_wiring_graphs.py. Re-runnable; each step saves only its own assets.
  python Tools/Unreal/ue_remote.py Tools/Unreal/player/audio_wiring_assets.py FOA_AREAS=Characters FOA_STEP=...
breath   BP_FoAPlayer.BreathAudio: S_Breath_TiredIdle_Loop_01 at volume 0.3, auto-play, on FollowCamera 8 cm below and
         4 cm ahead of the eyes (his mouth). UpdateBreathAudio (graph side) ducks it in cinematics and the battle.
foley    AN_FoA_Foley (Sound, Chance, Socket): plays Sound at the mesh socket with probability Chance.
events   montage foley at the gameplay notify times: Grab -> S_Foley_Reach at hand_r + S_Breath_Effort 40% at head;
         Pull -> S_Breath_Effort; KneelDown -> S_Foley_Crouch at pelvis. Track 'Audio', rebuilt each run.
(No LS_WakeUp crumble track: world plays S_Sand_Crumble inside BP_SandMaterialize.SetDissolveAmount, on the slap frame.)"""
import os

import unreal

P = '/Game/FoA/Characters/Player'
MS = '/Game/FoA/Audio/MetaSounds/'
EAL, BEL, AL = unreal.EditorAssetLibrary, unreal.BlueprintEditorLibrary, unreal.AnimationLibrary
AES = unreal.get_editor_subsystem(unreal.AssetEditorSubsystem)
FOLEY = P + '/Anims/AN_FoA_Foley'


def snd(name):
    a = unreal.load_asset(f'{MS}{name.split("_")[1]}/{name}')
    assert a, name
    return a


def breath():
    bp = unreal.load_asset(P + '/BP_FoAPlayer')
    AES.close_all_editors_for_asset(bp)
    sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    lib = unreal.SubobjectDataBlueprintFunctionLibrary
    handles = {str(lib.get_variable_name(lib.get_data(h))): h for h in sds.k2_gather_subobject_data_for_blueprint(bp)}
    assert 'FollowCamera' in handles, sorted(handles)
    if 'BreathAudio' not in handles:
        h, fail = sds.add_new_subobject(unreal.AddNewSubobjectParams(parent_handle=handles['FollowCamera'],
                                                                     new_class=unreal.AudioComponent, blueprint_context=bp))
        assert not str(fail), fail
        sds.rename_subobject(h, unreal.Text('BreathAudio'))
        handles['BreathAudio'] = h
    else:
        sds.attach_subobject(handles['FollowCamera'], handles['BreathAudio'])
    c = lib.get_object_for_blueprint(lib.get_data(handles['BreathAudio']), bp)
    c.set_editor_property('sound', snd('S_Breath_TiredIdle_Loop_01'))
    c.set_editor_property('volume_multiplier', 0.3)
    c.set_editor_property('auto_activate', True)
    c.set_editor_property('relative_location', unreal.Vector(4.0, 0.0, -8.0))
    BEL.compile_blueprint(bp)
    assert EAL.save_loaded_asset(bp, False)
    print('breath', c.get_path_name(), c.get_editor_property('volume_multiplier'), c.get_editor_property('sound').get_name())


def foley():
    bp = unreal.load_asset(FOLEY)
    if not bp:
        f = unreal.BlueprintFactory()
        f.set_editor_property('parent_class', unreal.AnimNotify)
        bp = unreal.AssetToolsHelpers.get_asset_tools().create_asset('AN_FoA_Foley', P + '/Anims', unreal.Blueprint, f)
    AES.close_all_editors_for_asset(bp)
    if 'Received_Notify' not in [str(g) for g in BEL.list_graph_names(bp)]:
        BEL.add_function_override(bp, 'Received_Notify')
    assert EAL.save_loaded_asset(bp, False)
    print('foley class', bp.get_path_name(), [str(g) for g in BEL.list_graph_names(bp)],
          [str(v) for v in BEL.list_member_variable_names(bp, False)])


def events():
    cls = EAL.load_blueprint_class(FOLEY)
    assert cls, FOLEY + ' (compile it first)'
    plan = {'AM_FoA_PickUp_Floor': ('Grab', [('S_Foley_Reach', 1.0, 'hand_r'), ('S_Breath_Effort', 0.4, 'head')]),
            'AM_FoA_PickUp_Table': ('Grab', [('S_Foley_Reach', 1.0, 'hand_r'), ('S_Breath_Effort', 0.4, 'head')]),
            'AM_FoA_OpenDrawer': ('Pull', [('S_Breath_Effort', 1.0, 'head')]),
            'AM_FoA_KneelScrewdriver': ('KneelDown', [('S_Foley_Crouch', 1.0, 'pelvis')])}
    for name, (marker, sounds) in plan.items():
        m = unreal.load_asset(P + '/Montages/' + name)
        AES.close_all_editors_for_asset(m)
        t = [AL.get_anim_notify_event_trigger_time(e) for e in AL.get_animation_notify_events(m)
             if isinstance(e.get_editor_property('notify'), unreal.AnimNotify_PlayMontageNotify)
             and str(e.get_editor_property('notify').get_editor_property('notify_name')) == marker]
        assert len(t) == 1, (name, marker, t)
        if 'Audio' in [str(n) for n in AL.get_animation_notify_track_names(m)]:
            AL.remove_animation_notify_events_by_track(m, 'Audio')
        else:
            AL.add_animation_notify_track(m, 'Audio')
        for sound, chance, socket in sounds:
            n = AL.add_animation_notify_event(m, 'Audio', t[0], cls)
            n.set_editor_property('Sound', snd(sound))
            n.set_editor_property('Chance', chance)
            n.set_editor_property('Socket', socket)
        assert EAL.save_loaded_asset(m, False)
        print('events', name, marker, round(t[0], 3), [s[0] for s in sounds])


{'breath': breath, 'foley': foley, 'events': events}[os.environ['FOA_STEP']]()
