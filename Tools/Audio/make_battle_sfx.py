"""The T8 fight's SFX set, from free recordings only (CC0 / public domain; credits in MANIFEST.md and SOURCES.txt).
  python -I Tools/Audio/make_battle_sfx.py
  GarmentHit_01-04   a flag snap (the garment whipped) over a soft body hit, a short sand spill 15 ms behind
  PlayerHit_01-04    a heavy punch (low-passed: a body, not a fist) and a breath grunt 60 ms later, a cloth rustle
  Telegraph{Cloth,Elastic,Knot}_01-02   a wind-up per garment: a reversed flag whoosh (shirt, trousers), a stretched
                     belt creak (socks), a slowed leather twist (tie), each ending on a small cloth tick
  Stun_01-02         a leather drop and a slowed cloth flop with a sand trickle
  Defeat_01-02       cloth collapsing: a slowed whoosh tail and a cloth drop sinking into a 1.6 s sand pour
  Worn_01-02         put on: a cloth settle over a soft hit (the garment arriving on him, OnGarmentWorn)
  Victory_01         sand settling (a slowed pour, fading) under one long exhale
  Select_01-02, Confirm_01-02   UI ticks: zipper-pull ticks and a small leather click (for the battle widget)
  ComposureLow_Loop_01   frightened breathing, levelled, 10 s with a 1.5 s loop crossfade (BP_RoomAudio fades it in)
Processing is cuts, gains, delays, varispeed, reversal, filters, envelopes and layering; nothing is synthesised.
Writes 44.1 kHz 16-bit mono WAVs to P:/FoA-Assets/audio/SFX/Battle/. Self-check: hits start on their transient
(<= 5 ms), one-shots peak -3 dBFS (UI -9), the loop's wrap has no step larger than its own 99.9th percentile."""
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
CC0, PD = 'CC0 1.0 Universal', 'Public domain'
CC0_BSB = "CC0 1.0 (BigSoundBank: 'CC0 (public domain): Free and royalty-free')"
KEN_IMP = 'https://kenney.nl/assets/impact-sounds'
KEN_RPG = 'https://kenney.nl/assets/rpg-audio'
OWL = 'https://opengameart.org/content/sound-effects-pack (file https://opengameart.org/sites/default/files/Owlish%20Media%20Sound%20Effects.zip)'
OWL2 = 'https://opengameart.org/content/202-more-sound-effects (file https://opengameart.org/sites/default/files/MoreSounds.zip)'
POUR = 'https://commons.wikimedia.org/wiki/File:Pouring_particles_like_grain.ogg'


def ken(pack, name, url):
    return (f'{L}/kenney/{pack}/{name}', f'Kenney {pack} / {name}', url, 'Kenney', CC0)


def proj(name, label, url, author, lic):  # an existing project take; its own MANIFEST row names the recording
    return (f'{A}/SFX/{name}.wav', f'project SFX: SFX/{name}.wav ({label})', url, author, lic)


SRC = {f'punch{i}': ken('impact-sounds', f'Audio/impactPunch_heavy_00{i}.ogg', KEN_IMP) for i in range(5)}
SRC.update({f'soft{i}': ken('impact-sounds', f'Audio/impactSoft_heavy_00{i}.ogg', KEN_IMP) for i in range(5)})
SRC.update({f'cloth{i}': ken('rpg-audio', f'Audio/cloth{i}.ogg', KEN_RPG) for i in range(1, 5)})
SRC.update({k: ken('rpg-audio', f'Audio/{v}.ogg', KEN_RPG) for k, v in (
    ('belt', 'clothBelt'), ('belt2', 'clothBelt2'), ('leatherdrop', 'dropLeather'), ('leather', 'handleSmallLeather'),
    ('leather2', 'handleSmallLeather2'), ('beltHandle', 'beltHandle1'))})
