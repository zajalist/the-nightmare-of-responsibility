"""Bounded independent UE skin diagnosis; run only through record_anim.sh."""
import importlib
import json
import os
import sys
import time
import traceback
from pathlib import Path
import unreal

sys.path.insert(0, 'P:/FoA/Tools/Unreal/player')
import proof_guard
import proof_slot
import pie_pose_capture
import hand_engine_probe
importlib.reload(hand_engine_probe)
importlib.reload(pie_pose_capture)

OUT = Path('P:/FoA/Saved/AnimShots/review')
OUT.mkdir(parents=True, exist_ok=True)
TAG = os.environ.get('FOA_HAND_TAG','phone_flip')
EXPOSURE = float(os.environ.get('FOA_REVIEW_EXPOSURE','0'))
S = dict(start=time.monotonic(), phase=0, probe=None, tests=[], index=0)


def restore_exposure():
    if 'exposure_before' in S:
        value = S.pop('exposure_before')
        unreal.SystemLibrary.execute_console_command(S['probe'].world,'r.ExposureOffset '+str(value))
        actual = unreal.SystemLibrary.get_console_variable_float_value('r.ExposureOffset')
        S['probe'].rows['review_exposure']['restored'] = abs(actual-value)<1e-5
        assert abs(actual-value)<1e-5, 'review exposure was not restored'


def finish(reason):
    restore_exposure()
    proof_guard.done(S)
    probe = S.get('probe')
    rows = probe.rows if probe else {}
    rows['reason'] = reason
    if probe:
        probe.close()
    proof_slot.leave(S)
    (OUT / (TAG+'_diagnosis.json')).write_text(json.dumps(rows, indent=2))
    unreal.log('[anim] phone flip ' + reason)
    unreal.log('[anim] done')


