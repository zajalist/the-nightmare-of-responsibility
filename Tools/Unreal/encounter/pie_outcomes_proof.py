"""Bounded PIE outcome proof; coordinator owns start/stop/exclusive lease.

Win: real front end, explicit T8 fixture, existing perfect-key fight policy and normal payoff/phone handoff.
Loss: fresh encounter API fixture, existing driver's authored Strike damage plus Flee; not a full player loss run.
No direct BattleState/Composure/Remaining/progress edits. Timing tweaks exist only in this PIE world.
"""
import json
import os
from pathlib import Path
import time

import unreal

CAP = float(os.environ.get('FOA_CAP', '70'))
MODE = os.environ.get('FOA_OUTCOME_MODE', 'both')
OUT = Path('P:/FoA/Saved/EncounterCaptures/outcomes_proof.json')
ROOT = '/Game/FoA/'
S = dict(start=time.time(), phase=0, handle=None, log=[], done=False, seen=set(), scopes=[], mode='win')
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
assert world
gi = unreal.GameplayStatics.get_game_instance(world)
original = (str(gi.get_editor_property('SaveSlot')), set(gi.get_editor_property('Knowledge')), list(gi.get_editor_property('Notebook')))
gi.call_method('SetProofProgressContext', ('FoA_QA_Outcome', set(), []))


def actor(w, path):
    return unreal.GameplayStatics.get_actor_of_class(w, unreal.load_class(None, ROOT + path))


def log(w, enc, label):
    pc = unreal.GameplayStatics.get_player_controller(w, 0)
    pawn = unreal.GameplayStatics.get_player_pawn(w, 0)
    director = actor(w, 'Gameplay/BP_BeatDirector.BP_BeatDirector_C')
    beat = director.get_editor_property('Beat')
    phone = actor(w, 'UI/Game/BP_Phone.BP_Phone_C')
    fe = actor(w, 'UI/Framework/BP_FoAFrontEnd.BP_FoAFrontEnd_C')
    battle_widget = enc.get_editor_property('Widget')
    cam = enc.get_editor_property('BattleCam')
    pos = cam.get_editor_property('relative_location')
    row = dict(t=round(time.time() - S['start'], 2), label=label, mode=S['mode'],
               active=enc.get_editor_property('bActive'), state=str(enc.get_editor_property('BattleState')),
               camera=[pos.x, pos.y, pos.z], fov=cam.get_editor_property('field_of_view'),
               view=pc.get_view_target().get_class().get_name(), move_ignored=pc.is_move_input_ignored(),
               look_ignored=pc.is_look_input_ignored(), cursor=pc.get_editor_property('show_mouse_cursor'),
               beat=str(beat.get_editor_property('Id')) if beat else None,
               cinematic=pawn.get_editor_property('bCinematic'),
               interaction_locked=pawn.get_editor_property('bInteractionLocked'),
               phone_open=phone.get_editor_property('bOpen'),
               ui_owns_input=fe.get_editor_property('bUIOwnsInputLocks'),
               battle_widget_visible=bool(battle_widget and battle_widget.is_in_viewport()),
               pawn_location=pawn.get_actor_location().to_tuple(), falling=pawn.character_movement.is_falling(),
               acting_owned=bool(enc.get_editor_property('BattleActingMontage')),
               contact_owned=bool(enc.get_editor_property('ContactGarment')),
               outfit={part:bool(pawn.get_editor_property(part).is_visible()) for part in ('Suit','StartOutfit','Shirt','Trousers','Socks','Tie')})
    row['velocity'] = pawn.get_velocity().to_tuple()
    row['root_motion_mode'] = str(pawn.mesh.get_anim_instance().get_editor_property('RootMotionMode'))
    if 'phone' in label:
        row['floor'] = pawn.character_movement.get_editor_property('current_floor').export_text()
        pawn_channels = [getattr(unreal.CollisionChannel, name) for name in dir(unreal.CollisionChannel) if name.endswith('PAWN')]
        assert len(pawn_channels) == 1, 'Pawn collision channel unavailable'
        row['phone_collision'] = [dict(name=c.get_name(),profile=str(c.get_collision_profile_name()),
            enabled=str(c.get_collision_enabled()),pawn_response=str(c.get_collision_response_to_channel(pawn_channels[0])))
            for c in phone.get_components_by_class(unreal.PrimitiveComponent)]
    S['log'].append(row)
    print('OUTCOME', label, row['state'], row['camera'])


def finish(reason):
    if S['done']:
        return
    S['done'] = True
    unreal.unregister_slate_post_tick_callback(S['handle'])
    for scope in S['scopes']:
        scope['finish']('outcome_proof_finished')
    unreal.GameplayStatics.set_global_time_dilation(world, 1)
    gi.call_method('SetProofProgressContext', original)
    unreal.GameplayStatics.delete_game_in_slot('FoA_QA_Outcome', 0)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(dict(reason=reason, win_kind='existing full-fight policy with perfect timed keys',
                                  loss_kind='fresh encounter API plus authored Strike damage/Flee fixture',
                                  log=S['log']), indent=1), encoding='utf-8')
    print('OUTCOME PROOF', reason, str(OUT))


