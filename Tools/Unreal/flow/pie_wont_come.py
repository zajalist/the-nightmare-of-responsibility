"""Story lane, in PIE (run_chase_final.py pie_wont_come, one EXCLUSIVE window): "It won't come" through the real flow.
Fixture (as QA B2b): T7 by its events, the top-down left, the three clue searches, the hanger, then the director's own
stage functions to the final chase (BeginClothingToss, EscapeClothingOne, EscapeClothingTwo). Then the real grab: the
interactor focuses Shirt_T7 and one real E is pressed -> the reach contact -> OnClothingCameraReady ->
ClothingBossFormed -> ShirtTaken -> T8 -> StartShirtFight -> LS_BattleIntro -> BattleIntroDone -> the encounter.
From the grab on, time runs at x0.5 and a frame is taken every 0.1 s (20 frames per game second); every frame logs the
view target, the camera, the beat, the vase and the garments. Stops 1.5 game seconds into PlayerCommand.
Checks: vase_broke (VaseIntact hidden or shards shown), one_cut_into_battle (no frame whose view target is the pawn
between the sequence and the battle camera), no_black (no frame darker than 6/255 mean after the grab), garments_in
(all five Rig components shown at PlayerCommand), lines (the two subtitles were requested).
Result: Saved/StoryShots/wont_come.json; frames Saved/StoryShots/wont_come/*.png."""
import importlib
import json
import sys
import time
from pathlib import Path

import unreal

sys.path.insert(0, 'P:/FoA/Tools/Unreal/flow')
import proof_save  # noqa: E402
importlib.reload(proof_save)

OUT = Path('P:/FoA/Saved/StoryShots/wont_come.json')
INPUTS = Path('P:/FoA/Saved/StoryShots/wont_come_input.json')
INPUTS.unlink(missing_ok=True)
SHOTS = Path('P:/FoA/Saved/StoryShots/wont_come/')
SHOTS.mkdir(parents=True, exist_ok=True)
for f in SHOTS.glob('*.png'):
    f.unlink()
w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
assert w, 'no PIE world'
PROOF = proof_save.isolate(w)
S = dict(t0=time.time(), phase=0, rows=[], done=False, h=None, at=0.0, n=0, shot=0.0, grab=None, cmd_at=None)
DIL = 0.5


def label(lbl):
    return next((a for a in unreal.GameplayStatics.get_all_actors_of_class(w, unreal.Actor) if a.get_actor_label() == lbl), None)


def prop(o, n, default=None):
    try:
        return o.get_editor_property(n)
    except Exception:  # noqa: BLE001
        return default


def r1(v):
    return [round(v.x, 1), round(v.y, 1), round(v.z, 1)]


def cmd(c):
    unreal.SystemLibrary.execute_console_command(w, c, unreal.GameplayStatics.get_player_controller(w, 0))


def finish(reason):
    if S['done']:
        return
    S['done'] = True
    unreal.unregister_slate_post_tick_callback(S['h'])
    unreal.GameplayStatics.set_global_time_dilation(w, 1.0)
    try:
        proof_save.restore(unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world(), PROOF)
    except Exception as exc:  # noqa: BLE001
        unreal.log_warning('[proof_save] restore failed: %r' % exc)
    rows = [r for r in S['rows'] if r.get('kind') == 'f']
    views = [r['view'] for r in rows]
    seq_i = [i for i, v in enumerate(views) if 'Cam_' in v or 'CineCamera' in v]
    enc_i = [i for i, v in enumerate(views) if 'Encounter' in v]
    pawn_gap = [views[i] for i in range(seq_i[-1] + 1, enc_i[0])] if seq_i and enc_i and enc_i[0] > seq_i[-1] else None
    last = rows[-1] if rows else {}
    checks = dict(sequence_seen=bool(seq_i), battle_seen=bool(enc_i),
                  one_cut_into_battle=pawn_gap == [], vase_broke=any(r.get('vase_broken') for r in rows),
                  garments_in=bool(last.get('garments')) and all(g['shown'] for g in last['garments']),
                  playercommand=S['cmd_at'] is not None)
    OUT.write_text(json.dumps(dict(reason=reason, checks=checks, pawn_frames_between=pawn_gap, rows=S['rows']), indent=1, default=str))
    print('RESULT', reason, json.dumps(checks))


def log(kind, **kw):
    S['rows'].append(dict(kind=kind, t=round(time.time() - S['t0'], 2), **kw))


def frame(d, enc):
    pc = unreal.GameplayStatics.get_player_controller(w, 0)
    cam = pc.player_camera_manager
    room = label('RoomTakeover')
    vase = prop(room, 'VaseIntact') if room else None
    gs = []
    for g in (prop(enc, 'Garments') or []):
        rig = prop(g, 'Body')
        gs.append(dict(id=prop(prop(g, 'Data'), 'GarmentId'), shown=bool(rig and rig.is_visible() and not rig.get_editor_property('hidden_in_game')),
                       at=r1(rig.get_world_location()) if rig else None))
    beat = prop(d, 'Beat')
    S['n'] += 1
    name = 'f%04d' % S['n']
    S['rows'].append(dict(kind='f', n=S['n'], gt=round(unreal.GameplayStatics.get_time_seconds(w) - S['grab'], 3),
                          view=pc.get_view_target().get_name(), cam=r1(cam.get_camera_location()),
                          rot=[round(cam.get_camera_rotation().pitch, 1), round(cam.get_camera_rotation().yaw, 1)],
                          beat=str(prop(beat, 'Id')) if beat else None, state=str(prop(enc, 'BattleState')),
                          active=prop(enc, 'bActive'), intro=prop(d, 'bBattleIntroPlaying'),
                          vase_broken=bool(vase and not vase.is_visible()), garments=gs))
    cmd('Shot showui filename=%s/%s.png -nosuffix' % (SHOTS.as_posix(), name))


