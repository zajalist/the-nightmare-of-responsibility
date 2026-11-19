"""Player foley set (footsteps, cloth/body, breathing, T8 battle) cut from real recordings only. No synthesis.
  python -I Tools/Audio/make_player_foley.py            (or --dry <dir> to preview without touching SFX/records)
Sources: BigSoundBank (CC0, files fetched as BWF from bigsoundbank.com/UPLOAD/bwf-en/NNNN.wav), OpenGameArt CC0 packs,
Kenney (CC0) and Sonniss GDC files already in _libraries/. Each output is cut, mono-mixed, high-passed (and low-passed
where noted), resampled to 44.1 kHz, faded (4 ms in), peak-set, TPDF-dithered to 16 bit. Rug steps and crouches are
layers of two real recordings. Loops are cut trough-to-trough on whole breath cycles with an equal-power crossfade.
Writes WAVs to P:/FoA-Assets/audio/SFX/<Category>/, the contact sheet P:/FoA/Saved/HorrorShots/audio/player_foley_sheet.png,
and (idempotently) its rows in MANIFEST.md and its section in SOURCES.txt.
Self-check: duration windows, peak targets, no clipping, mono 44.1 kHz PCM_16 on read-back, DC, silent ends,
loop seam jump and level match."""
import os
import site
import sys

sys.path.append(site.getusersitepackages())  # -I drops user site; numpy/scipy/soundfile/matplotlib live there (trusted)
import numpy as np  # noqa: E402
import soundfile as sf  # noqa: E402
from scipy.signal import butter, find_peaks, resample_poly, sosfiltfilt  # noqa: E402

SR = 44100
A = 'P:/FoA-Assets/audio'
L = A + '/_libraries'
SB = L + '/sonniss'
BSB = L + '/bigsoundbank'
OGA = L + '/opengameart'
PNG = 'P:/FoA/Saved/HorrorShots/audio/player_foley_sheet.png'
DRY = sys.argv[1] if len(sys.argv) > 2 and sys.argv[1] == '--dry' else None  # --dry <dir>: preview only
OUT = sys.argv[2] if DRY else A
SECTION = '== Player foley: footsteps, cloth and body, breathing, T8 battle (make_player_foley.py, 2026-11-09) =='
END = '== end player foley =='

SONNISS = 'Sonniss #GameAudioGDC Bundle License (royalty-free, commercial use, no attribution required)'
CC0 = 'CC0 1.0 Universal'
FILM = (SB + '/Sonniss.com_-_GDC_2016-_Game_Audio_Bundle_Part_2of6/Filmnoise - Unusual Footsteps and Movements Vol.1/'
        'SOCKS WOOD DECK FOOTSTEP SUDDEN FAST MOVEMENT FIGHT STRUGGLE PSYCH OUT.wav')
OWEN = (SB + '/Sonniss.com-GDC2024-GameAudioBundle9of9/UberDuo - Inhale \u2013 Owen \u2013 Character Playset/'
        'HMNBrth_Human, Adult, Male, Breathe, Mouth, Slow,_UberDuo_INHL.wav')
OWL = OGA + '/owlishmedia_sound-effects-pack/OwlishMediaSoundEffects_x'
RUST = OGA + '/iochi-glaucus_fabric-rustling/rustling.ogg'
CARPET = L + '/kenney/impact-sounds/Audio/footstep_carpet_00%d.ogg'
CLOTH = L + '/kenney/rpg-audio/Audio/cloth%d.ogg'


def bsb(n):
    return f'{BSB}/s{n:04d}/{n:04d}.wav'


# source path -> (label for MANIFEST, page URL, author, licence)
def _bsb_meta(n, title, author='Joseph SARDIN'):
    return (f'BigSoundBank #{n:04d} "{title}" / {n:04d}.wav', f'https://bigsoundbank.com/s{n:04d}.html', author, CC0)


