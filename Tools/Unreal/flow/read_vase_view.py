"""Story lane, read only: the final-reach vase shot markers (BP_RoomTakeover ClueViewVase/ClueFocusVase), what a
visibility trace from the view to the focus hits first, and the actors near the view point.
-> Saved/StoryShots/vase_view.json"""
import json
import unreal

w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
room = unreal.GameplayStatics.get_actor_of_class(w, unreal.load_class(None, '/Game/FoA/Gameplay/Ambient/BP_RoomTakeover.BP_RoomTakeover_C'))
comps = {c.get_name(): c for c in room.get_components_by_class(unreal.SceneComponent)}
out = dict(markers={n: comps[n].get_world_location().to_tuple() for n in comps if 'Vase' in n})
view, focus = comps['ClueViewVase'].get_world_location(), comps['ClueFocusVase'].get_world_location()
hits = unreal.SystemLibrary.line_trace_multi(w, view, focus, unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, True, [], unreal.DrawDebugTrace.NONE, True)
out['trace'] = []
for hit in hits or []:
    t = hit.to_tuple()
    out['trace'].append(dict(actor=t[9].get_actor_label() if t[9] else None, comp=t[10].get_name() if t[10] else None, dist=round(t[3], 1)))
near = []
for a in unreal.GameplayStatics.get_all_actors_of_class(w, unreal.Actor):
    o, e = a.get_actor_bounds(False)
    if abs(o.x - view.x) < e.x + 30 and abs(o.y - view.y) < e.y + 30 and abs(o.z - view.z) < e.z + 30:
        near.append(dict(actor=a.get_actor_label(), cls=a.get_class().get_name(), origin=o.to_tuple(), extent=e.to_tuple()))
out['near_view'] = near[:20]
open('P:/FoA/Saved/StoryShots/vase_view.json', 'w').write(json.dumps(out, indent=1, default=str))