def drive(mode):
    values = {'FOA_MODE': mode, 'FOA_SPEED': '8', 'FOA_CAP': '48',
              'FOA_TURN_PAUSE': '0.04', 'FOA_SHOT_INTERVAL': '1.0'}
    saved = {key: os.environ.get(key) for key in values}
    scope = {'__name__': '__main__', '__file__': 'P:/FoA/Tools/Unreal/encounter/pie_fight.py'}
    try:
        os.environ.update(values)
        source = Path(scope['__file__']).read_text(encoding='utf-8')
        exec(compile(source, scope['__file__'], 'exec'), scope)
    finally:
        for key, value in saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
    S['scopes'].append(scope)


def tick(_dt):
    try:
        w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
        if not w:
            return finish('pie_ended')
        t = time.time() - S['start']
        if t > CAP:
            unreal.GameplayStatics.set_global_time_dilation(w, 1)
            return finish('cap')
        d = actor(w, 'Gameplay/BP_BeatDirector.BP_BeatDirector_C')
        fe = actor(w, 'UI/Framework/BP_FoAFrontEnd.BP_FoAFrontEnd_C')
        enc = actor(w, 'Gameplay/Encounter/BP_Encounter.BP_Encounter_C')
        pc = unreal.GameplayStatics.get_player_controller(w, 0)
        p = unreal.GameplayStatics.get_player_character(w, 0)
        beat = d.get_editor_property('Beat')
        beat_id = str(beat.get_editor_property('Id')) if beat else None
        if S['phase'] == 0 and t > 0.1:
            fe.call_method('OnSplashFinished', ())
            S['phase'] = 1
        elif S['phase'] == 1 and t > 0.4:
            fe.call_method('OnTitleConfirmed', ())
            S['phase'] = 2
        elif S['phase'] == 2 and t > 0.7:
            fe.call_method('WakeUp', ())
            S['phase'] = 3
        elif S['phase'] == 3:
            story = fe.get_editor_property('Story')
            if story and story.is_in_viewport():
                story.call_method('Finish', ())
            elif fe.get_editor_property('bInGameplay') and d.get_editor_property('SeqPlayer') and not d.get_editor_property('bWakeDone'):
                d.call_method('SkipWakeUp', ())
                S['phase'] = 4
        elif S['phase'] == 4 and d.get_editor_property('bWakeDone') and pc.get_view_target() == p and not p.get_editor_property('bCinematic'):
            unreal.SystemLibrary.pause_timer(d, 'PollStoryMoment')
            unreal.SystemLibrary.clear_timer(d, 'TryStoryMoment')
            d.call_method('EnterBeat', (8,))
            S['phase'] = 6
        elif S['phase'] == 6 and enc.get_editor_property('bActive'):
            log(w, enc, 'T8_fixture_started_fight')
            drive('win')
            S['phase'] = 7
        elif S['phase'] == 8:
            phone = actor(w, 'UI/Game/BP_Phone.BP_Phone_C')
            if t < S['phone_closed_at'] + float(phone.get_editor_property('BlendSeconds')) + .2:
                return
            log(w, enc, 'Victory_phone_closed_input_restored')
            assert not phone.get_editor_property('bOpen'), 'Phone remained open after its real action'
            assert not enc.get_editor_property('bActive'), 'Encounter reactivated during phone handoff'
            assert pc.get_view_target() == p, 'Camera did not return from phone to player'
            assert not pc.is_move_input_ignored(), 'Movement still locked after phone closed'
            assert not pc.is_look_input_ignored(), 'Look still locked after phone closed'
            assert not p.get_editor_property('bInteractionLocked'), 'Player interaction survived payoff and phone'
            assert not p.get_editor_property('bCinematic'), 'Cinematic ownership survived payoff and phone'
            assert p.get_current_montage() is None, 'Phone hold montage survived closure'
            before_phone = next(row['pawn_location'] for row in S['log'] if row['label'] == 'Victory_free_input_before_phone')
            current = p.get_actor_location()
            assert ((current.x-before_phone[0])**2 + (current.y-before_phone[1])**2)**.5 < 1, 'Phone displaced the player horizontally'
            assert str(phone.get_editor_property('Mesh').get_collision_profile_name()) == 'NoCollision', 'Held phone mesh still blocks its owner'
            assert not fe.get_editor_property('bUIOwnsInputLocks'), 'Front end retained an input lock'
            assert not enc.get_editor_property('BattleActingMontage'), 'Battle acting survived victory'
            assert not enc.get_editor_property('ContactGarment'), 'Battle contact survived victory'
            assert not p.character_movement.is_falling() and p.get_actor_location().z > 25, 'Unsafe handoff position'
            assert p.get_editor_property('Suit').is_visible() and not p.get_editor_property('StartOutfit').is_visible(), 'Suit payoff did not replace the polo'
            unreal.SystemLibrary.execute_console_command(w, 'Shot showui filename=P:/FoA/Saved/PresentationReview/victory_released.png -nosuffix', pc)
            if MODE == 'win':
                return finish('win_complete')
            S.pop('handoff_at')
            d.call_method('ResetHouse', ())
            S['mode'] = 'loss_fixture'
            enc.call_method('StartEncounter', ('Shirt',))
            drive('lose')
            S['phase'] = 9
        elif S['phase'] in (7, 9):
            state = str(enc.get_editor_property('BattleState'))
            expected = 'Victory' if S['phase'] == 7 else 'Defeat'
            if state in ('Victory', 'Defeat') and state != expected:
                log(w, enc, 'unexpected_outcome')
                unreal.GameplayStatics.set_global_time_dilation(w, 1)
                return finish('win_policy_lost' if S['phase'] == 7 else 'loss_fixture_won')
            if state == expected and expected not in S['seen']:
                S['seen'].add(expected)
                unreal.GameplayStatics.set_global_time_dilation(w, 1)
                log(w, enc, expected + '_shot')
                unreal.SystemLibrary.execute_console_command(w, 'Shot showui filename=P:/FoA/Saved/PresentationReview/outcome_' + expected + '.png -nosuffix', pc)
            if expected in S['seen'] and not enc.get_editor_property('bActive'):
                if 'handoff_at' not in S:
                    log(w, enc, expected + '_normal_handoff')
                    S['handoff_at'] = t
                if expected == 'Victory':
                    phone = actor(w, 'UI/Game/BP_Phone.BP_Phone_C')
                    widget = enc.get_editor_property('Widget')
                    assert not widget or not widget.is_in_viewport(), 'Battle UI retained viewport ownership'
                    assert not fe.get_editor_property('bUIOwnsInputLocks'), 'Front end retained an input lock'
                    if not phone.get_editor_property('bOpen'):
                        # T9 deliberately starts the suit payoff interaction after
                        # EndEncounter restores the controller. A lock without that
                        # owner is a leak even if ClosePhone would later reset it.
                        view = pc.get_view_target()
                        if view != p and view.actor_has_tag('PayoffCam'):
                            # T9 hero shot (BP_BeatDirector.PayoffShot): owns view, move and look for 2.7 s, then hands back
                            assert t < S['handoff_at'] + 4, 'T9 hero shot did not hand the camera back'
                            return
                        assert view == p, 'Battle camera survived into payoff'
                        assert not pc.is_look_input_ignored(), 'Look lock leaked before phone opened'
                        assert not pc.is_move_input_ignored() or p.get_editor_property('bInteractionLocked'), 'Unowned move lock before phone opened'
                        if not pc.is_move_input_ignored() and 'free_before_phone' not in S:
                            log(w, enc, 'Victory_free_input_before_phone')
                            S['free_before_phone'] = t
                        assert t < S['handoff_at'] + 6, 'T9 payoff did not reach its T10 phone task'
                        return
                    assert beat_id == 'T10', 'Unexpected phone opened after victory'
                    assert pc.get_view_target() == phone, 'T10 phone did not take camera ownership'
                    assert pc.is_move_input_ignored() and pc.is_look_input_ignored(), 'Open phone failed to own move/look input'
                    if p.get_editor_property('bInteractionLocked'):
                        assert t < S['handoff_at'] + 6, 'Payoff ownership did not release to phone'
                        return
                    assert p.get_editor_property('bCinematic'), 'Portable phone did not own the hold pose'
                    assert not phone.get_editor_property('bPreviousCinematic'), 'Phone inherited unreleased payoff ownership'
                    if 'phone_seen' not in S:
                        S['phone_seen'] = t
                        return
                    if t < S['phone_seen'] + 1:
                        if 'phone_shot' not in S and t > S['phone_seen'] + .7:
                            S['phone_shot'] = True
                            unreal.SystemLibrary.execute_console_command(w, 'Shot showui filename=P:/FoA/Saved/PresentationReview/victory_phone.png -nosuffix', pc)
                        return
                    log(w, enc, 'Victory_T10_phone_owns_input')
                    phone.get_component_by_class(unreal.WidgetComponent).get_widget().call_method('DoAction', ())
                    S['phone_closed_at'] = t
                    S['phase'] = 8
                elif t >= S['handoff_at'] + 4.0:
                    log(w, enc, expected + '_settled_handoff')
                    return finish('both_outcomes')
    except Exception as exc:
        S['log'].append(dict(error=repr(exc), t=round(time.time() - S['start'], 2)))
        w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
        if w:
            unreal.GameplayStatics.set_global_time_dilation(w, 1)
        finish('error')


S['handle'] = unreal.register_slate_post_tick_callback(tick)
print('Outcome proof scheduled', CAP, 'seconds; no forced outcome states')
