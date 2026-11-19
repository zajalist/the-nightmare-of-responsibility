"""Perf driver. Runs ONLY inside a standalone game process started by Tools/Perf/perf_run.py
(UnrealEditor.exe FoA.uproject -game ...), never in the shared editor (it refuses to start there).

It boots through the real front end and reaches each heavy moment with the same calls the QA proofs use
(Tools/Unreal/gameplay/pie_play.py, Tools/Unreal/level2/threshold_proof.py). At each moment it cycles the scalability
presets and records one native CSV profile per (moment, preset), plus a screenshot per preset and an optional
profilegpu dump. Progress goes to the QA slot (GI_FoA.SetProofProgressContext('FoA_QA_Play')), never FoA.sav.

Env (set by perf_run.py):
  FOA_PERF_OUT      output dir (manifest.json, driver log, shots)
  FOA_PERF_PLAN     l1 (bedroom, window, battle) | l2 (door portal, dream room, fall, city drive, ending) | idle
  FOA_PERF_PRESETS  "0,1,2,3"
  FOA_PERF_SAMPLE   seconds per CSV capture (default 4)
  FOA_PERF_CVARS    "r.X 1;r.Y 0" applied after every preset switch (A/B experiments)
  FOA_PERF_GPUDUMP  presets that also get one profilegpu dump, e.g. "1,3" (default none)
  FOA_PERF_SHOTS    1 = screenshot per preset (default 1)
  FOA_PERF_VARIANTS JSON A/B list [{"name": "base", "cvars": "r.X 2"}, {"name": "cand", "cvars": "r.X 0"}]
"""
import json
import os
import time

import unreal

OUT = os.environ.get('FOA_PERF_OUT', 'P:/FoA/Saved/Perf/runs/manual').replace('\\', '/')
PLAN = os.environ.get('FOA_PERF_PLAN', 'l1')
PRESETS = [int(x) for x in os.environ.get('FOA_PERF_PRESETS', '0,1,2,3').split(',') if x.strip()]
SAMPLE = float(os.environ.get('FOA_PERF_SAMPLE', '4'))
SETTLE = float(os.environ.get('FOA_PERF_SETTLE', '1.5'))
CVARS = [c.strip() for c in os.environ.get('FOA_PERF_CVARS', '').split(';') if c.strip()]
GPUDUMP = {int(x) for x in os.environ.get('FOA_PERF_GPUDUMP', '').split(',') if x.strip()}
SHOTS = os.environ.get('FOA_PERF_SHOTS', '1') == '1'
BURST = int(os.environ.get('FOA_PERF_BURST', '0'))
CAP = float(os.environ.get('FOA_PERF_CAP', '420'))
# A/B variants measured back to back at each moment: [{"name": "base", "cvars": "a 1;b 2"}, ...]
# optional "py": a statement run in this module at variant start, e.g. "set_shadows(['Lamp'], False)" (state persists
# like cvars, so every variant states it explicitly)
VARIANTS = [dict(name=v['name'], cvars=[c.strip() for c in v['cvars'].split(';') if c.strip()], py=v.get('py', ''))
            for v in json.loads(os.environ.get('FOA_PERF_VARIANTS') or '[{"name": "", "cvars": ""}]')]
QA_SLOT = 'FoA_QA_Play'
G = '/Game/FoA/Gameplay/'
PATHS = dict(director=G + 'BP_BeatDirector', fe='/Game/FoA/UI/Framework/BP_FoAFrontEnd',
             enc=G + 'Encounter/BP_Encounter', player='/Game/FoA/Characters/Player/BP_FoAPlayer',
             th='/Game/FoA/Level2/Transition/BP_DreamThreshold', journey='/Game/FoA/Level2/Journey/BP_L2Journey')
os.makedirs(OUT + '/shots', exist_ok=True)
S = dict(t0=time.time(), log=[], segments=[], gen=None, h=None, done=False, w=None, cls={})


def editor_running_here():
    try:
        return bool(unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem))
    except Exception:
        return False