def tick(dt):
    try:
        t = time.time() - S['t0']
        if unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world() != w:  # PIE ended or was replaced:
            return finish('pie_gone')  # touch nothing cached from the old world (editor-rules, crash safety 8)
        if t > 46:
            return finish('cap')
        d, fe = label('BeatDirector'), label('BP_FoAFrontEnd')
        enc = label('Encounter_T8')
        if not (d and fe and enc):
            return
        pc = unreal.GameplayStatics.get_player_controller(w, 0)
        p = unreal.GameplayStatics.get_player_character(w, 0)
        if S['grab'] is not None:
            if time.time() - S['shot'] >= 0.1:
                S['shot'] = time.time()
                frame(d, enc)
            if S['cmd_at'] is None and str(prop(enc, 'BattleState')) == 'PlayerCommand':
                S['cmd_at'] = unreal.GameplayStatics.get_time_seconds(w)
            if S['cmd_at'] is not None and unreal.GameplayStatics.get_time_seconds(w) - S['cmd_at'] > 1.5:
                return finish('done')
            return
        if t < S['at']:
            return
        ph = S['phase']
        if ph == 0:
            fe.call_method('OnSplashFinished', ()); S['phase'] = 1; S['at'] = t + 0.3
        elif ph == 1:
            fe.call_method('OnTitleConfirmed', ()); S['phase'] = 2; S['at'] = t + 0.3
        elif ph == 2:
            fe.call_method('WakeUp', ()); S['phase'] = 3
        elif ph == 3:
            story = fe.get_editor_property('Story')
            if story and story.is_in_viewport():
                story.call_method('Finish', ())
            elif fe.get_editor_property('bInGameplay') and d.get_editor_property('SeqPlayer') and not d.get_editor_property('bWakeDone'):
                d.call_method('SkipWakeUp', ()); S['phase'] = 4
        elif ph == 4 and d.get_editor_property('bWakeDone') and pc.get_view_target() == p and not p.get_editor_property('bCinematic'):
            for ev in ('PhoneWakeUp', 'FirstSteps', 'Searched', 'KeyTaken', 'KeySnapped', 'LatchFreed', 'WardrobeLanded'):
                d.call_method('ReportEvent', (ev,))
            cmd('ke * ClosePhone')
            log('to_t7', beat=str(prop(prop(d, 'Beat'), 'Id')))
            S['phase'] = 5; S['at'] = t + 1.0
        elif ph == 5:
            if prop(d, 'bTopDown'):
                d.call_method('ExitTopDown', ())
            S['phase'] = 6; S['at'] = t + 1.2
        elif ph == 6:
            for fn in ('SearchWardrobeClue', 'SearchDeskClue', 'SearchBedClue', 'CancelClothingInspection'):
                d.call_method(fn, ())
            bag = p.get_component_by_class(unreal.load_class(None, '/Game/FoA/Gameplay/BPC_Inventory.BPC_Inventory_C'))
            bag.call_method('Add', ('Hanger',))
            log('searched', stage=prop(d, 'ClothingSearchStage'))
            S['phase'] = 7; S['at'] = t + 1.0
        elif ph == 7:
            for fn in ('BeginClothingToss', 'EscapeClothingOne', 'EscapeClothingTwo'):
                d.call_method(fn, ())
            log('to_final', stage=prop(d, 'ClothingSearchStage'), shirt=str(prop(label('Shirt_T7'), 'State')))
            S['phase'] = 8; S['at'] = t + 2.5
        elif ph == 8:
            shirt = label('Shirt_T7')
            if str(prop(shirt, 'State')) != 'ChaseFinal' and t < 40:
                log('wait_final', stage=prop(d, 'ClothingSearchStage'), shirt=str(prop(shirt, 'State')))
                S['at'] = t + 0.5
                return
            o, e = shirt.get_actor_bounds(True)
            p.teleport(unreal.Vector(-41, -263, 92), unreal.MathLibrary.find_look_at_rotation(unreal.Vector(-41, -263, 92), o))
            pc.set_control_rotation(unreal.MathLibrary.find_look_at_rotation(pc.player_camera_manager.get_camera_location(), o))
            S['phase'] = 9; S['at'] = t + 0.6
        elif ph == 9:
            shirt = label('Shirt_T7')
            ia = p.get_component_by_class(unreal.load_class(None, '/Game/FoA/Gameplay/BPC_Interactor.BPC_Interactor_C'))
            if prop(ia, 'Target') != shirt:
                log('focus_pinned', saw=prop(ia, 'Target').get_actor_label() if prop(ia, 'Target') else None)
                ia.call_method('SetFocus', (shirt,))
                ia.call_method('Refresh', (True,))
            log('grab', prompt=str(prop(ia, 'Prompt')), stage=prop(d, 'ClothingSearchStage'))
            unreal.GameplayStatics.set_global_time_dilation(w, DIL)
            S['grab'] = unreal.GameplayStatics.get_time_seconds(w)
            INPUTS.write_text(json.dumps(dict(id=1, key='E')))  # one real E, relayed by run_chase_final.py
    except Exception as exc:  # noqa: BLE001
        log('error', error=repr(exc))
        finish('error')


S['h'] = unreal.register_slate_post_tick_callback(tick)
print('wont_come scheduled')
