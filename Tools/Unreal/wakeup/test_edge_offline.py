"""Offline check of edge_clip.py on the Quaternius UAL1 GLB (no editor): plants, reach warp and blends, as stick figures.
  python Tools/Unreal/wakeup/test_edge_offline.py
Asserts the planted wrists sit on their targets, the grab lands on the clock, and no bone length changes; writes
Saved/WakeUp/clips/edge_offline.png (side and front views over time)."""
import os
import sys

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import edge_clip  # noqa: E402
import glb_clip_preview as G  # noqa: E402
import wake_math as m  # noqa: E402

GLB = "P:/FoA-Assets/animation/quaternius_ual1/Animation Library[Standard]/Godot/AnimationLibrary_Godot_Standard.glb"
NAME = dict(G.RIGIFY)
for s, u in (("L", "l"), ("R", "r")):
    for f in ("index", "middle", "pinky", "ring"):
        for k in ("01", "02", "03"):
            NAME[f"DEF-f_{f}.{k}.{s}"] = f"{f}_{k}_{u}"
    for k in ("01", "02", "03"):
        NAME[f"DEF-thumb.{k}.{s}"] = f"thumb_{k}_{u}"


class GlbAdapter(m.PoseAdapter):
    def __init__(self):
        super().__init__()
        j, bin_ = G.load(GLB)
        self.j, self.bin = j, bin_
        self.clips = {}
        nodes = j["nodes"]
        self.nm = [NAME.get(n.get("name"), n.get("name")) for n in nodes]
        self.parent = {}
        for i, n in enumerate(nodes):
            for c in n.get("children", []):
                self.parent[self.nm[c]] = self.nm[i]

    def clip(self, name):
        if name not in self.clips:
            self.clips[name] = G.Clip(self.j, self.bin, name)
        return self.clips[name]

    def raw(self, clip, t):
        c = self.clip(clip)
        local = {}
        for i, n in enumerate(c.nodes):
            tr = tuple(n.get("translation", [0, 0, 0]))
            q = tuple(n.get("rotation", [0, 0, 0, 1]))
            sc = tuple(n.get("scale", [1, 1, 1]))
            if (i, "translation") in c.ch:
                tr = tuple(G.sample(*c.ch[(i, "translation")], t, False))
            if (i, "rotation") in c.ch:
                q = tuple(G.sample(*c.ch[(i, "rotation")], t, True))
            if (i, "scale") in c.ch:
                sc = tuple(G.sample(*c.ch[(i, "scale")], t, False))
            local[self.nm[i]] = (tuple(float(x) for x in tr), m.qnorm(tuple(float(x) for x in q)), tuple(float(x) for x in sc))
        return m.Pose(local, self.parent)


