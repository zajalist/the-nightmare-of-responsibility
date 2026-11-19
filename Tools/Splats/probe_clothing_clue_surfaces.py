"""Read-only editor geometry for authored clothing clues; run outside PIE only."""
import json,itertools,unreal
from pathlib import Path
assert unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world() is None
actors={a.get_actor_label():a for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()}
result={}
for label in ['Wardrobe','Desk','Bed','Shirt_T7']:
 a=actors[label];rows=[]
 for component in a.get_components_by_class(unreal.StaticMeshComponent):
  mesh=component.get_editor_property('static_mesh')
  if not mesh:continue
  o,e,_=unreal.SystemLibrary.get_component_bounds(component)
  rows.append({'component':component.get_name(),'mesh':mesh.get_path_name(),
   'min':list((o-e).to_tuple()),'max':list((o+e).to_tuple()),
   'transform':str(component.get_world_transform()),
   'materials':[m.get_path_name() if m else None for m in component.get_materials()]})
 result[label]={'transform':str(a.get_actor_transform()),'location':list(a.get_actor_location().to_tuple()),'components':rows}
 if label=='Wardrobe':
  pivot=a.get_editor_property('Pivot');old=pivot.get_world_transform()
  pose=a.get_editor_property('Poses')[unreal.Name('Fallen')]
  points=[]
  for row in rows:
   for xyz in itertools.product(*zip(row['min'],row['max'])):
    local=old.inverse_transform_location(unreal.Vector(*xyz))
    points.append(a.get_actor_transform().transform_location(pose.transform_location(local)))
  result[label]['fallen_min']=[min(getattr(p,k) for p in points) for k in ('x','y','z')]
  result[label]['fallen_max']=[max(getattr(p,k) for p in points) for k in ('x','y','z')]
result['paper_actors']=[label for label in actors if any(s in label.lower() for s in ('paper','book','desk'))]
Path('P:/FoA/Saved/Integration/clothing_clue_surfaces.json').write_text(json.dumps(result,indent=1))
print(json.dumps(result,indent=1))
