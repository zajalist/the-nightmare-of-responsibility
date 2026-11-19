"""ui lane: one PIE proof burst of the front end, driven from a slate post-tick callback (pattern of Tools/QA/pie_drive.py).
Started by pie_proof_run.py through ue_remote.py with FOA_EXCLUSIVE=1 while the ui lane holds EXCLUSIVE.
Beats: boot skipped at 1 s -> title (shots at 3/6/10 s) -> any key -> menu (2/5 s) -> Wake up -> cut to black ->
gameplay -> TogglePause (the Esc handler; its call time and the next frame times are logged) -> Resume.
Every top-level widget in the viewport is listed after the cut and in gameplay. Writes to UI_OUT: shots.json,
widgets.json, timeline.json, frametimes.csv, done.json. UI_CAP is the hard stop in seconds; UI_CMD=END only ends PIE."""
import csv
import json
import os
import time

import unreal

OUT = os.environ.get('UI_OUT', '')
CAP = float(os.environ.get('UI_CAP', '50'))
MODE = os.environ.get('UI_MODE', '')  # read at load: ue_remote removes its KEY=VALUE env vars when the run ends
FE_C = '/Game/FoA/UI/Framework/BP_FoAFrontEnd.BP_FoAFrontEnd_C'
UES = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
LES = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
S = {'t0': time.time(), 'w0': None, 'phase': 'boot', 'mark': 0.0, 'n': 0, 'shot_n': -99, 'taken': set(),
     'shots': [], 'frames': [], 'log': [], 'widgets': [], 'h': None, 'done': False, 'fe': None}


def log(kind, **kw):
    e = dict(t=round(time.time() - S['t0'], 2), kind=kind, **kw)
    S['log'].append(e)
    unreal.log('[uiproof] ' + json.dumps(e, default=str))


def fe(w):
    if S['fe'] is None:
        S['fe'] = unreal.GameplayStatics.get_actor_of_class(w, unreal.load_class(None, FE_C))
    return S['fe']


def call(w, fn):
    a = fe(w)
    t = time.perf_counter()
    if a:
        a.call_method(fn)
    ms = round((time.perf_counter() - t) * 1000.0, 2)
    log('call', fn=fn, ok=bool(a), ms=ms)
    return ms


def screen(w):
    a = fe(w)
    s = a.get_editor_property('Screen') if a else None
    return s.get_class().get_name() if s else None


def widgets(w, tag):
    """Every UserWidget of this PIE world that is in the viewport (WidgetBlueprintLibrary is not exposed to Python)."""
    out = []
    for u in unreal.ObjectIterator(unreal.UserWidget):
        try:
            if u.get_world() != w or not u.is_in_viewport():
                continue
            out.append(dict(cls=u.get_class().get_name(), vis=str(u.get_visibility()).split('.')[-1],
                            opacity=round(u.get_render_opacity(), 2)))
        except Exception:  # half-destroyed widgets during the cut
            continue
    S['widgets'].append(dict(tag=tag, t=round(time.time() - S['t0'], 2), widgets=out))
    log('widgets', tag=tag, n=len(out), list=out)


