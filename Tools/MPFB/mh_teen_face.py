# Runs INSIDE MakeHuman via Tools/MPFB/mh_drive.py @Tools/MPFB/mh_teen_face.py (after mh_teen_v1.py).
# A tired, soft-faced 16-17 year old: heavy lids and eye bags, hump nose, ears that stick out a little,
# round cheeks, a hint of double chin. Slight left/right differences so he doesn't look mirrored.
import getpath
import material

FACE = {
    "head/head-round": 0.45, "head/head-fat-decr|incr": 0.35, "head/head-age-decr|incr": -0.15,
    "neck/neck-double-decr|incr": 0.35,
    "cheek/l-cheek-volume-decr|incr": 0.45, "cheek/r-cheek-volume-decr|incr": 0.40,
    "cheek/l-cheek-bones-decr|incr": -0.25, "cheek/r-cheek-bones-decr|incr": -0.25,
    "chin/chin-prominent-decr|incr": -0.2, "chin/chin-width-decr|incr": 0.15,
    "nose/nose-hump-decr|incr": 0.5, "nose/nose-scale-vert-decr|incr": 0.25, "nose/nose-point-down|up": -0.25,
    "nose/nose-volume-decr|incr": 0.2, "nose/nose-nostrils-width-decr|incr": 0.15,
    "eyebrows/eyebrows-trans-down|up": -0.25, "eyebrows/eyebrows-angle-down|up": -0.2,
    "mouth/mouth-lowerlip-volume-decr|incr": 0.35, "mouth/mouth-angles-down|up": -0.3,
    "mouth/mouth-scale-horiz-decr|incr": -0.1,
}
for side, k in (("l", 1.0), ("r", 0.85)):  # right side a touch less, for asymmetry
    FACE.update({
        "eyes/%s-eye-bag-decr|incr" % side: 0.55 * k,
        "eyes/%s-eye-eyefold-down|up" % side: -0.45 * k,        # heavy upper lid
        "eyes/%s-eye-corner2-down|up" % side: -0.3 * k,         # outer corner droops
        "eyes/%s-eye-scale-decr|incr" % side: -0.12,
        "ears/%s-ear-rot-backward|forward" % side: 0.45 * k,    # ears stick out
        "ears/%s-ear-flap-decr|incr" % side: 0.35 * k,
        "ears/%s-ear-scale-decr|incr" % side: 0.15,
    })

missing = []
for name, value in FACE.items():
    m = human.getModifier(name)
    if m is None:
        missing.append(name)
        continue
    m.setValue(value)
human.applyAllTargets()

human.setHairProxy(None)  # strand hair replaces MakeHuman card hair in the Blender stage
human.eyesProxy.object.material = material.fromFile(getpath.getSysDataPath("eyes/materials/brown.mhmat"))
G.redraw()
print("missing", missing, "height", round(human.getHeightCm(), 1))
