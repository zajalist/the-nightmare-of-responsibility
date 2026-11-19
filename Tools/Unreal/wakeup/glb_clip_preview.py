"""Offline clip preview for the Quaternius UAL GLBs (no editor needed): stick figures from the side and front at even
times, plus bone heights over time, so clip choices are made before taking the editor lock.
  python Tools/Unreal/wakeup/glb_clip_preview.py <glb> <clip> [<clip> ...]
Writes Saved/WakeUp/clips/<clip>.png and prints pelvis/head/hand/foot heights (cm, glTF Y-up converted to Z-up)."""
import json
import os
import struct
import sys

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

OUT = "P:/FoA/Saved/WakeUp/clips"
CT = {5120: np.int8, 5121: np.uint8, 5122: np.int16, 5123: np.uint16, 5125: np.uint32, 5126: np.float32}
NC = {"SCALAR": 1, "VEC3": 3, "VEC4": 4, "MAT4": 16}


def load(path):
    b = open(path, "rb").read()
    jl = struct.unpack("<I", b[12:16])[0]
    j = json.loads(b[20:20 + jl])
    bin_ = b[20 + jl + 8:]
    return j, bin_


def acc(j, bin_, i):
    a = j["accessors"][i]
    bv = j["bufferViews"][a["bufferView"]]
    n = NC[a["type"]]
    arr = np.frombuffer(bin_, CT[a["componentType"]], a["count"] * n, bv.get("byteOffset", 0) + a.get("byteOffset", 0))
    return arr.reshape(a["count"], n).astype(np.float64)


def qmat(q):
    x, y, z, w = q
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                     [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                     [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])


def slerp(a, b, f):
    d = np.dot(a, b)
    if d < 0:
        b, d = -b, -d
    if d > 0.9995:
        r = a + f * (b - a)
        return r / np.linalg.norm(r)
    th = np.arccos(d)
    return (np.sin((1 - f) * th) * a + np.sin(f * th) * b) / np.sin(th)


def sample(times, vals, t, rot):
    if t <= times[0]:
        return vals[0]
    if t >= times[-1]:
        return vals[-1]
    i = np.searchsorted(times, t) - 1
    f = (t - times[i]) / (times[i + 1] - times[i])
    return slerp(vals[i], vals[i + 1], f) if rot else vals[i] + f * (vals[i + 1] - vals[i])


class Clip:
    def __init__(self, j, bin_, name):
        self.j = j
        self.nodes = j["nodes"]
        self.parent = {c: i for i, n in enumerate(self.nodes) for c in n.get("children", [])}
        anim = next(a for a in j["animations"] if a["name"] == name)
        self.ch = {}
        self.length = 0.0
        for c in anim["channels"]:
            s = anim["samplers"][c["sampler"]]
            t = acc(j, bin_, s["input"])[:, 0]
            self.length = max(self.length, t[-1])
            self.ch[(c["target"]["node"], c["target"]["path"])] = (t, acc(j, bin_, s["output"]))
        self.idx = {RIGIFY.get(n.get("name"), n.get("name")): i for i, n in enumerate(self.nodes)}

    def world(self, t):
        cache = {}

        def w(i):
            if i in cache:
                return cache[i]
            n = self.nodes[i]
            tr = np.array(n.get("translation", [0, 0, 0]), float)
            q = np.array(n.get("rotation", [0, 0, 0, 1]), float)
            sc = np.array(n.get("scale", [1, 1, 1]), float)
            if (i, "translation") in self.ch:
                tr = sample(*self.ch[(i, "translation")], t, False)
            if (i, "rotation") in self.ch:
                q = sample(*self.ch[(i, "rotation")], t, True)
            if (i, "scale") in self.ch:
                sc = sample(*self.ch[(i, "scale")], t, False)
            m = np.eye(4)
            m[:3, :3] = qmat(q) * sc
            m[:3, 3] = tr
            if i in self.parent:
                m = w(self.parent[i]) @ m
            cache[i] = m
            return m
        return {name: w(i)[:3, 3] for name, i in self.idx.items()}


