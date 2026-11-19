"""Music lane: one shared treatment for every music cue, plus the game's music cuts (loop beds, a sting). Offline.
  python -I Tools/Audio/make_music.py                 (all slots)
  python -I Tools/Audio/make_music.py MUS_Battle_Loop (some slots; the music list keeps the others' last rows)
Sources: P:/FoA-Assets/audio/music/work/src_<name>.wav, decoded to 48 kHz float with ffmpeg from user_src/ or cc_src/.
Writes P:/FoA-Assets/audio/music/processed/<slot>.wav (48 kHz, 16-bit, stereo), previews/<slot>.mp3, music_meta.json,
and P:/FoA/docs/design/horror/music_list.md.

The treatment is subtle on purpose, because the voices are the point. It is the same for every cue, so they read as one soundtrack:
  tape speed 0.95 (tempo and pitch together, about -0.9 semitone), 70 Hz high-pass, 7 kHz low-pass, +1.5 dB at 220 Hz,
  -2 dB at 3.2 kHz, soft tape saturation (about 2.4 dB off the peaks), wow 0.2 % at 0.45 Hz and flutter 0.05 % at 5.7 Hz,
  a dark hall (RT60 2.8 s in the lows to 0.9 s in the highs, 25 ms pre-delay) 10 dB under the dry voice, tape hiss 42 dB
  under the music, then loudness to the slot's target (beds -23 LUFS, the sting -18 LUFS) with a -1 dBTP ceiling.
Loops are periodic by construction: an excerpt is crossfaded tail-into-head over one bar, and every stage with memory
(filters, wow, reverb, hiss) wraps around the loop, so the last sample flows into the first and the reverb tail of the
end rings over the start."""
import json
import os
import site
import subprocess
import sys

sys.path.append(site.getusersitepackages())  # -I drops user site; numpy/scipy/soundfile/librosa/pyloudnorm live there (trusted)
if sys.platform == 'win32':  # heavy offline work at BelowNormal so the shared PC stays responsive
    import ctypes
    ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), 0x4000)
import librosa  # noqa: E402
import numpy as np  # noqa: E402
import pyloudnorm as pyln  # noqa: E402
import soundfile as sf  # noqa: E402
from scipy.signal import butter, fftconvolve, resample_poly, sosfilt  # noqa: E402

SR = 48000
ROOT = 'P:/FoA-Assets/audio/music'
WORK, OUT = f'{ROOT}/work', f'{ROOT}/processed'
META = f'{OUT}/music_meta.json'
DOC = 'P:/FoA/docs/design/horror/music_list.md'
WET_DB, HISS_DB, TAIL = -10.0, -42.0, 2.5
SOURCES = {
    'lastdrop': ('Alaa Wardi, "Last Drop Of Hope" (آخر قطرة أمل), a cappella', 'user_src/Alaa Wardi - 6 - Last Drop Of Hope  آخر قطرة أمل - Alaa Wardi.mp3',
                 'Commercial release, all rights reserved (Alaa Wardi). The user picked it; the risk has been flagged to the user.'),
    'amwaaj': ('Alaa Wardi, "Amwaaj", a cappella', 'user_src/Alaa Wardi - 6 - Amwaaj.mp3',
               'Commercial release, all rights reserved (Alaa Wardi). The user picked it; the risk has been flagged to the user.'),
    'plevne': ('"Plevne Marşı", halal version by Halal Professor (vocals and swords only; youtube 7Ft_NyV7WeA)',
               "user_src/Plevne Marşı Halal version by Halalprofessor _ vocals and swords only ringtone.mp3",
               "The user's own pick; licence unknown. The user accepted the risk for their own tracks."),
    # voice only from here on (the user, 2026-11-10): every src_<key>.wav is Demucs's vocal stem (vocal_stems.py)
    'bn1': ('"Background Nasheed 1" (archive.org Islamic Background Nasheed Ahat Collection), vocal stem',
            'archive_src/background-nasheed-collection/Background Nasheed 1.mp3',
            "The user's pick; the archive.org item states no licence (https://archive.org/details/background-nasheed-collection)."),
    'bn10': ('"Background Nasheed 10" (archive.org Islamic Background Nasheed Ahat Collection), vocal stem',
             'archive_src/background-nasheed-collection/Background Nasheed 10.mp3',
             "The user's pick; the archive.org item states no licence (https://archive.org/details/background-nasheed-collection)."),
    'bn26': ('"Background Nasheed 26" (archive.org Islamic Background Nasheed Ahat Collection), vocal stem',
             'archive_src/background-nasheed-collection/Background Nasheed 26.mp3',
             "The user's pick; the archive.org item states no licence (https://archive.org/details/background-nasheed-collection)."),
    'bn2': ('"Background Nasheed 2" (archive.org Islamic Background Nasheed Ahat Collection), vocal stem',
            'archive_src/background-nasheed-collection/Background Nasheed 2.mp3',
            "The user's pick; the archive.org item states no licence (https://archive.org/details/background-nasheed-collection)."),
    'bn3': ('"Background Nasheed 3" (archive.org Islamic Background Nasheed Ahat Collection), vocal stem',
            'archive_src/background-nasheed-collection/Background Nasheed 3.mp3',
            "The user's pick; the archive.org item states no licence (https://archive.org/details/background-nasheed-collection)."),
    'bn4': ('"Background Nasheed 4" (archive.org Islamic Background Nasheed Ahat Collection), vocal stem',
            'archive_src/background-nasheed-collection/Background Nasheed 4.mp3',
            "The user's pick; the archive.org item states no licence (https://archive.org/details/background-nasheed-collection)."),
    'bn5': ('"Background Nasheed 5" (archive.org Islamic Background Nasheed Ahat Collection), vocal stem',
            'archive_src/background-nasheed-collection/Background Nasheed 5.mp3',
            "The user's pick; the archive.org item states no licence (https://archive.org/details/background-nasheed-collection)."),
    'pokemon': ('"It\'s Pokémon Day!", a cappella cover of the Pokémon melody by Raniel Herco', "user_src/It's Pokémon Day!  #acapella.mp3",
                'The melody belongs to Nintendo / The Pokémon Company, and the cover\'s licence is unknown. '
                'The user chose it for the fight knowing the risk.'),
    # free sources (cc_src/CREDITS.txt): Freesound HQ previews, CC BY 4.0; edited, so the credit says so.
    # The Imani nasheed (HalalTrax) was dropped: it is a paid-licence beat.
    'serbianchoir': ('"CHOIR_Serbian_Orthodox_Ambience_4" by SignatureSoundsOrg, church choir in its room (liturgical)',
                     'cc_src/signaturesounds_serbian-choir-4/869836_signaturesoundsorg_choir-serbian-orthodox-ambience-4-hq.mp3',
                     'CC0 1.0. Credit (optional): "CHOIR_Serbian_Orthodox_Ambience_4" by SignatureSoundsOrg (edited), CC0, https://freesound.org/people/SignatureSoundsOrg/sounds/869836/'),
    'monkom': ('"Monk Om" by qubodup (Iwan Gabovitch), hummed male "Om" with echo', 'cc_src/qubodup_monk-om/191662_qubodup_monk-om-hq.mp3',
               'CC BY 4.0. Credit: "Monk Om" Copyright 2013 Iwan Gabovitch (qubodup) (edited), CC BY 4.0, https://freesound.org/people/qubodup/sounds/191662/'),
    'lamento': ('"A cappella - Gregorian lamento" by Vrymaa, male Gregorian-style vocalise with heavy echo', 'cc_src/vrymaa_gregorian-lamento/738774_vrymaa_a-cappella-gregorian-lamento-hq.mp3',
                'CC BY 4.0. Credit: "A cappella - Gregorian lamento" by Vrymaa (edited), CC BY 4.0, https://freesound.org/people/Vrymaa/sounds/738774/'),
    'ferry': ('"ferry_girne-silifke-male_voice" by sazman, a man singing on a ferry (1993, with lyrics)', 'cc_src/sazman_ferry-male-voice/28464_sazman_ferry-girne-silifke-male-voice-hq.mp3',
              'CC BY 4.0. Credit: "ferry_girne-silifke-male_voice" by sazman (edited), CC BY 4.0, https://freesound.org/people/sazman/sounds/28464/'),
    'vrymaa': ('"A cappella - Arabian nights" by Vrymaa, solo male vocalise', 'cc_src/vrymaa_arabian-nights/738836_vrymaa_a-cappella-arabian-nights-hq.mp3',
               'CC BY 4.0. Credit: "A cappella - Arabian nights" by Vrymaa (edited), CC BY 4.0, https://freesound.org/people/Vrymaa/sounds/738836/'),
    'metzik': ('"Throat singing" by Metzik, male throat singing', 'cc_src/metzik_throat-singing/244155_metzik_throat-singing-hq.mp3',
               'CC BY 4.0. Credit: "Throat singing" by Metzik (edited), CC BY 4.0, https://freesound.org/people/Metzik/sounds/244155/'),
    'qubodup': ('"Throat Vocal Groan" by qubodup, slowed male groan', 'cc_src/qubodup_throat-vocal-groan/773750_qubodup_throat-vocal-groan-hq.mp3',
                'CC BY 4.0. Credit: "Throat Vocal Groan" by qubodup (edited), CC BY 4.0, https://freesound.org/people/qubodup/sounds/773750/'),
}


