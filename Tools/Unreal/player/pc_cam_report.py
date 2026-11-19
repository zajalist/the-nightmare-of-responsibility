"""playercam lane: first-person camera motion metrics and before/after plots from pie_play.py's PCM plan (pc_cam.csv).
  python Tools/Unreal/player/pc_cam_report.py <before_plan_dir> [<after_plan_dir>] [--out P:/FoA/Saved/QA/lanes/playercam/x.png]
Per phase: standing sway (peak to peak, cm and deg), walking bob (detrended by a 1 s centred mean; amplitude = half the
peak to peak), per-tick jolt (largest one-tick change of the detrended offset, ticks next to a screenshot excluded),
stop settle time (last moment any axis is more than 0.2 cm from where it comes to rest), turn roll, and the view's
yaw from the animated torso. Offline only (reads CSVs)."""
import csv
import json
import os
import sys

import numpy as np


def load(plan_dir):
    rows = list(csv.DictReader(open(os.path.join(plan_dir, 'pc_cam.csv'), encoding='utf-8')))
    for r in rows:
        for k, v in r.items():
            try:
                r[k] = float(v)
            except (TypeError, ValueError):
                pass
    return rows


def wrap(a):
    return (np.asarray(a) + 180.0) % 360.0 - 180.0


def detrend(t, v, win=1.0):
    t, v = np.asarray(t), np.asarray(v)
    return np.array([v[i] - v[np.abs(t - t[i]) <= win / 2].mean() for i in range(len(v))])


def phase_metrics(rows, name):
    ph = [r for r in rows if r['phase'] == name]
    if len(ph) < 3:
        return None
    t = np.array([r['t'] for r in ph]) - ph[0]['t']
    col = {k: np.array([r[k] for r in ph]) for k in ('fwd', 'right', 'up', 'croll', 'view_torso', 'speed')}
    col['dpitch'] = wrap([r['cpitch'] - r['kpitch'] for r in ph])
    col['dyaw'] = wrap([r['cyaw'] - r['kyaw'] for r in ph])
    clean = np.array([r['near_shot'] == 0 for r in ph])
    m = dict(ticks=len(ph), dt_ms=round(float(np.median([r['dt'] for r in ph])), 1), speed_max=round(float(col['speed'].max())),
             roll_max_deg=round(float(np.abs(col['croll']).max()), 3), view_torso_max_deg=round(float(np.abs(col['view_torso']).max()), 1),
             cam_vs_control_deg=round(float(max(np.abs(col['dpitch']).max(), np.abs(col['dyaw']).max())), 3))
    if name.startswith(('idle', 'stop', 'turnstop', 'flickstop')):
        keep = t >= (0.0 if name.startswith('idle') else 0.6)  # after a stop: the rest, once settled
        for k in ('fwd', 'right', 'up'):
            m[f'{k}_p2p_cm'] = round(float(np.ptp(col[k][keep])), 2)
        m['rot_p2p_deg'] = round(float(max(np.ptp(col['dpitch'][keep]), np.ptp(col['dyaw'][keep]))), 3)
    if name.startswith('stop') or name in ('turnstop', 'flickstop'):
        rest = {k: col[k][t >= t[-1] - 0.3].mean() for k in ('fwd', 'right', 'up')}
        off = np.max(np.abs(np.stack([col[k] - rest[k] for k in rest])), axis=0)
        late = np.where(off > 0.2)[0]
        m['settle_s'] = round(float(t[late[-1]]) if len(late) else 0.0, 2)
        steps = np.max(np.abs(np.diff(np.stack([col[k] for k in rest]), axis=1)), axis=0)
        m['max_tick_step_cm'] = round(float(steps[clean[1:]].max()) if clean[1:].any() else float('nan'), 2)
    if 'cz' in ph[0] and 'ex' in ph[0]:  # newer runs: world height and the true eye (head landmark) in the capsule frame
        col['cz'] = np.array([r['cz'] for r in ph])
        m['eye_dev_max_cm'] = round(float(max(np.hypot(r['fwd'] - r['ex'], r['right'] - r['ey']) for r in ph)), 1)
    if name in ('walk', 'strafe', 'walkturn', 'walkdown'):
        keep = t >= 0.6  # past the first steps
        if 'cz' in col:
            d = detrend(t, col['cz'])[keep]
            m['world_z_bob_amp_cm'] = round(float(np.ptp(d)) / 2, 2)
            dd = np.abs(np.diff(d))
            m['world_z_jolt_cm'] = round(float(dd[clean[keep][1:]].max()), 2)
        for k in ('fwd', 'right', 'up'):
            d = detrend(t, col[k])[keep]
            m[f'{k}_bob_amp_cm'] = round(float(np.ptp(d)) / 2, 2)
            dd = np.abs(np.diff(d))
            ok = clean[keep][1:]
            m[f'{k}_jolt_cm'] = round(float(dd[ok].max()) if ok.any() else float('nan'), 2)
    return m


PHASES = ('idle', 'walk', 'stop', 'strafe', 'stop2', 'turn', 'turnstop', 'flick', 'flickstop', 'walkturn', 'stop3', 'walkdown', 'stopdown')


def metrics(rows):
    return {p: phase_metrics(rows, p) for p in PHASES if phase_metrics(rows, p)}


def plot(runs, out):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(5, 1, figsize=(14, 13), sharex=True)
    keys = (('up', 'eye height above the capsule (cm)'), ('right', 'eye right of the capsule (cm)'),
            ('fwd', 'eye ahead of the capsule (cm)'), ('croll', 'camera roll (deg)'), ('view_torso', 'view yaw from the torso (deg)'))
    colors = {'before': '#c0392b', 'after': '#1e8449'}
    for label, rows in runs:
        t0 = rows[0]['t']
        t = np.array([r['t'] - t0 for r in rows])
        for ax, (k, title) in zip(axes, keys):
            ax.plot(t, [r[k] for r in rows], color=colors.get(label, 'k'), lw=1.2, label=label)
            ax.set_ylabel(title, fontsize=8)
    rows = runs[0][1]
    t0 = rows[0]['t']
    spans, cur = [], None
    for r in rows:
        if cur is None or r['phase'] != cur[0]:
            cur = [r['phase'], r['t'] - t0, r['t'] - t0]
            spans.append(cur)
        cur[2] = r['t'] - t0
    for i, (name, a, b) in enumerate(spans):
        for ax in axes:
            if i % 2:
                ax.axvspan(a, b, color='#888', alpha=0.08)
        axes[0].text((a + b) / 2, 1.02, name, transform=axes[0].get_xaxis_transform(), ha='center', fontsize=8)
    axes[0].legend(loc='lower right', fontsize=8)
    axes[-1].set_xlabel('seconds into the probe (phases from the first run)')
    fig.suptitle('First-person camera, per tick: PCM probe', y=0.995)
    fig.tight_layout()
    fig.savefig(out, dpi=110)
    print('plot', out)


if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    out = sys.argv[sys.argv.index('--out') + 1] if '--out' in sys.argv else None
    if out in args:
        args.remove(out)
    runs = [('before', load(args[0]))] + ([('after', load(args[1]))] if len(args) > 1 else [])
    print(json.dumps({label: metrics(rows) for label, rows in runs}, indent=1))
    if out:
        plot(runs, out)
