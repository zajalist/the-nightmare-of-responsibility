"""Read-only: every level actor's label, class, transform and bounds -> Saved/StoryShots/actors.json (intro shot planning)."""
import json
import unreal
rows = []
for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
    l, r = a.get_actor_location(), a.get_actor_rotation()
    o, e = a.get_actor_bounds(False)
    rows.append(dict(label=a.get_actor_label(), cls=a.get_class().get_name(), loc=[round(l.x), round(l.y), round(l.z)],
                     rot=[round(r.pitch, 1), round(r.yaw, 1), round(r.roll, 1)], hidden=a.is_hidden_ed(),
                     bmin=[round(o.x - e.x), round(o.y - e.y), round(o.z - e.z)], bmax=[round(o.x + e.x), round(o.y + e.y), round(o.z + e.z)]))
open('P:/FoA/Saved/StoryShots/actors.json', 'w').write(json.dumps(rows, indent=0))
print(len(rows))
