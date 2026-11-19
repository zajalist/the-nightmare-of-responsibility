"""qa lane, read-only: validate the playtest's stand-point probe (capsule overlap) in the editor world."""
import math

import unreal

w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
acts = {a.get_actor_label(): a for a in unreal.GameplayStatics.get_all_actors_of_class(w, unreal.Actor)}
OT = [unreal.ObjectTypeQuery.OBJECT_TYPE_QUERY1, unreal.ObjectTypeQuery.OBJECT_TYPE_QUERY2]


def fits(x, y):
    return not unreal.SystemLibrary.capsule_overlap_actors(w, unreal.Vector(x, y, 94), 38, 86, OT, None, [])


print('centre fits', fits(0, 0), 'inside bed fits', fits(270, -191))
for label in ('Bed', 'Boot_L', 'Door_Bedroom', 'Hanger_CoatRail', 'Desk', 'Wardrobe'):
    a = acts[label]
    lo = hi = None
    for c in a.get_components_by_class(unreal.StaticMeshComponent):
        if not c.is_visible() or not c.get_editor_property('static_mesh'):
            continue
        o, e, _ = unreal.SystemLibrary.get_component_bounds(c)
        lo = [min(p, q) for p, q in zip(lo, (o - e).to_tuple())] if lo else list((o - e).to_tuple())
        hi = [max(p, q) for p, q in zip(hi, (o + e).to_tuple())] if hi else list((o + e).to_tuple())
    o = [(p + q) / 2 for p, q in zip(lo, hi)]
    e = [(q - p) / 2 for p, q in zip(lo, hi)]
    base = math.atan2(-o[1], -o[0])
    found = None
    for deg in (0, 25, -25, 50, -50, 80, -80, 115, -115):
        ang = base + math.radians(deg)
        dx, dy = math.cos(ang), math.sin(ang)
        dist = min(abs(dx) * e[0] + abs(dy) * e[1] + 45, 170)
        x, y = o[0] + dx * dist, o[1] + dy * dist
        if abs(x) < 360 and abs(y) < 290 and fits(x, y):
            found = (round(x), round(y), deg)
            break
    print(label, 'centre', [round(v) for v in o], 'ext', [round(v) for v in e], 'stand', found)
