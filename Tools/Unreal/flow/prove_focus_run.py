"""Story lane: the focus-flicker proof in ONE EXCLUSIVE hold (main's GO, 2026-11-10): pie_focus_probe (read only), then
pie_focus_repro (expect RED), patch_focus_hold.py, pie_focus_repro again (expect GREEN), then QA's B1 and B2 (the real-E
unhook to T8) through playtest_all.burst under the story owner. Each PIE driver goes through run_chase_final.py inside the
hold; the hold is renewed between steps. A copy of each repro result is kept (focus_repro_red.json, focus_repro_green.json).
  python Tools/Unreal/flow/prove_focus_run.py [--skip-patch]"""
import json
import os
import shutil
import subprocess
import sys

sys.path.insert(0, 'P:/FoA/Tools/QA')
import playtest_all as Q  # noqa: E402

ROOT = 'P:/FoA'
SS = ROOT + '/Saved/StoryShots/'
Q.OWNER = 'story'
os.environ.update(FOA_AGENT='story', HAYBA_AGENT_ID='story', FOA_CALLER='story', MSYS_NO_PATHCONV='1')
real_lock = Q.lock


def lock(cmd, *extra):
    if cmd in ('acquire', 'release'):
        return subprocess.CompletedProcess([], 0, '', '')
    return real_lock(cmd, *extra)


def pie(driver):
    real_lock('renew', '--ttl', '90')
    r = subprocess.run([sys.executable, ROOT + '/Tools/Unreal/flow/run_chase_final.py', driver], cwd=ROOT, capture_output=True,
                       text=True, timeout=80)
    tail = [ln for ln in r.stdout.splitlines() if ln.startswith('RESULT')]
    print(driver, tail, r.stderr[-200:], flush=True)


def verdict(name):
    try:
        d = json.load(open(SS + name, encoding='utf-8'))
        return d.get('reason'), d.get('verdict'), d.get('checks'), d.get('flickers')
    except (OSError, ValueError):
        return None


r = real_lock('acquire', '--ttl', '90', '--wait', '1500')
print('hold', r.returncode, (r.stdout + r.stderr)[-120:], flush=True)
try:
    assert Q.holds_exclusive(), 'no EXCLUSIVE hold'
    if '--skip-patch' not in sys.argv:
        pie('pie_focus_probe')
        pie('pie_focus_repro')
        shutil.copy(SS + 'focus_repro.json', SS + 'focus_repro_red.json')
        print('RED', verdict('focus_repro.json'), flush=True)
    if '--skip-patch' not in sys.argv:
        real_lock('renew', '--ttl', '90')
        p = subprocess.run([sys.executable, ROOT + '/Tools/Unreal/flow/patch_focus_hold.py'], cwd=ROOT, capture_output=True,
                           text=True, timeout=200)
        print('patch', p.stdout[-600:], p.stderr[-300:], flush=True)
    pie('pie_focus_repro')
    shutil.copy(SS + 'focus_repro.json', SS + 'focus_repro_green.json')
    print('GREEN?', verdict('focus_repro.json'), flush=True)
    Q.lock = lock
    for plan in [a for a in sys.argv[1:] if not a.startswith('--')] or ['B1', 'B2']:
        real_lock('renew', '--ttl', '90')
        info = Q.burst(plan, os.path.join(SS, 'focus_run', plan), 46)
        print(plan, json.dumps(info.get('result'), default=str), flush=True)
finally:
    Q.lock = real_lock
    real_lock('release')
    print('released', flush=True)
