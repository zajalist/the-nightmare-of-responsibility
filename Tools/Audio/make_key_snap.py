"""The key snapping in the door lock: SFX_Door_KeySnap_06..08, from real CC0 recordings only.
  python -I Tools/Audio/make_key_snap.py
The old takes (_01.._05) are thin clicks: 60-72 % of their energy above 6 kHz, almost nothing below 2 kHz, about 27 dB
crest and 0.1-0.6 s of silence before the click, so the room attenuation's occlusion low-pass (2.5 kHz) left almost
nothing. Each new take starts on its transient (3 ms pre-roll) and layers:
  body  a barn-lock clack or a metal hit (the lock's weight, 0.5-2 kHz, survives filtering)
  snap  a metal can tab snapping off (the break itself, 2-6 kHz)
  ring  a brass cartridge case's first ping, slowed (the broken key's ring, 25-35 ms later)
then a soft tanh drive (less crest, so it reads at the same peak), 120 Hz high-pass, 120 ms fade-out, peak -3 dBFS.
Writes 44.1 kHz 16-bit mono WAVs to P:/FoA-Assets/audio/SFX/Door/ and adds their rows to MANIFEST.md and SOURCES.txt
once. Self-check: onset within 5 ms, at least 25 % of the energy below 2 kHz, crest under 18 dB."""
import site
import sys

sys.path.append(site.getusersitepackages())  # -I drops user site; numpy/scipy/soundfile/librosa live there (trusted)
import librosa  # noqa: E402
import numpy as np  # noqa: E402
import soundfile as sf  # noqa: E402
from scipy.signal import butter, resample_poly, sosfiltfilt  # noqa: E402

SR = 44100
A = 'P:/FoA-Assets/audio'
L = A + '/_libraries'
CC0_BSB = "CC0 1.0 (BigSoundBank: 'CC0 (public domain): Free and royalty-free')"
SRC = {  # key -> (path, label, url, author, licence)
    'can': (L + '/freesound/ashley12275_metal-can-snap/518731_11141750-hq.mp3',
            'Freesound "Cracking, snapping, and clanging (metal can)" (HQ preview MP3)',
            'https://freesound.org/people/Ashley12275/sounds/518731/ (file https://cdn.freesound.org/previews/518/518731_11141750-hq.mp3)',
            'Ashley12275', 'CC0 1.0 Universal'),
    'cart': (L + '/bigsoundbank/s1367_cartridge-case-762-concrete-1/1367.flac', 'BigSoundBank #1367 Cartridge case 7.62mm on concrete #1',
             'https://bigsoundbank.com/bullet-case-7-62mm-on-concrete-1-s1367.html (file https://bigsoundbank.com/UPLOAD/flac/1367.flac)',
             'Joseph SARDIN', CC0_BSB),
    'lock1540': (L + '/bigsoundbank/s1540_barn-lock-locking/1540.flac', 'BigSoundBank #1540 barn lock locking',
                 'https://bigsoundbank.com/barn-lock-locking-s1540.html (file https://bigsoundbank.com/UPLOAD/flac/1540.flac)',
                 'Joseph SARDIN', CC0_BSB),
    'lock1539': (L + '/bigsoundbank/s1539_barn-lock-unlocking/1539.flac', 'BigSoundBank #1539 barn lock unlocking',
                 'https://bigsoundbank.com/barn-lock-unlocking-s1539.html (file https://bigsoundbank.com/UPLOAD/flac/1539.flac)',
                 'Joseph SARDIN', CC0_BSB),
    'hit06': (L + '/opengameart/rubberduck_75-cc0-breaking-falling-hit/sfx_breaking_and_falling_x/bfh1_metal_hit_06.ogg',
              'OpenGameArt rubberduck "75 CC0 breaking / falling / hit sfx" / bfh1_metal_hit_06.ogg',
              'https://opengameart.org/content/75-cc0-breaking-falling-hit-sfx (file https://opengameart.org/sites/default/files/sfx_breaking_and_falling.zip)',
              'rubberduck', 'CC0 1.0 Universal'),
}
# take -> layers (source, onset s in the source, length s in the source, gain dB, delay ms, speed, low-pass Hz or None).
# Lengths stop before each source's next event: the cartridge's bounces would read as a dropped piece (the broken half
# stays in the lock) and the barn lock's second clack as a double hit.
TAKES = {
    6: [('lock1540', 1.277, 0.065, -1, 0, 1.0, None), ('can', 2.821, 0.15, -3, 2, 1.0, None), ('cart', 0.046, 0.22, -10, 30, 0.75, None)],
    7: [('lock1539', 1.567, 0.25, -4, 0, 1.0, None), ('can', 0.697, 0.15, 0, 2, 1.0, None), ('cart', 0.290, 0.13, -8, 25, 0.85, None)],
    8: [('hit06', 0.0, 0.25, -2, 0, 1.0, None), ('can', 2.821, 0.15, -2, 2, 1.0, None), ('lock1540', 1.347, 0.2, -6, 40, 1.0, 3000),
        ('cart', 0.290, 0.13, -12, 30, 0.8, None)],
}
CACHE = {}


def load(key):
    if key not in CACHE:
        CACHE[key] = librosa.load(SRC[key][0], sr=SR, mono=True)[0]
    return CACHE[key]