def peak_eq(f, db, q):  # RBJ peaking biquad as one sos row
    a_, w = 10 ** (db / 40), 2 * np.pi * f / SR
    al, c = np.sin(w) / (2 * q), np.cos(w)
    b, a = np.array([1 + al * a_, -2 * c, 1 - al * a_]), np.array([1 + al / a_, -2 * c, 1 - al / a_])
    return np.hstack([b / a[0], a / a[0]])[None]


EQ = np.vstack([butter(2, 70, 'highpass', fs=SR, output='sos'), butter(2, 7000, 'lowpass', fs=SR, output='sos'),
                peak_eq(220, 1.5, 0.7), peak_eq(3200, -2.0, 1.0)])


def hall():
    rng = np.random.default_rng(11)
    n = int(3.6 * SR)
    t = np.arange(n) / SR
    ir = np.zeros((n, 2))
    # (band, RT60 s, level): long dark lows, short quiet highs
    for band, rt, g in (((None, 350), 2.8, 1.0), ((350, 1400), 2.3, 0.8), ((1400, 4000), 1.5, 0.35), ((4000, 8000), 0.9, 0.12)):
        sos = butter(4, band[1], 'lowpass', fs=SR, output='sos') if band[0] is None else butter(4, band, 'bandpass', fs=SR, output='sos')
        b = sosfilt(sos, rng.standard_normal((n, 2)), axis=0)
        ir += b / np.sqrt(np.mean(b ** 2)) * g * np.exp(-6.91 * t / rt)[:, None]
    ir *= np.minimum(t / 0.06, 1)[:, None]  # diffuse build-up instead of a hard onset
    ir = np.vstack([np.zeros((int(0.025 * SR), 2)), ir])  # pre-delay
    return ir / np.sqrt((ir ** 2).sum(0))  # unit energy per channel


IR = hall()


def load(name):
    x, sr = sf.read(f'{WORK}/src_{name}.wav', dtype='float64', always_2d=True)
    assert sr == SR and x.shape[1] == 2, (name, sr, x.shape)
    return resample_poly(x, 20, 19, axis=0)  # tape speed 0.95: 20 samples where there were 19


def rubberband(x, pitch, tag):
    """ffmpeg's rubberband: pitch shift, tempo kept (for layers that must stay locked to the original)"""
    a, b = f'{WORK}/rb_in_{tag}.wav', f'{WORK}/rb_out_{tag}.wav'
    sf.write(a, x.astype(np.float32), SR, subtype='FLOAT')
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', a, '-af', f'rubberband=pitch={pitch}:pitchq=quality:channels=together',
                    '-c:a', 'pcm_f32le', b], check=True)
    y, _ = sf.read(b, dtype='float64', always_2d=True)
    return y[:len(x)] if len(y) >= len(x) else np.vstack([y, np.zeros((len(x) - len(y), 2))])


def wow(x, loop):
    n = len(x)
    t, dur = np.arange(n) / SR, n / SR
    fw, ff = 0.45, 5.7
    if loop:  # whole cycles per loop so the modulation wraps too
        fw, ff = max(1, round(fw * dur)) / dur, max(1, round(ff * dur)) / dur
    d = 0.0020 / (2 * np.pi * fw) * np.sin(2 * np.pi * fw * t) + 0.0005 / (2 * np.pi * ff) * np.sin(2 * np.pi * ff * t + 1.3)
    pos = np.arange(n) - (d + 0.003) * SR  # 3 ms base delay keeps the read head behind
    return np.stack([np.interp(pos, np.arange(n), x[:, c], period=n if loop else None) for c in range(2)], 1)


def conv(x, loop):
    n = len(x)
    if loop:  # circular: the tail of the end rings over the start
        assert n > len(IR)
        return np.fft.irfft(np.fft.rfft(x, axis=0) * np.fft.rfft(IR, n, axis=0), n, axis=0)
    return fftconvolve(x, IR, axes=0)[:n]


def hiss(n, seed=5):
    rng = np.random.default_rng(seed)
    f = np.fft.rfftfreq(n, 1 / SR)
    mag = np.where((f > 400) & (f < 8000), 1 / np.sqrt(np.maximum(f, 1)), 0)  # pink, band-limited; periodic in n
    h = np.fft.irfft(mag[:, None] * np.exp(2j * np.pi * rng.random((len(f), 2))), n, axis=0)
    return h / np.sqrt(np.mean(h ** 2))


