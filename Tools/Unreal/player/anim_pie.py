"""Anim lane proof run inside a running PIE (a slate tick callback; reads the PIE world, drives the pawn like a player).
  python Tools/Unreal/ue_remote.py Tools/Unreal/player/anim_pie.py FOA_EXCLUSIVE=1     (record_anim.sh does it all)
Skips splash, title and the wake-up, waits for control, then runs four phases and 'Shot's the game viewport in each:
  still    behind-the-shoulder and 3/4-front stills
  loco     12 s: walk, stop, a hard turn, walk, jog, stop (headings picked from free space so he never hits a wall)
  interact walks up to a drawer or door and presses Interact through BPC_Interactor (the real montage path)
  idle     hands off for FOA_IDLE s at the room centre, camera on his 3/4 front
Each phase start is logged as '[anim] phase=<name> wall=<epoch s>' so record_anim.sh can sort the frames by time.
  sand     walks across the biggest Sand-tagged floor actor (foot-plant puffs), then the host API and BP_Nightmare checks
FOA_TARGETS: interactable labels to try in order (first one present wins). FOA_PLAN=idle: control, stills, then only
the idle for FOA_IDLE s (idle breaks are random: give it 25+ s). Ends PIE when done."""
import math
import os
import time
import json
from pathlib import Path

import unreal

IDLE = float(os.environ.get('FOA_IDLE', '7'))
TEEN_QA = os.environ.get('FOA_TEEN_QA') == '1'
NO_SHOTS = os.environ.get('FOA_NO_SHOTS') == '1'
CINE_S = float(os.environ.get('FOA_CINE_S', '38'))  # PLAN=cine: seconds of LS_WakeUp to film
PLAN = os.environ.get('FOA_PLAN', 'full')  # read now: ue_remote removes the run's env vars before the ticks run
NIGHTMARE = os.environ.get('FOA_NIGHTMARE', '1') == '1'
INTERACT_S = float(os.environ.get('FOA_INTERACT_S', '4.5'))
TARGETS = [t for t in os.environ.get('FOA_TARGETS', 'Commode_GothicCommode_01_door01,Boot_R').split(',') if t]
FE_C = '/Game/FoA/UI/Framework/BP_FoAFrontEnd.BP_FoAFrontEnd_C'
# loco script: (seconds, mode, turn in degrees relative to the free heading picked at the segment start)
LOCO = [(2.6, 'walk', 0), (1.3, 'stop', 0), (2.4, 'walk', 150), (2.4, 'jog', 0), (1.5, 'stop', 0), (1.8, 'walk', -90)]
S = {'t0': time.time(), 'phase': 'menu', 'mark': time.time(), 'shot': 0.0, 'h': None, 'seg': -1, 'heading': 0.0,
     'goal': None, 'target': None}
SHOT_DT = {name: .75 for name in ('loco','interact','idle','nightmare','sand','turn')}


def log(msg):
    unreal.log(f'[anim] {msg} t={time.time() - S["t0"]:.2f}')


def phase(name):
    S['phase'], S['mark'] = name, time.time()
    log(f'phase={name} wall={time.time():.3f}')


def cmd(w, c):
    if NO_SHOTS and c == 'Shot':
        return
    unreal.SystemLibrary.execute_console_command(w, c)


def free(w, pawn, yaw, reach=420.0):
    """Free distance (cm) along yaw from knee height, a 36 cm sphere sweep."""
    p = pawn.get_actor_location()
    a = math.radians(yaw)
    start = unreal.Vector(p.x, p.y, p.z - 35.0)
    end = unreal.Vector(p.x + math.cos(a) * reach, p.y + math.sin(a) * reach, p.z - 35.0)
    h = unreal.SystemLibrary.sphere_trace_single(w, start, end, 36.0, unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, False,
                                                 [pawn], unreal.DrawDebugTrace.NONE, True)
    if isinstance(h, tuple):
        h = h[1] if h[0] else None
    if not h:
        return reach
    t = h.to_tuple()
    return reach * t[2] if t[0] else reach


def freest(w, pawn, want):
    """Heading closest to `want` with at least 2 m free, else the freest of 12."""
    best = None
    for i in range(12):
        yaw = want + i * 30.0
        d = free(w, pawn, yaw)
        off = abs((yaw - want + 540.0) % 360.0 - 180.0)
        score = (d >= 200.0) * 1000.0 - off + d * 0.1
        if not best or score > best[0]:
            best = (score, yaw)
    return best[1]


