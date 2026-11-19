"""Offline phone context, shared progress and native batch construction checks."""
import ast
from pathlib import Path
import unittest
import phone_progress_data as d
import build_phone_progress as p
from phone_progress_proof import PhoneProof


class Contracts(unittest.TestCase):
    def test_phone_never_interrupts_drive_fight_transition_or_busy_stop(self):
        self.assertEqual([n for n in range(12) if d.can_open_phone(n)],list(d.PHONE_PHASES))
        for phase in range(12):
            self.assertFalse(d.can_open_phone(phase,stop_busy=True))
            self.assertFalse(d.can_open_phone(phase,phone_session=True))
            for mode in (1,2,3):self.assertFalse(d.can_open_phone(phase,dialogue_mode=mode))

    def test_stop_lines_and_notebook_are_separate(self):
        self.assertEqual(d.phone_lines([False]*3),[x['truth'] for x in d.STOPS])
        self.assertEqual(d.phone_lines([True,False,True]),
                         [d.PHONE_REVISIONS[0],d.STOPS[1]['truth'],d.PHONE_REVISIONS[2]])
        self.assertEqual(d.GOAL,'Find a job')
        self.assertEqual(d.MOM,'Did you go out?')

    def test_one_integer_drives_every_bar(self):
        for value, expected in ((-5,0),(0,0),(20,20),(40,40),(60,60),(73,73),(100,100),(120,100)):
            self.assertEqual(d.progress(value),(expected,expected/100))
        self.assertFalse(d.show_progress(0));self.assertFalse(d.show_progress(1))
        self.assertFalse(d.show_progress(9));self.assertFalse(d.show_progress(10))

    def test_route_preserves_original_l1_chain(self):
        nodes=[dict(node_id='entry',title='DoAction'),dict(node_id='original',title='Branch')]
        edges=[dict(from_node='entry',from_pin='then',to_node='original',to_pin='execute')]
        plan=p.route_plan('DoAction',nodes,edges,'CloseL2Phone')
        self.assertFalse(any(o['op']=='remove' for o in plan.ops))
        self.assertTrue(any(o.get('from_node')=='gate' and o.get('from_pin')=='else' and
                            o.get('to_node')=='original' for o in plan.ops))
        self.assertIsNone(p.route_plan('DoAction',nodes+[dict(node_id='new',title='Close L2 Phone')],edges,'CloseL2Phone'))

    def test_all_owned_graphs_have_sequential_references_and_unique_data_inputs(self):
        plans=[]
        original_run=p.Batch.run
        original_graph_run=p.G.run
        original_inspect=p.inspect
        original_base_inspect=p.b.inspect
        def inspect(path,name):
            return [dict(node_id='entry',title=name),dict(node_id='return',title='Return Node')],[]
        p.Batch.run=p.G.run=lambda g:plans.append(g)
        p.inspect=p.b.inspect=inspect
        try:
            for name,build in p.STEPS.items():
                if name not in ('skeleton','tree','hooks','keys','verify'):build()
        finally:
            p.Batch.run=original_run;p.G.run=original_graph_run
            p.inspect=original_inspect;p.b.inspect=original_base_inspect
        self.assertGreaterEqual(len(plans),20)
        for plan in plans:
            known={'entry','return'};inputs=set()
            for op in plan.ops:
                if op['op']=='add_node':
                    self.assertNotIn(op['ref'],known,(plan.graph,op))
                    known.add(op['ref'])
                for key in ('from_node','to_node','node_id'):
                    if key in op:self.assertIn(op[key],known,(plan.graph,op,'forward reference'))
                if op['op']=='connect' and op['to_pin']!='execute':
                    pin=(op['to_node'],op['to_pin']);self.assertNotIn(pin,inputs,(plan.graph,pin));inputs.add(pin)
            calls=[o.get('function_name','') for o in plan.ops]
            if plan.graph=='CacheL1Phone':
                saved={o.get('variable_name') for o in plan.ops if o.get('node_type')=='variable_set'}
                self.assertTrue({'Saved'+name+'Brush' for name in p.INK_BORDERS}<=saved)
            if plan.graph=='RestoreL1Phone':
                self.assertEqual(sum(fn.endswith(':SetBrush') for fn in calls),len(p.INK_BORDERS))
            self.assertFalse(any(n.endswith((':ReportEvent',':FailDay',':StartNewDay',':Equip')) for n in calls),plan.graph)
            if plan.graph=='OpenPhone':
                camera=next(o['ref'] for o in plan.ops if o.get('function_name','').endswith(':SetViewTargetWithBlend'))
                open_call=next(o['ref'] for o in plan.ops if o.get('function_name')==p.cls(p.FRONT)+':OpenPhone')
                self.assertTrue(any(o.get('from_node')==camera and o.get('from_pin')=='then' and
                                    o.get('to_node')==open_call and o.get('to_pin')=='execute' for o in plan.ops))
                player=next(o['ref'] for o in plan.ops if o.get('variable_name')=='Player' and o['op']=='add_node')
                self.assertTrue(any(o.get('from_node')==player and o.get('to_node')==camera and
                                    o.get('to_pin')=='NewViewTarget' for o in plan.ops))
        print('Phone/progress plans:',len(plans),'graphs,',sum(len(x.ops) for x in plans),'operations')

    def test_phone_proof_rejects_exterior_view_and_unsettled_hold(self):
        class Actor:
            def __init__(self,name):self.name=name
            def get_name(self):return self.name
        proof=PhoneProof.__new__(PhoneProof)
        proof.player=Actor('Player');proof.pc=type('PC',(),{})()
        proof.valid=lambda actor:actor is not None
        state=dict(bCameraClose=True,PhoneRaise=1.)
        proof.get=lambda actor,name:state[name]
        proof.pc.get_view_target=lambda:Actor('StopSet')
        with self.assertRaisesRegex(AssertionError,'player camera'):proof.phone_view()
        proof.pc.get_view_target=lambda:proof.player
        state['PhoneRaise']=.5
        with self.assertRaisesRegex(AssertionError,'not settled'):proof.phone_view()
        state['PhoneRaise']=1.
        self.assertEqual(proof.phone_view(),dict(view='Player',phone_raise=1.))

    def test_structural_input_patch_preserves_existing_events(self):
        source=Path(__file__).with_name('phone_progress_setup.py').read_text()
        ast.parse(source)
        self.assertNotIn('.clear()',source)
        self.assertNotIn('Gamepad_Special_Right',source)
        self.assertIn('Gamepad_FaceButton_Left',source)


if __name__=='__main__':unittest.main()
