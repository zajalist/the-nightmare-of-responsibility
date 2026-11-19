"""Build the tactile UI set (menu, HUD, phone) from recorded foley only: no synthesis, no Kenney interface-sounds.
  python -I Tools/Audio/make_ui_tactile.py
Each sound is one recording, cut (onset-aligned for clicks and taps), mono-mixed, high-passed at 60-80 Hz against room
rumble, low-passed at 7 kHz so nothing is bright, resampled to 44.1 kHz, faded and peak-set to -10..-6 dBFS.
Writes 16-bit mono WAVs to P:/FoA-Assets/audio/SFX/UI_Tactile/ and a contact sheet to
P:/FoA/Saved/HorrorShots/audio/ui_tactile_sheet.png.
Self-check: every duration inside its window, peaks inside -10..-6 dBFS with Hover the quietest and Confirm the loudest,
and spectral flatness (100 Hz-6 kHz, energy-weighted) below 0.30: white noise reads about 0.56 and the noise-glitch
stinger it replaced read 0.41."""
import os
import site
import sys

sys.path.append(site.getusersitepackages())  # -I drops user site; numpy/scipy/soundfile/matplotlib live there (trusted)
import numpy as np  # noqa: E402
import soundfile as sf  # noqa: E402
from scipy.signal import butter, resample_poly, sosfiltfilt  # noqa: E402

SR = 44100
A = 'P:/FoA-Assets/audio'
L = A + '/_libraries'
SB = L + '/sonniss'
OUT = A + '/SFX/UI_Tactile'
PNG = 'P:/FoA/Saved/HorrorShots/audio/ui_tactile_sheet.png'
RPG = L + '/kenney/rpg-audio/Audio'
CUP = SB + '/Sonniss.com_-_GDC_-_Game_Audio_Bundle_1of5/Coll Anderson - House/EFX INT HOUSE Kitchen Cupbord O_C Close Medium 01.wav'
WAR = (SB + '/Sonniss.com_-_GDC_2020_-_Game_Audio_Bundle_Part12of14/SoundFxwizard - Closets Small Doors'
       '/CST_Wardrobe_Door_Closure_Action_Multiple_SFXWiz.wav')
PAGE = SB + '/Sonniss.com-GDC2024-GameAudioBundle2of9/Mechanical Wave - Cardboard and Paper/PAPRHndl_Large Book Squeak Page Turn_ 01_MWSFX_CDAP.wav'
CLK = SB + '/Sonniss.com-GDC2026-GameAudioBundle1of5/344 Audio - Antique Clocks/CLOCKTick_Crooked Antique Clock_344 Audio_Antique Clocks.wav'
PHONE = SB + '/Sonniss.com-GDC2023-GameAudioBundle2of14/Joshua Reinhardt - The Ultimate Phone Bundle/Smartphone_Swipe_Short.wav'

# name: (source, t0 s, length s, (min, max) length s, peak dBFS, high-pass Hz, onset search (dB below peak) or None,
#        fade-in s, fade-out s)
SPEC = {
    'Hover_A': (RPG + '/cloth3.ogg', 0.02, 0.12, (0.06, 0.15), -10.0, 60, None, 0.015, 0.05),
    'Confirm_A': (WAR, 1.95, 0.16, (0.08, 0.20), -6.0, 70, -20, 0.002, 0.06),
    'Back_A': (CUP, 2.46, 0.15, (0.08, 0.20), -8.0, 80, -20, 0.002, 0.06),
    'Open_A': (RPG + '/bookOpen.ogg', 0.0, 0.153, (0.15, 0.40), -8.0, 60, None, 0.003, 0.03),
    'Close_A': (RPG + '/bookClose.ogg', 0.0, 0.230, (0.15, 0.40), -8.0, 60, None, 0.003, 0.05),
    'PhoneTap_A': (PHONE, 18.14, 0.055, (0.03, 0.08), -9.0, 80, -10, 0.002, 0.02),
    'PhoneBuzz_A': (A + '/SFX/Phone/SFX_Phone_Buzz_01.wav', 0.0, 0.58, (0.4, 0.6), -9.5, 60, None, 0.005, 0.05),
    'PageTurn_A': (PAGE, 1.85, 0.35, (0.15, 0.40), -9.0, 60, None, 0.01, 0.08),
    'SliderTick_A': (CLK, 4.05, 0.03, (0.015, 0.04), -9.0, 80, -20, 0.001, 0.012),
    'PauseIn_A': (RPG + '/dropLeather.ogg', 0.0, 0.40, (0.2, 0.5), -7.0, 60, None, 0.005, 0.08),
    'PauseOut_A': (RPG + '/cloth2.ogg', 0.0, 0.40, (0.2, 0.5), -9.5, 60, None, 0.005, 0.10),
}


