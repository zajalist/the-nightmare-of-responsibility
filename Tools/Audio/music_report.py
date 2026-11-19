"""Read a level-1 music PIE recording by section: python -I Tools/Audio/music_report.py <run>
Sections come from <run>_timeline.json (pie_music.py): title (menu loop) from the first music=Menu to Wake up, the
wake-out (Wake up + 4 s), the bedroom (to the sting), the battle intro (sting to intro_end), the fight (intro_end to
EncounterWon), the victory fade (EncounterWon + 4 s). Prints the fade events in recording seconds, each section's
integrated loudness and peak, and which MUS_ sounds the sampler saw in it."""
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
rec0 = float(open(f'{H}{run}_recstart.txt').read().strip())
x, sr = sf.read(f'P:/FoA/Saved/BouncedWavFiles/HorrorShots/{run}_mix.wav', always_2d=True)
meter = pyln.Meter(sr)
dur = len(x) / sr


def at(pred):
    e = next((e for e in tl if pred(e)), None)
    return None if e is None else e['epoch'] - rec0


ev = {'menu': at(lambda e: e['kind'] == 'music' and e['state'] == 'Menu'),
      'wake': at(lambda e: e['kind'] == 'step' and e['what'] == 'ke * WakeUp'),
      'menu_off': at(lambda e: e['kind'] == 'music' and e['state'] == 'None' and e['t'] > 1),
      'sting': at(lambda e: e['kind'] == 'sting'),
      'intro_end': at(lambda e: e['kind'] == 'intro_end' and e['t'] > 1),
      'battle': at(lambda e: e['kind'] == 'music' and e['state'] == 'Battle'),
      'won': at(lambda e: e['kind'] == 'step' and e['what'] == 'ke * ReportEvent EncounterWon')}
ev['battle_off'] = at(lambda e: e['kind'] == 'music' and e['state'] == 'None' and ev['battle'] is not None
                      and e['epoch'] - rec0 > ev['battle'])
print('events (s into the recording):', {k: (round(v, 2) if v is not None else None) for k, v in ev.items()})
print('fades: menu in 3.0 s at', ev['menu'], '| menu out 2.5 s at', ev['menu_off'], '| sting at', ev['sting'],
      '| sting out 1.0 s at', ev['intro_end'], '| battle in 3.0 s at', ev['battle'], '| battle out 2.5 s at', ev['battle_off'])


def section(name, a, b):
    if a is None or b is None:
        print(f'{name:12s} (missing)')
        return
    a, b = max(0.0, a), min(dur, b)
    seg = x[int(a * sr):int(b * sr)]
    lufs = meter.integrated_loudness(seg) if len(seg) > 0.5 * sr else float('nan')
    seen = set()
    for line in open(f'{H}{run}_audio.jsonl'):
        d = json.loads(line)
        if a <= d['epoch'] - rec0 <= b:
            seen |= {s.split('@')[0] for s in d['sounds'] if 'MUS_' in s}
    print(f'{name:12s} {a:6.1f}-{b:6.1f} s  {lufs:6.1f} LUFS  peak {20 * np.log10(np.abs(seg).max() + 1e-12):6.1f} dBFS  music {sorted(seen)}')


section('title', ev['menu'], ev['wake'])
section('wake-out', ev['wake'], (ev['wake'] or 0) + 4)
section('bedroom', (ev['wake'] or 0) + 4, ev['sting'])
section('intro', ev['sting'], ev['intro_end'])
section('fight', ev['intro_end'], ev['won'])
section('victory', ev['won'], (ev['won'] or 0) + 4)

# every MusicState section (the beats pass): from one change to the next, its loudness and the MUS_ sounds seen
chg = [(e['epoch'] - rec0, e['state'], e['beat']) for e in tl if e['kind'] == 'music'] + [(dur, 'end', None)]
print('\nby MusicState (crossfade: out 2.5 s / in 3 s from each change):')
for (a, st, beat), (b, _, _) in zip(chg, chg[1:]):
    section(f'{st} (beat {beat})', a, b)
