"""Offline: the Teen right thumb against the palm in a pie_wake_film.py run (film.json contact samples), per sample in a
time window: degrees to the palm side of the palm plane (palm normal oriented down, the palm faces the clock at the
slap) and degrees from the fingers toward the index. Slap target (slap_thumb.py): about 5 and 33.
  python Tools/Unreal/player/slap_thumb_angle.py <wake_film folder> [t0 t1]"""
import json
import math
import sys

d = sys.argv[1]
t0, t1 = (float(sys.argv[2]), float(sys.argv[3])) if len(sys.argv) > 3 else (12.3, 13.3)
sub = lambda a, b: [x - y for x, y in zip(a, b)]  # noqa: E731
dot = lambda a, b: sum(x * y for x, y in zip(a, b))  # noqa: E731
norm = lambda a: [x / math.sqrt(dot(a, a)) for x in a]  # noqa: E731
cross = lambda a, b: [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]  # noqa: E731
rows = [r for r in json.load(open(d + '/film.json'))['contact'] if t0 <= r['seq'] <= t1 and 'teen_thumb_03_r' in r]
assert rows, 'no thumb samples in the window (run predates the thumb logging?)'
out = []
for r in rows:
    f = norm(sub(r['teen_middle_01_r'], r['teen_hand_r']))
    a = sub(r['teen_index_01_r'], r['teen_pinky_01_r'])
    a = norm(sub(a, [x * dot(a, f) for x in f]))
    n = norm(cross(f, a))
    if n[2] > 0:  # the palm faces down onto the clock
        n = [-x for x in n]
    t = norm(sub(r['teen_thumb_03_r'], r['teen_thumb_01_r']))
    out.append((r['seq'], round(math.degrees(math.asin(dot(t, n))), 1), round(math.degrees(math.atan2(dot(t, a), dot(t, f))), 1),
                r.get('slap_thumb_w')))
for o in out:
    print('t %.3f thumb %5.1f deg to the palm side, %5.1f deg from the fingers toward the index, layer weight %s' % o)
print('SLAP_THUMB_ANGLE palm side %.1f..%.1f deg' % (min(o[1] for o in out), max(o[1] for o in out)))
