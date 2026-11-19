# Runs INSIDE MakeHuman: waist close-ups (front, side, back, 3/4) of whatever is worn, saved to Saved/CharacterShots/makehuman/.
import numpy as np

TAG = globals().get("TAG", "waist")
shirt = next(p for p in human.clothesProxies.values() if p.name in ("crude_male_shirt", "FoA_Crude_Tee_Layered", "FoA_Polo_Layered", "Polo t-shirt"))
co = shirt.getCoords()
y = np.percentile(co[:, 1], 6)  # around the hem
centre = np.array([co[:, 0].mean(), y, co[:, 2].mean()])
for name, d in (("front", (0, 0, 1)), ("side", (1, 0, 0)), ("back", (0, 0, -1)), ("tq", (0.7, 0, 0.7)), ("poke", (-0.77, 0, 0.64))):
    G.modelCamera.focusOn(centre, np.array(d, float), 4.0, False)
    G.redraw()
    G.mainwin.grab().save(r"P:/FoA/Saved/CharacterShots/makehuman/%s_%s.png" % (TAG, name))
print("shots", TAG)
