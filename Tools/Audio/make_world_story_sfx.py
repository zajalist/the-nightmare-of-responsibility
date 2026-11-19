"""Build the world/story SFX set (interactions, ambience beds, sand, presence drone, story stings) from real recordings only.
  python -I Tools/Audio/make_world_story_sfx.py
Every layer is a recording (BigSoundBank CC0, Wikimedia Commons public domain, OpenGameArt CC0, Kenney CC0, Sonniss
GDC bundle files already in the project, or the project's own Dream SFX). Processing is cuts, mono mixdown, gains,
fades, filters, varispeed (slowing a recording), envelope levelling, layering and equal-power loop crossfades.
Nothing is synthesised and no generative model is used.
Writes 16-bit 44.1 kHz WAVs (TPDF dither) to P:/FoA-Assets/audio/SFX/<Category>/, a contact sheet to
P:/FoA/Saved/HorrorShots/audio/world_story_sheet.png, and refreshes this set's rows in MANIFEST.md and its section in
SOURCES.txt (idempotent: re-running replaces them).
Self-check: rate, bit depth, channel count, duration window, no clipping, one-shot peaks -6 dBFS, quiet beds, and for
loops a seam test (sample step at the wrap no larger than the file's own 99.9th-percentile step, and 100 ms RMS on
both sides of the wrap within 3 dB)."""
import os
import re
import site
import subprocess
import sys
import tempfile
from fractions import Fraction

sys.path.append(site.getusersitepackages())  # -I drops user site; numpy/scipy/soundfile/matplotlib live there (trusted)
import numpy as np  # noqa: E402
import soundfile as sf  # noqa: E402
from scipy.signal import butter, resample_poly, sosfiltfilt  # noqa: E402

SR = 44100
A = 'P:/FoA-Assets/audio'
L = A + '/_libraries'
SB = L + '/sonniss'
BSB = L + '/bigsoundbank'
PNG = 'P:/FoA/Saved/HorrorShots/audio/world_story_sheet.png'
RNG = np.random.default_rng(20261109)

# ---- sources: key -> (path, label for MANIFEST, source URL, author, licence) ----
CC0_BSB = "CC0 1.0 (BigSoundBank: 'CC0 (public domain): Free and royalty-free')"
SON_LIC = 'Sonniss #GameAudioGDC Bundle License (royalty-free, commercial use, no attribution required)'
CC0 = 'CC0 1.0 Universal'


def bsb(num, slug, ext, author='Joseph SARDIN', title=None):
    page = f'https://bigsoundbank.com/s{num}.html' if ext == 'wav' else f'https://bigsoundbank.com/{slug}-s{num}.html'
    sub = {'flac': 'flac', 'aiff': 'aiff', 'wav': 'bwf-en'}[ext]
    return (f'{BSB}/s{num}_{slug}/{num}.{ext}', f'BigSoundBank #{int(num)} {title or slug} / {num}.{ext}',
            f'{page} (file https://bigsoundbank.com/UPLOAD/{sub}/{num}.{ext})', author, CC0_BSB)


def son(bundle_dir, pack, name, zip_url, author):
    return (f'{SB}/{bundle_dir}/{pack}/{name}', f'Sonniss GDC bundle: {pack} / {name}', zip_url, author, SON_LIC)


Z17_3 = 'https://downloads.sonniss.com/Sonniss.com%20-%20GDC%202017%20-%20Game%20Audio%20Bundle%20Part%203of9.zip'
G17_3 = 'Sonniss.com_-_GDC_2017_-_Game_Audio_Bundle_Part_3of9/Sonniss.com - GDC 2017 - Game Audio Bundle Part 3of9'
RD = L + '/opengameart/rubberduck_75-cc0-breaking-falling-hit/sfx_breaking_and_falling_x'
RD_URL = ('https://opengameart.org/content/75-cc0-breaking-falling-hit-sfx '
          '(file https://opengameart.org/sites/default/files/sfx_breaking_and_falling.zip)')


def rd(name):
    return (f'{RD}/{name}', f'OpenGameArt rubberduck "75 CC0 breaking / falling / hit sfx" / {name}', RD_URL, 'rubberduck', CC0)


def ken(pack, name):
    return (f'{L}/kenney/{pack}/Audio/{name}', f'Kenney {pack} / {name}', f'https://kenney.nl/assets/{pack}', 'Kenney (kenney.nl)', CC0)


def dream(name):
    return (f'{A}/SFX/Dream/{name}.wav', f'project SFX: SFX/Dream/{name}.wav (sources in its MANIFEST row)', '(see the MANIFEST row of ' + name + ')',
            '(see that row)', '(see that row)')


