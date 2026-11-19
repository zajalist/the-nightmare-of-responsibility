"""Fit a reused wall cube/material to the actual east doorway. No furniture transform changes."""
import unreal
bp=unreal.load_asset('/Game/FoA/Gameplay/BP_BeatDirector')
actors={a.get_actor_label():a for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()}
before={n:actors[n].get_actor_transform().export_text() for n in ('Wardrobe','Door_Bedroom','DoorFrame_Bedroom')}
center=actors['DoorFrame_Bedroom'].get_actor_location()
walls=[]
for n,a in actors.items():
    if n.startswith('Wall_'):
        o,e=a.get_actor_bounds(False)
        if o.x>370 and e.x<30: walls.append((a,o,e))
lintel=min((w for w in walls if w[1].y-w[2].y<center.y<w[1].y+w[2].y and w[1].z-w[2].z>150),
           key=lambda w:w[1].z-w[2].z)
left=max(w[1].y+w[2].y for w in walls if w[1].y+w[2].y<center.y)
right=min(w[1].y-w[2].y for w in walls if w[1].y-w[2].y>center.y)
top=lintel[1].z-lintel[2].z
source=lintel[0].get_component_by_class(unreal.StaticMeshComponent)
mesh=source.static_mesh;bounds=mesh.get_bounds();size=bounds.box_extent*2
location=unreal.Vector(lintel[1].x,(left+right)/2,top/2)
scale=unreal.Vector(lintel[2].x*2/size.x,(right-left)/size.y,top/size.z)
sub=unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem);lib=unreal.SubobjectDataBlueprintFunctionLibrary
targets=[lib.get_object_for_blueprint(lib.get_data(h),bp) for h in sub.k2_gather_subobject_data_for_blueprint(bp)
         if str(lib.get_variable_name(lib.get_data(h)))=='OldDoorWall']
targets += [c for c in actors['BeatDirector'].get_components_by_class(unreal.StaticMeshComponent) if c.get_name()=='OldDoorWall']
assert targets
for c in targets:
    c.set_static_mesh(mesh);c.set_material(0,source.get_material(0))
    c.set_editor_property('relative_location',location);c.set_editor_property('relative_rotation',unreal.Rotator())
    c.set_editor_property('relative_scale3d',scale);c.set_collision_profile_name('BlockAll')
    c.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION);c.set_visibility(False);c.set_hidden_in_game(True)
unreal.EditorAssetLibrary.save_loaded_asset(bp,False)
assert all(actors[n].get_actor_transform().export_text()==t for n,t in before.items())
print('OLD WALL fitted from',lintel[0].get_actor_label(),'location',location,'size',lintel[2].x*2,right-left,top,'material',source.get_material(0))
