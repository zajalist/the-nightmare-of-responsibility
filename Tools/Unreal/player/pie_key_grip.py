"""PIE proof of the twin-solved key grip (run by record_anim.sh as FOA_PIE_SCRIPT; guarded by proof_guard). Real front
end and wake skip into free play, then the key row's own preconditions (EnterBeat 4, the key in the inventory, the
boots worn, as pie_key_pinch_capture.py), Door.Interact('Use', 'Key'): BeginDoorTool, which now calls
BP_FoAPlayer.BeginGrip on the key. Shoots the first-person frame once the tool is ready ('seated'), half a turn
('turn') and the end of the turn ('bound'), and writes each pose for the twin replay (pie_pose_capture.capture_grip:
the Body's local pose, the key, the plate and the door in world and in hand_r). Ends with '[anim] done'.
Output: Saved/AnimShots/key_grip/<stamp>/."""
import datetime
import json
import os
import sys
import time
import traceback
from pathlib import Path

import unreal

sys.path.insert(0, 'P:/FoA/Tools/Unreal/player')
import pie_pose_capture  # noqa: E402
import importlib
importlib.reload(pie_pose_capture)
import proof_guard  # noqa: E402
import proof_slot  # noqa: E402
import hand_engine_probe
importlib.reload(hand_engine_probe)

KIND = os.environ.get('FOA_TOOL_KIND','key')
FULL_TURN = os.environ.get('FOA_FULL_TURN') == '1'
assert KIND in ('key','screwdriver')
SCREW = int(os.environ.get('FOA_SCREW_INDEX','0'))
assert 0 <= SCREW <= 3
LABEL = 'key' if KIND == 'key' else f'screwdriver_{SCREW}'
folder = Path('P:/FoA/Saved/AnimShots') / (LABEL+'_grip') / datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
folder.mkdir(parents=True, exist_ok=True)
S = dict(start=time.monotonic(), phase=0, rows=[], fin=False, story=False, skipped=False)
G = {}


def resolve():
    w = proof_guard._world()
    find = lambda c: unreal.GameplayStatics.get_actor_of_class(w, unreal.load_class(None, c))  # noqa: E731
    G.update(w=w, p=unreal.GameplayStatics.get_player_character(w, 0), pc=unreal.GameplayStatics.get_player_controller(w, 0),
             fe=find('/Game/FoA/UI/Framework/BP_FoAFrontEnd.BP_FoAFrontEnd_C'), d=find('/Game/FoA/Gameplay/BP_BeatDirector.BP_BeatDirector_C'),
             door=find('/Game/FoA/Gameplay/BP_Door.BP_Door_C'))
    alive = all(v and unreal.SystemLibrary.is_valid(v) for v in G.values())
    if not alive:
        G.clear()
    return alive


def shoot(label):
    p, door = G['p'], G['door']
    parts = {c.get_name(): c for c in door.get_components_by_class(unreal.SceneComponent)}
    body = p.get_editor_property('Body')
    objs = {k: parts[k] for k in ('ToolMesh', 'ToolPlate', 'Mesh') if k in parts}
    if KIND == 'screwdriver':
        objs['HeldTool'] = p.get_editor_property('HeldTool')
    path = pie_pose_capture.capture_grip(body, objs, str(folder / ('pose_' + label + '.json')))
    mh = body.get_anim_instance()
    S['rows'].append(dict(label=label, angle=door.get_editor_property('ToolAngle'), pose=path,
                          grip=[str(p.get_editor_property('GripPose')), p.get_editor_property('GripAlpha')],
                          right_grip_key=mh.get_editor_property('RightGrip_Key'), hand_weight=mh.get_editor_property('ToolHandWeight')))
    pie_pose_capture.request_shot(S, G['w'], folder / (label + '.png'))


def finish(reason):
    if S['fin']:
        return
    S['fin'] = True
    proof_guard.done(S)
    if S.get('probe'):
        (Path('P:/FoA/Saved/AnimShots/review')/(LABEL+'_flip_diagnosis.json')).write_text(json.dumps(S['probe'].rows,indent=2))
        S['probe'].close()
    try:
        if G.get('door') and unreal.SystemLibrary.is_valid(G['door']):
            G['door'].call_method('CancelDoorTool', ())
    except Exception:  # noqa: BLE001
        pass
    proof_slot.leave(S)
    (folder / 'key_grip.json').write_text(json.dumps(dict(reason=reason, rows=S['rows']), indent=1))
    unreal.log('[anim] key grip %s %s' % (reason, folder))
    unreal.log('[anim] done')