def diag(w):
    """What the menu really renders through: the view target's post-process blendables, and each sand word's effect
    material, Ink and the label's own colour (logged once in the title and once in the menu)."""
    try:
        pc = unreal.GameplayStatics.get_player_controller(w, 0)
        vt = pc.get_view_target() if pc else None
        cams = vt.get_components_by_class(unreal.CameraComponent) if vt else []
        pp = [[(round(b.weight, 2), b.object.get_name() if b.object else None)
               for b in c.get_editor_property('post_process_settings').weighted_blendables.array] for c in cams]
        log('view', target=vt.get_name() if vt else None, cls=vt.get_class().get_name() if vt else None, blendables=pp,
            pp_weight=[c.get_editor_property('post_process_blend_weight') for c in cams])
    except Exception as e:
        log('view_error', err=repr(e))
    for u in unreal.ObjectIterator(unreal.UserWidget):
        try:
            if u.get_world() != w or u.get_class().get_name() != 'WBP_SandButton_C':
                continue
            ret, txt = u.get_editor_property('Ret_Sand'), u.get_editor_property('Txt_Label')
            m = ret.get_effect_material() if ret else None
            ink = None
            if isinstance(m, unreal.MaterialInstanceDynamic):  # the live MID: what PushState/SetReveal pushed
                ink = {n: str(m.get_vector_parameter_value(n)) for n in ('Ink', 'State', 'Calm')}
                ink.update({n: round(m.get_scalar_parameter_value(n), 3) for n in ('Reveal', 'Scale', 'Glint')})
            log('word', label=str(txt.get_text()) if txt else None, effect=m.get_name() if m else None,
                parent=m.get_editor_property('parent').get_name() if m and hasattr(m, 'parent') else None, ink=ink,
                label_color=str(txt.get_editor_property('color_and_opacity').get_editor_property('specified_color')) if txt else None,
                ret_opacity=round(ret.get_render_opacity(), 2) if ret else None)
        except Exception as e:
            log('word_error', err=repr(e)[:200])


def viewport_rect(w):
    try:
        geo = unreal.WidgetLayoutLibrary.get_viewport_widget_geometry(w)
        pos = unreal.SlateLibrary.local_to_absolute(geo, unreal.Vector2D(0, 0))
        size = unreal.SlateLibrary.get_absolute_size(geo)
        return [round(pos.x), round(pos.y), round(size.x), round(size.y)]
    except Exception as e:  # the runner then keeps the frame uncropped and says so
        log('viewport_rect_error', err=repr(e))
        return None


def shot(w, name):
    if name in S['taken']:
        return
    S['taken'].add(name)
    unreal.SystemLibrary.execute_console_command(w, 'Shot showui')
    S['shot_n'] = S['n']
    S['shots'].append(dict(name=name, t=round(time.time() - S['t0'], 2), phase=S['phase'], screen=screen(w),
                           vp=viewport_rect(w)))


def throttle(restore):
    """An unfocused editor throttles to ~3 fps; off for this burst only, restored in finish()."""
    try:
        perf = unreal.get_default_object(unreal.EditorPerformanceSettings)
        if not restore:
            unreal._ui_throttle = perf.get_editor_property('throttle_cpu_when_not_foreground')
            perf.set_editor_property('throttle_cpu_when_not_foreground', False)
        elif getattr(unreal, '_ui_throttle', None) is not None:
            perf.set_editor_property('throttle_cpu_when_not_foreground', unreal._ui_throttle)
            unreal._ui_throttle = None
    except Exception as e:  # not exposed in every build: never block the burst or its cleanup on it
        log('throttle_error', err=repr(e))


def finish(reason):
    if S['done']:
        return
    S['done'] = True
    unreal.unregister_slate_post_tick_callback(S['h'])
    throttle(True)
    log('finish', reason=reason)
    for name, data in (('shots.json', S['shots']), ('timeline.json', S['log']), ('widgets.json', S['widgets'])):
        with open(os.path.join(OUT, name), 'w', encoding='utf-8') as fh:
            json.dump(data, fh, indent=1, default=str)
    with open(os.path.join(OUT, 'frametimes.csv'), 'w', newline='', encoding='utf-8') as fh:
        wr = csv.writer(fh)
        wr.writerow(['t', 'ms', 'near_shot', 'phase'])
        wr.writerows(S['frames'])
    if UES.get_game_world():
        LES.editor_request_end_play()
    with open(os.path.join(OUT, 'done.json'), 'w', encoding='utf-8') as fh:
        json.dump({'reason': reason, 't': round(time.time() - S['t0'], 2)}, fh)


