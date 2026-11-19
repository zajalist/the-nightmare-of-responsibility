"""atmosphere lane: loudness over time of a recorded PIE mix (qa_mix_recorder.py output).
  python Tools/Audio/mix_meter.py <mix.wav> [<mix.wav> ...]
Per file: integrated loudness (LUFS), true-ish peak (dBFS, 4x oversampled), and a 1 s short-term loudness strip
(3 s window, EBU R128 K-weighting via pyloudnorm), so loud spikes and silent holes can be found by time."""
import sys

import numpy as np
import pyloudnorm as pyln
import soundfile as sf
from scipy.signal import resample_poly


def meter(path):
    x, sr = sf.read(path, always_2d=True)
    m = pyln.Meter(sr)
    integ = m.integrated_loudness(x) if len(x) > sr * 0.5 else float('-inf')
    peak = 20 * np.log10(max(np.abs(resample_poly(x, 4, 1, axis=0)).max(), 1e-9))
    strip = []
    for t in range(0, max(1, int(len(x) / sr) - 2)):
        seg = x[t * sr:(t + 3) * sr]
        strip.append(m.integrated_loudness(seg) if len(seg) >= sr else float('-inf'))
    return dict(seconds=round(len(x) / sr, 1), lufs=round(integ, 1), peak_dbfs=round(peak, 1),
                st=[round(v, 1) if np.isfinite(v) else None for v in strip])


def selftest():
    sr = 48000
    t = np.arange(sr * 6) / sr
    tone = 0.1 * np.sin(2 * np.pi * 1000 * t)  # -20 dBFS sine at 1 kHz reads about -23 LUFS in one channel
    path = 'P:/FoA/Saved/QA/atmosphere/_selftest_tone.wav'
    sf.write(path, np.stack([tone, tone], 1), sr)
    r = meter(path)
    assert -21.5 < r['lufs'] < -19.0, r  # stereo: two equal channels add 3 dB over one
    assert -20.5 < r['peak_dbfs'] < -19.5, r
    print('selftest ok', r['lufs'], r['peak_dbfs'])


if __name__ == '__main__':
    if sys.argv[1:] == ['--selftest']:
        selftest()
    for p in sys.argv[1:]:
        if p == '--selftest':
            continue
        r = meter(p)
        print(p.replace('\\', '/').split('/')[-1], 'len', r['seconds'], 's  integrated', r['lufs'], 'LUFS  peak', r['peak_dbfs'], 'dBFS')
        print('  short-term (3 s window, per second):', ' '.join('--' if v is None else f'{v:.0f}' for v in r['st']))
