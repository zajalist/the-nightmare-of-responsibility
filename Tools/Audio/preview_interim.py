"""Interim jumpscare preview from EXISTING game SFX only (new Sonniss layers could not be fetched).
Riser (best ReverseSwell, trimmed at its loudness peak) ends at HIT_T; LowImpact_01 + Gasp_01 onsets at HIT_T.

usage: python -I preview_interim.py <SFX dir> <out.wav>
"""
import site, sys
sys.path.append(site.getusersitepackages())  # -I drops user site; numpy/soundfile live there (trusted)
import os
import numpy as np, soundfile as sf

HIT_T = 1.0


def load(p):
    x, sr = sf.read(p, always_2d=True)
    assert sr == 44100, (p, sr)
    return np.repeat(x, 2, axis=1) if x.shape[1] == 1 else x


def env(x, sr, win=0.02):
    e = np.sqrt(np.convolve((x ** 2).mean(axis=1), np.ones(int(sr * win)) / int(sr * win), "same"))
    return 20 * np.log10(e + 1e-12)


def onset(x, sr):
    e = env(x, sr, 0.005)
    return int(np.argmax(e > e.max() - 30))


def main(sfx, out):
    sr = 44100
    swells = {}
    for i in range(1, 5):
        x = load(os.path.join(sfx, "Dream", f"SFX_Dream_ReverseSwell_0{i}.wav"))
        pk = int(np.argmax(env(x, sr)))
        swells[i] = (x, pk)
        print(f"ReverseSwell_0{i}: dur={len(x)/sr:.2f}s loudness peak at {pk/sr:.2f}s ({pk/len(x):.0%} of length)")
    best = max(swells, key=lambda i: swells[i][1] / len(swells[i][0]))  # builds latest = cleanest butt into the hit
    riser, pk = swells[best]
    riser = riser[: pk + 1]
    hit = load(os.path.join(sfx, "Dream", "SFX_Dream_LowImpact_01.wav"))
    gasp = load(os.path.join(sfx, "Dream", "SFX_Dream_Gasp_01.wav"))
    h0, g0 = int(np.argmax(env(hit, sr, 0.005))), onset(gasp, sr)  # hit: align its main transient, not its pre-roll
    print(f"chose ReverseSwell_0{best} trimmed at {pk/sr:.2f}s; LowImpact_01 main transient {h0/sr*1000:.0f} ms (so it starts that much before HIT_T); Gasp_01 onset {g0/sr*1000:.0f} ms")
    t = int(HIT_T * sr)
    assert h0 <= t, "hit pre-roll longer than HIT_T"
    n = t + max(len(hit) - h0, len(gasp) - g0)
    mix = np.zeros((n, 2))
    r0 = max(t - len(riser), 0)
    mix[r0:t] += riser[len(riser) - (t - r0):] * np.minimum(1, np.arange(t - r0) / (0.05 * sr))[:, None]  # 50 ms fade-in on the cut head
    mix[t - h0:t - h0 + len(hit)] += hit  # keep the hit's own pre-roll: it starts h0 early so its transient lands on HIT_T
    mix[t:t + len(gasp) - g0] += gasp[g0:] * 0.7  # gasp sits under the impact
    mix *= 10 ** (-1 / 20) / np.abs(mix).max()
    assert np.abs(mix).max() <= 10 ** (-1 / 20) + 1e-6
    os.makedirs(os.path.dirname(out), exist_ok=True)
    sf.write(out, mix, sr, subtype="PCM_16")
    print(f"wrote {out} dur={n/sr:.2f}s riser {r0/sr:.2f}-{t/sr:.2f}s, hits at {t/sr:.2f}s")


if __name__ == "__main__":
    main(*sys.argv[1:3])
