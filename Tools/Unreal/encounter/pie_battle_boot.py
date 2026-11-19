"""Bounded in-PIE fixture, never starts/stops PIE. Root owns EXCLUSIVE and native key injection.

FOA_STAGE=roam: real front-end handlers -> cinematic skip -> real phone DoAction; stops for native W test.
FOA_STAGE=battle: explicit T7 beat shortcut, then the real interactor takes Shirt_T7 (no F8).
FOA_STAGE=snapshot: read-only input/focus snapshot for comparison around native W/pause/resume.
FOA_STAGE=abort: direct PIE-world ResetHouse, checks controls/HUD/idle again after two seconds.
FOA_STAGE=pause_battle: direct PIE TogglePause/Resume, verifies the existing battle widget and locks survive.
FOA_STAGE=rapid_abort: real shirt start, immediate PIE ResetHouse, API re-entry, delayed release ownership check.
"""
import json
import os
from pathlib import Path
import time

import unreal

STAGE = os.environ.get('FOA_STAGE', 'roam')
LABEL = os.environ.get('FOA_LABEL', 'snapshot')
ROOT = '/Game/FoA/'
S = dict(start=time.time(), phase=0, handle=None, log=[], done=False, ready=0)
OUT = Path('P:/FoA/Saved/EncounterCaptures/boot_' + STAGE + '.json')


def actor(w, path):
    return unreal.GameplayStatics.get_actor_of_class(w, unreal.load_class(None, ROOT + path))


def snapshot(w, label):
    pc = unreal.GameplayStatics.get_player_controller(w, 0)
    p = unreal.GameplayStatics.get_player_character(w, 0)
    ph = actor(w, 'UI/Game/BP_Phone.BP_Phone_C')
    phone = ph.get_component_by_class(unreal.WidgetComponent).get_widget()
    btn = phone.get_editor_property('Btn_Action').get_editor_property('Btn_Hit')
    v = p.get_actor_location()
    vel = p.get_velocity()
    def vector(value):
        return [round(value.x, 3), round(value.y, 3), round(value.z, 3)]
    w_key = unreal.Key()
    w_key.set_editor_property('key_name', 'W')
    row = dict(label=label, t=round(time.time() - S['start'], 2),
               controller_class=pc.get_class().get_path_name(), player_controlled=p.is_player_controlled(),
               pos=[v.x, v.y, v.z], velocity=[vel.x, vel.y, vel.z],
               w_down=pc.is_input_key_down(w_key),
               last_input=vector(p.get_last_movement_input_vector()),
               pending_input=vector(p.get_pending_movement_input_vector()),
               acceleration=vector(p.character_movement.get_current_acceleration()),
               move_ignored=pc.is_move_input_ignored(), look_ignored=pc.is_look_input_ignored(),
               cursor=pc.get_editor_property('show_mouse_cursor'), paused=unreal.GameplayStatics.is_game_paused(w),
               phone_open=ph.get_editor_property('bOpen'), phone_keyboard_focus=btn.has_keyboard_focus(),
               phone_user_focus=btn.has_user_focus(pc), view=pc.get_view_target().get_class().get_name(),
               movement=str(p.character_movement.movement_mode), cinematic=p.get_editor_property('bCinematic'),
               interaction_locked=p.get_editor_property('bInteractionLocked'))
    S['log'].append(row)
    print('BATTLE BOOT', row)
    return row


def finish(reason):
    if S['done']:
        return
    S['done'] = True
    if S['handle'] is not None:
        unreal.unregister_slate_post_tick_callback(S['handle'])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(dict(reason=reason, stage=STAGE, log=S['log']), indent=1), encoding='utf-8')
    print('BATTLE BOOT', reason, str(OUT))


