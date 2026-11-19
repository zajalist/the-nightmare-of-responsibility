"""qa lane: play every plan of Tools/Unreal/gameplay/pie_play.py back to back, one EXCLUSIVE PIE burst each (60 s or
less, only in the PIE windows :x0-:x2; editor_lock waits for them), then write Saved/QA/run_<stamp>/report.md with a
contact sheet per plan, the per-beat pass/fail table, `foa_qa.py logs`, per-session log errors and frame-time
percentiles (QA check f).
  python Tools/QA/playtest_all.py                     all plans (A1 A2 A3 S1 S2 B1 B2 B3 C D1 D2)
  python Tools/QA/playtest_all.py A1 B3 --cap 46      chosen plans; --cap = seconds of play per burst
  python Tools/QA/playtest_all.py --report RUN_DIR    rebuild the report of an earlier run
  python Tools/QA/playtest_all.py --abort             after killing the runner mid-burst: stop our PIE, restore, release
PIE starts through pie_call (owner-checked) after a read-only Blueprint pre-flight; it waits while the user plays PIE.
Kills nothing but its own recorded tree (--abort).
RULE (2026-11-10, after the 03:10 UTC editor crash): no Python access to any Blueprint delegate property, ever: no
get_editor_property on an event dispatcher / multicast delegate, no .broadcast(). Call the owner's handler event
instead. forbid_delegates() enforces it on every QA driver before a burst."""
import csv
import glob
import json
import os
import re
import subprocess
import sys
import time

from PIL import Image, ImageDraw, ImageStat

ROOT = 'P:/FoA'
sys.path.insert(0, ROOT + '/Tools/Unreal')
sys.path.insert(0, ROOT + '/Tools/QA')
OWNER = os.environ.get('FOA_QA_OWNER', 'qa')  # the coordinator runs as main-qa: exempt from the PIE window
os.environ.update(FOA_AGENT=OWNER, HAYBA_AGENT_ID=OWNER, MSYS_NO_PATHCONV='1')
import hayba_call as hc  # noqa: E402

ALL = ['A1', 'A1b', 'A2', 'A3', 'S1', 'S2', 'S2R', 'B1', 'B2', 'B2b', 'B3', 'B3i', 'C', 'C2', 'D1', 'D2', 'D3', 'I1', 'I2', 'I3', 'SP', 'V', 'V2', 'F22']
ALL += ['A2k','A3h','A3f','S1p','S1s','S1l','B1w','B1d','B1b','B2c1','B2c2','B2c3','D1l','D1r','D1k']
ALL += ['B3u','Aim']
ALL += ['B3k', 'B3f', 'D1f']  # battle lane: real keys, then a win and a loss that fit a burst at ~3 fps
ALL += ['B3d']  # battle lane: Low takes the sand out of the fight's custom depth, Medium untouched
ALL += ['CR']  # credits lane: the ending roll's Lux3D showcase (unlisted plans fall back to ALL, so it must be named here)
ALL += ['DR', 'DR2a', 'DR2b', 'DR2c', 'DR2d', 'DRP', 'DRF', 'DR3', 'DR3P', 'DR4', 'DRS2', 'DRS3']  # drive lane: Level 2's rails drive and its QTE strikes
ALL += ['CP', 'CPM', 'DPL', 'WF']  # coordinator: the door portal probe (CPM after the T7 door move)
ALL += ['L1H', 'L1P', 'L1W', 'L1M', 'L1C', 'L1N', 'L1T1', 'L1T2', 'L1T3', 'L1CAM', 'L1INS', 'L1WF', 'L1HD', 'L1S0', 'L1S2', 'L1S4', 'L1SD', 'L1S7', 'L1S8', 'L1S9']  # level1 lane: the T7 bed hanger (arm/leg bones) and the T9 payoff, filmed every 0.25 s
ALL += ['PCM', 'PCI', 'PCP']  # playercam lane: first-person camera motion per tick; the fast-turn screwdriver inspect
ALL += ['L2R', 'D2H']  # main: D2H traces the HUD over the restart film; the ending room is the starting room (door closed, wardrobe standing)
ALL += ['L2E','L2S', 'L2S1', 'L2S2', 'L2F', 'L2W', 'L2I', 'L2H']  # level2 lane: the interview, ending film and credits; the first two job stops
ALL += ['AT1', 'AT2', 'ATX', 'ATC', 'AT1r', 'AT8r', 'ATLr', 'ATF', 'ATP', 'ATE', 'ATH']  # atmosphere lane: opening, T8 takeover and T9-to-Dream A untouched; Dream A exposure; street beds; PP probes
ALL += ['DRM']  # dreamroom lane: the colour dream walked through both breaths to the fall
ALL += ['UIK', 'UIG', 'UIJ', 'UII', 'UIR', 'UIS', 'UIF']  # ui lane: text FX kit; first-run graphics auto-detect; L2 journey card; interview look
ALL += ['DTS', 'DTB']  # doortool lane: the screwdriver at the lock plate, measured per screw and filmed every 15 deg of one stroke
ALL += ['CL']  # citylife lane: the Lux3D walkers, chairs and flocks around the car on leg 2
ALL += ['IN1', 'IN2', 'IN0', 'IN3']  # intro lane: the opening story (v4) in full at 0.25 s; skipped mid-line; unfilmed for frame times; Reduce Motion
SETTINGS = '/Script/UnrealEd.Default__LevelEditorPlaySettings'
LEASE_S = 60  # each PIE burst ends within this
LEASE_TTL = 70  # renewed every 20 s while the burst runs
PREFS = ROOT + '/Saved/QA/play_settings_user.json'  # the user's PIE settings, recorded before the first change


