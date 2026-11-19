"""One read-only user-session snapshot. No callbacks, inputs, world or asset edits."""
import json, time
from pathlib import Path
import unreal
w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
assert w, 'No active user session'
find = lambda path: unreal.GameplayStatics.get_actor_of_class(w, unreal.load_class(None,path))
door = find('/Game/FoA/Gameplay/BP_Door.BP_Door_C')
d = find('/Game/FoA/Gameplay/BP_BeatDirector.BP_BeatDirector_C')
p = unreal.GameplayStatics.get_player_character(w,0)
data = dict(time=time.time(), beat=d.get_editor_property('BeatIndex'), search=d.get_editor_property('ClothingSearchStage'),
    door_state=str(door.get_editor_property('State')), tool_mode=str(door.get_editor_property('ToolMode')),
    active=door.get_editor_property('bToolActive'), ready=door.get_editor_property('bToolReady'),
    angle=door.get_editor_property('ToolAngle'), stage=door.get_editor_property('ToolStepIndex'),
    releasing=door.get_editor_property('bToolReleasing'), owns_locks=door.get_editor_property('bToolOwnsLocks'),
    cinematic=p.get_editor_property('bCinematic'), locked=p.get_editor_property('bInteractionLocked'))
pc=unreal.GameplayStatics.get_player_controller(w,0)
data.update(move_ignored=pc.is_move_input_ignored(),look_ignored=pc.is_look_input_ignored(),view=pc.get_view_target().get_class().get_name())
for obj,names in ((p,('bHeadache','bHeadacheActive')),(d,('bWardrobeTransition','bRollingOver','bTopDown'))):
    for n in names:
        try:data[n]=obj.get_editor_property(n)
        except Exception:pass
if data['active']:
    body=p.get_editor_property('Body')
    data['bones']={n:list(body.get_socket_location(n).to_tuple()) for n in ('upperarm_r','lowerarm_r','hand_r')}
    data['pawn']=list(p.get_actor_location().to_tuple())
    data['door_forward']=list(door.get_actor_forward_vector().to_tuple())
    data['components']={c.get_name():c.get_world_transform().export_text()
                        for c in door.get_components_by_class(unreal.SceneComponent)
                        if c.get_name() in ('ToolContact','ToolPivot','ToolMesh','Pivot')}
    data['held_tool']=p.get_editor_property('HeldTool').get_world_transform().export_text()
    data['grip']=p.get_editor_property('HeldToolGrip').get_world_transform().export_text()
    data['grip_target']=list(p.get_editor_property('ToolGripWorld').to_tuple())
Path('P:/FoA/Saved/Integration/door_user_session.json').write_text(json.dumps(data,indent=1))
print(json.dumps({k:v for k,v in data.items() if k not in ('bones','components','held_tool','grip')}))
