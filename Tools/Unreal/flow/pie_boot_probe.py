"""BOOT PROBE (copy of pie_notify_repro phases 0-6): Story lane, in PIE (run_chase_final.py pie_boot_probe, one EXCLUSIVE window): Notify rows, red then green (the
user's stuck T6, 2026-11-10). Real E presses where the player acts; fixtures only for the beats in between.
  menu -> Wake up -> intro -> skip -> T0 phone -> FirstSteps, Searched (T3) -> real E on Boot_L: KeyTaken (T4) and the
  boot's Notify Searched hides the Key actor (Key Hidden -> Taken) -> every container whose Linked pickup is Hidden:
  real E opens it, the pickup must go Available (Notify Open) -> KeySnapped, LatchFreed (T6), fixture: Door LatchFree ->
  real E "Pull the handle": HandleOff, the door's Notify HandleOff topples the wardrobe (Standing -> Falling -> Fallen,
  WardrobeLanded) and BeatIndex reaches 7 -> fixture EnterBeat(10): OpenTheDoor's Notify Open, the Door must go Open.
Result: Saved/StoryShots/notify_repro.json (verdict GREEN only if every check holds)."""
import importlib
import json
import math
import sys
import time
from pathlib import Path

import unreal

sys.path.insert(0, 'P:/FoA/Tools/Unreal/flow')
import proof_save  # noqa: E402
importlib.reload(proof_save)

OUT = Path('P:/FoA/Saved/StoryShots/boot_probe.json')
INPUTS = Path('P:/FoA/Saved/StoryShots/boot_probe_input.json')
w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
assert w, 'no PIE world'
PROOF = proof_save.isolate(w)
pc = unreal.GameplayStatics.get_player_controller(w, 0)
S = dict(t0=time.time(), phase=0, after=0.0, rows=[], done=False, h=None, input_id=0, pressed=0.0, tries=0,
         checks={}, wardrobe_seen=[], reveal=[], ri=0)


def cls(path):
    return unreal.load_class(None, path)


D = unreal.GameplayStatics.get_actor_of_class(w, cls('/Game/FoA/Gameplay/BP_BeatDirector.BP_BeatDirector_C'))
P = unreal.GameplayStatics.get_player_character(w, 0)
IA = P.get_component_by_class(cls('/Game/FoA/Gameplay/BPC_Interactor.BPC_Interactor_C'))
BAG = P.get_component_by_class(cls('/Game/FoA/Gameplay/BPC_Inventory.BPC_Inventory_C'))
ACT = {a.get_actor_label(): a for a in unreal.GameplayStatics.get_all_actors_of_class(w, cls('/Game/FoA/Gameplay/BP_Interactable.BP_Interactable_C'))}
DOOR, BOOT = ACT['Door_Bedroom'], ACT['Boot_L']
WARD = next(a for a in ACT.values() if a.get_class().get_name().startswith('BP_Topple'))
KEY = next((a for n, a in ACT.items() if n.startswith('Key')), None)


def prop(o, n, default=None):
    try:
        return o.get_editor_property(n)
    except Exception:  # noqa: BLE001
        return default


def st(a):
    return str(prop(a, 'State')) if a else None


def log(kind, **kw):
    tgt = prop(IA, 'Target')
    ws = st(WARD)
    if not S['wardrobe_seen'] or S['wardrobe_seen'][-1] != ws:
        S['wardrobe_seen'].append(ws)
    row = dict(t=round(time.time() - S['t0'], 2), kind=kind, beat=prop(D, 'BeatIndex'), door=st(DOOR), wardrobe=ws,
               boot=st(BOOT), key=st(KEY), items=[str(i) for i in (prop(BAG, 'Items') or [])],
               target=tgt.get_actor_label() if tgt else None, prompt=str(prop(IA, 'Prompt')), **kw)
    S['rows'].append(row)
    unreal.log('[boot_probe] ' + json.dumps(row, default=str))
    return row


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
    c = S['checks']
    c.setdefault('wardrobe_fell', 'Falling' in S['wardrobe_seen'] and 'Fallen' in S['wardrobe_seen'])
    ok = reason == 'done' and all(v for k, v in c.items() if k != 'reveals_tested')
    OUT.write_text(json.dumps(dict(reason=reason, verdict='GREEN' if ok else 'RED', checks=c, wardrobe_seen=S['wardrobe_seen'],
                                   reveal=S['reveal'], rows=S['rows']), indent=1, default=str))
    unreal.log('[boot_probe] finished %s %s' % (reason, c))


def cmd(c):
    unreal.SystemLibrary.execute_console_command(w, c, pc)


def wait(sec):
    S['after'] = time.time() + sec
    S['phase'] += 1


