"""Map operations, ONLY under drive_burst.py's single EXCLUSIVE lease."""
import json
import os
import sys
from pathlib import Path
import unreal

sys.path.insert(0,'P:/FoA/Tools/Unreal/level2')
import drive_data as D
import importlib
importlib.reload(D)
LES=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
EAS=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
UES=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
OUT=Path('P:/FoA/Saved/Codex/l2_drive');OUT.mkdir(parents=True,exist_ok=True)


def current():return UES.get_editor_world().get_path_name().split('.')[0]


def count():
    acts=EAS.get_all_level_actors();names={a.get_actor_label() for a in acts};classes={a.get_class().get_name() for a in acts}
    return dict(map=current(),actors=len(acts),encounter='Encounter_T8' in names,
                beat=any(c.startswith('BP_BeatDirector') for c in classes),player_start='PlayerStart' in classes)


def build():
    assert current()==D.MAP,current()
    world=UES.get_editor_world()
    city=D.CITY_EXPANDED if unreal.EditorAssetLibrary.does_asset_exist(D.CITY_EXPANDED) else D.CITY
    if city==D.CITY_EXPANDED:
        old=unreal.GameplayStatics.get_streaming_level(world,D.CITY)
        if old:assert unreal.EditorLevelUtils.remove_level_from_world(old.get_loaded_level())
    if not unreal.GameplayStatics.get_streaming_level(world,city):
        stream=unreal.EditorLevelUtils.add_level_to_world(world,city,unreal.LevelStreamingAlwaysLoaded)
        assert stream,'city sublevel failed'
    # Keep new actors in the persistent prototype level, never in the streamed city's package.
    assert LES.set_current_level_by_name('L_L2_DriveProto')
    have={a.get_actor_label():a for a in EAS.get_all_level_actors()}
    for name,label,pos in [('BP_L2RoadNetwork','L2Drive_Road',(0,0,0)),('BP_Meteor','L2Drive_Meteor',(0,0,0)),
                           ('BP_L2Car','L2Drive_Car',(5000,180,-63))]:
        if label not in have:
            a=EAS.spawn_actor_from_class(unreal.load_class(None,D.ROOT+'/'+name+'.'+name+'_C'),unreal.Vector(*pos))
            assert a;a.set_actor_label(label);a.set_folder_path('Drive')
            have[label]=a
    road=have['L2Drive_Road']
    have['L2Drive_Car'].set_editor_property('auto_possess_player',unreal.AutoReceiveInput.DISABLED)
    for i,points in enumerate(D.RAILS):
        spline=road.get_editor_property('Rail'+str(i));spline.clear_spline_points(False)
        for point in points:spline.add_spline_point(unreal.Vector(*point),unreal.SplineCoordinateSpace.LOCAL,False)
        for j in range(len(points)):spline.set_spline_point_type(j,unreal.SplinePointType.LINEAR,False)
        spline.update_spline()
    world.get_world_settings().set_editor_property('default_game_mode',unreal.GameModeBase.static_class())
    assert LES.save_current_level()
    (OUT/'map_city.json').write_text(json.dumps(dict(city=city)))
    print('DRIVE map saved',city,count())


step=os.environ['FOA_DRIVE_MAP']
if step=='before':
    assert current()==D.BEDROOM,('Another map is open; do not take it over',current())
    snap=count();assert snap['map']==D.BEDROOM,snap
    (OUT/'bedroom_before.json').write_text(json.dumps(snap));print('DRIVE before',snap)
elif step=='open':
    assert unreal.EditorAssetLibrary.does_asset_exist(D.CITY),'city not ready'
    if unreal.EditorAssetLibrary.does_asset_exist(D.MAP):assert LES.load_level(D.MAP)
    else:assert LES.new_level(D.MAP)
    print('DRIVE open',current())
elif step=='build':build()
elif step=='back':
    if current()!=D.BEDROOM:assert LES.load_level(D.BEDROOM)
    before=json.loads((OUT/'bedroom_before.json').read_text());after=count()
    (OUT/'bedroom_after.json').write_text(json.dumps(after));assert before==after,(before,after)
    print('DRIVE bedroom verified',after)
