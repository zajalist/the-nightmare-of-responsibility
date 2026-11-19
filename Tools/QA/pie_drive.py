"""qa lane: one PIE smoke burst, driven from a slate post-tick callback. Started by `foa_qa.py pie-smoke` through
ue_remote.py with FOA_EXCLUSIVE=1 while the qa lane holds EXCLUSIVE. Reads PIE actors and calls the front end's own
input handlers; writes nothing to /Game. QA_OUT=<dir> receives shots.json (Shot requests in order), frametimes.csv
(slate dt per tick), timeline.json and done.json. QA_CAP is the hard stop in seconds after this script starts.
QA_CMD=END only ends PIE (the caller's failsafe)."""
import csv
import json
import os
import time

import unreal

OUT = os.environ.get('QA_OUT', '')
CAP = float(os.environ.get('QA_CAP', '52'))
FE_C = '/Game/FoA/UI/Framework/BP_FoAFrontEnd.BP_FoAFrontEnd_C'
WAKE_C = '/Game/FoA/Cinematics/BP_WakeUpCinematic.BP_WakeUpCinematic_C'
DIR_C = '/Game/FoA/Gameplay/BP_BeatDirector.BP_BeatDirector_C'
UES = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
LES = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
S = {'t0': time.time(), 'w0': None, 'phase': 'boot', 'mark': 0.0, 'title_at': None, 'next_wake': 0.0, 'n': 0,
     'shot_n': -99, 'st': {}, 'st_t': -1.0, 'seen_wake': False, 'skipped': False, 'taken': set(),
     'shots': [], 'frames': [], 'log': [], 'h': None, 'done': False}
CLS = {}


def log(kind, **kw):
    e = dict(t=round(time.time() - S['t0'], 2), kind=kind, **kw)
    S['log'].append(e)
    unreal.log('[qa] ' + json.dumps(e, default=str))


def cls(path):
    if path not in CLS:
        CLS[path] = unreal.load_class(None, path)
    return CLS[path]


def state(w):
    out = {}
    fe = unreal.GameplayStatics.get_actor_of_class(w, cls(FE_C))
    if fe:
        scr = fe.get_editor_property('Screen')
        out['screen'] = scr.get_class().get_name() if scr else None
        out['in_gameplay'] = bool(fe.get_editor_property('bInGameplay'))
    wk = cls(WAKE_C)
    out['wake_cine'] = bool(wk and unreal.GameplayStatics.get_actor_of_class(w, wk))
    d = unreal.GameplayStatics.get_actor_of_class(w, cls(DIR_C))
    b = d.get_editor_property('Beat') if d else None
    out['beat'] = str(b.get_editor_property('Id')) if b else None
    return out


def fe_call(w, fn):
    fe = unreal.GameplayStatics.get_actor_of_class(w, cls(FE_C))
    if fe:
        fe.call_method(fn)
    log('call', fn=fn, ok=bool(fe))


def viewport_rect(w):
    """The PIE game viewport in absolute (desktop) pixels: 'Shot showui' saves the whole editor window, so the
    caller crops each shot to this rect."""
    try:
        geo = unreal.WidgetLayoutLibrary.get_viewport_widget_geometry(w)
        pos = unreal.SlateLibrary.local_to_absolute(geo, unreal.Vector2D(0, 0))
        size = unreal.SlateLibrary.get_absolute_size(geo)
        return [round(pos.x), round(pos.y), round(size.x), round(size.y)]
    except Exception as e:  # the report then flags the frame as uncropped
        log('viewport_rect_error', err=repr(e))
        return None


def shot(w, name):
    if name in S['taken']:
        return
    S['taken'].add(name)
    unreal.SystemLibrary.execute_console_command(w, 'Shot showui')  # whole editor window incl. UMG; cropped later
    S['shot_n'] = S['n']
    S['shots'].append(dict(name=name, t=round(time.time() - S['t0'], 2), phase=S['phase'], vp=viewport_rect(w), **S['st']))


def throttle(on):
    """Background throttling caps an unfocused editor near 3 fps, which slows game time and makes frame times
    meaningless; it is off only for this burst and restored in finish()."""
    try:
        perf = unreal.get_default_object(unreal.EditorPerformanceSettings)
        if on is None:
            unreal._qa_throttle = perf.get_editor_property('throttle_cpu_when_not_foreground')
            perf.set_editor_property('throttle_cpu_when_not_foreground', False)
        elif getattr(unreal, '_qa_throttle', None) is not None:
            perf.set_editor_property('throttle_cpu_when_not_foreground', unreal._qa_throttle)
            unreal._qa_throttle = None
        log('throttle', restored=on is not None, value=perf.get_editor_property('throttle_cpu_when_not_foreground'))
    except Exception as e:  # never block the burst or its cleanup on this
        log('throttle_error', err=repr(e))