# ---- world access ------------------------------------------------------------------------------------------------
def W():
    w = S['w']
    if w is not None and unreal.SystemLibrary.is_valid(w):
        return w
    S['w'] = None
    for cand in unreal.ObjectIterator(unreal.World):
        if unreal.GameplayStatics.get_player_controller(cand, 0):
            S['w'] = cand
            break
    return S['w']


def one(key):
    path = PATHS[key]
    if path not in S['cls']:
        S['cls'][path] = unreal.load_class(None, path + '.' + path.rsplit('/', 1)[1] + '_C')
    return unreal.GameplayStatics.get_actor_of_class(W(), S['cls'][path])


def prop(o, name, default=None):
    try:
        return o.get_editor_property(name) if o else default
    except Exception:
        return default


def pc():
    return unreal.GameplayStatics.get_player_controller(W(), 0)


def cmd(c):
    unreal.SystemLibrary.execute_console_command(W(), c, None)


def cvar(name):
    return unreal.SystemLibrary.get_console_variable_float_value(name)


def log(kind, **kw):
    row = dict(t=round(time.time() - S['t0'], 2), kind=kind, **kw)
    S['log'].append(row)
    unreal.log('[perf] ' + json.dumps(row, default=str))
    flush()


def flush():
    with open(OUT + '/manifest.pending', 'w') as fh:
        json.dump(dict(plan=PLAN, presets=PRESETS, sample=SAMPLE, cvars=CVARS, segments=S['segments'], log=S['log'],
                       done=S['done']), fh, indent=1, default=str)
    os.replace(OUT + '/manifest.pending', OUT + '/manifest.json')


def light_comps():
    for a in unreal.GameplayStatics.get_all_actors_of_class(W(), unreal.Actor):
        for c in a.get_components_by_class(unreal.LightComponent):
            yield a, c


def light_name(a, c):
    try:
        label = a.get_actor_label()
    except Exception:
        label = a.get_name()
    return f'{label}.{c.get_name()}'


def dump_lights():
    """Variant hook: every light component in the world, for picking what a variant changes."""
    log('lights', rows=[dict(name=light_name(a, c), cls=a.get_class().get_name(), type=c.get_class().get_name(),
                             shadows=prop(c, 'cast_shadows'), visible=c.is_visible(), intensity=prop(c, 'intensity'),
                             radius=prop(c, 'attenuation_radius'), channels=str(prop(c, 'lighting_channels')),
                             loc=[round(v) for v in c.get_world_location().to_tuple()]) for a, c in light_comps()])


def set_shadows(match, on):
    """Variant hook: cast shadows on or off for the light components whose 'Label.Component' contains any of match."""
    hits = [light_name(a, c) for a, c in light_comps() if any(m in light_name(a, c) for m in match)]
    for a, c in light_comps():
        if light_name(a, c) in hits:
            c.set_cast_shadows(on)
    log('set_shadows', on=on, hits=hits)


def remove_widgets():
    lib = unreal.get_default_object(unreal.load_class(None, '/Script/UMG.WidgetBlueprintLibrary'))
    for widget in lib.call_method('GetAllWidgetsOfClass', (W(), unreal.UserWidget, True)):
        widget.remove_from_parent()
    lib.call_method('SetInputMode_GameOnly', (pc(), True))
    pc().set_editor_property('show_mouse_cursor', False, notify_mode=unreal.PropertyAccessChangeNotifyMode.NEVER)


def isolate_save():
    g = unreal.GameplayStatics.get_game_instance(W())
    g.call_method('SetProofProgressContext', (QA_SLOT, set(), []))
    g.call_method('ResetProgress')  # SaveSlot is the QA slot now: only that slot is deleted
    assert str(g.get_editor_property('SaveSlot')) == QA_SLOT, 'proof context did not take'
    log('save_isolated', slot=QA_SLOT)


# ---- generator helpers -------------------------------------------------------------------------------------------
def sleep(s):
    end = time.time() + s
    while time.time() < end:
        yield


def wait(cond, timeout, what):
    end = time.time() + timeout
    while time.time() < end:
        try:
            if cond():
                return True
        except Exception:
            pass
        yield
    log('miss', what=what, timeout=timeout)
    return False


def shot(name):
    path = f'{OUT}/shots/{name}.png'
    cmd(f'HighResShot 1 filename={path}')
    return path


