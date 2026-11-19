"""One <=60 s EXCLUSIVE map switch, with dirty gate and verified bedroom return.
python Tools/Splats/run_splat_dynamics_map.py dream|city build|proof|perf
"""
import json
import os
from pathlib import Path
import subprocess
import shutil
import sys
import time

os.environ.update(FOA_AGENT='splat-vfx', HAYBA_AGENT_ID='splat-vfx', FOA_EXCLUSIVE='1', FOA_AREAS='/Game/FoA/Level2')
sys.path.insert(0, 'P:/FoA/Tools/Unreal')
import hayba_call as h
from build_splat_dynamics import call

ROOT = Path('P:/FoA')
OUT = ROOT / 'Saved/Codex/splat_dynamics'
BED = '/Game/FoA/Maps/L_Tutorial_Bedroom'
BP = '/Game/FoA/Level2/Blueprints/BP_SplatFXDirector'
_last_renew = None


def script(path, **env):
    global _last_renew
    if _last_renew is not None and time.monotonic() - _last_renew > 20:
        assert any('global' in resources for _, resources in h.leases_of('splat-vfx')), 'Lost EXCLUSIVE'
        h.renew_all('splat-vfx', 70)
        _last_renew = time.monotonic()
    p = subprocess.run([sys.executable, 'Tools/Unreal/integration/run_read.py', path,
                        *[f'{k}={v}' for k, v in env.items()]], cwd=ROOT, capture_output=True, text=True, timeout=15)
    print(p.stdout, flush=True)
    assert p.returncode == 0, p.stderr + p.stdout
    return p.stdout


def count():
    return next(s for s in script('Tools/Splats/l2_dream_map.py', FOA_L2MAP='count').splitlines() if 'L2MAP count' in s)


