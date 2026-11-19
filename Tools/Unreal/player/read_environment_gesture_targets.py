"""Read real placed interaction geometry and anchors; no asset/world mutations."""
import unreal,json
from pathlib import Path
assert not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
def xf(t):return dict(position=list(t.translation.to_tuple()),rotation=list(t.rotation.to_tuple()),scale=list(t.scale3d.to_tuple()))
rows=[]
for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
    if a.get_actor_label() not in ('Door_Bedroom','Wardrobe_GothicCabinet_01_door1','Commode_GothicCommode_01_door01'):continue
    row=dict(label=a.get_actor_label(),path=a.get_path_name(),world=xf(a.get_actor_transform()),components={})
    for c in a.get_components_by_class(unreal.SceneComponent):
        part=dict(path=c.get_path_name(),world=xf(c.get_world_transform()),relative=xf(c.get_relative_transform()))
        if isinstance(c,unreal.StaticMeshComponent) and c.static_mesh:
            box=c.static_mesh.get_bounding_box();part.update(mesh=c.static_mesh.get_path_name(),bounds_min=list(box.min.to_tuple()),bounds_max=list(box.max.to_tuple()))
        row['components'][c.get_name()]=part
    rows.append(row)
Path('P:/FoA/Saved/Integration/environment_gesture_targets.json').write_text(json.dumps(rows,indent=2))
print('Read placed targets',[(r['label'],list(r['components'])) for r in rows])