META = {
    FILM: ('Sonniss GDC bundle: Filmnoise - Unusual Footsteps and Movements Vol.1 / SOCKS WOOD DECK FOOTSTEP SUDDEN FAST '
           'MOVEMENT FIGHT STRUGGLE PSYCH OUT.wav',
           'https://downloads.sonniss.com/Sonniss.com%20-%20GDC%202016-%20Game%20Audio%20Bundle%20Part%202of6.zip',
           'Filmnoise', SONNISS),
    OWEN: ('Sonniss GDC bundle: UberDuo - Inhale \u2013 Owen \u2013 Character Playset / HMNBrth_Human, Adult, Male, Breathe, '
           'Mouth, Slow,_UberDuo_INHL.wav',
           'https://downloads.sonniss.com/Sonniss.com-GDC2024-GameAudioBundle9of9.zip', 'UberDuo', SONNISS),
    bsb(165): _bsb_meta(165, 'Man Footsteps on the Wooden Floor', 'DavidGreck'),
    bsb(518): _bsb_meta(518, 'Floating Floor Squeaks'),
    bsb(1103): _bsb_meta(1103, 'Breathless Man'),
    bsb(14): _bsb_meta(14, 'Zip #1'),
    bsb(270): _bsb_meta(270, 'Zipper #2', 'DenisChardonnet'),
    bsb(3328): _bsb_meta(3328, 'Zipper #13', 'Joseph SARDIN & Axeline T.'),
    bsb(3330): _bsb_meta(3330, 'Zipper #15', 'Joseph SARDIN & Axeline T.'),
    **{bsb(n): _bsb_meta(n, f'Flag #{n - 1786}') for n in (1787, 1788, 1789, 1790, 1792, 1793, 1794)},
    **{OWL + f'/Footsteps/{f}': (f'OpenGameArt / Owlish Media Sound Effects / Footsteps/{f}',
                                 'https://opengameart.org/content/sound-effects-pack', 'Owlish Media', CC0)
       for f in ('hard-footstep1.wav', 'hard-footstep2.wav', 'hard-footstep3.wav', 'hard-footstep4.wav',
                 'Womens_shoes_2.wav')},
    OWL + '/Human/breath-male.wav': ('OpenGameArt / Owlish Media Sound Effects / Human/breath-male.wav',
                                     'https://opengameart.org/content/sound-effects-pack', 'Owlish Media', CC0),
    RUST: ('OpenGameArt / rustling.ogg (a wool leg warmer rustled by hand)',
           'https://opengameart.org/content/fabric-rustling', 'iochi-glaucus', CC0),
    **{CARPET % i: (f'Kenney impact-sounds / footstep_carpet_00{i}.ogg', 'https://kenney.nl/assets/impact-sounds',
                    'Kenney (kenney.nl)', CC0) for i in (0, 1, 3)},
    **{CLOTH % i: (f'Kenney rpg-audio / cloth{i}.ogg', 'https://kenney.nl/assets/rpg-audio', 'Kenney (kenney.nl)', CC0)
       for i in (1, 2, 3, 4)},
}


def lay(src, t0, dur, hp, lp=None, gain=0.0, at=0.0, onset=None):
    """One layer: src cut from t0 for dur s, filtered hp..lp, gain dB, placed at `at` s; onset=dB below max to align."""
    return dict(src=src, t0=t0, dur=dur, hp=hp, lp=lp, gain=gain, at=at, onset=onset)


# name -> (category, what it is, layers, total s, (min, max) s, peak dBFS, fade-out s)
STEP = (0.15, 0.5)
SPEC = {}
for k, t in enumerate((7.33, 8.32, 47.41), 1):
    SPEC[f'SocksWood_{k:02d}'] = ('Footsteps', 'Socked foot on a wooden deck, walking.',
                                  [lay(FILM, t, 0.45, 50, onset=-30)], 0.45, STEP, -6.0, 0.08)