def tape(x, loop, wet_db=WET_DB, tail=TAIL):
    """The shared treatment. loop=True treats x as one period of a loop. wet_db/tail: the remixes ask for more hall."""
    if not loop:
        x = np.vstack([x, np.zeros((int(tail * SR), 2))])  # room for the reverb tail
    n = len(x)
    y = sosfilt(EQ, np.vstack([x, x]) if loop else x, axis=0)[-n:]  # loop: the second pass is the steady state
    pk = np.abs(y).max()
    y = np.tanh(y / pk) / np.tanh(1.0) * pk
    y = wow(y, loop)
    y = y + conv(y, loop) * 10 ** (wet_db / 20)
    return y + hiss(n) * np.sqrt(np.mean(y ** 2)) * 10 ** (HISS_DB / 20)


def finish(y, target, name, loop):
    lufs = pyln.Meter(SR).integrated_loudness(y)
    y = y * 10 ** ((target - lufs) / 20)
    tp = 20 * np.log10(np.abs(resample_poly(y, 4, 1, axis=0)).max())
    if tp > -1.0:  # the true-peak ceiling wins over the loudness target
        y *= 10 ** ((-1.0 - tp) / 20)
    q = np.round(y * 32767 + np.random.default_rng(1).triangular(-1, 0, 1, y.shape))  # TPDF dither
    q = np.clip(q, -32768, 32767).astype(np.int16)
    sf.write(f'{OUT}/{name}.wav', q, SR, subtype='PCM_16')
    f = q / 32768.0
    st = dict(lufs=round(pyln.Meter(SR).integrated_loudness(f), 1),
              tp=round(20 * np.log10(np.abs(resample_poly(f, 4, 1, axis=0)).max()), 1), seconds=round(len(f) / SR, 2))
    os.makedirs(f'{OUT}/previews', exist_ok=True)
    prev = np.vstack([f, f[:int(15 * SR)]]) if loop else f  # loops: the whole loop, then 15 s past the wrap
    sf.write(f'{WORK}/prev.wav', prev.astype(np.float32), SR, subtype='FLOAT')
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', f'{WORK}/prev.wav', '-c:a', 'libmp3lame', '-b:a', '192k',
                    f'{OUT}/previews/{name}.mp3'], check=True)
    if loop:
        st['seam'] = seam(f)
    return st


def flux(m, n=2048, hop=1024):
    fr = librosa.util.frame(np.ascontiguousarray(m), frame_length=n, hop_length=hop).T * np.hanning(n)
    s = np.log(np.abs(np.fft.rfft(fr, axis=1)) + 1e-5)
    return np.abs(np.diff(s, axis=0)).mean(1)


