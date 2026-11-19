"""Print a coarse per-second envelope (RMS dBFS, spectral centroid Hz, flatness) of one WAV.
usage: python -I env.py <file.wav> [hop_seconds]"""
import site, sys
sys.path.append(site.getusersitepackages())  # -I drops user site; numpy/soundfile live there (trusted)
import numpy as np, soundfile as sf

x, sr = sf.read(sys.argv[1], always_2d=True)
hop = float(sys.argv[2]) if len(sys.argv) > 2 else 1.0
m = x.mean(axis=1)
print(f"{sys.argv[1]}\n sr={sr} ch={x.shape[1]} dur={len(m)/sr:.2f}s peak={20*np.log10(np.abs(x).max()+1e-12):.1f}dBFS")
n = int(hop * sr)
for i in range(0, len(m) - n + 1, n):
    s = m[i:i + n]
    S = np.abs(np.fft.rfft(s * np.hanning(len(s)))) + 1e-12
    f = np.fft.rfftfreq(len(s), 1 / sr)
    rms = 20 * np.log10(np.sqrt(np.mean(s ** 2)) + 1e-12)
    cen = (f * S).sum() / S.sum()
    flat = np.exp(np.mean(np.log(S))) / np.mean(S)
    print(f" {i/sr:6.1f}s rms={rms:6.1f} cen={cen:6.0f} flat={flat:.3f}")
