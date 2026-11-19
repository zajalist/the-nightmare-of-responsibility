"""Story lane: one EXCLUSIVE hold runs pie_<driver> drivers in order through run_chase_final.py (renewing between them)
and, with --plan X, QA plans through playtest_all.burst under the story owner.
  python Tools/Unreal/flow/prove_defeat_run.py focus_repro defeat_respace [--plan B2]"""
import json
import os
import subprocess
import sys

sys.path.insert(0, 'P:/FoA/Tools/QA')
import playtest_all as Q  # noqa: E402

ROOT = 'P:/FoA'
SS = ROOT + '/Saved/StoryShots/'
Q.OWNER = 'story'
os.environ.update(FOA_AGENT='story', HAYBA_AGENT_ID='story', FOA_CALLER='story', MSYS_NO_PATHCONV='1')
real_lock = Q.lock
args = sys.argv[1:]
plans = [args[i + 1] for i, a in enumerate(args) if a == '--plan']
drivers = [a for i, a in enumerate(args) if a != '--plan' and (i == 0 or args[i - 1] != '--plan')]
r = real_lock('acquire', '--ttl', '90', '--wait', '1500')
print('hold', r.returncode, flush=True)
try:
    assert Q.holds_exclusive(), 'no EXCLUSIVE hold'
    for d in drivers:
        real_lock('renew', '--ttl', '90')
        p = subprocess.run([sys.executable, ROOT + '/Tools/Unreal/flow/run_chase_final.py', 'pie_' + d], cwd=ROOT,
                           capture_output=True, text=True, timeout=85)
        print(d, [ln[:900] for ln in p.stdout.splitlines() if ln.startswith('RESULT')], p.stderr[-300:], flush=True)
    Q.lock = lambda cmd, *x: subprocess.CompletedProcess([], 0, '', '') if cmd in ('acquire', 'release') else real_lock(cmd, *x)
    for plan in plans:
        real_lock('renew', '--ttl', '90')
        info = Q.burst(plan, os.path.join(SS, 'focus_run', plan), 46)
        print(plan, json.dumps(info.get('result'), default=str), flush=True)
finally:
    Q.lock = real_lock
    real_lock('release')
    print('released', flush=True)
