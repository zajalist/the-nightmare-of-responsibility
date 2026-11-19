"""Read-only: room actors (furniture, lights, windows, volumes) with transform, bounds and light settings -> Saved/Cinematics/room.txt."""
import os
import unreal
W = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
keys = ("bed", "night", "lamp", "lantern", "light", "moon", "clock", "pillow", "window", "sky", "fog", "post", "desk", "wardrobe", "rug", "player", "fire", "sand", "curtain", "bay", "shaft")
rows = []
for a in unreal.GameplayStatics.get_all_actors_of_class(W, unreal.Actor):
    lab = a.get_actor_label()
    if "_hand" in lab or not any(k in lab.lower() for k in keys):
        continue
    l, r = a.get_actor_location(), a.get_actor_rotation()
    o, e = a.get_actor_bounds(False)
    extra = ""
    lc = a.get_component_by_class(unreal.LightComponent)
    if lc:
        c = lc.get_editor_property("light_color")
        extra = " I=%.3f unit=%s col=(%d,%d,%d) shadows=%s" % (lc.get_editor_property("intensity"), lc.get_editor_property("intensity_units") if isinstance(lc, unreal.LocalLightComponent) else "-", c.r, c.g, c.b, lc.get_editor_property("cast_shadows"))
    rows.append("%s | %s | loc(%.0f,%.0f,%.0f) rot(p%.0f,y%.0f,r%.0f) | bo(%.0f,%.0f,%.0f) be(%.0f,%.0f,%.0f)%s | %s" % (lab, a.get_class().get_name(), l.x, l.y, l.z, r.pitch, r.yaw, r.roll, o.x, o.y, o.z, e.x, e.y, e.z, extra, a.get_folder_path()))
os.makedirs("P:/FoA/Saved/Cinematics", exist_ok=True)
with open("P:/FoA/Saved/Cinematics/room.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(sorted(rows)))
print("rows", len(rows))