for k, t in enumerate((1.08, 1.70, 2.93, 3.50, 4.82, 6.11), 1):
    SPEC[f'BootsWood_{k:02d}'] = ('Footsteps', 'Heavy shod step on a hollow wooden floor (heel then toe).',
                                  [lay(bsb(165), t, 0.42, 60, onset=-30)], 0.42, STEP, -6.0, 0.08)
DRESS = ([(OWL + f'/Footsteps/hard-footstep{i}.wav', 0.0) for i in (1, 2, 3, 4)]  # clean studio heel-toe clicks
         + [(OWL + '/Footsteps/Womens_shoes_2.wav', t) for t in (0.15, 1.35)])
for k, (src, t) in enumerate(DRESS, 1):
    SPEC[f'DressShoeWood_{k:02d}'] = ('Footsteps', 'Hard-soled shoe: crisp heel click, then toe.',
                                      [lay(src, t, 0.36, 80, onset=-30)], 0.36, STEP, -6.0, 0.08)
for k, (t, c) in enumerate(zip((2.33, 4.15, 25.02, 26.17, 33.60), (0, 1, 3, 1, 0)), 1):
    SPEC[f'SocksRug_{k:02d}'] = ('Footsteps', 'Socked step through a thick rug: the sock step low-passed at 600 Hz '
                                 'under a quiet real foot-on-carpet scuff.',
                                 [lay(FILM, t, 0.40, 50, 600, 0.0, 0.0, -30),
                                  lay(CARPET % c, 0.0, 0.13, 300, 3500, -14.0, 0.006, -30)], 0.38, STEP, -6.0, 0.10)
for k, (t, c) in enumerate(zip((7.44, 8.08, 2.29, 4.11, 0.34), (1, 3, 0, 3, 1)), 1):
    SPEC[f'BootsRug_{k:02d}'] = ('Footsteps', 'Heavy shod step on a thick rug: the wooden-floor step low-passed at '
                                 '1.2 kHz under a real foot-on-carpet scuff.',
                                 [lay(bsb(165), t, 0.42, 60, 1200, 0.0, 0.0, -30),
                                  lay(CARPET % c, 0.0, 0.13, 200, None, -7.0, 0.004, -30)], 0.40, STEP, -6.0, 0.10)
for k, i in enumerate((1, 2, 3, 4), 1):
    SPEC[f'ClothMove_{k:02d}'] = ('Foley', 'Short clothing rustle (step or arm move).',
                                  [lay(CLOTH % i, 0.0, 0.55 if i == 1 else 0.36, 80, onset=-30)],
                                  0.55 if i == 1 else 0.36, (0.2, 0.6), -10.0, 0.10)
for k, t in enumerate((11.43, 20.25), 5):
    SPEC[f'ClothMove_{k:02d}'] = ('Foley', 'Short wool rustle (step or arm move).',
                                  [lay(RUST, t, 0.45, 120, onset=-30)], 0.45, (0.2, 0.6), -10.0, 0.12)
for k, t in enumerate((5.22, 18.45, 24.92), 1):
    SPEC[f'ClothTurn_{k:02d}'] = ('Foley', 'Bigger wool rustle for a body turn.',
                                  [lay(RUST, t, 0.85, 120, onset=-30)], 0.85, (0.4, 0.9), -10.0, 0.20)
SPEC['Reach_01'] = ('Foley', 'Sleeve rustle for an arm reach.', [lay(RUST, 16.58, 0.62, 120, onset=-30)],
                    0.62, (0.4, 0.9), -10.0, 0.15)
for k, t in enumerate((8.30, 6.55), 2):  # slow wool swells read as a sleeve drawn taut
    SPEC[f'Reach_{k:02d}'] = ('Foley', 'Sleeve drawn and stretched for an arm reach.',
                              [lay(RUST, t, 0.75, 120, onset=-30)], 0.75, (0.4, 0.9), -10.0, 0.18)
