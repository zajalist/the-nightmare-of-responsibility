"""Structural component defaults and graph captures, inside the Transition lease.
No actors are placed or bedroom packages saved by this script.
"""
import json
from pathlib import Path
import sys
import unreal
sys.path.insert(0,'P:/FoA/Tools/Unreal/level2')
import threshold_data as D

def main():
    assert unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world() is None
    bp=unreal.load_asset(D.BP)
    unreal.get_editor_subsystem(unreal.EditorActorSubsystem).select_nothing()
    unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(bp)
    sds=unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    lib=unreal.SubobjectDataBlueprintFunctionLibrary
    hs=sds.k2_gather_subobject_data_for_blueprint(bp)
    handles={str(lib.get_variable_name(lib.get_data(h))):h for h in hs}
    if not lib.is_root_component(lib.get_data(handles['Root'])):
        assert sds.make_new_scene_root(hs[0],handles['Root'],bp)
    assert sds.attach_subobject(handles['Root'],handles['Floor'])
    floor=lib.get_object_for_blueprint(lib.get_data(handles['Floor']),bp)
    floor.set_static_mesh(unreal.load_asset('/Engine/BasicShapes/Cube'))
    floor.set_editor_property('relative_location',unreal.Vector(0,0,-15))
    floor.set_editor_property('relative_scale3d',unreal.Vector(12,12,.3))
    floor.set_editor_property('hidden_in_game',True)
    floor.set_editor_property('cast_shadow',False)
    floor.set_collision_profile_name('BlockAll')
    floor.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    assert bp.get_editor_property('status') in (unreal.BlueprintStatus.BS_UP_TO_DATE,unreal.BlueprintStatus.BS_UP_TO_DATE_WITH_WARNINGS)
    assert unreal.EditorAssetLibrary.save_loaded_asset(bp)
    out=Path('P:/FoA/Saved/Codex/dream_transition/graphs');out.mkdir(parents=True,exist_ok=True)
    names=['EventGraph','StartThreshold','EnterDream','StartPath','Step','BeginFall','Land','Finish','Abort','RestoreRoom']
    for n in names:
        unreal.FoAGraphToolsLibrary.capture_graph_png(bp,n,str(out/(n+'.png')),True)
    (out.parent/'build_status.json').write_text(json.dumps(dict(blueprint=D.BP,status=str(bp.get_editor_property('status')),graphs=names),indent=2))
    print('THRESHOLD floor and graph captures saved')
main()
