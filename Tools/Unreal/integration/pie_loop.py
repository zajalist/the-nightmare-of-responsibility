"""Integration lane: drives the whole loop inside a running PIE from an in-editor tick callback and logs a timeline.
  python Tools/Unreal/ue_remote.py Tools/Unreal/integration/pie_loop.py FOA_RUN=<name> [FOA_CHAIN=...]
Chain items, '|' separated: '<delay>:<console cmd>' runs the command <delay> s after the previous item;
'WAIT:<beat>:<timeout>' holds until BP_BeatDirector's Beat.Id is <beat> (or the timeout lapses, logged as a miss).
Every beat change, command and miss goes to the Output Log as '[integration]' and to
Saved/Integration/<name>_timeline.json when the chain ends or PIE stops. Reads PIE actors only; writes nothing."""
import json
import os
import time

import sys

import unreal

sys.path.insert(0, 'P:/FoA/Tools/Unreal/flow')
import proof_save  # noqa: E402  keeps every loop run off the player's save (editor-rules, 11-10)

RUN = os.environ.get('FOA_RUN', 'loop')
SHOT = float(os.environ.get('FOA_SHOT', '0.25'))  # seconds between in-engine viewport shots (0 = none)
OUT = f'P:/FoA/Saved/Integration/{RUN}_timeline.json'
DIR_C = '/Game/FoA/Gameplay/BP_BeatDirector.BP_BeatDirector_C'
MPC = '/Game/FoA/PostProcess/MPC_Dream.MPC_Dream'
FE_C = '/Game/FoA/UI/Framework/BP_FoAFrontEnd.BP_FoAFrontEnd_C'
WAKE_C = '/Game/FoA/Cinematics/BP_WakeUpCinematic.BP_WakeUpCinematic_C'
DEFAULT = ('0:viewmode lit|0.5:ke * OnSplashFinished|1.0:ke * OnTitleConfirmed|1.5:ke * WakeUp|WAIT:T1:45'
           '|1.2:ke * ReportEvent FirstSteps|WAIT:T2:3'
           '|1.2:ke * ReportEvent Searched|WAIT:T3:3|1.2:ke * ReportEvent KeyTaken|WAIT:T4:3'
           '|1.2:ke * ReportEvent KeySnapped|WAIT:T5:3|1.2:ke * ReportEvent LatchFreed|WAIT:T6:3'
           '|1.2:ke * ReportEvent WardrobeLanded|WAIT:T7:3|4.0:ke * ReportEvent ShirtTaken|WAIT:T8:3'
           '|2.0:ke * ReportEvent EncounterWon|WAIT:T9:3|WAIT:T10:6|0:ke * ReportEvent PayoffEnded|WAIT:T10:2'
           '|2.0:ke * ReportEvent WalkedOut|2.0:ke * FailDay|WAIT:T1:45'
           '|1.5:ke * TogglePause|1.5:ke * RequestQuitToTitle|1.5:ke * ConfirmPending|2.0:END')
chain = []
for item in os.environ.get('FOA_CHAIN', DEFAULT).split('|'):
    head, rest = item.split(':', 1)
    chain.append(('WAIT', *rest.split(':')) if head == 'WAIT' else ('CMD', float(head), rest))
S = {'t0': time.time(), 'mark': time.time(), 'snap': 0.0, 'shot': 0.0, 'i': 0, 'h': None, 'beat': None, 'log': [], 'done': False, 'ctx': None}


def log(kind, **kw):
    e = dict(t=round(time.time() - S['t0'], 2), kind=kind, **kw)
    S['log'].append(e)
    unreal.log('[integration] ' + json.dumps(e))


def beat_id(w):
    d = unreal.GameplayStatics.get_actor_of_class(w, unreal.load_class(None, DIR_C))
    if not d:
        return 'NO_DIRECTOR'
    b = d.get_editor_property('Beat')
    return str(b.get_editor_property('Id')) if b else 'None'


def state(w):
    """Director, front end, cinematic and pawn at a glance (read-only)."""
    out = {}
    d = unreal.GameplayStatics.get_actor_of_class(w, unreal.load_class(None, DIR_C))
    if d:
        for k in ('BeatIndex', 'bRollingOver', 'bTopDown'):
            out[k] = d.get_editor_property(k)
    fe = unreal.GameplayStatics.get_actor_of_class(w, unreal.load_class(None, FE_C))
    if fe:
        out['bInGameplay'] = fe.get_editor_property('bInGameplay')
        scr = fe.get_editor_property('Screen')
        out['screen'] = scr.get_class().get_name() if scr else None
    wk = unreal.load_class(None, WAKE_C)
    out['wakeup_cine'] = bool(wk and unreal.GameplayStatics.get_actor_of_class(w, wk))
    pawn = unreal.GameplayStatics.get_player_pawn(w, 0)
    out['pawn'] = [round(c) for c in pawn.get_actor_location().to_tuple()] if pawn else None
    pc = unreal.GameplayStatics.get_player_controller(w, 0)
    vt = pc.get_view_target() if pc else None
    out['view'] = vt.get_class().get_name() if vt else None
    return out


def mpc(w):
    col = unreal.load_asset(MPC)
    return {p: round(unreal.MaterialLibrary.get_scalar_parameter_value(w, col, p), 3)
            for p in ('ColorReveal', 'GlitchAmount', 'Letterbox', 'HueDrift')}


def finish(w=None):
    if S['done']:
        return
    S['done'] = True
    if S['ctx'] is not None:
        log('restored', ok=proof_save.restore(w, S['ctx']))  # PIE already gone: the player's file was never touched
    unreal.unregister_slate_post_tick_callback(S['h'])
    with open(OUT, 'w', encoding='utf-8') as fh:
        json.dump(S['log'], fh, indent=1)
    unreal.log(f'[integration] timeline -> {OUT}')


def tick(_dt):
    w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
    if not w:
        log('pie_gone')
        return finish()
    if S['ctx'] is None:  # before any chain command: progress goes to the QA slot, never FoA.sav
        try:
            S['ctx'] = proof_save.isolate(w)
        except Exception as e:  # never drive game flow on the player's save: stop instead
            log('isolate_failed', error=str(e))
            finish()
            unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_end_play()
            return
        log('isolated', player_slot=S['ctx']['slot'])
    b = beat_id(w)
    now = time.time()
    if now - S['snap'] > 2.0:
        S['snap'] = now
        log('state', beat=b, **state(w))
    if SHOT and now - S['shot'] > SHOT:
        S['shot'] = now
        unreal.SystemLibrary.execute_console_command(w, 'Shot showui')
    if b != S['beat']:
        S['beat'] = b
        log('beat', beat=b, mpc=mpc(w), paused=unreal.GameplayStatics.is_game_paused(w))
    if S['i'] >= len(chain):
        return finish(w)
    step = chain[S['i']]
    if step[0] == 'WAIT':
        _, want, timeout = step
        if b == want or now - S['mark'] > float(timeout):
            if b != want:
                log('miss', want=want, beat=b)
            S['i'] += 1
            S['mark'] = now
        return
    _, delay, cmd = step
    if now - S['mark'] < delay:
        return
    S['i'] += 1
    S['mark'] = now
    if cmd == 'END':
        log('end')
        finish(w)
        unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_end_play()
        return
    unreal.SystemLibrary.execute_console_command(w, cmd)
    log('cmd', cmd=cmd, beat=b)


S['h'] = unreal.register_slate_post_tick_callback(tick)
print('integration loop scheduled', len(chain), 'steps ->', OUT)
