"""Standalone perf run: one -game process of FoA (never the shared editor), driven by Tools/Perf/perf_driver.py.

  python Tools/Perf/perf_run.py --plan l1|l2|idle [--presets 0,1,2,3] [--res 1920x1080] [--sample 4] [--tag before]
         [--cvars "r.X 1;r.Y 0"] [--gpudump 1,3] [--ini "Scalability:[Section]:Key=Value" ...] [--window]

Safety (AGENTS.md / editor-rules.md):
- The game runs from the mirror P:/FoA-PerfMirror, refreshed by robocopy before every run (see mirror()), never
  against P:/FoA: a game process keeps the .uasset files it loaded open, and the shared editor then fails to save
  them (coordinator, 11-17 23:55). The mirror has its own Saved, so the player's saves and settings are never touched.
- The game process gets Python remote execution switched OFF (-ini override), so Tools/Unreal/ue_remote.py can never
  pick it instead of the shared editor; the launcher checks discovery sees exactly one FoA node while the game runs.
- -nosound (no music over the user's session), -RenderOffScreen unless --window (no window over the editor).
- Only the PID this script starts is ever killed (taskkill /T on that PID).
- The mirror's GameUserSettings.ini (the preset switch rewrites it), FoA.sav and Settings.sav are restored afterwards
  (the driver plays in the QA slot), so every run starts from the same state.
Output: Saved/Perf/runs/<stamp>_<plan>_<tag>/ with manifest.json (driver), csv/<moment>_q<preset>.csv, game.log,
shots/, summary.json and summary.md (p50/p95 per segment, top GPU passes)."""
import argparse
import csv
import hashlib
import json
import os
import re
import shutil
import statistics
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path('P:/FoA')
MIRROR = Path('P:/FoA-PerfMirror')  # the game process runs here, never against P:/FoA (see mirror())
EXE = r'C:\Program Files\Epic Games\UE_5.9\Engine\Binaries\Win64\UnrealEditor.exe'
CSV_DIR = MIRROR / 'Saved/Profiling/CSV'
GUS = MIRROR / 'Saved/Config/WindowsEditor/GameUserSettings.ini'
SAVES = [MIRROR / 'Saved/SaveGames/FoA.sav', MIRROR / 'Saved/SaveGames/Settings.sav']
DRIVER = ROOT / 'Tools/Perf/perf_driver.py'
ENGINE_PY = r'C:\Program Files\Epic Games\UE_5.9\Engine\Plugins\Experimental\PythonScriptPlugin\Content\Python'
STATS = ('FrameTime', 'GameThreadTime', 'RenderThreadTime', 'RHIThreadTime', 'GPUTime')


def digest(p):
    return hashlib.sha1(p.read_bytes()).hexdigest() if p.exists() else None


def free_ram_gb():
    out = subprocess.run(['powershell', '-NoProfile', '-Command',
                          '(Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory'], capture_output=True, text=True)
    return int(out.stdout.strip() or 0) / 1048576


def gpu_util():
    out = subprocess.run(['nvidia-smi', '--query-gpu=utilization.gpu', '--format=csv,noheader,nounits'],
                         capture_output=True, text=True)
    return int((out.stdout.strip() or '0').splitlines()[0])


def others_gpu(exclude=()):
    """GPU engine use (percent summed over engines, one 2 s sample) of every process but ours. The shared editor's PIE
    and viewports time-slice the game's GPU passes and inflate them: on 11-18 at 13:44 and 13:57 the editor at about
    44% turned TSR 1.35 into 9.8 ms and the fight's skin-cache pass into 13 to 24 ms. A run above ~10% is not clean."""
    ps = (r"(Get-Counter '\GPU Engine(*)\Utilization Percentage' -SampleInterval 2 -MaxSamples 1).CounterSamples"
          r" | % { $_.InstanceName + '=' + $_.CookedValue }")
    out = subprocess.run(['powershell', '-NoProfile', '-Command', ps], capture_output=True, text=True, timeout=60).stdout
    return round(sum(float(m[2]) for m in (re.match(r'pid_(\d+)_.*=([\d.]+)$', ln.strip()) for ln in out.splitlines())
                     if m and int(m[1]) not in exclude), 1)


def foa_nodes(seconds=4.0):
    """Python remote-execution nodes answering for P:/FoA or the mirror (the shared editor must be the only one)."""
    sys.path.append(ENGINE_PY)
    import remote_execution as rex
    r = rex.RemoteExecution(rex.RemoteExecutionConfig())
    r.start()
    try:
        time.sleep(seconds)
        want = {os.path.normcase(os.path.abspath(str(p))) for p in (ROOT, MIRROR)}
        return [n for n in r.remote_nodes
                if os.path.normcase(os.path.abspath(str(n.get('project_root', '')) or '?')).rstrip('\\/') in want]
    finally:
        r.stop()


