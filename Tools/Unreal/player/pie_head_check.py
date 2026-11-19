"""PIE check (anim lane, main 2026-11-09 HIGH): is the player's head visible in the T8 battle-start shot and in the T9
PayoffCam shot, and hidden in first person? Same route as story's pie_payoff_shot.py (menu, wake-up skip, T0 phone,
events to T7, EnterBeat(8) fixture, the encounter's own SetState('Victory'), then the shipped payoff). Logs every 0.1 s:
the view target and its attach parent, bCameraClose, Face/Hair visibility, PhoneActor and what the phone is attached to.
Shots: first person before T8, the battle start, the payoff. Ends with '[anim] done'.
Pixel proof of first person: at each first-person point (after ClosePhone, 2.5 s into T1, after the T9 return) it shoots
the frame as is (A), then the next frame with every head component forced hidden (B), then restores them and shoots
the face lane's mask review (MPC_Dream FaceSlip = -1: the blur weight, i.e. stencil-4 Face/Hair coverage) (M); head_pixels.py diffs
the pairs (any head pixel in front of the camera shows up as a difference).
Output: Saved/AnimShots/head_check/<stamp>/ (head.json + shots)."""
import datetime
import json
import time
from pathlib import Path

import unreal

import sys as _sys
_sys.path.insert(0, 'P:/FoA/Tools/Unreal/player')
import proof_slot  # noqa: E402  (QA save slot: never the player's FoA.sav)

folder = Path('P:/FoA/Saved/AnimShots/head_check') / datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
folder.mkdir(parents=True, exist_ok=True)
S = dict(t0=time.time(), phase=0, after=0.0, rows=[], done=False, h=None, shot=0.0, n=0, won=None, fight=None, w=None, ab=None,
         ab_done=set(), returned=None)
HEAD = ('Face', 'Hair', 'Eyebrows', 'FaceDrift', 'BodyDrift')


def prop(o, n, default=None):
    try:
        return o.get_editor_property(n)
    except Exception:  # noqa: BLE001
        return default


def resolve():
    w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
    if not w:
        return False
    S.update(w=w, pc=unreal.GameplayStatics.get_player_controller(w, 0), p=unreal.GameplayStatics.get_player_character(w, 0),
             d=unreal.GameplayStatics.get_actor_of_class(w, unreal.load_class(None, '/Game/FoA/Gameplay/BP_BeatDirector.BP_BeatDirector_C')),
             enc=unreal.GameplayStatics.get_actor_of_class(w, unreal.load_class(None, '/Game/FoA/Gameplay/Encounter/BP_Encounter.BP_Encounter_C')))
    return bool(S['p'] and S['d'])


def name(a):
    return a.get_actor_label() if a and hasattr(a, 'get_actor_label') else (a.get_name() if a else None)


def log(kind, **kw):
    p, pc = S['p'], S['pc']
    vt = pc.get_view_target()
    par = vt.get_attach_parent_actor() if vt else None
    ph = prop(p, 'PhoneActor')
    face, hair = prop(p, 'Face'), prop(p, 'Hair')
    row = dict(t=round(time.time() - S['t0'], 2), kind=kind, beat=prop(S['d'], 'BeatIndex'), view=name(vt),
               view_class=vt.get_class().get_name() if vt else None, view_parent=name(par), camera_close=prop(p, 'bCameraClose'),
               face=face.is_visible() if face else None, hair=hair.is_visible() if hair else None, battle=prop(p, 'bBattleActive'),
               phone=name(ph), phone_parent=name(ph.get_attach_parent_actor()) if ph else None, **kw)
    S['rows'].append(row)
    return row


def shot(label):
    unreal.SystemLibrary.execute_console_command(S['w'], 'Shot showui filename=%s -nosuffix' % (folder / (label + '.png')), S['pc'])


def head_comps():
    p = S['p']
    out = [c for c in (prop(p, n) for n in HEAD) if c]
    face = prop(p, 'Face')
    if face:
        out += [c for c in face.get_children_components(True) if isinstance(c, unreal.PrimitiveComponent)]
    return out


