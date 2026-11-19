"""Build the jumpscare's two new sounds from recorded library audio (no synthesis: only trims, gains, filters,
resampling, reversal-free layering and a crossfaded loop). Writes 44.1 kHz 16-bit stereo WAVs.
  python -I Tools/Audio/make_jumpscare_sfx.py <scratch_dir_with_decoded_wavs>
The scratch dir must hold sh1.wav (scream_horror1.mp3), fs.wav (screams.ogg) and ah.wav (ambient_horror.wav), decoded
by ffmpeg; the rest are read from P:/FoA-Assets/audio. Outputs:
  SFX/Horror/SFX_Horror_Stinger_01.wav       riser lead-in 0.40 s, then hit + boom + shriek + growl at HIT
  SFX/Horror/SFX_Horror_TensionBed_Loop_01.wav  pitched-down, low-passed room recording, seamless 24 s loop
Self-check at the end: peaks, the hit onset position and the loop seam."""
import os
import site
import sys

sys.path.append(site.getusersitepackages())  # -I drops user site; numpy/scipy/soundfile live there (trusted)
import numpy as np  # noqa: E402
import soundfile as sf  # noqa: E402
from scipy.signal import butter, resample_poly, sosfiltfilt  # noqa: E402

SR = 44100
HIT = 0.40  # seconds of lead-in before the hit: BP_Jumpscare reveals the monster this long after starting the file
A = 'P:/FoA-Assets/audio'
OUT = A + '/SFX/Horror'
scratch = sys.argv[1]


def load(path):
    x, sr = sf.read(path, always_2d=True, dtype='float64')
    if x.shape[1] == 1:
        x = np.repeat(x, 2, axis=1)
    if sr != SR:
        x = resample_poly(x, SR, sr, axis=0)
    return x


def cut(x, t0, t1):
    return x[int(t0 * SR):int(t1 * SR)]


def filt(x, kind, hz, order=4):
    return sosfiltfilt(butter(order, hz, kind, fs=SR, output='sos'), x, axis=0)


def fade(x, fin=0.005, fout=0.0):
    x = x.copy()
    n = int(fin * SR)
    if n:
        x[:n] *= np.linspace(0, 1, n)[:, None]
    n = int(fout * SR)
    if n:
        x[-n:] *= np.linspace(1, 0, n)[:, None] ** 2
    return x


def put(buf, x, at, gain_db):
    i = int(at * SR)
    n = min(len(x), len(buf) - i)
    buf[i:i + n] += x[:n] * 10 ** (gain_db / 20)


def onset(x, thresh_db=-20):
    """First sample whose 5 ms RMS reaches thresh_db below the file's 5 ms RMS peak."""
    w = int(0.005 * SR)
    e = np.sqrt(np.convolve((x ** 2).mean(axis=1), np.ones(w) / w, mode='same'))
    return int(np.argmax(e > e.max() * 10 ** (thresh_db / 20)))


def stinger():
    total = HIT + 2.9
    buf = np.zeros((int(total * SR), 2))
    # Designed horror scream (CC0): its own 0.4 s growl-to-scream crescendo is the riser, full scream lands on HIT
    scream = filt(cut(load(scratch + '/sh1.wav'), 0.90, 3.60), 'highpass', 120)
    t = np.arange(len(scream)) / SR
    scream *= (10 ** (np.where(t < HIT, -16 + 10 * t / HIT, 0) / 20))[:, None]  # keep the lead-in low so the hit punches
    put(buf, fade(scream, 0.02, 1.2), 0.0, -1.0)
    # Bright reversed-cymbal swell (Sonniss, already in the game) peaking exactly on HIT
    swell = cut(load(A + '/SFX/Dream/SFX_Dream_ReverseSwell_01.wav'), 5.65, 6.05)
    put(buf, fade(swell, 0.05), HIT - 0.40, -4.0)
    # Bright cinematic hit (Sonniss), aligned by its measured onset
    hit = load(A + '/SFX/Dream/SFX_Dream_LowImpact_02.wav')
    put(buf, fade(hit[onset(hit):], 0.001, 1.5)[:int(2.8 * SR)], HIT, -3.0)
    # Sub boom (Sonniss), onset at its start
    boom = load(A + '/SFX/Dream/SFX_Dream_LowImpact_03.wav')
    put(buf, fade(filt(boom[onset(boom):], 'lowpass', 900), 0.001, 1.5)[:int(2.8 * SR)], HIT, -1.0)
    # Real female scream (CC0), first take, high-passed so its room rumble drops out
    fs = load(scratch + '/fs.wav')
    take = filt(cut(fs, 0.05, 1.25), 'highpass', 350)
    put(buf, fade(take[onset(take):], 0.002, 0.4), HIT, -7.0)
    # Creature growl (CC0 voice), a fifth lower for body
    growl = load(A + '/_libraries/opengameart/horror_4543_monster-sfx-pack/monster_sfx_pack_x/monster_sfx_pack/monster-8.wav')
    growl = resample_poly(growl, 3, 2, axis=0)  # played at 44.1k: 2/3 speed, about 7 semitones down
    put(buf, fade(growl[onset(growl):], 0.002, 0.5), HIT, -6.0)
    y = np.tanh(buf * 1.4) / np.tanh(1.4)  # gentle glue so the layers share one transient
    y = fade(y, 0.0, 0.8) * (10 ** (-1 / 20) / np.abs(y).max())
    return y


def bed():
    # Room recording (CC0) an octave down and low-passed: a slow dark drone instead of its bright hiss
    x = load(scratch + '/ah.wav')
    x = resample_poly(x, 2, 1, axis=0)  # twice the samples at the same rate: half speed, one octave down
    x = filt(filt(x, 'lowpass', 1800), 'highpass', 35, 2)
    body, xf = cut(x, 2.0, 26.0), int(2.0 * SR)
    tail = cut(x, 26.0, 28.0)
    if len(tail) < xf:
        sys.exit('ambient_horror too short for the crossfade')
    k = np.sin(np.linspace(0, np.pi / 2, xf))[:, None]
    body[:xf] = body[:xf] * k + tail[:xf] * np.cos(np.linspace(0, np.pi / 2, xf))[:, None]  # equal-power seam
    rms = np.sqrt((body ** 2).mean())
    return body * (10 ** (-24 / 20) / rms)


def main():
    os.makedirs(OUT, exist_ok=True)
    s, b = stinger(), bed()
    assert np.abs(b).max() < 0.99, 'bed clips'
    sf.write(OUT + '/SFX_Horror_Stinger_01.wav', s, SR, subtype='PCM_16')
    sf.write(OUT + '/SFX_Horror_TensionBed_Loop_01.wav', b, SR, subtype='PCM_16')
    # self-check: the loudest 10 ms window sits at or just after HIT; the loop seam jump is small
    w = int(0.01 * SR)
    e = np.convolve((s ** 2).mean(axis=1), np.ones(w), mode='valid')
    peak_t = np.argmax(e) / SR
    seam = np.abs(b[0] - b[-1]).max()
    print(f'stinger {len(s) / SR:.2f}s peak {20 * np.log10(np.abs(s).max()):.1f} dBFS loudest at {peak_t:.3f}s (HIT {HIT})')
    print(f'bed {len(b) / SR:.2f}s peak {20 * np.log10(np.abs(b).max()):.1f} dBFS seam jump {seam:.4f}')
    assert HIT - 0.02 <= peak_t <= HIT + 0.6, 'stinger peak not on the hit'
    assert seam < 0.05, 'loop seam clicks'


main()
