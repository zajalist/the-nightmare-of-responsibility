"""Build the real bedroom camera and tag the room effects that it suppresses."""

import os
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parent))
SEQUENCE='/Game/FoA/Level2/Transition/LS_L2RealWake'
ROOM_GRADE='FoA_DreamRoomGrade'
ROOM_SAND='FoA_DreamRoomSand'
WAKE_LENGTH=7.8


def build():
    import unreal as u
    editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
    assert not editor.get_game_world()
    world=editor.get_editor_world();assert world.get_name()=='L_Tutorial_Bedroom'
    scope={'__name__':'foa_wake_helpers'}
    helpers=Path('P:/FoA/Tools/Unreal/flow/build_battle_intro.py').read_text(encoding='utf-8').rsplit('\nmain()',1)[0]
    exec(helpers,scope);scope['END']=WAKE_LENGTH
    eal=u.EditorAssetLibrary
    package,name=SEQUENCE.rsplit('/',1)
    sequence=u.load_asset(SEQUENCE) if eal.does_asset_exist(SEQUENCE) else u.AssetToolsHelpers.get_asset_tools().create_asset(
        name,package,u.LevelSequence,u.LevelSequenceFactoryNew())
    sequencer=u.LevelSequenceEditorBlueprintLibrary
    sequencer.close_level_sequence()
    sequencer.open_level_sequence(sequence)
    sequencer.set_lock_camera_cut_to_viewport(False)
    for binding in list(sequence.get_bindings()):
        if binding.is_valid():binding.remove()
    for track in list(sequence.get_tracks()):sequence.remove_track(track)
    sequence.set_display_rate(u.FrameRate(30,1));sequence.set_playback_start_seconds(0);sequence.set_playback_end_seconds(WAKE_LENGTH)
    keys=[(0,(318,-190,99),(-3,155,6)),
        (1.05,(318,-190,101),(-6,159,4)),(2.25,(313,-180,122),(-8,172,1.5)),
        (4.1,(300,-163,149),(-4,188,0)),(WAKE_LENGTH,(298,-160,150),(-4,190,0))]
    camera=scope['camera'](sequence,'WakeAtHome',[(frame,position,(-140,-245,135)) for frame,position,_ in keys],29,(0,WAKE_LENGTH))
    scope['transform_track'](camera[0],keys)
    scope['cuts'](sequence,[camera])
    light,template=scope['spawnable'](sequence,u.PointLight,'Warm window bounce')
    point=template.get_editor_property('point_light_component')
    point.set_editor_property('intensity',620.)
    point.set_editor_property('attenuation_radius',750.)
    point.set_editor_property('light_color',u.Color(255,233,204,255))
    point.set_editor_property('source_radius',28.)
    point.set_editor_property('cast_shadows',True)
    scope['transform_track'](light,[(0,(-138,-303,208),(0,0,0))])
    scope['lifetime'](light,0,WAKE_LENGTH)
    scope['fade'](sequence,[(0,1),(.35,1),(.64,.24),(.81,.64),(1.3,0),(6.7,0),(7.75,1)])
    scope['audio'](sequence,[('/Game/FoA/Audio/SFX/Breath/SFX_Breath_Effort_03',.18,1.4,.33)])
    sequencer.close_level_sequence()
    assert eal.save_loaded_asset(sequence,False)


def tag_room():
    import unreal as u
    assert not u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
    actors=u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors()
    grade=[actor for actor in actors if isinstance(actor,u.PostProcessVolume) and actor.get_actor_label()=='PP_DreamMono']
    assert len(grade)==1,'Expected the original bedroom grade'
    sand=[actor for actor in actors if str(actor.get_folder_path()).startswith('FX/Sand')
          or actor.get_actor_label().startswith(('SandSplats_','SandMound_','SandStream_','SandSpill_','SandClock_'))]
    assert sand,'No original bedroom sand actors found'
    changed=False
    for tag,group in ((ROOM_GRADE,grade),(ROOM_SAND,sand)):
        for actor in group:
            tags=list(actor.get_editor_property('tags'))
            if tag in map(str,tags):continue
            actor.set_editor_property('tags',tags+[u.Name(tag)]);changed=True
    if changed:assert u.get_editor_subsystem(u.LevelEditorSubsystem).save_current_level()
    print('Real wake grade tagged and sand actors',len(sand))


def wake_graphs():
    import unreal as u
    assert not u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
    scope={}
    exec(Path('P:/FoA/Tools/Unreal/ui/bp_graph.py').read_text(encoding='utf-8'),scope)
    graph=scope['Graph'];bp='/Game/FoA/Level2/Transition/BP_DreamThreshold'
    owner=bp+'.BP_DreamThreshold_C:'
    array='/Script/Engine.KismetArrayLibrary:'
    math='/Script/Engine.KismetMathLibrary:'
    actor='/Script/Engine.Actor'

    g=graph.function(bp,'FindWakeGrade');entry=g.ed.list_nodes_of_class(u.K2Node_FunctionEntry)[0]
    result=g.ed.list_nodes_of_class(u.K2Node_FunctionResult)[0]
    tagged=g.call('/Script/Engine.GameplayStatics:GetAllActorsWithTag',320,0,Tag=ROOM_GRADE)
    first=g.call(array+'Array_Get',640,240,Index=0)
    g.exec_chain(entry,tagged,result)
    g.link(tagged,'OutActors',first,'TargetArray');g.link(first,'Item',result,'Target')

    g=graph.function(bp,'RememberWakeSand');entry=g.ed.list_nodes_of_class(u.K2Node_FunctionEntry)[0]
    hidden=g.get('WakeSandHidden',0,220);remember=g.call(array+'Array_Add',320,0)
    g.exec_chain(entry,remember)
    g.link(hidden,'WakeSandHidden',remember,'TargetArray');g.link(entry,'Target',remember,'NewItem')

    for restore,name in ((False,'HideWakeSand'),(True,'RestoreWakeSand')):
        g=graph.function(bp,name);entry=g.ed.list_nodes_of_class(u.K2Node_FunctionEntry)[0]
        field='WakeSandHidden' if restore else 'WakeSandTargets';items=g.get(field,0,260)
        length=g.call(array+'Array_Length',280,265)
        less=g.call(math+'Less_IntInt',520,260);branch=g.branch(600,0)
        get=g.call(array+'Array_Get',860,260)
        g.link(items,field,length,'TargetArray');g.link(length,'ReturnValue',less,'B')
        g.link(entry,'Index',less,'A');g.link(less,'ReturnValue',branch,'Condition');g.exec_chain(entry,branch)
        g.link(items,field,get,'TargetArray');g.link(entry,'Index',get,'Index')
        if restore:
            apply=g.call(actor+':SetActorHiddenInGame',1160,0,bNewHidden='false')
            g.link(get,'Item',apply,'self')
            clear=g.call(array+'Array_Clear',1060,470)
            g.link(branch,'else',clear,'execute');g.link(items,field,clear,'TargetArray')
        else:
            apply=g.call(owner+'HideWakeActor',1160,0);g.link(get,'Item',apply,'Target')
        add=g.call(math+'Add_IntInt',1160,260,B=1);g.link(entry,'Index',add,'A')
        again=g.call(owner+name,1460,0);g.link(add,'ReturnValue',again,'Index')
        g.exec_chain(branch,apply,again)
    print('Typed the original room actor arrays in the Blueprint graph editor')


if __name__=='__main__':
    {'sequence':build,'tags':tag_room,'graphs':wake_graphs}[os.environ['FOA_WAKE_STEP']]()