def ab_step():
    """A/B pair over three ticks: as is, all head components hidden, restore."""
    tag, k = S['ab']
    if k == 0:
        shot('fp_%s_A' % tag)
        log('fp_check', point=tag, shown=[c.get_name() for c in head_comps() if c.is_visible() and not c.get_editor_property('hidden_in_game')])
    elif k == 1:
        vt = S['pc'].get_view_target()
        if vt != S['p']:  # the camera moved on (a cut or a blend): an A/B pair here would diff the motion, not the head
            S['rows'].append(dict(kind='fp_check_void', point=tag, view=name(vt)))
            S['ab'] = None
            S['ab_done'].add(tag)
            return
        S['saved'] = [(c, c.get_editor_property('hidden_in_game')) for c in head_comps()]
        for c, _ in S['saved']:
            c.set_hidden_in_game(True, False)
        shot('fp_%s_B' % tag)
    elif k == 2:
        for c, hid in S['saved']:
            c.set_hidden_in_game(hid, False)
        mpc = unreal.load_asset('/Game/FoA/PostProcess/MPC_Dream')
        S['slip'] = unreal.MaterialLibrary.get_scalar_parameter_value(S['w'], mpc, 'FaceSlip')
        unreal.MaterialLibrary.set_scalar_parameter_value(S['w'], mpc, 'FaceSlip', -1.0)  # face lane's mask review: the blur weight
        shot('fp_%s_M' % tag)
    else:
        unreal.MaterialLibrary.set_scalar_parameter_value(S['w'], unreal.load_asset('/Game/FoA/PostProcess/MPC_Dream'), 'FaceSlip', S['slip'])
        S['ab'] = None
        S['ab_done'].add(tag)
        return
    S['ab'] = (tag, k + 1)


def finish(reason):
    if S['done']:
        return
    S['done'] = True
    proof_slot.leave(S)
    unreal.unregister_slate_post_tick_callback(S['h'])
    (folder / 'head.json').write_text(json.dumps(dict(reason=reason, rows=S['rows']), indent=1, default=str))
    unreal.log('[anim] head check %s %s' % (reason, folder))
    unreal.log('[anim] done')


def cmd(c):
    unreal.SystemLibrary.execute_console_command(S['w'], c, S['pc'])


def wait(sec):
    S['after'] = time.time() + sec
    S['phase'] += 1


def tick(dt):
    try:
        if not proof_slot.enter_once(S):
            return
        if S['done']:
            return
        if S['w'] is None or not unreal.SystemLibrary.is_valid(S['w']):
            if not resolve():
                if time.time() - S['t0'] > 25:
                    finish('no PIE world')
                return
        if S['ab'] is not None:
            return ab_step()
        el = time.time() - S['t0']
        if el > 42:
            return finish('time_cap phase %d' % S['phase'])
        if S['fight'] is not None and time.time() - S['shot'] >= 0.25:
            S['n'] += 1
            S['shot'] = time.time()
            r = log('frame')
            since_fight = time.time() - S['fight']
            label = 'f%02d_%s' % (S['n'], 'battle' if S['won'] is None else 'payoff')
            if S['n'] % 2 == 1:
                shot(label)
            if S['won'] is not None and r['view_class'] == 'BP_FoAPlayer_C' and S['returned'] is None:
                S['returned'] = time.time()
            if S['returned'] and 't9_return' not in S['ab_done']:  # at once: T10 swaps to the phone view within a second
                S['ab'] = ('t9_return', 0)
                return
            if S['won'] is not None and ('t9_return' in S['ab_done'] or time.time() - S['won'] > 9.0) and (
                    time.time() - S['won'] > 9.0 or r['beat'] == 10 or 't9_return' in S['ab_done']):
                return finish('watched')
        if time.time() < S['after']:
            return
        ph, D, ENC = S['phase'], S['d'], S['enc']
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
            cmd('ke * ReportEvent PhoneWakeUp'); cmd('ke * ClosePhone'); wait(0.8)
        elif ph == 6:
            if 'after_closephone' not in S['ab_done']:
                S['ab'] = ('after_closephone', 0)
                return
            log('first_person')
            wait(2.5)
        elif ph == 7:
            if 't1_mid' not in S['ab_done']:
                S['ab'] = ('t1_mid', 0)
                return
            for ev in ('FirstSteps', 'Searched', 'KeyTaken', 'KeySnapped', 'LatchFreed', 'WardrobeLanded'):
                cmd('ke * ReportEvent ' + ev)
            wait(0.6)
        elif ph == 8:
            if prop(D, 'BeatIndex') != 7:
                return
            D.call_method('EnterBeat', (8,)); log('enter_t8_fixture'); wait(0.4)
        elif ph == 9:
            if not prop(ENC, 'bActive'):
                return
            S['fight'] = time.time(); log('fight_started'); wait(2.0)
        elif ph == 10:
            ENC.call_method('SetState', ('Victory',))
            S['won'] = time.time(); log('victory_fixture'); wait(60)
    except Exception as exc:  # noqa: BLE001
        S['rows'].append(dict(error=repr(exc)))
        finish('error ' + repr(exc))


S['h'] = unreal.register_slate_post_tick_callback(tick)
unreal.log('[anim] head check armed')