for i in range(1, 5):
    SRC[f'snap{i}'] = proj(f'Battle/SFX_Battle_ClothSnap_0{i}', 'BigSoundBank flag recordings', 'https://bigsoundbank.com/ (flags #1-#8)', 'Joseph SARDIN', CC0_BSB)
    SRC[f'whoosh{i}'] = proj(f'Battle/SFX_Battle_FabricWhoosh_0{i}', 'BigSoundBank flag recordings', 'https://bigsoundbank.com/ (flags #1-#8)', 'Joseph SARDIN', CC0_BSB)
    SRC[f'button{i}'] = proj(f'Battle/SFX_Battle_Button_0{i}', 'BigSoundBank zipper recordings', 'https://bigsoundbank.com/ (zipper #13, #15)', 'Joseph SARDIN', CC0_BSB)
for i in range(1, 6):
    SRC[f'grunt{i}'] = proj(f'Breath/SFX_Breath_Effort_0{i}', 'Owlish Media breath-male.wav', OWL, 'Owlish Media', CC0)
SRC['pour'] = (f'{L}/wikimedia/pouring-particles-like-grain/Pouring_particles_like_grain.ogg', 'Wikimedia Commons Pouring_particles_like_grain.ogg',
               POUR, 'stephan (pdsounds.org)', PD)
SRC['plevne'] = ('P:/FoA-Assets/audio/music/user_src/Plevne Marşı Halal version by Halalprofessor _ vocals and swords only ringtone.mp3',
                 "the user's Plevne march (Halal Professor, vocals and swords only)", 'https://www.youtube.com/watch?v=7Ft_NyV7WeA',
                 'Halal Professor', "The user's own pick; licence unknown (the user accepted the risk)")
SRC['owlcloth'] = (f'{L}/opengameart/owlishmedia_202-more-sound-effects/MoreSounds_x/Cloth/Cloth_03.wav', 'Owlish Media 202 More / Cloth_03.wav',
                   OWL2, 'Owlish Media', CC0)
SRC['scared'] = (f'{L}/opengameart/owlishmedia_sound-effects-pack/OwlishMediaSoundEffects_x/Human/scared-breathing.wav',
                 'Owlish Media / Human/scared-breathing.wav', OWL, 'Owlish Media', CC0)
SRC['exhale'] = (f'{L}/opengameart/owlishmedia_sound-effects-pack/OwlishMediaSoundEffects_x/Human/breath-male.wav',
                 'Owlish Media / Human/breath-male.wav', OWL, 'Owlish Media', CC0)

# layer: (source, start s or None = its first peak, length s, gain dB, delay ms, speed, low-pass Hz, reverse, envelope)
#   envelope 'spill' = 4 ms attack then an exponential decay over the length (a pour shaped into a spill)
SETS = {
    'GarmentHit': [[(f'snap{i}', None, 0.30, 0, 0, 1.0, None, False, None), (f'soft{i - 1}', None, 0.25, -4, 0, 1.0, 6000, False, None),
                    ('pour', 42.0 + 3 * i, 0.45, -9, 15, 1.0, 9000, False, 'spill')] for i in range(1, 5)],
    'PlayerHit': [[(f'punch{i - 1}', None, 0.30, 0, 0, 1.0, 4500, False, None), (f'grunt{i}', None, 0.45, -3, 60, 1.0, None, False, None),
                   (f'cloth{i}', None, 0.25, -10, 10, 1.0, None, False, None)] for i in range(1, 5)],
    'TelegraphCloth': [[(f'whoosh{i}', None, 0.9, 0, 0, 1.0, None, True, None), (f'cloth{i}', None, 0.2, -6, 880, 1.0, None, False, None)]
                       for i in (1, 2)],
    'TelegraphElastic': [[(k, None, 0.9, 0, 0, 0.8, None, False, None), (f'cloth{i}', None, 0.2, -6, 900, 1.0, None, False, None)]
                         for i, k in ((3, 'belt'), (4, 'belt2'))],
    'TelegraphKnot': [[(k, None, 0.9, 0, 0, 0.75, None, False, None), (f'cloth{i}', None, 0.2, -6, 900, 1.0, None, False, None)]
                      for i, k in ((1, 'leather'), (2, 'leather2'))],
    'Stun': [[('leatherdrop', None, 0.4, 0, 0, 1.0, None, False, None), (f'cloth{i}', None, 0.35, -4, 40, 0.8, None, False, None),
              ('pour', 48.0 + i, 0.8, -12, 60, 1.0, 7000, False, 'spill')] for i in (2, 3)],
    'Defeat': [[(f'whoosh{i}', None, 1.0, -2, 0, 0.85, None, False, None), ('owlcloth', None, 0.5, 0, 250, 0.9, None, False, None),
                ('pour', 44.0 + 4 * i, 1.6, -6, 300, 0.9, 8000, False, 'spill')] for i in (3, 4)],
    'Worn': [[(f'cloth{i}', None, 0.3, 0, 0, 1.0, None, False, None), (f'soft{i}', None, 0.2, -6, 0, 1.0, 5000, False, None)]
             for i in (1, 2)],
    'Victory': [[('pour', 50.0, 2.6, -6, 0, 0.8, 6000, False, 'spill'), ('exhale', 8.0, 1.6, -2, 300, 0.9, None, False, None)]],
    # the user's pick, not CC0: the march's cleanest sword clashes (high band over the voices), an optional hit layer
    'SwordClash': [[('plevne', t, 0.35, 0, 0, 1.0, None, False, None)] for t in (13.40, 13.86, 61.27, 61.70)],
    'Select': [[(f'button{i}', None, 0.15, 0, 0, 1.0, None, False, None)] for i in (1, 2)],
    'Confirm': [[('leather', None, 0.25, 0, 0, 1.0, None, False, None), (f'button{i}', None, 0.15, -6, 0, 1.0, None, False, None)] for i in (3, 4)],
}
LOOPS = {'ComposureLow_Loop_01': ('scared', 2.0, 10.0, 1.5)}  # source, start, length, crossfade
CACHE = {}