def mirror():
    """Coordinator rule (11-17 23:55): never run a game process against P:/FoA. A game that has loaded a .uasset keeps
    it open and the shared editor then cannot save it. Robocopy the project to MIRROR (Content, Config, Plugins,
    FoA.uproject; no Saved, Intermediate, DerivedDataCache or .git) and junction its DerivedDataCache to the
    project's, so shaders are not rebuilt. Unchanged files are skipped, so a re-mirror takes seconds."""
    MIRROR.mkdir(exist_ok=True)
    for sub in ('Content', 'Config', 'Plugins'):
        r = subprocess.run(['robocopy', str(ROOT / sub), str(MIRROR / sub), '/MIR', '/R:2', '/W:1', '/NP', '/NFL',
                            '/NDL', '/NJH', '/XD', 'Intermediate', 'Saved', 'DerivedDataCache', '.git'],
                           capture_output=True, text=True)
        if r.returncode >= 8:
            sys.exit(f'mirror of {sub} failed ({r.returncode}): {r.stdout[-800:]}')
    shutil.copy2(ROOT / 'FoA.uproject', MIRROR / 'FoA.uproject')
    ddc = MIRROR / 'DerivedDataCache'
    if not ddc.exists():
        subprocess.run(['cmd', '/c', 'mklink', '/J', str(ddc), str(ROOT / 'DerivedDataCache')], check=True,
                       capture_output=True)


def kill_tree(pid):
    subprocess.run(['taskkill', '/T', '/F', '/PID', str(pid)], capture_output=True)


# ---- CSV summary -------------------------------------------------------------------------------------------------
def read_csv(path):
    with open(path, encoding='utf-8-sig', newline='') as fh:
        rows = list(csv.reader(fh))
    header = rows[0]
    data = []
    for r in rows[1:]:
        if not r or r[0].startswith('[') or r == header or len(r) < len(header) // 2:
            break  # the repeated header and metadata footer (column 0 is EVENTS, usually empty)
        data.append(r)
    cols = {}
    for i, name in enumerate(header):
        vals = []
        for r in data:
            try:
                vals.append(float(r[i]))
            except (ValueError, IndexError):
                pass
        if vals:
            cols[name] = vals
    return cols


def pct(vals, q):
    s = sorted(vals)
    return s[min(len(s) - 1, int(round(q * (len(s) - 1))))]


def summarize_csv(path, trim=3):
    cols = read_csv(path)
    out = {}
    for name in STATS:
        v = cols.get(name, [])[trim:-trim] if len(cols.get(name, [])) > 2 * trim + 5 else cols.get(name, [])
        if v:
            out[name] = dict(p50=round(statistics.median(v), 2), p95=round(pct(v, .95), 2),
                             max=round(max(v), 1), n=len(v))
    gpu = {k[4:]: round(statistics.mean(v), 3) for k, v in cols.items() if k.startswith('GPU/') and v}
    out['gpu_top'] = dict(sorted(gpu.items(), key=lambda kv: -kv[1])[:12])
    return out


def match_csvs(segments, files):
    """Each segment's capture is the CSV whose name stamp is closest after its start (local time)."""
    stamped = []
    for f in files:
        try:
            stamp = datetime.strptime(f.stem.split('(')[1].rstrip(')'), '%Y%m%d_%H%M%S').timestamp()
        except (IndexError, ValueError):
            stamp = f.stat().st_mtime
        stamped.append((stamp, f))
    used, out = set(), []
    for seg in segments:
        best = min(((abs(s - seg['t0']), f) for s, f in stamped if f not in used and -3 < s - seg['t0'] < 6),
                   default=(None, None), key=lambda x: x[0])
        out.append(best[1])
        if best[1]:
            used.add(best[1])
    return out


def table(rows):
    lines = ['| moment | preset | SP% | frames | GPU p50 | GPU p95 | Frame p50 | GT p50 | RT p50 | top GPU passes (ms) |',
             '|---|---|---|---|---|---|---|---|---|---|']
    for r in rows:
        s = r.get('stats') or {}
        g = lambda k, q='p50': s.get(k, {}).get(q, '')  # noqa: E731
        top = ', '.join(f'{k} {v}' for k, v in list(s.get('gpu_top', {}).items())[:5])
        lines.append(f"| {r['moment']} | {r['preset']} | {r.get('screen_percentage', '')} | {r.get('frames', '')} | "
                     f"{g('GPUTime')} | {g('GPUTime', 'p95')} | {g('FrameTime')} | {g('GameThreadTime')} | "
                     f"{g('RenderThreadTime')} | {top} |")
    return '\n'.join(lines)


