"""Bell / chime check (the user: "no bell sound"): python -I Tools/Audio/bell_check.py <wav> ...
A bell reads as narrow, steady partials above the voice's formants that ring on after the attack. In 46 ms frames,
any bin between 1.2 and 9 kHz that is a local peak at least 18 dB over its +-200 Hz surroundings for 0.8 s or more
without moving more than one bin is reported with its time, frequency and how far it decays. A voice's held vowel can
trip it too, so each hit is a span to listen to or cut, not proof of a bell. Exit code 1 when anything is flagged."""
import site
import sys

sys.path.append(site.getusersitepackages())  # -I drops user site (trusted libs)
import numpy as np  # noqa: E402
import soundfile as sf  # noqa: E402
from scipy.signal import stft  # noqa: E402

flagged = 0
for path in sys.argv[1:]:
    x, sr = sf.read(path, always_2d=True)
    f, t, Z = stft(x.mean(1), sr, nperseg=2048, noverlap=1024)
    S = 20 * np.log10(np.abs(Z) + 1e-9)
    df = f[1] - f[0]
    w = int(200 / df)
    lo, hi = np.searchsorted(f, 1200), np.searchsorted(f, 9000)
    hits = []
    for k in range(lo, hi):
        around = np.concatenate([S[k - w:k - 2], S[k + 3:k + w + 1]]).mean(0)
        peak = (S[k] - around > 18) & (S[k] >= S[k - 1]) & (S[k] >= S[k + 1])
        run = 0
        for j, p in enumerate(peak):
            run = run + 1 if p else 0
            if run == int(0.8 / (t[1] - t[0])):
                a = j - run + 1
                hits.append((round(t[a], 2), int(f[k]), round(S[k, a] - S[k, j], 1)))
    hits = sorted(set(hits))
    merged = []
    for h in hits:
        if merged and h[0] - merged[-1][0] < 1.0 and abs(h[1] - merged[-1][1]) < 400:
            continue
        merged.append(h)
    flagged += len(merged)
    print(path.split('/')[-1], 'clean' if not merged else f'{len(merged)} ringing partials (s, Hz, decay dB): {merged[:12]}')
sys.exit(1 if flagged else 0)