def qa_full_body_camera(w,pawn,pc):
    """PIE-only diagnostic camera: side/three-quarter body plus visible floor.

The shipping spring arm collides with bedroom walls and can crop both feet.
Choose a clear side and fit a245cm vertical span without touching game assets.
"""
    camera=S.get('qa_camera')
    if camera is None:
        before={a.get_path_name() for a in unreal.GameplayStatics.get_all_actors_of_class(w,unreal.CameraActor)}
        cmd(w,'summon /Script/Engine.CameraActor')
        made=[a for a in unreal.GameplayStatics.get_all_actors_of_class(w,unreal.CameraActor) if a.get_path_name() not in before]
        assert len(made)==1,'QA camera did not spawn'
        camera=made[0];S['qa_camera']=camera
    now=time.time()
    if now-S.get('qa_camera_check',0)>.3:
        heading=S.get('heading',pawn.get_actor_rotation().yaw)
        candidates=[heading+angle for angle in (-100,100,-135,135)]
        if 'qa_camera_yaw' in S:candidates.insert(0,S['qa_camera_yaw'])
        available=[(free(w,pawn,yaw,420),yaw) for yaw in candidates]
        distance,yaw=max(available,key=lambda item:item[0])
        if S.get('qa_camera_segment')==S.get('seg') and available[0][0]>=240:
            distance,yaw=available[0]
        S.update(qa_camera_check=now,qa_camera_yaw=yaw,qa_camera_distance=max(145,min(400,distance-28)),qa_camera_segment=S.get('seg'))
    distance=S['qa_camera_distance'];angle=math.radians(S['qa_camera_yaw'])
    aim=pawn.get_actor_location()-unreal.Vector(0,0,5)
    eye=aim+unreal.Vector(math.cos(angle)*distance,math.sin(angle)*distance,70)
    camera.set_actor_location_and_rotation(eye,unreal.MathLibrary.find_look_at_rotation(eye,aim),False,True)
    focal=math.degrees(2*math.atan(245/(2*distance*(9/16))))
    camera.get_editor_property('camera_component').set_field_of_view(min(110,max(55,focal)))
    pc.set_view_target_with_blend(camera,0)


def finish():
    if TEEN_QA and S.get('feet'):
        Path('P:/FoA/Saved/AnimShots/loco_feet_latest.json').write_text(json.dumps(S['feet']))
    if S['h'] is not None:
        unreal.unregister_slate_post_tick_callback(S['h'])
        if getattr(unreal, '_foa_anim_pie_handle', None) == S['h']:
            unreal._foa_anim_pie_handle = None
        S['h'] = None
    log('done')
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_end_play()


def in_control(w, pawn, pc):
    fe = unreal.GameplayStatics.get_actor_of_class(w, unreal.load_class(None, FE_C))
    vt = pc.get_view_target() if pc else None
    return bool(pawn and vt == pawn and (not fe or fe.get_editor_property('bInGameplay')))


def ease_cam(pc, want_yaw, pitch, dt, rate=2.0):
    cur = pc.get_control_rotation()
    d = (want_yaw - cur.yaw + 540.0) % 360.0 - 180.0
    dp = (pitch - cur.pitch + 540.0) % 360.0 - 180.0  # -8 deg is stored as 352: ease the short way round
    k = min(1.0, rate * dt)
    pc.set_control_rotation(unreal.Rotator(roll=0.0, pitch=cur.pitch + dp * k, yaw=cur.yaw + d * k))


def find(w, label):
    for a in unreal.GameplayStatics.get_all_actors_of_class(w, unreal.Actor):
        if a.get_actor_label() == label:
            return a
    return None


LIE_CLIP = os.environ.get('FOA_CLIP', '/Game/FoA/Characters/Player/Anims/Wake/AS_FoA_Lie_Breathe')
LIE_AT = (unreal.Vector(238.04, -191.28, 155.04), unreal.Rotator(roll=0.0, pitch=0.0, yaw=-179.97))  # Saved/WakeUp/placement.json lay
LIE_CAMS = [('side', unreal.Vector(262.0, -20.0, 110.0), unreal.Vector(262.0, -191.0, 72.0)),
            ('pillow', unreal.Vector(250.0, -150.0, 150.0), unreal.Vector(325.5, -191.0, 88.0)),
            ('foot', unreal.Vector(150.0, -191.0, 125.0), unreal.Vector(270.0, -191.0, 72.0))]