SRC = {
    'grind1': bsb('0322', 'petit-grincement-metal-1', 'aiff', 'DavidGreck', 'Small metal grinding #1'),
    'grind2': bsb('0323', 'small-metal-grinding-2', 'aiff', 'DavidGreck', 'Small metal grinding #2'),
    'barn_unlock': bsb('1539', 'barn-lock-unlocking', 'flac', title='Barn lock, unlocking'),
    'barn_lock': bsb('1540', 'barn-lock-locking', 'flac', title='Barn lock, locking'),
    'knob': bsb('0617', 'grinding-doorknob', 'aiff', title='Grinding doorknob'),
    'clunk0': ken('impact-sounds', 'impactMetal_light_001.ogg'),
    'clunk2': ken('impact-sounds', 'impactMetal_light_004.ogg'),
    'thud0': ken('impact-sounds', 'impactWood_light_000.ogg'),
    'thud1': ken('impact-sounds', 'impactWood_light_001.ogg'),
    'screw': son(G17_3, 'Digital Rain Lab - Woodwork', 'screwdriver screwing 4 mono.wav', Z17_3, 'Digital Rain Lab'),
    'nail': bsb('0461', 'nail-falling-on-tiled-floor', 'aiff', title='Nail falling on tiled floor'),
    'rustle_pile': son(G17_3, 'Double Trouble Audio - Wood Impacts and Debris', 'Rustles - Pile, Debris 22.wav', Z17_3, 'Double Trouble Audio'),
    'rd_fall1': rd('bfh1_falling_01.ogg'), 'rd_fall3': rd('bfh1_falling_03.ogg'), 'rd_fall4': rd('bfh1_falling_04.ogg'),
    'rd_fall7': rd('bfh1_falling_07.ogg'), 'rd_wood1': rd('bfh1_wood_falling_01.ogg'), 'rd_wood2': rd('bfh1_wood_falling_02.ogg'),
    'rd_misc6': rd('bfh1_misc_06.ogg'), 'rd_metal3': rd('bfh1_metal_falling_03.ogg'),
    'vib': bsb('1034', 'phone-vibrating-wood', 'wav', title='Mobile vibrator without protective shell'),
    'plate1643': bsb('1643', 'broken-plate', 'wav', title='Broken plate #1'),
    'plate1645': bsb('1645', 'broken-plate', 'wav', title='Broken plate #3'),
    'plate1646': bsb('1646', 'broken-plate', 'wav', title='Broken plate #4'),
    'plank0': ken('impact-sounds', 'impactPlank_medium_000.ogg'),
    'plank2': ken('impact-sounds', 'impactPlank_medium_002.ogg'),
    'plank4': ken('impact-sounds', 'impactPlank_medium_004.ogg'),
    # downloaded by the player-foley lane into a folder without a slug
    'bare': (f'{BSB}/s0181/0181.wav', 'BigSoundBank #181 Footsteps (barefoot on wooden stairs) / 0181.wav',
             'https://bigsoundbank.com/s0181.html (file https://bigsoundbank.com/UPLOAD/bwf-en/0181.wav)', 'Joseph SARDIN', CC0_BSB),
    'paper': bsb('1251', 'news-paper-manipulations', 'flac', title='News paper, manipulations'),
    'tshirt29': son('Sonniss.com-GDC2026-GameAudioBundle3of5', 'InMotionAudio - Foley T-Shirt',
                    'FOLYClth_ClothMovement29_InMotionAudio_FoleyT-Shirt.wav',
                    'https://downloads.sonniss.com/Sonniss.com-GDC2026-GameAudioBundle3of5.zip', 'InMotionAudio'),
    'boiler': (f'{L}/wikimedia/boiler-gas-heater/Boiler_gas_heater.ogg', 'Wikimedia Commons / Boiler gas heater.ogg (PDSounds #164)',
               'https://commons.wikimedia.org/wiki/File:Boiler_gas_heater.ogg', 'stephan (pdsounds.org)', 'Public domain'),
    'lentils': (f'{L}/wikimedia/pouring-particles-like-grain/Pouring_particles_like_grain.ogg',
                'Wikimedia Commons / Pouring particles like grain.ogg (PDSounds #552: lentils poured into a plastic tub)',
                'https://commons.wikimedia.org/wiki/File:Pouring_particles_like_grain.ogg', 'stephan (pdsounds.org)', 'Public domain'),
    'relay': (f'{L}/wikimedia/heating-system-turning-on/Sound_of_heating_system_turning_on.ogg',
              'Wikimedia Commons / Sound of heating system turning on.ogg',
              'https://commons.wikimedia.org/wiki/File:Sound_of_heating_system_turning_on.ogg', 'MKFI', 'Public domain'),
    'birds': bsb('1906', 'birds-waking-4', 'flac', title='Birds waking #4'),
    'traffic': son('Sonniss.com_-_GDC_2018_-_Game_Audio_Bundle_Part_8of8/Sonniss.com - GDC 2018 - Game Audio Bundle Part 8of8',
                   'West Wolf - Night Cityscapes', 'NC_63_Night_City_Big Street_Light Traffic_Hum_ORTF_(96_24).wav',
                   'https://downloads.sonniss.com/Sonniss.com%20-%20GDC%202018%20-%20Game%20Audio%20Bundle%20Part%208of8.zip', 'West Wolf'),
    'trickle': son('Sonniss.com-GDC2023-GameAudioBundle3of14', 'Justsoundeffects - Stones and Debris',
                   'DIRTCrsh_Stone Sand Trickle Reverberant 01_JSE_SD.wav',
                   'https://downloads.sonniss.com/Sonniss.com-GDC2023-GameAudioBundle3of14.zip', 'Justsoundeffects'),
    'rock': son('Sonniss.com-GDC2023-GameAudioBundle8of14', 'Pole Position Production - The Stone & Sand Library',
                'Small Crushed Rock - DROP - Thick - Stereo.wav',
                'https://downloads.sonniss.com/Sonniss.com-GDC2023-GameAudioBundle8of14.zip', 'Pole Position Production'),
    'lungs': son('Sonniss.com_-_GDC_2016-_Game_Audio_Bundle_Part_5of6', 'ShapingWaves -  STETHOSCOPE',
                 'SW002_Stethoscope_Chest_Lungs_Breathing_Slow_Low.wav',
                 'https://downloads.sonniss.com/Sonniss.com%20-%20GDC%202016-%20Game%20Audio%20Bundle%20Part%205of6.zip', 'ShapingWaves'),
    'heart': son('Sonniss.com_-_GDC_2016-_Game_Audio_Bundle_Part_5of6', 'ShapingWaves -  STETHOSCOPE',
                 'SW002_Stethoscope_Chest_Heart_Heartbeat_Blood_Flow_A.wav',
                 'https://downloads.sonniss.com/Sonniss.com%20-%20GDC%202016-%20Game%20Audio%20Bundle%20Part%205of6.zip', 'ShapingWaves'),
    'bowl_sing': bsb('1109', 'tibetan-bowl-singing', 'flac', title='Tibetan bowl singing'),
    'bowl_struck': bsb('1110', 'tibetan-bowl-struck', 'flac', title='Tibetan bowl struck #1'),
    'rogue_door': son('Sonniss.com-GDC2024-GameAudioBundle6of9', 'Rogue Waves - Creaking Door',
                      'DOORCreak_Wooden Door, Opening and Closing 09_RogueWaves_CreakingDoor.wav',
                      'https://downloads.sonniss.com/Sonniss.com-GDC2024-GameAudioBundle6of9.zip', 'Rogue Waves'),
    'ww_door': son('Sonniss.com-GDC2023-GameAudioBundle14of14', 'West Wolf - Quiet School Ambiences',
                   'DOORWood_School Classroom-Door-CD03, Old Wooden Door, Squeaky, Opening, Closing, Recorded From The Classroom_WWA_QSRT_Neumann KM184_XY_3.wav',
                   'https://downloads.sonniss.com/Sonniss.com-GDC2023-GameAudioBundle14of14.zip', 'West Wolf'),
    'tape_rewind': dream('SFX_Dream_TapeRewind_01'), 'tape_stop1': dream('SFX_Dream_TapeStop_01'),
    'tape_scrub1': dream('SFX_Dream_TapeScrub_01'), 'tape_scrub2': dream('SFX_Dream_TapeScrub_02'),
    'swell2': dream('SFX_Dream_ReverseSwell_02'), 'swell3': dream('SFX_Dream_ReverseSwell_03'),
}

_decoded = {}


