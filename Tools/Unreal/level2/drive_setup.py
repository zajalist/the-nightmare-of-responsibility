"""Short structural operations missing native graph nodes: input assets, SCS templates and event nodes.
Run with ue_remote.py FOA_DRIVE_SETUP=assets|components|events inside the Drive asset lease.
"""
import json
import os
import sys
import unreal

sys.path.insert(0,'P:/FoA/Tools/Unreal/level2')
import drive_data as D
import importlib
importlib.reload(D)
exec(open('P:/FoA/Tools/Unreal/encounter/enc_graph.py').read())
CAR=D.ROOT+'/BP_L2Car';ROAD=D.ROOT+'/BP_L2RoadNetwork';MET=D.ROOT+'/BP_Meteor';HUD=D.ROOT+'/WBP_L2Drive'
EAL=unreal.EditorAssetLibrary
AT=unreal.AssetToolsHelpers.get_asset_tools()
BINDINGS={'Throttle':('W','Gamepad_RightTrigger'), 'Brake':('S','Gamepad_LeftTrigger'),
          'Left':('A','Gamepad_DPad_Left'), 'Right':('D','Gamepad_DPad_Right'),
          'Turn':('Q','Gamepad_LeftShoulder'), 'Brace':('SpaceBar','Gamepad_FaceButton_Bottom'),
          'Continue':('Enter','Gamepad_FaceButton_Top')}


def cpath(path):return path+'.'+path.rsplit('/',1)[1]+'_C'


def clean(path):
    bp=unreal.load_asset(path)
    BEL.compile_blueprint(bp)
    assert bp.get_editor_property('status') in (unreal.BlueprintStatus.BS_UP_TO_DATE,unreal.BlueprintStatus.BS_UP_TO_DATE_WITH_WARNINGS),path
    EAL.save_loaded_asset(bp)


def assets():
    folder=D.ROOT+'/Input'
    imc=unreal.load_asset(folder+'/IMC_L2Drive') or AT.create_asset('IMC_L2Drive',folder,unreal.InputMappingContext,unreal.InputMappingContext_Factory())
    for name,keys in BINDINGS.items():
        ia=unreal.load_asset(folder+'/IA_L2'+name) or AT.create_asset('IA_L2'+name,folder,unreal.InputAction,unreal.InputAction_Factory())
        ia.set_editor_property('value_type',unreal.InputActionValueType.BOOLEAN)
        existing={(str(m.action.get_name()),str(m.key.get_editor_property('key_name'))) for m in imc.get_editor_property('default_key_mappings').get_editor_property('mappings')}
        for key in keys:
            if (ia.get_name(),key) not in existing:
                k=unreal.Key();k.set_editor_property('key_name',key);imc.map_key(ia,k)
        EAL.save_loaded_asset(ia)
    EAL.save_loaded_asset(imc)
    path=D.ROOT+'/MPC_L2DriveImpact'
    mpc=unreal.load_asset(path) or AT.create_asset('MPC_L2DriveImpact',D.ROOT,unreal.MaterialParameterCollection,unreal.MaterialParameterCollectionFactoryNew())
    if not mpc.get_editor_property('vector_parameters'):
        p=unreal.CollectionVectorParameter();p.set_editor_property('parameter_name','Impact0');p.set_editor_property('default_value',unreal.LinearColor(0,0,-10000,0))
        mpc.set_editor_property('vector_parameters',[p]);EAL.save_loaded_asset(mpc)
    print('DRIVE input and isolated Impact0 collection saved')


def mesh():
    if not EAL.does_asset_exist(D.ROOT+'/SM_L2Ring/StaticMeshes/SM_L2Ring'):
        task=unreal.AssetImportTask()
        for key,value in [('filename','P:/FoA/Saved/Codex/l2_drive/generated/SM_L2Ring.gltf'),('destination_path',D.ROOT),
                          ('automated',True),('save',True)]:task.set_editor_property(key,value)
        AT.import_asset_tasks([task])
        print('DRIVE ring imported',task.get_editor_property('imported_object_paths'))


def templates(path):
    bp=unreal.load_asset(path)
    unreal.get_editor_subsystem(unreal.EditorActorSubsystem).select_nothing()
    unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(bp)
    sds=unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem);lib=unreal.SubobjectDataBlueprintFunctionLibrary
    allhandles=sds.k2_gather_subobject_data_for_blueprint(bp)
    handles={str(lib.get_variable_name(lib.get_data(h))):h for h in allhandles}
    root='Collision' if 'Collision' in handles else 'Root'
    if not lib.is_root_component(lib.get_data(handles[root])):
        assert sds.make_new_scene_root(allhandles[0],handles[root],bp)
    for name,handle in handles.items():
        if name not in ('Root','DefaultSceneRoot') and name in ('Body','Roof','CameraBoom','FollowCamera','Shadow','Ring',*['Rail'+str(i) for i in range(8)]):
            assert sds.attach_subobject(handles['Root'],handle)
    return bp,{name:lib.get_object_for_blueprint(lib.get_data(handle),bp) for name,handle in handles.items()}


def roads():
    bp=unreal.load_asset(ROAD)
    unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(bp)
    sds=unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem);lib=unreal.SubobjectDataBlueprintFunctionLibrary
    cs={str(lib.get_variable_name(lib.get_data(h))):lib.get_object_for_blueprint(lib.get_data(h),bp)
        for h in sds.k2_gather_subobject_data_for_blueprint(bp)}
    for i,points in enumerate(D.RAILS):
        s=cs['Rail'+str(i)];s.clear_spline_points(False)
        for p in points:s.add_spline_point(unreal.Vector(*p),unreal.SplineCoordinateSpace.LOCAL,False)
        for j in range(len(points)):s.set_spline_point_type(j,unreal.SplinePointType.LINEAR,False)
        s.update_spline();s.set_editor_property('editor_unselected_spline_segment_color',unreal.LinearColor(.3,.3,.3,1))
    EAL.save_loaded_asset(bp)