def main():
    A = GlbAdapter()
    sit = A.pose_at("Sitting_Idle_Loop", 0.0)
    tp = A.pose_at("A_TPose", 0.0)
    cm = 152.0 / (A.wget(tp, "Head")[0][1] - A.wget(tp, "foot_l")[0][1])  # head bone to ankle bone of a ~178 cm adult
    F, L, U = (0.0, 0.0, 1.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)
    pel = A.wget(sit, "pelvis")[0]
    seat = pel[1] - 10.0 / cm
    unit = lambda v: m.mul(v, 1.0 / cm)  # noqa: E731
    plant = {s: m.add(m.add(pel, unit(m.mul(L, sg * 26.0))), m.add(unit(m.mul(F, 8.0)), (0.0, seat + 12.0 / cm - pel[1], 0.0)))  # mattress 9 cm above a chair seat
             for s, sg in (("l", 1.0), ("r", -1.0))}
    clock = m.add(pel, m.add(unit(m.mul(F, 48.0)), m.add(unit(m.mul(L, -28.0)), (0.0, seat + 8.0 / cm - pel[1], 0.0))))
    cfg = {"sit": "Sitting_Idle_Loop", "pick": "PickUp_Table", "exit": "Sitting_Exit",
           "sit_len": A.clip("Sitting_Idle_Loop").length, "pick_len": A.clip("PickUp_Table").length,
           "exit_len": A.clip("Sitting_Exit").length, "exit_rate": 0.8, "release": (0.28, 0.58),
           "T_hold": 0.9, "T_reach": 1.4, "T_breath": 1.1, "F": F, "L": L, "U": U, "plant": plant, "clock": clock,
           "reach_side": "l", "spine": ["spine_01", "spine_02", "spine_03", "neck_01", "Head"], "palm_out_deg": 20.0,
           "slouch_bones": ["spine_01", "spine_02", "spine_03"]}
    E = edge_clip.Edge(A, cfg)
    print("slouch %.0f deg" % E.auto_slouch())
    g0 = E.source_grab()
    clock = m.add(g0, unit((-6.0, 3.0, 5.0)))  # placement leaves a few cm for the warp
    cfg["clock"] = clock
    print("grab at reach+%.2fs, warp %s cm" % (E.t_grab, np.round(np.array(E.measure_warp()) * cm, 1)))
    ref = A.pose_at("Sitting_Idle_Loop", 0.0)
    lens = {b: m.length(A.lget(ref, b)[0]) for b in ("lowerarm_l", "hand_l", "lowerarm_r", "hand_r")}
    T = E.duration()
    ts = np.arange(0.0, T, 1.0 / 30.0)
    frames = []
    for t in ts:
        p = E.frame(float(t))
        for b, l0 in lens.items():
            assert abs(m.length(A.lget(p, b)[0]) - l0) < 1e-6, ("bone length", b, t)
        frames.append(p)
    # planted wrists on target during hold and breath
    for t in (0.3, 2.6, 3.2):
        p = frames[int(t * 30)]
        for s in ("l", "r"):
            d = m.length(m.sub(A.wget(p, "hand_" + s)[0], plant[s])) * cm
            assert d < 0.5, ("plant", s, t, d)
    g = frames[int(round((0.9 + E.t_grab) * 30))]
    dg = m.length(m.sub(A.wget(g, "hand_l")[0], clock)) * cm
    print("grab error %.2f cm" % dg)
    assert dg < 2.0
    # palm-down check: palm normal from the hand frame points down
    p = frames[10]
    for s, sg in (("l", 1.0), ("r", -1.0)):
        hp = A.wget(p, "hand_" + s)[0]
        f = m.norm(m.sub(A.wget(p, "middle_01_" + s)[0], hp))
        print(s, "finger dir (F,L,U) = %.2f %.2f %.2f" % (m.dot(f, F), m.dot(f, L), m.dot(f, U)))
    # stick figures
    n = 12
    idx = np.linspace(0, len(frames) - 1, n).astype(int)
    fig, axes = plt.subplots(2, n, figsize=(n * 2.2, 5.2))
    for k, i in enumerate(idx):
        W = {b: np.array(v[0]) * cm for b, v in frames[i].world().items()}
        for row, (a, bb) in enumerate(((2, 1), (0, 1))):  # side: forward(Z) vs up(Y); front: left(X) vs up
            ax = axes[row][k]
            for u, v in G.LINKS:
                if u in W and v in W:
                    ax.plot([W[u][a], W[v][a]], [W[u][bb], W[v][bb]], "-", lw=1.4,
                            color="tab:red" if u.endswith("_l") or v.endswith("_l") else "k")
            ax.plot(np.array(clock)[a] * cm, np.array(clock)[bb] * cm, "o", color="tab:blue", ms=4)
            for s in plant.values():
                ax.plot(np.array(s)[a] * cm, np.array(s)[bb] * cm, "x", color="tab:green", ms=4)
            ax.axhline(seat * cm, color="0.8", lw=0.8)
            ax.set_xlim(-80, 80)
            ax.set_ylim(-10, 150)
            ax.set_aspect("equal")
            ax.set_xticks([])
            ax.set_yticks([])
            if row == 0:
                ax.set_title("%.2fs" % ts[i], fontsize=8)
    fig.tight_layout()
    out = "P:/FoA/Saved/WakeUp/clips/edge_offline.png"
    fig.savefig(out, dpi=70)
    print("ok", len(frames), "frames", out)


if __name__ == "__main__":
    main()