def turn_proof(dt):
    door,p = G['door'],G['p']
    body = p.get_editor_property('Body')
    index,angle = door.get_editor_property('ToolStepIndex'),door.get_editor_property('ToolAngle')
    hand = body.get_socket_location('hand_r')
    wrist = hand_engine_probe.angle(hand-body.get_socket_location('lowerarm_r'),body.get_socket_location('middle_01_r')-hand)
    hand_local={'hand_r':pie_pose_capture._xf(body.get_socket_transform('hand_r',pie_pose_capture.PARENT))}
    twist=hand_engine_probe.measure_grip_pose.wrist_rotation(hand_local,S['probe'].fixture['local'],'r')
    S['probe'].rows.setdefault('turn_trace',[]).append(dict(index=index,angle=angle,wrist_deg=wrist,**twist))
    complete = not door.get_editor_property('bToolActive') or KIND=='screwdriver' and index>SCREW
    if complete:
        trace=S['probe'].rows['turn_trace']
        S['probe'].rows['turn_complete']=dict(completed=True,index=index,angle=angle,max_wrist_deg=max(r['wrist_deg'] for r in trace),
            max_axial_twist_deg=max(abs(r['wrist_axial_twist_deg']) for r in trace))
        return finish('full tool turn completed')
    markers = [(SCREW,45),(SCREW,90),(SCREW,180),(SCREW,270)] if KIND=='screwdriver' else [(1,18),(2,42),(3,30),(3,53)]
    sample=S.setdefault('turn_sample',0)
    if sample<len(markers):
        wanted,threshold=markers[sample]
        reached=index>wanted or index==wanted and angle>=threshold-.01
        if reached:
            if 'sample_at' not in S:
                S['sample_at']=time.monotonic()+.12
                return
            if time.monotonic()<S['sample_at']:
                return
            label='turn_%s_%s'%(index,int(round(angle)))
            probe=S['probe']; tool=p.get_editor_property('HeldTool') if KIND=='screwdriver' else door.get_editor_property('ToolMesh')
            probe.fixture_path=folder/(label+'_fixture.json')
            probe.measure_live(tool,G['pc'].player_camera_manager.get_camera_location(),KIND)
            live=json.loads(json.dumps(probe.rows['live']))
            failures=[]
            if live['wrist_deg']>(20 if KIND=='screwdriver' else 35):failures.append('wrist limit')
            if not live['joints_pass']:failures.append('joint limits')
            if not live['wrist_axial_pass']:failures.append('axial wrist twist')
            if live['palm_to_phone_dot']<=0:failures.append('palm facing')
            if min(live['actual_mesh_clearance_mm'].values())<-.01:failures.append('mesh penetration')
            if any(live['actual_mesh_clearance_mm'][d]>3 for d in (hand_engine_probe.DIGITS if KIND=='screwdriver' else ('index','thumb'))):failures.append('contact')
            if not 1<=live['actual_thumb_pad_gap_mm']<=3:failures.append('thumb pad')
            probe.rows.setdefault('turn_samples',[]).append(dict(label=label,live=live,passed=not failures,failures=failures))
            shoot(label);S['turn_sample']+=1;S.pop('sample_at',None)
            return
    # The real key requires easing back at its bound stage; no state or angle is forced.
    turn=-1. if KIND=='key' and index==2 else 1.
    step=min(dt,.05)
    if KIND=='screwdriver' and sample<len(markers):
        step=min(step,max(.0001,(markers[sample][1]-angle)/300))
    door.call_method('AdvanceDoorTool',(turn,step))