def path_of(key):
    """A path libsndfile can open; Ogg files with an extra data stream (Commons/PDSounds) are decoded once with ffmpeg."""
    p = SRC[key][0]
    try:
        sf.info(p)
        return p
    except Exception:
        if key not in _decoded:
            t = os.path.join(tempfile.mkdtemp(), 'dec.wav')
            subprocess.run(['ffmpeg', '-v', 'error', '-i', p, '-vn', '-c:a', 'pcm_f32le', t], check=True)
            _decoded[key] = t
        return _decoded[key]


def read(key, t0, dur):
    """[n, ch] float64 from t0 for dur seconds of the source, at its own rate (reads only that span)."""
    with sf.SoundFile(path_of(key)) as f:
        sr = f.samplerate
        a, n = int(t0 * sr), int(dur * sr) + 64
        assert 0 <= a and a + n <= f.frames + 64, (key, t0, dur, 'outside the source', f.frames / sr)
        f.seek(a)
        return f.read(n, dtype='float64', always_2d=True), sr


def envelope(key, hop):
    """Per-hop RMS dB of a whole (long) source, streamed."""
    with sf.SoundFile(path_of(key)) as f:
        n = int(hop * f.samplerate)
        return np.array([db(np.sqrt(np.mean(b ** 2))) for b in f.blocks(blocksize=n, dtype='float64', always_2d=True) if len(b) == n])


def cut(key, t0, dur, ch=1, speed=1.0):
    """dur seconds of OUTPUT at 44.1 kHz from source time t0, played at `speed` (0.5 = an octave down, twice as long).
    ch=1 mixes to mono, ch=2 keeps stereo (a mono source is duplicated)."""
    y, sr = read(key, t0, dur * speed)
    y = y.mean(axis=1, keepdims=True) if ch == 1 else (y if y.shape[1] == 2 else np.repeat(y[:, :1], 2, axis=1))
    r = Fraction(int(round(SR / speed)), sr).limit_denominator(2000)
    if r != 1:
        y = resample_poly(y, r.numerator, r.denominator, axis=0)
    n = int(round(dur * SR))
    assert len(y) >= n, (key, 'short', len(y), n)
    return y[:n].copy()


def filt(y, hp=None, lp=None, order=2):
    if hp:
        y = sosfiltfilt(butter(order, hp, 'highpass', fs=SR, output='sos'), y, axis=0)
    if lp:
        y = sosfiltfilt(butter(order, lp, 'lowpass', fs=SR, output='sos'), y, axis=0)
    return y


def fade(y, fin=0.004, fout=0.08, shape_in='lin'):
    y = y.copy()
    n = max(int(fin * SR), 1)
    g = np.linspace(0, 1, n)
    y[:n] *= (np.sin(g * np.pi / 2) ** 2 if shape_in == 'sin' else g)[:, None]
    n = max(int(fout * SR), 1)
    y[-n:] *= (np.linspace(1, 0, n) ** 2)[:, None]
    return y


def db(v):
    return 20 * np.log10(v + 1e-12)


def peak_to(y, d):
    return y * 10 ** (d / 20) / np.abs(y).max()


def rms_to(y, d):
    return y * 10 ** (d / 20) / np.sqrt(np.mean(y ** 2))


def bed_level(y, rms, max_peak=-8.0):
    """RMS target for a bed, pulled down if a transient would pass max_peak (beds stay quiet, never clip)."""
    y = rms_to(y, rms)
    return y * min(1.0, 10 ** (max_peak / 20) / np.abs(y).max())


def mix(length, ch, *layers):
    """layers: (signal, offset s, gain dB). Signals are converted to ch channels."""
    out = np.zeros((int(round(length * SR)), ch))
    for s, off, g in layers:
        s = s if s.shape[1] == ch else (np.repeat(s, ch, axis=1) if s.shape[1] == 1 else s.mean(axis=1, keepdims=True))
        i = int(round(off * SR))
        n = min(len(s), len(out) - i)
        out[i:i + n] += s[:n] * 10 ** (g / 20)
    return out


