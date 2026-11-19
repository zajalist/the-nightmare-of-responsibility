"""Story lane, read only: the T8 encounter's PlayerMark world transform and the payoff camera candidates around it
(low three-quarter, both sides) with a visibility trace from each candidate to the hero's chest.
-> Saved/StoryShots/payoff_marks.json"""
import json
import unreal

w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
enc = [a for a in unreal.GameplayStatics.get_all_actors_of_class(w, unreal.load_class(None, '/Game/FoA/Gameplay/Encounter/BP_Encounter.BP_Encounter_C'))]
out = []
for a in enc:
    mark = next(c for c in a.get_components_by_class(unreal.ArrowComponent) if c.get_name() == 'PlayerMark')
    t = mark.get_world_transform()
    row = dict(actor=a.get_actor_label(), loc=a.get_actor_location().to_tuple(), yaw=a.get_actor_rotation().yaw,
               mark=t.translation.to_tuple(), mark_yaw=t.rotation.rotator().yaw, cams=[])
    for side in (-1, 1):
        for fwd, lat in ((155.6, 109.0), (140.0, 140.0), (175.0, 80.0)):
            loc = unreal.MathLibrary.transform_location(t, unreal.Vector(fwd, side * lat, -37.0))
            aim = unreal.MathLibrary.transform_location(t, unreal.Vector(0, 0, 23.0))
            hit = unreal.SystemLibrary.line_trace_single(w, loc, aim, unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, False, [], unreal.DrawDebugTrace.NONE, True)
            blocked = None
            if hit:
                h = hit.to_tuple()
                blocked = (h[9].get_actor_label() if h[9] else None, round(h[3], 1))  # hit actor, distance
            row['cams'].append(dict(side=side, fwd=fwd, lat=lat, loc=loc.to_tuple(), aim=aim.to_tuple(), blocked=blocked))
    out.append(row)
open('P:/FoA/Saved/StoryShots/payoff_marks.json', 'w').write(json.dumps(out, indent=1, default=str))