def measure(moment, presets=None, sample=None):
    """One CSV capture per preset (and per A/B variant) at the current moment; the scalability switch is the same one
    the Settings menu's Quality row makes (GameUserSettings.SetOverallScalabilityLevel = every sg.* group at that
    level). Variant cvars are set by console, which outranks later scalability switches: every variant must state
    explicit values for every cvar any variant changes."""
    for p in presets if presets is not None else PRESETS:
        cmd(f'scalability {p}')
        # The game's boot hook (BPFL_FoASettings.ApplyDynamicResolution, 11-18 14:35) turns dynamic resolution on with
        # the saved preset's max, and with it on r.ScreenPercentage is ignored: the 14:44 "Low" ran at 71%. A console
        # preset switch does not run the hook, so measure each preset at its fixed resolution; variants may turn it on.
        cmd('r.DynamicRes.OperationMode 0')
        for c in CVARS:
            cmd(c)
        for v in VARIANTS:
            for c in v['cvars']:
                cmd(c)
            if v['py']:
                exec(v['py'], globals())
            name = moment + (f"_{v['name']}" if v['name'] else '')
            yield from sleep(SETTLE)
            if SHOTS:
                path = shot(f'{name}_q{p}')
                yield from sleep(0.4)
            for i in range(BURST):  # consecutive frames in motion (ghosting checks)
                shot(f'{name}_q{p}_burst{i}')
                for _ in range(3):  # one pending screenshot request at a time
                    yield
            cmd('csvprofile start')
            t0 = time.time()
            f0 = unreal.SystemLibrary.get_frame_count()
            yield from sleep(sample or SAMPLE)
            cmd('csvprofile stop')
            seg = dict(moment=name, preset=p, variant=v['name'], t0=t0, t1=time.time(),
                       frames=unreal.SystemLibrary.get_frame_count() - f0,
                       screen_percentage=cvar('r.ScreenPercentage'), sg_res=cvar('sg.ResolutionQuality'),
                       lumen_gi=cvar('r.Lumen.DiffuseIndirect.Allow'), shot=path if SHOTS else None,
                       dilation=unreal.GameplayStatics.get_global_time_dilation(W()))
            S['segments'].append(seg)
            log('segment', **seg)
            yield from sleep(0.6)  # let the CSV writer finish before the next start
            if p in GPUDUMP:
                cmd('profilegpu')
                log('profilegpu', moment=name, preset=p)
                yield from sleep(1.0)


# ---- plans -------------------------------------------------------------------------------------------------------
def boot_front_end():
    """Real front end, as pie_play.boot / threshold_proof phases 0-4 do it."""
    yield from wait(lambda: one('fe') and one('director') and one('player') and pc(), 30, 'boot actors')
    isolate_save()
    fe, d = one('fe'), one('director')
    yield from sleep(1.0)
    fe.call_method('OnSplashFinished')
    yield from sleep(0.3)
    fe.call_method('OnTitleConfirmed')
    yield from sleep(0.3)
    fe.call_method('WakeUp')

    def story_or_film():
        story = prop(fe, 'Story')
        if story and story.is_in_viewport():
            story.call_method('Finish')
            return False
        return prop(fe, 'bInGameplay') and prop(d, 'SeqPlayer') and not prop(d, 'bWakeDone')
    if (yield from wait(story_or_film, 20, 'wake film')):
        d.call_method('SkipWakeUp')
    yield from wait(lambda: prop(d, 'bWakeDone') and not prop(one('player'), 'bCinematic'), 15, 'wake done')
    yield from sleep(1.0)
    fe.call_method('ClosePhone')
    log('booted', beat=str(prop(prop(d, 'Beat'), 'Id')))


def look_at(target):
    p = one('player')
    loc = p.get_actor_location()
    rot = unreal.MathLibrary.find_look_at_rotation(loc + unreal.Vector(0, 0, 60), unreal.Vector(*target))
    pc().set_control_rotation(rot)