def selftest():
    """CSV parsing (EVENTS column empty, repeated header and metadata footer) and capture-to-segment matching."""
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / 'Profile(20261118_010000).csv'
        rows = ['EVENTS,FrameTime,GPUTime,GPU/Lights'] + [f',{10 + i % 3},{5 + i % 2},0.5' for i in range(20)]
        p.write_text('\n'.join(rows + ['EVENTS,FrameTime,GPUTime,GPU/Lights', '[HasHeaderRowAtEnd],1,[platform],Windows']))
        cols = read_csv(p)
        assert len(cols['FrameTime']) == 20 and 'EVENTS' not in cols, cols.keys()
        s = summarize_csv(p)
        assert s['GPUTime']['p50'] in (5.0, 5.5, 6.0) and s['gpu_top'] == {'Lights': 0.5}, s
        t0 = datetime(2026, 11, 18, 1, 0, 0).timestamp()
        assert match_csvs([dict(t0=t0 - 0.4), dict(t0=t0 + 30)], [p]) == [p, None]
    print('perf_run selftest passed')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--plan', default='l1')
    ap.add_argument('--presets', default='0,1,2,3')
    ap.add_argument('--res', default='1920x1080')
    ap.add_argument('--sample', default='4')
    ap.add_argument('--tag', default='run')
    ap.add_argument('--cvars', default='')
    ap.add_argument('--gpudump', default='')
    ap.add_argument('--ini', action='append', default=[])
    ap.add_argument('--window', action='store_true')
    ap.add_argument('--burst', default='0', help='consecutive screenshots per segment (ghosting checks)')
    ap.add_argument('--variants', default='', help='JSON A/B list or a .json file: [{"name": "base", "cvars": "r.X 2"}, ...]')
    ap.add_argument('--timeout', type=float, default=420)
    ap.add_argument('--summarize', help='re-summarize an existing run dir (no game process)')
    ap.add_argument('--no-mirror', action='store_true', help='skip the re-mirror (the mirror must already exist)')
    ap.add_argument('--selftest', action='store_true')
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.summarize:
        out = Path(a.summarize)
        man = json.loads((out / 'manifest.json').read_text())
        rows = []
        for seg in man['segments']:
            f = out / 'csv' / f"{seg['moment']}_q{seg['preset']}.csv"
            rows.append(dict(seg, stats=summarize_csv(f)) if f.exists() else dict(seg))
        md = f"# {out.name}\n\n{table(rows)}\n"
        (out / 'summary.md').write_text(md)
        old = json.loads((out / 'summary.json').read_text()) if (out / 'summary.json').exists() else {}
        (out / 'summary.json').write_text(json.dumps(dict(meta=old.get('meta', {}), rows=rows), indent=1, default=str))
        print(md)
        return

    ram = free_ram_gb()
    if ram < 4.0:
        sys.exit(f'only {ram:.1f} GB RAM free: not starting a game process next to the shared editor')
    stamp = datetime.now().strftime('%m%d_%H%M%S')
    out = ROOT / f'Saved/Perf/runs/{stamp}_{a.plan}_{a.tag}'
    (out / 'csv').mkdir(parents=True, exist_ok=True)
    gus_backup = out / 'GameUserSettings.ini.bak'
    if GUS.exists():
        shutil.copy2(GUS, gus_backup)
    hashes = {str(p): digest(p) for p in SAVES}
    for p in SAVES:  # the front-end boot rewrites Settings.sav (bSeenIntro): put the player's files back afterwards
        if p.exists():
            shutil.copy2(p, out / (p.name + '.bak'))
    rx, ry = a.res.split('x')
    if not a.no_mirror:
        t_m = time.time()
        mirror()
        print(f'perf: mirrored P:/FoA -> {MIRROR} in {time.time() - t_m:.0f} s', flush=True)
    for p in (GUS.parent, SAVES[0].parent):
        p.mkdir(parents=True, exist_ok=True)
    args = [EXE, str(MIRROR / 'FoA.uproject'), '-game', '-windowed', f'-ResX={rx}', f'-ResY={ry}', '-nosound',
            '-unattended', '-nosplash', '-NoVerifyGC', f'-abslog={out / "game.log"}',
            '-ini:Engine:[/Script/PythonScriptPlugin.PythonScriptPluginSettings]:bRemoteExecution=False',
            '-ModelContextProtocolPort=18799',  # never the editor's MCP port 8000, even if the editor is closed
            f'-ExecCmds=py {DRIVER.as_posix()}']
    if not a.window:
        args.append('-RenderOffScreen')
    args += [f'-ini:{x}' for x in a.ini]
    env = dict(os.environ, FOA_PERF_OUT=str(out), FOA_PERF_PLAN=a.plan, FOA_PERF_PRESETS=a.presets,
               FOA_PERF_SAMPLE=a.sample, FOA_PERF_CVARS=a.cvars, FOA_PERF_GPUDUMP=a.gpudump,
               FOA_PERF_CAP=str(a.timeout - 20), FOA_PERF_BURST=a.burst,
               FOA_PERF_VARIANTS=Path(a.variants).read_text() if a.variants.endswith('.json') else a.variants)
    meta = dict(args=args, start=time.time(), ram_free_gb=round(ram, 1), gpu_util_before=gpu_util(), tag=a.tag,
                cvars=a.cvars, ini=a.ini, variants=a.variants)
    t_start = time.time()
    proc = subprocess.Popen(args, env=env)
    (out / 'pid.txt').write_text(str(proc.pid))
    print(f'perf: started pid {proc.pid} -> {out}', flush=True)
    checked = False
    try:
        while time.time() - t_start < a.timeout:
            if proc.poll() is not None:
                break
            if not checked and (out / 'manifest.json').exists():
                nodes = foa_nodes()
                meta['remote_exec_nodes'] = len(nodes)
                meta['others_gpu_start'] = others_gpu({proc.pid})
                checked = True
                if len(nodes) > 1:
                    print('perf: the game answers remote execution: killing it', flush=True)
                    kill_tree(proc.pid)
                    break
            if (out / 'done.json').exists():
                meta['others_gpu_end'] = others_gpu({proc.pid})
                try:
                    proc.wait(30)
                except subprocess.TimeoutExpired:
                    pass
                break
            time.sleep(1)
    finally:
        if proc.poll() is None:
            kill_tree(proc.pid)
            meta['killed'] = True
        meta['exit'] = proc.poll()
        meta['seconds'] = round(time.time() - t_start, 1)
        if gus_backup.exists():
            shutil.copy2(gus_backup, GUS)
        meta['saves_restored'] = []
        for p in SAVES:
            if digest(p) != hashes[str(p)] and (out / (p.name + '.bak')).exists():
                shutil.copy2(out / (p.name + '.bak'), p)
                meta['saves_restored'].append(p.name)
            elif hashes[str(p)] is None and p.exists():  # created by this run: remove, so every run starts alike
                p.unlink()
                meta['saves_restored'].append(p.name + ' (removed)')
        meta['saves_unchanged'] = all(digest(Path(p)) == h for p, h in hashes.items())
        if not meta['saves_unchanged']:
            print('perf: WARNING a player save differs after the run and could not be restored', hashes, flush=True)

    man = json.loads((out / 'manifest.json').read_text()) if (out / 'manifest.json').exists() else dict(segments=[])
    time.sleep(1.0)
    files = sorted(f for f in CSV_DIR.glob('*.csv') if f.stat().st_mtime >= t_start - 1) if CSV_DIR.exists() else []
    rows = []
    for seg, f in zip(man['segments'], match_csvs(man['segments'], files)):
        row = dict(seg)
        if f:
            dest = out / 'csv' / f"{seg['moment']}_q{seg['preset']}.csv"
            shutil.move(str(f), dest)
            row['csv'] = str(dest)
            row['stats'] = summarize_csv(dest)
        rows.append(row)
    meta['misses'] = [r for r in man.get('log', []) if r['kind'] in ('miss', 'error')]
    meta['done'] = [r for r in man.get('log', []) if r['kind'] == 'done']
    (out / 'summary.json').write_text(json.dumps(dict(meta=meta, rows=rows), indent=1, default=str))
    md = f"# {a.plan} {a.tag} ({stamp}, {a.res}, cvars '{a.cvars}', ini {a.ini})\n\n{table(rows)}\n\nmisses: {meta['misses']}\n"
    (out / 'summary.md').write_text(md)
    print(md)
    busy = max(meta.get('others_gpu_start', 0), meta.get('others_gpu_end', 0))
    if busy > 10:
        print(f'perf: WARNING other processes used {busy}% of the GPU during the run: timings are inflated, not clean', flush=True)
    print(json.dumps({k: meta[k] for k in ('exit', 'seconds', 'saves_unchanged', 'saves_restored', 'done', 'remote_exec_nodes',
                                          'others_gpu_start', 'others_gpu_end')
                      if k in meta}, default=str))


if __name__ == '__main__':
    main()