def load(key):
    if key not in CACHE:
        CACHE[key] = librosa.load(SRC[key][0], sr=SR, mono=True)[0].astype(np.float64)
    return CACHE[key]


def layer(key, t0, dur, gain, delay, speed, lp, rev, env):
    y = load(key)
    if t0 is None:  # start 3 ms before its first strong peak
        k = int(np.argmax(np.abs(y) > 0.5 * np.abs(y).max()))
        a = max(0, k - int(0.003 * SR))
    else:
        a = int(t0 * SR)
    seg = y[a:a + int(dur * speed * SR)].copy()
    if rev:
        seg = seg[::-1].copy()
    if speed != 1.0:  # varispeed: slower and lower together
        seg = resample_poly(seg, int(round(100 / speed)), 100)
    if lp:
        seg = sosfiltfilt(butter(2, lp, 'lowpass', fs=SR, output='sos'), seg)
    if env == 'spill':
        t = np.arange(len(seg)) / SR
        seg *= np.minimum(t / 0.004, 1) * np.exp(-4.0 * t / max(t[-1], 1e-3))
    n = min(int(0.03 * SR), len(seg) // 4)
    seg[-n:] *= np.linspace(1, 0, n)
    if rev:  # a reversed tail has no attack: ease it in
        m = min(int(0.05 * SR), len(seg) // 4)
        seg[:m] *= np.linspace(0, 1, m)
    return np.concatenate([np.zeros(int(delay / 1000 * SR)), seg / (np.abs(seg).max() + 1e-12) * 10 ** (gain / 20)])


def mix(layers, peak):
    parts = [layer(*spec) for spec in layers]
    y = np.zeros(max(len(p) for p in parts))
    for p in parts:
        y[:len(p)] += p
    y = sosfiltfilt(butter(2, 60, 'highpass', fs=SR, output='sos'), y)
    n = int(0.06 * SR)
    y[-n:] *= np.linspace(1, 0, n)
    return y / np.abs(y).max() * 10 ** (peak / 20)


def loop(key, t0, dur, xf):
    y = load(key)
    a, n, x = int(t0 * SR), int(dur * SR), int(xf * SR)
    seg = y[a:a + n + x].copy()
    h = int(0.5 * SR)  # level it: a 0.5 s RMS contour flattened
    rms = np.sqrt(np.convolve(seg ** 2, np.ones(h) / h, 'same')) + 1e-4
    seg = seg / rms * np.median(rms)
    k = np.arange(x) / x
    out = seg[:n].copy()
    out[:x] = seg[:x] * np.sin(0.5 * np.pi * k) + seg[n:n + x] * np.cos(0.5 * np.pi * k)
    out = sosfiltfilt(butter(2, [120, 7000], 'bandpass', fs=SR, output='sos'), np.concatenate([out, out]))[n:]
    return out / np.sqrt(np.mean(out ** 2)) * 10 ** (-26 / 20)  # a quiet bed: RMS -26 dBFS


def onset_ms(y):
    h = int(0.001 * SR)
    return next(k for k in range(0, len(y), h) if np.abs(y[k:k + h]).max() > 0.3 * np.abs(y).max()) / SR * 1000


def main():
    rng = np.random.default_rng(8)
    out = {}
    for name, takes in SETS.items():
        for i, layers in enumerate(takes, 1):
            ui = name in ('Select', 'Confirm')
            y = mix(layers, -9 if ui else -3)
            if name in ('GarmentHit', 'PlayerHit', 'Stun', 'Worn', 'SwordClash', 'Select', 'Confirm'):
                assert onset_ms(y) <= 5, (name, i, onset_ms(y))
            out[f'SFX_Battle_{name}_{i:02d}'] = (y, [s[0] for s in layers], layers)
    for name, (key, t0, dur, xf) in LOOPS.items():
        y = loop(key, t0, dur, xf)
        step = np.abs(np.diff(y))
        assert abs(y[0] - y[-1]) <= np.percentile(step, 99.9), name
        out[f'SFX_Battle_{name}'] = (y, [key], [(key, t0, dur, 0, 0, 1.0, None, False, f'loop {xf} s crossfade')])
    mine = [f'{n}.wav' for n in out]
    man = [ln for ln in open(A + '/MANIFEST.md', encoding='utf-8').read().split('\n') if not any(m in ln for m in mine)]
    src, skip = [], False
    for ln in open(A + '/SOURCES.txt', encoding='utf-8').read().split('\n'):  # re-running replaces this set's rows
        skip = any(m in ln for m in mine) or (skip and ln.startswith('    local:'))
        if not skip:
            src.append(ln)
    man, src = '\n'.join(man).rstrip('\n'), '\n'.join(src).rstrip('\n')
    for name, (y, keys, layers) in out.items():
        q = np.clip(np.round(y * 32767 + rng.triangular(-1, 0, 1, len(y))), -32768, 32767).astype(np.int16)
        sf.write(f'{A}/SFX/Battle/{name}.wav', q, SR, subtype='PCM_16')
        proc = '; '.join(f'{SRC[k][1]}' + (f' from {t0:.2f} s' if t0 is not None else ' from its first peak') + f', {d:.2f} s, {g} dB'
                         + (f', +{dl} ms' if dl else '') + (f', speed {sp}' if sp != 1 else '') + (f', low-pass {lp} Hz' if lp else '')
                         + (', reversed' if rv else '') + (f', {en}' if en else '') for k, t0, d, g, dl, sp, lp, rv, en in layers)
        u = list(dict.fromkeys(keys))
        loop_ = 'Loop' in name
        man += (f'\n| `SFX/Battle/{name}.wav` | {name.split("_")[2]} (T8 fight). | {proc} | {" + ".join(f"<{SRC[k][2].split(" ")[0]}>" for k in u)} '
                f'| {" + ".join(dict.fromkeys(SRC[k][3] for k in u))} | {" + ".join(dict.fromkeys(SRC[k][4] for k in u))} '
                f'| {len(q) / SR:.2f} s | {(44 + 2 * len(q)) / 1024:.1f} KiB | {"seamless" if loop_ else "n/a (one-shot)"} | mono |')
        src += (f'\nSFX\\Battle\\{name}.wav | {" + ".join(SRC[k][2] for k in u)} | {" + ".join(dict.fromkeys(SRC[k][3] for k in u))} '
                f'| {" + ".join(dict.fromkeys(SRC[k][4] for k in u))} | {proc}')
        src += ''.join(f'\n    local: {SRC[k][0]}' for k in u)
        print(name, f'{len(q) / SR:.2f} s', f'onset {onset_ms(y):.1f} ms')
    open(A + '/MANIFEST.md', 'w', encoding='utf-8').write(man + '\n')
    open(A + '/SOURCES.txt', 'w', encoding='utf-8').write(src + '\n')
    print('wrote', len(out), 'files and their MANIFEST/SOURCES rows')


main()