def stand_and_look(actor, dist=95.0, aim_z=None):
    at = actor.get_actor_location()
    d = math.hypot(at.x, at.y) or 1.0
    spot = unreal.Vector(at.x - at.x / d * dist, at.y - at.y / d * dist, 92.0)  # toward the room's middle
    P.teleport(spot, unreal.Rotator(0, 0, 0))
    o, e = actor.get_actor_bounds(False)
    eye = pc.player_camera_manager.get_camera_location()
    pc.set_control_rotation(unreal.MathLibrary.find_look_at_rotation(eye, unreal.Vector(o.x, o.y, aim_z if aim_z is not None else o.z)))


def press(actor, label, aim_z=None, verb='Use', dist=95.0):
    """focus actor (the scan's own pick, else pinned as QA's driver does), the Use verb, one real E"""
    if not S.get('aimed'):
        stand_and_look(actor, dist=dist, aim_z=aim_z)
        S['aimed'] = time.time()
        S['after'] = time.time() + 0.35
        return False
    if prop(IA, 'Target') != actor:
        log('focus_pinned', what=label, scan_chose=str(prop(IA, 'Target').get_actor_label() if prop(IA, 'Target') else None))
        IA.call_method('SetFocus', (actor,))
        IA.call_method('Refresh', (True,))
    for _ in range(3):
        if str(prop(IA, 'Verb')) == verb:
            break
        IA.call_method('CycleVerb')
    S['aimed'] = 0.0
    S['input_id'] += 1
    INPUTS.write_text(json.dumps(dict(id=S['input_id'], key='E')))
    S['pressed'] = time.time()
    log('press_E', what=label, verb=str(prop(IA, 'Verb')))
    return True