def plan_l1():
    yield from boot_front_end()
    yield from sleep(3.0)  # texture streaming and Lumen settle after the wake film
    yield from measure('bedroom')
    look_at((-60, -345, 150))  # the bay window: light shafts, black sand on the sill
    yield from sleep(1.0)
    yield from measure('bedroom_window')
    d = one('director')
    d.call_method('EnterBeat', (8,))
    cine = lambda: bool(prop(one('player'), 'bCinematic'))  # noqa: E731
    if (yield from wait(cine, 8, 'battle intro')):
        yield from sleep(1.6)
        d.call_method('SkipWakeUp')  # what holding Space calls
    if (yield from wait(lambda: prop(one('enc'), 'bActive'), 15, 'encounter active')):
        unreal.GameplayStatics.set_global_time_dilation(W(), 0.5)  # stretch the fight so every preset sees it
        yield from sleep(1.0)
        yield from measure('battle')
        unreal.GameplayStatics.set_global_time_dilation(W(), 1)


def plan_l2():
    """The JOB_CASE fixture of threshold_proof: straight from boot to the T10 door, then the native transition."""
    yield from wait(lambda: one('fe') and one('director') and one('player') and pc(), 30, 'boot actors')
    isolate_save()
    yield from sleep(2.0)
    unreal.GameplayStatics.set_game_paused(W(), False)
    remove_widgets()
    one('director').call_method('OpenTheDoor')
    th = one('th')
    if not th:
        log('miss', what='BP_DreamThreshold not spawned')
        return
    th.call_method('StartThreshold')
    log('threshold_started')

    def phase():
        return prop(one('th'), 'Phase', -9)

    def close_phone():
        phone = prop(one('th'), 'Phone')
        if phone and prop(phone, 'bOpen'):
            one('fe').call_method('ClosePhone')
        return phase() >= 1
    yield from wait(close_phone, 15, 'threshold phase 1')
    # Phase 1 is the 9 s door sequence with the SceneCapture portal: slow it so every preset sees the portal.
    unreal.GameplayStatics.set_global_time_dilation(W(), 0.2)
    yield from sleep(1.5)
    yield from measure('door_portal', sample=min(SAMPLE, 3))
    unreal.GameplayStatics.set_global_time_dilation(W(), 3)
    yield from wait(lambda: phase() >= 3, 40, 'dream walk (phase 3)')
    unreal.GameplayStatics.set_global_time_dilation(W(), 1)
    yield from sleep(2.5)
    yield from measure('dream_room')
    th = one('th')
    unreal.get_default_object(unreal.SystemLibrary).call_method('SetIntPropertyByName', (th, 'RouteBeat', 2))
    th.call_method('HidePath')
    one('player').set_actor_location(unreal.Vector(20000, -79660, 92), False, True)
    th.call_method('BeginFall')
    log('fall_started', phase=phase())
    unreal.GameplayStatics.set_global_time_dilation(W(), 0.25)
    yield from sleep(1.0)
    yield from measure('dream_fall', presets=[p for p in PRESETS if p in (1, 3)] or PRESETS[:1], sample=min(SAMPLE, 3))
    unreal.GameplayStatics.set_global_time_dilation(W(), 3)
    yield from wait(lambda: phase() >= 6 and prop(one('th'), 'Journey'), 60, 'city arrival (phase 6)')
    unreal.GameplayStatics.set_global_time_dilation(W(), 1)
    journey = prop(one('th'), 'Journey')
    if not journey:
        return
    yield from sleep(1.5)
    journey.call_method('Confirm')
    yield from sleep(0.3)
    journey.call_method('Confirm')
    car = prop(journey, 'Car')
    yield from wait(lambda: prop(prop(journey, 'Car'), 'Active'), 10, 'car active')
    yield from sleep(3.0)
    log('driving', car=str(car), speed=prop(prop(journey, 'Car'), 'Speed'))
    yield from measure('city_drive')
    merge = prop(journey, 'Merge')
    if merge:
        merge.call_method('SetVisible', (True,))
        journey.call_method('ApplyMerge', (1.,))
    hud = prop(journey, 'HUD')
    if hud:
        hud.remove_from_parent()
    one('th').call_method('BeginEnding')
    log('ending_started')
    yield from sleep(2.0)
    yield from measure('ending')