def tick(dt):
    try:
        w = proof_guard.live(S)
        if not w or not proof_slot.enter_once(S):
            return
        if not pie_pose_capture.collect_shot(S):
            return
        t = time.monotonic() - S['start']
        if t > 35:
            return finish('time_cap')
        p = unreal.GameplayStatics.get_player_character(w, 0)
        pc = unreal.GameplayStatics.get_player_controller(w, 0)
        if 'fe' not in S:
            S['fe'] = unreal.GameplayStatics.get_actor_of_class(w, unreal.load_class(None, '/Game/FoA/UI/Framework/BP_FoAFrontEnd.BP_FoAFrontEnd_C'))
            S['director'] = unreal.GameplayStatics.get_actor_of_class(w, unreal.load_class(None, '/Game/FoA/Gameplay/BP_BeatDirector.BP_BeatDirector_C'))
        fe, director = S['fe'], S['director']
        if S['phase'] == 0 and t > .3:
            fe.call_method('OnSplashFinished', ()); S['phase'] = 1
        elif S['phase'] == 1 and t > 1:
            fe.call_method('OnTitleConfirmed', ()); S['phase'] = 2
        elif S['phase'] == 2 and t > 1.8:
            fe.call_method('WakeUp', ()); S['phase'] = 3
        if S['phase'] < 3:
            return
        story = fe.get_editor_property('Story')
        if story and story.is_in_viewport() and not S.get('story_done'):
            story.call_method('Finish', ()); S['story_done'] = True
            return
        seq = director.get_editor_property('SeqPlayer')
        if not S.get('skipped') and seq and seq.is_playing() and not director.get_editor_property('bWakeDone'):
            director.call_method('SkipWakeUp', ()); S['skipped'] = True
            return
        if not director.get_editor_property('bWakeDone'):
            return
        if 'phone' not in S:
            phone = unreal.GameplayStatics.get_actor_of_class(w, unreal.load_class(None, '/Game/FoA/UI/Game/BP_Phone.BP_Phone_C'))
            if not phone or not phone.get_editor_property('bOpen'):
                return
            S.setdefault('opened', t)
            if t - S['opened'] < 1.5:
                return
            S['phone'] = phone.get_component_by_class(unreal.StaticMeshComponent)
            S['probe'] = hand_engine_probe.Probe(w, p.get_editor_property('Body'), 'l')
            if TAG != 'phone_flip':
                S['probe'].fixture_path = OUT / (TAG+'_fixture.json')
            return
        probe, phone = S['probe'], S['phone']
        probe.rows.setdefault('hold_timeline',[]).append(dict(t=t,phase=S['phase'],state=probe.hold_state(phone)))
        if S['phase'] == 3:
            probe.prepare()
            S['phase'] = 4
            return
        if S['phase'] == 4:
            probe.measure_live(phone, pc.player_camera_manager.get_camera_location())
            pie_pose_capture.capture_phone(probe.body, phone, str(OUT / (TAG+'_pose.json')))
            if EXPOSURE:
                S['exposure_before'] = unreal.SystemLibrary.get_console_variable_float_value('r.ExposureOffset')
                value = S['exposure_before']+EXPOSURE
                unreal.SystemLibrary.execute_console_command(w,'r.ExposureOffset '+str(value))
                assert abs(unreal.SystemLibrary.get_console_variable_float_value('r.ExposureOffset')-value)<1e-5
                probe.rows['review_exposure'] = dict(before=S['exposure_before'],during=value,restored=False)
            pie_pose_capture.request_shot(S, w, OUT / (TAG+'_fp.png'))
            S['phase'] = 5
            return
        if S['phase'] in (5, 6):
            label = 'screen' if S['phase'] == 5 else 'back'
            probe.capture(phone, label, OUT / (TAG+'_' + label + '.png'))
            S['phase'] += 1
            return
        if S['phase'] in (7,8):
            albedo = S['phase'] == 8
            probe.capture(phone,'side',OUT/(TAG+('_side_albedo.png' if albedo else '_side.png')),base_color=albedo)
            if albedo:
                restore_exposure()
            S['phase'] += 1
            return
        if not S['tests']:
            S['tests'] = [(d,m,j) for d in hand_engine_probe.DIGITS for j in ((2,) if TAG == 'phone_flip' else (2,3))
                for m in ('positive_control','negative_control','baked_curl')]
        if S.pop('pending', False):
            probe.read_bend()
            S['index'] += 1
        if S['index'] == len(S['tests']):
            if TAG != 'phone_flip':
                if not S.get('tapped'):
                    p.call_method('PhoneTap', ())
                    S['tapped'] = time.monotonic()
                    return
                if time.monotonic()-S['tapped'] < .10:
                    return
                held = probe.rows['live']
                probe.fixture_path = OUT / (TAG+'_tap_fixture.json')
                probe.measure_live(phone,pc.player_camera_manager.get_camera_location())
                probe.rows['tap_live'] = probe.rows['live']
                probe.rows['live'] = held
                original = phone.get_relative_transform().rotation
                try:
                    flipped = unreal.MathLibrary.multiply_quat_quat(original,unreal.Quat(1,0,0,0))
                    phone.set_relative_rotation(flipped.rotator(),False,True)
                    normal = phone.get_world_transform().rotation.rotate_vector(unreal.Vector(0,0,-1))
                    probe.rows['flipped_actual_control_deg'] = hand_engine_probe.angle(normal,
                        pc.player_camera_manager.get_camera_location()-phone.get_world_location())
                finally:
                    phone.set_relative_rotation(original.rotator(),False,True)
                failures = []
                for label,row in (('hold',held),('tap',probe.rows['tap_live'])):
                    if not row['joints_pass']:
                        failures.append(label+' joint limits')
                    if not row['wrist_axial_pass']:
                        failures.append(label+' axial wrist twist')
                    if row['palm_against_back_deg'] > 35 or row['screen_to_eye_deg'] > 30:
                        failures.append(label+' orientation')
                    if min(row['actual_mesh_clearance_mm'].values()) < -.01:
                        failures.append(label+' actual mesh penetration')
                    state = row['hold_state']
                    if min(state['player']['PhoneRaise'],state['player']['PhoneRaiseTarget'],state['anim']['PhoneIKWeight'],state['anim']['PhoneGripWeight']) < .999:
                        failures.append(label+' sampled outside full phone hold')
                if any(not 1 <= held['actual_mesh_clearance_mm'][d] <= 3 for d in hand_engine_probe.DIGITS):
                    failures.append('actual finger contact outside 1-3 mm')
                if not 1 <= held['actual_thumb_pad_gap_mm'] <= 3:
                    failures.append('actual thumb pad contact')
                if held['thumb_pad_to_glass_deg'] > 35:
                    failures.append('thumb pad facing')
                if TAG.startswith('phone_bezel'):
                    if held['thumb_screen_interior_overlap_vertices']!=0:failures.append('rest thumb covers screen')
                    if any('IGNORE' not in v.upper() for v in held['phone_collision'].values()):failures.append('phone blocks Pawn or Camera')
                if any(held['tips_phone_local'][d][1] >= -3.55 for d in hand_engine_probe.DIGITS[:4]):
                    failures.append('far-edge wrap')
                for row in probe.rows['curl_tests']:
                    if (row['toward_palm_cm'] > 0) != (row['mode'] != 'negative_control'):
                        failures.append('%s joint %s %s' % (row['digit'],row['joint'],row['mode']))
                if probe.rows['flipped_actual_control_deg'] <= 30:
                    failures.append('actual flipped-phone negative control')
                probe.rows['numeric_acceptance'] = dict(passed=not failures,failures=failures)
            return finish('measured')
        probe.bend_test(*S['tests'][S['index']])
        S['pending'] = True
    except Exception:
        finish(traceback.format_exc())


proof_guard.arm(S, tick, 'phone_flip')