def finish(reason):
    if S['done']:
        return
    S['done'] = True
    unreal.unregister_slate_post_tick_callback(S['h'])
    throttle(True)
    w = UES.get_game_world()
    if w:
        unreal.SystemLibrary.execute_console_command(w, 'csvprofile stop')
    log('finish', reason=reason)
    with open(os.path.join(OUT, 'shots.json'), 'w', encoding='utf-8') as fh:
        json.dump(S['shots'], fh, indent=1)
    with open(os.path.join(OUT, 'timeline.json'), 'w', encoding='utf-8') as fh:
        json.dump(S['log'], fh, indent=1, default=str)
    with open(os.path.join(OUT, 'frametimes.csv'), 'w', newline='', encoding='utf-8') as fh:
        wr = csv.writer(fh)
        wr.writerow(['t', 'ms', 'near_shot', 'phase'])
        wr.writerows(S['frames'])
    if w:
        LES.editor_request_end_play()
    with open(os.path.join(OUT, 'done.json'), 'w', encoding='utf-8') as fh:
        json.dump({'reason': reason, 't': round(time.time() - S['t0'], 2)}, fh)


def step(dt):
    now = time.time() - S['t0']
    w = UES.get_game_world()
    if w is None:
        if S['w0'] is not None:
            return finish('pie_gone')
        return finish('no_pie_world') if now > 20 else None
    if S['w0'] is None:
        S['w0'] = now
        log('pie_up')
        unreal.SystemLibrary.execute_console_command(w, 'viewmode lit')  # the PIE view only; gone when PIE ends
        unreal.SystemLibrary.execute_console_command(w, 'csvprofile start')
    S['n'] += 1
    last, S['last'] = S.get('last', now), now  # wall clock: the slate dt saturates at 125 ms
    S['frames'].append((round(now, 3), round((now - last) * 1000.0, 2), int(S['n'] - S['shot_n'] <= 3), S['phase']))
    if now >= CAP:
        return finish('cap')
    pt = now - S['w0']
    if pt - S['st_t'] >= 0.25:
        S['st_t'] = pt
        st = state(w)
        if st != S['st']:
            log('state', **st)
        S['st'] = st
    st, ph = S['st'], S['phase']
    if ph == 'boot':
        if pt >= 3:
            shot(w, 'boot_03s')
        if 'Title' in str(st.get('screen')):
            S['title_at'], S['phase'] = pt, 'title'
        elif pt > 22 and not S['skipped']:
            S['skipped'] = True
            log('miss', want='title screen by 22 s')
            fe_call(w, 'OnSplashFinished')
        elif pt > 26:
            S['title_at'], S['phase'] = pt, 'title'
    elif ph == 'title':
        ta = S['title_at']
        if pt >= ta + 3:
            shot(w, 'title_03s')
        if pt >= ta + 8:
            shot(w, 'title_08s')
        if pt >= ta + 8.6:
            fe_call(w, 'OnTitleConfirmed')  # the title's any-key handler
            S['phase'], S['mark'] = 'menu', pt
    elif ph == 'menu':
        if pt >= S['mark'] + 2.0:
            shot(w, 'menu_02s')
        if pt >= S['mark'] + 2.6:
            fe_call(w, 'WakeUp')  # the menu's start button handler
            S['phase'], S['mark'], S['next_wake'] = 'wake', pt, pt + 3
    elif ph == 'wake':
        S['seen_wake'] = S['seen_wake'] or st.get('wake_cine')
        if pt >= S['next_wake']:
            shot(w, 'wake_%02ds' % round(S['next_wake'] - S['mark']))
            S['next_wake'] += 3
        if pt > S['mark'] + 2 and (st.get('beat') == 'T0' or (S['seen_wake'] and not st.get('wake_cine'))):
            log('gameplay', wake_s=round(pt - S['mark'], 2))
            S['phase'], S['mark'] = 'game', pt
    elif ph == 'game':
        if pt >= S['mark'] + 1:
            shot(w, 'game_01s')
        if pt >= S['mark'] + 4:
            shot(w, 'game_04s')
        if pt >= S['mark'] + 4.6:
            finish('ok')


def tick(dt):
    if S['done']:
        return
    try:
        step(dt)
    except Exception as e:  # never leave PIE running or the callback registered
        log('error', err=repr(e))
        finish('error')


if os.environ.get('QA_CMD') == 'END':
    throttle(True)
    if UES.get_game_world():
        LES.editor_request_end_play()
    print('qa: PIE end requested')
else:
    throttle(None)
    LES.editor_request_begin_play()
    S['h'] = unreal.register_slate_post_tick_callback(tick)
    print('qa: PIE begin requested, smoke driver scheduled ->', OUT)
