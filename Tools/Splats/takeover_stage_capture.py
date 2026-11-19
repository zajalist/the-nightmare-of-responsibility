"""Editor-only stage stills. Restores the placed takeover to stage zero; no gameplay simulation."""
import json
import os
import unreal

eas=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
actors=eas.get_all_level_actors()
take=next(a for a in actors if a.get_actor_label()=='RoomTakeover')
take.set_folder_path('FX/Sand')
assert take.root_component.get_name()=='Root'
take.set_actor_location(unreal.Vector(0,0,0),False,True)
take.set_actor_scale3d(unreal.Vector(1,1,1))
records=[]
states=[]
for a in actors:
    if any(s in a.get_actor_label().lower() for s in ('art_','painting','picture')):
        records.append(dict(label=a.get_actor_label(),path=a.get_path_name(),location=str(a.get_actor_location()),
            rotation=str(a.get_actor_rotation()),scale=str(a.get_actor_scale3d()),components=[dict(name=c.get_name(),
            mesh=c.static_mesh.get_path_name() if c.static_mesh else None,materials=[c.get_material(i).get_path_name() for i in range(c.get_num_materials())])
            for c in a.get_components_by_class(unreal.StaticMeshComponent)]))
try:
    take.call_method('Reset')
    for stage in (0,3,5):
        take.call_method('SetStage',(stage,))
        for _ in range(61):take.call_method('Grow')
        states.append({'stage':take.get_editor_property('Stage'),'progress':take.get_editor_property('StageProgress'),
            'parts':[{'name':c.get_name(),'visible':c.is_visible(),'location':list(c.get_world_location().to_tuple()),
                'scale':list(c.get_world_scale().to_tuple()),'cpd':str(c.get_editor_property('custom_primitive_data')),
                'material':c.get_material(0).get_path_name() if c.get_material(0) else None}
                for c in take.get_components_by_class(unreal.StaticMeshComponent)]})
        prefix='takeover_base' if os.environ.get('WC_SRC')=='base' else 'takeover_stage'
        os.environ['WC_SHOTS']=f'{prefix}{stage}=340,-280,250,-16.9,130,90'
        if stage==5:
            os.environ['WC_SHOTS']+=';painting_sand_horse=-250,208,166,0,180,35;painting_sand_lion=240,-60,168,0,0,45'
        os.environ['WC_WARM']='5'
        exec(compile(open('P:/FoA/Tools/Splats/world_capture.py').read(),'world_capture.py','exec'),{})
finally:
    take.call_method('Reset')
with open('P:/FoA/Saved/WorldShots/painting_sources.json','w') as f:json.dump(records,f,indent=1)
with open('P:/FoA/Saved/WorldShots/takeover_stage_states.json','w') as f:json.dump(states,f,indent=1)
print('Stage stills complete, restored stage zero')