def tick(dt):
    try:
        if S['done']:
            return
        if not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world():
            return finish('pie_gone')
        S.setdefault('dts', []).append(dt)  # a minimized editor throttles PIE to 3 fps: the proof means nothing then
        if len(S['dts']) == 40:
            med = sorted(S['dts'])[20]
            log('fps', median_ms=round(med * 1000, 1))
            if med > 0.066:
                return finish('throttled_fps')
        if time.time() - S['t0'] > 46:
            return finish('timeout_phase_%d' % S['phase'])
        if S['phase'] >= 9 and time.time() - S.get('lp', 0.0) > 0.1:
            S['lp'] = time.time()
            log('poll')  # keep the wardrobe's states
        if time.time() < S['after']:
            return
        ph = S['phase']
        if ph == 0:
            cmd('ke * OnSplashFinished'); wait(0.8)
        elif ph == 1:
            cmd('ke * OnTitleConfirmed'); wait(1.2)
        elif ph == 2:
            cmd('ke * WakeUp'); wait(6.2)
        elif ph == 3:
            cmd('ke * OnStoryFinished'); wait(2.6)
        elif ph == 4:
            cmd('ke * SkipWakeUp'); wait(0.6)
        elif ph == 5:
            if prop(D, 'BeatIndex') != 0:
                return
            cmd('ke * ReportEvent PhoneWakeUp'); cmd('ke * ClosePhone')
            for ev in ('FirstSteps', 'Searched'):
                cmd('ke * ReportEvent ' + ev)
            log('to_t3'); wait(0.6)
        elif ph == 6:  # the boot: what Resolve and CanInteract say first, then a real E
            if not S.get('probed'):
                S['probed'] = True
                res = {}
                for fn, args in (('Resolve', ('Use', 'None')), ('CanInteract', ('Use', 'None')), ('FindRow', ('Use', 'None')),
                                 ('FindCarriedRow', ('Use',)), ('CanApplyProgressionRow', None), ('IsDressingBlocked', None)):
                    try:
                        if args is None:
                            ok, row = BOOT.call_method('Resolve', ('Use', 'None'))
                            res[fn] = str(BOOT.call_method(fn, (row,)))
                        else:
                            res[fn] = str(BOOT.call_method(fn, args))[:300]
                    except Exception as exc:  # noqa: BLE001
                        res[fn] = 'ERR ' + repr(exc)[:200]
                log('probe', res=res)
            if not S.get('looked'):  # what the scan sees: look at the boot from where QA stood, and trace to it
                P.teleport(unreal.Vector(90.0, -100.0, 92.0), unreal.Rotator(0, 0, 0))
                o, ex = BOOT.get_actor_bounds(False)
                eye = pc.player_camera_manager.get_camera_location()
                pc.set_control_rotation(unreal.MathLibrary.find_look_at_rotation(eye, o))
                S['looked'] = time.time(); S['after'] = time.time() + 0.6
                return
            if not S.get('traced'):
                o, ex = BOOT.get_actor_bounds(False)
                eye = pc.player_camera_manager.get_camera_location()
                hits = {}
                for ch in (unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, unreal.TraceTypeQuery.TRACE_TYPE_QUERY2):
                    hit = unreal.SystemLibrary.line_trace_single(w, eye, o, ch, False, [P], unreal.DrawDebugTrace.NONE, True)
                    try:
                        t = hit.to_tuple()
                        hits[str(ch)] = [str(x.get_actor_label()) if hasattr(x, 'get_actor_label') else str(x) for x in t if hasattr(x, 'get_actor_label')][:3]
                    except Exception as exc:  # noqa: BLE001
                        hits[str(ch)] = repr(exc)[:120]
                tl = []
                for k in range(8):
                    tl.append(str(prop(IA, 'Target').get_actor_label() if prop(IA, 'Target') else None))
                log('trace', hits=hits, boot_bounds=[round(o.x), round(o.y), round(o.z), round(ex.x), round(ex.y), round(ex.z)], target_now=tl[0])
                S['traced'] = True
                S['tlog'] = []
                S['after'] = time.time() + 0.1
                return
            if len(S.get('tlog', [])) < 20:
                S['tlog'].append(str(prop(IA, 'Target').get_actor_label() if prop(IA, 'Target') else None))
                S['after'] = time.time() + 0.1
                if len(S['tlog']) == 20:
                    log('targets', tlog=S['tlog'])
                    IA.call_method('Interact')
                    S['pressed'] = time.time()
                    log('ia_interact')
                return
            mi = P.get_editor_property('mesh').get_anim_instance()
            mont = mi.get_current_active_montage() if mi else None
            row = log('poll_boot', pending=prop(BOOT, 'bPendingRow'), pmont=str(prop(BOOT, 'PendingMontage')), montage=str(mont.get_name()) if mont else None,
                      pawn=[round(v) for v in P.get_actor_location().to_tuple()], locked=prop(P, 'bInteractionLocked'), approach=prop(P, 'bApproaching'))
            if 'Key' in row['items'] and row['key'] != 'Hidden':
                S['checks']['boot_key_notify'] = row['key'] == 'Taken'
                S['pressed'] = 0.0; log('boot_done'); return finish('done')
            elif time.time() - S['pressed'] > 16:
                S['checks']['boot_key_notify'] = False
                S['pressed'] = 0.0; log('boot_key_stuck'); return finish('done')
            else:
                S['after'] = time.time() + 0.25
        elif ph == 7:  # containers whose Linked pickup is Hidden: open each, the pickup must show
            if not S['reveal']:
                for name, a in sorted(ACT.items()):
                    linked = prop(a, 'Linked')
                    if linked and st(linked) == 'Hidden' and a.get_class().get_name().startswith('BP_Container'):
                        S['reveal'].append(dict(container=name, pickup=linked.get_actor_label(), before='Hidden'))
                S['checks']['reveals_tested'] = len(S['reveal'])
                if not S['reveal']:
                    log('no_hidden_linked_pickups'); wait(0.1); return
            r = S['reveal'][S['ri']]
            if not S['pressed']:
                press(ACT[r['container']], 'open_' + r['container'])
                return
            r['after'] = st(ACT[r['pickup']])
            if r['after'] == 'Available' or time.time() - S['pressed'] > 5:
                log('reveal', **r)
                S['pressed'] = 0.0; S['ri'] += 1
                if S['ri'] >= len(S['reveal']):
                    S['checks']['drawer_reveal'] = all(x.get('after') == 'Available' for x in S['reveal'])
                    wait(0.4)
            else:
                S['after'] = time.time() + 0.25
        elif ph == 8:
            for ev in ('KeySnapped', 'LatchFreed'):
                cmd('ke * ReportEvent ' + ev)
            DOOR.call_method('SetState', ('LatchFree', True))
            log('to_t6_latch_free'); wait(0.8)
        elif ph == 9:  # pull the handle: real E
            if not S['pressed']:
                press(DOOR, 'handle', aim_z=95.0)
                return
            row = S['rows'][-1]
            if row['beat'] == 7 or 'Fallen' in S['wardrobe_seen']:
                S['checks']['handle_off'] = row['door'] == 'HandleOff' or 'HandleOff' in [r['door'] for r in S['rows']]
                S['checks']['beat_7'] = True
                S['pressed'] = 0.0; wait(1.0)
            elif time.time() - S['pressed'] > 12:
                S['checks']['handle_off'] = 'HandleOff' in [r['door'] for r in S['rows']]
                S['checks']['beat_7'] = False
                S['pressed'] = 0.0; log('stuck_at_t6'); wait(0.2)
        elif ph == 10:  # T10: OpenTheDoor's Notify Open
            D.call_method('EnterBeat', (10,)); log('enter_t10_fixture'); wait(1.5)
        elif ph == 11:
            row = log('t10_door')
            S['checks']['t10_door_open'] = row['door'] == 'Open'
            finish('done')
    except Exception as exc:  # noqa: BLE001
        log('error', error=repr(exc))
        finish('error')


INPUTS.unlink(missing_ok=True)
OUT.unlink(missing_ok=True)
S['h'] = unreal.register_slate_post_tick_callback(tick)
log('started')