def cut(path, t0, dur, hp, onset_db):
    """Mono slice (with 50 ms filter margin) band-limited hp..7 kHz, at 44.1 kHz; onset-aligned when onset_db is set."""
    x, sr = sf.read(path, always_2d=True, dtype='float64')
    a, b = max(int((t0 - 0.05) * sr), 0), min(int((t0 + dur + 0.25) * sr), len(x))
    m = sosfiltfilt(butter(2, hp, 'highpass', fs=sr, output='sos'), x[a:b].mean(axis=1))
    m = sosfiltfilt(butter(4, 7000, 'lowpass', fs=sr, output='sos'), m)
    g = np.gcd(SR, sr)
    m = resample_poly(m, SR // g, sr // g)
    i = int((t0 - a / sr) * SR)
    if onset_db is not None:  # first 3 ms RMS within onset_db of the slice's loudest, minus 2 ms
        w = int(0.003 * SR)
        e = np.sqrt(np.convolve(m[i:i + int((dur + 0.1) * SR)] ** 2, np.ones(w) / w, mode='same'))
        i += max(int(np.argmax(e > e.max() * 10 ** (onset_db / 20))) - int(0.002 * SR), 0)
    y = m[i:i + int(round(dur * SR))]
    assert len(y) == int(round(dur * SR)), f'{path} too short for {dur} s from {t0} s'
    return y, a / sr + i / SR  # second value: the cut's start time in the source file


def fade(y, fin, fout):
    y = y.copy()
    n = max(int(fin * SR), 1)
    y[:n] *= np.linspace(0, 1, n)
    n = int(fout * SR)
    y[-n:] *= np.linspace(1, 0, n) ** 2
    return y


def flatness(y):
    """Energy-weighted spectral flatness of 1024-pt frames within 40 dB of the loudest, 100 Hz-6 kHz."""
    n = 1024
    y = np.pad(y, (0, max(0, n - len(y))))
    f = np.fft.rfftfreq(n, 1 / SR)
    band = (f >= 100) & (f <= 6000)
    fr = np.lib.stride_tricks.sliding_window_view(y, n)[::256] * np.hanning(n)
    P = np.abs(np.fft.rfft(fr, axis=1)) ** 2
    P = P[:, band] + 1e-20
    e = P.sum(axis=1)
    keep = e > e.max() * 1e-4
    fl = np.exp(np.log(P[keep]).mean(axis=1)) / P[keep].mean(axis=1)
    return float((fl * e[keep]).sum() / e[keep].sum())


def render(out):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig = plt.figure(figsize=(16, 13))
    grid = fig.add_gridspec(4, 3, hspace=0.45, wspace=0.25)
    for k, (name, y, st) in enumerate(out):
        cell = grid[k // 3, k % 3].subgridspec(2, 1, height_ratios=[1, 2], hspace=0.05)
        a = fig.add_subplot(cell[0])
        t = np.arange(len(y)) / SR * 1000
        a.plot(t, y, lw=0.6, color='k')
        a.set_xlim(0, max(len(y) / SR * 1000, 40))
        a.set_ylim(-0.5, 0.5)
        a.set_xticks([])
        a.set_title(f'SFX_UI_{name}\n{st["dur"] * 1000:.0f} ms, peak {st["peak"]:.1f} dBFS, flatness {st["flat"]:.3f}',
                    fontsize=9)
        a = fig.add_subplot(cell[1])
        nfft = 256 if len(y) < 4096 else 512
        a.specgram(y, NFFT=nfft, Fs=SR, noverlap=nfft * 7 // 8, cmap='magma', vmin=-140, vmax=-40,
                   xextent=(0, len(y) / SR * 1000))
        a.set_xlim(0, max(len(y) / SR * 1000, 40))
        a.set_ylim(0, 12000)
        a.set_xlabel('ms', fontsize=8)
        a.tick_params(labelsize=7)
    os.makedirs(os.path.dirname(PNG), exist_ok=True)
    fig.savefig(PNG, dpi=100, bbox_inches='tight')


def main():
    os.makedirs(OUT, exist_ok=True)
    out, stats = [], {}
    for name, (path, t0, dur, (lo, hi), peak, hp, onset_db, fin, fout) in SPEC.items():
        y, start = cut(path, t0, dur, hp, onset_db)
        y = fade(y, fin, fout)
        y *= 10 ** (peak / 20) / np.abs(y).max()
        y = np.round(y * 32767) / 32767  # judge the 16-bit result
        st = dict(dur=len(y) / SR, peak=20 * np.log10(np.abs(y).max()), rms=20 * np.log10(np.sqrt((y ** 2).mean())),
                  flat=flatness(y), start=start)
        print(f'SFX_UI_{name:13s} {st["dur"] * 1000:5.0f} ms  peak {st["peak"]:6.1f} dBFS  RMS {st["rms"]:6.1f} dBFS  flatness {st["flat"]:.3f}  '
              f'from {os.path.basename(path)} @ {start:.3f}-{start + dur:.3f} s')
        assert lo - 1e-9 <= st['dur'] <= hi + 1e-9, (name, 'duration outside its window')
        assert -10.05 <= st['peak'] <= -5.95, (name, 'peak outside -10..-6 dBFS')
        assert st['flat'] < 0.30, (name, 'too noise-like')
        stats[name] = st
        out.append((name, y, st))
    peaks = {k: v['peak'] for k, v in stats.items()}
    assert min(peaks, key=peaks.get) == 'Hover_A' and max(peaks, key=peaks.get) == 'Confirm_A', peaks
    for name, y, _ in out:
        sf.write(f'{OUT}/SFX_UI_{name}.wav', y, SR, subtype='PCM_16')
    render(out)
    print('wrote', len(out), 'files to', OUT, 'and', PNG)


main()
