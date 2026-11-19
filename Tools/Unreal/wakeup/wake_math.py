"""Pure-Python vector/quaternion helpers and a two-bone IK for the wake-up composite clips.
No numpy and no unreal import, so it runs inside the editor and offline (python wake_math.py runs the self-check).
Quaternions are (x, y, z, w) Hamilton products, the same convention as UE's FQuat: (a * b) applies b first."""
import math


def add(a, b):
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def mul(a, s):
    return (a[0] * s, a[1] * s, a[2] * s)


def dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def length(a):
    return math.sqrt(dot(a, a))


def norm(a):
    n = length(a)
    return mul(a, 1.0 / n) if n > 1e-9 else (0.0, 0.0, 0.0)


def lerp(a, b, t):
    return add(a, mul(sub(b, a), t))


def cos_d(deg):
    return math.cos(math.radians(deg))


def sin_d(deg):
    return math.sin(math.radians(deg))


def smooth(t):
    t = min(1.0, max(0.0, t))
    return t * t * (3.0 - 2.0 * t)


def qmul(a, b):
    ax, ay, az, aw = a
    bx, by, bz, bw = b
    return (aw * bx + ax * bw + ay * bz - az * by,
            aw * by - ax * bz + ay * bw + az * bx,
            aw * bz + ax * by - ay * bx + az * bw,
            aw * bw - ax * bx - ay * by - az * bz)


def qinv(q):
    return (-q[0], -q[1], -q[2], q[3])


def qnorm(q):
    n = math.sqrt(sum(c * c for c in q)) or 1.0
    return tuple(c / n for c in q)


def qrot(q, v):
    """Rotate vector v by unit quaternion q."""
    p = qmul(qmul(q, (v[0], v[1], v[2], 0.0)), qinv(q))
    return (p[0], p[1], p[2])


def qaxis(axis, deg):
    a = norm(axis)
    s = math.sin(math.radians(deg) * 0.5)
    return (a[0] * s, a[1] * s, a[2] * s, math.cos(math.radians(deg) * 0.5))


def qslerp(a, b, t):
    d = sum(x * y for x, y in zip(a, b))
    if d < 0.0:
        b, d = tuple(-c for c in b), -d
    if d > 0.9995:
        return qnorm(tuple(x + (y - x) * t for x, y in zip(a, b)))
    th = math.acos(d)
    s = math.sin(th)
    wa, wb = math.sin((1.0 - t) * th) / s, math.sin(t * th) / s
    return tuple(wa * x + wb * y for x, y in zip(a, b))


def from_to(u, v):
    """Shortest-arc rotation taking direction u onto direction v."""
    u, v = norm(u), norm(v)
    d = dot(u, v)
    if d < -0.999999:  # opposite: any perpendicular axis
        ax = cross((1.0, 0.0, 0.0), u)
        if length(ax) < 1e-6:
            ax = cross((0.0, 1.0, 0.0), u)
        return qaxis(ax, 180.0)
    c = cross(u, v)
    return qnorm((c[0], c[1], c[2], 1.0 + d))


def frame_quat(primary, secondary):
    """Quaternion of the orthonormal frame whose X is `primary` and whose XY plane holds `secondary`."""
    x = norm(primary)
    z = norm(cross(x, secondary))
    y = cross(z, x)
    m = ((x[0], y[0], z[0]), (x[1], y[1], z[1]), (x[2], y[2], z[2]))  # columns x, y, z
    tr = m[0][0] + m[1][1] + m[2][2]
    if tr > 0:
        s = math.sqrt(tr + 1.0) * 2
        return qnorm(((m[2][1] - m[1][2]) / s, (m[0][2] - m[2][0]) / s, (m[1][0] - m[0][1]) / s, 0.25 * s))
    if m[0][0] > m[1][1] and m[0][0] > m[2][2]:
        s = math.sqrt(1.0 + m[0][0] - m[1][1] - m[2][2]) * 2
        return qnorm((0.25 * s, (m[0][1] + m[1][0]) / s, (m[0][2] + m[2][0]) / s, (m[2][1] - m[1][2]) / s))
    if m[1][1] > m[2][2]:
        s = math.sqrt(1.0 + m[1][1] - m[0][0] - m[2][2]) * 2
        return qnorm(((m[0][1] + m[1][0]) / s, 0.25 * s, (m[1][2] + m[2][1]) / s, (m[0][2] - m[2][0]) / s))
    s = math.sqrt(1.0 + m[2][2] - m[0][0] - m[1][1]) * 2
    return qnorm(((m[0][2] + m[2][0]) / s, (m[1][2] + m[2][1]) / s, 0.25 * s, (m[1][0] - m[0][1]) / s))


def align(cur_primary, cur_secondary, want_primary, want_secondary):
    """Rotation that carries the current (primary, secondary) frame onto the wanted one."""
    return qmul(frame_quat(want_primary, want_secondary), qinv(frame_quat(cur_primary, cur_secondary)))