def tick(_dt):
    try:
        w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
        if not w:
            return finish('pie_gone')
        t = time.time() - S['start']
        if t > 25:
            return finish('cap')
        d = actor(w, 'Gameplay/BP_BeatDirector.BP_BeatDirector_C')
        fe = actor(w, 'UI/Framework/BP_FoAFrontEnd.BP_FoAFrontEnd_C')
        pc = unreal.GameplayStatics.get_player_controller(w, 0)
        p = unreal.GameplayStatics.get_player_character(w, 0)
        beat = d.get_editor_property('Beat')
        beat_id = str(beat.get_editor_property('Id')) if beat else None
        if STAGE == 'snapshot':
            snapshot(w, LABEL)
            return finish('snapshot')
        if STAGE == 'roam':
            if S['phase'] == 0 and t > 0.3:
                fe.call_method('OnSplashFinished', ())
                S['phase'] = 1
            elif S['phase'] == 1 and t > 1:
                fe.call_method('OnTitleConfirmed', ())
                S['phase'] = 2
            elif S['phase'] == 2 and t > 1.8:
                fe.call_method('WakeUp', ())
                S['phase'] = 3
            elif S['phase'] == 3 and pc.get_view_target().get_class().get_name() == 'CineCameraActor':
                d.call_method('SkipWakeUp', ())
                S['phase'] = 4
                S['ready'] = t + 0.6
            elif S['phase'] == 4 and beat_id == 'T0' and t > S['ready']:
                snapshot(w, 'phone_before_action')
                ph = actor(w, 'UI/Game/BP_Phone.BP_Phone_C')
                ph.get_component_by_class(unreal.WidgetComponent).get_widget().call_method('DoAction', ())
                S['phase'] = 5
                S['ready'] = t + 1
            elif S['phase'] == 5 and t > S['ready']:
                row = snapshot(w, 'phone_closed_ready_for_native_W')
                assert not row['phone_open'] and not row['move_ignored'] and not row['look_ignored'], row
                return finish('ready_for_native_W')
        elif STAGE == 'pause_battle':
            enc = actor(w, 'Gameplay/Encounter/BP_Encounter.BP_Encounter_C')
            if S['phase'] == 0 and enc.get_editor_property('bActive') and enc.get_editor_property('bPlayerTurn'):
                snapshot(w, 'battle_before_pause')
                S['widget'] = enc.get_editor_property('Widget').get_path_name()
                fe.call_method('TogglePause', ())
                S['ready'] = t + 0.4
                S['phase'] = 1
            elif S['phase'] == 1 and t > S['ready']:
                row = snapshot(w, 'battle_paused')
                assert row['paused'], row
                fe.call_method('Resume', ())
                S['ready'] = t + 0.7
                S['phase'] = 2
            elif S['phase'] == 2 and t > S['ready']:
                row = snapshot(w, 'battle_after_resume')
                widget = enc.get_editor_property('Widget')
                row.update(active=enc.get_editor_property('bActive'),
                           is_battle=p.mesh.get_anim_instance().get_editor_property('IsBattle'),
                           widget_path=widget.get_path_name(), expected_widget_path=S['widget'],
                           command_visibility=str(widget.get_editor_property('CommandPanel').get_visibility()),
                           hud_visibility=str(fe.get_editor_property('HUD').get_visibility()))
                assert not row['paused'] and row['active'] and row['is_battle'], row
                assert row['move_ignored'] and row['look_ignored'] and row['cursor'], row
                assert row['view'] == 'BP_Encounter_C' and row['widget_path'] == row['expected_widget_path'], row
                assert 'COLLAPSED' in row['hud_visibility'].upper(), row
                return finish('battle_pause_resume_preserved_widget_and_locks')
        elif STAGE == 'abort':
            enc = actor(w, 'Gameplay/Encounter/BP_Encounter.BP_Encounter_C')
            if S['phase'] == 0:
                snapshot(w, 'before_direct_PIE_abort')
                S['hud_before'] = str(enc.get_editor_property('BattleHUDVisibility'))
                d.call_method('ResetHouse', ())
                S['ready'] = t + 2
                S['phase'] = 1
            elif S['phase'] == 1 and t > S['ready']:
                row = snapshot(w, 'two_seconds_after_direct_PIE_abort')
                hud = fe.get_editor_property('HUD')
                row.update(active=enc.get_editor_property('bActive'),
                           is_battle=p.mesh.get_anim_instance().get_editor_property('IsBattle'),
                           hud_visibility=str(hud.get_visibility()), expected_hud_visibility=S['hud_before'])
                assert not row['active'] and not row['is_battle'], row
                assert not row['move_ignored'] and not row['look_ignored'] and not row['cursor'], row
                assert row['view'] == 'BP_FoAPlayer_C' and row['hud_visibility'] == row['expected_hud_visibility'], row
                return finish('abort_restored_and_stayed_restored')
        elif STAGE in ('battle', 'rapid_abort'):
            enc = actor(w, 'Gameplay/Encounter/BP_Encounter.BP_Encounter_C')
            if S['phase'] == 0:
                d.call_method('ReportEvent', ('WardrobeLanded',))
                S['log'].append(dict(label='explicit_T7_shortcut'))
                S['phase'] = 1
            elif S['phase'] == 1 and beat_id == 'T7' and not d.get_editor_property('bWardrobeTransition'):
                shirt = next(a for a in unreal.GameplayStatics.get_all_actors_of_class(w, unreal.Actor)
                             if a.get_actor_label() == 'Shirt_T7')
                v = shirt.get_actor_location()
                toward = unreal.Vector(-v.x, -v.y, 0)
                toward.normalize()
                stand = unreal.Vector(v.x + toward.x * 100, v.y + toward.y * 100, p.get_actor_location().z)
                assert p.teleport(stand, p.get_actor_rotation())
                pc.set_control_rotation(unreal.MathLibrary.find_look_at_rotation(stand + unreal.Vector(0, 0, 60), v))
                ia = p.get_component_by_class(unreal.load_class(None, ROOT + 'Gameplay/BPC_Interactor.BPC_Interactor_C'))
                ia.call_method('SetFocus', (shirt,))
                ia.call_method('Refresh', (True,))
                ia.call_method('Interact', ())
                S['log'].append(dict(label='real_Shirt_T7_interactor'))
                S['phase'] = 2
            elif S['phase'] == 2 and beat_id == 'T8' and enc.get_editor_property('bActive'):
                row = snapshot(w, 'T8_started')
                if STAGE == 'battle':
                    return finish('battle_ready')
                assert row['interaction_locked'], 'Race fixture missed the live shirt interaction hold'
                assert row['move_ignored'] and row['look_ignored'], row
                d.call_method('ResetHouse', ())
                row = snapshot(w, 'immediately_after_shirt_abort')
                assert not enc.get_editor_property('bActive') and not row['interaction_locked'], row
                assert not row['move_ignored'] and not row['look_ignored'], row
                enc.call_method('StartEncounter', ('Shirt',))
                S['log'].append(dict(label='explicit_API_reentry_fixture'))
                S['ready'] = t + 6
                S['phase'] = 3
            elif S['phase'] == 3 and t > S['ready']:
                row = snapshot(w, 'six_seconds_after_immediate_reentry')
                assert enc.get_editor_property('bActive') and not row['interaction_locked'], row
                assert row['move_ignored'] and row['look_ignored'] and row['cursor'], row
                # Also exercise the old timer's exact idempotent callback, irrespective of montage duration.
                p.call_method('EndInteraction', ())
                row = snapshot(w, 'after_repeated_late_interaction_release')
                assert row['move_ignored'] and row['look_ignored'] and not row['interaction_locked'], row
                enc.call_method('EndEncounter', ())
                S['ready'] = t + 0.5
                S['phase'] = 4
            elif S['phase'] == 4 and t > S['ready']:
                row = snapshot(w, 'rapid_abort_fixture_final_cleanup')
                assert not enc.get_editor_property('bActive') and not row['interaction_locked'], row
                assert not row['move_ignored'] and not row['look_ignored'] and not row['cursor'], row
                return finish('immediate_abort_reentry_preserved_owned_locks')
    except Exception as exc:
        S['log'].append(dict(error=repr(exc)))
        finish('error')


S['handle'] = unreal.register_slate_post_tick_callback(tick)
print('battle boot fixture scheduled', STAGE, '25 second cap')
