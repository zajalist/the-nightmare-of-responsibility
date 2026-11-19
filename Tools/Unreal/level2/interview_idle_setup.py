"""Retarget one reused relaxed idle, then configure the owned interviewer only.

Native writer grant/lease required. No player, rig, source clip or map edits.
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
    assert unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world() is None
    source=unreal.load_asset(data.IDLE_SOURCE);assert source
    manny=unreal.load_asset('/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple')
    teen=unreal.load_asset('/Game/FoA/Characters/Teen/Mesh/SK_Teen_Body')
    rig=unreal.load_asset('/Game/FoA/Characters/Player/Retarget/RTG_Mannequin_to_Teen')
    assert manny and teen and rig
    assert source.get_editor_property('skeleton')==manny.get_editor_property('skeleton')
    idle=unreal.load_asset(data.IDLE)
    if not idle:
        inputs=unreal.IKRetargetBatchOperationInputs()
        for key,value in (
            ('assets_to_retarget',[unreal.EditorAssetLibrary.find_asset_data(data.IDLE_SOURCE)]),
            ('source_mesh',manny),('target_mesh',teen),('ik_retarget_asset',rig),
            ('target_path',data.IDLE.rsplit('/',1)[0]),('include_referenced_assets',False),
            ('overwrite_existing_files',False),('suffix','_Interview')):
            inputs.set_editor_property(key,value)
        outputs=unreal.IKRetargetBatchOperation.run_batch_retarget(inputs)
        assert len(outputs)==1,('Expected one reused idle',outputs)
        idle=unreal.load_asset(data.IDLE);assert idle
    assert idle.get_editor_property('skeleton')==teen.get_editor_property('skeleton')
    assert idle.get_play_length()>1,'Idle must have breathing motion'
    assert unreal.EditorAssetLibrary.save_loaded_asset(idle,False)
    # Retarget validation catches a reference/T pose before assigning the clip.
    ap=unreal.AnimPoseExtensions;rows=[]
    for fraction in (0,.2,.4,.6,.8):
        pose=ap.get_anim_pose_at_time(idle,idle.get_play_length()*fraction,unreal.AnimPoseEvaluationOptions())
        row={name:ap.get_bone_pose(pose,name,unreal.AnimPoseSpaces.WORLD).translation.to_tuple()
             for name in ('hand_r','hand_l','upperarm_r','upperarm_l','head')}
        for side in ('r','l'):
            assert row['upperarm_'+side][2]-row['hand_'+side][2]>20,('Idle arm is raised',row)
        rows.append(row)
    motion={name:max(sum((a-b)**2 for a,b in zip(row[name],rows[0][name]))**.5 for row in rows)
            for name in ('hand_r','head')}
    assert all(value>.01 for value in motion.values()),('Idle is static',motion)
    bp=unreal.load_asset(data.ROOT+'/BP_L2StopSet');assert bp
    unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(bp)
    sub=unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    lib=unreal.SubobjectDataBlueprintFunctionLibrary
    for handle in sub.k2_gather_subobject_data_for_blueprint(bp):
        if str(lib.get_variable_name(lib.get_data(handle)))=='InterviewBody':
            body=lib.get_object_for_blueprint(lib.get_data(handle),bp)
            body.set_editor_property('visibility_based_anim_tick_option',unreal.VisibilityBasedAnimTickOption.ALWAYS_TICK_POSE_AND_REFRESH_BONES)
            break
    else:raise AssertionError('Missing interviewer body')
    assert unreal.EditorAssetLibrary.save_loaded_asset(bp,False)
    Path('P:/FoA/Saved/Integration/city_ui/interview_idle.json').write_text(json.dumps(dict(
        source=data.IDLE_SOURCE,clip=idle.get_path_name(),length=idle.get_play_length(),
        skeleton=idle.get_editor_property('skeleton').get_path_name(),motion_cm=motion,poses=rows),indent=2))
    print('One relaxed Teen idle ready; PrepareInterview graph and native visual proof remain required')


if __name__=='__main__':main()