def call(name, **args):
    r = hc.call(name, args, timeout=20)
    if not r.get('ok'):
        raise RuntimeError(f'{name}: {str(r.get("error"))[:300]}')
    return r.get('data', {})


def lock(cmd, *extra):
    return subprocess.run([sys.executable, ROOT + '/Tools/Unreal/editor_lock.py', cmd, OWNER, *extra], cwd=ROOT,
                          capture_output=True, text=True)


def holds_exclusive():
    st = subprocess.run([sys.executable, ROOT + '/Tools/Unreal/editor_lock.py', 'status'], cwd=ROOT, capture_output=True, text=True).stdout
    return any(ln.startswith(OWNER + ': exclusive') for ln in st.splitlines())


def pie_running():
    try:
        return call('editor_get_state').get('pie_running')
    except (OSError, RuntimeError, ValueError):  # the editor is down or restarting: busy, keep waiting
        return True


def abort():
    """After the runner was killed mid-burst: stop PIE only if qa holds EXCLUSIVE (then it is ours), restore the
    user's play settings and release qa's lease. First kills the recorded runner's whole tree, if that PID really is
    a playtest_all.py process (never by name)."""
    pid_file = ROOT + '/Saved/QA/playtest_all.pid'
    pid = open(pid_file).read().strip() if os.path.exists(pid_file) else ''
    if pid.isdigit() and int(pid) != os.getpid():
        cmd = subprocess.run(['powershell', '-NoProfile', '-Command',
                              f'(Get-CimInstance Win32_Process -Filter "ProcessId={pid}").CommandLine'],
                             capture_output=True, text=True).stdout
        if 'playtest_all.py' in cmd:
            print(subprocess.run(['taskkill', '/T', '/F', '/PID', pid], capture_output=True, text=True).stdout.strip())
    if holds_exclusive() and pie_running():
        print('END:', call('editor_stop_pie'))  # Hayba attributes this session to qa, so it stops its own session
    if os.path.exists(PREFS):
        call('object_set_property', path=SETTINGS, properties=json.load(open(PREFS, encoding='utf-8')))
        print('play settings restored')
    print(lock('release').stdout.strip())


DRIVERS = (ROOT + '/Tools/Unreal/gameplay/pie_play.py', ROOT + '/Tools/QA/preflight_blueprints.py')


def forbid_delegates():
    """The delegate rule above, checked on the scripts this runner injects: any hit stops the run before PIE."""
    pat = re.compile(r"\.broadcast\(|get_editor_property\(\s*['\"](On[A-Z]|on_)")
    hits = [f'{os.path.basename(f)}:{i}' for f in DRIVERS for i, ln in enumerate(open(f, encoding='utf-8'), 1)
            if pat.search(ln) and not ln.lstrip().startswith('#')]
    if hits:
        raise SystemExit('refusing to run: Blueprint delegate access in ' + ', '.join(hits))


def pie_call(what):
    try:
        r = subprocess.run([sys.executable, ROOT + '/Tools/Unreal/integration/run_read.py', ROOT + '/Tools/Unreal/ui/pie_call.py',
                            f'FOA_CALL={what}'], cwd=ROOT, capture_output=True, text=True, timeout=20)
    except subprocess.TimeoutExpired:  # the game thread is frozen (a modal dialog, a long compile): say so, never hang
        return [f'pie_call {what} timed out: the editor game thread is not answering']
    return (r.stdout + r.stderr).strip().splitlines()[-1:] if (r.stdout + r.stderr).strip() else []


def preflight():
    """Tools/QA/preflight_blueprints.py through run_read: no Blueprint may be in error when PIE starts."""
    out = ROOT + '/Saved/QA/preflight.json'
    if os.path.exists(out):
        os.remove(out)
    try:
        subprocess.run([sys.executable, ROOT + '/Tools/Unreal/integration/run_read.py', ROOT + '/Tools/QA/preflight_blueprints.py'],
                       cwd=ROOT, capture_output=True, text=True, timeout=40)
    except subprocess.TimeoutExpired:
        return dict(ok=False, failures=[dict(path='(preflight)', status='timed out: editor not answering')])
    return json.load(open(out, encoding='utf-8')) if os.path.exists(out) else dict(ok=False, failures=[dict(path='(preflight)', status='no result')])


def audio_sample(t0):
    """One read of Hayba's audio_active_sounds (restart 8 reads the PIE world): short names, instance ids, loops."""
    try:
        r = hc.call('audio_active_sounds', {'limit': 64}, timeout=5)
    except (OSError, ValueError, RuntimeError):
        return None
    d = r.get('data') or {}
    return dict(t=round(time.time() - t0, 2), wall=round(time.time(), 2), world=d.get('world'), n=d.get('active_sound_count'),
                sounds=[(str(x.get('sound_path', '')).rsplit('.', 1)[-1], x.get('instance_id'), bool(x.get('looping')),
                         x.get('playing_audio', True) and not x.get('paused', False), x.get('owner'), x.get('volume'))
                        for x in d.get('sounds') or []])


