"""Read-only snapshot of the user's current clothing-search session. Never changes PIE."""
import json
from pathlib import Path
import unreal
world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world();assert world
player=unreal.GameplayStatics.get_player_character(world,0);pc=unreal.GameplayStatics.get_player_controller(world,0)
def prop(obj,name):
    try:
        value=obj.get_editor_property(name)
        if isinstance(value,unreal.Object):return value.get_path_name()
        if isinstance(value,unreal.Vector):return list(value.to_tuple())
        if isinstance(value,(int,float,bool,str)) or value is None:return value
        return str(value)
    except Exception as exc:return 'unavailable:'+str(exc)
def snapshot(obj,names):return {name:prop(obj,name) for name in names}
inter=player.get_component_by_class(unreal.load_class(None,'/Game/FoA/Gameplay/BPC_Interactor.BPC_Interactor_C'))
bag=inter.get_editor_property('Inventory')
director=unreal.GameplayStatics.get_actor_of_class(world,unreal.load_class(None,'/Game/FoA/Gameplay/BP_BeatDirector.BP_BeatDirector_C'))
result=dict(player=snapshot(player,['bCinematic','bInteractionLocked','bRollingOver']),
    pawn_location=list(player.get_actor_location().to_tuple()),camera_location=list(pc.player_camera_manager.get_camera_location().to_tuple()),
    camera_rotation=list(pc.player_camera_manager.get_camera_rotation().to_tuple()),
    director=snapshot(director,['ClothingSearchStage','BeatIndex','bRollingOver','SearchBed','ClothingShirtSpot']),
    interactor=snapshot(inter,['Target','Prompt','Verb','Verbs','Reach','Radius','bSuspended']),
    inventory=snapshot(bag,['Items','Selected']),actors={})
for actor in unreal.GameplayStatics.get_all_actors_of_class(world,unreal.Actor):
    if actor.get_actor_label() not in ('Bed','Wardrobe','Desk','Shirt_T7','Hanger_CoatRail'):continue
    row=snapshot(actor,['State','MorningState','InteractionKey','AutoUseItem','Rows','HiddenStates'])
    row['location']=list(actor.get_actor_location().to_tuple())
    row['pawn_distance']=unreal.MathLibrary.vector_distance(player.get_actor_location(),actor.get_actor_location())
    row['components']=[dict(name=c.get_name(),location=list(c.get_world_location().to_tuple()),
        bounds=str(unreal.SystemLibrary.get_component_bounds(c)),collision=str(c.get_collision_enabled()))
        for c in actor.get_components_by_class(unreal.PrimitiveComponent)]
    result['actors'][actor.get_actor_label()]=row
Path('P:/FoA/Saved/Integration/clothing_live_blocker.json').write_text(json.dumps(result,indent=1))
print('READ_ONLY_CLOTHING',json.dumps(result))