def level(y, win=2.0):
    """Divide out the slow loudness contour (win-second RMS) so a swelling source reads as a steady bed."""
    n = int(win * SR)
    c = np.concatenate([[0], np.cumsum(np.pad((y ** 2).mean(axis=1), (n // 2, n - n // 2), mode='reflect'))])
    e = np.sqrt(np.maximum((c[n:n + len(y)] - c[:len(y)]) / n, 0)) + 1e-9  # centred moving RMS (cumsum, not O(N*n))
    return y / (e / np.median(e))[:, None]


def chain(parts, xf):
    """Join parts with equal-power crossfades of xf seconds."""
    n = int(xf * SR)
    g = np.linspace(0, np.pi / 2, n)[:, None]
    out = parts[0]
    for p in parts[1:]:
        out = np.concatenate([out[:-n], out[-n:] * np.cos(g) + p[:n] * np.sin(g), p[n:]])
    return out


def loopify(y, length, xf):
    """Seamless loop of `length` s from y (needs length+xf s): the material after the loop end is crossfaded into its start."""
    n, x = int(round(length * SR)), int(round(xf * SR))
    assert len(y) >= n + x, ('loop source too short', len(y) / SR, length + xf)
    g = np.linspace(0, np.pi / 2, x)[:, None]
    out = y[:n].copy()
    out[:x] = y[:x] * np.sin(g) + y[n:n + x] * np.cos(g)
    return out


def q16(y):
    """TPDF dither to 16 bit; returns the quantised float signal that will be written."""
    d = (RNG.random(y.shape) - RNG.random(y.shape)) / 32767
    q = np.round((y + d) * 32767)
    assert np.abs(q).max() <= 32767, 'clipping'
    return q / 32767


def seam(y):
    """(wrap sample step / the file's 99.9th-pct step, [(RMS dB jump across the wrap, 95th pct of that jump inside the file)
    for 0.5 s, 2 s and up to 6 s windows]). Short windows catch clicks and local bumps, long windows catch level drift that a
    strongly modulated texture (breathing, chirps, grains) would hide at short scales. Passes when the wrap is no rougher than the
    material itself at both scales (or under 3 dB)."""
    step = np.abs(np.diff(y, axis=0)).max(axis=1)
    jump = np.abs(y[0] - y[-1]).max()
    r = lambda a: db(np.sqrt(np.mean(a ** 2)))
    lv = []
    for w in (0.5, 2.0, min(6.0, len(y) / SR / 3)):
        n, h = int(w * SR), int(0.1 * SR)
        inner = [abs(r(y[i - n:i]) - r(y[i:i + n])) for i in range(n, len(y) - n, h)]
        lv.append((abs(r(y[-n:]) - r(y[:n])), float(np.percentile(inner, 95))))
    return jump / np.percentile(step, 99.9), lv


def seam_ok(s):
    return s[0] < 1.0 and all(j < max(3.0, p95) for j, p95 in s[1])


OUT = []  # (relpath, signal, kind, what, [source keys], processing, (dmin, dmax))


PEAK = {}  # one-shots whose target peak is not -6 dBFS


def emit(rel, y, kind, what, keys, proc, dwin, peak=-6.0):
    OUT.append((rel, y, kind, what, keys, proc, dwin))
    PEAK[rel] = peak


def one_shot_mono(y, peak=-6.0, fin=0.004, fout=0.08, hp=60, lp=None):
    y = filt(y, hp, lp)
    return peak_to(fade(y, fin, fout), peak)


# ================= Interactions (mono one-shots, peak -6 dBFS) =================
for i, (k, t0, d) in enumerate([('grind1', 0.08, 0.56), ('grind1', 0.88, 0.80), ('grind2', 1.14, 0.74)], 1):
    emit(f'Props/SFX_Props_HangerRail_{i:02d}.wav', one_shot_mono(cut(k, t0, d), hp=250, fout=0.06), 'mono',
         'Wire hanger hook scraping along a metal rail (small metal-on-metal grind foley).', [k],
         f'cut {t0:.2f}-{t0 + d:.2f} s, mono, high-pass 250 Hz, 4 ms fade-in, 60 ms fade-out, peak -6 dBFS', (0.4, 1.0))

emit('Door/SFX_Door_LatchSlide_01.wav', one_shot_mono(cut('barn_unlock', 0.10, 1.90), fout=0.15), 'mono',
     'Old barn-door bolt lifted and slid free, ending on the stop.', ['barn_unlock'],
     'cut 0.10-2.00 s, high-pass 60 Hz, 4 ms fade-in, 150 ms fade-out, peak -6 dBFS', (1.0, 2.5))
emit('Door/SFX_Door_LatchSlide_02.wav', one_shot_mono(cut('barn_lock', 0.56, 1.06), fout=0.12), 'mono',
     'Old barn-door bolt sliding and catching (shorter throw).', ['barn_lock'],
     'cut 0.56-1.62 s, high-pass 60 Hz, 4 ms fade-in, 120 ms fade-out, peak -6 dBFS', (0.6, 2.0))

ho1 = mix(1.25, 1, (fade(filt(cut('knob', 11.94, 0.62), 80), 0.004, 0.08), 0, 0),
          (fade(filt(cut('thud0', 0, 0.26), 80), 0.002, 0.08), 0.66, -1),
          (fade(filt(cut('clunk0', 0, 0.24), 80, 3500), 0.002, 0.10), 0.665, -8))
emit('Door/SFX_Door_HandleOff_01.wav', one_shot_mono(ho1, fout=0.25), 'mono',
     'Edit of real recordings: a loose metal doorknob grinds and rattles, then drops off with a clunk.', ['knob', 'thud0', 'clunk0'],
     'doorknob cut 11.94-12.56 s; clunk at 0.66 s = Kenney light wood impact (-1 dB) plus light metal impact (low-passed 3.5 kHz, -8 dB); '
     'high-pass 80 Hz, peak -6 dBFS', (0.6, 1.6))
ho2 = mix(1.10, 1, (fade(filt(cut('knob', 6.92, 0.58), 80), 0.004, 0.06), 0, 0),
          (fade(filt(cut('thud1', 0, 0.26), 80), 0.002, 0.08), 0.60, -1),
          (fade(filt(cut('clunk2', 0, 0.20), 80, 3500), 0.002, 0.08), 0.605, -8))
emit('Door/SFX_Door_HandleOff_02.wav', one_shot_mono(ho2, fout=0.25), 'mono',
     'Edit of real recordings: the loose knob squeaks and rattles on its spindle, then clunks onto the floor.', ['knob', 'thud1', 'clunk2'],
     'doorknob cut 6.92-7.50 s; clunk at 0.60 s = Kenney light wood impact (-1 dB) plus light metal impact (low-passed 3.5 kHz, -8 dB); '
     'high-pass 80 Hz, peak -6 dBFS', (0.6, 1.6))

for i, (t0, d) in enumerate([(0.04, 0.95), (1.55, 0.90), (3.05, 0.80), (5.42, 1.00)], 1):
    emit(f'Props/SFX_Props_ScrewTurn_{i:02d}.wav', one_shot_mono(cut('screw', t0, d), hp=120, fout=0.08), 'mono',
         'Hand screwdriver turning a screw in wood (single turn, scrape and squeak).', ['screw'],
         f'cut {t0:.2f}-{t0 + d:.2f} s, high-pass 120 Hz, 4 ms fade-in, 80 ms fade-out, peak -6 dBFS', (0.4, 1.2))

for i, (t0, d) in enumerate([(3.66, 0.95), (9.20, 1.05), (12.52, 1.00), (15.48, 0.85)], 1):
    emit(f'Props/SFX_Props_ScrewDrop_{i:02d}.wav', one_shot_mono(filt(cut('nail', t0, d), None, 6000, order=4), hp=200, fout=0.12), 'mono',
         'Small screw-sized metal piece dropping and bouncing (nail on a hard floor, low-passed to dull the tile ring).', ['nail'],
         f'cut {t0:.2f}-{t0 + d:.2f} s, high-pass 200 Hz, low-pass 6 kHz (4th order), 4 ms fade-in, 120 ms fade-out, peak -6 dBFS', (0.5, 1.5))


def piece(k, lp=9000):
    y = cut(k, 0, sf.info(path_of(k)).duration - 0.01)
    y = y[:np.nonzero(np.abs(y).max(axis=1) > 1e-4)[0][-1] + 1]  # some takes are gated to digital silence mid-tail:
    return fade(filt(y, 80, lp), 0.003, 0.2)  # end the fade at the gate so no tail is chopped off


deb = [
    ([('rustle_pile', 0, 0), ('rd_wood1', 0.42, -4), ('rd_fall3', 0.95, -9)], 1.80),
    ([('rd_fall4', 0, 0), ('rd_wood2', 0.78, -5), ('rd_misc6', 1.35, -11)], 2.40),
    ([('rd_fall1', 0, 0), ('rd_fall7', 0.52, -5), ('rd_metal3', 1.48, -13)], 2.00),
]
for i, (layers, length) in enumerate(deb, 1):
    y = mix(length, 1, *[(piece(k), off, g) for k, off, g in layers])
    emit(f'Wardrobe/SFX_Wardrobe_Debris_{i:02d}.wav', one_shot_mono(y, hp=80, fout=0.25), 'mono',
         'Edit of real recordings: wood debris and small items settling after the wardrobe falls.', [k for k, *_ in layers],
         'layers ' + ', '.join(f'{os.path.basename(SRC[k][0])} @ {off:.2f} s {g:+d} dB' for k, off, g in layers)
         + '; each whole take up to its gate, low-passed 9 kHz, 200 ms fade-out; high-pass 80 Hz, 250 ms fade-out, peak -6 dBFS', (1.0, 3.0))

for i, (t0, d) in enumerate([(0.30, 1.45), (3.58, 1.40), (10.32, 1.40), (22.36, 1.45)], 1):
    emit(f'Props/SFX_Props_PaperRustle_{i:02d}.wav', one_shot_mono(cut('paper', t0, d), hp=100, fout=0.15), 'mono',
         'Paper notebook handled on a desk (rustle and page flex).', ['paper'],
         f'cut {t0:.2f}-{t0 + d:.2f} s, high-pass 100 Hz, 4 ms fade-in, 150 ms fade-out, peak -6 dBFS', (0.5, 2.0))

# third variant: reuse Bed/SFX_Bed_Sheets_01 (the same cotton T-shirt foley)
for i, (k, t0, d) in enumerate([('tshirt29', 0.02, 0.76), ('tshirt29', 0.78, 0.62)], 1):
    emit(f'Props/SFX_Props_ShirtPickup_{i:02d}.wav', one_shot_mono(cut(k, t0, d), hp=80, fout=0.08), 'mono',
         'Cotton shirt picked up (cloth lift and swish).', [k],
         f'cut {t0:.2f}-{t0 + d:.2f} s, mono, high-pass 80 Hz, 4 ms fade-in, 80 ms fade-out, peak -6 dBFS', (0.3, 1.2))

emit('Door/SFX_Door_FinalOpen_01.wav',
     one_shot_mono(mix(3.05, 1, (peak_to(fade(filt(cut('rogue_door', 0.10, 0.55), 60), 0.004, 0.10), -8), 0, 0),
                       (peak_to(fade(filt(cut('ww_door', 3.25, 2.60), 60), 0.02, 0.6), -6), 0.42, 0)), fout=0.4),
     'mono', 'Edit of real recordings: the bedroom door latch releases, then the old door swings open on a slow squeaky creak.',
     ['rogue_door', 'ww_door'],
     'latch cut 0.10-0.65 s (Rogue Waves) at 0 s; slow creak cut 3.25-5.85 s (West Wolf old wooden door) at 0.42 s; '
     'high-pass 60 Hz, 400 ms fade-out, peak -6 dBFS', (2.0, 4.0))

# Nightstand alarm buzz: iPhone vibrating on a wooden table. Each recorded buzz is ~1.0 s with digital silence between;
# a pulse keeps a buzz's real attack (first `on` s) and its real release (last 0.2 s), joined with a 30 ms crossfade.
VIB_UNITS = [(0.30, 1.47), (2.30, 3.47), (4.30, 5.49), (6.32, 7.49), (8.30, 9.47), (10.32, 11.47)]  # (onset, end of decay)


def buzz(u, on):
    s, e = VIB_UNITS[u]
    return chain([cut('vib', s, on), cut('vib', e - 0.20, 0.20)], 0.03)


for i, pattern in enumerate([[(0, 0.38), 0.22, (1, 0.38), 0.22, (2, 0.43)],
                             [(3, 0.33), 0.28, (4, 0.38), 0.20, (5, 0.33)]], 1):
    parts, desc = [], []
    for item in pattern:
        if isinstance(item, tuple):
            parts.append(buzz(*item))
            desc.append(f'buzz {VIB_UNITS[item[0]][0]:.2f} s (attack {item[1]:.2f} s + release)')
        else:
            parts.append(np.zeros((int(item * SR), 1)))
            desc.append(f'{item * 1000:.0f} ms gap')
    y = np.concatenate(parts)
    emit(f'Phone/SFX_Phone_NightstandBuzz_{i:02d}.wav', one_shot_mono(y, peak=-4.0, hp=60, fout=0.03), 'mono',
         'Morning alarm: a smartphone vibrating hard against a wooden nightstand, three pulses (motor buzz with the wood rattling).',
         ['vib'], '; '.join(desc) + '; high-pass 60 Hz, 4 ms fade-in, peak -4 dBFS', (2.0, 3.0), peak=-4.0)

# Vase break: a real ceramic plate smashing (BigSoundBank, on concrete) with a low wooden plank thud under the first
# impact so it lands on floorboards; the recorded shard scatter is kept to the end.
for i, (k, t0, d, pk) in enumerate([('plate1646', 0.0, 2.35, 'plank0'), ('plate1643', 0.04, 1.36, 'plank2'),
                                    ('plate1645', 0.10, 1.36, 'plank4')], 1):
    smash = filt(cut(k, t0, d), 60)
    hit = int(np.argmax(np.abs(smash[:, 0]) > 0.3 * np.abs(smash).max())) / SR  # first strong transient = floor contact
    y = mix(d, 1, (smash, 0, 0), (fade(filt(cut(pk, 0, 0.5), 40, 600), 0.002, 0.15), max(hit - 0.004, 0), -6))
    emit(f'Props/SFX_Props_VaseBreak_{i:02d}.wav', one_shot_mono(y, hp=40, fout=0.2), 'mono',
         'Edit of real recordings: a ceramic vase smashing on the floorboards, with the shard scatter (a real plate break plus a low '
         'wooden plank thud under the impact).', [k, pk],
         f'plate break cut {t0:.2f}-{t0 + d:.2f} s, high-pass 60 Hz; Kenney plank impact (band 40-600 Hz, -6 dB) at the first '
         f'transient ({hit:.3f} s); 4 ms fade-in, 200 ms fade-out, peak -6 dBFS', (1.0, 2.5))

# Bare feet: a real barefoot recording (BigSoundBank #181, a man climbing old wooden stairs barefoot, the boards creaking).
def footfall(key, a, b):
    """Source time 15 ms before the loudest 5 ms frame between a and b (the foot landing, not a creak before it)."""
    y = cut(key, a, b - a)[:, 0]
    n = int(0.005 * SR)
    e = np.convolve(y ** 2, np.ones(n) / n, mode='same')
    return a + max(int(np.argmax(e)) - int(0.015 * SR), 0) / SR


# steps 5 and 6 end before the next foot lands (0.22 s after the footfall)
for i, (a, b, d) in enumerate([(0.62, 1.06, 0.34), (2.70, 3.08, 0.34), (3.40, 3.74, 0.34), (4.04, 4.42, 0.34),
                               (6.04, 6.44, 0.21), (7.26, 7.68, 0.21)], 1):
    t0 = footfall('bare', a, b)
    emit(f'Footsteps/SFX_Footsteps_BareWood_{i:02d}.wav', one_shot_mono(cut('bare', t0, d), peak=-8.0, hp=50, fout=0.07),
         'mono', 'Bare foot on old wooden boards: soft skin contact with a little board give.', ['bare'],
         f'cut {t0:.3f}-{t0 + d:.3f} s (15 ms before the footfall), high-pass 50 Hz, 4 ms fade-in, 70 ms fade-out, peak -8 dBFS',
         (0.2, 0.5), peak=-8.0)

# ================= Ambience beds (stereo loops) =================
# Radiator: the steady burn of a gas boiler (public domain) as a faint pipe hiss, alternately forward and reversed so the
# 5.8 s burn fills the loop, plus sparse low-passed relay/metal ticks. No CC0 radiator recording was found (see report).
burn = cut('boiler', 5.8, 5.8, ch=2)  # the even part of the burn (4-5.5 s is 4 dB quieter and dipped at every join)
bed = chain([burn, burn[::-1]] * 3, 1.0)
bed = level(filt(bed, 60, 6000), 2.0)
bed = rms_to(bed, -40)
tick_a = fade(filt(cut('relay', 0.0, 0.16, ch=2), 150, 3000), 0.002, 0.06)
tick_b = fade(filt(cut('relay', 1.08, 0.16, ch=2), 150, 3000), 0.002, 0.06)
ticks = [(tick_a, 2.9, -27, 0.7), (tick_b, 7.6, -31, 0.3), (tick_a, 8.05, -34, 0.35), (tick_b, 13.4, -29, 0.8),
         (tick_a, 18.2, -32, 0.2), (tick_b, 21.9, -28, 0.6), (tick_a, 22.3, -35, 0.6), (tick_b, 26.0, -33, 0.4)]
rad = bed[:int(29.0 * SR)].copy()
for t, off, pk, pan in ticks:
    s = peak_to(t, pk)
    i = int(off * SR)
    rad[i:i + len(s), 0] += s[:, 0] * np.cos(pan * np.pi / 2) * 1.41
    rad[i:i + len(s), 1] += s[:, 1] * np.sin(pan * np.pi / 2) * 1.41
rad = bed_level(loopify(rad, 27.0, 2.0), -34)
emit('Ambience/SFX_Ambience_Radiator_Loop_01.wav', rad, 'loop',
     'Edit of real recordings: faint heating hiss (a gas boiler burning, heard through the pipes) with sparse metallic ticks. '
     'Quiet loop.', ['boiler', 'relay'],
     'boiler burn cut 5.8-11.6 s, alternated forward/reversed with 1 s equal-power crossfades, high-pass 60 Hz, low-pass 6 kHz, '
     'levelled with a 2 s RMS contour; '
     'eight relay clicks (cuts 0.00-0.16 and 1.08-1.24 s, band 150 Hz-3 kHz) peaking 5-13 dB above the bed RMS, panned; '
     '2 s loop crossfade, loop RMS -34 dBFS', (20, 40))

# Outside: the quietest 32 s of a CC0 dawn chorus plus far traffic hum.
r05 = envelope('birds', 0.5)
win = int(32 / 0.5)
lo = int(180 / 0.5)  # search the second half, where the dawn chorus is more distant
pw = 10 ** (r05 / 10)
edge = lambda k: abs(db(np.sqrt(pw[k:k + 12].mean())) - db(np.sqrt(pw[k + 48:k + 60].mean())))  # first vs last 6 s of the 30 s loop
quiet = {k: np.percentile(r05[k:k + win], 95) for k in range(lo, len(r05) - win)}
best = min((k for k in quiet if quiet[k] < min(quiet.values()) + 2.0), key=edge)  # among the quietest, the most even wrap
t_birds = best * 0.5
birds = rms_to(filt(cut('birds', t_birds, 32.0, ch=2), 50), -30)
traffic = rms_to(filt(cut('traffic', 100.0, 32.0, ch=2), 40, 600), -41)
out_bed = bed_level(loopify(birds + traffic, 30.0, 2.0), -29)
emit('Ambience/SFX_Ambience_Outside_Loop_01.wav', out_bed, 'loop',
     'Early-morning outdoors through an open door: distant dawn birds, soft air, far traffic hum. Two real recordings layered.',
     ['birds', 'traffic'],
     f'dawn chorus cut {t_birds:.1f}-{t_birds + 32:.1f} s (after 180 s, among the quietest stretches the one whose first and last 6 s match in level), high-pass 50 Hz; '
     'traffic hum cut 100-132 s, band 40-600 Hz, 11 dB under the birds; 2 s loop crossfade, loop RMS -29 dBFS', (20, 40))

# ================= Sand and horror =================
pour = level(filt(cut('lentils', 41.4, 14.5, ch=2), 300, 14000), 2.0)
r100 = lambda a: db(np.sqrt(np.mean(a ** 2)))
k = int(0.1 * SR)
hiss_len = min(np.arange(12.0, 13.0, 0.01), key=lambda s: abs(r100(pour[int(s * SR) - k:int(s * SR)]) - r100(pour[int(s * SR):int(s * SR) + k])))
hiss = bed_level(loopify(pour, hiss_len, 1.5), -30)  # loop end placed where the pour is locally even (grain bursts vary 5 dB)
emit('Sand/SFX_Sand_Hiss_Loop_01.wav', hiss, 'loop',
     'Fine grain hiss and flow: a steady pour of lentils into a tub, as a seamless stereo loop for the black sand.', ['lentils'],
     f'cut 41.4-55.9 s (the steadiest pour), band 300 Hz-14 kHz, levelled with a 2 s RMS contour, {hiss_len:.2f} s loop with a 1.5 s crossfade, '
     'RMS -30 dBFS', (10, 20))

for i, t0 in enumerate([21.62, 49.86], 1):
    emit(f'Sand/SFX_Sand_Crumble_{i:02d}.wav', one_shot_mono(cut('rock', t0, 1.70), hp=90, lp=12000, fout=0.45), 'mono',
         'A small object crumbling into sand: gritty collapse with a trickling tail.', ['rock'],
         f'cut {t0:.2f}-{t0 + 1.7:.2f} s, mono, band 90 Hz-12 kHz, 4 ms fade-in, 450 ms fade-out, peak -6 dBFS', (1.0, 2.0))

# Presence: a stethoscope recording of slow breathing an octave down (two different stretches for L and R) under a
# singing bowl's bowed tone two octaves down (bowed metal), levelled to a steady bed. Seamless, quiet.
lungL = filt(cut('lungs', 3.0, 28.0, speed=0.5), 25, 500)
lungR = filt(cut('lungs', 16.5, 28.0, speed=0.5), 25, 500)
lung = level(np.concatenate([lungL, lungR], axis=1), 3.0)
bowl = level(filt(cut('bowl_sing', 1.2, 28.0, speed=0.25), 30, 450), 3.0)
pres = rms_to(lung, -33) + rms_to(np.repeat(bowl, 2, axis=1), -37)
pres = loopify(pres, 26.0, 2.0)
pres = bed_level(pres, -31)
emit('Horror/SFX_Horror_Presence_Loop_01.wav', pres, 'loop',
     "The Nightmare's presence: slowed stethoscope breathing (an octave down) under a bowed singing bowl (two octaves down). "
     'Low, organic, quiet loop.', ['lungs', 'bowl_sing'],
     'breathing cuts 3.0-17.0 s (L) and 16.5-30.5 s (R) at half speed, band 25-500 Hz; bowl friction cut 1.2-8.2 s at quarter '
     'speed, band 30-450 Hz; both levelled with a 3 s RMS contour; bowl 4 dB under the breathing; 2 s loop crossfade, RMS -31 dBFS', (20, 30))

# ================= Story (non-diegetic, stereo one-shots, peak -6 dBFS) =================
hp_ = mix(3.2, 2, (rms_to(filt(cut('swell3', 0.9, 3.2, ch=2, speed=0.5), 25, 350, order=4), -16), 0, 0),
          (rms_to(filt(cut('heart', 20.0, 3.2, ch=2, speed=0.5), 25, 300), -28), 0, 0))
hp_ = fade(hp_, 0.6, 0.9, 'sin')
emit('Story/SFX_Story_HeadPressure_01.wav', peak_to(hp_, -6), 'story',
     'Muffled pressure swell for a headache: an airy whoosh swell slowed an octave and heavily low-passed, with a slowed '
     'stethoscope heartbeat under it.', ['swell3', 'heart'],
     'Dream ReverseSwell_03 cut 0.9-2.5 s at half speed, band 25-350 Hz (4th order); stethoscope blood flow cut 20.0-21.6 s at '
     'half speed, band 25-300 Hz, 12 dB under the swell; 0.6 s sine fade-in, 0.9 s fade-out, peak -6 dBFS', (2.0, 4.0))

ring = filt(cut('bowl_sing', 1.0, 5.0, ch=2), 150, 1200, order=4)
emit('Story/SFX_Story_HeadRing_01.wav', peak_to(fade(ring, 0.8, 1.6, 'sin'), -6), 'story',
     'Muffled ringing in the head: a singing bowl played by friction, its tone heavily low-passed.', ['bowl_sing'],
     'cut 1.0-6.0 s (the bowl starting to sing), band 150 Hz-1.2 kHz (4th order), 0.8 s sine fade-in, 1.6 s fade-out, peak -6 dBFS',
     (3.0, 6.0))

suit = filt(cut('bowl_struck', 0.35, 5.6, ch=2, speed=0.5), 60, 1100, order=4)
emit('Story/SFX_Story_SuitTone_01.wav', peak_to(fade(suit, 0.35, 2.6, 'sin'), -6), 'story',
     'Warm sustained tone for the suit payoff: a struck singing bowl an octave down, its strike removed, soft attack, long release.',
     ['bowl_struck'],
     'cut 0.35-3.15 s at half speed (an octave down, after the strike), band 60 Hz-1.1 kHz (4th order), 0.35 s sine fade-in, '
     '2.6 s fade-out, peak -6 dBFS', (3.0, 6.0))


def dr(k, t0, d):
    return cut(k, t0, d, ch=2)


ts1 = mix(4.3, 2,
          (fade(dr('swell3', 0.0, 2.6), 0.005, 0.30), 0.0, 0),
          (fade(dr('tape_rewind', 0.3, 2.0), 0.9, 0.3, 'sin'), 0.3, -12),
          (fade(dr('tape_scrub2', 0.0, 1.0), 0.02, 0.25), 1.55, -6),
          (fade(dr('tape_stop1', 0.0, 2.2), 0.01, 0.9), 2.1, -3))
emit('Story/SFX_Story_TimeShift_01.wav', peak_to(fade(ts1, 0.005, 0.3), -6), 'story',
     'Time shift: a reverse swell and tape warble that winds down like a stopping tape. Layered from the project Dream SFX.',
     ['swell3', 'tape_rewind', 'tape_scrub2', 'tape_stop1'],
     'ReverseSwell_03 0-2.6 s at 0 s; TapeRewind_01 0.3-2.3 s at 0.3 s -12 dB (sine fade-in); TapeScrub_02 at 1.55 s -6 dB; '
     'TapeStop_01 0-2.2 s at 2.1 s -3 dB; peak -6 dBFS', (2.5, 5.0))
ts2 = mix(5.0, 2,
          (fade(dr('swell2', 1.0, 4.6), 0.4, 0.5, 'sin'), 0.0, 0),
          (fade(dr('tape_rewind', 1.0, 3.0), 1.2, 0.4, 'sin'), 0.2, -10),
          (fade(dr('tape_scrub1', 0.0, 1.0), 0.01, 0.4), 3.35, -4))
emit('Story/SFX_Story_TimeShift_02.wav', peak_to(fade(ts2, 0.005, 0.5), -6), 'story',
     'Day rollover: a rising swell with tape rewind underneath, cut off by a tape scrub. Layered from the project Dream SFX.',
     ['swell2', 'tape_rewind', 'tape_scrub1'],
     'ReverseSwell_02 1.0-5.6 s at 0 s; TapeRewind_01 1.0-4.0 s at 0.2 s -10 dB (sine fade-in); TapeScrub_01 at 3.35 s -4 dB; '
     'peak -6 dBFS', (2.5, 5.5))


# ================= write, check, document =================
def render(rows):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    cols = 5
    nrow = (len(rows) + cols - 1) // cols
    fig = plt.figure(figsize=(4.2 * cols, 3.0 * nrow))
    grid = fig.add_gridspec(nrow, cols, hspace=0.6, wspace=0.25)
    for k, (rel, y, st) in enumerate(rows):
        cell = grid[k // cols, k % cols].subgridspec(2, 1, height_ratios=[1, 2], hspace=0.05)
        m = y.mean(axis=1)
        a = fig.add_subplot(cell[0])
        a.plot(np.arange(len(m)) / SR, m, lw=0.4, color='k')
        a.set_xlim(0, len(m) / SR)
        a.set_ylim(-1, 1)
        a.set_xticks([])
        a.set_yticks([])
        extra = f', seam {st["seam"][0]:.2f}x/{st["seam"][1][0][0]:.1f}/{st["seam"][1][1][0]:.1f} dB' if st['seam'] else ''
        a.set_title(f'{os.path.basename(rel)[4:-4]}\n{st["dur"]:.2f} s, pk {st["peak"]:.1f}, rms {st["rms"]:.1f} dBFS, '
                    f'{y.shape[1]}ch{extra}', fontsize=7)
        a = fig.add_subplot(cell[1])
        nfft = 1024 if len(m) > 4 * SR else 512
        a.specgram(m + 1e-9, NFFT=nfft, Fs=SR, noverlap=nfft * 3 // 4, cmap='magma', vmin=-150, vmax=-50)
        a.set_ylim(0, 12000)
        a.tick_params(labelsize=6)
    os.makedirs(os.path.dirname(PNG), exist_ok=True)
    fig.savefig(PNG, dpi=80, bbox_inches='tight')


def update_records(rows):
    man = A + '/MANIFEST.md'
    text = open(man, encoding='utf-8').read().rstrip('\n').split('\n')
    mine = {f'`SFX/{rel}`' for rel, *_ in rows}
    text = [ln for ln in text if not any(ln.startswith(f'| {m} ') for m in mine)]
    for rel, y, kind, what, keys, proc, st in rows:
        cols = [SRC[k] for k in dict.fromkeys(keys)]
        label = '<br>'.join(c[1] for c in cols)
        url = '<br>'.join(f'<{c[2].split(" ")[0]}>' if c[2].startswith('http') else c[2] for c in cols)
        auth = '<br>'.join(c[3] for c in cols)
        lic = '<br>'.join(dict.fromkeys(c[4] for c in cols))
        loops = 'yes (crossfaded, seam checked)' if kind == 'loop' else 'n/a (one-shot)'
        text.append(f'| `SFX/{rel}` | {what} | {label} | {url} | {auth} | {lic} | {st["dur"]:.2f} s | '
                    f'{st["size"] / 1024:.1f} KiB | {loops} | {"mono" if y.shape[1] == 1 else "stereo"} |')
    open(man, 'w', encoding='utf-8').write('\n'.join(text) + '\n')

    src = A + '/SOURCES.txt'
    t = open(src, encoding='utf-8').read()
    head = '== New 2026-11-09: world and story set'
    t = re.sub(r'\n?' + re.escape(head) + r'.*?(?=\n== |\Z)', '', t, flags=re.S).rstrip('\n') + '\n'
    lines = ['', head + ' (builder P:\\FoA\\Tools\\Audio\\make_world_story_sfx.py; 44.1 kHz 16-bit, TPDF dither) ==',
             'Format: path | source URL | author | licence | processing. Every layer is a recording; nothing is synthesised.']
    for rel, y, kind, what, keys, proc, st in rows:
        cols = [SRC[k] for k in dict.fromkeys(keys)]
        lines.append(f'SFX\\{rel.replace("/", chr(92))} | ' + ' + '.join(c[2] for c in cols) + ' | '
                     + ' + '.join(c[3] for c in cols) + ' | ' + ' + '.join(dict.fromkeys(c[4] for c in cols)) + f' | {proc}')
        lines.extend(f'    local: {c[0]}' for c in cols)
    lines += ['Reused instead of new files (licences in MANIFEST.md):',
              '    Ambience HouseSettle one-shots: SFX\\Creaks\\SFX_Creaks_Wood_01..04 and SFX_Creaks_Settle_01..03 '
              '(SFX_Creaks_Groan_01..03 for louder beats; Floor/Board are footstep creaks)',
              '    Props ShirtPickup third variant: SFX\\Bed\\SFX_Bed_Sheets_01 (and _02), the same InMotionAudio cotton T-shirt foley',
              'Not found as a CC0/PD recording, so built as noted above: a radiator (gas-boiler burn + relay ticks), a wire hanger '
              'on a rail (small metal-grinding foley), a screw on floorboards (a nail on tiles, low-passed), a vase on '
              'floorboards (a ceramic plate breaking on concrete, with a wooden plank thud under the impact).',
              'Not made: Phone\\SFX_Phone_Pickup_01..03. No CC0/PD recording of a smartphone lifted off a table was found '
              '(BigSoundBank COM/OBJ/PLAS/CMPT, OpenGameArt, Wikimedia Commons, the project libraries).']
    open(src, 'w', encoding='utf-8').write(t + '\n'.join(lines) + '\n')


def main():
    rows, sheet = [], []
    for rel, y, kind, what, keys, proc, (dmin, dmax) in OUT:
        if kind != 'loop':  # trim tight: drop trailing near-silence (gated layers), keep 20 ms after the last -70 dBFS sample
            y = y[:np.nonzero(np.abs(y).max(axis=1) > 10 ** (-70 / 20))[0][-1] + int(0.02 * SR)]
        y = q16(y)
        path = f'{A}/SFX/{rel}'
        os.makedirs(os.path.dirname(path), exist_ok=True)
        sf.write(path, y, SR, subtype='PCM_16')
        info = sf.info(path)
        z, zsr = sf.read(path, always_2d=True)
        st = dict(dur=len(z) / zsr, peak=db(np.abs(z).max()), rms=db(np.sqrt(np.mean(z ** 2))), size=os.path.getsize(path),
                  seam=seam(z) if kind == 'loop' else None)
        want_ch = 1 if kind == 'mono' else 2
        assert zsr == SR and info.subtype == 'PCM_16', (rel, zsr, info.subtype)
        assert z.shape[1] == want_ch, (rel, 'channels', z.shape[1])
        assert dmin - 1e-6 <= st['dur'] <= dmax + 1e-6, (rel, 'duration', st['dur'], (dmin, dmax))
        assert st['peak'] < -0.5, (rel, 'too hot / clipping', st['peak'])
        if kind in ('mono', 'story'):
            assert abs(st['peak'] - PEAK[rel]) <= 0.3, (rel, 'one-shot peak off target', st['peak'], PEAK[rel])
            assert np.abs(z[0]).max() < 1e-3, (rel, 'no fade-in')
        else:
            assert st['peak'] < -6 and st['rms'] < -24, (rel, 'bed not quiet', st)
            assert seam_ok(st['seam']), (rel, 'loop seam', st['seam'])
        print(f'{rel:48s} {st["dur"]:6.2f} s  pk {st["peak"]:6.1f}  rms {st["rms"]:6.1f}  {z.shape[1]}ch'
              + (f'  seam step {st["seam"][0]:.2f}x, level jump ' + ', '.join(f'{j:.1f} dB (inner p95 {q:.1f})' for j, q in st['seam'][1])
                 if st['seam'] else ''))
        rows.append((rel, z, kind, what, keys, proc, st))
        sheet.append((rel, z, st))
    render(sheet)
    update_records(rows)
    print('wrote', len(rows), 'files, sheet', PNG)


main()