for k, (t, c) in enumerate(zip((13.58, 22.40, 24.06), (4.72, 8.30, 13.67)), 1):
    SPEC[f'Crouch_{k:02d}'] = ('Foley', 'Knee bend: a cloth rustle, then a floorboard squeak under the weight.',
                               [lay(RUST, t, 0.42, 120, None, 0.0, 0.0, -30),
                                lay(bsb(518), c, 0.40, 120, None, -5.0, 0.20, -30)], 0.72, (0.5, 1.0), -10.0, 0.15)
for k, t in enumerate((0.15, 0.95, 1.90, 2.70, 3.55), 1):
    SPEC[f'Effort_{k:02d}'] = ('Breath', 'Short male effort exhale (reach or lift).',
                               [lay(OWL + '/Human/breath-male.wav', t, 0.48, 100, onset=-24)], 0.48, (0.3, 1.0), -12.0,
                               0.16)
for k, (n, t) in enumerate(((1787, 0.60), (1788, 0.12), (1789, 2.10), (1792, 0.35)), 1):
    SPEC[f'ClothSnap_{k:02d}'] = ('Battle', 'Fabric snapped taut: a short swish into a sharp crack (nylon flag).',
                                  [lay(bsb(n), t, 0.32, 80)], 0.32, (0.2, 0.5), -6.0, 0.08)
for k, (n, t, d) in enumerate(((3328, 0.905, 0.15), (3328, 1.94, 0.16), (3328, 2.395, 0.13), (3330, 2.81, 0.13)), 1):
    SPEC[f'Button_{k:02d}'] = ('Battle', 'Trouser button clicking through its hole.',
                               [lay(bsb(n), t, d, 300)], d, (0.08, 0.4), -8.0, 0.04)
for k, (n, t, d) in enumerate(((14, 1.66, 0.90), (14, 2.92, 0.52), (270, 0.0, 0.42)), 1):
    SPEC[f'Zipper_{k:02d}'] = ('Battle', 'Fast zip.', [lay(bsb(n), t, d, 120, onset=-30)], d, (0.3, 1.0), -8.0, 0.06)
for k, (n, t, d) in enumerate(((1790, 0.18, 0.95), (1794, 0.28, 1.20), (1793, 0.55, 1.15), (1789, 1.15, 0.95)), 1):
    SPEC[f'FabricWhoosh_{k:02d}'] = ('Battle', 'Fabric swung through the air (nylon flag shaken).',
                                     [lay(bsb(n), t, d, 80)], d, (0.5, 1.3), -8.0, 0.15)

# loops: name -> (category, what, src, high-pass, low-pass, troughs spanned, trough min distance s, (min, max) s, peak)
LOOPS = {  # Owen: troughs alternate after-inhale/after-exhale, 4 = two full slow breaths; the 7 kHz low-pass trims hiss
    'TiredIdle_Loop_01': ('Breath', 'Slow tired mouth breathing, quiet (male).', OWEN, 60, 7000, 4, 2.5, (10.0, 20.0),
                          -20.0),
    'Panic_Loop_01': ('Breath', 'Fast frightened panting (male, out of breath).', bsb(1103), 100, None, 16, 0.4,
                      (6.0, 12.0), -10.0),
}

_cache = {}


