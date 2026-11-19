"""Joint angles -> wrinkle weights and phases. The reference for BPC_FoA_ClothWrinkles (same formulas, same
thresholds), used by the Blender proof renders. Inputs are bone head/tail positions in any one space.

Channels match the mask texture: elbow (R), arm (G), torso (B), knee (A). Each has a Left and a Right value.
Weights are 0 at the neutral stance the masks were measured from and 1 at the "full" pose of bake_wrinkles.py.
Phase (radians) slides the folds a little as the joint moves, plus a walk drift tied to distance travelled."""
import math

# (lo, hi) degrees for smoothstep; must stay in step with POSES in bake_wrinkles.py and the BPC defaults.
ELBOW = (45.0, 130.0)   # angle upper-arm -> forearm; bind pose already has 45
ARM = (20.0, 80.0)      # upper arm away from the torso's down axis; hanging arms ~11
SPINE = (30.0, 62.0)    # chest axis vs pelvis axis; teen bind 25 (pelvis bone tilts back), full bend 65
HIP = (15.0, 75.0)      # thigh away from the torso's down axis; bind ~8
KNEE = (12.0, 100.0)    # thigh -> calf; bind ~10
PHASE_PER_WEIGHT = 1.2  # radians of fold slide over the full bend
WALK_DRIFT = 0.35       # radians, sin(2 pi * distance / stride)
STRIDE_CM = 140.0


def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _angle(a, b):
    la = math.sqrt(sum(x * x for x in a)) or 1e-9
    lb = math.sqrt(sum(x * x for x in b)) or 1e-9
    c = max(-1.0, min(1.0, sum(x * y for x, y in zip(a, b)) / (la * lb)))
    return math.degrees(math.acos(c))


def _smooth(lo_hi, x):
    lo, hi = lo_hi
    t = max(0.0, min(1.0, (x - lo) / (hi - lo)))
    return t * t * (3 - 2 * t)


def angles(head):
    """Raw joint angles in degrees, for tuning the thresholds against a new rig."""
    down = _sub(head["pelvis"], head["spine_03"])
    a = {"spine": _angle(_sub(head["neck_01"], head["spine_03"]), _sub(head["spine_01"], head["pelvis"]))}
    for s in "lr":
        upper = _sub(head["lowerarm_" + s], head["upperarm_" + s])
        thigh = _sub(head["calf_" + s], head["thigh_" + s])
        a.update({"elbow_" + s: _angle(upper, _sub(head["hand_" + s], head["lowerarm_" + s])),
                  "arm_" + s: _angle(upper, down), "hip_" + s: _angle(thigh, down),
                  "knee_" + s: _angle(thigh, _sub(head["foot_" + s], head["calf_" + s]))})
    return {k: round(v, 1) for k, v in a.items()}


def weights(head, distance_cm=0.0, garment=None):
    """head: dict bone -> (x, y, z) position of the bone's head (joint). Returns (wL, wR, pL, pR), each a
    4-tuple ordered (elbow, arm, torso, knee)."""
    down = _sub(head["pelvis"], head["spine_03"])                   # torso down axis
    spine = _angle(_sub(head["neck_01"], head["spine_03"]), _sub(head["spine_01"], head["pelvis"]))
    drift = WALK_DRIFT * math.sin(2 * math.pi * distance_cm / STRIDE_CM)
    out = []
    for s in "lr":
        upper = _sub(head["lowerarm_" + s], head["upperarm_" + s])
        fore = _sub(head["hand_" + s], head["lowerarm_" + s])
        thigh = _sub(head["calf_" + s], head["thigh_" + s])
        calf = _sub(head["foot_" + s], head["calf_" + s])
        w = (_smooth(ELBOW, _angle(upper, fore)),
             _smooth(ARM, _angle(upper, down)),
             (_smooth(SPINE, spine) if garment in ('Polo','Shirt','foa_polo_layered')
              else max(_smooth(SPINE, spine), _smooth(HIP, _angle(thigh, down)))),
             _smooth(KNEE, _angle(thigh, calf)))
        p = tuple(PHASE_PER_WEIGHT * x + (drift if s == "l" else -drift) for x in w)
        out.append((w, p))
    (wl, pl), (wr, pr) = out
    return wl, wr, pl, pr


if __name__ == "__main__":
    # self-check: a straight, hanging limb set gives ~0; a deep knee bend gives knee ~1
    rest = {"pelvis": (0, 0, 100), "spine_01": (0, 0, 110), "spine_03": (0, 0, 130), "neck_01": (0, 0, 150),
            "upperarm_l": (20, 0, 145), "lowerarm_l": (22, 0, 115), "hand_l": (24, 0, 88),
            "upperarm_r": (-20, 0, 145), "lowerarm_r": (-22, 0, 115), "hand_r": (-24, 0, 88),
            "thigh_l": (10, 0, 100), "calf_l": (11, 0, 55), "foot_l": (12, 0, 8),
            "thigh_r": (-10, 0, 100), "calf_r": (-11, 0, 55), "foot_r": (-12, 0, 8)}
    wl, wr, _, _ = weights(rest)
    assert max(wl + wr) < 0.05, (wl, wr)
    bent = dict(rest, foot_l=(11, 45, 55))
    wl, wr, _, _ = weights(bent)
    assert wl[3] > 0.95 and wr[3] < 0.05, (wl, wr)
    print("wrinkle_driver selftest ok")