def audio_lines(run_dir, plans):
    """Footstep triggers (unique instances of *Foot*/*Step* sounds) and stacking per plan, from <plan>/audio.json.
    Stacking counts AUDIBLE copies only (playing, not culled by concurrency): one sound 3+ times at once, or a loop
    twice. Files sampled before 2026-11-10 00:10 have no audible flag: their counts are spawns and say so."""
    out = []
    for plan in plans:
        f = os.path.join(run_dir, plan, 'audio.json')
        if not os.path.exists(f):
            continue
        rows = [r for r in json.load(open(f, encoding='utf-8')) if r.get('world') != 'editor']
        steps = {x[1] for r in rows for x in r['sounds'] if re.search('foot|step', x[0], re.I)}
        stacked, flagged = [], all(len(x) > 3 for r in rows for x in r['sounds'])
        for r in rows:
            counts, owners = {}, {}
            for x in r['sounds']:
                if len(x) > 3 and not x[3]:
                    continue  # culled or stopped by concurrency: not heard
                counts[(x[0], x[2])] = counts.get((x[0], x[2]), 0) + 1
                owners.setdefault(x[0], set()).add(str(x[4]) if len(x) > 4 else '?')
            stacked += [f'{r["t"]} s {n} x{c} (owners {", ".join(sorted(owners[n]))})'
                        for (n, loop), c in counts.items() if c >= 3 or (loop and c >= 2)]
        peak = max((r.get('n') or 0 for r in rows), default=0)
        out.append(f'- {plan}: {len(rows)} PIE samples ({"audible copies" if flagged else "SPAWNS, sampled before the audible flag"}), '
                   f'peak {peak} active sounds, {len(steps)} footstep sounds triggered; '
                   + (f'stacked: {"; ".join(stacked[:6])}' + (f' and {len(stacked) - 6} more' if len(stacked) > 6 else '') if stacked else 'nothing stacked'))
    return out or ['- no audio samples']


CHECK_KINDS = ('selftest', 'spare', 'inspect', 'notify', 'carried', 'inventory_unit', 'inv_dup', 'battle_intro', 'hanger_glance',
               'restart_mid_glance', 'view_into_player', 'walkout_hold', 'menu_focus', 'victory_ui', 'hud_over_film',
               'door_focus', 'walkout_probe')


def key_snap_check(run_dir):
    """(f) A2: S_Door_KeySnap (horror's 2D one-shot) active and audible (playing, volume > 0) within 2 s of the door
    going KeyJammed (the snap); the beat entering T5 when no state row exists (runs before 18:30)."""
    pj, aj = os.path.join(run_dir, 'A2', 'play.json'), os.path.join(run_dir, 'A2', 'audio.json')
    if not (os.path.exists(pj) and os.path.exists(aj)):
        return None
    log = json.load(open(pj, encoding='utf-8'))['log']
    snap = [e['t'] for e in log if e['kind'] == 'state_change' and e.get('actor') == 'Door_Bedroom' and e.get('state') == 'KeyJammed']         or [e['t'] for e in log if e['kind'] == 'beat' and e.get('beat') == 'T5']
    if not snap:
        return ('key snap sound', 'A2', 'FAIL', 'the snap (T5) never happened', '')
    t0w = next((e.get('t0_wall') for e in log if e['kind'] == 'setup'), None)
    if t0w is None:
        return ('key snap sound', 'A2', 'UNKNOWN', 'no common clock (run before 18:30)', '')
    rows = [r for r in json.load(open(aj, encoding='utf-8')) if 'wall' in r and -0.5 <= r['wall'] - t0w - snap[0] <= 2.0]
    hits = [x for r in rows for x in r['sounds'] if 'KeySnap' in x[0]]
    heard = [x for x in hits if len(x) > 5 and x[3] and (x[5] or 0) > 0.01]
    detail = f'{len(hits)} KeySnap samples near {snap[0]} s, {len(heard)} audible with volume > 0' + \
        (f' (volume {max((x[5] or 0) for x in hits):.2f})' if hits and len(hits[0]) > 5 else '')
    return ('key snap sound', 'A2', 'PASS' if heard else 'FAIL', detail, '')


def script_warning_rows(run_dir, plans):
    """(e) LogScript warnings and Accessed None in each burst's own FoA.log slice (battle plans are the sand VFX test)."""
    out = []
    for plan in plans:
        f = os.path.join(run_dir, plan, 'pie_log.txt')
        if not os.path.exists(f):
            continue
        lines = open(f, encoding='utf-8', errors='replace').read().splitlines()
        bad = [ln for ln in lines if re.search(r'LogScript: Warning|Script Msg|Accessed None|LogBlueprint: Error', ln)]
        out.append(('script warnings', plan, 'PASS' if not bad else 'FAIL', f'{len(bad)} lines' + (f': {bad[0][-160:]}' if bad else ''), ''))
    return out


def check_rows(run_dir, plans):
    rows = []
    for plan in plans:
        pj = os.path.join(run_dir, plan, 'play.json')
        if not os.path.exists(pj):
            continue
        for e in json.load(open(pj, encoding='utf-8'))['log']:
            if e['kind'] in CHECK_KINDS and 'result' in e:
                name = e.get('check') or e.get('item') or e['kind']
                detail = {k: v for k, v in e.items() if k not in ('t', 'kind', 'result', 'frame', 'check')}
                rows.append((f"{e['kind']}: {name}" if name != e['kind'] else e['kind'], plan, e['result'],
                             f"{e['t']} s " + json.dumps(detail, default=str)[:220], e.get('frame') or ''))
    k = key_snap_check(run_dir)
    return rows + ([k] if k else []) + script_warning_rows(run_dir, plans)