def lie_step(w, pawn, pc, now, el):
    if 'lie' not in S:
        pawn.call_method('SetCinematic', (True,))
        pawn.get_editor_property('character_movement').disable_movement()
        pawn.set_actor_enable_collision(False)
        pawn.set_actor_location_and_rotation(LIE_AT[0], LIE_AT[1], False, True)
        mesh = pawn.get_editor_property('mesh')
        mesh.set_animation_mode(unreal.AnimationMode.ANIMATION_SINGLE_NODE)
        mesh.play_animation(unreal.load_asset(LIE_CLIP), True)
        cmd(w, 'summon /Script/Engine.CameraActor')
        S['lie'] = {'t': now, 'shot': 0}
        log(f'lie placed, clip {LIE_CLIP.split("/")[-1]}')
        return
    L = S['lie']
    if now - L['t'] > 1.0 and not L.get('faces'):  # where each head really points (Manny source vs retargeted body)
        L['faces'] = True
        for c in pawn.get_components_by_class(unreal.SkeletalMeshComponent):
            if c.get_name() not in ('CharacterMesh0', 'Body'):
                continue
            skel = c.get_skeletal_mesh_asset().get_editor_property('skeleton')
            ref = unreal.AnimPoseExtensions.get_reference_pose(skel)
            rq = unreal.AnimPoseExtensions.get_bone_pose(ref, 'head', unreal.AnimPoseSpaces.WORLD).rotation
            face_local = rq.unrotate_vector(unreal.Vector(0, 1, 0))
            face = c.get_socket_rotation('head').quaternion().rotate_vector(face_local)
            log(f"face {c.get_name()} world {face} (z up; -x toward his feet here)")
    shots = [(tag, name, frm, at) for tag in ('mh', 'manny') for name, frm, at in LIE_CAMS]
    k = int((now - L['t'] - 1.2) // 1.0)  # one shot a second after a settle
    if k < 0 or k == L['shot'] - 1:
        return
    if k >= len(shots):
        return finish()
    tag, name, frm, at = shots[k]
    cam = unreal.GameplayStatics.get_actor_of_class(w, unreal.CameraActor)
    if not cam:
        log('lie: no summoned camera')
        return finish()
    if tag == 'manny' and not L.get('swapped'):
        L['swapped'] = True
        pawn.get_editor_property('mesh').set_visibility(True, False)
        for c in pawn.get_components_by_class(unreal.SkeletalMeshComponent):
            if c.get_name() != 'CharacterMesh0':
                c.set_visibility(False, False)
        for g in pawn.get_components_by_class(unreal.GroomComponent):
            g.set_visibility(False, False)
    cam.set_actor_location_and_rotation(frm, unreal.MathLibrary.find_look_at_rotation(frm, at), False, True)
    pc.set_view_target_with_blend(cam, 0.0)
    if k > 0 or L['shot'] > 0:
        pass
    L['shot'] = k + 1
    log(f'phase=lie_{name}_{tag} wall={time.time() + 0.6:.3f}')
    S['lie_shot_at'] = now + 0.6


def tick(dt):
    try:
        step(dt)
    except Exception as e:  # one bad tick must not spam the log for the rest of the burst
        log(f'error {e!r}')
        finish()


def step(dt):
    w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
    if not w:
        return finish()
    now, el = time.time(), time.time() - S['mark']
    pawn = unreal.GameplayStatics.get_player_pawn(w, 0)
    pc = unreal.GameplayStatics.get_player_controller(w, 0)
    ph = S['phase']
    if TEEN_QA and ph in ('loco','idle'):
        qa_full_body_camera(w,pawn,pc)
        parts = {c.get_name():c for c in pawn.get_components_by_class(unreal.SkeletalMeshComponent)}
        ai = parts['CharacterMesh0'].get_anim_instance()
        vec = lambda v:[v.x,v.y,v.z]
        row = dict(t=unreal.GameplayStatics.get_time_seconds(w),phase=ph,seg=S['seg'],
                   pos=vec(pawn.get_actor_location()),velocity=vec(pawn.get_velocity()),yaw=pawn.get_actor_rotation().yaw,
                   rates={k:ai.get_editor_property(k) for k in ('GroundSpeed','WalkPlayRate','JogPlayRate','StartDone')})
        for name in ('CharacterMesh0','Body'):
            c=parts[name]
            row[name]={str(b):vec(c.get_socket_location(b)) for b in c.get_all_socket_names() if any(s in str(b).lower() for s in ('foot','toe','ball'))}
        S.setdefault('feet',[]).append(row)
    if S.get('lie_shot_at') and now >= S['lie_shot_at']:
        S['lie_shot_at'] = None
        cmd(w, 'Shot')
    if ph in SHOT_DT and now - S['shot'] > SHOT_DT[ph]:
        S['shot'] = now
        cmd(w, 'Shot')
    if ph == 'menu':
        if el > 0.5:
            for c in ('viewmode lit', 'ke * OnSplashFinished', 'ke * OnTitleConfirmed', 'ke * WakeUp'):
                cmd(w, c)
            phase('wake')
    elif ph == 'wake' and PLAN == 'cine':  # film the real LS_WakeUp from the game viewport: no skip, a frame every 0.2 s
        if now - S['shot'] > 0.2:
            S['shot'] = now
            cmd(w, 'Shot')
        if el > CINE_S:
            return finish()
    elif ph == 'wake':
        if el > 3.0 and now - S.get('skip', 0.0) > 2.0:  # the skip only lands once the cinematic is playing
            S['skip'] = now
            cmd(w, 'ke * SkipWakeUp')
        if in_control(w, pawn, pc) and el > 3.5 or el > 25.0:
            S['heading'] = pawn.get_actor_rotation().yaw
            log(f'control={in_control(w, pawn, pc)}')
            parts = {c.get_name(): c for c in pawn.get_components_by_class(unreal.SkeletalMeshComponent)}
            log('runtime meshes=' + str({n:c.get_skeletal_mesh_asset().get_name() if c.get_skeletal_mesh_asset() else None for n,c in parts.items()}))
            log('runtime source=' + str(pawn.get_editor_property('Mesh').get_anim_instance().get_class().get_path_name()))
            if 'Body' in parts:
                log('runtime head=' + str(parts['Body'].get_socket_location('head')))
            if TEEN_QA:
                director = unreal.GameplayStatics.get_actor_of_class(w, unreal.load_class(None, '/Game/FoA/Gameplay/BP_BeatDirector.BP_BeatDirector_C'))
                assert director.get_editor_property('bWakeDone') and director.get_editor_property('BeatIndex') == 1, 'Wake handoff did not enter first steps'
                log('wake handoff: T1 first steps; no phone action required')
                assert pawn.get_editor_property('Mesh').get_anim_instance().get_class().get_name() == 'ABP_FoAPlayer_C', 'Locomotion source was not restored'
                assert parts['Body'].get_skeletal_mesh_asset().get_name() == 'SK_Teen_Body'
                assert parts['Face'].get_skeletal_mesh_asset().get_name() == 'SK_Teen_Head'
                assert parts['Face'].get_editor_property('custom_depth_stencil_value') == 4
                assert 100 < parts['Body'].get_socket_location('head').z - pawn.get_actor_location().z + 85 < 220, 'Teen retarget scale is invalid'
                head_gap=(parts['Face'].get_socket_location('head')-parts['Body'].get_socket_location('head')).length()
                log(f'teen CopyPose head gap={head_gap:.3f} cm')
                assert head_gap < .5, 'Separate head did not copy the animated body'
            phase('lie' if PLAN == 'lie' else 'settle')
    elif ph == 'settle':  # camera behind the shoulder; the boom lag settles, then the first still
        ease_cam(pc, S['heading'], -10.0, dt, 6.0)
        if el > 1.6:
            cmd(w, 'Shot')
            phase('swing')
    elif ph == 'swing':  # swing round to his 3/4 front for the second still
        k = min(el / 1.4, 1.0)
        pc.set_control_rotation(unreal.Rotator(roll=0.0, pitch=-8.0, yaw=S['heading'] + 150.0 * (0.5 - 0.5 * math.cos(math.pi * k))))
        if el > 2.2:
            cmd(w, 'Shot')
            pc.set_control_rotation(unreal.Rotator(roll=0.0, pitch=-10.0, yaw=S['heading']))
            phase('idle_prep' if PLAN in ('idle', 'turn') else 'approach' if PLAN == 'interact' else 'loco')
    elif ph == 'loco':
        if not S.get('state_target_written'):
            Path('P:/FoA/Saved/AnimShots/dm_runtime_target.json').write_text(json.dumps(dict(
                actor_path=pawn.get_path_name(),component_name=pawn.get_editor_property('Mesh').get_name(),machine_name='Locomotion')))
            S['state_target_written']=True
        if now - S.get('dm_log', 0.0) > .1:
            S['dm_log'] = now
            ai = pawn.get_editor_property('Mesh').get_anim_instance()
            S['dm_moving'] = S.get('dm_moving', False) or (ai.get_editor_property('GroundSpeed') > 10 and ai.get_editor_property('DisplacementSinceLastUpdate') > 0)
            log('dm class=%s speed=%.1f stop=%.1f moved=%.2f start_done=%s' % (ai.get_class().get_name(),
                ai.get_editor_property('GroundSpeed'), ai.get_editor_property('StopDistance'),
                ai.get_editor_property('DisplacementSinceLastUpdate'), ai.get_editor_property('StartDone')))
        t, acc = el, 0.0
        for i, (secs, mode, turn) in enumerate(LOCO):
            if t < acc + secs:
                break
            acc += secs
        else:
            if TEEN_QA:
                assert S.get('dm_moving'), 'Distance update never advanced during movement'
                director = unreal.GameplayStatics.get_actor_of_class(w, unreal.load_class(None, '/Game/FoA/Gameplay/BP_BeatDirector.BP_BeatDirector_C'))
                assert director.get_editor_property('BeatIndex') == 2, 'Walking did not advance the objective'
                log('movement advanced objective to T2')
            pawn.call_method('SetJogging', (False,))
            return phase('idle_prep' if PLAN == 'loco' else 'approach')
        if i != S['seg']:
            S['seg'] = i
            if mode != 'stop':
                S['heading'] = freest(w, pawn, S['heading'] + turn)
            pawn.call_method('SetJogging', (mode == 'jog',))
            log(f'seg {i} {mode} heading={S["heading"]:.0f}')
        if mode != 'stop':
            a = math.radians(S['heading'])
            pawn.add_movement_input(unreal.Vector(math.cos(a), math.sin(a), 0.0), 1.0, True)
        ease_cam(pc, pawn.get_actor_rotation().yaw + 20.0, -12.0, dt, 1.6)
    elif ph == 'approach':  # stand ~1.6 m in front of the first target present, facing it; walk in until it is in reach
        if S['target'] is None:
            S['target'] = next((a for a in (find(w, l) for l in TARGETS) if a), None)
            if not S['target']:
                log('no interactable found')
                return phase('idle')
            o, _ = S['target'].get_actor_bounds(False)
            to = unreal.Vector(-o.x, -o.y, 0.0).normal()  # toward the room centre
            stand = unreal.Vector(o.x + to.x * 170.0, o.y + to.y * 170.0, pawn.get_actor_location().z)
            pawn.set_actor_location(stand, False, True)
            yaw = math.degrees(math.atan2(-to.y, -to.x))
            pawn.set_actor_rotation(unreal.Rotator(0.0, 0.0, yaw), True)
            pc.set_control_rotation(unreal.Rotator(roll=0.0, pitch=-14.0, yaw=yaw + 35.0))
            S['goal'] = o
            log(f'target {S["target"].get_actor_label()}')
        if el > 0.5:
            phase('interact')
    elif ph == 'interact':
        I = pawn.get_component_by_class(unreal.load_asset('/Game/FoA/Gameplay/BPC_Interactor').generated_class())
        g = S['goal'] - pawn.get_actor_location()
        g.z = 0.0
        if not S.get('used'):
            if g.length() > 105.0 and el < 2.5:
                pawn.add_movement_input(g.normal(), 1.0, True)
            elif el > 0.4:
                S['used'] = True
                S['used_at'] = now
                I.call_method('SetFocus', (S['target'],))
                for _ in range(4):  # the montage rows are Use rows (Look only narrates); Verb is read-only here
                    if str(I.get_editor_property('Verb')) == 'Use':
                        break
                    I.call_method('CycleVerb')
                I.call_method('Interact')
                log(f'interact {S["target"].get_actor_label()} verb={I.get_editor_property("Verb")} state={S["target"].get_editor_property("State")}')
        elif now - S['used_at'] > INTERACT_S:
            phase('finish' if PLAN == 'interact' else 'idle_prep')
    elif ph == 'idle_prep':  # open floor for the idle shot: the room centre, facing west, camera swung to his 3/4 front
        if not S.get('placed'):  # once (a Shot hitch can make the first tick late): facing north, camera over open floor
            pawn.set_actor_location(unreal.Vector(-40.0, -120.0, pawn.get_actor_location().z), False, True)
            if PLAN == 'turn':  # cinematic eases RootYawOffset out, so the proof's own snap is not a turn
                pawn.call_method('SetCinematic', (True,))
            pawn.set_actor_rotation(unreal.Rotator(0.0, 0.0, 90.0), True)
            S['placed'] = True
            boom = next(c for c in pawn.get_components_by_class(unreal.SpringArmComponent))
            boom.set_editor_property('socket_offset', unreal.Vector(0.0, 30.0, -30.0))  # proof framing only (runtime)
            boom.set_editor_property('target_arm_length', 300.0)
            log(f"idle spot {pawn.get_actor_location()}")
        pc.set_control_rotation(unreal.Rotator(roll=0.0, pitch=-6.0, yaw=90.0 + 150.0))
        if el > 1.2:
            phase('turn' if PLAN == 'turn' else 'idle')
    elif ph == 'turn':  # turn in place: snap the capsule +90 then -180 while he stands; the body must step round after it
        pc.set_control_rotation(unreal.Rotator(roll=0.0, pitch=-6.0, yaw=240.0))  # fixed camera, his front-left
        if not S.get('zeroed'):  # idle_prep's placement snap was held off as cinematic, so the body starts square
            S['zeroed'] = True
            pawn.call_method('SetCinematic', (False,))
        for at, yaw in ((1.0, 180.0), (4.5, 0.0)):
            if el > at and S.get('turned', 0.0) < at:
                S['turned'] = at
                pawn.set_actor_rotation(unreal.Rotator(0.0, 0.0, yaw), True)
                log(f'turn capsule to yaw {yaw:.0f}')
        if now - S.get('turnlog', 0.0) > 0.25:
            S['turnlog'] = now
            ai = pawn.get_editor_property('mesh').get_anim_instance()
            log(f"turn offset={ai.get_editor_property('RootYawOffset'):.1f} wants={ai.get_editor_property('WantsTurn')} "
                f"index={ai.get_editor_property('TurnIndex')} actor={pawn.get_actor_rotation().yaw:.0f}")
        if el > 8.5:
            phase('finish')
    elif ph == 'idle':
        if TEEN_QA and not S.get('suit_tested'):
            pawn.call_method('Equip', ('Suit',))
            S['suit_tested']=True
            log('teen suit equipped; body='+pawn.get_editor_property('Body').get_skeletal_mesh_asset().get_name())
            assert pawn.get_editor_property('Body').get_skeletal_mesh_asset().get_name() == 'SK_Teen_Body'
            assert pawn.get_editor_property('Suit').is_visible()
            assert not any(pawn.get_editor_property(n).is_visible() for n in ('StartOutfit','StartPants','StartSocks'))
        ease_cam(pc, pawn.get_actor_rotation().yaw + 150.0, -6.0, dt, 0.3)  # head to feet in frame
        if now - S.get('camlog', 0.0) > 1.0:  # where the camera really is (the boom can collapse onto him)
            S['camlog'] = now
            cm = pc.player_camera_manager
            boom = next(c for c in pawn.get_components_by_class(unreal.SpringArmComponent))
            cam = next(c for c in pawn.get_components_by_class(unreal.CameraComponent))
            log(f"cam view={cm.get_camera_location()} pawn={pawn.get_actor_location()} yaw={pawn.get_actor_rotation().yaw:.0f} "
                f"ctrl={pc.get_control_rotation().yaw:.0f} boom_to_cam={(cam.get_world_location() - boom.get_world_location()).length():.0f} "
                f"close={pawn.get_editor_property('bCameraClose')} vt={pc.get_view_target().get_name()}")
        if el > IDLE:
            phase('finish' if PLAN in ('idle', 'loco') else 'sand')
    elif ph == 'finish':
        return finish()
    elif ph == 'lie':  # cine's lying shot: the pose on the bed, MetaHuman then the Mannequin, from two cameras
        lie_step(w, pawn, pc, now, el)
    elif ph == 'sand':  # walk across the biggest Sand-tagged floor actor: the foot plants should puff (SpawnSandStep)
        if 'sand' not in S:
            sands = unreal.GameplayStatics.get_all_actors_with_tag(w, 'Sand')
            if not sands:
                log('sand: no Sand-tagged actors')
                return phase('api')
            big = max(sands, key=lambda a: a.get_actor_bounds(False)[1].x * a.get_actor_bounds(False)[1].y)
            o, e = big.get_actor_bounds(False)
            start = unreal.Vector(o.x - e.x * 0.8, o.y, pawn.get_actor_location().z)
            pawn.set_actor_location(start, False, True)
            pawn.set_actor_rotation(unreal.Rotator(0.0, 0.0, 0.0), True)
            pc.set_control_rotation(unreal.Rotator(roll=0.0, pitch=-25.0, yaw=60.0))
            S['sand'] = (big, o)
            log(f"sand walk over {big.get_name()} centre {o} extent {e}")
        big, o = S['sand']
        g = o - pawn.get_actor_location()
        g.z = 0.0
        if el > 0.4 and el < 3.0 and g.length() > 40.0:
            pawn.add_movement_input(g.normal(), 1.0, True)
        if el > 3.4:
            phase('api')
    elif ph == 'api':  # the host API gameplay calls, exercised for real and logged
        I = pawn.get_component_by_class(unreal.load_asset('/Game/FoA/Gameplay/BPC_Interactor').generated_class())
        pawn.call_method('SetCinematic', (True,))
        log(f"api SetCinematic(true): bCinematic={pawn.get_editor_property('bCinematic')} focus={I.get_editor_property('Target')}")
        pawn.call_method('SetCinematic', (False,))
        log(f"api SetCinematic(false): bCinematic={pawn.get_editor_property('bCinematic')}")
        pawn.call_method('UnequipAll')
        pawn.call_method('Equip', ('Shirt',))
        shirt = next(c for c in pawn.get_components_by_class(unreal.SkeletalMeshComponent) if c.get_name() == 'Shirt')
        mesh = pawn.get_editor_property('mesh')
        m = mesh.get_anim_instance().get_current_active_montage() if mesh.get_anim_instance() else None
        log(f"api UnequipAll+Equip(Shirt): shirt visible={shirt.is_visible()} montage={m.get_name() if m else None}")
        if NIGHTMARE:
            return phase('nightmare')
        return finish()
    elif ph == 'nightmare':  # BP_Nightmare's API for the director: Appear 3 m away, StalkTo the player, Vanish
        if 'nm' not in S:
            cls = unreal.load_class(None, '/Game/FoA/Characters/Player/BP_Nightmare.BP_Nightmare_C')
            nm = unreal.GameplayStatics.get_actor_of_class(w, cls)
            if nm is None:  # Python cannot spawn into PIE: the summon cheat can (PIE has cheats on)
                if not S.get('summoned'):
                    S['summoned'] = now
                    cmd(w, 'summon /Game/FoA/Characters/Player/BP_Nightmare.BP_Nightmare_C')
                elif now - S['summoned'] > 1.0:
                    log('nightmare summon failed')
                    return finish()
                return
            p = pawn.get_actor_location()
            spot = unreal.Vector(p.x + 250.0, p.y + 150.0, p.z)
            nm.call_method('Appear', (spot, 200.0))
            nm.call_method('StalkTo', (pawn,))
            S['nm'], S['nm0'], S['nm_t'] = nm, nm.get_actor_location(), now
            log(f"nightmare appear at {spot} hidden={nm.get_editor_property('hidden')} controller={nm.get_controller()}")
        elif now - S['nm_t'] > 2.5:
            nm = S['nm']
            moved = (nm.get_actor_location() - S['nm0']).length()
            stalking = nm.get_editor_property('bStalking')
            nm.call_method('Vanish')
            log(f"nightmare walked {moved:.0f} cm in 2.5 s stalking={stalking}; vanish hidden={nm.get_editor_property('hidden')}")
            nm.destroy_actor()
            return finish()


old = getattr(unreal, '_foa_anim_pie_handle', None)  # one harness per PIE: a second copy would double every input
if old is not None:
    unreal.unregister_slate_post_tick_callback(old)
    print('replaced a running anim proof harness')
S['h'] = unreal.register_slate_post_tick_callback(tick)
unreal._foa_anim_pie_handle = S['h']
print('anim proof run scheduled')
