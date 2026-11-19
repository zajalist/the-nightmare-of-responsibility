"""atmosphere lane: the Level 2 drive's engine bed from BigSoundBank #3098 "Car interior, 80 km/h" (CC0).
  python -I Tools/Audio/make_car_loop.py
Takes the steady 80 km/h cruise (17.0-31.0 s of the recording; the start, a gear change near 9 s, the slow-down from 66 s
and the stop are left out), wraps it with a 2 s equal-power crossfade of what follows the end into the head, cleans the
rumble below 30 Hz and the hiss above 8 kHz, and sets it to -20 LUFS (-1 dBTP), the level of the other ambience sources.
Writes P:/FoA-Assets/audio/SFX/Drive/SFX_Drive_CarInterior_Loop_01.wav (48 kHz, 16-bit, stereo) and checks the seam:
the spectral change across the wrap must be no larger than the 95th percentile of the loop's own frame-to-frame change."""
import os
import site
import sys

sys.path.append(site.getusersitepackages())  # -I drops user site; numpy/scipy/soundfile/pyloudnorm live there (trusted)
import numpy as np  # noqa: E402
import pyloudnorm as pyln  # noqa: E402
import soundfile as sf  # noqa: E402
from scipy.signal import butter, resample_poly, sosfiltfilt  # noqa: E402

SRC = 'P:/FoA-Assets/audio/_libraries/bigsoundbank/s3098_car-interior-80kmh/s3098_car-interior-80kmh.wav'
OUT = 'P:/FoA-Assets/audio/SFX/Drive/SFX_Drive_CarInterior_Loop_01.wav'
START, LOOP, FADE, LUFS = 17.0, 14.0, 2.0, -20.0


def spec(frames):
    return np.log10(np.abs(np.fft.rfft(frames * np.hanning(frames.shape[-1]), axis=-1)) + 1e-6)


def seam_ratio(y, sr):
    """Spectral change across the wrap over the 95th percentile of the change between neighbouring 50 ms frames."""
    m, n = y.mean(1), int(0.05 * sr)
    frames = np.stack([m[i:i + n] for i in range(0, len(m) - n, n)])
    d = np.abs(np.diff(spec(frames), axis=0)).mean(1)
    wrap = np.abs(spec(np.concatenate([m[-n // 2:], m[:n // 2]])) - spec(m[-n:])).mean()
    return wrap / np.percentile(d, 95)


def main():
    x, sr = sf.read(SRC, always_2d=True)
    a, l, f = int(START * sr), int(LOOP * sr), int(FADE * sr)
    seg = x[a:a + l + f].copy()
    t = np.linspace(0.0, np.pi / 2, f)[:, None]
    y = seg[:l].copy()
    y[:f] = seg[:f] * np.sin(t) + seg[l:l + f] * np.cos(t)  # what follows the end fades into the head: a seamless wrap
    sos = np.vstack([butter(2, 30, 'highpass', fs=sr, output='sos'), butter(2, 8000, 'lowpass', fs=sr, output='sos')])
    y = sosfiltfilt(sos, np.concatenate([y, y, y]), axis=0)[l:2 * l]  # filter circularly so the wrap stays seamless
    y *= 10 ** ((LUFS - pyln.Meter(sr).integrated_loudness(y)) / 20)
    peak = 20 * np.log10(np.abs(resample_poly(y, 4, 1, axis=0)).max())
    if peak > -1.0:
        y *= 10 ** ((-1.0 - peak) / 20)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    sf.write(OUT, y, sr, subtype='PCM_16')
    r = seam_ratio(y, sr)
    print(OUT, f'{len(y) / sr:.2f} s', f'{pyln.Meter(sr).integrated_loudness(y):.1f} LUFS', f'seam {r:.2f}')
    assert r <= 1.0, f'audible seam ({r:.2f})'


if __name__ == '__main__':
    main()
