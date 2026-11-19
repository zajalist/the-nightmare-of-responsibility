# Runs INSIDE MakeHuman via Tools/MPFB/mh_drive.py @Tools/MPFB/mh_teen_v1.py (G, human, mh, gui3d in scope).
import getpath
import material
import skeleton

u = lambda kind, name, ext: getpath.getPath("data/%s/%s/%s.%s" % (kind, name, name, ext))

human.resetMeshValues()
human.setGender(1.0)
human.setAgeYears(16.5)
human.setWeight(0.78)     # heavier teen
human.setMuscle(0.32)     # soft, not athletic
human.setHeight(0.44)
human.setBodyProportions(0.45)
human.applyAllTargets()

human.material = material.fromFile(u("skins", "toigo_light_skin_male_freckles", "mhmat"))

for kind, task, name in (("hair", "Hair", "cortu_short_messy_hair"),
                         ("eyebrows", "Eyebrows", "mindfront_eyebrows_05"),
                         ("eyelashes", "Eyelashes", "mindfront_eyelashes_02")):
    G.getTask("Geometries", task).proxyFileSelected(u(kind, name, "mhclo"))

clothes = G.getTask("Geometries", "Clothes")
for name in ("elvs_crude_t-shirt_male", "toigo_wool_pants", "joepal_crude_low_socks"):
    clothes.proxyFileSelected(u("clothes", name, "mhclo"))

human.setSkeleton(skeleton.load(getpath.getSysDataPath("rigs/game_engine.mhskel"), human.meshData))
G.redraw()
print("age", round(human.getAgeYears(), 1), "weight", human.getWeight(), "muscle", human.getMuscle(),
      "clothes", [p.name for p in human.clothesProxies.values()] if hasattr(human, "clothesProxies") else "?",
      "skeleton", human.getSkeleton().name if human.getSkeleton() else None)
