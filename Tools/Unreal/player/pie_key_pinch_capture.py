"""Coordinator-owned PIE only: authentic key row, three rendered grip poses, <=14s.

Inject after real FE wake reaches free gameplay. Does not start or stop PIE.
The key never completes: the fixture cancels at the mandatory bind.
"""
import datetime,json,time
from pathlib import Path
import unreal
w=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world();assert w
find=lambda path:unreal.GameplayStatics.get_actor_of_class(w,unreal.load_class(None,path))
p=unreal.GameplayStatics.get_player_character(w,0);pc=unreal.GameplayStatics.get_player_controller(w,0)
d=find('/Game/FoA/Gameplay/BP_BeatDirector.BP_BeatDirector_C')
door=find('/Game/FoA/Gameplay/BP_Door.BP_Door_C')
ia=p.get_component_by_class(unreal.load_class(None,'/Game/FoA/Gameplay/BPC_Interactor.BPC_Interactor_C'))
inv=ia.get_editor_property('Inventory')
assert d.get_editor_property('bWakeDone') and pc.get_view_target()==p and not p.get_editor_property('bCinematic'),'Requires actual free gameplay'
gi=unreal.GameplayStatics.get_game_instance(w)
original=(str(gi.get_editor_property('SaveSlot')),set(gi.get_editor_property('Knowledge')),list(gi.get_editor_property('Notebook')))
gi.call_method('SetProofProgressContext',('FoA_QA_KeyGrip',set(),[]))
folder=Path('P:/FoA/Saved/AnimShots/key_pinch')/datetime.datetime.now().strftime('%Y%m%d_%H%M%S');folder.mkdir(parents=True)
out=Path('P:/FoA/Saved/Integration/key_pinch_capture.json')
S=dict(start=time.time(),last=time.time(),h=None,done=False,phase=0,hold_until=0,rows=[])

def xf(t):return dict(position=list(t.translation.to_tuple()),rotation=list(t.rotation.to_tuple()),scale=list(t.scale3d.to_tuple()))

def capture(label):
    source=p.get_editor_property('Mesh').get_anim_instance()
    row=dict(label=label,angle=door.get_editor_property('ToolAngle'),stage=door.get_editor_property('ToolStepIndex'),
             key_grip=source.get_editor_property('KeyGrip'),grip_weight=source.get_editor_property('GripWeight'),
             ready=door.get_editor_property('bToolReady'),seconds_since_ready=time.time()-S.get('ready_at',time.time()),
             pawn=xf(p.get_actor_transform()))
    for component_name in ('Mesh','Body'):
        component=p.get_editor_property(component_name)
        bones=[dict(name=str(component.get_bone_name(i)),**xf(component.get_socket_transform(component.get_bone_name(i),unreal.RelativeTransformSpace.RTS_COMPONENT)))
               for i in range(component.get_num_bones())]
        path=folder/(label+'_'+component_name.lower()+'.json')
        path.write_text(json.dumps(dict(mesh=component.get_skeletal_mesh_asset().get_path_name(),space='component',world=xf(component.get_world_transform()),bones=bones),indent=1))
        row[component_name]=str(path)
    parts={c.get_name():c for c in door.get_components_by_class(unreal.SceneComponent)}
    row['key']=xf(parts['ToolMesh'].get_world_transform());row['contact']=xf(parts['ToolContact'].get_world_transform())
    row['key_mesh']=parts['ToolMesh'].get_editor_property('static_mesh').get_path_name()
    box=parts['ToolMesh'].get_editor_property('static_mesh').get_bounding_box()
    row['key_local_bounds']=[list(box.min.to_tuple()),list(box.max.to_tuple())]
    row['grip_target']=list(p.get_editor_property('ToolGripWorld').to_tuple())
    S['rows'].append(row)
    unreal.SystemLibrary.execute_console_command(w,'Shot showui filename='+str(folder/(label+'.png'))+' -nosuffix',pc)
    out.write_text(json.dumps(dict(status='running',folder=str(folder),rows=S['rows']),indent=1))

