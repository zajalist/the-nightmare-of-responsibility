"""In-editor recorder for sweep_intro.py: while a PIE world exists, request 'Shot showui' every UI_STEP seconds (the PIE
viewport renders it, so it works whatever covers the window or whichever virtual desktop is in front). Logs the request
times; when PIE ends (or 25 s pass without one) it unregisters itself and writes UI_OUT/shots.json.
Run via ue_remote.py with UI_OUT=<dir> UI_STEP=0.04 (25 requests/s).
Each request names its own BMP (UI_OUT/raw/sNNNNN.bmp): BMP skips the synchronous PNG encode that held the game thread
(menu fell to 11 fps), and a unique name per request lets sweep_intro drop the requests the level editor viewport
consumed instead of PIE (the request is global; those frames come out at the editor viewport's size).
Shots are SCHEDULED (next += STEP), not 'STEP since the last one': the old rule snapped to every 3rd frame and gave
~10 fps. Each request logs wall time and PIE game time, so frame N maps to an exact game moment.
UI_PERF=1: a measuring run. No shots and no once-a-second probe (its ObjectIterator costs a frame of its own); every
frame's dt goes to UI_OUT/frametimes.csv (t, ms, pie_t, near_shot) for QA check (f), and `stat dumphitches` with
t.HitchFrameTimeThreshold 50 writes each hitch's stat tree to the log for the cause."""
import json
import os
import time

import unreal

OUT = os.environ['UI_OUT']
STEP = float(os.environ.get('UI_STEP', '0.05'))
PERF = os.environ.get('UI_PERF') == '1'
# UI_TRACE=a,b: an Insights trace (cpu, task, frame) from PIE+a to PIE+b s into UI_OUT/trace.utrace (names the workers)
TRACE = [float(v) for v in os.environ.get('UI_TRACE', '').split(',') if v]
ARM_S = 120  # PIE may start late (lease wait, shader compile): a 25 s arm window lost a whole run
UES = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
S = {'t0': time.time(), 'ft': [], 'next': -1.0, 'game': [], 'seen': False, 'log': [], 'done': False, 'h': None, 'probe': -9.0, 'state': []}
FE_C = '/Game/FoA/UI/Framework/BP_FoAFrontEnd.BP_FoAFrontEnd_C'


def probe(w, now):
    """Once a second: what the player should be seeing (front-end screen, widgets in the viewport, view target, size)."""
    e = {'t': round(now, 2)}
    try:
        fe = unreal.GameplayStatics.get_actor_of_class(w, unreal.load_class(None, FE_C))
        e['fe'] = bool(fe)
        if fe:
            for k in ('Screen', 'BlackOverlay'):
                v = fe.get_editor_property(k)
                e[k] = v.get_class().get_name() if v else None
            for k in ('bWaking', 'bInGameplay'):
                e[k] = fe.get_editor_property(k)
        pc = unreal.GameplayStatics.get_player_controller(w, 0)
        vt = pc.get_view_target() if pc else None
        e['vt'] = vt.get_name() if vt else None
        e['cursor'] = pc.get_editor_property('show_mouse_cursor') if pc else None
        e['vp'] = str(unreal.WidgetLayoutLibrary.get_viewport_size(w))
        e['ui'] = [(u.get_class().get_name(), str(u.get_visibility()).split('.')[-1], round(u.get_render_opacity(), 2))
                   for u in unreal.ObjectIterator(unreal.UserWidget) if u.get_world() == w and u.is_in_viewport()]
    except Exception as ex:
        e['err'] = repr(ex)[:200]
    S['state'].append(e)
    # The input sweep gates actions on observed screens, never guessed boot timings.
    tmp = os.path.join(OUT, 'live_state.tmp')
    with open(tmp, 'w', encoding='utf-8') as fh:
        json.dump(dict(e, epoch=time.time()), fh)
    os.replace(tmp, os.path.join(OUT, 'live_state.json'))


def finish():
    if S['done']:
        return
    S['done'] = True
    unreal.unregister_slate_post_tick_callback(S['h'])
    with open(os.path.join(OUT, 'shots.json'), 'w', encoding='utf-8') as fh:
        json.dump({'t0': S['t0'], 'step': STEP, 'requests': S['log'], 'game_t': S['game'], 'state': S['state']}, fh)
    if TRACE and S.get('tr_on') and not S.get('tr_off'):
        unreal.SystemLibrary.execute_console_command(None, 'Trace.Stop')
    if PERF:
        with open(os.path.join(OUT, 'frametimes.csv'), 'w', encoding='utf-8') as fh:
            fh.write('t,ms,pie_t,near_shot' + chr(10))
            for t, ms, g in S['ft']:
                fh.write(f'{t},{ms},{g},0' + chr(10))
        unreal.SystemLibrary.execute_console_command(None, 'stat dumphitches')  # toggles it back off
        unreal.SystemLibrary.execute_console_command(None, 't.HitchFrameTimeThreshold -1')


def tick(dt):
    if S['done']:
        return
    now = time.time() - S['t0']
    w = UES.get_game_world()
    if w is None:
        if S['seen'] or now > ARM_S:
            finish()
        return
    if not S['seen']:
        S['seen'], S['next'], S['t_pie'] = True, now, now
        if PERF:  # each hitch over 50 ms dumps its stat tree to the log (the cause), for this PIE only
            unreal.SystemLibrary.execute_console_command(w, 't.HitchFrameTimeThreshold 50')
            unreal.SystemLibrary.execute_console_command(w, 'stat dumphitches')
    if TRACE and not S.get('tr_on') and now - S['t_pie'] >= TRACE[0]:
        S['tr_on'] = True
        unreal.SystemLibrary.execute_console_command(w, f'Trace.File "{OUT}/trace.utrace" cpu,task,frame,loadtime')
    if TRACE and S.get('tr_on') and not S.get('tr_off') and now - S['t_pie'] >= TRACE[1]:
        S['tr_off'] = True
        unreal.SystemLibrary.execute_console_command(w, 'Trace.Stop')
    if PERF:
        S['ft'].append((round(now, 4), round(dt * 1000.0, 2), round(unreal.GameplayStatics.get_real_time_seconds(w), 3)))
    if STEP > 0 and now >= S['next']:
        S['next'] = max(S['next'] + STEP, now - STEP)  # keep the average rate, never burst to catch up
        # quoted: FParse::Value stops an unquoted value at the dot; -nosuffix needs its dash (FParse::Param)
        unreal.SystemLibrary.execute_console_command(w, f'Shot showui -nosuffix filename="{OUT}/raw/s{len(S["log"]):05d}.bmp"')
        S['log'].append(round(now, 3))
        S['game'].append(round(unreal.GameplayStatics.get_real_time_seconds(w), 3))
    if not PERF and now - S['probe'] >= 1.0:
        S['probe'] = now
        probe(w, now)
    if now - S.get('t_pie', now) > 75:  # hard stop, 75 s after PIE starts
        finish()


os.makedirs(OUT + '/raw', exist_ok=True)
S['h'] = unreal.register_slate_post_tick_callback(tick)
print('sweep recorder armed ->', OUT)
