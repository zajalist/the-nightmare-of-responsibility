"""Read a key-snap PIE recording at the snap: python -I Tools/Audio/snap_report.py <run>
Uses Saved/HorrorShots/<run>_timeline.json (the epoch the door reached KeyJammed), <run>_recstart.txt (recording start
epoch), <run>_audio.jsonl (active sounds) and Saved/BouncedWavFiles/HorrorShots/<run>_mix.wav. Prints the whole-file
loudness, the peak and the 400 ms momentary loudness at the snap against the second before it, and whether
S_Door_KeySnap was among the active sounds."""
import json
import site
import sys

sys.path.append(site.getusersitepackages())  # -I drops user site (trusted libs)
import numpy as np  # noqa: E402
import pyloudnorm as pyln  # noqa: E402
import soundfile as sf  # noqa: E402

run = sys.argv[1]
H = 'P:/FoA/Saved/HorrorShots/'
tl = json.load(open(f'{H}{run}_timeline.json'))
snap = next((e['epoch'] for e in tl if e['kind'] == 'state' and e['state'] == 'KeyJammed'), None)
rec0 = float(open(f'{H}{run}_recstart.txt').read().strip())
x, sr = sf.read(f'P:/FoA/Saved/BouncedWavFiles/HorrorShots/{run}_mix.wav', always_2d=True)
meter = pyln.Meter(sr)
print('events', [(e['t'], e['kind'], e.get('state', e.get('reason', ''))) for e in tl])
print(f'whole file {len(x) / sr:.1f} s, {meter.integrated_loudness(x):.1f} LUFS, peak {20 * np.log10(np.abs(x).max()):.1f} dBFS')
if snap is None:
    sys.exit('no KeyJammed in the timeline')
at = snap - rec0
i = int(at * sr)


def window(a, b):
    return x[max(0, int(a * sr)):max(0, int(b * sr))]


def mom(seg):  # momentary loudness of a 400 ms block
    return meter.integrated_loudness(seg) if len(seg) >= int(0.4 * sr) else float('nan')


# the commit and the sound can land a frame or two apart: search 0.5 s around the logged epoch for the peak
w = window(at - 0.25, at + 0.5)
k = int(np.argmax(np.abs(w).max(1)))
pk_t = at - 0.25 + k / sr
print(f'snap logged at {at:.3f} s into the recording; loudest sample within -0.25..+0.5 s at {pk_t:.3f} s: '
      f'{20 * np.log10(np.abs(w).max()):.1f} dBFS')
print(f'momentary (400 ms) at the snap {mom(window(pk_t - 0.05, pk_t + 0.35)):.1f} LUFS; '
      f'the second before it {meter.integrated_loudness(window(pk_t - 1.2, pk_t - 0.2)):.1f} LUFS; '
      f'peak in the second before {20 * np.log10(np.abs(window(pk_t - 1.2, pk_t - 0.2)).max()):.1f} dBFS')
seen = []
for line in open(f'{H}{run}_audio.jsonl'):
    d = json.loads(line)
    hits = [s for s in d['sounds'] if 'KeySnap' in s]
    if hits:
        seen.append((round(d['epoch'] - snap, 2), hits))
print('S_Door_KeySnap in the active sounds (s after the snap, instances):', seen or 'never')