def plan_idle():
    yield from wait(lambda: one('fe') and pc(), 30, 'boot actors')
    isolate_save()
    yield from sleep(2.0)
    yield from measure('front_end')


def plan_bench():
    """The same synthetic benchmark GameUserSettings.RunHardwareBenchmark uses; the CPU/GPU perf indices go to the log
    (calibration for the PerfIndexThresholds in Config/DefaultScalability.ini)."""
    yield from wait(lambda: pc(), 30, 'boot')
    yield from sleep(3.0)
    for _ in range(3):
        cmd('synthbenchmark 10')
        yield from sleep(4.0)
    cmd('scalability auto')
    yield from sleep(3.0)
    log('bench_done', resolution=cvar('sg.ResolutionQuality'), shadows=cvar('sg.ShadowQuality'),
        gi=cvar('sg.GlobalIlluminationQuality'))


def plan_l2drive():
    """Drive lane (coordinator 11-18 02:10): the long leg, Queen Market to Night Dispatch (795 m), one continuous CSV
    capture per preset from the moment the car moves until 60 m before the stop, so every city sector the rolling
    preload streams in lands inside a capture. Strikes are answered through the handlers the keys call (Brace,
    ChangeLane), so the leg is driven clean, as a player would. plan_l2 is unchanged."""
    yield from wait(lambda: one('fe') and one('director') and one('player') and pc(), 30, 'boot actors')
    isolate_save()
    yield from sleep(2.0)
    unreal.GameplayStatics.set_game_paused(W(), False)
    remove_widgets()
    one('director').call_method('OpenTheDoor')
    if not one('th'):
        log('miss', what='BP_DreamThreshold not spawned')
        return
    one('th').call_method('StartThreshold')

    def phase():
        return prop(one('th'), 'Phase', -9)

    def close_phone():
        phone = prop(one('th'), 'Phone')
        if phone and prop(phone, 'bOpen'):
            one('fe').call_method('ClosePhone')
        return phase() >= 1
    yield from wait(close_phone, 15, 'threshold phase 1')
    unreal.GameplayStatics.set_global_time_dilation(W(), 4)
    yield from wait(lambda: phase() >= 3, 40, 'dream walk (phase 3)')
    th = one('th')
    unreal.get_default_object(unreal.SystemLibrary).call_method('SetIntPropertyByName', (th, 'RouteBeat', 2))
    th.call_method('HidePath')
    one('player').set_actor_location(unreal.Vector(20000, -79660, 92), False, True)
    th.call_method('BeginFall')
    yield from wait(lambda: phase() >= 6 and prop(one('th'), 'Journey'), 60, 'city arrival (phase 6)')
    unreal.GameplayStatics.set_global_time_dilation(W(), 1)
    journey = prop(one('th'), 'Journey')
    yield from sleep(1.5)
    journey.call_method('Confirm')
    yield from sleep(0.3)
    journey.call_method('Confirm')
    yield from wait(lambda: prop(prop(journey, 'Car'), 'Active'), 10, 'car active')
    car = prop(journey, 'Car')
    for p in PRESETS:
        cmd(f'scalability {p}')
        cmd('r.DynamicRes.OperationMode 0')  # fixed resolution per preset (see measure())
        car.call_method('StartLeg', (1,))
        yield from wait(lambda: prop(car, 'RouteReady'), 10, 'leg 2 route')
        # In play the stop before this leg already streams its first 250 m (AutoPark); here the hold stands in for the
        # stop: up to 10 s until every pinned sector is visible, so the capture holds only the rolling preload.
        t_hold = time.time()
        unreal.get_default_object(unreal.SystemLibrary).call_method(
            'SetDoublePropertyByName', (car, 'HoldUntil', float(prop(car, 'Clock', 0)) + 10.0))
        yield from wait(lambda: not prop(car, 'CityHold'), 15, 'leg 2 city in')
        log('leg_start', preset=p, distance=prop(car, 'Distance'), length=prop(car, 'RouteLength'),
            hold_s=round(time.time() - t_hold, 1), city_ready=prop(car, 'CityReady'))
        cmd('csvprofile start')
        t0, f0 = time.time(), unreal.SystemLibrary.get_frame_count()
        met, sent = prop(car, 'Meteor'), set()
        while prop(car, 'Distance', 0) < prop(car, 'RouteLength', 1e9) - 6000 and time.time() - t0 < 120:
            if prop(met, 'Active') and not prop(met, 'Impacted'):
                kind, age, n = prop(met, 'Kind', 0), prop(met, 'Age', 0), prop(car, 'MeteorIndex', 0)
                if n not in sent and ((kind == 0 and age >= 2.15) or (kind != 0 and age >= 1.0)):
                    sent.add(n)
                    if kind == 0:
                        car.call_method('Brace')
                    else:  # free steering (11-18 10:4x): a dodge is the car steered aside; no keys in this process
                        side = max(-300.0, min(300.0, prop(car, 'StrikeLateral', 0.0) + kind * 300.0))
                        unreal.get_default_object(unreal.SystemLibrary).call_method(
                            'SetDoublePropertyByName', (car, 'Lateral', side))
            yield
        cmd('csvprofile stop')
        seg = dict(moment='long_leg', preset=p, variant='', t0=t0, t1=time.time(),
                   frames=unreal.SystemLibrary.get_frame_count() - f0, distance_m=round(prop(car, 'Distance', 0) / 100),
                   composure=prop(car, 'Composure'), strikes_answered=len(sent),
                   dilation=unreal.GameplayStatics.get_global_time_dilation(W()))
        S['segments'].append(seg)
        log('segment', **seg)
        yield from sleep(0.6)


