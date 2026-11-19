"""Rig lane: one EXCLUSIVE PIE burst (PIE up <= 50 s, started only in a PIE window :x0-:x2) that runs
rig/pie_fight_film.py, stops PIE, restores the settings save bytes, releases the lease, then builds
Saved/RigShots/garments/fight_film.mp4 from the frames (real time: fps = frames per game second sampled).
  python Tools/Unreal/rig/run_fight_film.py"""
import datetime
import json
import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, 'P:/FoA/Tools/Unreal')
import hayba_call as h  # noqa: E402

os.environ['HAYBA_AGENT_ID'] = owner = 'rig'
LOCK = ['python', 'P:/FoA/Tools/Unreal/editor_lock.py']
OUT = Path('P:/FoA/Saved/RigShots/garments/fight_film.json')
SHOTS = Path('P:/FoA/Saved/RigShots/garments/fight_film')
prefs = Path('P:/FoA/Saved/SaveGames/Settings.sav')


def in_window():
    m = datetime.datetime.now().minute % 10
    return m in (0, 1) or (m == 2 and datetime.datetime.now().second < 5)  # room for a 55 s burst inside :x0-:x2


def call(name, **args):
    r = h.call(name, args, owner=owner, timeout=20)
    assert r.get('ok'), r
    return r.get('data', {})


while True:
    while not in_window():
        time.sleep(5)
    if subprocess.run(LOCK + ['acquire', owner, '--ttl', '60', '--wait', '60']).returncode != 0:
        continue
    if in_window():
        break
    subprocess.run(LOCK + ['release', owner])  # granted too late in the window: give it back, wait for the next one

for f in SHOTS.glob('v_*.png'):
    f.unlink()
original = prefs.read_bytes() if prefs.exists() else None
started = False
t0 = time.time()
try:
    assert not call('editor_get_state')['pie_running'], 'PIE already running'
    started = call('editor_start_pie').get('pie_started', False)
    assert started, 'PIE did not start'
    print('PIE_START', time.strftime('%T'), flush=True)
    time.sleep(0.5)
    stamp = time.time()
    call('python_exec_file', path='P:/FoA/Tools/Unreal/rig/pie_fight_film.py', env={}, resources=['global'])
    while time.time() - stamp < 47:
        if OUT.exists() and OUT.stat().st_mtime >= stamp:
            try:
                rep = json.loads(OUT.read_text())
            except (json.JSONDecodeError, PermissionError):
                time.sleep(0.1)
                continue
            print('RESULT', rep['reason'], rep['frames'], 'frames', rep['clips_seen'])
            for e in rep['fight'] or []:
                print(e)
            break
        time.sleep(0.2)
    else:
        print('RESULT runner_timeout')
finally:
    if started:
        call('editor_stop_pie')
        if original is not None:
            prefs.write_bytes(original)
    print('PIE_END', time.strftime('%T'), 'up', round(time.time() - t0, 1), 's', flush=True)
    subprocess.run(LOCK + ['release', owner])

rep = json.loads(OUT.read_text())
ts = [r['t'] for r in rep['rows'] if 't' in r]
fps = round((len(ts) - 1) / (ts[-1] - ts[0]), 2)  # real time: frames per game second
frames = sorted(SHOTS.glob('f_*.png'))
for i, f in enumerate(frames):  # contiguous numbering for ffmpeg
    f.rename(SHOTS / f'v_{i:05d}.png')
subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-framerate', str(fps), '-i', str(SHOTS / 'v_%05d.png'),
                '-vf', 'scale=1600:-2', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '20',
                str(SHOTS.parent / 'fight_film.mp4')], check=True)
print(len(frames), 'frames ->', SHOTS.parent / 'fight_film.mp4', 'at', fps, 'fps')
