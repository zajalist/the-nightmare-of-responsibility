"""One-shot integration assertions inside the parent's EXCLUSIVE QA PIE.

FOA_JOURNEY_PROOF=snapshot|reset. Staged stops use journey_stop_proof's async driver.
The parent sets FoA_QA_Play before running this script and owns PIE teardown.
"""
import json
import os
from pathlib import Path
import unreal

def main():
    world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
    assert world and unreal.SystemLibrary.is_valid(world),'QA PIE required'
    gi=unreal.GameplayStatics.get_game_instance(world)
    assert str(gi.get_editor_property('SaveSlot'))=='FoA_QA_Play','Set isolated proof context before any game-flow calls'
    journey=unreal.GameplayStatics.get_actor_of_class(world,unreal.load_class(None,
        '/Game/FoA/Level2/Journey/BP_L2Journey.BP_L2Journey_C'))
    assert journey and unreal.SystemLibrary.is_valid(journey),'Journey not ready'
    car=journey.get_editor_property('Car')
    mode=os.environ.get('FOA_JOURNEY_PROOF','snapshot')
    def state():
        return dict(phase=journey.get_editor_property('Phase'),stop=journey.get_editor_property('Stop'),
          employability=journey.get_editor_property('Employability'),
          edits=[journey.get_editor_property('Edited'+str(i)) for i in range(3)],
          attempts=journey.get_editor_property('RoadAttempts'),active=car.get_editor_property('Active'),
          leg=car.get_editor_property('Leg'),failed=car.get_editor_property('Failed'),
          possessed=unreal.GameplayStatics.get_player_pawn(world,0).get_class().get_name(),
          view=unreal.GameplayStatics.get_player_controller(world,0).get_view_target().get_class().get_name(),
          notes=[str(x) for x in gi.get_editor_property('Notebook')])
    trace=[state()]
    if mode=='reset':
        before=state();assert before['phase']==3,before
        car.call_method('ResolveHit',(100,'QA'))
        assert car.get_editor_property('Failed')
        car.call_method('DriveStep',(3.,))
        after=state();trace.append(after)
        assert after['phase']==10 and not after['active'],after
        assert after['employability']==0 and after['edits']==[False,False,False],after
        assert after['attempts']==before['attempts']+1 and after['notes']==before['notes'],after
    elif mode!='snapshot':raise AssertionError(mode)
    result=dict(mode=mode,passed=True,trace=trace,scope='Native API contract; real-input drive and rendering require separate playtest')
    path=Path('P:/FoA/Saved/Codex/l2_journey');path.mkdir(parents=True,exist_ok=True)
    (path/(mode+'.json')).write_text(json.dumps(result,indent=2))
    print(json.dumps(result))

main()
