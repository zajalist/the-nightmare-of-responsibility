"""Offline safety/liveness checks; rendered actions and key routing require PIE."""
from types import SimpleNamespace as NS
import unittest
import journey_stop_proof as p


class Obj:
    valid=True
    def __init__(self,**fields):self.fields=fields
    def get_editor_property(self,key):return self.fields[key]


def fixture(slot='FoA_QA_Play'):
    clock=[0.];world=Obj();live=[world];requests=[]
    gi=Obj(SaveSlot=slot,DayCount=3,Notebook=['Before Level 2'],Knowledge=[])
    car=Obj(Active=False,Leg=0,Meteor=Obj(Active=False))
    stage=Obj(TicketTaken=True)
    journey=Obj(Phase=1,Stop=0,StopBusy=False,StopActionState=0,StopActionDone=False,
        Employability=0,Edited0=False,Edited1=False,Edited2=False,Car=car,StopSet=stage,
        DialogueMode=0,DialogueState=0,DialogueSelected=0,DialogueReady=False)
    journey.get_world=lambda:world
    engine=NS(SystemLibrary=NS(is_valid=lambda o:o.valid),UnrealEditorSubsystem=object,
        get_editor_subsystem=lambda _:NS(get_game_world=lambda:live[0]),
        GameplayStatics=NS(get_game_instance=lambda _:gi))
    driver=p.StopProof(world,journey,requests.append,engine=engine,now=lambda:clock[0])
    return NS(clock=clock,live=live,journey=journey,gi=gi,requests=requests,driver=driver)


class StopProofTests(unittest.TestCase):
    def test_actual_street_input_closes_paper_before_car_confirm(self):
        f=fixture();paper=Obj(bOpen=True)
        f.journey.fields.update(Phase=2,CVPaper=paper)
        f.driver.tick();self.assertEqual(f.requests[0]['key'],'E')
        f.clock[0]=.5;f.driver.tick();self.assertEqual(len(f.requests),1)
        f.journey.fields['CVPaper']=None;f.driver.tick()
        self.assertEqual(f.requests[-1]['key'],'Enter')

    def test_consecutive_selection_waits_for_key_release(self):
        f=fixture();f.journey.fields.update(Phase=4,Stop=2,DialogueMode=1,DialogueReady=True)
        f.driver.tick();self.assertEqual(f.requests[-1]['key'],'Down')
        f.journey.fields['DialogueSelected']=1;f.clock[0]=.02;f.driver.tick()
        self.assertEqual(len(f.requests),1)
        f.clock[0]=.45;f.driver.tick();self.assertEqual(len(f.requests),2)
        f.journey.fields['DialogueSelected']=2;f.clock[0]=.46;f.driver.tick()
        self.assertEqual(len(f.requests),2)
        f.clock[0]=.9;f.driver.tick();self.assertEqual(f.requests[-1]['key'],'Enter')

    def test_completed_action_holds_before_any_debrief_input(self):
        f=fixture();f.journey.fields.update(Phase=4,StopActionState=3,
            StopActionDone=True,DialogueMode=2,DialogueReady=True)
        f.driver.tick()
        self.assertEqual(f.driver.state,'action_hold')
        self.assertEqual(f.requests,[])
        self.assertEqual(f.driver.result['trace'][-1]['event'],'action_completed')
        f.clock[0]=.4;f.driver.tick();self.assertEqual(f.requests,[])
        f.clock[0]=.6;f.driver.tick();self.assertEqual(f.requests[0]['key'],'Enter')

    def test_real_e_only_after_confirm_gate_probe(self):
        f=fixture();f.journey.fields.update(Phase=4,StopActionState=1)
        f.driver.tick();self.assertEqual(f.requests[0]['key'],'Enter')
        f.clock[0]=.5;f.driver.tick()
        self.assertEqual(f.requests[1],dict(key='E',event='pressed_and_released',held_ms=90))
        f.clock[0]=3.6;f.driver.tick()
        self.assertIn('did not advance',f.driver.result['reason'])

    def test_busy_stage_never_gets_input_and_timeout_is_bounded(self):
        f=fixture();f.journey.fields.update(Phase=4,StopBusy=True)
        f.driver.tick();self.assertEqual(f.requests,[])
        f.clock[0]=23;f.driver.tick()
        self.assertEqual(f.driver.result['reason'],'timeout')

    def test_replaced_world_and_changed_day_stop_before_input(self):
        f=fixture();f.live[0]=Obj();f.driver.tick()
        self.assertEqual(f.driver.result['reason'],'world_or_actor_gone')
        self.assertEqual(f.requests,[])
        f=fixture();f.gi.fields['DayCount']+=1;f.driver.tick()
        self.assertIn('Level 1 day',f.driver.result['reason']);self.assertEqual(f.requests,[])

    def test_rejects_player_save_slot(self):
        with self.assertRaisesRegex(AssertionError,'Isolate QA'):fixture('FoA')


if __name__=='__main__':unittest.main()