def seam(y, at=()):
    """How the wrap compares with the loop's own changes. flux: the largest spectral change in the 0.2 s across the wrap
    over the 95th percentile of that same measure anywhere in the loop (under 1: smoother than most moments). beats: the
    99th percentile of the same measure at the loop's own beats (at, in samples): a bar-aligned wrap sits on a beat, and
    the crossfade makes the wrap the source's own continuous audio at that beat, so it should read like one of its beats. jump: the sample step at the wrap over the loop's 99th-percentile step (under 1: no click)."""
    m = y.mean(1)
    fl = flux(m)
    z = np.concatenate([m[-8192:], m[:8192]])
    jump = abs(m[0] - m[-1]) / np.percentile(np.abs(np.diff(m)), 99)
    ref = np.percentile(np.lib.stride_tricks.sliding_window_view(fl, 9).max(1), 95)
    out = dict(flux=round(float(flux(z)[3:12].max() / ref), 2), jump=round(float(jump), 2))
    v = [fl[i - 5:i + 4].max() for i in np.asarray(at, dtype=int) // 1024 if 5 <= i < len(fl) - 4]
    if v:
        out['beats'] = round(float(np.percentile(v, 99) / ref), 2)
    return out


def beats(x):
    y = librosa.resample(x.mean(1), orig_sr=SR, target_sr=22050)
    tempo, b = librosa.beat.beat_track(y=y, sr=22050, hop_length=512, units='time')
    return y, float(np.atleast_1d(tempo)[0]), b


def find_loop(x, region, lo, hi, grid=None):
    """Best bar-aligned loop in region (s): the bar after the end must sound like the bar after the start (chroma and
    level), because that is what the crossfade blends. grid (s): for beatless material, try points on that grid and use
    a 3 s crossfade instead of one bar."""
    y, tempo, bt = beats(x)
    step = 4  # whole bars keep the downbeat phase
    if grid:
        bt, step = np.arange(region[0], region[1], grid), 1
    fr = 22050 / 512
    ch = librosa.feature.chroma_cqt(y=y, sr=22050, hop_length=512)
    rd = 20 * np.log10(librosa.feature.rms(y=y, hop_length=512)[0] + 1e-6)
    w = int(3.0 * fr)
    cs = np.cumsum(np.pad(ch, ((0, 0), (1, 0))), axis=1)
    win = (cs[:, w:] - cs[:, :-w]) / w
    rs = np.cumsum(np.pad(rd, (1, 0)))
    rwin = (rs[w:] - rs[:-w]) / w
    bf = np.round(bt * fr).astype(int)
    ok = (bt >= region[0]) & (bt <= region[1]) & (bf < win.shape[1] - 1)
    bt, bf = bt[ok], bf[ok]
    best = None
    for i in range(len(bt)):
        for j in range(i + step, len(bt), step):
            L = bt[j] - bt[i]
            if L > hi:
                break
            if L < lo:
                continue
            u, v = win[:, bf[i]], win[:, bf[j]]
            s = u @ v / (np.linalg.norm(u) * np.linalg.norm(v) + 1e-9) - 0.03 * abs(rwin[bf[i]] - rwin[bf[j]])
            if best is None or s > best[0]:
                best = (s, bt[i], bt[j])
    assert best, (region, lo, hi)
    bar = 3.0 if grid else 4 * float(np.median(np.diff(bt)))
    return int(best[1] * SR), int(best[2] * SR), round(float(best[0]), 3), round(tempo, 1), bar


def xfade_loop(x, a, b, n):
    """x[a:b] as one period: the n samples after b fade out over the head while the head fades in (equal power)"""
    y = x[a:b].copy()
    k = np.arange(n) / n
    y[:n] = x[a:a + n] * np.sin(0.5 * np.pi * k)[:, None] + x[b:b + n] * np.cos(0.5 * np.pi * k)[:, None]
    return y


def src_s(i):  # a sample index in the slowed source back to seconds in the original file
    return round(i / SR * 0.95, 2)


def bed(slot, name, region=None, lo=None, hi=None, target=-23.0, grid=None, span=None, xf=4.0):
    """A loop found in region (see find_loop), or a given span (seconds in the original) for one whole gesture, such as a
    single swell: its last xf seconds fade out over its head while the head fades in."""
    x = load(name)
    if span:
        a, b, score, bar = int(span[0] / 0.95 * SR), int((span[1] / 0.95 - xf) * SR), None, xf
    else:
        a, b, score, tempo, bar = find_loop(x, region, lo, hi, grid)
    y = xfade_loop(x, a, b, int(bar * SR))
    naive = seam(x[a:b])
    st = finish(tape(y, True), target, slot, True)
    f = sf.read(f'{OUT}/{slot}.wav', always_2d=True)[0]
    st['seam'] = seam(f, beats(f)[2] * SR)
    st['seam_limit'] = max(1.0, st['seam']['beats'])  # smoother than most moments, or no rougher than its own beats
    assert naive['flux'] > st['seam_limit'] or naive['jump'] >= 1.0, (slot, naive, st['seam_limit'])  # the check can fail
    st.update(source=name, src_in=src_s(a), src_out=src_s(b), xfade=round(bar, 2), match=score, naive_seam=naive,
              how=(f'one gesture, {span[0]}-{span[1]} s of the original, its last {xf} s faded over its head (equal power)'
                   if span else
                   (f'loop {src_s(a)}-{src_s(b)} s of the original (beatless: points on a {grid} s grid), a {bar:.2f} s'
                    if grid else f'bar-aligned loop {src_s(a)}-{src_s(b)} s of the original, a one-bar ({bar:.2f} s)')
                   + f' equal-power crossfade of what follows the end into the head (chroma match {score})'))
    return st


def sting(slot, name, region=None, dur=7.0, target=-18.0, start=None, fades=(1.2, 1.8)):
    """The strongest swell in region (level rise from its first 1.5 s to its last 2 s), or a whole phrase from start
    (seconds in the original file) when one is known"""
    x = load(name)
    if start is None:
        m = x.mean(1)
        hop = int(0.1 * SR)
        rd = 20 * np.log10(np.sqrt(np.convolve(m ** 2, np.ones(hop) / hop, 'valid')[::hop]) + 1e-6)
        n = int(dur * 10)
        cands = [(rd[i + n - 20:i + n].mean() - rd[i:i + 15].mean(), i) for i in range(int(region[0] * 10), int(region[1] * 10) - n)]
        rise, i = max(cands)
        a = i * hop
        why = f'the biggest swell in {region[0]}-{region[1]} s, +{rise:.1f} dB'
    else:
        a = int(start / 0.95 * SR)
        why = 'one whole phrase'
    seg = x[a:a + int(dur * SR)].copy()
    fi, fo = int(fades[0] * SR), int(fades[1] * SR)
    seg[:fi] *= (np.sin(0.5 * np.pi * np.arange(fi) / fi) ** 2)[:, None]  # swell in
    seg[-fo:] *= np.cos(0.5 * np.pi * np.arange(fo) / fo)[:, None]  # let the hall carry the end
    st = finish(tape(seg, False), target, slot, False)
    st.update(source=name, src_in=src_s(a), src_out=src_s(a + len(seg)),
              how=f'{src_s(a)}-{src_s(a + len(seg))} s of the original ({why}), {fades[0]} s swell-in, {fades[1]} s '
                  f'fade into a {TAIL} s hall tail')
    return st


def battle(slot='MUS_Battle_Loop', target=-23.0):
    """The 15 s Pokemon cover as a fight loop of five phrases (beat 1 at 0.21 s, 86 bpm, the closing hit at 14.26 s is
    beat 1 of the next phrase, so a phrase is 5 bars): the theme twice over an octave-down copy, the theme reversed over its
    reversed octave copy, then the whole theme at half speed (an octave down, half tempo) for two phrases. Each layer is
    placed circularly, so every closing hit lands on the next section's downbeat, including the wrap."""
    x = load('pokemon')
    k = 20 / 19
    s0, p = int(0.21 * k * SR), int((14.26 - 0.21) * k * SR)
    f = int(0.02 * SR)
    x[-f:] *= np.linspace(1, 0, f)[:, None]
    lowo = butter(2, 2000, 'lowpass', fs=SR, output='sos')
    o = sosfilt(lowo, rubberband(x, 0.5, 'poke'), axis=0)  # an octave down, locked to the original
    L = 5 * p
    y = np.zeros((L, 2))

    def put(seg, at, g):
        idx = (np.arange(len(seg)) + at) % L
        y[idx] += seg * g

    def rev(z):
        r = z[s0:s0 + p][::-1].copy()
        r[:f] *= np.linspace(0, 1, f)[:, None]
        r[-f:] *= np.linspace(1, 0, f)[:, None]
        return r

    for sec in (0, 1):
        put(x, sec * p - s0, 1.0)
        put(o, sec * p - s0, 0.35)
    put(rev(x), 2 * p, 0.7)
    put(rev(o), 2 * p, 0.35)
    put(resample_poly(x, 2, 1, axis=0), 3 * p - 2 * s0, 0.9)
    st = finish(tape(y, True), target, slot, True)
    f = sf.read(f'{OUT}/{slot}.wav', always_2d=True)[0]
    # the wrap is a section change by design (the half-speed closing hit on the theme's downbeat): hold it to the
    # arrangement's own section changes rather than to the music's ordinary moments
    st['inner_seams'] = [seam(np.roll(f, -k * p, axis=0))['flux'] for k in range(1, 5)]
    st['seam_limit'] = max(st['inner_seams'])
    st.update(source='pokemon', src_in=0.0, src_out=14.7, xfade=0.0,
              how='five-phrase arrangement (phrase 0.21-14.26 s of the original, 5 bars at 86 bpm, 14.79 s after the tape '
                  'slow-down): 1-2 the theme with an octave-down copy 9 dB under (rubberband, locked, low-passed at 2 kHz); '
                  '3 the theme reversed with its reversed octave copy; 4-5 the theme at half speed (an octave down, half '
                  'tempo); layers placed circularly so each closing hit lands on the next downbeat, including the wrap')
    return st



def pingpong(x, beat, loop, g=0.55, lp=2200.0, wet_db=-5.0, wash=8.0):
    """Tempo-synced ping-pong delay: the mono sum enters left; left repeats after 1 beat into right, right after 1.5
    beats back into left, each pass low-passed (dark) at gain g, so the feedback smears into a wash. Solved per
    frequency as y = x + M y (circular when loop, so the wash wraps over the loop's start)."""
    n = len(x)
    if not loop:
        n = n + int(wash * SR)  # room for the wash to die away
    f = np.fft.rfftfreq(n, 1 / SR)
    d1, d2 = int(beat * SR), int(1.5 * beat * SR)
    a = g / np.sqrt(1 + (f / lp) ** 4)  # second-order low-pass magnitude in the loop
    e1, e2 = a * np.exp(-2j * np.pi * f * d1 / SR), a * np.exp(-2j * np.pi * f * d2 / SR)
    xin = np.fft.rfft(np.pad(x.mean(1), (0, n - len(x))))
    det = 1 - e1 * e2  # [yl; yr] = [xin + e2*yr; e1*yl]
    yl = xin / det
    yr = e1 * yl
    wet = np.stack([np.fft.irfft(yl - xin, n), np.fft.irfft(yr, n)], 1)  # the repeats only
    dry = np.pad(x, ((0, n - len(x)), (0, 0)))
    return dry + wet * 10 ** (wet_db / 20)


def sweep(seg, lo=300.0):
    """A filtered drop: the segment slides from dry into a low-pass at lo Hz"""
    k = np.linspace(0, 1, len(seg))[:, None] ** 1.5
    return seg * (1 - k) + sosfilt(butter(2, lo, 'lowpass', fs=SR, output='sos'), seg, axis=0) * k


def edge(seg, ms=15):
    seg = seg.copy()
    n = int(ms / 1000 * SR)
    seg[:n] *= np.linspace(0, 1, n)[:, None]
    seg[-n:] *= np.linspace(1, 0, n)[:, None]
    return seg


def plevne_parts():
    """The slowed march, its beat, and the fragments every Plevne remix uses (times in the original file)."""
    x = load('plevne')
    _, tempo, bt = beats(x)
    beat = float(np.median(np.diff(bt)))
    if beat < 0.6:  # the tracker can lock to the eighth; the march's step is the slower pulse
        beat *= 2
    on = lambda t: int(bt[np.argmin(np.abs(bt - t / 0.95))] * SR)  # noqa: E731  the tracked beat nearest a time
    fr = lambda t, nb: edge(x[on(t):on(t) + int(nb * beat * SR)])  # noqa: E731
    clash = [edge(x[int(t / 0.95 * SR) - int(0.003 * SR):int(t / 0.95 * SR) + int(0.35 * SR)], 3) for t in (13.40, 13.86, 61.27, 61.70)]
    return x, beat, fr, clash


def remix_battle(slot='MUS_ALT_Battle_PlevneRemix', target=-23.0):
    """The march chopped and rearranged, 14 bars: A the chant over itself an octave down; B a one-beat word stuttered
    (4 x 1 beat, 8 x 1/2 beat) into a filtered drop; C a two-bar phrase reversed over clashes on the downbeats; D two
    bars at half speed (four bars, a swell) under a faint copy of the pulse; E the chant again with clashes. Then a
    ping-pong delay on the beat (1 and 1.5 beats, dark, feedback 0.55) and the shared chain with a heavier hall."""
    x, beat, fr, clash = plevne_parts()
    bar = 4 * beat
    L = int(round(14 * bar * SR))
    y = np.zeros((L, 2))

    def put(seg, at_beats, g=1.0):
        idx = (np.arange(len(seg)) + int(at_beats * beat * SR)) % L
        y[idx] += seg * g

    a = fr(30.3, 16)
    put(a, 0)
    put(sosfilt(butter(2, 1800, 'lowpass', fs=SR, output='sos'), rubberband(a, 0.5, 'plevA'), axis=0), 0, 0.4)
    word = fr(33.6, 1)
    for i in range(4):
        put(word, 16 + i)
    half = edge(word[:len(word) // 2], 5)
    st = np.concatenate([half] * 8)
    put(sweep(st), 20)
    put(fr(45.0, 8)[::-1], 24, 0.85)
    for i in range(2):
        put(clash[i], 24 + 4 * i, 0.9)
    sw = resample_poly(fr(52.0, 8), 2, 1, axis=0)  # half speed: an octave down, a 16-beat swell
    sw *= (np.sin(0.5 * np.pi * np.minimum(np.arange(len(sw)) / (len(sw) * 0.6), 1)) ** 2)[:, None]
    put(sw, 32, 0.9)
    put(sosfilt(butter(2, 400, 'lowpass', fs=SR, output='sos'), fr(30.3, 16), axis=0), 32, 0.3)  # the pulse, under
    put(fr(61.3, 8), 48)
    for i in range(2):
        put(clash[2 + i], 48 + 4 * i, 0.9)
    y = pingpong(y, beat, True)
    st = finish(tape(y, True, wet_db=-4.0), target, slot, True)
    f = sf.read(f'{OUT}/{slot}.wav', always_2d=True)[0]
    st['inner_seams'] = [seam(np.roll(f, -int(b * beat * SR), axis=0))['flux'] for b in (16, 20, 24, 32, 48)]
    st['seam_limit'] = max(st['inner_seams'])  # the wrap is a section change by design: no rougher than the others
    st.update(source='plevne', src_in=30.3, src_out=69.0, xfade=0.0,
              how=f'a remix on the march\'s beat ({60 / beat:.1f} bpm after the slow-down), 14 bars: the chant over itself '
                  'an octave down; a one-beat word stuttered 4x, then 8 half-beat repeats into a filtered drop; a two-bar '
                  'phrase reversed over sword clashes; two bars at half speed as a swell over a low-passed pulse; the chant '
                  'again with clashes; a ping-pong delay on 1 and 1.5 beats with dark feedback; a heavier hall (-4 dB)')
    return st


def remix_short(slot='MUS_ALT_Victory_PlevneRemix', target=-23.0):
    """About 20 s: the last phrase, its final word stuttered, a reversed swell into one clash, then the delay wash"""
    x, beat, fr, clash = plevne_parts()
    parts = [fr(63.5, 8), np.concatenate([edge(fr(70.0, 1)[:int(0.5 * beat * SR)], 5)] * 6),
             fr(66.0, 4)[::-1].copy(), clash[3]]
    y = np.concatenate(parts)
    y = pingpong(y, beat, False, g=0.6)
    st = finish(tape(y, False, wet_db=-3.0, tail=4.0), target, slot, False)
    st.update(source='plevne', src_in=63.5, src_out=74.0,
              how='the march\'s last phrase (8 beats), its last word stuttered 6 half-beats, 4 beats reversed as a swell '
                  'into one sword clash, then the ping-pong delay (feedback 0.6) washing out under a 4 s hall tail')
    return st


def wordless(key):
    """Wordless spans (seconds in the original) from vocal_stems.py's word check; the whole file when none was run"""
    p = f'{ROOT}/stems/{key}.json'
    return json.load(open(p, encoding='utf-8'))['wordless'] if os.path.exists(p) else None


def voice_parts(key):
    """The vocal stem (slowed), its beat, a fragment cutter on that beat restricted to wordless time, and the
    loudest wordless one-beat word (for stutters)."""
    x = load(key)
    _, tempo, bt = beats(x)
    beat = float(np.median(np.diff(bt))) if len(bt) > 4 else 0.85
    if beat < 0.45:
        beat *= 2
    free = [(a / 0.95, b / 0.95) for a, b in (wordless(key) or [[0, len(x) / SR * 0.95]])]  # in slowed seconds

    def fr(t, nb, near=True):
        """nb beats from the tracked beat nearest t (slowed s), moved inside the wordless span that holds most of it"""
        n = nb * beat
        span = max(free, key=lambda s: min(s[1], t + n) - max(s[0], t)) if free else (0, len(x) / SR)
        t = min(max(t, span[0]), max(span[0], span[1] - n))
        if near and len(bt):
            t = float(bt[np.argmin(np.abs(bt - t))])
            t = min(max(t, span[0]), max(span[0], span[1] - n))
        return edge(x[int(t * SR):int((t + n) * SR)])

    m = x.mean(1)
    h = int(beat * SR)
    best = max(((np.sqrt(np.mean(m[int(a * SR) + k:int(a * SR) + k + h] ** 2)), a + k / SR)
                for a, b in free for k in range(0, max(1, int((b - a) * SR) - h), h)), default=(0, 0))[1]
    return x, beat, fr, best, free


def remix(slot, key, style, bars, target=-23.0, at=None, wash=8.0, tail=4.0):
    """A remix of a vocal stem's wordless time on its own beat, for the level-1 set (the user: 'proper remixing and
    processing'). style 'drift' (beds): a phrase with itself an octave down under it, then the same phrase at half
    speed as a swell, then a reversed phrase; light ping-pong (feedback 0.45) and a heavy hall. style 'march' (the
    chase): a phrase over its octave, a word stuttered into a filtered drop, a reversed phrase, a half-speed swell, the
    phrase again; ping-pong 0.55. style 'swell' (one-shots: sting, payoff, ending): a phrase over its octave rising out
    of a reversed copy, then the delay washing out. at: where to start (seconds in the original), else the loudest
    wordless beat."""
    x, beat, fr, best, free = voice_parts(key)
    t0 = (at / 0.95) if at is not None else max(free[0][0], best - 4 * beat) if free else 0.0
    if style == 'swell':
        a = fr(t0, bars * 4)
        oct_ = sosfilt(butter(2, 1600, 'lowpass', fs=SR, output='sos'), rubberband(a, 0.5, slot), axis=0)
        rev = a[:len(a) // 2][::-1].copy()
        rev *= np.linspace(0, 1, len(rev))[:, None] ** 2
        y = np.concatenate([rev * 0.7, a + oct_ * 0.4])
        y = pingpong(y, beat, False, g=0.5, wash=wash)
        n = len(y) - int(wash * SR) + int(min(wash, 1.5) * SR)  # the delay's wash is cut short with a fade where asked
        if wash < 8.0:
            y = y[:n]
            f = int(min(wash, 1.5) * SR)
            y[-f:] *= np.linspace(1, 0, f)[:, None] ** 2
        st = finish(tape(y, False, wet_db=-3.0, tail=tail), target, slot, False)
        st.update(source=key, src_in=round(t0 * 0.95, 2), src_out=round((t0 + bars * 4 * beat) * 0.95, 2),
                  how=f'{bars} bars of wordless voice rising out of its own first half reversed, an octave-down copy under '
                      'it, a ping-pong delay (feedback 0.5) washing out under a heavy hall')
        return st
    L = int(round(bars * 4 * beat * SR))
    y = np.zeros((L, 2))

    def put(seg, at_beats, g=1.0):
        idx = (np.arange(len(seg)) + int(at_beats * beat * SR)) % L
        y[idx] += seg * g

    q = bars // 4  # sections of the loop, in bars
    a = fr(t0, q * 4)
    oct_a = sosfilt(butter(2, 1600, 'lowpass', fs=SR, output='sos'), rubberband(a, 0.5, slot), axis=0)
    if style == 'drift':
        nb = int(beat * SR)
        soft = a.copy()  # the loop's wrap: the last section fades out over its last beat, the first fades in over one
        soft[:nb] *= (np.sin(0.5 * np.pi * np.arange(nb) / nb) ** 2)[:, None]
        put(soft, 0)
        put(oct_a, 0, 0.45)
        sw = resample_poly(fr(t0 + q * 4 * beat, q * 2), 2, 1, axis=0)  # half speed: q*2 beats become q*4
        sw *= (np.sin(0.5 * np.pi * np.minimum(np.arange(len(sw)) / (len(sw) * 0.5), 1)) ** 2)[:, None]
        put(sw, q * 4, 0.9)
        put(fr(t0 + q * 6 * beat, q * 4)[::-1], q * 8, 0.75)
        tailw = np.ones((len(a), 1))
        tailw[-nb:, 0] = np.cos(0.5 * np.pi * np.arange(nb) / nb) ** 2
        put(oct_a * tailw, q * 12, 0.5)
        put(sweep(a, 500) * tailw, q * 12, 0.6)
        g, how = 0.45, ('a wordless phrase over itself an octave down; the next phrase at half speed as a swell; a phrase '
                        'reversed; the first phrase again sinking into a low-pass over its octave')
    else:
        nq = int(beat * SR / 4)  # a quarter-beat fade-in on the downbeat: no step at the wrap, the pulse stays
        a0 = a.copy()
        a0[:nq] *= np.linspace(0, 1, nq)[:, None]
        put(a0, 0)
        put(oct_a, 0, 0.4)
        word = fr(best, 1)
        for i in range(4):
            put(word, q * 4 + i)
        half = edge(word[:len(word) // 2], 5)
        put(sweep(np.concatenate([half] * 8)), q * 4 + 4)
        put(fr(t0 + q * 4 * beat, q * 2)[::-1], q * 4 + 8, 0.85)
        sw = resample_poly(fr(t0 + q * 6 * beat, q * 2), 2, 1, axis=0)
        sw *= (np.sin(0.5 * np.pi * np.minimum(np.arange(len(sw)) / (len(sw) * 0.6), 1)) ** 2)[:, None]
        put(sw, q * 8, 0.9)
        put(a, q * 12)
        g, how = 0.55, ('a wordless phrase over its octave; one word stuttered 4x then 8 half-beats into a filtered drop; a '
                        'phrase reversed; a half-speed swell; the phrase again')
    y = pingpong(y, beat, True, g=g)
    st = finish(tape(y, True, wet_db=-3.5), target, slot, True)
    f = sf.read(f'{OUT}/{slot}.wav', always_2d=True)[0]
    st['inner_seams'] = [seam(np.roll(f, -int(b * beat * SR), axis=0))['flux'] for b in (q * 4, q * 8, q * 12)]
    st['seam_limit'] = max(1.0, max(st['inner_seams']))
    st.update(source=key, src_in=round(t0 * 0.95, 2), src_out=round((t0 + q * 10 * beat) * 0.95, 2), xfade=0.0,
              how=f'remix ({style}, {bars} bars at {60 / beat:.1f} bpm, vocal stem only, wordless time only): {how}; '
                  f'ping-pong delay on 1 and 1.5 beats (feedback {g}), heavy hall (-3.5 dB)')
    return st


def light(slot, key, region, lo, hi, target=-23.0, oct_db=-12.0, echo=0.3, grid=None):
    """The voice nearly as recorded (the user: "you synthesized way too much"): a clean bar-aligned loop of a strong
    passage of the vocal stem, one subtle octave-down copy under it (oct_db), a light ping-pong echo (feedback echo,
    -12 dB) and the shared chain. No stutters, reversals, drops or half-speed."""
    x = load(key)
    a, b, score, tempo, bar = find_loop(x, region, lo, hi, grid)
    y = xfade_loop(x, a, b, int(bar * SR))
    naive = seam(x[a:b])
    if oct_db is not None:
        o = sosfilt(butter(2, 1600, 'lowpass', fs=SR, output='sos'), rubberband(np.vstack([y, y, y]), 0.5, slot), axis=0)
        y = y + o[len(y):2 * len(y)] * 10 ** (oct_db / 20)  # pitched over three periods; the middle one wraps cleanly
    beat = bar / 4
    if echo:
        y = pingpong(y, beat, True, g=echo, wet_db=-12.0)
    st = finish(tape(y, True), target, slot, True)
    f = sf.read(f'{OUT}/{slot}.wav', always_2d=True)[0]
    st['seam'] = seam(f, beats(f)[2] * SR)
    st['seam_limit'] = max(1.0, st['seam'].get('beats', 1.0))
    st.update(source=key, src_in=src_s(a), src_out=src_s(b), xfade=round(bar, 2), match=score, naive_seam=naive,
              how=f'the voice nearly as recorded: bar-aligned loop {src_s(a)}-{src_s(b)} s of the vocal stem, a one-bar '
                  f'crossfade at the wrap, an octave-down copy {oct_db:.0f} dB under it, a light ping-pong echo on the '
                  f'beat (feedback {echo}, -12 dB) and the shared chain')
    return st


def composite(slot, parts, target=-23.0, xf=3.0, oct_db=-12.0, echo=0.3):
    """A longer bed from wordless takes as recorded (the user: no repeat every 9-17 s): parts = [(key, start, end)] in
    seconds of each original, chained with equal-power crossfades of xf seconds; the end crossfades into the start the
    same way, so it loops. One octave-down copy oct_db under it, a light echo, the shared chain."""
    segs = []
    for key, a0, b0 in parts:
        x = load(key)
        seg = x[int(a0 / 0.95 * SR):int(b0 / 0.95 * SR)]
        segs.append(seg / (np.sqrt(np.mean(seg ** 2)) + 1e-9) * 0.1)  # takes at one level, so no join jumps in loudness
    n = int(xf * SR)
    k = np.arange(n) / n
    fin, fout = np.sin(0.5 * np.pi * k)[:, None], np.cos(0.5 * np.pi * k)[:, None]
    c = segs[0]
    for s_ in segs[1:]:
        c = np.vstack([c[:-n], c[-n:] * fout + s_[:n] * fin, s_[n:]])
    y = xfade_loop(c, 0, len(c) - n, n)  # the last xf seconds fade out over the head
    if oct_db is not None:
        o = sosfilt(butter(2, 1600, 'lowpass', fs=SR, output='sos'), rubberband(np.vstack([y, y, y]), 0.5, slot), axis=0)
        y = y + o[len(y):2 * len(y)] * 10 ** (oct_db / 20)
    _, tempo, bt = beats(y)
    beat = float(np.median(np.diff(bt))) if len(bt) > 4 else 0.8
    if echo:
        y = pingpong(y, beat, True, g=echo, wet_db=-12.0)
    st = finish(tape(y, True), target, slot, True)
    f = sf.read(f'{OUT}/{slot}.wav', always_2d=True)[0]
    st['seam'] = seam(f, beats(f)[2] * SR)
    joins = []  # each join between takes is held to the same check as the wrap
    t = 0
    for s_ in segs[:-1]:
        t += len(s_) - n
        joins.append(seam(np.roll(f, -(t + n // 2), axis=0))['flux'])
    st['inner_seams'] = joins
    st['seam_limit'] = max(1.0, st['seam'].get('beats', 1.0))
    st.update(source=parts[0][0], src_in=parts[0][1], src_out=parts[0][2], xfade=xf,
              how='takes as recorded, chained: ' + ', '.join(f'{k} {a}-{b} s' for k, a, b in parts)
                  + f'; {xf} s equal-power crossfades (and back to the start), an octave-down copy {oct_db:.0f} dB under, '
                    f'a light ping-pong echo (feedback {echo}, -12 dB), the shared chain')
    return st

SLOTS = {
    'MUS_Battle_Loop': ('Battle bed (loop): the Pokemon cover, voice only', lambda: battle()),
    'MUS_BattleIntro_Sting': ('Battle intro sting (the Nightmare watches)', lambda: remix('MUS_BattleIntro_Sting', 'bn1', 'swell', 1.5, at=20.0, wash=3.0, tail=2.0)),
    'MUS_Dream_Loop': ('Level 2 dream world bed (loop)', lambda: bed('MUS_Dream_Loop', 'lastdrop', (20, 160), 80, 120)),
    'MUS_CityDrive_Loop': ('Level 2 city drive bed (loop)', lambda: bed('MUS_CityDrive_Loop', 'amwaaj', (95, 195), 60, 100)),
    # the calm "ethereal pad" part of the vocalise (about 116-153 s of the original)
    'MUS_Menu_Loop': ('Menu / title bed (loop): Nasheed 1 then Nasheed 4, as recorded', lambda: composite('MUS_Menu_Loop', [('bn1', 20.5, 43.0), ('bn4', 6.0, 36.0)])),
    # clean CC BY backups through the same chain (the fight stays the Pokemon cover, the user's call)
    'MUS_CC_Dream_Loop': ('Backup: Level 2 dream world bed (loop)', lambda: bed('MUS_CC_Dream_Loop', 'qubodup', (1, 70), 40, 66)),
    'MUS_CC_CityDrive_Loop': ('Backup: Level 2 city drive or menu bed (loop)', lambda: bed('MUS_CC_CityDrive_Loop', 'vrymaa', (44, 163), 60, 100)),
    'MUS_CC_BattleIntro_Sting': ('Backup: battle intro sting', lambda: sting('MUS_CC_BattleIntro_Sting', 'metzik', dur=7.5, start=85.3, fades=(0.6, 0.4))),
    # A/B alternatives from the second free shortlist (offline previews, not imported)
    'MUS_ALT_Menu_SerbianChoir': ('A/B: menu bed, alt 1', lambda: bed('MUS_ALT_Menu_SerbianChoir', 'serbianchoir', span=(1.6, 45.7), xf=5.0)),
    'MUS_ALT_Menu_MonkOm': ('A/B: menu bed, alt 2', lambda: bed('MUS_ALT_Menu_MonkOm', 'monkom', span=(0.0, 40.6), xf=4.0)),
    'MUS_ALT_Dream_GregorianLamento': ('A/B: Level 2 dream world bed', lambda: bed('MUS_ALT_Dream_GregorianLamento', 'lamento', (1, 83), 60, 80, grid=0.25)),
    'MUS_ALT_City_Ferry': ('A/B: Level 2 city drive bed', lambda: bed('MUS_ALT_City_Ferry', 'ferry', (205, 251), 35, 46)),
    # level 1, more cues (the user, 2026-11-10): wake cinematic, exploration T1-T6, the T7 chase, the T9 payoff, the ending
    'MUS_Wake_Loop': ('Wake-up cinematic bed (quiet loop): Nasheed 26 then Nasheed 4, as recorded', lambda: composite('MUS_Wake_Loop', [('bn26', 1.3, 17.0), ('bn4', 30.0, 56.0)], target=-28.0, xf=4.0, oct_db=-10.0, echo=0.4)),
    'MUS_Explore_Loop': ('T1-T6 exploration bed (low loop): Nasheed 10 nearly as recorded', lambda: light('MUS_Explore_Loop', 'bn10', (2, 66), 48, 62, target=-29.0, grid=0.25)),
    'MUS_Chase_Loop': ('T7 shirt chase (loop): Nasheed 10 nearly as recorded', lambda: light('MUS_Chase_Loop', 'bn10', (20, 70), 32, 60, grid=0.25)),
    'MUS_Payoff': ('T9 suit payoff into T10 (one swell)', lambda: remix('MUS_Payoff', 'lastdrop', 'swell', 6, at=60.0)),
    # the user's Plevne march (2026-11-10): alternates for the fight and the chase, and a victory phrase
    'MUS_ALT_Battle_Plevne': ('A/B: battle bed, the march (loop)', lambda: bed('MUS_ALT_Battle_Plevne', 'plevne', (11, 84), 40, 65)),
    'MUS_ALT_Chase_Plevne': ('A/B: T7 chase, the march (short loop)', lambda: bed('MUS_ALT_Chase_Plevne', 'plevne', (60, 86), 16, 24)),
    'MUS_ALT_Victory_Plevne': ("A/B: victory, the march's last phrase",
                               lambda: sting('MUS_ALT_Victory_Plevne', 'plevne', dur=22.0, target=-23.0, start=63.5, fades=(0.3, 3.0))),
    'MUS_ALT_Battle_PlevneRemix': ('A/B: battle bed, the march remixed (loop)', lambda: remix_battle()),
    'MUS_ALT_Victory_PlevneRemix': ('A/B: victory or chase sting, the march remixed', lambda: remix_short()),
    'MUS_Ending': ('Walk-out, ending and credits (one cue)', lambda: remix('MUS_Ending', 'amwaaj', 'swell', 14, at=95.0)),
}


def write_doc(meta):
    rows = ['| Slot | File | Source | Licence | Length | Loop | Loudness |', '|---|---|---|---|---|---|---|']
    notes = []
    for slot, (label, _) in SLOTS.items():
        m = meta.get(slot)
        if not m:
            continue
        title, path, lic = SOURCES[m['source']]
        loop = (f"whole file; cut from {m['src_in']}-{m['src_out']} s; seam {m['seam']['flux']}, beats "
                f"{m['seam'].get('beats')}, naive cut {m['naive_seam']['flux']}" if m.get('naive_seam') else
                f"whole file; seam {m['seam']['flux']}, its own section changes {m['inner_seams']}" if m.get('inner_seams') else
                'one-shot')
        rows.append(f"| {label} | {slot}.wav | {title} | {lic} | {m['seconds']} s | {loop} | {m['lufs']} LUFS, TP {m['tp']} dBTP |")
        notes.append(f"- {slot}: {m['how']}.")
    with open(DOC, 'w', encoding='utf-8') as fh:
        fh.write('# Music list\n\n'
                 'Files: P:/FoA-Assets/audio/music/processed/ (48 kHz, 16-bit, stereo WAV), previews in previews/ as MP3 '
                 '(loops play once through and then 15 s past the wrap). Built by Tools/Audio/make_music.py from the '
                 'sources in user_src/ (the user\'s picks) and cc_src/.\n\n'
                 'Each loop is the whole file: the file\'s last sample flows into its first, so set Looping on the '
                 'SoundWave and don\'t add any loop points. "Seam" is the largest spectral change in the 0.2 s across the '
                 'wrap divided by the 95th percentile of the same measure anywhere in the loop: below 1 means the wrap is '
                 'smoother than most moments in the music. "Beats" is the same measure at the loop\'s own beats (99th '
                 'percentile): a bar-aligned wrap lands on a beat, so it passes if it reads like one of them. "Naive cut" is the same excerpt looped without '
                 'the crossfade.\n\n'
                 'Shared treatment, the same for every cue, so they read as one soundtrack and stay subtle, '
                 'because the voices are the point: tape speed 0.95 (tempo and pitch, about -0.9 semitone), 70 Hz high-pass, '
                 '7 kHz low-pass, +1.5 dB at 220 Hz, -2 dB at 3.2 kHz, soft tape saturation, wow 0.2 % and flutter 0.05 %, '
                 'a dark hall (RT60 2.8 s lows to 0.9 s highs) 10 dB under the dry voice, tape hiss 42 dB under, beds at '
                 '-23 LUFS and the sting at -18 LUFS, -1 dBTP ceiling. No lyric smearing: the vocals stay intact.\n\n'
                 + '\n'.join(rows) + '\n\nHow each was cut:\n' + '\n'.join(notes) + '\n\n'
                 'Licensing: Battle_Loop, BattleIntro_Sting, Dream_Loop, CityDrive_Loop, Chase_Loop, Ending and the '
                 '*_Plevne files are the user\'s picks (the Plevne march, Halal Professor, licence unknown). The '
                 'Alaa Wardi tracks are commercial releases and the Pokémon melody is Nintendo\'s (cover by Raniel Herco, '
                 'licence unknown); the user chose them knowing the risk. MUS_Menu_Loop and the MUS_CC_ and MUS_ALT_ files '
                 'are free (CC BY 4.0, one CC0), from Freesound HQ previews (records in '
                 'P:/FoA-Assets/audio/music/cc_src/CREDITS.txt). The Serbian choir and the Gregorian lamento are liturgical '
                 'in style, so weigh them against "not too religious"; the ferry singer has clear lyrics. MUS_Menu_Loop '
                 'ships, so its credit line is required; the others are needed only if their file ships:\n'
                 + '\n'.join(f'- {SOURCES[k][2].split("Credit", 1)[1].split(": ", 1)[1]}  ({", ".join(s for s in SLOTS if meta.get(s, {}).get("source") == k)})'
                             for k in SOURCES if 'Credit' in SOURCES[k][2] and any(m.get('source') == k for m in meta.values())) + '\n')


def main():
    os.makedirs(OUT, exist_ok=True)
    only = sys.argv[1:] or list(SLOTS)
    meta = json.load(open(META, encoding='utf-8')) if os.path.exists(META) else {}
    for slot in only:
        meta[slot] = SLOTS[slot][1]()
        print(slot, json.dumps(meta[slot], ensure_ascii=False))
        if meta[slot].get('seam'):  # self-check: the wrap must be no click and smoother than the music's own changes
            lim = meta[slot].get('seam_limit', 1.0)
            assert meta[slot]['seam']['jump'] <= 1.0 and meta[slot]['seam']['flux'] <= lim, (slot, meta[slot]['seam'], lim)
    with open(META, 'w', encoding='utf-8') as fh:
        json.dump(meta, fh, indent=1, ensure_ascii=False)
    write_doc(meta)
    print('wrote', DOC)


main()
