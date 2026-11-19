"""Offline state-machine tests. Native keyboard routing is proved only in PIE."""
import ast
from pathlib import Path
from types import SimpleNamespace as NS
import unittest
import journey_debug_proof as p


class Obj:
    def __init__(self,**fields):self.fields=fields;self.valid=True
    def get_editor_property(self,key):return self.fields[key]
    def get_path_name(self):return str(id(self))
    def is_in_viewport(self):return True
    def is_visible(self):return True


def fixture(slot='FoA_QA_Play',repeat_bug=False,deliver=True):
    clock=[0.];world=Obj();live=[world];requests=[]
    gi=Obj(SaveSlot=slot,DayCount=3,Knowledge={'Known'},Notebook=['A note'])
    player=Obj(bCinematic=False,bInteractionLocked=False)
    car=Obj(Active=False,Leg=0,Failed=False,Arrived=False,Composure=100)
    journey=Obj(Phase=1,Stop=0,Employability=0,RoadAttempts=0,Assisted=False,
        Submitted=False,FinaleComplete=False,Edited0=False,Edited1=False,Edited2=False,Player=player,Car=car,
        StopBusy=False,StopActionState=0,StopActionDone=False)
    journey.get_world=lambda:world
    fe=Obj(DebugPanel=None,bDebugStepHeld=False,bInGameplay=True)
    pc=Obj(bShowMouseCursor=False)
    pc.get_view_target=lambda:player
    pc.is_move_input_ignored=pc.is_look_input_ignored=lambda:False
    engine=NS(SystemLibrary=NS(is_valid=lambda o:o.valid),UnrealEditorSubsystem=object,
        get_editor_subsystem=lambda _:NS(get_game_world=lambda:live[0]),load_class=lambda *_:object,
        GameplayStatics=NS(get_game_instance=lambda _:gi,get_actor_of_class=lambda *_:fe,
            get_player_controller=lambda *_:pc,get_player_pawn=lambda *_:player,is_game_paused=lambda _:False))
    def request(args):
        requests.append(args)
        if not deliver:return
        if args['key']=='F9':fe.fields['DebugPanel']=None if fe.fields['DebugPanel'] else Obj()
        elif args['event']=='released':fe.fields['bDebugStepHeld']=False
        else:
            if not fe.fields['bDebugStepHeld'] or repeat_bug:
                journey.fields['Phase']+=1;gi.fields['SaveSlot']='FoA_QA_DebugSkip'
            fe.fields['bDebugStepHeld']=True
    driver=p.JourneyDebugProof(world,journey,request,engine=engine,now=lambda:clock[0])
    return NS(driver=driver,clock=clock,requests=requests,gi=gi,journey=journey,live=live,fe=fe)


def run(f,times):
    for t in times:f.clock[0]=t;f.driver.tick()


class DebugProof(unittest.TestCase):
    def test_actual_request_sequence_and_unchanged_state(self):
        f=fixture();run(f,[0,.1,.2,1.1,2.,2.1,2.7])
        self.assertTrue(f.driver.result['passed'],f.driver.result)
        self.assertEqual([(r['key'],r['event']) for r in f.requests],
            [('F9','pressed_and_released'),('F6','pressed'),('F6','pressed'),
             ('F6','released'),('F9','pressed_and_released')])
        self.assertEqual(f.journey.fields['Phase'],2)
        self.assertIsNone(f.fe.fields['DebugPanel'])
        self.assertFalse(f.fe.fields['bDebugStepHeld'])

    def test_detects_missing_held_guard(self):
        f=fixture(repeat_bug=True);run(f,[0,.1,.2,1.1,1.2])
        self.assertFalse(f.driver.result['passed'])
        self.assertIn('Held F6',f.driver.result['reason'])
        self.assertEqual(f.requests[-1],dict(key='F6',event='released'))

    def test_f9_must_not_mutate_gameplay(self):
        f=fixture();run(f,[0]);f.gi.fields['DayCount']+=1;run(f,[.1])
        self.assertIn('F9 changed gameplay',f.driver.result['reason'])

    def test_input_timeout_is_bounded(self):
        f=fixture(deliver=False);run(f,[0,13])
        self.assertEqual(f.driver.result['reason'],'timeout')

    def test_replaced_world_never_receives_cleanup_keys(self):
        f=fixture();run(f,[0,.1]);count=len(f.requests);f.live[0]=Obj();run(f,[.2])
        self.assertEqual(f.driver.result['reason'],'world_or_actor_gone')
        self.assertEqual(len(f.requests),count)

    def test_close_releases_own_key_once(self):
        f=fixture();run(f,[0,.1]);f.driver.close();f.driver.close()
        self.assertEqual(sum(r['event']=='released' for r in f.requests),1)

    def test_player_slot_rejected_before_input(self):
        with self.assertRaisesRegex(AssertionError,'Isolate QA'):fixture(slot='FoA')

    def test_no_engine_mutation_or_own_callback(self):
        tree=ast.parse(Path(p.__file__).read_text())
        methods={n.func.attr for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute)}
        self.assertFalse(methods & {'call_method','set_editor_property','register_slate_post_tick_callback',
            'editor_end_play','editor_play_simulate','save_loaded_asset','write_text','write_bytes'})


if __name__=='__main__':unittest.main()