def components():
    templates(ROAD)
    roads()
    bp,cs=templates(CAR)
    sds=unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem);lib=unreal.SubobjectDataBlueprintFunctionLibrary
    handles={str(lib.get_variable_name(lib.get_data(h))):h for h in sds.k2_gather_subobject_data_for_blueprint(bp)}
    assert sds.attach_subobject(handles['CameraBoom'],handles['FollowCamera'])
    import car_visual_setup
    sedan=car_visual_setup.find_sedan()
    if sedan:
        car_visual_setup.apply_to_components(cs,sedan)
    else:
        for name,loc,scale in [('Body',(0,0,45),(3.9,1.75,.9)),('Roof',(-30,0,110),(1.9,1.5,.7))]:
            c=cs[name];c.set_static_mesh(unreal.load_asset('/Engine/BasicShapes/Cube'))
            c.set_editor_property('relative_location',unreal.Vector(*loc));c.set_editor_property('relative_scale3d',unreal.Vector(*scale))
            c.set_collision_profile_name('NoCollision');c.set_editor_property('cast_shadow',False)
            c.set_material(0,unreal.load_asset(D.ROOT+('/M_L2Flat' if name=='Body' else '/MI_L2Dark')))
    boom=cs['CameraBoom']
    for k,v in [('target_arm_length',5000.0),('do_collision_test',False),('enable_camera_lag',True),('camera_lag_speed',5.0),
                ('absolute_rotation',True),('relative_rotation',unreal.Rotator(pitch=-90,yaw=0,roll=0)),
                ('inherit_pitch',False),('inherit_yaw',False),('inherit_roll',False)]:boom.set_editor_property(k,v)
    cam=cs['FollowCamera'];cam.set_editor_property('field_of_view',90.0)
    cam.set_editor_property('relative_location',unreal.Vector(0,0,0))
    cdo=unreal.get_default_object(bp.generated_class());cdo.set_editor_property('auto_possess_player',unreal.AutoReceiveInput.DISABLED)
    if 'Collision' in cs:
        import free_drive_setup
        importlib.reload(free_drive_setup)
        free_drive_setup.car()
    clean(CAR)
    bp,cs=templates(MET)
    for name,mesh,mat,loc,scale in [('Shadow','/Engine/BasicShapes/Cylinder',D.ROOT+'/MI_L2Dark',(0,0,8),(4.8,4.8,.015)),
                                  ('Ring',D.ROOT+'/SM_L2Ring/StaticMeshes/SM_L2Ring',D.ROOT+'/M_L2Flat',(0,0,15),(10,10,1))]:
        c=cs[name];c.set_static_mesh(unreal.load_asset(mesh));c.set_material(0,unreal.load_asset(mat));c.set_collision_profile_name('NoCollision')
        c.set_editor_property('relative_location',unreal.Vector(*loc));c.set_editor_property('relative_scale3d',unreal.Vector(*scale));c.set_editor_property('cast_shadow',False)
    clean(MET)
    road_bp,road_cs=templates(ROAD)
    if 'CityCollision' in road_cs:
        import free_drive_setup
        importlib.reload(free_drive_setup)
        free_drive_setup.road();clean(ROAD)
    print('DRIVE spline, car, camera and meteor templates saved')


def events():
    # Only these new EventGraphs belong to this builder. Roll back to disconnected stubs on an authoring error.
    for path in (CAR,MET):
        g=Graph(path).clear()
        try:
            tick=g.event('ReceiveTick',0,800)
            step=g.call(cpath(path)+(':'+ 'DriveStep' if path==CAR else ':Step'),400,800)
            g.link(tick,'DeltaSeconds',step,'Delta');g.exec_chain(tick,step)
            g.comment('Drive tick','',[tick,step])
            begin=g.event('ReceiveBeginPlay',0,0)
            if path==MET:
                hide=g.call(cpath(MET)+':Hide',400,0);g.exec_chain(begin,hide)
                g.comment('Pooled meteor','',[begin,hide])
            else:
                setup=g.call(cpath(CAR)+':Begin',400,0);g.exec_chain(begin,setup)
                g.comment('Player setup','',[begin,setup])
                for i,name in enumerate(BINDINGS):
                    ev=make(g,0,1400+i*500,'IA_L2'+name)
                    if name in ('Throttle','Brake'):
                        var='Throttle' if name=='Throttle' else 'BrakeHeld'
                        on=g.set(var,420,1400+i*500);off=g.set(var,420,1600+i*500)
                        g.default(on,var,'true');g.default(off,var,'false')
                        g.link(ev,'Started',on,'execute');g.link(ev,'Completed',off,'execute');g.link(ev,'Canceled',off,'execute')
                        g.comment(name+' input','',[ev,on,off])
                    else:
                        fn={'Left':'ChangeLane','Right':'ChangeLane','Turn':'QueueTurn','Brace':'Brace','Continue':'Continue'}[name]
                        n=g.call(cpath(CAR)+':'+fn,420,1400+i*500)
                        if name in ('Left','Right'):g.default(n,'Side',-1 if name=='Left' else 1)
                        g.link(ev,'Started',n,'execute')
                        g.comment(name+' input','',[ev,n])
            clean(path)
        except Exception:
            g.clear();clean(path);raise
    print('DRIVE Enhanced Input events and Tick saved')


{'assets':assets,'mesh':mesh,'components':components,'roads':roads,'events':events}[os.environ['FOA_DRIVE_SETUP']]()