BATTLE_PLANS = {'B2', 'B2b', 'B3', 'B3i', 'B3u', 'D1', 'B2c3', 'D1l'}  # these start BP_Encounter


def graph_reaches(bp, graph, title_prefix):
    """Static, read-only: from the function entry of `graph`, following exec wires only, is a node whose title starts
    with `title_prefix` reachable? (A half-applied graph batch can leave a function dead-ending: 2026-11-10.)"""
    nodes, edges, no, eo = [], [], 0, 0
    while True:
        r = hc.call('blueprint_inspect_graph', {'path': bp, 'graph_name': graph, 'offset': no, 'edge_offset': eo}, timeout=20)
        if not r.get('ok'):
            return False, f'{graph}: {str(r.get("error"))[:120]}'
        d = r['data']
        if d.get('_truncated') and no == 0 and eo == 0 and 'page' not in d:
            # shortcut: Hayba on UE 5.9 returns at most 50 nodes/edges and ignores offsets; upgrade when it pages again
            return None, f"{graph}: unreadable (Hayba caps the graph at 50 of {d.get('node_count')} nodes and does not page)"
        nodes += d['nodes']
        edges += d['edges']
        pg = d.get('page') or {}
        nn, ne = (pg.get('nodes') or {}).get('next_offset'), (pg.get('edges') or {}).get('next_offset')
        if nn is None and ne is None or len(nodes) > 3000:
            break
        no, eo = nn or no, ne or eo
    exec_pins = {(n['node_id'], p['name']) for n in nodes for p in n.get('pins', []) if p.get('type') == 'exec'}
    title = {n['node_id']: n['title'].replace('\n', ' ') for n in nodes}
    entry = next((n['node_id'] for n in nodes if n['title'].split('\n')[0] == graph), None)
    if entry is None:
        return False, f'{graph}: no entry node'
    seen, todo = {entry}, [entry]
    while todo:
        cur = todo.pop()
        for e in edges:
            if e.get('from_node') == cur and (cur, e.get('from_pin')) in exec_pins and e.get('to_node') not in seen:
                seen.add(e['to_node'])
                todo.append(e['to_node'])
    hits = [title[n] for n in seen if title.get(n, '').replace(' ', '').startswith(title_prefix.replace(' ', ''))]
    return bool(hits), f'{graph}: {len(seen)} nodes reachable, {len(hits)} {title_prefix}'


def modifiers_down():
    """Alt, Ctrl, Shift or Win held anywhere on the machine (editor_pie_press_key copies the live OS modifiers: an Alt
    turned qa's P into Alt+P, the editor's RepeatLastPlay, and ended PIE; UI 2026-11-10)."""
    import ctypes
    u = ctypes.windll.user32
    return [n for n, vk in (('Alt', 0x12), ('Ctrl', 0x11), ('Shift', 0x10), ('LWin', 0x5B), ('RWin', 0x5C))
            if u.GetAsyncKeyState(vk) & 0x8000]


def maintenance():
    """main's maintenance hold, even past its ttl (editor_lock then treats it as stale; main lifts it by message)."""
    st = subprocess.run([sys.executable, ROOT + '/Tools/Unreal/editor_lock.py', 'status'], cwd=ROOT, capture_output=True, text=True).stdout
    return 'MAINTENANCE' in st