def run(kind, mode):
    global _last_renew
    assert kind in ('dream', 'city') and mode in ('build', 'proof', 'perf')
    OUT.mkdir(exist_ok=True)
    (OUT / 'runner.pid').write_text(str(os.getpid()))
    subprocess.run([sys.executable, 'Tools/Unreal/editor_lock.py', 'acquire', 'splat-vfx', '--ttl', '60', '--wait', '600'], check=True)
    _last_renew = time.monotonic()
    switched = pie = capture_stopped = False
    start = time.monotonic()
    log = {'kind': kind, 'mode': mode, 'start': time.time()}
    try:
        state = call('editor_get_state')
        if state['pie_running']:
            time.sleep(2)
            state = call('editor_get_state')
        assert not state['pie_running'], 'PIE already running'
        assert 'L_Tutorial_Bedroom' in state['map'], state['map']
        dirty = [p for p in state['dirty_packages'] if '/Maps/' in p or '__External' in p or 'L_Tutorial_Bedroom' in p]
        assert not dirty, ('Coordinator must resolve dirty bedroom packages', dirty)
        before = count(); log['before'] = before
        path = '/Game/FoA/Level2/Maps/L_L2_' + ('DreamTest' if kind == 'dream' else 'CityTest')
        switched = True
        call('level_load', path=path)
        if mode == 'build':
            have = call('actor_list', class_filter='BP_SplatFXDirector_C')['actors']
            assert len(have) <= 1, have
            actor_id = have[0]['id'] if have else call('actor_spawn', class_path=BP+'.BP_SplatFXDirector_C', location=[0,0,0], label='SplatFXDirector')['actor_id']
            call('actor_set_properties', actor_id=actor_id, properties={
                'AmbientIntensity': .8, 'SandRadius': 1800 if kind == 'city' else 240,
                'SandCentre': {'R': 5000 if kind == 'city' else 300, 'G': 1000 if kind == 'city' else 0, 'B': 150, 'A': 0}})
            script('Tools/Splats/splat_dynamics_map.py', SPLAT_STEP='cpd', SPLAT_MAP=kind)
            call('level_save')
        else:
            (OUT / (kind + '_cvars.json')).unlink(missing_ok=True)
            pie = True
            script('Tools/Unreal/ui/pie_call.py', FOA_CALL='BEGIN')
            time.sleep(2)
            script('Tools/Splats/splat_dynamics_map.py', SPLAT_STEP='proof', SPLAT_MAP=kind)
            if mode == 'proof':
                # Fixed-camera desktop proof; the coordinator's recorder is left alone.
                video = OUT / (kind + '_dynamics.mp4')
                window = subprocess.check_output(['powershell', '-NoProfile', '-Command',
                    "(Get-Process UnrealEditor | Where-Object MainWindowTitle -like 'FoA Preview*' | Select-Object -First 1).MainWindowTitle"], text=True).strip()
                assert window, 'No FoA preview window; refuse to record the wrong surface'
                log['recorded_window'] = window
                p = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'gdigrab', '-framerate', '30',
                                      '-i', 'title=' + window, '-t', '14', '-an', '-c:v', 'libx264',
                                      '-preset', 'ultrafast', '-crf', '20', '-vf', 'pad=ceil(iw/2)*2:ceil(ih/2)*2',
                                      '-pix_fmt', 'yuv420p', str(video)],
                                     stdout=subprocess.DEVNULL, stderr=open(OUT / (kind+'_record.log'), 'w'))
                log['ffmpeg_pid'] = p.pid
                try:
                    p.wait(timeout=20)
                except subprocess.TimeoutExpired:
                    subprocess.run(['taskkill', '/T', '/F', '/PID', str(p.pid)], check=False)
                    raise
                assert p.returncode == 0, 'See recorder log'
            else:
                log['samples'] = []
                for state in ['off_rest', 'on_rest', 'off_sand', 'on_sand']:
                    assert time.monotonic() - start < 42, 'Burst limit; return to bedroom'
                    stamp = script('Tools/Splats/splat_dynamics_map.py', SPLAT_STEP='state', SPLAT_MAP=kind, SPLAT_STATE=state)
                    log['samples'].append({'state': state, 'wall': time.time(), 'readback': stamp})
                    time.sleep(2)
                    script('Tools/Splats/splat_dynamics_map.py', SPLAT_STEP='state', SPLAT_MAP=kind, SPLAT_STATE='shot', SPLAT_SHOT=state)
            script('Tools/Splats/splat_dynamics_map.py', SPLAT_STEP='state', SPLAT_MAP=kind, SPLAT_STATE='stop')
            capture_stopped = True
        log['completed'] = True
    except Exception as exc:
        log['error'] = str(exc)
        raise
    finally:
        cleanup_error = None
        try:
            if pie:
                # Restore capture CVars even if recording or a later sample failed.
                if not capture_stopped:
                    try:
                        script('Tools/Splats/splat_dynamics_map.py', SPLAT_STEP='state', SPLAT_MAP=kind, SPLAT_STATE='stop')
                    except Exception as exc:
                        log['capture_cleanup_error'] = str(exc)
                script('Tools/Unreal/ui/pie_call.py', FOA_CALL='END')
                time.sleep(1)
        except Exception as exc:
            cleanup_error = exc
            log['pie_cleanup_error'] = str(exc)
        finally:
            if switched:
                call('level_load', path=BED)
                after = count(); log['after'] = after
                assert before == after, ('Bedroom verification failed', before, after)
        log['hold_seconds'] = time.monotonic() - start
        for csv in (ROOT / 'Saved/Profiling/CSV').glob('*.csv'):
            if csv.stat().st_mtime >= log['start']:
                shutil.copy2(csv, OUT / (kind+'_'+mode+'_'+csv.name))
        (OUT / f'{kind}_{mode}_switch.json').write_text(json.dumps(log, indent=2))
        subprocess.run([sys.executable, 'Tools/Unreal/editor_lock.py', 'release', 'splat-vfx'], check=True)
        print('SPLAT return verified' if switched else 'SPLAT released without switching',
              round(log['hold_seconds'], 2), 'seconds', flush=True)
        if cleanup_error:
            raise cleanup_error


if __name__ == '__main__':
    run(*sys.argv[1:])
