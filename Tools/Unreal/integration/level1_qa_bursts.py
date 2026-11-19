"""Bounded Level1 PIE bursts in the next allowed window; root owns this process.
Each session releases its global lease before the next, and all outcomes remain in Saved/QA.
"""
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path('P:/FoA')
sys.path.insert(0, str(ROOT / 'Tools/Unreal'))
import hayba_call as hc

OWNER = os.environ.get('FOA_QA_OWNER', 'codex-qa')
os.environ.update(FOA_AGENT=OWNER, HAYBA_AGENT_ID=OWNER)
OUT = ROOT / 'Saved/QA' / ('level1_' + datetime.datetime.now().strftime('%Y%m%d_%H%M%S'))
OUT.mkdir(parents=True, exist_ok=True)
ROOT.joinpath('Saved/Integration/level1_qa.pid').write_text(str(os.getpid()))
case_start = 0.0
CASE_CAP = float(os.environ.get('FOA_QA_CASE_CAP', '43'))


def command(name, **args):
    reply = hc.call(name, args, timeout=12)
    assert reply.get('ok'), reply
    return reply.get('data', {})


def inject(script, **env):
    source = ROOT / script
    identity = dict(script=script, sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                    modified=source.stat().st_mtime, injected=time.time(), env=env)
    with OUT.joinpath('source_versions.jsonl').open('a', encoding='utf-8') as versions:
        versions.write(json.dumps(identity) + '\n')
    args = [sys.executable, str(ROOT / 'Tools/Unreal/integration/run_read.py'), str(ROOT / script)]
    args += [f'{k}={v}' for k, v in env.items()]
    child = subprocess.Popen(args, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    ROOT.joinpath('Saved/Integration/level1_qa_child.pid').write_text(str(child.pid))
    try:
        output = child.communicate(timeout=12)[0]
    except subprocess.TimeoutExpired:
        child.kill()  # Only this recorded, owned child.
        output = child.communicate()[0]
        raise RuntimeError(f'Editor script timed out: {script}: {output[-1000:]}')
    OUT.joinpath('injections.log').open('a', encoding='utf-8').write(script + '\n' + output + '\n')
    assert child.returncode == 0, (script, output[-1500:])


def result(path, since, seconds, progress=None):
    file = ROOT / path
    deadline = min(time.time() + seconds, case_start + CASE_CAP)
    while time.time() < deadline:
        if file.exists() and file.stat().st_mtime >= since:
            try:
                data = json.loads(file.read_text(encoding='utf-8'))
            except (json.JSONDecodeError, PermissionError):
                time.sleep(.05)
                continue
            if progress:
                progress(data)
            if str(data.get('status', '')).lower() != 'running':
                return data
        time.sleep(0.2)
    raise TimeoutError(path)


def screenshot(name, show_ui=True):
    name = case_name + '_' + name
    path = str(OUT / (name + '.png'))
    metadata = command('editor_pie_screenshot', filename=path, show_ui=show_ui)
    for _ in range(12):
        if command('editor_pie_screenshot', filename=path, check_only=True).get('captured'):
            break
        time.sleep(0.1)
    OUT.joinpath(name + '_capture.json').write_text(json.dumps(metadata, indent=2))


def roam():
    stamp = time.time()
    inject('Tools/Unreal/encounter/pie_battle_boot.py', FOA_STAGE='roam')
    data = result('Saved/EncounterCaptures/boot_roam.json', stamp, 22)
    assert data['reason'] == 'ready_for_native_W', data


def focus_pie_window():
    """Mouse hit testing needs the owned game window above the editor."""
    import ctypes
    from ctypes import wintypes
    user = ctypes.windll.user32
    found = []
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    def visit(hwnd, _):
        title = ctypes.create_unicode_buffer(512)
        user.GetWindowTextW(hwnd, title, len(title))
        if user.IsWindowVisible(hwnd) and title.value.startswith('FoA Preview ['):
            found.append(hwnd)
        return True

    user.EnumWindows(callback_type(visit), 0)
    assert len(found) == 1, ('Expected one owned PIE window', len(found))
    hwnd = wintypes.HWND(found[0])
    # PIE is destroyed in finally, so this temporary topmost state cannot persist.
    assert user.SetWindowPos(hwnd, wintypes.HWND(-1), 0, 0, 0, 0, 0x43)
    user.SetForegroundWindow(hwnd)


def teen():
    roam()
    stamp = time.time()
    inject('Tools/Unreal/player/pie_teen_capture.py', FOA_INCLUDE_SUIT=1)
    data = result('Saved/CharacterShots/teen_pie.json', stamp, 25)
    screenshot('teen_game', False)
    return data


def battle(width=1280, height=720):
    roam()
    stamp = time.time()
    inject('Tools/Unreal/encounter/pie_battle_boot.py', FOA_STAGE='battle')
    ready = result('Saved/EncounterCaptures/boot_battle.json', stamp, 10)
    assert ready['reason'] == 'battle_ready', ready
    stamp = time.time()
    inject('Tools/Unreal/encounter/pie_ui_layout_check.py', FOA_EXPECT_WIDTH=width, FOA_EXPECT_HEIGHT=height)
    inject('Tools/Unreal/encounter/pie_clothing_motion_check.py')
    screenshot('battle_commands')
    layout = result('Saved/EncounterCaptures/ui_layout_runtime.json', stamp, 13)
    motion = result('Saved/EncounterCaptures/clothing_motion/proof.json', stamp, 9)
    screenshot('battle_final')
    proof = dict(layout=layout, motion=motion)
    if os.environ.get('FOA_COMPARE_LOOK') == '1':
        stamp = time.time()
        inject('Tools/Unreal/integration/pie_look_compare.py')
        proof['look'] = result('Saved/PPShots/game_clarity/proof.json', stamp, 5)
    return proof


def battlefeedback():
    roam()
    stamp = time.time()
    inject('Tools/Unreal/encounter/pie_battle_boot.py', FOA_STAGE='battle')
    ready = result('Saved/EncounterCaptures/boot_battle.json', stamp, 10)
    assert ready['reason'] == 'battle_ready', ready
    stamp, responses = time.time(), {}

    def progress(data):
        if data.get('status') != 'running' or data['label'] in responses:
            return
        name = data['label']
        if data['action'] == 'click':
            responses[name] = command('editor_pie_click_widget', match=data['match'])
        elif data['action'] == 'key':
            responses[name] = command('editor_pie_press_key', key=data['key'], held_ms=80)
        else:
            snapshot = command('editor_pie_widget_tree', filter='STextBlock', max_depth=80)
            viewports = command('editor_pie_widget_tree', filter='SWindow', max_depth=80)
            responses[name] = dict(request=data, text=snapshot, viewports=viewports)
            OUT.joinpath('battlefeedback_' + name + '_slate.json').write_text(json.dumps(responses[name], indent=2))
        Path(data['ack']).write_text(name)

    inject('Tools/Unreal/encounter/pie_battle_feedback_check.py', FOA_BATTLE_UI_OUT=str(OUT / 'battlefeedback_pages'))
    proof = result('Saved/EncounterCaptures/battle_feedback_runtime.json', stamp, 29, progress=progress)
    failures, checks = [], []
    for name, data in responses.items():
        if 'request' not in data:
            continue
        widgets = [w for w in data['text'].get('widgets', []) if w.get('text') and w.get('width', 0) > 0 and w.get('height', 0) > 0]
        viewports = [v for v in data['viewports'].get('widgets', []) if v.get('width', 0) > 0 and v.get('height', 0) > 0]
        viewport = max(viewports, key=lambda v: v['width'] * v['height']) if viewports else None
        if viewport is None:
            failures.append([name, 'Game window bounds unavailable'])
        rects = []
        for text in data['request']['commands']:
            matches = [w for w in widgets if w['text'] == text]
            if not matches:
                failures.append([name, 'Command missing from native Slate', text])
            else:
                rects.append(matches[-1])
        for index, a in enumerate(rects):
            for b in rects[index + 1:]:
                if min(a['x']+a['width'],b['x']+b['width']) > max(a['x'],b['x']) + 2 and min(a['y']+a['height'],b['y']+b['height']) > max(a['y'],b['y']) + 2:
                    failures.append([name, 'Commands overlap', a, b])
        for text in data['request']['expected_text']:
            matches = [w for w in widgets if w['text'] == text]
            if not matches:
                failures.append([name, 'Feedback missing from native Slate', text])
            elif viewport and not any(w['x'] >= viewport['x'] - 2 and w['y'] >= viewport['y'] - 2
                                      and w['x'] + w['width'] <= viewport['x'] + viewport['width'] + 2
                                      and w['y'] + w['height'] <= viewport['y'] + viewport['height'] + 2 for w in matches):
                failures.append([name, 'Feedback extends beyond game window', text, matches])
        checks.append(dict(frame=name, commands=len(rects), expected_text=data['request']['expected_text']))
    proof['native_ui'] = dict(checks=checks, failures=failures, responses=responses)
    if failures:
        proof['result'] = 'FAIL'
    return proof


def wardrobe():
    roam()
    stamp = time.time()
    inject('Tools/Unreal/gameplay/pie_wardrobe_transition.py', FOA_FROM_ROAM=1)
    return result('Saved/Integration/wardrobe_transition.json', stamp, 34)


def pacing():
    roam()
    stamp = time.time()
    inject('Tools/Unreal/gameplay/pie_pacing_proof.py')
    proof = result('Saved/Integration/pacing_runtime.json', stamp, 29)
    screenshot('pacing_after')
    return proof


def tools():
    roam()
    stamp = time.time()
    native = os.environ.get('FOA_TOOL_NATIVE') == '1'
    inject('Tools/Unreal/gameplay/pie_door_tools_proof.py', FOA_TOOL_NATIVE=int(native))
    driven, inputs = set(), []
    holds = {'ready_native_D_350ms_then_Q': 350, 'ready_native_D_key_until_bind': 8500,
             'ready_native_A_key_ease_1300ms': 1300, 'ready_native_D_key_retry_3500ms': 3500,
             'ready_native_D_screws_11500ms': 11500, 'ready_native_D_reset_2800ms': 2800}
    screw_hold_until = None

    def release_screw_hold():
        nonlocal screw_hold_until
        reply = command('editor_pie_press_key', key='D', event='released')
        assert reply.get('dispatched'), reply
        inputs.append(reply)
        screw_hold_until = None

    def drive(data):
        nonlocal screw_hold_until
        if screw_hold_until is not None and (time.time() >= screw_hold_until or any(
                row.get('label') in ('plate_release_before_reentry', 'four_screws_removed')
                for row in data.get('rows', []))):
            release_screw_hold()
        for row in data.get('rows', []):
            label = row.get('label')
            if label not in holds or label in driven:
                continue
            driven.add(label)
            if label == 'ready_native_A_key_ease_1300ms' and screw_hold_until is not None:
                release_screw_hold()
            if label == 'ready_native_D_key_retry_3500ms':
                command('editor_pie_press_key', key='A', event='released')
            if label in ('ready_native_D_screws_11500ms', 'ready_native_D_key_until_bind'):
                time.sleep(.25)
            screenshot(label)
            if label in ('ready_native_D_screws_11500ms', 'ready_native_D_key_until_bind'):
                # Hayba clamps scheduled holds to 5000ms, even when its receipt
                # echoes a larger requested duration. Own this longer hold.
                screw_hold_until = time.time() + holds[label] / 1000.0
                reply = command('editor_pie_press_key', key='D', event='pressed')
            else:
                key = 'A' if label.startswith('ready_native_A') else 'D'
                reply = command('editor_pie_press_key', key=key, event='pressed_and_released', held_ms=holds[label])
            assert reply.get('dispatched'), reply
            inputs.append(reply)
            if label == 'ready_native_D_350ms_then_Q':
                time.sleep(.5)
                reply = command('editor_pie_press_key', key='Q', event='pressed_and_released', held_ms=100)
                assert reply.get('dispatched'), reply
                inputs.append(reply)

    try:
        proof = result('Saved/Integration/door_tools_runtime.json', stamp, 44, drive if native else None)
    finally:
        if screw_hold_until is not None:
            release_screw_hold()
    if native:
        proof['native_inputs'] = inputs
    screenshot('tools_after')
    return proof


def movement():
    roam()
    stamp = time.time()
    inject('Tools/Unreal/integration/pie_movement_proof.py')
    inputs = []
    for key in 'WASD':
        inputs.append(command('editor_pie_press_key', key=key, event='pressed_and_released', held_ms=500))
        time.sleep(.85)
    proof = result('Saved/Integration/movement_runtime.json', stamp, 9)
    proof['native_inputs'] = inputs
    screenshot('movement_after')
    return proof


def outcomes():
    stamp = time.time()
    inject('Tools/Unreal/encounter/pie_outcomes_proof.py', FOA_OUTCOME_MODE='win', FOA_CAP=35)
    proof = result('Saved/EncounterCaptures/outcomes_proof.json', stamp, 38)
    screenshot('outcome_after')
    return proof


def settings():
    roam()
    stamp = time.time()
    native = os.environ.get('FOA_SETTINGS_NATIVE_LAYOUT') == '1'
    snapshots, clicks = {}, {}

    def inspect_page(data):
        if not native or data.get('status') != 'running':
            return
        page = data['page']
        if data.get('action') == 'click_page':
            if page not in clicks:
                clicks[page] = command('editor_pie_click_widget', match=data['match'])
                Path(data['ack']).write_text('clicked:' + str(page))
            return
        if page in snapshots:
            return
        snapshot = command('editor_pie_widget_tree', filter='STextBlock', max_depth=80)
        snapshots[page] = dict(expected=data['expected'], actual=data['actual'], snapshot=snapshot)
        OUT.joinpath(f'{case_name}_slate_{page}.json').write_text(json.dumps(snapshots[page], indent=2))
        Path(data['ack']).write_text('captured:' + str(page))

    inject('Tools/Unreal/ui/pie_settings_check.py',
           FOA_LAYOUT_ONLY=os.environ.get('FOA_SETTINGS_LAYOUT_ONLY', '0'),
           FOA_UI_NATIVE_LAYOUT='1' if native else '0',
           FOA_UI_OUT=str(OUT / (case_name + '_pages')))
    proof = result('Saved/UIShots/settings_runtime.json', stamp, 18, progress=inspect_page)
    if native:
        checks, failures = [], []
        for page, data in snapshots.items():
            widgets = data['snapshot'].get('widgets', [])
            text_widgets = [w for w in widgets if w.get('text') and w.get('width', 0) > 0 and w.get('height', 0) > 0]
            for row in data['expected']:
                labels = [w for w in text_widgets if w['text'] == row['label']]
                values = [w for w in text_widgets if w['text'] == row['value']]
                pairs = [(label, value) for label in labels for value in values
                         if abs(label['center_y'] - value['center_y']) < 8]
                valid = [(label, value) for label, value in pairs if label['x'] + label['width'] + 8 <= value['x']]
                checks.append(dict(page=page, row=row['row'], verified=bool(valid), pairs=valid))
                if not valid:
                    failures.append(dict(page=page, row=row, labels=labels, values=values))
        proof['native_layout'] = dict(pages=len(snapshots), clicks=clicks, checks=checks, failures=failures)
        if len(snapshots) != 4 or failures:
            proof['result'] = 'FAIL'
            proof['native_layout_error'] = 'Native Slate bounds did not verify every visible Settings row'
    screenshot('settings_after')
    return proof


now = datetime.datetime.now()
target = now.replace(second=0, microsecond=0)
if now.minute % 10 < 2:
    target = now
else:
    target += datetime.timedelta(minutes=(10 - now.minute % 10))
if os.environ.get('FOA_QA_START'):
    target = datetime.datetime.fromisoformat(os.environ['FOA_QA_START'])
print('QA process', os.getpid(), 'next window', target.isoformat(), 'output', OUT, flush=True)
cases = [('teen', teen, 1280, 720),
         ('battlefeedback', battlefeedback, 960, 640),
         ('battlelarge', lambda: battle(1600, 900), 1600, 900),
         ('battle720', lambda: battle(1280, 720), 1280, 720),
         ('battle960', lambda: battle(960, 640), 960, 640),
         ('wardrobe', wardrobe, 1280, 720),
         ('pacing', pacing, 1280, 720), ('tools', tools, 1280, 720), ('movement', movement, 1280, 720),
         ('outcomes', outcomes, 1280, 720), ('settings', settings, 1280, 720),
         ('settings960', settings, 960, 640)]
if os.environ.get('FOA_QA_CASES'):
    selected = os.environ['FOA_QA_CASES'].split(',')
    cases = [next(case for case in cases if case[0] == name) for name in selected]
spacing = int(os.environ.get('FOA_QA_SPACING', '35'))
settings_path = '/Script/UnrealEd.Default__LevelEditorPlaySettings'
for index, (name, run, width, height) in enumerate(cases):
    case_name = name
    at = target + datetime.timedelta(seconds=index * spacing)
    while datetime.datetime.now() < at:
        time.sleep(0.2)
    acquired = subprocess.run([sys.executable, str(ROOT / 'Tools/Unreal/editor_lock.py'), 'acquire', OWNER,
                               '--ttl', '60', '--wait', '10'], cwd=ROOT, text=True, capture_output=True)
    print(acquired.stdout.strip(), flush=True)
    if acquired.returncode:
        print('SKIP lease rejected', name, acquired.stderr[-300:], flush=True)
        continue
    started = False
    payload = {}
    settings = None
    case_start = time.time()
    try:
        assert not command('editor_get_state').get('pie_running'), 'User PIE already running'
        settings = command('object_get_property', path=settings_path,
                           names=['NewWindowWidth', 'NewWindowHeight', 'LastExecutedPlayModeType'])['properties']
        command('object_set_property', path=settings_path,
                properties=dict(NewWindowWidth=width, NewWindowHeight=height,
                                LastExecutedPlayModeType='PlayMode_InEditorFloating'))
        command('editor_start_pie'); started = True
        for _ in range(15):
            if command('editor_get_state').get('pie_running'):
                break
            time.sleep(0.1)
        else:
            raise RuntimeError('PIE did not become active')
        focus_pie_window()
        payload = run()
    except Exception as error:
        payload = dict(error=repr(error))
    finally:
        try:
            if started:
                command('editor_stop_pie')
            if settings:
                command('object_set_property', path=settings_path, properties=settings)
        finally:
            subprocess.run([sys.executable, str(ROOT / 'Tools/Unreal/editor_lock.py'), 'release', OWNER], cwd=ROOT)
    payload['lease_elapsed_s'] = time.time() - case_start
    OUT.joinpath(name + '.json').write_text(json.dumps(payload, indent=2))
    print(name, json.dumps(payload)[:1400], flush=True)
print('QA bursts finished', OUT, flush=True)
