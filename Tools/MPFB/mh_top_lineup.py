# Runs INSIDE MakeHuman: try each candidate top (or whole outfit) on the current teen, shoot a 3/4 and a front view,
# then put the original clothes back. Set CANDIDATES = [(label, mhclo_path, replaces_pants), ...] before exec.
import os

import numpy as np
import getpath

OUT = r"P:/FoA/Saved/CharacterShots/makehuman/tops"
os.makedirs(OUT, exist_ok=True)
cl = G.getTask("Geometries", "Clothes")
original = [p.file for p in human.clothesProxies.values()]
TOPS = ("FoA_Crude_Tee_Layered", "crude_male_shirt")
PANTS = ("Pants_Wool",)

hco = human.getRestposeCoordinates()
centre = np.array([0.0, np.percentile(hco[:, 1], 70), hco[:, 2].mean()])  # chest height
done = []
for label, path, replaces_pants in CANDIDATES:
    for p in list(human.clothesProxies.values()):
        if p.name in TOPS or (replaces_pants and p.name in PANTS):
            cl.proxyFileDeselected(p.file)
    cl.proxyFileSelected(path)
    for view, d in (("tq", (0.6, 0.0, 0.8)), ("front", (0.0, 0.0, 1.0))):
        G.modelCamera.focusOn(centre, np.array(d, float), 2.2, False)
        G.redraw()
        G.mainwin.grab().save(os.path.join(OUT, "%s_%s.png" % (label, view)))
    cl.proxyFileDeselected(path)
    done.append(label)
for f in original:
    if not any(p.file == f for p in human.clothesProxies.values()):
        cl.proxyFileSelected(f)
G.setGlobalCamera(); G.frontView(); G.redraw()
print("shot", done, "restored", sorted(p.name for p in human.clothesProxies.values()))