RIGIFY = {"DEF-hips": "pelvis", "DEF-spine.001": "spine_01", "DEF-spine.002": "spine_02", "DEF-spine.003": "spine_03",
          "DEF-neck": "neck_01", "DEF-head": "Head"}  # UAL1's Godot GLB uses Rigify DEF- names
for _s, _u in (("L", "l"), ("R", "r")):
    RIGIFY.update({f"DEF-shoulder.{_s}": f"clavicle_{_u}", f"DEF-upper_arm.{_s}": f"upperarm_{_u}",
                   f"DEF-forearm.{_s}": f"lowerarm_{_u}", f"DEF-hand.{_s}": f"hand_{_u}", f"DEF-thigh.{_s}": f"thigh_{_u}",
                   f"DEF-shin.{_s}": f"calf_{_u}", f"DEF-foot.{_s}": f"foot_{_u}", f"DEF-toe.{_s}": f"ball_{_u}"})


def zup(p, scale):
    """glTF Y-up metres (after armature scale) -> UE-ish Z-up cm: x right, y forward, z up."""
    return np.array([p[0], -p[2], p[1]]) * scale


LINKS = [("pelvis", "spine_01"), ("spine_01", "spine_02"), ("spine_02", "spine_03"), ("spine_03", "neck_01"),
         ("neck_01", "Head"), ("spine_03", "clavicle_l"), ("clavicle_l", "upperarm_l"), ("upperarm_l", "lowerarm_l"),
         ("lowerarm_l", "hand_l"), ("spine_03", "clavicle_r"), ("clavicle_r", "upperarm_r"), ("upperarm_r", "lowerarm_r"),
         ("lowerarm_r", "hand_r"), ("pelvis", "thigh_l"), ("thigh_l", "calf_l"), ("calf_l", "foot_l"), ("foot_l", "ball_l"),
         ("pelvis", "thigh_r"), ("thigh_r", "calf_r"), ("calf_r", "foot_r"), ("foot_r", "ball_r")]


def main():
    glb, names = sys.argv[1], sys.argv[2:]
    j, bin_ = load(glb)
    os.makedirs(OUT, exist_ok=True)
    for name in names:
        c = Clip(j, bin_, name)
        # calibrate to cm: standing head height of frame 0 of the T-pose is about 170 cm for the mannequin
        ref = Clip(j, bin_, "A_TPose").world(0.0)
        s = 175.0 / max(1e-6, np.max([ref[k][1] for k in ("Head",)]))
        n = 8
        ts = np.linspace(0, c.length, n)
        fig, axes = plt.subplots(2, n, figsize=(n * 2.4, 5.2))
        print(f"== {name}  {c.length:.2f}s")
        for k, t in enumerate(ts):
            p = {b: zup(v, s) for b, v in c.world(t).items()}
            for row, (a, bb) in enumerate(((0, 2), (1, 2))):  # side view (x vs z)... front view (y vs z)
                ax = axes[row][k]
                for u, v in LINKS:
                    if u in p and v in p:
                        ax.plot([p[u][a], p[v][a]], [p[u][bb], p[v][bb]], "-",
                                color="tab:red" if u.endswith("_l") or v.endswith("_l") else "k", lw=1.5)
                ax.plot([-120, 120], [0, 0], color="0.7", lw=0.8)
                ax.set_xlim(-120, 120)
                ax.set_ylim(-10, 190)
                ax.set_aspect("equal")
                ax.set_xticks([])
                ax.set_yticks([])
                if row == 0:
                    ax.set_title(f"{t:.2f}s", fontsize=8)
            print(f"  t={t:5.2f} pelvis={np.round(p['pelvis'], 0)} head={np.round(p['Head'], 0)} "
                  f"hand_l={np.round(p['hand_l'], 0)} hand_r={np.round(p['hand_r'], 0)} "
                  f"foot_l={np.round(p['foot_l'], 0)} foot_r={np.round(p['foot_r'], 0)}")
        axes[0][0].set_ylabel("x-z (red = left)")
        axes[1][0].set_ylabel("y-z")
        fig.suptitle(name)
        fig.tight_layout()
        fig.savefig(f"{OUT}/{name}.png", dpi=70)
        plt.close(fig)


if __name__ == "__main__":
    main()
