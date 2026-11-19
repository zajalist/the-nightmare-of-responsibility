"""Story lane: the T1-to-T10 proof for the carried-set inventory and the Notify fix (main, 2026-11-10). ONE EXCLUSIVE hold
(main's order): QA's pie_play.py plans back to back through playtest_all.burst, each on the FoA_QA_Play save context the
driver sets, under the story owner, with the hold renewed between bursts (burst's own acquire and release become no-ops
inside the hold). Then pie_inventory_repro (the spent screwdriver) inside the same hold. A failed plan stops the run.
  python Tools/Unreal/flow/prove_inventory_run.py [plans...]  ->  Saved/StoryShots/inventory_run.json, inventory_run/<plan>/"""
import json
import os
import subprocess
import sys
import time

sys.path.insert(0, 'P:/FoA/Tools/QA')
import playtest_all as Q  # noqa: E402

Q.OWNER = 'story'
os.environ.update(FOA_AGENT='story', HAYBA_AGENT_ID='story', FOA_CALLER='story', MSYS_NO_PATHCONV='1')
ROOT = 'P:/FoA'
OUT = ROOT + '/Saved/StoryShots/inventory_run'
os.makedirs(OUT, exist_ok=True)
plans = sys.argv[1:] or ['A1', 'A2', 'A3', 'B1', 'B2', 'B3', 'C']
real_lock = Q.lock


def lock(cmd, *extra):  # inside our one hold: burst's acquire and release are no-ops, renew still renews
    if cmd in ('acquire', 'release'):
        return subprocess.CompletedProcess([], 0, '', '')
    return real_lock(cmd, *extra)


def passed(info, plan=None):
    r = info.get('result')  # pie_play's done.json: {"why": "done", "passed": n, "steps": n}
    if isinstance(r, dict) and r.get('why') in ('pie_gone', 'cap') and plan:
        try:  # QA's item-inspect test (UI's feature) can end a floating PIE or run out the cap: judge the steps before it
            log = json.load(open(os.path.join(OUT, plan, 'play.json'), encoding='utf-8'))['log']
            starts = [x.get('name', '') for x in log if x.get('kind') == 'start']
            results = [x.get('result') for x in log if x.get('kind') == 'step' and 'item inspect' not in str(x.get('name', ''))]
            if starts and 'item inspect' in starts[-1] and results and all(x == 'pass' for x in results):
                print('NOTE: plan', plan, 'stopped inside the item-inspect test (%s); every other step passed' % r.get('why'), flush=True)
                return True
            if r.get('why') == 'cap' and results and all(x == 'pass' for x in results[:-1]):
                print('NOTE: plan', plan, 'ran out of its burst in its last step ("%s"); every step before it passed' % starts[-1], flush=True)
                return True  # the next plan starts from its own shortcut, so a time-out mid-step is reported, not fatal
        except (OSError, ValueError, KeyError, IndexError):
            pass
    return isinstance(r, dict) and r.get('why') == 'done' and r.get('passed') == r.get('steps')


summary = {}
r = real_lock('acquire', '--ttl', '90', '--wait', '1500')
print('hold', r.returncode, (r.stdout + r.stderr)[-200:], flush=True)
try:
    assert Q.holds_exclusive(), 'no EXCLUSIVE hold'
    Q.lock = lock
    for plan in plans:
        real_lock('renew', '--ttl', '90')
        info = Q.burst(plan, os.path.join(OUT, plan), 46)
        rows, last = [], None
        try:
            play = json.load(open(os.path.join(OUT, plan, 'play.json'), encoding='utf-8'))
            for row in play['log']:
                items = row.get('items')
                key = (str(items), row.get('beat'))
                if items is not None and key != last:
                    rows.append(dict(t=row.get('t'), beat=row.get('beat'), kind=row.get('kind'), items=items))
                    last = key
        except (OSError, ValueError, KeyError) as ex:
            rows.append(dict(error=repr(ex)))
        summary[plan] = dict(result=info.get('result'), bag=rows)
        json.dump(summary, open(OUT + '.json', 'w', encoding='utf-8'), indent=1, default=str)
        print(plan, json.dumps(summary[plan], default=str)[:900], flush=True)
        try:  # pie_play's frame times: a minimized editor throttles PIE to 3 fps, which makes the run meaningless
            ms = sorted(float(r.split(',')[1]) for r in open(os.path.join(OUT, plan, 'frametimes.csv')).read().splitlines()[2:])
            summary[plan]['median_frame_ms'] = ms[len(ms) // 2] if ms else None
        except (OSError, ValueError, IndexError):
            ms = []
        if ms and ms[len(ms) // 2] > 66:
            print('STOP: plan', plan, 'ran throttled (median %.0f ms per frame)' % ms[len(ms) // 2], flush=True)
            break
        if not passed(info, plan):
            print('STOP: plan', plan, 'did not pass', flush=True)
            break
    else:
        real_lock('renew', '--ttl', '90')
        rep = subprocess.run([sys.executable, ROOT + '/Tools/Unreal/flow/run_chase_final.py', 'pie_inventory_repro'], cwd=ROOT,
                             capture_output=True, text=True, timeout=75)
        print('spare repro', rep.stdout[-300:], rep.stderr[-300:], flush=True)
finally:
    Q.lock = real_lock
    real_lock('release')
    print('released', flush=True)