def finish(reason):
    if S['done']:return
    S['done']=True
    if S['h'] is not None:unreal.unregister_slate_post_tick_callback(S['h'])
    door.call_method('CancelDoorTool',())
    gi.call_method('SetProofProgressContext',original)
    unreal.GameplayStatics.delete_game_in_slot('FoA_QA_KeyGrip',0)
    out.write_text(json.dumps(dict(status='complete',reason=reason,folder=str(folder),rows=S['rows'],
        early_cancel=S.get('early_cancel'),
        precondition='Owned PIE after real FE wake. EnterBeat4, boots Worn and inventory Key are explicit grip-test preconditions.'),indent=1))

def tick(dt):
    try:
        now=time.time();elapsed=now-S['start']
        if elapsed>14:return finish('timeout')
        if S['phase']==0:
            unreal.SystemLibrary.pause_timer(d,'PollStoryMoment');unreal.SystemLibrary.clear_timer(d,'TryStoryMoment')
            d.call_method('EnterBeat',(4,));inv.call_method('Add',('Key',))
            boot=door.get_editor_property('BootProgressionSource')
            if boot:boot.call_method('SetState',('Worn',True));d.call_method('ReportEvent',('BootsWorn',))
            door.call_method('Interact',('Use','Key'));assert door.get_editor_property('bToolActive')
            S['phase']=1
        elif S['phase']==1 and not S.get('early_cancel') and unreal.SystemLibrary.is_timer_active(door,'MarkDoorToolReady'):
            before=list(inv.get_editor_property('Items'));angle=door.get_editor_property('ToolAngle')
            assert not door.get_editor_property('bToolReady')
            door.call_method('AdvanceDoorTool',(1.,.1))
            assert door.get_editor_property('ToolAngle')==angle,'Turn accepted before the hand was seated'
            door.call_method('CancelDoorTool',())
            assert not door.get_editor_property('bToolActive') and not door.get_editor_property('bToolReady')
            assert not unreal.SystemLibrary.is_timer_active(door,'MarkDoorToolReady')
            assert list(inv.get_editor_property('Items'))==before,'Cancel spent an item'
            assert not p.get_editor_property('bCinematic') and not pc.is_move_input_ignored() and not pc.is_look_input_ignored()
            S['early_cancel']=dict(turn_blocked=True,inventory_preserved=True,ready_timer_cleared=True,controls_released=True)
            door.call_method('Interact',('Use','Key'));assert door.get_editor_property('bToolActive')
        elif S['phase']==1 and door.get_editor_property('bToolReady'):
            assert S.get('early_cancel'),'Did not observe the hand-settle interval'
            # One render frame after readiness, not an extra half-second settling allowance.
            S['ready_at']=now;S['hold_until']=now+.04;S['phase']=2
        elif S['phase']==2 and now>=S['hold_until']:
            capture('seated');S['phase']=3
        elif S['phase']==3:
            door.call_method('AdvanceDoorTool',(1.,min(dt,.1)))
            if door.get_editor_property('ToolStepIndex')==1:
                S['hold_until']=now+.25;S['phase']=4
        elif S['phase']==4 and now>=S['hold_until']:
            capture('pressure');S['phase']=5
        elif S['phase']==5:
            door.call_method('AdvanceDoorTool',(1.,min(dt,.1)))
            if door.get_editor_property('ToolStepIndex')==2:
                S['hold_until']=now+.25;S['phase']=6
        elif S['phase']==6 and now>=S['hold_until']:
            capture('bound');S['hold_until']=now+.2;S['phase']=7
        elif S['phase']==7 and now>=S['hold_until']:
            finish('captured_three_actual_key_poses')
    except Exception as exc:
        S['rows'].append(dict(error=repr(exc)));finish('failed')
S['h']=unreal.register_slate_post_tick_callback(tick)
