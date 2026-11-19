"""Owned free-driving component templates and footprint mesh import. Parent compiles/saves."""
import os
import unreal

ROOT='/Game/FoA/Level2/Drive'
EAL=unreal.EditorAssetLibrary


def templates(path):
    bp=unreal.load_asset(path);assert bp,path
    unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(bp)
    sds=unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    lib=unreal.SubobjectDataBlueprintFunctionLibrary
    gathered=sds.k2_gather_subobject_data_for_blueprint(bp)
    handles={str(lib.get_variable_name(lib.get_data(h))):h for h in gathered}
    cs={name:lib.get_object_for_blueprint(lib.get_data(h),bp) for name,h in handles.items()}
    return bp,sds,lib,gathered,handles,cs


def collision_mesh():
    dest=ROOT+'/SM_L2CityCollision'
    def find():
        paths=EAL.list_assets(dest,recursive=True,include_folder=False) if EAL.does_directory_exist(dest) else []
        if EAL.does_asset_exist(dest):paths.append(dest)
        matches=[p for p in paths if str(EAL.find_asset_data(p).asset_class_path.asset_name)=='StaticMesh']
        assert len(matches)<=1,matches
        return unreal.load_asset(matches[0]) if matches else None
    mesh=find()
    if not mesh:
        pipe=unreal.InterchangeGenericAssetsPipeline()
        materials=pipe.get_editor_property('material_pipeline')
        materials.set_editor_property('import_materials',False)
        materials.get_editor_property('texture_pipeline').set_editor_property('import_textures',False)
        pipe.get_editor_property('mesh_pipeline').set_editor_property('build_nanite',False)
        pipe.get_editor_property('mesh_pipeline').set_editor_property('distance_field_resolution_scale',0.)
        overrides=unreal.InterchangePipelineStackOverride();overrides.add_pipeline(pipe)
        task=unreal.AssetImportTask()
        for key,value in [('filename','P:/FoA-Assets/level2/toronto/processed/free_drive_collision/SM_L2CityCollision.gltf'),
                          ('destination_path',dest),('automated',True),('save',True),('options',overrides)]:task.set_editor_property(key,value)
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        mesh=find();assert mesh,task.get_editor_property('imported_object_paths')
    body=mesh.get_editor_property('body_setup')
    body.set_editor_property('collision_trace_flag',unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
    body.set_editor_property('double_sided_geometry',True)
    dark=unreal.load_asset(ROOT+'/MI_L2Dark');assert dark
    for i in range(len(mesh.get_editor_property('static_materials'))):mesh.set_material(i,dark)
    EAL.save_loaded_asset(mesh)
    return mesh


def car():
    bp,sds,lib,gathered,handles,cs=templates(ROOT+'/BP_L2Car')
    assert 'Collision' in handles,'Run free_setup first'
    if not lib.is_root_component(lib.get_data(handles['Collision'])):
        assert sds.make_new_scene_root(gathered[0],handles['Collision'],bp)
    assert sds.attach_subobject(handles['Collision'],handles['Root'])
    for name in ('Body','Roof'):assert sds.attach_subobject(handles['Root'],handles[name])
    assert sds.attach_subobject(handles['Collision'],handles['CameraBoom'])
    assert sds.attach_subobject(handles['CameraBoom'],handles['FollowCamera'])
    collision=cs['Collision'];collision.set_box_extent(unreal.Vector(200,90,60),False)
    collision.set_collision_profile_name('Pawn')
    collision.set_collision_enabled(unreal.CollisionEnabled.QUERY_ONLY)
    collision.set_collision_response_to_channel(unreal.CollisionChannel.ECC_CAMERA,unreal.CollisionResponseType.ECR_IGNORE)
    collision.set_editor_property('relative_location',unreal.Vector(0,0,0))
    collision.set_editor_property('generate_overlap_events',False)
    cs['Root'].set_editor_property('relative_location',unreal.Vector(0,0,-65))
    boom=cs['CameraBoom']
    for key,value in [('target_arm_length',850.),('relative_location',unreal.Vector(0,0,185)),
                      ('relative_rotation',unreal.Rotator(pitch=-12,yaw=0,roll=0)),('absolute_rotation',True),
                      ('do_collision_test',True),('probe_size',18.),('enable_camera_lag',True),('camera_lag_speed',8.),
                      ('enable_camera_rotation_lag',False),('inherit_pitch',False),('inherit_yaw',False),('inherit_roll',False)]:
        boom.set_editor_property(key,value)
    boom.set_component_tick_enabled(True)
    cam=cs['FollowCamera']
    for key,value in [('absolute_location',False),('absolute_rotation',False),('relative_location',unreal.Vector(0,0,0)),
                      ('relative_rotation',unreal.Rotator(0,0,0)),('field_of_view',80.),('constrain_aspect_ratio',False),
                      ('override_aspect_ratio_axis_constraint',True),
                      ('aspect_ratio_axis_constraint',unreal.AspectRatioAxisConstraint.ASPECT_RATIO_MAINTAIN_XFOV)]:cam.set_editor_property(key,value)
    cdo=unreal.get_default_object(bp.generated_class())
    cdo.set_editor_property('CameraPitch',12.);cdo.set_editor_property('CameraYawOffset',0.)
    print('Free drive car templates: collision root, 8.5m spring arm, pitch12 FOV80')


def road():
    import importlib
    import drive_data as data
    importlib.reload(data)
    parking=('DestinationPost','BayEdgeLeft','BayEdgeRight')
    mesh=collision_mesh()
    bp,sds,lib,gathered,handles,cs=templates(ROOT+'/BP_L2RoadNetwork')
    for name in ('CityCollision','DestinationMarker','DestinationLabel','ShelterSouth','ShelterNorth','CitySky',*parking):
        assert sds.attach_subobject(handles['Root'],handles[name])
    c=cs['CityCollision'];c.set_static_mesh(mesh);c.set_collision_profile_name('BlockAll')
    c.set_editor_property('cast_shadow',False)
    c.set_editor_property('visible',False);c.set_editor_property('hidden_in_game',True)
    # Surveyed massing is collision only. Nearby and far surfaces are splats.
    c.set_editor_property('relative_location',unreal.Vector(0,0,0))
    # The shared glTF exporter stores -Y; Unreal imports that as world Y.
    c.set_editor_property('relative_scale3d',unreal.Vector(1,-1,1))
    marker=cs['DestinationMarker']
    marker.set_static_mesh(unreal.load_asset('/Engine/BasicShapes/Cube'))
    marker.set_material(0,unreal.load_asset(ROOT+'/MI_L2Dark'))
    marker.set_collision_profile_name('NoCollision');marker.set_editor_property('cast_shadow',False)
    marker.set_editor_property('relative_scale3d',unreal.Vector(.17,5.9,.8))
    marker.set_visibility(False)
    for name in parking:
        post=name=='DestinationPost';prop=cs[name]
        prop.set_static_mesh(unreal.load_asset('/Engine/BasicShapes/'+('Cylinder' if post else 'Cube')))
        prop.set_material(0,unreal.load_asset(ROOT+('/MI_L2Dark' if post else '/M_L2Flat')))
        prop.set_collision_profile_name('NoCollision');prop.set_editor_property('cast_shadow',False)
        prop.set_editor_property('relative_scale3d',unreal.Vector(*((.15,.15,2.15) if post else (5.1,.13,.025))))
        prop.set_visibility(False)
    for name in ('DestinationLabel','ShelterSouth','ShelterNorth'):
        label=cs[name]
        label.set_horizontal_alignment(unreal.HorizTextAligment.EHTA_CENTER)
        label.set_vertical_alignment(unreal.VerticalTextAligment.EVRTA_TEXT_CENTER)
        label.set_text_render_color(unreal.Color(245,245,245,255))
        label.set_world_size(52.)
        label.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
        label.set_editor_property('cast_shadow',False)
    cs['DestinationLabel'].set_visibility(False)
    for name,position,yaw in zip(('ShelterSouth','ShelterNorth'),data.SHELTERS,(-90,90)):
        label=cs[name];label.set_text(unreal.Text('SHELTER\nSlow to recover'))
        label.set_editor_property('relative_location',unreal.Vector(position[0],position[1],310))
        label.set_editor_property('relative_rotation',unreal.Rotator(yaw=yaw))
    sky=cs['CitySky'];sky.set_static_mesh(unreal.load_asset('/Engine/BasicShapes/Sphere'))
    sky.set_material(0,unreal.load_asset('/Game/FoA/Level2/Dream/M_L2_PanoSky'))
    sky.set_collision_profile_name('NoCollision');sky.set_editor_property('cast_shadow',False)
    sky.set_editor_property('relative_location',unreal.Vector(30000,0,0))
    sky.set_editor_property('relative_scale3d',unreal.Vector(1600,1600,1600))
    print('Free drive road templates: surveyed collision, street signs, shelters and procedural sky')


if __name__=='__main__':
    assert os.environ.get('FOA_LEASE'),'Parent asset lease required'
    assert not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world(),'Stop PIE first'
    {'car':car,'road':road}[os.environ['FOA_FREE_SETUP']]()
