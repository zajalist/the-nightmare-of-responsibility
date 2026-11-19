"""Rig lane, in PIE (rig/run_rig_pie.py, one EXCLUSIVE window): the hanger uses, played through the real rows.
  FOA_USE=door|bed  FOA_VIEW=fp|side
Fixture (story's patterns, save-isolated with proof_save): front end, SkipWakeUp, phone closed.
  door  Knows.KeySnaps learnt, the hanger in the bag, he stands by the door; Door.Interact(Use, Hanger): the row
        Locked/Use/Hanger -> LatchFree plays AM_FoA_HangerDoor, commits LatchFreed at the latch click.
  bed   the events to the fall, T7 top-down left early, the clues to the snag, the hanger in the bag, he stands by the
        bed; Bed.Interact(Use, Hanger): ClothingSnag/Use/Hanger plays AM_FoA_HangerBed, commits at "it lets go".
  side  the view is a camera beside him (same run otherwise).
Every frame: montage position, the hanger actor, the Teen right hand vs where the grip puts it (HandInAnchor composed
with the hanger: the hold error), the row state, the pawn. 'Shot showui' frames every 0.08 s while the use runs.
Result: Saved/RigShots/hanger_use/<use>_<view>.json; frames Saved/RigShots/hanger_use/<use>_<view>/f_*.png."""
import importlib
import json
import os
import sys
import time
from pathlib import Path

import unreal

sys.path.insert(0, 'P:/FoA/Tools/Unreal/flow')
import proof_save  # noqa: E402
importlib.reload(proof_save)

USE = os.environ.get('FOA_USE', 'door')
VIEW = os.environ.get('FOA_VIEW', 'fp')
NAME = f'{USE}_{VIEW}'
OUT = Path(f'P:/FoA/Saved/RigShots/hanger_use/{NAME}.json')
SHOTS = Path(f'P:/FoA/Saved/RigShots/hanger_use/{NAME}')
SHOTS.mkdir(parents=True, exist_ok=True)
for f in SHOTS.glob('*.png'):
    f.unlink()
w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
assert w, 'no PIE world'
PROOF = proof_save.isolate(w)
pc = unreal.GameplayStatics.get_player_controller(w, 0)
P = unreal.GameplayStatics.get_player_character(w, 0)
S = dict(t0=time.time(), phase=0, after=0.0, rows=[], done=False, h=None, shot=0.0, n=0, began=None, ended=None, cam=None)
HIO = json.load(open('P:/FoA/Saved/AnimShots/grip_bake.json'))['Hanger']['hand_in_object']
HAND_IN = unreal.Transform(unreal.Vector(*HIO['loc']), unreal.Quat(*HIO['quat']).rotator(), unreal.Vector(1, 1, 1))
SIDE = {'door': ((322.0, 128.0, 105.0), (318.0, 30.0, 70.0)), 'bed': ((175.0, -88.0, 80.0), (262.0, -122.0, 28.0))}
STAND = {'door': ((300.0, 30.0), 0.0), 'bed': ((150.0, -100.0), -40.0)}


def cls(path):
    return unreal.load_class(None, path)


D = unreal.GameplayStatics.get_actor_of_class(w, cls('/Game/FoA/Gameplay/BP_BeatDirector.BP_BeatDirector_C'))
BAG = P.get_component_by_class(cls('/Game/FoA/Gameplay/BPC_Inventory.BPC_Inventory_C'))
ACT = {a.get_actor_label(): a for a in unreal.GameplayStatics.get_all_actors_of_class(w, cls('/Game/FoA/Gameplay/BP_Interactable.BP_Interactable_C'))}
TARGET = ACT['Door_Bedroom'] if USE == 'door' else ACT['Bed']
HU = cls('/Game/FoA/Characters/Player/Hanger/BP_FoAHangerUse.BP_FoAHangerUse_C')


def prop(o, n, default=None):
    try:
        return o.get_editor_property(n)
    except Exception:  # noqa: BLE001
        return default


def r1(v):
    return [round(v.x, 1), round(v.y, 1), round(v.z, 1)]


def cmd(c):
    unreal.SystemLibrary.execute_console_command(w, c, pc)


def wait(sec):
    S['after'] = time.time() + sec
    S['phase'] += 1


def stand(xy, yaw):
    P.teleport(unreal.Vector(xy[0], xy[1], P.get_actor_location().z), unreal.Rotator(0, 0, yaw))
    pc.set_control_rotation(unreal.Rotator(0, -15, yaw))


def sample():
    body = prop(P, 'Body')
    anim = P.get_editor_property('mesh').get_anim_instance()
    mon = anim.get_current_active_montage() if anim else None
    hu = unreal.GameplayStatics.get_actor_of_class(w, HU)
    row = dict(t=round(time.time() - S['t0'], 3), state=str(prop(TARGET, 'State')), pawn=r1(P.get_actor_location()),
               yaw=round(P.get_actor_rotation().yaw, 1), montage=mon.get_name() if mon else None,
               pos=round(anim.montage_get_position(mon), 3) if mon else None, frame=S['n'])
    if USE == 'bed':
        row['stage'] = prop(D, 'ClothingSearchStage')
    if hu:
        hg = prop(hu, 'Hanger')
        hx = hg.get_world_transform()
        want = HAND_IN * hx  # the hand where the grip puts it: HandInAnchor composed with the hanger
        hand = body.get_socket_transform('hand_r', unreal.RelativeTransformSpace.RTS_WORLD)
        row.update(hanger=r1(hx.translation), tip=r1(hx.transform_location(unreal.Vector(0, 0, 16.1))),
                   hand=r1(hand.translation), hold_err_cm=round((hand.translation - want.translation).length(), 2),
                   hold_rot_deg=round(abs(unreal.MathLibrary.normalize_axis(
                       (hand.rotation.rotator().yaw - want.rotation.rotator().yaw))), 1))
    S['rows'].append(row)
    return row, hu


