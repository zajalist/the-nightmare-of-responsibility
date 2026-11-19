"""Configure owned StopSet interview templates after the measured splat import.

Requires the coordinator's editor lease. No maps, source Teen meshes, player
templates, shared materials or existing city-stage components are changed.
"""
def main():
    import importlib
    import json
    from pathlib import Path
    import sys
    import unreal
    sys.path.insert(0,'P:/FoA/Tools/Unreal/level2')
    import interview_data as data
    importlib.reload(data)
    assert data.STAGING_MEASURED, 'Measure the generated floor and bounds first'
    assert unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world() is None
    path='/Game/FoA/Level2/Journey/BP_L2StopSet'
    bp=unreal.load_asset(path);assert bp
    mesh=unreal.load_asset(data.SPLAT);assert mesh, data.SPLAT
    padded=tuple(2*x for x in mesh.get_bounds().box_extent.to_tuple())
    positive=mesh.get_editor_property('positive_bounds_extension').to_tuple()
    negative=mesh.get_editor_property('negative_bounds_extension').to_tuple()
    actual=data.geometry_size(padded,positive,negative)
    assert all(abs(a-b)<20 for a,b in zip(actual,data.SPLAT_SIZE)), ('Import measured v2 before staging',actual,data.SPLAT_SIZE)
    sphere=unreal.load_asset('/Engine/BasicShapes/Sphere');assert sphere
    sky=unreal.load_asset(data.SKY);assert sky
    shell=unreal.load_asset('/Game/FoA/Level2/Journey/M_L2MergeShell');assert shell
    player=unreal.load_asset('/Game/FoA/Characters/Player/BP_FoAPlayer');assert player
    sub=unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    lib=unreal.SubobjectDataBlueprintFunctionLibrary
    handles=sub.k2_gather_subobject_data_for_blueprint(bp)
    hs={str(lib.get_variable_name(lib.get_data(h))):h for h in handles}
    sources={str(lib.get_variable_name(lib.get_data(h))):lib.get_object_for_blueprint(lib.get_data(h),player)
             for h in sub.k2_gather_subobject_data_for_blueprint(player)}
    for name in ('InterviewBackdrop','InterviewSky','InterviewBody','InterviewFace'):
        assert name in hs, 'Declare interview components before configuring them'
    unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(bp)

    def component(name,parent='Root'):
        assert sub.attach_subobject(hs[parent],hs[name])
        obj=lib.get_object_for_blueprint(lib.get_data(hs[name]),bp)
        obj.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
        obj.set_editor_property('generate_overlap_events',False)
        obj.set_editor_property('cast_shadow',False)
        obj.set_editor_property('visible',False)
        obj.set_editor_property('hidden_in_game',False)
        return obj

    backdrop=component('InterviewBackdrop');backdrop.set_static_mesh(mesh)
    backdrop.set_editor_property('override_materials',[])
    assert 'M_SplatWorld_Aniso' in backdrop.get_material(0).get_path_name(), 'Use the imported anisotropic material default'
    backdrop.set_editor_property('relative_location',unreal.Vector(*data.BACKDROP))
    backdrop.set_editor_property('relative_rotation',unreal.Rotator())
    backdrop.set_editor_property('relative_scale3d',unreal.Vector(1,1,1))
    dome=component('InterviewSky');dome.set_static_mesh(sphere);dome.set_material(0,sky)
    dome.set_editor_property('relative_location',unreal.Vector(0,0,0))
    dome.set_editor_property('relative_rotation',unreal.Rotator())
    dome.set_editor_property('relative_scale3d',unreal.Vector(-100,-100,-100))
    rows=[]
    for name,leader,parent in (('InterviewBody','Body','Root'),('InterviewFace','Face','InterviewBody')):
        obj=component(name,parent);source=sources[leader]
        teen=source.get_editor_property('skeletal_mesh_asset')
        assert teen and teen.get_path_name().startswith('/Game/FoA/Characters/Teen/Mesh/'), (leader,teen)
        obj.set_skeletal_mesh_asset(teen)
        location=source.get_editor_property('relative_location')
        if leader=='Body':
            location=unreal.Vector(data.INTERVIEWER[0]+location.x,data.INTERVIEWER[1]+location.y,
                                   data.INTERVIEWER[2]+92+location.z)
        obj.set_editor_property('relative_location',location)
        for prop in ('relative_rotation','relative_scale3d'):obj.set_editor_property(prop,source.get_editor_property(prop))
        obj.set_editor_property('disable_post_process_blueprint',True)
        obj.set_editor_property('visibility_based_anim_tick_option',unreal.VisibilityBasedAnimTickOption.ALWAYS_TICK_POSE_AND_REFRESH_BONES)
        obj.set_editor_property('use_bounds_from_leader_pose_component',False)
        obj.set_editor_property('use_attach_parent_bound',False)
        for index in range(obj.get_num_materials()):obj.set_material(index,shell)
        rows.append(dict(component=name,leader=leader,mesh=teen.get_path_name(),location=location.to_tuple()))
    assert unreal.EditorAssetLibrary.save_loaded_asset(bp,False)
    out=Path('P:/FoA/Saved/Integration/interview_stage_setup.json')
    out.write_text(json.dumps(dict(mesh=mesh.get_path_name(),origin=data.ORIGIN,backdrop=data.BACKDROP,
        camera=data.CAMERA,desk=data.DESK,figures=rows,geometry_size=actual,render_size=padded,
        pose_source='PrepareInterview plays the owned relaxed Teen idle; face follows InterviewBody',
        requires_native_visual_proof=True),indent=2))
    import interview_suit_setup
    importlib.reload(interview_suit_setup)
    interview_suit_setup.main()
    print('Four interview templates configured. Native compile/save and visual proof still required.')


if __name__=='__main__':main()