def two_bone(s, e, w, target, pole):
    """Two-bone IK in one space. s, e, w: shoulder, elbow, wrist positions; pole: a point the elbow should bend toward.
    Returns (q_upper, q_lower, reached_wrist): world-space delta rotations to pre-multiply onto the upper bone's and
    (after the upper delta) the lower bone's world rotations. Bone lengths are preserved; out-of-reach targets clamp."""
    a, b = length(sub(e, s)), length(sub(w, e))
    to_t = sub(target, s)
    d = min(max(length(to_t), abs(a - b) + 1e-3), a + b - 1e-3)
    dirn = norm(to_t)
    pdir = sub(pole, s)
    pdir = norm(sub(pdir, mul(dirn, dot(pdir, dirn))))
    x = (a * a - b * b + d * d) / (2.0 * d)
    h = math.sqrt(max(a * a - x * x, 0.0))
    e_new = add(add(s, mul(dirn, x)), mul(pdir, h))
    q1 = from_to(sub(e, s), sub(e_new, s))
    w1 = add(s, qrot(q1, sub(w, s)))  # wrist after the upper rotation
    t_clamped = add(s, mul(dirn, d))
    q2 = from_to(sub(w1, e_new), sub(t_clamped, e_new))
    return q1, q2, add(e_new, qrot(q2, sub(w1, e_new)))


class Pose:
    """Local transforms {bone: (pos, quat, scale)} plus parents; world transforms are computed lazily (UE order:
    world = parent * local). Engine-free so the composite math runs the same on GLB data and on AnimPose data."""

    def __init__(self, local, parent):
        self.local, self.parent, self._w = local, parent, None

    def copy(self):
        return Pose(dict(self.local), self.parent)

    def world(self):
        if self._w is None:
            w = {}

            def get(b):
                if b not in w:
                    lp, lq, ls = self.local[b]
                    par = self.parent.get(b)
                    if par is None:
                        w[b] = (lp, lq, ls)
                    else:
                        pp, pq, ps = get(par)
                        w[b] = (add(pp, qrot(pq, (lp[0] * ps[0], lp[1] * ps[1], lp[2] * ps[2]))), qnorm(qmul(pq, lq)),
                                (ls[0] * ps[0], ls[1] * ps[1], ls[2] * ps[2]))
                return w[b]
            for b in self.local:
                get(b)
            self._w = w
        return self._w


class PoseAdapter:
    """The interface edge_clip.Edge uses, over Pose objects. Subclasses only supply raw(clip, t) -> Pose."""
    parent = {}

    def __init__(self):
        self._cache = {}

    def pose_at(self, clip, t):
        key = (clip, round(t, 4))
        if key not in self._cache:
            self._cache[key] = self.raw(clip, t)
        return self._cache[key].copy()

    def bones(self, p):
        return list(p.local)

    def lget(self, p, b):
        return p.local[b][0], p.local[b][1]

    def lset(self, p, b, pos, q):
        p.local[b] = (pos, q, p.local[b][2])
        p._w = None

    def wget(self, p, b):
        w = p.world()[b]
        return w[0], w[1]

    def wset(self, p, b, pos, q):
        par = p.parent.get(b)
        if par is None:
            self.lset(p, b, pos, q)
            return
        pp, pq, ps = p.world()[par]
        inv = qinv(pq)
        lp = qrot(inv, sub(pos, pp))
        self.lset(p, b, (lp[0] / ps[0], lp[1] / ps[1], lp[2] / ps[2]), qnorm(qmul(inv, q)))


def _selfcheck():
    import random
    random.seed(4)
    for _ in range(200):
        s = (0.0, 0.0, 0.0)
        e = (random.uniform(-30, 30), random.uniform(-30, 30), random.uniform(-30, 30))
        e = mul(norm(e), 30.0)
        w = add(e, mul(norm((random.uniform(-1, 1), random.uniform(-1, 1), random.uniform(-1, 1))), 26.0))
        tgt = mul(norm((random.uniform(-1, 1), random.uniform(-1, 1), random.uniform(-1, 1))), random.uniform(10, 50))
        pole = (random.uniform(-50, 50), random.uniform(-50, 50), random.uniform(-50, 50))
        q1, q2, got = two_bone(s, e, w, tgt, pole)
        e2 = qrot(q1, e)
        assert abs(length(e2) - 30.0) < 1e-6
        assert abs(length(sub(got, e2)) - 26.0) < 1e-6, "forearm length"
        assert length(sub(got, tgt)) < 1e-4, (got, tgt)
    for _ in range(100):
        q = qnorm((random.uniform(-1, 1), random.uniform(-1, 1), random.uniform(-1, 1), random.uniform(-1, 1)))
        p, sc = qrot(q, (1, 0, 0)), qrot(q, (0, 1, 0))
        wp, ws = norm((1, 2, 0.3)), norm((-2, 1, 0.5))
        r = align(p, sc, wp, ws)
        assert length(sub(qrot(r, p), wp)) < 1e-6
        assert dot(qrot(r, sc), cross(wp, cross(ws, wp))) > 0.0  # secondary lands on the wanted side
        assert abs(dot(qrot(r, sc), wp)) < 1e-6
    assert length(sub(qrot(from_to((1, 0, 0), (0, 0, 1)), (1, 0, 0)), (0, 0, 1))) < 1e-9
    print("wake_math selfcheck ok")


if __name__ == "__main__":
    _selfcheck()