def finish(reason):
    if S['done']:
        return
    S['done'] = True
    if S['h'] is not None:
        unreal.unregister_slate_post_tick_callback(S['h'])
    try:
        proof_save.restore(unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world(), PROOF)
    except Exception as exc:  # noqa: BLE001
        unreal.log_warning('[proof_save] restore failed: %r' % exc)
    held = [r for r in S['rows'] if 'hold_err_cm' in r and r.get('pos') and r['pos'] > 0.6]
    summary = dict(reason=reason, use=USE, view=VIEW, frames=S['n'],
                   montages=sorted({r['montage'] for r in S['rows'] if r.get('montage')}),
                   states=[r['state'] for i, r in enumerate(S['rows']) if i == 0 or r['state'] != S['rows'][i - 1]['state']],
                   hanger_frames=sum(1 for r in S['rows'] if 'hanger' in r),
                   hold_err_max_cm=max([r['hold_err_cm'] for r in held] or [None]) if held else None,
                   hold_err_median_cm=sorted(r['hold_err_cm'] for r in held)[len(held) // 2] if held else None)
    OUT.write_text(json.dumps(dict(summary=summary, rows=S['rows']), indent=1, default=str))
    print('RESULT', json.dumps(summary))


def tick(dt):
    try:
        if S['done']:
            return
        if not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world():
            return finish('pie_gone')
        if time.time() - S['t0'] > 46:
            return finish('timeout_phase_%d' % S['phase'])
        ph = S['phase']
        if ph >= 9:
            if not S.get('used'):
                if time.time() < S['after']:
                    return
                S['used'] = True
                S['after'] = time.time()
                TARGET.call_method('Interact', ('Use', 'Hanger'))
            row, hu = sample()
            if time.time() - S['shot'] > 0.08:
                S['shot'] = time.time()
                S['n'] += 1
                cmd('Shot showui filename=%s/f_%04d.png -nosuffix' % (SHOTS.as_posix(), S['n']))
            if hu and S['began'] is None:
                S['began'] = time.time()
            if S['began'] and not hu and S['ended'] is None:
                S['ended'] = time.time()
            if S['ended'] and time.time() - S['ended'] > 1.2:
                return finish('done')
            if S['began'] is None and time.time() - S['after'] > 6:
                return finish('hanger_use_never_started')
            return
        if time.time() < S['after']:
            return
        steps = {0: ('ke * OnSplashFinished', 0.8), 1: ('ke * OnTitleConfirmed', 1.2), 2: ('ke * WakeUp', 6.2),
                 3: ('ke * OnStoryFinished', 2.6), 4: ('ke * SkipWakeUp', 0.6)}
        if ph in steps:
            cmd(steps[ph][0]); wait(steps[ph][1])
        elif ph == 5:
            if prop(D, 'BeatIndex') != 0:
                return
            cmd('ke * ReportEvent PhoneWakeUp'); cmd('ke * ClosePhone'); wait(0.6)
        elif ph == 6:
            if USE == 'door':
                D.call_method('LearnFlag', ('Knows.KeySnaps',))
                S['phase'] = 8
            else:
                for ev in ('FirstSteps', 'Searched', 'KeyTaken', 'KeySnapped', 'LatchFreed', 'WardrobeLanded'):
                    cmd('ke * ReportEvent ' + ev)
                wait(0.3)
        elif ph == 7:  # bed: T7 top-down with the search started; leave it early
            if prop(D, 'BeatIndex') != 7 or not prop(D, 'bTopDown') or (prop(D, 'ClothingSearchStage') or 0) < 1:
                return
            D.call_method('ExitTopDown', ()); wait(1.0)
        elif ph == 8:
            if USE == 'bed':
                for fn in ('SearchWardrobeClue', 'SearchDeskClue', 'SearchBedClue', 'CancelClothingInspection'):
                    D.call_method(fn, ())
            BAG.call_method('Add', ('Hanger',))
            stand(*STAND[USE])
            if VIEW == 'side':
                eye, look = SIDE[USE]
                cam = w.spawn_actor(unreal.CameraActor, unreal.Vector(*eye),
                                    unreal.MathLibrary.find_look_at_rotation(unreal.Vector(*eye), unreal.Vector(*look)))
                cam.camera_component.set_editor_property('field_of_view', 60.0)
                cam.camera_component.set_editor_property('constrain_aspect_ratio', False)
                pc.set_view_target_with_blend(cam, 0.0)
                S['cam'] = cam
            S['rows'].append(dict(kind='fixture', state=str(prop(TARGET, 'State')), items=[str(i) for i in (prop(BAG, 'Items') or [])],
                                  stage=prop(D, 'ClothingSearchStage')))
            wait(0.5)
    except Exception as exc:  # noqa: BLE001
        S['rows'].append(dict(kind='error', error=repr(exc)))
        finish('error')


OUT.unlink(missing_ok=True)
S['h'] = unreal.register_slate_post_tick_callback(tick)
print('hanger_use scheduled', USE, VIEW)
