"""Story lane, read only: candidate in-bay views for the final reach (vase on the sill, its fall, the sand boss rising),
replacing the ClueViewVase/ClueViewBoss markers that look through the closed bay curtain (main's decision (b)).
For each candidate: collision traces (complex) to the vase, the floor pile and the boss focus, one from the landing
(same open space), a 12 cm sphere overlap (not inside a wall), and whether the sight line crosses the curtain's
bounds (the curtain has no collision, so a trace cannot see it). -> Saved/StoryShots/bay_views.json"""
import json
import unreal

w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
room = unreal.GameplayStatics.get_actor_of_class(w, unreal.load_class(None, '/Game/FoA/Gameplay/Ambient/BP_RoomTakeover.BP_RoomTakeover_C'))
comps = {c.get_name(): c for c in room.get_components_by_class(unreal.SceneComponent)}
marks = {n: comps[n].get_world_location() for n in comps if n.startswith('Clue') and ('Vase' in n or 'Boss' in n)}
curtain = next(a for a in unreal.EditorLevelLibrary.get_all_level_actors() if a.get_actor_label() == 'Dress_Curtains_Bay')
co, ce = curtain.get_actor_bounds(False)
VASE = unreal.Vector(-15, -379, 100)
PILE = unreal.Vector(-15, -345, 10)
BOSS = marks.get('ClueFocusBoss', unreal.Vector(-15, -345, 90))
LAND = unreal.Vector(-55, -335, 120)
VIS = unreal.TraceTypeQuery.TRACE_TYPE_QUERY1


def blocked(a, b):
    hit = unreal.SystemLibrary.line_trace_single(w, a, b, VIS, True, [], unreal.DrawDebugTrace.NONE, True)
    if not hit:
        return None
    t = hit.to_tuple()
    return (t[9].get_actor_label() if t[9] else None, round(t[3], 1))


def crosses_curtain(a, b):
    lo_y, hi_y = co.y - ce.y, co.y + ce.y
    for i in range(1, 40):
        p = a + (b - a) * (i / 40.0)
        if lo_y <= p.y <= hi_y and co.x - ce.x <= p.x <= co.x + ce.x and p.z <= co.z + ce.z:
            return True
    return False


rows = []
for x in (-170, -130, -90, 40, 70, 100):
    for y in (-315, -330, -350):
        for z in (110, 140, 170):
            v = unreal.Vector(x, y, z)
            inside = unreal.SystemLibrary.sphere_overlap_actors(w, v, 12.0, [unreal.ObjectTypeQuery.OBJECT_TYPE_QUERY1], None, [])
            rows.append(dict(view=(x, y, z), inside=[a.get_actor_label() for a in inside or []],
                             from_landing=blocked(LAND, v), vase=blocked(v, VASE), pile=blocked(v, PILE), boss=blocked(v, BOSS),
                             curtain=crosses_curtain(v, VASE) or crosses_curtain(v, PILE) or crosses_curtain(v, BOSS)))
good = [r for r in rows if not r['inside'] and not r['from_landing'] and not r['vase'] and not r['pile'] and not r['boss'] and not r['curtain']]
out = dict(markers={k: v.to_tuple() for k, v in marks.items()}, curtain=dict(origin=co.to_tuple(), extent=ce.to_tuple()),
           boss_focus=BOSS.to_tuple(), good=[r['view'] for r in good], rows=rows)
open('P:/FoA/Saved/StoryShots/bay_views.json', 'w').write(json.dumps(out, indent=1, default=str))
print('bay views good', len(good), 'of', len(rows))
