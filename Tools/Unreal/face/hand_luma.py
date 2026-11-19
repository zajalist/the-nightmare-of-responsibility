"""Hand/arm skin luma from a rendered / player-hidden PNG pair (world's phone-hold proof):
  python Tools/Unreal/face/hand_luma.py <with_player.png> <player_hidden.png>
Mask = pixels that change by more than 6/255 between the pair (his visible body in that frame), lit-skin part
only (luma > 0.12, which drops the dark polo sleeve and pants). Prints mean, p10, p90, p99 and the clipped share.
Pass: mean 0.30-0.45, p99 < 0.85, clipped < 0.5%, p90 - p10 >= 0.12 (shading survives)."""
import sys

import numpy as np
from PIL import Image


def luma(p):
    a = np.asarray(Image.open(p).convert('RGB')).astype(np.float32) / 255.0
    return a @ np.array([0.2126, 0.7152, 0.0722], np.float32), a


def measure(a_path, b_path):
    ya, ra = luma(a_path)
    _, rb = luma(b_path)
    mask = (np.abs(ra - rb).max(-1) > 6 / 255) & (ya > 0.12)
    v = ya[mask]
    if v.size < 50:
        return dict(px=int(v.size), error='no hand pixels')
    r = dict(px=int(v.size), mean=float(v.mean()), p10=float(np.percentile(v, 10)), p90=float(np.percentile(v, 90)),
             p99=float(np.percentile(v, 99)), clipped=float((v > 0.95).mean()))
    r['pass'] = 0.30 <= r['mean'] <= 0.45 and r['p99'] < 0.85 and r['clipped'] < 0.005 and r['p90'] - r['p10'] >= 0.12
    return {k: (round(x, 4) if isinstance(x, float) else x) for k, x in r.items()}


if __name__ == '__main__':
    print(measure(sys.argv[1], sys.argv[2]))
