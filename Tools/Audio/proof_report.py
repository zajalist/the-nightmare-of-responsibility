"""Per-beat numbers for a sound-on PIE proof (record_audio.sh): integrated loudness (LUFS) and true peak of the recorded
main-submix WAV, the most simultaneous voices, and how many times each cue was triggered (new instance ids).
  python Tools/Audio/proof_report.py <name>   ->  Saved/HorrorShots/<name>_report.txt
Inputs: Saved/HorrorShots/<name>_timeline.json (beats, rec_start), <name>_audio.jsonl (sampler), <name>_mix.wav."""
import collections
import json
import re
import subprocess
import sys

name = sys.argv[1]
D = 'P:/FoA/Saved/HorrorShots'
log = json.load(open(f'{D}/{name}_timeline.json'))
import os  # noqa: E402
rec0 = (float(open(f'{D}/{name}_recstart.txt').read()) if os.path.exists(f'{D}/{name}_recstart.txt')
        else next(e['epoch'] for e in log if e['kind'] == 'rec_start'))  # when audio_recording_start returned
end = next((e['epoch'] for e in log if e['kind'] in ('rec_stop', 'end', 'pie_gone')), log[-1]['epoch'])
beats = [('wake', rec0)] + [(e['beat'], e['epoch']) for e in log if e['kind'] == 'beat' and e['epoch'] > rec0]
spans = [(b, t, beats[i + 1][1] if i + 1 < len(beats) else end) for i, (b, t) in enumerate(beats)]
S = [json.loads(line) for line in open(f'{D}/{name}_audio.jsonl') if line.strip()]
import os  # noqa: E402
wav = next((w for w in (f'{D}/{name}_mix.wav', f'P:/FoA/Saved/BouncedWavFiles/{name}_mix.wav',
                        f'P:/FoA/Saved/BouncedWavFiles/HorrorShots/{name}_mix.wav') if os.path.exists(w)), f'{D}/{name}_mix.wav')


def loud(t0, t1):
    if t1 - t0 < 0.5:
        return None, None
    r = subprocess.run(['ffmpeg', '-hide_banner', '-nostats', '-ss', f'{t0 - rec0:.2f}', '-t', f'{t1 - t0:.2f}', '-i', wav,
                        '-af', 'ebur128=peak=true', '-f', 'null', '-'], capture_output=True, text=True)
    i = re.findall(r'I:\s+(-?[\d.]+|-inf) LUFS', r.stderr)
    p = re.findall(r'Peak:\s+(-?[\d.]+|-inf) dBFS', r.stderr)
    return (i[-1] if i else None), (p[-1] if p else None)


seen = set()
lines = [f'Sound-on proof {name}: PIE-world main output recorded by Hayba audio_recording_start/stop to {wav}', '',
         f'{"beat":6} {"secs":>5} {"LUFS":>7} {"TP dBFS":>8} {"audible":>7}  triggers (new instances in this beat)']
for b, t0, t1 in spans:
    ss = [s for s in S if t0 <= s['epoch'] < t1]
    voices = max((sum(1 for x in s['sounds'] if not x.endswith('!')) for s in ss), default=0)  # audible: playing, not paused
    trig = collections.Counter()
    for s in ss:
        for x in s['sounds']:
            snd, _, inst = x.rstrip('!').partition('#')
            key = (snd.split('@')[0], inst)
            if key not in seen:
                seen.add(key)
                trig[key[0]] += 1
    lufs, tp = loud(t0, t1)
    lines.append(f'{b:6} {t1 - t0:5.1f} {lufs or "-":>7} {tp or "-":>8} {voices:7d}  '
                 + ', '.join(f'{k} x{v}' for k, v in sorted(trig.items())))
whole = loud(rec0, end)
lines += ['', f'whole walk: {whole[0]} LUFS integrated, true peak {whole[1]} dBFS, '
          f'max audible sounds {max(sum(1 for x in s["sounds"] if not x.endswith("!")) for s in S)}']
open(f'{D}/{name}_report.txt', 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
print('\n'.join(lines))
