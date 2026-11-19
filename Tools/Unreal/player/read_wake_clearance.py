"""Read-only static capsule probes at the wake handoff; no actors are moved."""
import json
from pathlib import Path
import unreal
sub=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
assert not sub.get_game_world()
w=sub.get_editor_world()
rows=[]
actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
d=next(a for a in actors if a.get_class().get_name()=='BP_BeatDirector_C')
bed=d.get_editor_property('WakeBed')
origin,extent=bed.get_actor_bounds(False)
meta=dict(bed=bed.get_actor_label(),origin=[origin.x,origin.y,origin.z],extent=[extent.x,extent.y,extent.z])
for radius,half in ((35,90),(33.055556,85)):
    for x,y in ((269.76,-80.35),(269.76,-88.81),(269.76,-65),(288.47,-114.77)):
        start=unreal.Vector(x,y,half+2.15);end=start+unreal.Vector(0,0,.01)
        r=unreal.SystemLibrary.capsule_trace_single_by_profile(w,start,end,radius,half,
            'Pawn',False,[],unreal.DrawDebugTrace.NONE,True)
        hit=r[1] if isinstance(r,tuple) else r;t=hit.to_tuple() if hit else None
        row=dict(radius=radius,half=half,x=x,y=y,z=half+2.15,blocking=bool(t and t[0]))
        if row['blocking']:
            row.update(initial_overlap=t[1],impact=[t[5].x,t[5].y,t[5].z],normal=[t[7].x,t[7].y,t[7].z])
        rows.append(row)
Path('P:/FoA/Saved/CharacterShots/wake_capsule_static.json').write_text(json.dumps(dict(bed=meta,probes=rows),indent=1))
print(json.dumps(rows))
