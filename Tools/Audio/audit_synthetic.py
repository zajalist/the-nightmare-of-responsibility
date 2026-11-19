"""Heuristic 'synthetic / noise-like' audit of every WAV under an SFX folder. Not a listening test.

usage: python -I audit_synthetic.py <SFX dir> <MANIFEST.md> [out.tsv]

Per file (mono mixdown, 2048-pt STFT, frames above -60 dBFS only):
  flat   median spectral flatness 50 Hz-16 kHz (1 = white noise, ~0 = tonal/structured)
  envsd  std of frame level in dB (low = steady, no transient structure)
  crest  peak/RMS of the whole file in dB (low = no transients)
  tonal  median share of frame energy within +-2 bins of the strongest bin (high = near pure tone)
  mid    share of energy above 150 Hz
  hf     share of energy above 4 kHz (hiss)
  score  noise-likeness = flat * steadiness, plus a tonal term; higher = more suspect
"""
import site, sys
sys.path.append(site.getusersitepackages())  # -I drops user site; numpy/scipy/soundfile live there (trusted)
import os, re
import numpy as np, soundfile as sf
from scipy.signal import stft


def metrics(path):
    x, sr = sf.read(path, always_2d=True)
    m = x.mean(axis=1)
    nps = min(2048, 2 ** int(np.log2(len(m))))  # very short clicks exist (514 samples)
    f, _, Z = stft(m, sr, nperseg=nps, noverlap=nps // 2, boundary=None, padded=False)
    P = np.abs(Z) ** 2
    lvl = 10 * np.log10(P.sum(axis=0) / 1024 ** 2 + 1e-20)  # rough frame level
    act = lvl > lvl.max() - 60
    Pw = P * f[:, None]  # tilt-compensate: pink/brown-ish real spectra would otherwise read as 'tonal' at their low end
    band = (f >= 50) & (f <= 16000)
    Pb = Pw[band][:, act] + 1e-20
    flat = np.exp(np.log(Pb).mean(axis=0)) / Pb.mean(axis=0)
    Pt = np.pad(Pw[(f >= 150) & (f <= 16000)][:, act], ((2, 2), (0, 0)))  # >150 Hz: ignore sub thumps; pad so +-2 never double-counts
    k = Pt[2:-2].argmax(axis=0) + 2
    idx = k[None, :] + np.arange(-2, 3)[:, None]
    tonal = np.take_along_axis(Pt, idx, 0).sum(axis=0) / (Pt.sum(axis=0) + 1e-20)
    tot = P[:, act].sum()
    peak = np.abs(m).max() + 1e-12
    rms = np.sqrt(np.mean(m ** 2)) + 1e-12
    r = dict(dur=len(m) / sr, ch=x.shape[1], flat=float(np.median(flat)), envsd=float(lvl[act].std()),
             crest=float(20 * np.log10(peak / rms)), tonal=float(np.median(tonal)),
             hf=float(P[f > 4000][:, act].sum() / tot), mid=float(P[f >= 150][:, act].sum() / tot))
    steady = 1 / (1 + r["envsd"] / 4) * 1 / (1 + max(r["crest"] - 15, 0) / 6)
    # tonal term only counts when >150 Hz actually carries the sound (sub-only thumps leave a meaningless residue there)
    r["score"] = r["flat"] * steady * 10 + max(r["tonal"] - 0.5, 0) * 4 * min(1.0, r["mid"] / 0.3)
    if r["dur"] < 0.15:  # too few frames for these stats to mean anything
        r["score"] = 0.0
    assert 0 <= r["tonal"] <= 1.0001, r
    return r


def manifest_rows(path):
    rows = {}
    for line in open(path, encoding="utf-8"):
        c = [s.strip() for s in line.split("|")]
        if len(c) > 6 and c[1].startswith("`SFX/"):
            rows[c[1].strip("`")] = (c[2], re.sub(r"<br>", " + ", c[3]))
    return rows


def main(sfx_dir, manifest, out=None):
    rows = manifest_rows(manifest)
    res = []
    for root, _, files in os.walk(sfx_dir):
        for n in files:
            if n.lower().endswith(".wav"):
                p = os.path.join(root, n)
                rel = "SFX/" + os.path.relpath(p, sfx_dir).replace("\\", "/")
                res.append((rel, metrics(p)))
    assert len(res) > 0
    res.sort(key=lambda t: -t[1]["score"])
    lines = ["file\tscore\tflat\tenvsd\tcrest\ttonal\tmid\thf\tdur\tch\tmanifest_what\tmanifest_source"]
    for rel, r in res:
        what, src = rows.get(rel, ("(not in MANIFEST)", ""))
        lines.append(f"{rel}\t{r['score']:.3f}\t{r['flat']:.3f}\t{r['envsd']:.1f}\t{r['crest']:.1f}\t{r['tonal']:.2f}\t{r['mid']:.2f}\t{r['hf']:.2f}\t{r['dur']:.1f}\t{r['ch']}\t{what}\t{src}")
    text = "\n".join(lines)
    if out:
        open(out, "w", encoding="utf-8").write(text + "\n")
    print(f"{len(res)} files, {sum(r in rows for r, _ in res)} matched in MANIFEST")
    print("\n".join(lines[:21]))


def selftest(tmp):
    sr, t = 44100, np.arange(44100 * 3) / 44100
    clicks = np.zeros_like(t); clicks[::11025] = 1.0
    clicks = np.convolve(clicks, np.exp(-np.arange(2000) / 200) * np.random.default_rng(1).standard_normal(2000))[: len(t)] * 0.5
    w = np.fft.rfft(np.random.default_rng(2).standard_normal(len(t)))
    pink = np.fft.irfft(w / np.sqrt(np.maximum(np.arange(len(w)), 1)), len(t)); pink *= 0.1 / pink.std()
    sigs = {"pink": pink, "noise": np.random.default_rng(0).standard_normal(len(t)) * 0.1, "sine": 0.5 * np.sin(2 * np.pi * 440 * t), "clicks": clicks}
    r = {}
    for k, s in sigs.items():
        p = os.path.join(tmp, f"_selftest_{k}.wav"); sf.write(p, s, sr); r[k] = metrics(p); os.remove(p)
    assert r["noise"]["flat"] > 0.3 and r["noise"]["envsd"] < 2, r["noise"]
    assert r["pink"]["flat"] > 0.3 and r["pink"]["score"] > 2, r["pink"]
    assert r["sine"]["tonal"] > 0.9 and r["sine"]["flat"] < 0.05, r["sine"]
    assert r["clicks"]["envsd"] > 6 and r["clicks"]["score"] < r["noise"]["score"], r["clicks"]
    print("selftest ok", {k: round(v["score"], 2) for k, v in r.items()})


if __name__ == "__main__":
    selftest(sys.argv[2]) if sys.argv[1] == "--selftest" else main(*sys.argv[1:4])
