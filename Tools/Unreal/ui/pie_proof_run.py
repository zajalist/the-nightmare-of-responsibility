"""ui lane: one EXCLUSIVE PIE proof burst (pie_proof.py), only inside a PIE window, then crop the frames to the game
viewport and run the QA checks on them.
  python Tools/Unreal/ui/pie_proof_run.py [OUT_DIR] [UI_MODE=boot]   default Saved/UIShots/proof_<HHMM>
Frames: OUT/frames/NN_<name>.png (cropped), OUT/frames/raw (whole window). Then: python Tools/QA/foa_qa.py checks OUT/frames"""
import glob
import json
import os
import shutil
import subprocess
import sys
import time

from PIL import Image

ROOT = 'P:/FoA'
sys.path.insert(0, ROOT + '/Tools/Unreal')
import editor_lock  # noqa: E402
import hayba_call as hc  # noqa: E402

PLAY = '/Script/UnrealEd.Default__LevelEditorPlaySettings'
WIN = (1600, 900)  # a new 16:9 PIE window, so UI scale and contrast match a real 16:9 game window


def win_size():
    p = hc.call('object_get_property', {'path': PLAY})['data']['properties']
    return int(p['NewWindowWidth']), int(p['NewWindowHeight'])


def set_win(wh):
    hc.call('object_set_property', {'path': PLAY, 'properties': {'NewWindowWidth': wh[0], 'NewWindowHeight': wh[1]}})

LANE = 'ui'
SHOTS = ROOT + '/Saved/Screenshots/WindowsEditor'
os.environ['HAYBA_AGENT_ID'] = os.environ['FOA_AGENT'] = LANE
out = sys.argv[1] if len(sys.argv) > 1 else ROOT + '/Saved/UIShots/proof_' + time.strftime('%H%M')
os.makedirs(out + '/frames/raw', exist_ok=True)
while True:
    editor_lock.acquire(LANE, wait_s=1500, ttl=75)  # EXCLUSIVE: waits for the PIE window by itself
    if editor_lock.in_exclusive_window(time.time() + 10):
        break
    editor_lock.release(LANE)  # granted at the window's very end
    time.sleep(30)
before = set(glob.glob(SHOTS + '/ScreenShot*.png'))
t0 = time.time()
env = dict(os.environ, FOA_EXCLUSIVE='1')
old_win = win_size()
try:
    set_win(WIN)
    r = subprocess.run([sys.executable, ROOT + '/Tools/Unreal/ue_remote.py', ROOT + '/Tools/Unreal/ui/pie_proof.py',
                        f'UI_OUT={out}', 'UI_CAP=50', 'UI_PIE=hayba', *sys.argv[2:]], env=env, capture_output=True,
                       text=True, timeout=60)  # extra KEY=VALUE args (UI_MODE=boot) reach the driver
    print(r.stdout.strip()[-300:], r.stderr.strip()[-300:], flush=True)
    started = 'PIE begin requested' in r.stdout
    if started:
        print('editor_start_pie', hc.call('editor_start_pie', {}).get('ok'), flush=True)
    while started and not os.path.exists(out + '/done.json') and time.time() - t0 < 55:
        time.sleep(0.5)
    if not os.path.exists(out + '/done.json'):
        subprocess.run([sys.executable, ROOT + '/Tools/Unreal/ue_remote.py', ROOT + '/Tools/Unreal/ui/pie_proof.py',
                        'UI_CMD=END'], env=env, timeout=30)
    time.sleep(1.0)
finally:
    set_win(old_win)  # the user's PIE window size back
    editor_lock.release(LANE)
print(f'EXCLUSIVE held {time.time() - t0:.0f} s')
time.sleep(2.0)  # the last Shot lands a frame or two later
shots = json.load(open(out + '/shots.json')) if os.path.exists(out + '/shots.json') else []
new = sorted(set(glob.glob(SHOTS + '/ScreenShot*.png')) - before)
print('shots', len(shots), 'files', len(new))
# shortcut: 'Shot showui' saves the whole editor window and the viewport rect reads as zero from Python, so the 16:9
# game image is cut at the current layout's letterbox (maximized 1920x1080 editor); the bar check flags a moved layout
CROP = tuple(int(v) for v in os.environ.get('UI_CROP', '4,226,1295,952').split(','))
for i, (s, f) in enumerate(zip(shots, new)):
    name = f'{i:02d}_{s["name"]}.png'
    shutil.copy(f, out + '/frames/raw/' + name)
    im = Image.open(f).convert('RGB')
    if (im.width, im.height) == (WIN[0] + 6, WIN[1] + 40):  # the new PIE window: 3 px frame, 37 px title bar
        im.crop((3, 36, 3 + WIN[0], 36 + WIN[1])).save(out + '/frames/' + name)
        continue
    bars = [im.getpixel((CROP[2] // 2, y))[1] for y in (CROP[1] - 6, CROP[3] + 4)]
    if max(bars) > 8:
        print('WARNING letterbox not where expected in', name, bars)
    im.crop(CROP).save(out + '/frames/' + name)
print(json.load(open(out + '/done.json')) if os.path.exists(out + '/done.json') else 'NO done.json')
print('frames ->', out + '/frames')
