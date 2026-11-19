"""Configure only BP_L2StopSet templates. No level actors/source assets are mutated."""
import sys
import importlib
import unreal
sys.path.insert(0,'P:/FoA/Tools/Unreal/level2')
import stop_set_data as D
importlib.reload(D)


def main():
    assert unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world() is None
    bp=unreal.load_asset(D.BP);assert bp
    unreal.get_editor_subsystem(unreal.EditorActorSubsystem).select_nothing()
    unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(bp)
    sds=unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem);lib=unreal.SubobjectDataBlueprintFunctionLibrary
    handles=sds.k2_gather_subobject_data_for_blueprint(bp)
    hs={str(lib.get_variable_name(lib.get_data(h))):h for h in handles}
    if not lib.is_root_component(lib.get_data(hs['Root'])):assert sds.make_new_scene_root(handles[0],hs['Root'],bp)
    def obj(name,parent='Root'):
        if name!='Root':assert sds.attach_subobject(hs[parent],hs[name])
        return lib.get_object_for_blueprint(lib.get_data(hs[name]),bp)
    for group in D.GROUPS:obj(group)
    for group,parent in D.EXTRA_GROUPS:obj(group,parent)
    for name,parent,path,at,size,material in D.MESHES:
        comp=obj(name,parent);mesh=unreal.load_asset(path);assert mesh,path
        comp.set_static_mesh(mesh)
        comp.set_editor_property('override_materials',[])
        bounds=mesh.get_bounds();extent=bounds.box_extent;origin=bounds.origin
        scale=[size[i]/max(2*extent.to_tuple()[i],.01) for i in range(3)]
        loc=[at[0]-origin.x*scale[0],at[1]-origin.y*scale[1],at[2]-(origin.z-extent.z)*scale[2]]
        comp.set_editor_property('relative_location',unreal.Vector(*loc))
        comp.set_editor_property('relative_scale3d',unreal.Vector(*scale))
        comp.set_editor_property('relative_rotation',unreal.Rotator(roll=D.LABEL_ROLL[int(name[-1])]) if name.startswith('Label') else unreal.Rotator())
        if name=='CareerGlass':
            # One transparent pane rather than six overlapping cube faces.
            comp.set_editor_property('relative_scale3d',unreal.Vector(size[2]/100,size[1]/100,1))
            comp.set_editor_property('relative_location',unreal.Vector(at[0],at[1],at[2]+size[2]/2))
            comp.set_editor_property('relative_rotation',unreal.Rotator(pitch=90,yaw=0,roll=0))
            comp.set_editor_property('cast_shadow',False)
        comp.set_collision_profile_name('BlockAll' if name=='Floor' else 'NoCollision')
        comp.set_editor_property('generate_overlap_events',False)
        comp.set_editor_property('can_character_step_up_on',unreal.CanBeCharacterBase.ECB_NO)
        if material:
            mat=unreal.load_asset(material);assert mat,material
            for i in range(comp.get_num_materials()):comp.set_material(i,mat)
    for name,parent,line,at,size in D.SIGNS:
        comp=obj(name,parent)
        comp.set_absolute(False,False,True)
        comp.set_editor_property('relative_scale3d',unreal.Vector(1,1,1))
        if name.startswith('LabelText'):at=(-55,0,0)
        if name=='TicketNumber':at=(0,0,60)
        comp.set_editor_property('relative_location',unreal.Vector(*at))
        comp.set_editor_property('relative_rotation',unreal.Rotator(pitch=90,yaw=0,roll=0) if name=='TicketNumber' else unreal.Rotator(pitch=0,yaw=180,roll=0))
        comp.set_text(unreal.Text(line));comp.set_world_size(size)
        comp.set_text_render_color(unreal.Color(245,245,245,255) if name in D.WHITE_SIGNS else unreal.Color(12,12,12,255))
        comp.set_horizontal_alignment(unreal.HorizTextAligment.EHTA_CENTER)
        comp.set_vertical_alignment(unreal.VerticalTextAligment.EVRTA_TEXT_CENTER)
        comp.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
    player=unreal.load_asset('/Game/FoA/Characters/Player/BP_FoAPlayer');assert player
    sources={str(lib.get_variable_name(lib.get_data(h))):lib.get_object_for_blueprint(lib.get_data(h),player)
             for h in sds.k2_gather_subobject_data_for_blueprint(player)}
    for name,parent,at,yaw in D.FIGURES:
        comp=obj(name,parent)
        comp.set_editor_property('relative_location',unreal.Vector(*at))
        comp.set_editor_property('relative_rotation',unreal.Rotator(yaw=yaw-90))
        comp.set_editor_property('relative_scale3d',unreal.Vector(.94,.94,.94))
        parts=[(comp,sources['Body'])] if name in D.STAFF else []
        if name in D.STAFF:
            parts.append((obj(name+'Face',name),sources['Face']))
            suit=obj(name+'Suit',name)
            suit.set_skeletal_mesh_asset(unreal.load_asset('/Game/FoA/Characters/Teen/Mesh/SK_Teen_Suit'))
            suit.set_editor_property('relative_location',unreal.Vector())
            suit.set_editor_property('relative_rotation',unreal.Rotator())
            suit.set_editor_property('relative_scale3d',unreal.Vector(1,1,1))
            material=unreal.load_asset('/Game/FoA/Characters/Teen/Cloth/MI_Teen_Suit')
            for i in range(suit.get_num_materials()):suit.set_material(i,material)
            parts.append((suit,None))
        else:
            comp.set_skeletal_mesh_asset(unreal.load_asset(D.MANNY))
            comp.set_editor_property('override_materials',[])
            parts=[(comp,None)]
        for part,source in parts:
            if source:
                part.set_skeletal_mesh_asset(source.get_editor_property('skeletal_mesh_asset'))
                part.set_editor_property('override_materials',[])
                for i in range(source.get_num_materials()):part.set_material(i,source.get_material(i))
            part.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
            part.set_editor_property('generate_overlap_events',False)
            part.set_editor_property('disable_post_process_blueprint',True)
            part.set_editor_property('visibility_based_anim_tick_option',unreal.VisibilityBasedAnimTickOption.ALWAYS_TICK_POSE_AND_REFRESH_BONES)
            part.set_editor_property('use_bounds_from_leader_pose_component',False)
            part.set_editor_property('use_attach_parent_bound',False)
    camera=obj('StageCamera');camera.set_field_of_view(D.CAMERA_FOV)
    for name,at,rot,intensity in D.LIGHTS:
        comp=obj(name);comp.set_editor_property('relative_location',unreal.Vector(*at))
        comp.set_editor_property('relative_rotation',unreal.Rotator(pitch=rot[0],yaw=rot[1],roll=rot[2]))
        comp.set_editor_property('intensity_units',unreal.LightUnits.LUMENS)
        comp.set_editor_property('intensity',intensity);comp.set_editor_property('attenuation_radius',1100)
        comp.set_editor_property('source_width',200);comp.set_editor_property('source_height',140)
        comp.set_editor_property('cast_shadows',True)
    unreal.EditorAssetLibrary.save_loaded_asset(bp,False)
    print('Stop-set templates configured; native compile/save follows')


main()