def tick(dt):
    try:
        if not proof_guard.live(S) or not proof_slot.enter_once(S):
            return
        if G and not all(v and unreal.SystemLibrary.is_valid(v) for v in G.values()):
            proof_guard.done(S)
            return
        if not pie_pose_capture.collect_shot(S):
            return
        t = time.monotonic() - S['start']
        if not G and not resolve():
            return finish('no PIE world') if t > 25 else None
        if t > (40 if FULL_TURN else 35):
            return finish('time_cap')
        fe, d, door, p = G['fe'], G['d'], G['door'], G['p']
        if S['phase'] == 0 and t > .3:
            fe.call_method('OnSplashFinished', ()); S['phase'] = 1
        elif S['phase'] == 1 and t > 1:
            fe.call_method('OnTitleConfirmed', ()); S['phase'] = 2
        elif S['phase'] == 2 and t > 1.8:
            fe.call_method('WakeUp', ()); S['phase'] = 3
        if S['phase'] == 3:
            story = fe.get_editor_property('Story')
            if story and story.is_in_viewport() and not S['story']:
                story.call_method('Finish', ()); S['story'] = True
                return
            sp = d.get_editor_property('SeqPlayer')
            if not S['skipped'] and sp and sp.is_playing() and not d.get_editor_property('bWakeDone'):
                d.call_method('SkipWakeUp', ()); S['skipped'] = True
                return
            if not d.get_editor_property('bWakeDone'):
                return
            # free first-person play, not the tail of the wake film (keygrip1 shot the bed while it still ran)
            if G['pc'].get_view_target() != p or p.get_editor_property('bCinematic'):
                S.pop('free_at', None)
                return
            S.setdefault('free_at', time.monotonic())
            if time.monotonic() - S['free_at'] < 1.5:
                return
            if p.get_editor_property('PhoneRaise') >= .999:
                phone = unreal.GameplayStatics.get_actor_of_class(G['w'],unreal.load_class(None,'/Game/FoA/UI/Game/BP_Phone.BP_Phone_C'))
                if phone and phone.get_editor_property('bOpen'):
                    review = hand_engine_probe.Probe(G['w'],p.get_editor_property('Body'),'l')
                    try:
                        review.capture(phone.get_component_by_class(unreal.StaticMeshComponent),'screen',Path('P:/FoA/Saved/AnimShots/review/phone_screen_albedo.png'),base_color=True)
                    finally:
                        review.close()
            unreal.SystemLibrary.pause_timer(d, 'PollStoryMoment'); unreal.SystemLibrary.clear_timer(d, 'TryStoryMoment')
            d.call_method('EnterBeat', (4 if KIND == 'key' else 5,))
            inventory = p.get_component_by_class(unreal.load_class(None, '/Game/FoA/Gameplay/BPC_Inventory.BPC_Inventory_C'))
            assert inventory, 'Player inventory component missing after EnterBeat(4)'
            inventory.call_method('Add', ('Key' if KIND == 'key' else 'Screwdriver',))
            boot = door.get_editor_property('BootProgressionSource')
            if boot:
                boot.call_method('SetState', ('Worn', True)); d.call_method('ReportEvent', ('BootsWorn',))
            if KIND == 'screwdriver':
                door.call_method('SetState', ('KeyJammed',True))
            door.call_method('Interact', ('Use', 'Key' if KIND == 'key' else 'Screwdriver'))
            assert door.get_editor_property('bToolActive'), KIND+' row did not start the door tool'
            S['phase'] = 4
        elif S['phase'] == 4 and door.get_editor_property('bToolReady'):
            if KIND == 'screwdriver' and door.get_editor_property('ToolStepIndex') < SCREW:
                door.call_method('AdvanceDoorTool',(1.,.1))
                return
            S['at'] = time.monotonic() + 0.6; S['phase'] = 5  # the grip eases in at 6/s
        elif S['phase'] == 5 and time.monotonic() >= S['at']:
            if 'probe' not in S:
                S['probe'] = hand_engine_probe.Probe(G['w'],p.get_editor_property('Body'),'r')
                S['probe'].fixture_path = Path('P:/FoA/Saved/AnimShots/review')/(LABEL+'_fixture.json')
                S['check_step'] = 0
                return
            probe = S['probe']
            if S['check_step'] == 0:
                probe.prepare(); S['check_step'] = 1
                return
            if S['check_step'] == 1:
                tool = next(c for c in door.get_components_by_class(unreal.StaticMeshComponent) if c.get_name() == 'ToolMesh')
                if KIND == 'screwdriver':
                    tool = p.get_editor_property('HeldTool')
                probe.measure_live(tool,G['pc'].player_camera_manager.get_camera_location(),KIND)
                if KIND == 'screwdriver':
                    xf = pie_pose_capture._xf
                    probe.rows['runtime'] = dict(index=door.get_editor_property('ToolStepIndex'),
                        grip_offset=xf(p.get_editor_property('ToolGripOffset')),
                        driver_transform=xf(door.get_editor_property('ToolDriverTransform')),
                        held_relative=xf(tool.get_relative_transform()),
                        grip_relative=xf(p.get_editor_property('HeldToolGrip').get_relative_transform()))
                review = Path('P:/FoA/Saved/AnimShots/review')
                probe.capture(tool,'side',review/(LABEL+'_side.png'))
                probe.capture(tool,'back',review/(LABEL+'_back.png'))
                probe.capture(tool,'side',review/(LABEL+'_side_albedo.png'),base_color=True)
                S['tests'] = [(d,mode,j) for d in hand_engine_probe.DIGITS for j in (2,3)
                    for mode in ('positive_control','negative_control','baked_curl')]
                S['test_index'] = 0; S['check_step'] = 2
            if S.pop('bend_pending',False):
                probe.read_bend(); S['test_index'] += 1
            if S['test_index'] < len(S['tests']):
                probe.bend_test(*S['tests'][S['test_index']]); S['bend_pending'] = True
                return
            live = probe.rows['live']
            stand = p.get_editor_property('Body').get_world_location()
            live['body_stand_world'] = hand_engine_probe.vec(stand)
            failures = []
            if KIND == 'key' and (stand-unreal.Vector(328.0689,23.0,3.0944)).length() > .2:
                failures.append('stand override')
            if not live['joints_pass']:
                failures.append('joint limits')
            if not live['wrist_axial_pass']:
                failures.append('axial wrist twist')
            if live['wrist_deg'] > (35 if KIND == 'key' else 20):
                failures.append('wrist limit')
            if live['palm_to_phone_dot'] <= 0:
                failures.append('palm points away from key')
            if min(live['actual_mesh_clearance_mm'].values()) < -.01:
                failures.append('actual mesh penetration')
            if any(live['actual_mesh_clearance_mm'][d] > 3 for d in (('index','thumb') if KIND == 'key' else hand_engine_probe.DIGITS)):
                failures.append('pinch contact')
            if not 1 <= live['actual_thumb_pad_gap_mm'] <= 3:
                failures.append('thumb pad contact')
            for row in probe.rows['curl_tests']:
                if (row['toward_palm_cm'] > 0) != (row['mode'] != 'negative_control'):
                    failures.append('%s joint %s %s' % (row['digit'],row['joint'],row['mode']))
            probe.rows['numeric_acceptance'] = dict(passed=not failures,failures=failures)
            probe.rows['engine']=unreal.SystemLibrary.get_engine_version()
            probe.rows['seated']=json.loads(json.dumps(live))
            shoot('seated'); S['phase'] = 6
        elif S['phase'] == 6 and FULL_TURN:
            turn_proof(dt)
        elif S['phase'] == 6:
            door.call_method('AdvanceDoorTool', (1., min(dt, .1)))
            if door.get_editor_property('ToolAngle') >= 22:
                shoot('turn'); S['phase'] = 7
        elif S['phase'] == 7:
            door.call_method('AdvanceDoorTool', (1., min(dt, .1)))
            if door.get_editor_property('ToolStepIndex') > (0 if KIND == 'key' else SCREW) or door.get_editor_property('ToolAngle') >= 44:
                shoot('bound'); S['at'] = time.monotonic() + 0.2; S['phase'] = 8
        elif S['phase'] == 8 and time.monotonic() >= S['at']:
            finish('measured (judge native checks and actual PIE frames)')
    except Exception as e:  # noqa: BLE001
        S['rows'].append(dict(error=repr(e),traceback=traceback.format_exc(),phase=S['phase']))
        finish('error ' + repr(e))


proof_guard.arm(S, tick, 'key grip')