def load(path, hp, lp):
    """Whole file, mono, filtered at its own rate, resampled to 44.1 kHz."""
    key = (path, hp, lp)
    if key not in _cache:
        x, sr = sf.read(path, always_2d=True, dtype='float64')
        m = sosfiltfilt(butter(2, hp, 'highpass', fs=sr, output='sos'), x.mean(axis=1))
        if lp:
            m = sosfiltfilt(butter(4, lp, 'lowpass', fs=sr, output='sos'), m)
        g = np.gcd(SR, sr)
        _cache[key] = resample_poly(m, SR // g, sr // g)
    return _cache[key]


def cut(ly):
    m = load(ly['src'], ly['hp'], ly['lp'])
    i = int(ly['t0'] * SR)
    if ly['onset'] is not None:  # first 3 ms RMS within `onset` dB of the window's loudest, minus 3 ms
        w = int(0.003 * SR)
        seg = m[i:i + int((ly['dur'] + 0.1) * SR)]
        e = np.sqrt(np.convolve(seg ** 2, np.ones(w) / w, mode='same'))
        i += max(int(np.argmax(e > e.max() * 10 ** (ly['onset'] / 20))) - w, 0)
    n = int(round(ly['dur'] * SR))
    y = m[i:i + n]
    if len(y) < n:  # one-shot source ended: pad only if it had already decayed to silence
        assert np.abs(m[-int(0.01 * SR):]).max() < np.abs(m).max() * 10 ** (-40 / 20), f'{ly["src"]} too short'
        y = np.pad(y, (0, n - len(y)))
    return y * 10 ** (ly['gain'] / 20), i / SR


def fade(y, fin, fout):
    y = y.copy()
    n = int(fin * SR)
    y[:n] *= np.sin(np.linspace(0, np.pi / 2, n)) ** 2
    n = int(fout * SR)
    y[-n:] *= np.cos(np.linspace(0, np.pi / 2, n)) ** 2
    return y


def finish(y, peak_db, rng):
    """Peak-set, TPDF dither, quantize to 16 bit (the returned array is what gets written)."""
    y = y * 10 ** (peak_db / 20) / np.abs(y).max()
    y = y + (rng.random(len(y)) - rng.random(len(y))) / 32767
    return np.round(np.clip(y, -1, 1) * 32767) / 32767


def make_loop(src, hp, lp, step, dist, lo, hi):
    """`step` envelope troughs (pauses between breaths) from a start trough, end crossfaded into the start.
    step is even for panting, whose troughs alternate after-inhale / after-exhale, so the phase matches at the seam."""
    m = load(src, hp, lp)
    w = int(0.1 * SR)
    env = np.sqrt(np.convolve(m ** 2, np.ones(w) / w, mode='same'))
    tr, _ = find_peaks(-env, distance=int(dist * SR), prominence=env.max() * 0.05)
    tr = tr[(tr > SR // 4) & (tr < len(m) - SR // 4)]
    ok = [a for a in range(len(tr) - step) if lo + 0.1 <= (tr[a + step] - tr[a]) / SR <= hi - 0.1]
    assert ok, (src, 'no trough pair in range', np.diff(tr) / SR)
    best = min(ok, key=lambda a: abs(20 * np.log10(env[tr[a]] / env[tr[a + step]])))
    a, b = tr[best], tr[best + step]
    xf = int(0.06 * SR)
    y = m[a:b].copy()
    r = np.linspace(0, np.pi / 2, xf)
    y[:xf] = y[:xf] * np.sin(r) + m[b:b + xf] * np.cos(r)  # tail past the end point fades into the head
    return y, a / SR, b / SR


def seam(y):
    """Jump across the wrap vs the signal's own 99.9th-pct step, and level of the last vs first 50 ms."""
    n = int(0.05 * SR)
    jump = abs(y[-1] - y[0])
    step99 = np.percentile(np.abs(np.diff(y)), 99.9)
    lv = 20 * np.log10(np.sqrt(np.mean(y[-n:] ** 2)) / np.sqrt(np.mean(y[:n] ** 2)))
    return jump, step99, lv


def render(items, png):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    cols = 7
    rows = -(-len(items) // cols)
    fig = plt.figure(figsize=(3.3 * cols, 2.5 * rows))
    grid = fig.add_gridspec(rows, cols, hspace=0.55, wspace=0.25)
    for k, (name, y, st) in enumerate(items):
        cell = grid[k // cols, k % cols].subgridspec(2, 1, height_ratios=[1, 1.6], hspace=0.04)
        a = fig.add_subplot(cell[0])
        t = np.arange(len(y)) / SR
        a.plot(t, y, lw=0.4, color='k')
        a.set_xlim(0, t[-1])
        a.set_ylim(-1, 1)
        a.set_xticks([])
        a.set_yticks([])
        a.set_title(f'{name}\n{st["dur"]:.2f} s  peak {st["peak"]:.1f} dBFS', fontsize=7)
        a = fig.add_subplot(cell[1])
        nfft = 256 if len(y) < SR else 1024
        a.specgram(y, NFFT=nfft, Fs=SR, noverlap=nfft * 3 // 4, cmap='magma', vmin=-130, vmax=-40)
        a.set_xlim(0, t[-1])
        a.set_ylim(0, 14000)
        a.tick_params(labelsize=5)
    os.makedirs(os.path.dirname(png), exist_ok=True)
    fig.savefig(png, dpi=80, bbox_inches='tight')


def _rw(path):
    """Text (newlines normalised) and the file's own newline, so a rewrite keeps CRLF files CRLF."""
    with open(path, 'rb') as f:
        raw = f.read()
    return raw.decode('utf-8').replace('\r\n', '\n'), '\r\n' if b'\r\n' in raw else '\n'


def update_records(rows, src_lines):
    """Replace this script's MANIFEST rows and SOURCES section if present (re-runs), else append."""
    man = A + '/MANIFEST.md'
    text, nl = _rw(man)
    ours = {r.split('|')[1].strip() for r in rows}
    lines = [ln for ln in text.split('\n') if not (ln.startswith('| `') and ln.split('|')[1].strip() in ours)]
    with open(man, 'w', encoding='utf-8', newline=nl) as f:
        f.write('\n'.join(lines).rstrip('\n') + '\n' + '\n'.join(rows) + '\n')
    so = A + '/SOURCES.txt'
    text, nl = _rw(so)
    if SECTION in text:
        head, rest = text.split(SECTION, 1)
        text = head.rstrip('\n') + '\n' + rest.split(END, 1)[1].lstrip('\n')
    with open(so, 'w', encoding='utf-8', newline=nl) as f:
        f.write(text.rstrip('\n') + '\n\n' + '\n'.join([SECTION] + src_lines + [END]) + '\n')


def main():
    rng = np.random.default_rng(20261109)
    items, rows, src_lines = [], [], [
        'Every file is cut from the real recordings listed; nothing is synthesised or generated. Processing: mono mix,',
        'high-pass (and low-pass where noted), resample to 44.1 kHz, 4 ms fade-in, cos^2 fade-out, peak set, TPDF dither',
        'to 16 bit. BigSoundBank files were downloaded as BWF from https://bigsoundbank.com/UPLOAD/bwf-en/NNNN.wav; each',
        'page shows "CC0 (public domain): Free and royalty-free" (checked 2026-11-09).',
        'path | source URL | author | licence | processing']
    out = []
    for name, (cat, what, layers, total, (lo, hi), peak, fout) in SPEC.items():
        y = np.zeros(int(round(total * SR)))
        used = []
        for ly in layers:
            seg, start = cut(ly)
            seg = fade(seg, 0.002, 0.03)
            j = int(ly['at'] * SR)
            n = min(len(seg), len(y) - j)
            y[j:j + n] += seg[:n]
            used.append((ly, start))
        y = finish(fade(y, 0.004, fout), peak, rng)
        out.append((cat, name, what, y, used, False))
    for name, (cat, what, src, hp, lp, step, dist, (lo, hi), peak) in LOOPS.items():
        y, a, b = make_loop(src, hp, lp, step, dist, lo, hi)
        y = finish(y, peak, rng)
        out.append((cat, name, what, y, [(dict(src=src, hp=hp, lp=lp, dur=b - a, gain=0.0, at=0.0), a)], True))
    allspec = {**{k: v[4] for k, v in SPEC.items()}, **{k: v[7] for k, v in LOOPS.items()}}
    peaks = {**{k: v[5] for k, v in SPEC.items()}, **{k: v[8] for k, v in LOOPS.items()}}
    for cat, name, what, y, used, loop in out:
        path = f'{OUT}/SFX/{cat}/SFX_{cat}_{name}.wav'
        os.makedirs(os.path.dirname(path), exist_ok=True)
        sf.write(path, y, SR, subtype='PCM_16')
        info = sf.info(path)
        z, zsr = sf.read(path, always_2d=True)
        st = dict(dur=len(z) / zsr, peak=20 * np.log10(np.abs(z).max()), dc=abs(z.mean()))
        lo, hi = allspec[name]
        assert info.channels == 1 and zsr == SR and info.subtype == 'PCM_16', (name, info)
        assert lo - 1e-9 <= st['dur'] <= hi + 1e-9, (name, 'duration', st['dur'], (lo, hi))
        assert abs(st['peak'] - peaks[name]) < 0.3 and np.abs(z).max() < 0.99, (name, 'peak/clip', st['peak'])
        assert st['dc'] < 0.005, (name, 'DC', st['dc'])
        z = z[:, 0]
        if loop:
            jump, step99, lv = seam(z)
            st['seam'] = (jump, step99, lv)
            assert jump <= step99 and abs(lv) < 4.0, (name, 'seam', jump, step99, lv)
        else:
            assert abs(z[0]) < 2e-3 and abs(z[-1]) < 2e-3, (name, 'ends not silent')
        size = os.path.getsize(path) / 1024
        rel = f'SFX/{cat}/SFX_{cat}_{name}.wav'
        labels = [f'{META[ly["src"]][0]} (cut {s:.2f}\u2013{s + ly["dur"]:.2f} s)' for ly, s in used]
        metas = [META[ly['src']] for ly, _ in used]
        uniq = lambda xs: '<br>'.join(dict.fromkeys(xs))  # noqa: E731
        desc = what + (' Layered and processed from the listed recordings.' if len(used) > 1 else '')
        rows.append(f'| `{rel}` | {desc} | {"<br>".join(labels)} | {uniq("<" + m[1] + ">" for m in metas)} | '
                    f'{uniq(m[2] for m in metas)} | {uniq(m[3] for m in metas)} | {st["dur"]:.2f} s | {size:.1f} KiB | '
                    f'{"Yes, seamless (seam checked)" if loop else "n/a (one-shot)"} | mono |')
        for (ly, s), m in zip(used, metas):
            proc = (f'cut {s:.3f}-{s + ly["dur"]:.3f} s, high-pass {ly["hp"]} Hz'
                    + (f', low-pass {ly["lp"]} Hz' if ly['lp'] else '') + (f', {ly["gain"]:+.0f} dB at +{ly["at"]:.3f} s'
                                                                         if len(used) > 1 else '')
                    + (', whole breath cycles, 60 ms equal-power seam crossfade' if loop else ''))
            src_lines.append(f'{rel} | {m[1]} | {m[2]} | {m[3]} | {m[0]}; {proc}; peak {st["peak"]:.1f} dBFS')
        items.append((f'SFX_{cat}_{name}', z, st))
        extra = f'  seam jump {st["seam"][0]:.4f} (signal step99.9 {st["seam"][1]:.4f}), end/start level {st["seam"][2]:+.1f} dB' if loop else ''
        print(f'{rel:52s} {st["dur"]:6.2f} s  peak {st["peak"]:6.1f} dBFS{extra}')
    render(items, OUT + '/player_foley_sheet.png' if DRY else PNG)
    if not DRY:
        update_records(rows, src_lines)
    print('wrote', len(items), 'files' + ('' if DRY else ', ' + PNG + ' and the MANIFEST/SOURCES records'))


main()
