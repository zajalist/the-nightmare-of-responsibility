"""Rebuild SFX_FE_GlitchStinger_02/_03 from recorded tape/VHS/cassette mechanics (no oscillators, no generated noise:
only trims, gains, filters, varispeed by time-varying resampling, layering and fades). 44.1 kHz 16-bit stereo WAVs.
  python -I Tools/Audio/make_glitch_stingers.py
Reads the before copies from _replaced/2026-11-09 (loudness targets + comparison), overwrites SFX/UI_FrontEnd/_02 and
_03, renders P:/FoA/Saved/HorrorShots/audio/glitchstinger_before_after.png.
Self-check: new spectral flatness clearly below the old file's, both in audit_synthetic.py's metric (the one that
flagged them; 50 Hz-16 kHz) and in 100 Hz-5 kHz only (so the low-pass alone can't pass it); audit score too; whole-file
RMS within 1 dB of the old file, peak no higher, length 0.5-1.1 s."""
import os
import site
import sys
import tempfile

sys.path.append(site.getusersitepackages())  # -I drops user site; numpy/scipy/soundfile/matplotlib live there (trusted)
import numpy as np  # noqa: E402
import soundfile as sf  # noqa: E402
from scipy.signal import butter, resample_poly, sosfiltfilt  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # -I drops the script dir; our own trusted tools
from audit_synthetic import metrics  # noqa: E402  the audit that flagged the old files as noise-like

SR = 44100
A = 'P:/FoA-Assets/audio'
SB = A + '/_libraries/sonniss'
VHS = SB + '/Sonniss.com_-_GDC_2020_-_Game_Audio_Bundle_Part11of14/Sonic Bat - The VHS & Betamax Sessions/SBtvbs_VHS Tape Rewind 001.wav'
BETA = SB + '/Sonniss.com_-_GDC_2020_-_Game_Audio_Bundle_Part11of14/Sonic Bat - The VHS & Betamax Sessions/SBtvbs_Betamax Tape Eject 004.wav'
CASS = (SB + '/Sonniss.com_-_GDC_2017_-_Game_Audio_Bundle_Part_8of9/Sonniss.com - GDC 2017 - Game Audio Bundle Part 8of9'
        '/Tone Manufacture - Cassette Tone/TM_CASSETTE TONE_Motor only, rewind, button perspective.wav')
OUT = A + '/SFX/UI_FrontEnd'
OLD = A + '/_replaced/2026-11-09'
PNG = 'P:/FoA/Saved/HorrorShots/audio/glitchstinger_before_after.png'


