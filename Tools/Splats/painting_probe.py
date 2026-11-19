import json
import unreal
out=[]
for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
    if a.get_actor_label() in ('Art_Whistlejacket_Canvas','Art_StubbsLion_Canvas','Art_Hammershoi_Lux3D'):
        c=a.get_component_by_class(unreal.StaticMeshComponent)
        o,e,_=unreal.SystemLibrary.get_component_bounds(c)
        out.append({'label':a.get_actor_label(),'centre':list(o.to_tuple()),'extent':list(e.to_tuple()),'transform':str(c.get_world_transform())})
with open('P:/FoA/Saved/WorldShots/painting_bounds.json','w') as f:json.dump(out,f,indent=1)
print(out)
