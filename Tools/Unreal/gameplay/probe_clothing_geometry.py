"""Read existing room bounds around the proposed freed-shirt location."""
import json
from pathlib import Path
import unreal
rows=[];point=(150.6763772964477,-190.40969467163086,38.48026657104492)
for actor in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
    for component in actor.get_components_by_class(unreal.StaticMeshComponent):
        if not component.get_editor_property('static_mesh'):continue
        o,e,_=unreal.SystemLibrary.get_component_bounds(component)
        lo=[o.x-e.x,o.y-e.y,o.z-e.z];hi=[o.x+e.x,o.y+e.y,o.z+e.z]
        if not all(lo[i]-60<=point[i]<=hi[i]+60 for i in (0,1)):continue
        if hi[2]<0 or lo[2]>150:continue
        rows.append(dict(actor=actor.get_actor_label(),component=component.get_name(),min=lo,max=hi,
            collision=str(component.get_collision_enabled()),contains_shirt=all(lo[i]<=point[i]<=hi[i] for i in range(3))))
Path('P:/FoA/Saved/Integration/clothing_geometry.json').write_text(json.dumps(rows,indent=1))
print('CLOTHING_GEOMETRY',json.dumps(rows))