def go(phase, pt):
    S['phase'], S['mark'] = phase, pt
    log('phase', phase=phase)


def step():
    now = time.time() - S['t0']
    w = UES.get_game_world()
    if w is None:
        if S['w0'] is not None:
            return finish('pie_gone')
        return finish('no_pie_world') if now > 20 else None
    if S['w0'] is None:
        S['w0'] = now
        log('pie_up')
        unreal.SystemLibrary.execute_console_command(w, 'viewmode lit')
    S['n'] += 1
    last, S['last'] = S.get('last', now), now
    S['frames'].append((round(now, 3), round((now - last) * 1000.0, 2), int(S['n'] - S['shot_n'] <= 3), S['phase']))
    if now >= CAP:
        return finish('cap')
    pt, ph, d = now - S['w0'], S['phase'], now - S['w0'] - S['mark']
    if ph == 'boot' and MODE == 'boot':  # step 4: the film boot unskipped, at the page's beats
        for s_, n in ((1.0, 'boot_black'), (3.2, 'boot_ue'), (8.6, 'boot_aholo'), (13.6, 'boot_hayba_form'),
                      (15.4, 'boot_hayba'), (17.4, 'boot_hayba_out'), (20.6, 'boot_title_in'), (23.5, 'title_boot')):
            if pt >= s_:
                shot(w, n)
        if pt >= 24.2:  # then into the menu: the default selection (Wake up) with its stir and grains
            call(w, 'OnTitleConfirmed')
            go('menu', pt)
        return
    if MODE == 'phone' or S.get('to_phone'):  # step 5: the diegetic phone as T0 opens it (BP_FoAFrontEnd.OpenPhone -> BP_Phone push-in)
        return phone_step(w, pt)
    if ph == 'boot':
        if pt >= 1.0 and fe(w):
            call(w, 'OnSplashFinished')  # boot cards are step 4; this burst proves title, menu, wake and pause
            go('title', pt)
    elif ph == 'title':
        for s in (3, 6, 10):
            if d >= s:
                shot(w, 'title_%02ds' % s)
        if d >= 3 and 'diag_t' not in S['taken']:
            S['taken'].add('diag_t')
            diag(w)
        if d >= 10.5:
            call(w, 'OnTitleConfirmed')  # the title's any-key handler
            go('menu', pt)
    elif ph == 'menu':
        for s in (2, 5):
            if d >= s:
                shot(w, 'menu_%02ds' % s)
        if d >= 2.2 and 'diag_m' not in S['taken']:
            S['taken'].add('diag_m')
            diag(w)
        if MODE == 'boot':
            if d >= 5.6:  # then Wake up and on into the phone flow (step 5) in the same burst
                call(w, 'WakeUp')
                S['to_phone'] = True
                go('wake', pt)
            return
        if d >= 5.2 and 'mm_off' not in S['taken']:  # A/B: is the smear the dream stack's menu mode?
            S['taken'].add('mm_off')
            try:
                fe(w).call_method('SetDreamMenuMode', (False,))
                log('call', fn='SetDreamMenuMode(false)', ok=True)
            except Exception as e:
                log('menumode_error', err=repr(e)[:200])
        if d >= 8.2:
            shot(w, 'menuoff_08s')
        if d >= 8.6:
            call(w, 'WakeUp')  # the menu's Wake up handler
            go('wake', pt)
    elif ph == 'wake':
        if d >= 1.5:
            shot(w, 'press_01s')  # the press sound plays out over the frozen menu (UI expected here)
        if d >= 4.0 and 'cut' not in S['taken']:
            S['taken'].add('cut')
            widgets(w, 'after_cut')
        for s in (5, 7):
            if d >= s:
                shot(w, 'wake_%02ds' % s)
        if d >= 7.5:
            widgets(w, 'gameplay_before_pause')
            S['pause_ms'] = call(w, 'TogglePause')  # the Esc handler while playing
            go('pause', pt)
    elif ph == 'pause':
        if 'pv' not in S['taken']:
            S['taken'].add('pv')
            pm = fe(w).get_editor_property('PauseMenu')
            log('pause_state', paused=unreal.GameplayStatics.is_game_paused(w), pause_menu=bool(pm),
                vis=str(pm.get_visibility()) if pm else None, call_ms=S.get('pause_ms'))
        if d >= 0.3:
            shot(w, 'pause_00s')
        if d >= 1.5:
            shot(w, 'pause_01s')
        if d >= 2.0:
            call(w, 'Resume')
            go('game', pt)
    elif ph == 'game':
        if d >= 1.0:
            shot(w, 'wake_resumed')
            widgets(w, 'after_resume')
            try:  # P13 rollover, as BP_BeatDirector.FailDay will call it
                fe(w).call_method('PlayDayRollover', (2, unreal.Text('The alarm only stops when you stand up.')))
                log('call', fn='PlayDayRollover', ok=True)
            except Exception as e:
                log('rollover_error', err=repr(e)[:200])
            go('roll', pt)
    elif ph == 'roll':
        for s, n in ((0.7, 'roll_wipe'), (1.6, 'roll_covered'), (3.0, 'roll_card')):
            if d >= s:
                shot(w, n)
        if d >= 4.3 and 'roll_cut' not in S['taken']:
            shot(w, 'roll_cut')
            log('rollover_after_cut', rollover=bool(fe(w).get_editor_property('Rollover')))
            widgets(w, 'after_rollover_cut')
            go('end', pt)
    elif ph == 'end' and d >= 0.6:
        finish('ok')