def burst(plan, out, cap):
    """One plan in one EXCLUSIVE lease: floating PIE, inject the driver, wait for its done.json, stop, restore."""
    out = out.replace(os.sep, '/')
    if os.path.isdir(out):  # a re-run keeps the old attempt beside it (an old abort flag would stop the new driver)
        os.rename(out, out + time.strftime('_prev_%H%M%S'))
    os.makedirs(out, exist_ok=True)
    waited = time.time()
    while pie_running() or maintenance():  # the user is playing, or main holds the editor: never interrupt
        if time.time() - waited > 1800:
            return dict(plan=plan, result='skipped: PIE busy or maintenance for 30 min')
        time.sleep(10)
    settle = time.time()  # nine lanes share the editor: wait (outside the lease) for others' edits to compile
    while time.time() - settle < 180:
        fails = preflight().get('failures', [])
        if not fails or any('DIRTY' not in str(f.get('status', '')) for f in fails):
            break  # clean, or a real error the in-lease check reports
        time.sleep(10)
    r = lock('acquire', '--ttl', str(LEASE_TTL), '--wait', '1500')
    if r.returncode or not holds_exclusive():
        return dict(plan=plan, result='skipped: no EXCLUSIVE lease', detail=(r.stdout + r.stderr)[-300:])
    lock('renew', '--ttl', str(LEASE_TTL))  # the ttl may have run while queued: count it from the grant
    t0, started, saved, info = time.time(), False, None, dict(plan=plan)
    abort_flag = os.path.join(out, 'abort')  # pie_play.py stops driving the tick it sees this
    done = os.path.join(out, 'done.json')
    log_path = os.path.join(ROOT, 'Saved', 'Logs', 'FoA.log')
    log_at = os.path.getsize(log_path) if os.path.exists(log_path) else 0
    try:
        if pie_running():
            raise RuntimeError('PIE started by someone else while the lease was queued')
        pre = preflight()
        info['preflight'] = dict(ok=pre.get('ok'), checked=pre.get('checked'), s=round(time.time() - t0, 1),
                                 failures=[f"{r['path']} {r['status']}" for r in pre.get('failures', [])])
        if not pre.get('ok'):  # PIE would stop on the editor's modal compile-error dialog: skip, never start it
            raise RuntimeError('preflight: Blueprint errors, burst skipped: ' + '; '.join(info['preflight']['failures']))
        if plan in BATTLE_PLANS:  # a dead-ending battle presentation hangs the fight: skip rather than hang
            ok, msg = graph_reaches('/Game/FoA/Gameplay/Encounter/WBP_Encounter', 'RefreshBattlePresentation', 'SetText')
            info['battle_graph'] = msg
            if ok is False:  # None: the graph could not be read whole (said in battle_graph), so not a reason to skip
                raise RuntimeError('preflight: WBP_Encounter.RefreshBattlePresentation never reaches SetText, battle plan skipped')
        saved = call('object_get_property', path=SETTINGS,
                     names=['NewWindowWidth', 'NewWindowHeight', 'LastExecutedPlayModeType'])['properties']
        if saved.get('LastExecutedPlayModeType') != 'PlayMode_InEditorFloating' or not os.path.exists(PREFS):
            json.dump(saved, open(PREFS, 'w', encoding='utf-8'))  # the user's own play settings, for --abort
        else:  # an aborted burst left ours in place: restore the user's recorded ones afterwards
            saved = json.load(open(PREFS, encoding='utf-8'))
        call('object_set_property', path=SETTINGS, properties=dict(NewWindowWidth=1280, NewWindowHeight=720,
                                                                    LastExecutedPlayModeType='PlayMode_InEditorFloating'))
        # PIE starts through Hayba's agent path, so Hayba records qa as the owner. A Python-started session reads as the user's.
        info['begin'] = call('editor_start_pie')
        started = True
        while not pie_running():
            if time.time() - t0 > 12:  # a frozen game thread here is usually the 'Blueprints have errors' modal
                raise RuntimeError('PIE did not start (a modal dialog in the editor? check the Blueprint compile warnings)')
            time.sleep(0.2)
        info['pie_start_s'] = round(time.time() - t0, 1)
        play_cap = min(cap, LEASE_S - 12 - (time.time() - t0))  # leaves time to end PIE inside the 60 s
        inj = subprocess.run([sys.executable, ROOT + '/Tools/Unreal/integration/run_read.py', ROOT + '/Tools/Unreal/gameplay/pie_play.py',
                              f'FOA_PLAN={plan}', f'FOA_CAP={play_cap:.0f}', f'FOA_OUT={out}', f'FOA_SHOT={os.environ.get("FOA_SHOT", "1.0")}'], cwd=ROOT, capture_output=True,
                             text=True, timeout=20)
        info['inject'] = (inj.stdout + inj.stderr).strip().splitlines()[-1:] if (inj.stdout + inj.stderr).strip() else []
        renewed, checked, audio, sampled, key_id = time.time(), time.time(), [], 0.0, None
        req, ack = os.path.join(out, 'input.json'), os.path.join(out, 'input_ack.json')
        while not os.path.exists(done) and time.time() - t0 < LEASE_S - 9:
            try:  # the driver's real-key requests (item inspect, battle intro skip): Hayba presses them in the PIE window
                r = json.load(open(req, encoding='utf-8')) if os.path.exists(req) else None
            except (OSError, ValueError):
                r = None
            if r and r.get('id') != key_id:
                key_id = r['id']
                wait_mods, mods = time.time() + 3.0, modifiers_down()
                while mods and time.time() < wait_mods:  # never press with a modifier down; wait for the hand to lift
                    time.sleep(0.1)
                    mods = modifiers_down()
                if r['key'] == 'Escape' or mods:  # Esc stops PIE even unmodified (PlayWorld chord)
                    res = dict(skipped='modifier held: ' + ','.join(mods) if mods else 'Escape is never sent')
                else:
                    try:
                        res = call('editor_pie_press_key', key=r['key'], held_ms=int(r.get('held_ms', 150)))
                    except RuntimeError as ex:
                        res = dict(error=str(ex)[:200])
                time.sleep(0.3)
                alive = pie_running()  # a key that reached the editor can stop PIE (18:5x): say so at once
                json.dump(dict(id=key_id, key=r['key'], result=str(res)[:300], pie_alive=alive), open(ack, 'w', encoding='utf-8'))
                if not alive:
                    info['pie_died_after_key'] = r['key']
                    break
            if time.time() - sampled < 0.5:
                time.sleep(0.05)
                continue
            sampled = time.time()
            if time.time() - renewed > 20:
                lock('renew', '--ttl', str(LEASE_TTL))
                renewed = time.time()
            if time.time() - checked > 2:
                checked = time.time()
                if not holds_exclusive():  # never drive a session we no longer own
                    open(abort_flag, 'w').write('lease lost')
                    info['lease_lost_at_s'] = round(time.time() - t0, 1)
                    break
            row = audio_sample(t0)
            if row:
                audio.append(row)
        json.dump(audio, open(os.path.join(out, 'audio.json'), 'w', encoding='utf-8'))
        time.sleep(0.5)
        info['result'] = json.load(open(done, encoding='utf-8')) if os.path.exists(done) else 'no done.json (driver did not finish)'
    except Exception as ex:  # report it and still stop PIE, restore settings and release below
        info['result'] = 'error: ' + repr(ex)[:300]
    finally:
        try:
            if started:
                if not os.path.exists(done):
                    open(abort_flag, 'w').write('burst over')
                info['end'] = call('editor_stop_pie')  # qa's own session (Hayba owner check)
                stop_by = min(time.time() + 8, t0 + LEASE_S - 1)
                while pie_running() and time.time() < stop_by:  # PIE ends before the lease is released
                    time.sleep(0.3)
            if saved:
                call('object_set_property', path=SETTINGS, properties=saved)
        finally:
            lock('release')
    info['lease_s'] = round(time.time() - t0, 1)
    try:  # this burst's own log lines, kept before an editor restart rotates FoA.log
        with open(log_path, 'rb') as fh:
            fh.seek(log_at if os.path.getsize(log_path) >= log_at else 0)
            open(os.path.join(out, 'pie_log.txt'), 'wb').write(fh.read())
    except OSError as ex:
        info['log_slice'] = repr(ex)
    print(plan, json.dumps(info)[:600], flush=True)
    return info


