"""Offline conversation branches, authored evidence and native graph contracts."""
import itertools
from pathlib import Path
import unittest
import build_drive as b
import build_interview as i
import build_journey as j
import build_stop_set as s
import interview_data as d
import journey_data as jd


class InterviewTests(unittest.TestCase):
    def test_stock_names_match_existing_shelf_labels(self):
        import stop_set_data
        signs={row[0]:row for row in stop_set_data.SIGNS}
        for index,name in enumerate(('Rice','Tea','Oats')):
            self.assertEqual(signs['LabelText'+str(index)][2],name)
            self.assertEqual(signs['StockText'+str(index)][2],name)
            self.assertEqual(signs['LabelText'+str(index)][1],'Label'+str(index))
            self.assertEqual(signs['StockText'+str(index)][1],'Grocery')
        self.assertEqual(len([name for name in signs if name.startswith('StockText')]),3)

    def test_six_turns_are_specific_to_the_previous_answer(self):
        self.assertEqual(tuple(row['note'] for row in jd.STOPS),d.NOTES)
        for section in d.SECTIONS:
            self.assertEqual(len(section['choices']),3)
            self.assertEqual(len({row['question'] for row in section['followups']}),3)
            for row in (section,*section['followups']):
                self.assertEqual(len(row['choices']),3)
                self.assertEqual(len({choice['text'] for choice in row['choices']}),3)
                self.assertTrue(all(len(choice['reply'])>25 for choice in row['choices']))

    def test_evidence_answers_win_and_unsupported_claims_cause_local_loss(self):
        for policy,should_win in ((min,True),(max,False)):
            prior=0;composure=100
            for step in range(6):
                row=d.question(step,prior);choice=policy(range(3),key=lambda n:row['choices'][n]['cost'])
                result=d.resolve(step,prior,choice,composure)
                prior,composure=result['prior'],result['composure']
                if result['failed']:break
            self.assertEqual(result['won'],should_win)
            self.assertEqual(result['score'],100 if should_win else 60)
        wins=losses=0
        for choices in itertools.product(range(3),repeat=6):
            prior=0;composure=100
            for step,choice in enumerate(choices):
                result=d.resolve(step,prior,choice,composure)
                prior,composure=result['prior'],result['composure']
                self.assertTrue(0<=composure<=100)
                if result['failed']:break
            wins+=result['won'];losses+=result['failed']
        self.assertGreater(wins,0);self.assertGreater(losses,0)
        self.assertEqual(wins+losses,729)

    def test_answer_order_varies_without_changing_followup_meaning(self):
        for original,reordered in zip(d._AUTHORED_SECTIONS,d.SECTIONS):
            for choice,followup in zip(reordered['choices'],reordered['followups']):
                old=original['choices'].index(choice)
                self.assertEqual(followup['question'],original['followups'][old]['question'])
                self.assertCountEqual(followup['choices'],original['followups'][old]['choices'])
        prior=0;composure=100;best=[]
        for step in range(6):
            row=d.question(step,prior);choice=min(range(3),key=lambda n:row['choices'][n]['cost']);best.append(choice)
            result=d.resolve(step,prior,choice,composure);prior,composure=result['prior'],result['composure']
        self.assertEqual(best,[1,2,0,1,2,0]);self.assertTrue(result['won'])
        prior=0;composure=100
        for step in range(6):
            result=d.resolve(step,prior,0,composure);prior,composure=result['prior'],result['composure']
            if result['failed']:break
        self.assertTrue(result['failed']);self.assertFalse(result['won'])

    def test_all_contacts_unlock_real_actions_and_teach_an_evidence_note(self):
        self.assertEqual(len(d.CONTACTS),3)
        for contact in d.CONTACTS:
            self.assertEqual(len(contact['choices']),3);self.assertEqual(len(contact['responses']),3)
            self.assertTrue(contact['task'] and contact['debrief'])
        self.assertIn('ticket',d.CONTACTS[0]['task'].lower())
        self.assertIn('labels',d.CONTACTS[1]['task'].lower())
        self.assertIn('sit',d.CONTACTS[2]['task'].lower())

    def test_measured_v2_staging_keeps_camera_inside_and_player_out_of_its_axis(self):
        self.assertTrue(d.STAGING_MEASURED)
        self.assertLess(abs(d.CAMERA[0][0]),d.SPLAT_SIZE[0]/2)
        self.assertGreater(abs(d.PLAYER[1]-d.CAMERA[0][1]),70)
        self.assertEqual(d.BACKDROP[2]+27,0)
        self.assertEqual(d.DESK[2],37+d.BACKDROP[2])
        self.assertEqual(d.PLAYER[2],92)
        actual=d.geometry_size(tuple(x+728 for x in d.SPLAT_SIZE),(364,)*3,(364,)*3)
        for value,expected in zip(actual,d.SPLAT_SIZE):self.assertAlmostEqual(value,expected)

    def test_generated_graph_references_and_context_boundaries(self):
        plans=[];original_inspect=b.inspect;original_run=b.G.run
        b.inspect=lambda path,name:([dict(node_id='entry',title=name)],[])
        b.G.run=lambda graph:plans.append(graph)
        try:
            for build in i.GRAPHS.values():build()
            for build in (i.refresh_widget,i.widget_click,i.widget_hover,i.start_interview,s.prepare_interview,s.configure,s.restore,
                          j.confirm,j.use_stop,j.stage_stop,j.stop_action_finished,j.submit,j.abort):build()
        finally:b.inspect=original_inspect;b.G.run=original_run
        for plan in plans:
            known={'entry'};inputs=set()
            for op in plan.ops:
                if op['op']=='add_node':
                    self.assertNotIn(op['ref'],known,(plan.graph,op));known.add(op['ref'])
                for key in ('from_node','to_node','node_id'):
                    if key in op:self.assertIn(op[key],known,(plan.graph,op,'forward reference'))
                if op['op']=='connect' and op['to_pin']!='execute':
                    pin=op['to_node'],op['to_pin'];self.assertNotIn(pin,inputs,(plan.graph,pin));inputs.add(pin)
                self.assertFalse(op.get('function_name','').endswith((':StartLevel2CV',':FailDay',':Equip',':StartNewDay')))
        by_name={plan.graph:plan for plan in plans}
        def calls(name):return [o.get('function_name','') for o in by_name[name].ops]
        self.assertTrue(any(x.endswith(':BeginEnding') for x in calls('Submit')))
        self.assertTrue(any(x.endswith(':ReleaseDialogue') for x in calls('Abort')))
        self.assertTrue(any(x.endswith(':DialogueConfirm') for x in calls('Confirm')))
        self.assertTrue(any(x.endswith(':BeginStopContact') for x in calls('StageStop')))
        self.assertTrue(any(x.endswith(':FinishStopContact') for x in calls('StopActionFinished')))
        self.assertIn('/Script/Engine.SkeletalMeshComponent:PlayAnimation',calls('PrepareInterview'))
        self.assertIn('/Script/Engine.SkeletalMeshComponent:Stop',calls('Restore'))
        for name in ('Configure','PrepareInterview','Restore'):
            variables={op.get('variable_name') for op in by_name[name].ops if op.get('node_type')=='variable_get'}
            self.assertIn('InterviewSuit',variables,name)
        held={op.get('variable_name') for op in by_name['DialogueConfirm'].ops if op.get('node_type')=='variable_get'}
        self.assertTrue({'DialogueHeld','DialogueReady'}<=held)
        loss=[op for op in by_name['InterviewLost'].ops if op.get('node_type')=='variable_set']
        self.assertFalse(any(op['variable_name'].startswith('Edited') for op in loss))
        print('Interview plans',len(plans),'graphs',sum(len(p.ops) for p in plans),'operations')

    def test_no_shared_battle_or_input_graph_rebuild(self):
        setup=Path(i.__file__).with_name('interview_setup.py').read_text()
        self.assertNotIn('.clear()',setup)
        self.assertIn("('Completed','Canceled')",setup)
        self.assertIn("('OnClicked','Click')",setup)
        self.assertNotIn('WBP_Encounter',Path(i.__file__).read_text())


if __name__=='__main__':unittest.main()