def src(path, t0, t1, lp=5000, hp=60):
    """Mono slice t0-t1 s, band-limited and resampled to 44.1 kHz (so varispeed, at speeds near or below 1, can't alias)."""
    x, sr = sf.read(path, always_2d=True, dtype='float64')
    x = x.mean(axis=1)[int(t0 * sr):int(t1 * sr)]
    x = sosfiltfilt(butter(4, [hp, lp], 'bandpass', fs=sr, output='sos'), x)
    g = np.gcd(SR, sr)
    return resample_poly(x, SR // g, sr // g), SR


def onset(x, sr, thresh_db=-20):
    """First sample whose 5 ms RMS reaches thresh_db below the slice's 5 ms RMS peak, minus 3 ms."""
    w = int(0.005 * sr)
    e = np.sqrt(np.convolve(x ** 2, np.ones(w) / w, mode='same'))
    return max(int(np.argmax(e > e.max() * 10 ** (thresh_db / 20))) - int(0.003 * sr), 0)


def varispeed(x, xsr, rate, dur):
    """Play x at speed rate(t) (t = output seconds, 1 = original): time-varying resampling, the tape-machine way."""
    t = np.arange(int(dur * SR)) / SR
    p = np.concatenate([[0.0], np.cumsum(rate(t))[:-1]]) * xsr / SR
    assert p[-1] < len(x) - 1, 'source slice too short for this varispeed'
    return np.interp(p, np.arange(len(x)), x)


def fade(x, fin=0.005, fout=0.0):
    x = x.copy()
    n = int(fin * SR)
    sh = (-1,) + (1,) * (x.ndim - 1)  # mono layers and the stereo mix
    x[:n] *= np.linspace(0, 1, n).reshape(sh)
    n = int(fout * SR)
    if n:
        x[-n:] *= (np.linspace(1, 0, n) ** 2).reshape(sh)
    return x


def put(buf, x, at, gain_db, pan=0.0):
    """Constant-power pan of a mono layer into the stereo buffer."""
    i = int(at * SR)
    n = min(len(x), len(buf) - i)
    a = (pan + 1) * np.pi / 4
    buf[i:i + n] += x[:n, None] * (10 ** (gain_db / 20)) * np.array([np.cos(a), np.sin(a)])


def tape_stop(r_end, dur, k=1.4):
    return lambda t: 1 - (1 - r_end) * (t / dur) ** k


def stinger_02():
    """Cassette stall: the deck's rewind button clunks, then motor whine and tape whir run down together (pitch falls)."""
    dur = 0.80
    buf = np.zeros((int(dur * SR), 2))
    clunk, csr = src(VHS, 26.80, 27.40, lp=4500)  # VHS transport clunk (the big one at 26.9 s)
    clunk = clunk[onset(clunk, csr):]
    put(buf, fade(varispeed(clunk, csr, lambda t: 0.82 + 0 * t, 0.30), 0.002, 0.12), 0.0, -9.0, -0.2)  # ~3.4 st down
    whine, wsr = src(CASS, 14.62, 15.62, lp=4000, hp=300)  # cassette motor whine (914 Hz), narrowed to cut its hiss
    put(buf, fade(varispeed(whine, wsr, tape_stop(0.15, dur), dur), 0.03, 0.15), 0.02, 17.0, 0.15)
    whir, hsr = src(VHS, 40.00, 41.00, lp=4000, hp=80)  # VHS steady rewind whir
    put(buf, fade(varispeed(whir, hsr, tape_stop(0.20, dur, 1.2), dur), 0.04, 0.2), 0.02, 0.0, -0.1)
    return buf


def stinger_03():
    """Betamax eject slip: eject clunk, the rewind spool running down with wow (warble), then the transport catches."""
    dur = 0.75
    buf = np.zeros((int(dur * SR), 2))
    ej, esr = src(BETA, 3.10, 3.60, lp=3500)  # Betamax eject mechanism clunk at ~3.2 s
    ej = ej[onset(ej, esr, -10):]  # -10 dB: skip the soft pre-roll so the clunk lands on the glitch frame
    put(buf, fade(varispeed(ej, esr, lambda t: 0.9 + 0 * t, 0.30), 0.002, 0.12), 0.0, -3.0, 0.25)
    spool, ssr = src(VHS, 18.30, 19.00, lp=4500, hp=80)  # VHS rewind spool at full speed (uses ~18.30-18.83 s)

    def wow(t):  # speed falls 1.0 -> 0.55 while wobbling +-7 % at 5.5 Hz: a stretched tape slipping on the capstan
        return (1 - 0.45 * (t / 0.68) ** 1.2) * (1 + 0.07 * np.sin(2 * np.pi * 5.5 * t))
    put(buf, fade(varispeed(spool, ssr, wow, 0.68), 0.02, 0.15), 0.03, 3.0, -0.15)
    catch, csr = src(VHS, 20.40, 20.90, lp=3500)  # VHS mechanism clunk at 20.5 s: the transport catching
    catch = catch[onset(catch, csr):]
    put(buf, fade(varispeed(catch, csr, lambda t: 0.85 + 0 * t, 0.34), 0.002, 0.18), 0.42, 2.0, 0.1)
    return buf


def flatness(x, lo=0.0, hi=None):
    """Energy-weighted mean spectral flatness of 2048-pt frames within 40 dB of the loudest, over lo-hi Hz."""
    m = x.mean(axis=1) if x.ndim == 2 else x
    n, h = 2048, 512
    f = np.fft.rfftfreq(n, 1 / SR)
    band = (f >= lo) & (f <= (hi or SR / 2)) & (f > 0)
    fr = np.lib.stride_tricks.sliding_window_view(m, n)[::h] * np.hanning(n)
    P = np.abs(np.fft.rfft(fr, axis=1)) ** 2
    P = P[:, band] + 1e-20
    e = P.sum(axis=1)
    keep = e > e.max() * 1e-4
    fl = np.exp(np.log(P[keep]).mean(axis=1)) / P[keep].mean(axis=1)
    return float((fl * e[keep]).sum() / e[keep].sum())


def stats(x):
    fd, tmp = tempfile.mkstemp(suffix='.wav')  # audit_synthetic.metrics reads a file
    os.close(fd)
    sf.write(tmp, x, SR, subtype='PCM_16')
    a = metrics(tmp)
    os.remove(tmp)
    return dict(dur=len(x) / SR, peak=20 * np.log10(np.abs(x).max()), rms=20 * np.log10(np.sqrt((x ** 2).mean())),
                flat=a['flat'], score=a['score'], flat_band=flatness(x, 100, 5000))


def render(pairs):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(4, 2, figsize=(14, 10), gridspec_kw=dict(height_ratios=[1, 2.2, 1, 2.2]), sharex=True)
    for r, (name, before, after) in enumerate(pairs):
        for c, (label, x) in enumerate((('before', before), ('after', after))):
            s, m = stats(x), x.mean(axis=1)
            t = np.arange(len(m)) / SR
            a = ax[2 * r, c]
            a.plot(t, m, lw=0.5, color='k')
            a.set_ylim(-0.25, 0.25)
            a.set_title(f'{name} {label}\n{s["dur"]:.2f} s, peak {s["peak"]:.1f} dBFS, RMS {s["rms"]:.1f} dBFS, '
                        f'flatness 100 Hz-5 kHz {s["flat_band"]:.3f}, audit flatness {s["flat"]:.3f}', fontsize=9)
            a = ax[2 * r + 1, c]
            a.specgram(m, NFFT=1024, Fs=SR, noverlap=896, cmap='magma', vmin=-150, vmax=-40)
            a.set_ylim(0, 20000)
            a.set_ylabel('Hz')
    for a in ax[-1]:
        a.set_xlabel('s')
        a.set_xlim(0, 1.0)
    fig.tight_layout()
    os.makedirs(os.path.dirname(PNG), exist_ok=True)
    fig.savefig(PNG, dpi=110)


def main():
    pairs = []
    for name, build in (('SFX_FE_GlitchStinger_02', stinger_02), ('SFX_FE_GlitchStinger_03', stinger_03)):
        old, sr = sf.read(f'{OLD}/{name}.wav', always_2d=True, dtype='float64')
        info = sf.info(f'{OLD}/{name}.wav')
        assert (sr, old.shape[1], info.subtype) == (SR, 2, 'PCM_16'), (sr, old.shape, info.subtype)
        so = stats(old)
        # 6 kHz low-pass on the mix also removes the faint linear-interpolation images varispeed leaves up high
        y = fade(sosfiltfilt(butter(4, 6000, 'low', fs=SR, output='sos'), build(), axis=0), 0.005, 0.08)
        # match the old whole-file RMS unless that would put the peak above the old peak (then the RMS check decides)
        y *= min(10 ** (so['rms'] / 20) / np.sqrt((y ** 2).mean()), 10 ** ((so['peak'] - 0.1) / 20) / np.abs(y).max())
        y = np.round(y * 32767) / 32767  # judge the 16-bit result; checks run before anything is overwritten
        sn = stats(y)
        for k in ('dur', 'peak', 'rms', 'flat', 'flat_band', 'score'):
            print(f'{name} {k:9s} old {so[k]:8.3f}  new {sn[k]:8.3f}')
        assert 0.5 <= sn['dur'] <= 1.1, 'length out of 0.5-1.1 s'
        assert abs(sn['rms'] - so['rms']) <= 1.0, 'RMS not within 1 dB of the old file'
        assert sn['peak'] <= so['peak'] + 0.05, 'peak higher than the old file'
        assert sn['flat'] < 0.5 * so['flat'] and sn['flat_band'] < 0.6 * so['flat_band'], 'not clearly less noise-like'
        assert sn['score'] < 0.5 * so['score'], 'audit still scores it noise-like'
        if '--dry' not in sys.argv:
            sf.write(f'{OUT}/{name}.wav', y, SR, subtype='PCM_16')
        pairs.append((name, old, y))
    render(pairs)
    print('wrote', PNG)


main()