# ---- report ------------------------------------------------------------------------------------------------------
def view_crop(im):
    """The game view inside a 'Shot showui' frame: the floating PIE window (3 px borders, title bar) or, when PIE ran
    in the editor viewport (pie_call BEGIN does), that viewport in the 1918x1054 editor layout."""
    w, h = im.size
    if (w, h) == (1918, 1054):
        return im.crop((8, 137, 1293, 1015))  # shortcut: fixed to today's editor layout; measure it if the layout moves
    if abs(w - 1286) <= 4 and h >= 723:
        return im.crop((3, h - 723, w - 3, h - 3))
    return im


def frames_of(plan_dir):
    return sorted(glob.glob(os.path.join(plan_dir, 'frames', '*.png')))


def sheet(plan_dir, dest, cols=6, tw=320, th=180, limit=48):
    fs = frames_of(plan_dir)
    if not fs:
        return None
    keep = [f for f in fs if '_ok_' in f or '_MISS_' in f or '_use_' in f or '_beat' in f]
    rest = [f for f in fs if f not in keep]
    room = max(0, limit - len(keep))
    if rest and room:
        step = max(1, len(rest) // room)
        keep += rest[::step][:room]
    keep = sorted(keep)[:limit]
    rows = (len(keep) + cols - 1) // cols
    img = Image.new('RGB', (cols * tw, rows * (th + 18)), (20, 20, 20))
    dr = ImageDraw.Draw(img)
    for i, f in enumerate(keep):
        try:
            im = view_crop(Image.open(f).convert('RGB'))
        except OSError:
            continue
        im.thumbnail((tw, th))
        x, y = (i % cols) * tw, (i // cols) * (th + 18)
        img.paste(im, (x, y + 18))
        parts = os.path.basename(f)[:-4].split('_')
        label = f'{int(parts[1]) / 100:.1f}s {parts[2]} {"_".join(parts[3:])}'[:44]
        dr.text((x + 3, y + 3), label, fill=(255, 80, 80) if 'MISS' in f else (230, 230, 230))
    img.save(dest)
    return dest


def black_frames(plan_dir):
    out = []
    for f in frames_of(plan_dir):
        try:
            m = ImageStat.Stat(Image.open(f).convert('L').resize((64, 36))).mean[0] / 255.0
        except OSError:
            out.append((os.path.basename(f), 'unreadable'))
            continue
        if m < 0.02:
            out.append((os.path.basename(f), f'{m:.3f}'))
    return out


def front_end_checks(run_dir, plans):
    """foa_qa checks (a) menu words, (b) title contrast, (c) no UI over the wake-up film on every plan's boot frames,
    cropped from the floating PIE window (3 px borders, title bar) to its 1280x720 viewport."""
    d = os.path.join(run_dir, 'checks')
    os.makedirs(d, exist_ok=True)
    for plan in plans:
        for f in frames_of(os.path.join(run_dir, plan)):
            for tag, prefix in (('_title.png', 'title'), ('_menu.png', 'menu'), ('_wakeup.png', 'wake')):
                if f.endswith(tag):
                    view_crop(Image.open(f).convert('RGB')).save(os.path.join(d, f'{prefix}_{plan}.png'))
    r = subprocess.run([sys.executable, ROOT + '/Tools/QA/foa_qa.py', 'checks', d], cwd=ROOT, capture_output=True, text=True)
    return [ln for ln in r.stdout.splitlines() if ln.strip().startswith(('- PASS', '- FAIL', '- SKIP', 'PASS', 'FAIL'))] or r.stdout.splitlines()[-12:]


def report(run_dir, plans, bursts):
    import foa_qa
    lines = [f'# Playtest run {os.path.basename(run_dir)}', '', time.strftime('%Y-%m-%d %H:%M'), '',
             'Driver: `Tools/Unreal/gameplay/pie_play.py` (real front end, skips through the intro and wake-up skip paths, '
             'first-person walking and looking, BPC_Interactor focus, CycleVerb, Interact; battle by button clicks and '
             'prompted keys at 6x game speed). Shortcuts appear as rows named "shortcut" or "fixture".', '']
    table = ['| Plan | # | Beat | Step | Result | Secs | Reason | Frame |', '|---|---|---|---|---|---|---|---|']
    summary = []
    for plan in plans:
        d = os.path.join(run_dir, plan)
        info = next((b for b in bursts if b.get('plan') == plan), {})
        pj = os.path.join(d, 'play.json')
        if not os.path.exists(pj):
            summary.append(f'- **{plan}**: no play.json ({info.get("result")})')
            continue
        doc = json.load(open(pj, encoding='utf-8'))
        steps = doc['steps']
        ok = sum(s['result'] == 'pass' for s in steps)
        beats = []
        for e in doc['log']:
            if e['kind'] == 'beat' and e.get('beat') not in beats:
                beats.append(e.get('beat'))
        notes = [e for e in doc['log'] if e['kind'] in ('focus_pinned', 'walk_teleport', 'walk_detour', 'battle_click_api', 'no_effect', 'stand_none_fits', 'focus_flicker', 'walkout_probe', 'reach_probe', 'reach_spots', 'battle_head', 'victory_ui', 'note',
                                                         'battle_click_blocked', 'battle_click_missing', 'error')]
        summary.append(f'- **{plan}**: {ok}/{len(steps)} steps passed, ended "{doc["why"]}"; beats seen {" > ".join(map(str, beats))}; '
                       f'lease {info.get("lease_s", "?")} s (PIE start {info.get("pie_start_s", "?")} s); '
                       f'{len(notes)} driver notes')
        for s in steps:
            fr = os.path.relpath(s['frame'], run_dir).replace('\\', '/') if s.get('frame') else ''
            table.append(f'| {plan} | {s["n"]} | {s["beat"]} | {s["name"]} | {"PASS" if s["result"] == "pass" else "**MISS**"} | '
                         f'{s["secs"]} | {s["reason"][:90].replace("|", "/")} | {fr} |')
        if doc['why'] != 'done':
            table.append(f'| {plan} | | | (plan ended: {doc["why"]}) | | | | |')
        for n in notes[:12]:
            summary.append(f'    - t={n["t"]} {n["kind"]}: ' + json.dumps({k: v for k, v in n.items() if k not in ("t", "kind")})[:200])
    lines += ['## Summary', ''] + summary + ['', '## Per-beat pass/fail', ''] + table + ['']
    lines += ['## Contact sheets', '']
    for plan in plans:
        s = sheet(os.path.join(run_dir, plan), os.path.join(run_dir, f'sheet_{plan}.png'))
        if s:
            lines.append(f'- {plan}: `{s}` ({len(frames_of(os.path.join(run_dir, plan)))} frames in `{plan}/frames/`)')
    pre = ROOT + '/Saved/QA/preflight.json'
    if os.path.exists(pre):
        pf = json.load(open(pre, encoding='utf-8'))
        lines += ['', f'## Pre-flight ({time.strftime("%H:%M", time.localtime(os.path.getmtime(pre)))}): Blueprints and interaction montages', '',
                  f'- {"PASS" if pf.get("ok") else "FAIL"} Blueprints: {pf.get("checked")} checked, failures: '
                  + (', '.join(f"{r['path']} {r['status']}" for r in pf.get('failures', [])) or 'none'),
                  f'- {"PASS" if pf.get("montages_ok") else "FAIL"} montages with AN_FoA_InteractionContact: '
                  + (', '.join(m['montage'] for m in pf.get('montage_failures', [])) + ' lack it' if pf.get('montage_failures') else 'all have it')]
    rows = check_rows(run_dir, plans)
    lines += ['', '## Checks (pass/fail; frames for the visual ones)', '',
              f'{sum(r[2] == "PASS" for r in rows)} PASS, {sum(r[2] == "FAIL" for r in rows)} FAIL, '
              f'{sum(r[2] not in ("PASS", "FAIL") for r in rows)} other', '',
              '| check | plan | result | detail | frame |', '|---|---|---|---|---|']
    lines += [f'| {c} | {pl} | {res} | {d.replace("|", "/")} | {os.path.relpath(fr, run_dir).replace(os.sep, "/") if fr else ""} |'
              for c, pl, res, d, fr in rows]
    lines += ['', '## Audio (Hayba audio_active_sounds every 0.5 s during each burst)', ''] + audio_lines(run_dir, plans)
    lines += ['', '## View changes into the player (main 2026-11-10: no body in front of an outside camera)', '']
    for plan in plans:
        pj = os.path.join(run_dir, plan, 'play.json')
        if os.path.exists(pj):
            rows = [e for e in json.load(open(pj, encoding='utf-8'))['log'] if e['kind'] == 'view_into_player']
            lines += [f'- {e["result"]} {plan} at {e["at"]} s: {e["frames_with_body"]} samples with the body in view '
                      f'(camera up to {e["cam_to_head_cm"]} cm from the head); frames `{plan}/frames/*viewchange*`' for e in rows]
    lines += ['', '## Front-end checks (foa_qa a, b, c on the boot frames, `checks/`)', ''] + front_end_checks(run_dir, plans)
    lines += ['', '## Black frames (mean luma < 0.02; expected only on the wake cut and rollover)', '']
    for plan in plans:
        bf = black_frames(os.path.join(run_dir, plan))
        lines.append(f'- {plan}: ' + (', '.join(f'{n} ({m})' for n, m in bf[:12]) + (f' and {len(bf) - 12} more' if len(bf) > 12 else '') if bf else 'none'))
    lines += ['', '## Frame time (QA check f; wall clock per Slate tick, screenshot frames excluded)', '']
    allrows = []
    for plan in plans:
        ft = os.path.join(run_dir, plan, 'frametimes.csv')
        if os.path.exists(ft):
            ok, msg = foa_qa.check_frametime(ft)
            lines.append(f'- {"PASS" if ok else "FAIL"} {plan}: {msg}')
            allrows += [dict(r, t=f'{plan}:{r["t"]}') for r in csv.DictReader(open(ft, encoding='utf-8'))]
            phases = {}
            for r in csv.DictReader(open(ft, encoding='utf-8')):
                if r['near_shot'] != '1':
                    phases.setdefault(r['phase'], []).append(float(r['ms']))
            worst = sorted(((sum(v) / len(v), k, len(v)) for k, v in phases.items() if v), reverse=True)[:4]
            lines.append('    - slowest phases (mean ms, frames): ' + ', '.join(f'{k} {m:.0f} ms ({n})' for m, k, n in worst))
    if allrows:
        comb = os.path.join(run_dir, 'frametimes_all.csv')
        with open(comb, 'w', newline='', encoding='utf-8') as fh:
            wr = csv.DictWriter(fh, fieldnames=['t', 'ms', 'near_shot', 'phase'])
            wr.writeheader()
            wr.writerows(allrows)
        ok, msg = foa_qa.check_frametime(comb)
        lines.append(f'- {"PASS" if ok else "FAIL"} all plans: {msg}')
    logs = subprocess.run([sys.executable, ROOT + '/Tools/QA/foa_qa.py', 'logs'], cwd=ROOT, capture_output=True, text=True)
    lines += ['', '## Logs (`python Tools/QA/foa_qa.py logs`)', '', '```'] + logs.stdout.strip().splitlines()[:120] + ['```', '']
    lines += ['## Errors per plan (each burst\'s own slice of FoA.log, `<plan>/pie_log.txt`)', '']
    for plan in plans:
        pl = os.path.join(run_dir, plan, 'pie_log.txt')
        if not os.path.exists(pl):
            continue
        r = foa_qa.scan_log(open(pl, encoding='utf-8', errors='replace').read().splitlines())
        lines.append(f'- {plan}: {sum(r["bp_errors"].values())} Blueprint runtime errors ({len(r["bp_errors"])} unique), '
                     f'{sum(r["accessed_none"].values())} Accessed None, {sum(r["ensures"].values())} ensures')
        for key in ('bp_errors', 'accessed_none', 'ensures'):
            for msg, n in r[key].most_common(4):
                lines.append(f'    - {n}x {msg[:220]}')
    bugs = os.path.join(run_dir, 'bugs.md')  # the qa lane's frame review, kept apart so a rebuilt report keeps it
    lines += ['', '## Bugs (QA review of the frames)', '']
    lines += open(bugs, encoding='utf-8').read().splitlines() if os.path.exists(bugs) else ['_Not reviewed yet._']
    with open(os.path.join(run_dir, 'report.md'), 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(lines) + '\n')
    print('report:', os.path.join(run_dir, 'report.md'))


def main():
    a = sys.argv[1:]
    if '--abort' in a:
        return abort()
    if '--report' in a:
        run_dir = a[a.index('--report') + 1]
        bursts = json.load(open(os.path.join(run_dir, 'bursts.json'), encoding='utf-8')) if os.path.exists(os.path.join(run_dir, 'bursts.json')) else []
        plans = [p for p in ALL if os.path.isdir(os.path.join(run_dir, p))]
        return report(run_dir, plans, bursts)
    if '--preflight' in a:
        print(json.dumps(preflight(), indent=1)[:1500])
        return print('battle graph:', graph_reaches('/Game/FoA/Gameplay/Encounter/WBP_Encounter', 'RefreshBattlePresentation', 'SetText'))
    forbid_delegates()
    cap = float(a[a.index('--cap') + 1]) if '--cap' in a else 48.0
    named = [x for i, x in enumerate(a) if not x.startswith('--') and (i == 0 or a[i - 1] not in ('--cap', '--into'))]
    unknown = [x for x in named if x not in ALL]
    if unknown:  # an unlisted plan used to fall back to ALL and start dozens of bursts
        sys.exit(f'unknown plan(s) {unknown}: add them to ALL in playtest_all.py first')
    plans = named or ALL
    run_dir = a[a.index('--into') + 1] if '--into' in a else os.path.join(ROOT, 'Saved', 'QA', 'run_' + time.strftime('%Y%m%d_%H%M'))
    run_dir = os.path.abspath(run_dir)  # the in-editor driver resolves relative paths against the engine's folder
    os.makedirs(run_dir, exist_ok=True)
    open(os.path.join(ROOT, 'Saved', 'QA', 'playtest_all.pid'), 'w').write(str(os.getpid()))
    bj = os.path.join(run_dir, 'bursts.json')
    bursts = [b for b in (json.load(open(bj, encoding='utf-8')) if os.path.exists(bj) else []) if b.get('plan') not in plans]
    for plan in plans:
        bursts.append(burst(plan, os.path.join(run_dir, plan), cap))
        json.dump(bursts, open(os.path.join(run_dir, 'bursts.json'), 'w', encoding='utf-8'), indent=1)
        while time.localtime().tm_min % 10 < 3:  # one plan per PIE window: let the other lanes' bursts in, then requeue
            time.sleep(5)
        if '--every-other' in a:  # main 22:2x: yield every other window to the lanes proving their work
            skip_to = (int(time.time() // 600) + 2) * 600  # the start of the window after next
            while time.time() < skip_to - 5:
                time.sleep(5)
    report(run_dir, [p for p in ALL if os.path.isdir(os.path.join(run_dir, p))], bursts)


if __name__ == '__main__':
    main()
