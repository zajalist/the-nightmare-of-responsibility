"""Read-only material audit of sand mesh components in editor and current PIE worlds."""
import json
from pathlib import Path
import unreal
rows=[]
sys=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
for name,w in [('editor',sys.get_editor_world()),('pie',sys.get_game_world())]:
 if not w:continue
 for a in unreal.GameplayStatics.get_all_actors_of_class(w,unreal.Actor):
  for c in a.get_components_by_class(unreal.StaticMeshComponent):
   mesh=c.static_mesh
   if not mesh or not any(x in (mesh.get_path_name()+a.get_name()+c.get_name()).lower() for x in ('sand','mound','takeover')):continue
   materials=[]
   for i in range(c.get_num_materials()):
    m=c.get_material(i)
    materials.append({'slot':i,'path':m.get_path_name() if m else None,'parent':m.get_editor_property('parent').get_path_name() if isinstance(m,unreal.MaterialInstanceConstant) and m.get_editor_property('parent') else None})
   p=c.get_world_location();s=c.get_world_scale()
   rows.append(dict(world=name,actor=a.get_name(),label=a.get_actor_label(),component=c.get_name(),mesh=mesh.get_path_name(),materials=materials,visible=c.is_visible(),location=[p.x,p.y,p.z],scale=[s.x,s.y,s.z]))
Path('P:/FoA/Saved/WorldShots/sand_material_audit.json').write_text(json.dumps(rows,indent=1))
print('Read-only sand audit',len(rows))
