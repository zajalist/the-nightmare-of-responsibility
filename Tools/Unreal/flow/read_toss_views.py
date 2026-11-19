"""Story lane, read only (QA B2): candidates for the toss cutaway's wide view and for a floor spot to stand up on after
the hanger kneel. Wide view: clear of walls (12 cm sphere), clear sight lines to the landing and the arc's middle,
the kneeling player's head outside the field of view (QA's check: half FOV + 5 deg) and at least 80 cm away. Floor
spot: the player's standing capsule fits (no WorldStatic overlap) and a trace down finds the floor.
-> Saved/StoryShots/toss_views.json"""
import json
import math
import sys

import unreal

sys.path.insert(0, 'P:/FoA/Tools/Unreal/flow')
from clothing_chase_contract import LANDINGS, SNAG, PULL_DISTANCE  # noqa: E402

w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
VIS = unreal.TraceTypeQuery.TRACE_TYPE_QUERY1
STATIC = [unreal.ObjectTypeQuery.OBJECT_TYPE_QUERY1]
cdo = unreal.get_default_object(unreal.load_class(None, '/Game/FoA/Characters/Player/BP_FoAPlayer.BP_FoAPlayer_C'))
cap = cdo.get_editor_property('capsule_component')
R, HH = cap.get_unscaled_capsule_radius(), cap.get_unscaled_capsule_half_height()
STANCE = unreal.Vector(269.759, -95.0, 87.15)
HEAD = unreal.Vector(269.759, -95.0, 95.0)  # kneeling: the head sits about at standing capsule centre height
START = unreal.Vector(SNAG[0], SNAG[1] + PULL_DISTANCE, SNAG[2] + 12)
LAND = unreal.Vector(*LANDINGS[0])
MID = (START + LAND) * 0.5 + unreal.Vector(0, 0, 60)


def blocked(a, b):
    hit = unreal.SystemLibrary.line_trace_single(w, a, b, VIS, True, [], unreal.DrawDebugTrace.NONE, True)
    if not hit:
        return None
    t = hit.to_tuple()
    return (t[9].get_actor_label() if t[9] else None, round(t[3], 1))


def angle(cam, look_at, point):
    f = look_at - cam
    f.normalize()
    to = point - cam
    to.normalize()
    return math.degrees(math.acos(max(-1.0, min(1.0, f.x * to.x + f.y * to.y + f.z * to.z))))


views = []
for x in (150, 190, 215, 240):
    for y in (-40, -20, 10, 40):
        for z in (140, 170):
            cam = unreal.Vector(x, y, z)
            focus = unreal.Vector(140, -80, 40)  # the landing end of the arc
            inside = unreal.SystemLibrary.sphere_overlap_actors(w, cam, 12.0, STATIC, None, [])
            views.append(dict(view=(x, y, z), focus=focus.to_tuple(), inside=[a.get_actor_label() for a in inside or []],
                              land=blocked(cam, LAND), mid=blocked(cam, MID), head_angle=round(angle(cam, focus, HEAD), 1),
                              start_angle=round(angle(cam, focus, START), 1), land_angle=round(angle(cam, focus, LAND), 1),
                              head_cm=round((cam - HEAD).length())))
good_views = [v for v in views if not v['inside'] and not v['land'] and not v['mid'] and v['head_angle'] > 45 + 2
              and v['land_angle'] < 30 and v['head_cm'] >= 80]
spots = []
for dx, dy in ((0, 40), (0, 60), (-40, 50), (40, 50), (-60, 30), (0, 80), (-90, 60)):
    p = unreal.Vector(STANCE.x + dx, STANCE.y + dy, HH + 4)
    over = unreal.SystemLibrary.capsule_overlap_actors(w, p, R, HH, STATIC, None, [])
    down = unreal.SystemLibrary.line_trace_single(w, p, p - unreal.Vector(0, 0, 300), VIS, True, [], unreal.DrawDebugTrace.NONE, True)
    floor = round(down.to_tuple()[4].z, 1) if down else None  # impact point z
    spots.append(dict(spot=p.to_tuple(), overlaps=[a.get_actor_label() for a in over or []], floor_z=floor))
good_spots = [s for s in spots if not s['overlaps'] and s['floor_z'] is not None and abs(s['floor_z']) < 6]
out = dict(capsule=(R, HH), start=START.to_tuple(), land=LAND.to_tuple(), good_views=[v['view'] for v in good_views],
           good_spots=[s['spot'] for s in good_spots], views=views, spots=spots)
open('P:/FoA/Saved/StoryShots/toss_views.json', 'w').write(json.dumps(out, indent=1, default=str))
print('toss views good', len(good_views), 'spots good', len(good_spots))
