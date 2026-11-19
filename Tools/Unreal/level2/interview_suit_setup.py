"""Fit the existing Teen suit to the owned interviewer; no source asset edits."""
def main():
    import importlib,json,sys
    from pathlib import Path
    import unreal
    sys.path.insert(0,'P:/FoA/Tools/Unreal/level2')
    import interview_data as data
    importlib.reload(data)
    assert unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world() is None
    bp=unreal.load_asset(data.ROOT+'/BP_L2StopSet');assert bp
    unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(bp)
    sub=unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    lib=unreal.SubobjectDataBlueprintFunctionLibrary
    hs={str(lib.get_variable_name(lib.get_data(h))):h for h in sub.k2_gather_subobject_data_for_blueprint(bp)}
    assert 'InterviewSuit' in hs,'Declare InterviewSuit with the scoped skeleton step'
    body=lib.get_object_for_blueprint(lib.get_data(hs['InterviewBody']),bp)
    suit=lib.get_object_for_blueprint(lib.get_data(hs['InterviewSuit']),bp)
    mesh=unreal.load_asset(data.SUIT);material=unreal.load_asset(data.SUIT_MATERIAL)
    assert mesh and material
    assert mesh.get_editor_property('skeleton')==body.get_editor_property('skeletal_mesh_asset').get_editor_property('skeleton')
    assert sub.attach_subobject(hs['InterviewBody'],hs['InterviewSuit'])
    suit.set_skeletal_mesh_asset(mesh)
    suit.set_editor_property('relative_location',unreal.Vector())
    suit.set_editor_property('relative_rotation',unreal.Rotator())
    suit.set_editor_property('relative_scale3d',unreal.Vector(1,1,1))
    suit.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
    for name,value in (('generate_overlap_events',False),('cast_shadow',False),('visible',False),
                       ('hidden_in_game',False),('disable_post_process_blueprint',True),
                       ('use_attach_parent_bound',True),('use_bounds_from_leader_pose_component',False)):
        suit.set_editor_property(name,value)
    for index in range(suit.get_num_materials()):suit.set_material(index,material)
    assert unreal.EditorAssetLibrary.save_loaded_asset(bp,False)
    Path('P:/FoA/Saved/Integration/city_ui/interview_suit.json').write_text(json.dumps(dict(
        mesh=mesh.get_path_name(),material=material.get_path_name(),parent='InterviewBody',
        relative_transform='identity',pose_leader='PrepareInterview binds InterviewBody'),indent=2))
    print('Existing matching Teen suit fitted to interviewer; compile and visual proof remain required')


if __name__=='__main__':main()
