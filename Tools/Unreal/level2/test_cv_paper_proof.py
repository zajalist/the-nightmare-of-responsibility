"""Offline state/teardown and independent viewport-fit contracts for actual paper QA."""
from types import SimpleNamespace as NS
import unittest
from unittest.mock import Mock
import cv_paper_proof as p


class Obj:
    valid=True
    def __init__(self,**fields):self.fields=fields;self.calls=[]
    def get_editor_property(self,key):
        assert self.valid,'dereferenced destroyed object'
        return self.fields[key]
    def call_method(self,name,args=()):self.calls.append(name)
    def is_in_viewport(self):return self.fields.get('visible',False)
    def is_visible(self):return self.fields.get('shown',False)
    def get_render_opacity(self):return self.fields.get('opacity',1.)
    def get_visibility(self):return 'Hidden' if not self.is_visible() else 'Visible'


def fixture():
    clock=[0.];world=Obj();live=[world];state=dict(paused=False,pawn=None);inputs=[]
    pc=Obj();gi=Obj(SaveSlot='FoA_QA_Play',DayCount=18)
    hint=NS(get_text=lambda:'Enter or gamepad Y to get in the car')
    hud=Obj(visible=True,Txt_Hint=hint);car=Obj(Active=False)
    journey=Obj(Phase=1,CVPaper=None,HUD=hud,Car=car)
    l1hud=Obj(visible=True,shown=False,opacity=1.);front=Obj(HUD=l1hud)
    engine=NS(SystemLibrary=NS(is_valid=lambda x:x.valid,execute_console_command=Mock()),
        load_class=lambda *args:args[-1],
        UnrealEditorSubsystem=object,get_editor_subsystem=lambda _:NS(get_game_world=lambda:live[0]),
        GameplayStatics=NS(get_player_controller=lambda *_:pc,get_game_instance=lambda _:gi,get_actor_of_class=lambda *_:front,
            is_game_paused=lambda _:state['paused'],get_player_pawn=lambda *_:state['pawn']))
    proof=p.PaperProof(world,journey,inputs.append,engine=engine,now=lambda:clock[0])
    proof.view=Mock(return_value={'rect_px':[300,100,700,700]})
    return NS(clock=clock,world=world,live=live,state=state,inputs=inputs,journey=journey,car=car,proof=proof,engine=engine,l1hud=l1hud)


class PaperProofTests(unittest.TestCase):
    def test_runtime_l1_hud_leak_and_missing_widget_are_failures(self):
        f=fixture();f.l1hud.fields['shown']=True
        f.proof.tick();self.assertFalse(f.proof.result['passed'])
        self.assertIn('L1 HUD leaks',f.proof.result['reason']);self.assertEqual(f.inputs,[])
        f=fixture();f.l1hud.valid=False
        with self.assertRaisesRegex(AssertionError,'Missing L1 HUD'):f.proof.l1_hud_snapshot()
        f=fixture();f.l1hud.fields.update(shown=True,opacity=0.)
        self.assertEqual(f.proof.l1_hud_snapshot()['opacity'],0)
        # ItemInspect Finish restores opacity1; catches a visibility leak after close.
        f.l1hud.fields['opacity']=1.
        with self.assertRaisesRegex(AssertionError,'L1 HUD leaks'):f.proof.l1_hud_snapshot()

    def test_projection_rejects_clipped_tiny_and_off_center_pages(self):
        good=[(700,140),(1220,140),(1220,940),(700,940)]
        result=p.check_rect(good,(1920,1080))
        self.assertAlmostEqual(result['height_fraction'],800/1080)
        for bad in ([(-1,140),(1220,140),(1220,940),(-1,940)],
                    [(700,400),(1220,400),(1220,650),(700,650)],
                    [(100,140),(620,140),(620,940),(100,940)]):
            with self.assertRaises(AssertionError):p.check_rect(bad,(1920,1080))

    def test_actual_input_cycles_and_repeat_fixture_are_distinct(self):
        f=fixture();d=f.proof
        for cycle in (0,1):
            f.journey.fields.update(Phase=1,CVPaper=None);f.state['paused']=False
            f.clock[0]=max(f.clock[0],d.after);d.tick();self.assertEqual(f.inputs[-1]['key'],'Enter')
            widget=Obj(visible=True);mesh=Obj(static_mesh=Obj())
            paper=Obj(bOpen=True,Widget=widget,ItemMesh=mesh)
            f.journey.fields.update(Phase=2,CVPaper=paper);f.state['paused']=True
            f.clock[0]=d.after;d.tick();f.clock[0]=d.after;d.tick()
            self.assertEqual(d.state,'capture_hold');self.assertEqual(len(f.inputs),cycle*3+1)
            f.clock[0]=d.after;d.tick();self.assertEqual(f.inputs[-1]['key'],'E')
            f.clock[0]=d.after;d.tick();self.assertEqual(d.state,'closing')
            paper.fields['bOpen']=False;widget.fields['visible']=False;mesh.fields['static_mesh']=None
            f.journey.fields['CVPaper']=None;f.state['paused']=False;d.tick()
            self.assertEqual(f.inputs[-1]['key'],'Enter')
            f.clock[0]=d.after;f.journey.fields['Phase']=3;f.car.fields['Active']=True;f.state['pawn']=f.car;d.tick()
        self.assertTrue(d.result['passed'])
        self.assertEqual([v['key'] for v in f.inputs],['Enter','E','Enter']*2)
        self.assertEqual(f.journey.calls,['ResumeRun'])
        self.assertEqual(f.car.calls,['Deactivate'])
        fixtures=[row for row in d.result['trace'] if row['event']=='retry_fixture']
        self.assertEqual(len(fixtures),1);self.assertFalse(fixtures[0]['genuine_progress'])

    def test_open_without_engine_response_times_out_without_direct_handler(self):
        f=fixture();f.proof.tick();f.clock[0]=21;f.proof.tick()
        self.assertEqual(f.proof.result['reason'],'timeout');self.assertFalse(f.proof.result['passed'])
        self.assertEqual(f.journey.calls,[]);self.assertEqual(len(f.inputs),1)

    def test_destroyed_actor_is_not_dereferenced_on_tick_or_cleanup(self):
        f=fixture();f.journey.valid=False;f.proof.tick();f.proof.close()
        self.assertEqual(f.proof.result['reason'],'world_or_actor_gone');self.assertEqual(f.inputs,[])
        f=fixture();f.engine.SystemLibrary.is_valid=Mock(side_effect=TypeError('ObjectInstance is null'))
        self.assertFalse(f.proof.alive());f.proof.close()
        f.engine.SystemLibrary.is_valid=Mock(side_effect=TypeError('unrelated argument error'))
        with self.assertRaisesRegex(TypeError,'unrelated'):f.proof.alive()


if __name__=='__main__':unittest.main()
