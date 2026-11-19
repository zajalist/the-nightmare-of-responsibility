"""Rig lane: one EXCLUSIVE PIE burst for a rig PIE driver (PIE up <= 50 s, started only in a PIE window :x0-:x2).
  python Tools/Unreal/rig/run_rig_pie.py <driver.py> <result.json> <frames dir> <video.mp4> [KEY=VALUE ...]
Runs the driver in PIE (KEY=VALUE reach it as os.environ), waits for its result json, stops PIE, restores the settings
save bytes, releases the lease, then builds the MP4 from the driver's f_*.png frames (fps = frames per second of run)."""
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
driver, out, shots, video = sys.argv[1:5]
env = dict(a.split('=', 1) for a in sys.argv[5:])
OUT, SHOTS = Path(out), Path(shots)
LOCK = ['python', 'P:/FoA/Tools/Unreal/editor_lock.py']
prefs = Path('P:/FoA/Saved/SaveGames/Settings.sav')


def in_window():
    n = datetime.datetime.now()
    return n.minute % 10 in (0, 1) or (n.minute % 10 == 2 and n.second < 5)


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
    subprocess.run(LOCK + ['release', owner])

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
    call('python_exec_file', path=driver, env=env, resources=['global'])
    while time.time() - stamp < 48:
        if OUT.exists() and OUT.stat().st_mtime >= stamp:
            try:
                rep = json.loads(OUT.read_text())
            except (json.JSONDecodeError, PermissionError):
                time.sleep(0.1)
                continue
            print('RESULT', json.dumps(rep.get('summary', rep.get('reason')))[:1500], flush=True)
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

frames = sorted(SHOTS.glob('f_*.png'))
if len(frames) > 2:
    span = frames[-1].stat().st_mtime - frames[0].stat().st_mtime
    fps = round(max(4.0, min(30.0, (len(frames) - 1) / max(span, 0.1))), 2)
    for i, f in enumerate(frames):
        f.rename(SHOTS / f'v_{i:05d}.png')
    subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-framerate', str(fps), '-i', str(SHOTS / 'v_%05d.png'),
                    '-vf', 'scale=1600:-2', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '20', video], check=True)
    for i in range(len(frames)):
        (SHOTS / f'v_{i:05d}.png').rename(SHOTS / f'f_{i + 1:04d}.png')
    print(len(frames), 'frames ->', video, 'at', fps, 'fps')