def phone_step(w, pt):
    ph, d = S['phase'], pt - S['mark']
    if ph == 'boot' and pt >= 1.0 and fe(w):
        call(w, 'OnSplashFinished'); go('title', pt)
    elif ph == 'title' and d >= 2.0:
        call(w, 'OnTitleConfirmed'); go('menu', pt)
    elif ph == 'menu' and d >= 1.5:
        call(w, 'WakeUp'); go('wake', pt)
    elif ph == 'wake' and fe(w).get_editor_property('bInGameplay') and d >= 6.0:
        widgets(w, 'before_phone'); go('phone_wait', pt)
    elif ph == 'phone_wait' and d >= 1.0:
        shot(w, 'game_before_phone'); call(w, 'OpenPhone'); go('phone', pt)
    elif ph == 'phone':
        for s_, n in ((0.4, 'phone_blend'), (1.2, 'phone_open'), (3.0, 'phone_hold')):
            if d >= s_:
                shot(w, n)
        if d >= 1.3 and 'pvt' not in S['taken']:
            S['taken'].add('pvt')
            pc = unreal.GameplayStatics.get_player_controller(w, 0)
            vt = pc.get_view_target() if pc else None
            log('phone_view', target=vt.get_actor_label() if vt else None, cls=vt.get_class().get_name() if vt else None)
        if d >= 3.4:
            call(w, 'ClosePhone'); go('phone_close', pt)
    elif ph == 'phone_close' and d >= 1.4:
        shot(w, 'phone_closed')
        if d >= 1.8:
            finish('ok')


def tick(dt):
    if S['done']:
        return
    try:
        step()
    except Exception as e:  # never leave PIE running or the callback registered
        log('error', err=repr(e))
        finish('error')


if os.environ.get('UI_CMD') == 'END':
    throttle(True)
    if UES.get_game_world():
        LES.editor_request_end_play()
    print('uiproof: PIE end requested')
else:
    throttle(False)
    if os.environ.get('UI_PIE') != 'hayba':  # hayba: the runner starts PIE in a new 16:9 window (editor_start_pie)
        LES.editor_request_begin_play()
    S['h'] = unreal.register_slate_post_tick_callback(tick)
    print('uiproof: PIE begin requested ->', OUT)
