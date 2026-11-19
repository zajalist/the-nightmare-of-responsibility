"""Bounded battle presentation monitor, injected only inside root's existing EXCLUSIVE PIE burst.

Run with integration/run_read.py, FOA_CAP=40. Start pie_fight.py alongside it to exercise real rules.
Records state/angles/live labels/input locks and actual screenshot requests; never touches editor assets.
"""
import json
import os
from pathlib import Path
import time

import unreal

CAP = float(os.environ.get('FOA_CAP', '40'))
OUT = Path('P:/FoA/Saved/EncounterCaptures/presentation_proof.json')
S = dict(start=time.time(), handle=None, samples=[], seen=set(), done=False, had_battle=False, last=0.0, reduce=False)
MPC = unreal.load_asset('/Game/FoA/PostProcess/MPC_Dream')
CLS = unreal.load_class(None, '/Game/FoA/Gameplay/Encounter/BP_Encounter.BP_Encounter_C')


def get(obj, key, default=None):
    try:
        return obj.get_editor_property(key) if obj else default
    except Exception:
        return default


def vec(v):
    return [round(v.x, 2), round(v.y, 2), round(v.z, 2)]


def sample(w, enc, tag):
    pawn = unreal.GameplayStatics.get_player_pawn(w, 0)
    pc = unreal.GameplayStatics.get_player_controller(w, 0)
    widget = get(enc, 'Widget')
    cam = get(enc, 'BattleCam')
    mesh = pawn.mesh if pawn else None
    anim = mesh.get_anim_instance() if mesh else None
    ia = pawn.get_component_by_class(unreal.load_class(None, '/Game/FoA/Gameplay/BPC_Interactor.BPC_Interactor_C'))
    hud = get(enc, 'BattleHUD')
    labels = {}
    for key in ('Btn_Act0', 'Btn_Act1', 'Btn_Breathe', 'Btn_Mirror', 'Btn_Items', 'Btn_Flee', 'Btn_NextTarget'):
        b = get(widget, key)
        labels[key] = dict(label=str(get(b, 'Label', '')), enabled=b.get_is_enabled() if b else None,
                           focus=b.has_user_focused_descendants(pc) if b else None)
    target = pc.get_view_target() if pc else None
    data = dict(t=round(time.time() - S['start'], 2), tag=tag, state=str(get(enc, 'BattleState')),
                active=get(enc, 'bActive'), player_turn=get(enc, 'bPlayerTurn'),
                camera=vec(cam.get_editor_property('relative_location')) if cam else None,
                fov=get(cam, 'field_of_view'), view=target.get_name() if target else None,
                is_battle=get(anim, 'IsBattle'), move_ignored=pc.is_move_input_ignored(),
                look_ignored=pc.is_look_input_ignored(), cursor=get(pc, 'show_mouse_cursor'),
                suspended=unreal.SystemLibrary.is_timer_paused(ia, 'Scan'),
                hud_visibility=str(hud.get_visibility()) if hud else None,
                cached_hud_visibility=str(get(enc, 'BattleHUDVisibility')),
                player_pos=vec(pawn.get_actor_location()),
                phase=str(get(get(widget, 'Txt_BattlePhase'), 'text', '')),
                narration=str(get(get(widget, 'Txt_Narration'), 'text', '')),
                composure=get(enc, 'Composure'), resolve=get(enc, 'Resolve'),
                command_visibility=str(get(get(widget, 'CommandPanel'), 'visibility', '')),
                labels=labels)
    S['samples'].append(data)
    return data


def finish(reason):
    if S['done']:
        return
    S['done'] = True
    unreal.unregister_slate_post_tick_callback(S['handle'])
    samples = [x for x in S['samples'] if 'state' in x]
    states = {x['state'] for x in samples}
    angles = {tuple(x['camera']) for x in samples if x['camera']}
    active_samples = [x for x in samples if x['active'] and x['is_battle']]
    checks = dict(battle_idle=bool(active_samples),
                  input_locked=bool(active_samples) and all(x['move_ignored'] and x['look_ignored'] for x in active_samples),
                  camera_switches=len(angles) >= 3,
                  readable_labels=any(x['labels']['Btn_Breathe']['label'] == 'Deep breath' for x in samples),
                  hud_hidden_in_battle=bool(active_samples) and all('COLLAPSED' in (x['hud_visibility'] or '').upper() for x in active_samples),
                  interaction_suspended=bool(active_samples) and all(x['suspended'] for x in active_samples),
                  commands_visible=any(x['player_turn'] and 'VISIBLE' in x['command_visibility'].upper() for x in samples),
                  reduce_motion=S['reduce'],
                  input_restored=any(x['tag'] == 'after_end' and not x['is_battle'] and not x['move_ignored']
                                     and not x['look_ignored'] and not x['cursor'] for x in samples))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(dict(reason=reason, states=sorted(states), angles=len(angles), checks=checks,
                                   samples=S['samples']), indent=1), encoding='utf-8')
    print('battle presentation proof', reason, checks, '->', str(OUT))


def tick(_dt):
    try:
        w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
        if not w:
            return finish('pie_ended')
        if time.time() - S['start'] > CAP:
            return finish('cap')
        enc = unreal.GameplayStatics.get_actor_of_class(w, CLS)
        if not enc:
            return
        active = get(enc, 'bActive')
        if not active:
            if S['had_battle']:
                sample(w, enc, 'after_end')
                return finish('encounter_ended')
            return
        S['had_battle'] = True
        state = str(get(enc, 'BattleState'))
        if time.time() - S['last'] > 0.15:
            S['last'] = time.time()
            sample(w, enc, 'state')
        if state not in S['seen']:
            S['seen'].add(state)
            sample(w, enc, 'first_' + state)
            unreal.SystemLibrary.execute_console_command(w, 'Shot showui')
        if state == 'PlayerCommand' and not S['reduce']:
            old = unreal.MaterialLibrary.get_scalar_parameter_value(w, MPC, 'ReduceMotion')
            try:
                unreal.MaterialLibrary.set_scalar_parameter_value(w, MPC, 'ReduceMotion', 1)
                enc.call_method('SetBattleShot', ('EnemyPhase',))
                d = sample(w, enc, 'reduce_motion')
                S['reduce'] = d['camera'] == [-475.0, 80.0, 180.0]
            finally:
                unreal.MaterialLibrary.set_scalar_parameter_value(w, MPC, 'ReduceMotion', old)
                enc.call_method('RestoreBattleShot', ())
    except Exception as err:
        S['samples'].append(dict(tag='error', error=str(err)))
        finish('error')


S['handle'] = unreal.register_slate_post_tick_callback(tick)
print('battle presentation monitor scheduled for', CAP, 'seconds')