def plan_cvars():
    """Log the values of FOA_PERF_QUERY (comma list of cvars) in this build, then quit."""
    yield from wait(lambda: pc(), 30, 'boot')
    for name in os.environ.get('FOA_PERF_QUERY', '').split(','):
        if name.strip():
            log('cvar', name=name.strip(), value=unreal.SystemLibrary.get_console_variable_float_value(name.strip()))
    if os.environ.get('FOA_PERF_LIBPROBE'):  # Blueprint-callable environment checks; a fixed list, never blind calls
        sl = unreal.SystemLibrary
        log('libprobe', values=dict(build_configuration=sl.get_build_configuration(),
                                    packaged_for_distribution=sl.is_packaged_for_distribution(),
                                    project_directory=sl.get_project_directory(), standalone=sl.is_standalone(W())))


PLANS = dict(l1=plan_l1, l2=plan_l2, idle=plan_idle, bench=plan_bench, l2drive=plan_l2drive, cvars=plan_cvars)


# ---- tick --------------------------------------------------------------------------------------------------------
def finish(reason):
    if S['done']:
        return
    S['done'] = True
    try:
        unreal.unregister_slate_post_tick_callback(S['h'])
    except Exception:
        pass
    log('done', reason=reason)
    with open(OUT + '/done.json', 'w') as fh:
        json.dump(dict(reason=reason), fh)
    try:
        cmd('quit')
    except Exception:
        pass


def tick(dt):
    try:
        if S['done']:
            return
        if time.time() - S['t0'] > CAP:
            return finish('cap')
        if W() is None:
            return
        if S['gen'] is None:
            log('start', plan=PLAN, world=W().get_name(), presets=PRESETS)
            # ShowUI 0: otherwise the first profilegpu opens the GPU Visualizer window, whose Slate cost pollutes
            # every later segment (2000+ UI draws, 3-4 ms of game-thread UI).
            for c in ('t.MaxFPS 0', 'r.VSync 0', 'r.GPUCsvStatsEnabled 1', 'r.ProfileGPU.ShowUI 0'):
                cmd(c)
            S['gen'] = PLANS[PLAN]()
        next(S['gen'])
    except StopIteration:
        finish('plan_complete')
    except Exception as exc:  # any error ends the run cleanly instead of ticking a broken generator
        import traceback
        log('error', error=repr(exc), tb=traceback.format_exc()[-1500:])
        finish('error')


if editor_running_here():
    unreal.log_error('[perf] perf_driver.py runs only in a standalone -game process, not in the editor')
else:
    S['h'] = unreal.register_slate_post_tick_callback(tick)
    unreal.log('[perf] driver registered: plan %s, out %s' % (PLAN, OUT))