def layer(key, t0, dur, gain, delay, speed, lp):
    y = load(key)
    w = y[int(t0 * SR):int((t0 + 0.06) * SR)]  # the detected onset is backtracked; start 3 ms before the actual peak
    a = max(0, int(t0 * SR) + int(np.argmax(np.abs(w))) - int(0.003 * SR))
    seg = y[a:a + int(dur / speed * SR)].astype(np.float64)
    if speed != 1.0:  # varispeed: slower and lower together, like tape
        seg = resample_poly(seg, int(round(100 / speed)), 100)
    if lp:
        seg = sosfiltfilt(butter(2, lp, 'lowpass', fs=SR, output='sos'), seg)
    n = int(0.02 * SR)
    seg[-n:] *= np.linspace(1, 0, n)
    return np.concatenate([np.zeros(int(delay / 1000 * SR)), seg / (np.abs(seg).max() + 1e-12) * 10 ** (gain / 20)])


def build(take):
    parts = [layer(*spec) for spec in TAKES[take]]
    y = np.zeros(max(len(p) for p in parts))
    for p in parts:
        y[:len(p)] += p
    y = sosfiltfilt(butter(2, 120, 'highpass', fs=SR, output='sos'), y)
    y = np.tanh(2.5 * y / np.abs(y).max()) / np.tanh(2.5)  # soft drive: denser, less crest
    n = int(0.12 * SR)
    y[-n:] *= np.linspace(1, 0, n) ** 2
    return y / np.abs(y).max() * 10 ** (-3 / 20)


def stats(y):
    S = np.abs(np.fft.rfft(y)) ** 2
    f = np.fft.rfftfreq(len(y), 1 / SR)
    h = int(0.001 * SR)
    onset = next(k for k in range(0, len(y), h) if np.abs(y[k:k + h]).max() > 0.1 * np.abs(y).max()) / SR * 1000
    return dict(seconds=round(len(y) / SR, 3), onset_ms=round(onset, 1),
                crest=round(20 * np.log10(np.abs(y).max() / np.sqrt(np.mean(y ** 2))), 1),
                below2k=round(S[f < 2000].sum() / S.sum(), 2), mid2_6k=round(S[(f >= 2000) & (f < 6000)].sum() / S.sum(), 2),
                above6k=round(S[f >= 6000].sum() / S.sum(), 2))


def main():
    rng = np.random.default_rng(6)
    built = {take: build(take) for take in TAKES}
    for take, y in built.items():  # check every take before anything is written
        st = stats(y)
        print(f'SFX_Door_KeySnap_{take:02d}', st)
        assert st['onset_ms'] <= 5 and st['below2k'] >= 0.25 and st['crest'] < 18, (take, st)
    mine = [f'SFX_Door_KeySnap_{t:02d}.wav' for t in TAKES]
    man = [ln for ln in open(A + '/MANIFEST.md', encoding='utf-8').read().split('\n') if not any(m in ln for m in mine)]
    src, skip = [], False
    for ln in open(A + '/SOURCES.txt', encoding='utf-8').read().split('\n'):  # re-running replaces this set's rows
        skip = any(m in ln for m in mine) or (skip and ln.startswith('    local:'))
        if not skip:
            src.append(ln)
    man, src = '\n'.join(man).rstrip('\n'), '\n'.join(src).rstrip('\n')
    for take, y in built.items():
        name = f'SFX_Door_KeySnap_{take:02d}'
        q = np.clip(np.round(y * 32767 + rng.triangular(-1, 0, 1, len(y))), -32768, 32767).astype(np.int16)
        sf.write(f'{A}/SFX/Door/{name}.wav', q, SR, subtype='PCM_16')
        keys = [s[0] for s in TAKES[take]]
        proc = '; '.join(f'{SRC[k][1]} from {t0:.3f} s, {dur * 1000:.0f} ms, {g} dB, +{d} ms' + (f', speed {sp}' if sp != 1 else '')
                         + (f', low-pass {lp} Hz' if lp else '') for k, t0, dur, g, d, sp, lp in TAKES[take])
        proc += '; 120 Hz high-pass, soft tanh drive, 120 ms fade-out, peak -3 dBFS'
        # MANIFEST columns: file | what | source | url | author | licence | length | size | loop | channels
        man += (f'\n| `SFX/Door/{name}.wav` | The key snapping in the lock: a lock clack, a metal tab snapping and a short ring. '
                f'| {proc} | {" + ".join(f"<{SRC[k][2].split(" ")[0]}>" for k in keys)} '
                f'| {" + ".join(dict.fromkeys(SRC[k][3] for k in keys))} | {" + ".join(dict.fromkeys(SRC[k][4] for k in keys))} '
                f'| {len(q) / SR:.2f} s | {(44 + 2 * len(q)) / 1024:.1f} KiB | n/a (one-shot) | mono |')
        src += (f'\nSFX\\Door\\{name}.wav | {" + ".join(SRC[k][2] for k in keys)} | {" + ".join(SRC[k][3] for k in keys)} '
                f'| {" + ".join(dict.fromkeys(SRC[k][4] for k in keys))} | {proc}')
        src += ''.join(f'\n    local: {SRC[k][0]}' for k in dict.fromkeys(keys))
    open(A + '/MANIFEST.md', 'w', encoding='utf-8').write(man + '\n')
    open(A + '/SOURCES.txt', 'w', encoding='utf-8').write(src + '\n')
    print('wrote', len(built), 'takes and their MANIFEST/SOURCES rows')


main()
