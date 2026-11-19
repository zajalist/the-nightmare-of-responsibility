"""Offline regression: incomplete native reads never dispatch layout mutations."""
import copy
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import bp_layout as layout
import hayba_call


PATH='/Game/FoA/UI/Framework/BP_FoAFrontEnd'
INSPECT=dict(nodes=[dict(node_id='A',pins=[])],edges=[],node_count=1,edge_count=0)
MEASURE=dict(nodes=[dict(node_id='A',rect=[0,0,100,50])],node_count=1)


class CompleteGraphLayout(unittest.TestCase):
    def run_drive(self,inspection,measurement,graphs=('SayCharacter',)):
        def read(command,args,**kwargs):
            self.assertIn(command,('blueprint_get_info','blueprint_inspect_graph','blueprint_measure_nodes'))
            data={'parent_class':'Actor'} if command=='blueprint_get_info' else (
                inspection if command=='blueprint_inspect_graph' else measurement)
            return dict(ok=True,data=copy.deepcopy(data))
        with tempfile.TemporaryDirectory() as folder, patch.object(layout,'SAVED',folder), \
             patch.object(hayba_call,'call',side_effect=read), \
             patch.object(hayba_call,'connect') as connect, \
             patch.object(layout,'hayba_graph_calls',return_value=([],{'nodes':1})) as planner:
            result=layout.drive(PATH,dry_run=False,graph_names=graphs)
            connect.assert_not_called()
            return result,planner.call_count

    def test_missing_nodes_edges_measurements_and_nested_pins_never_plan(self):
        cases=[]
        for field in ('node_count','edge_count'):
            value=copy.deepcopy(INSPECT);value[field]+=1;cases.append((value,MEASURE))
        value=copy.deepcopy(MEASURE);value['node_count']=2;cases.append((INSPECT,value))
        value=copy.deepcopy(INSPECT);value['_truncated']=['nodes'];cases.append((value,MEASURE))
        value=copy.deepcopy(INSPECT);value['nodes'][0]['_truncated']=['pins'];cases.append((value,MEASURE))
        value=copy.deepcopy(MEASURE);value['nodes'][0]['node_id']='B';cases.append((INSPECT,value))
        for inspection,measurement in cases:
            with self.subTest(inspection=inspection,measurement=measurement):
                result,planned=self.run_drive(inspection,measurement)
                self.assertTrue(result['incomplete_snapshot'])
                self.assertEqual(planned,0)
                self.assertNotIn('applied',result)

    def test_complete_snapshot_reaches_planner(self):
        result,planned=self.run_drive(INSPECT,MEASURE)
        self.assertNotIn('error',result)
        self.assertEqual(planned,1)

    def test_later_incomplete_graph_prevents_earlier_planned_mutations(self):
        def read(command,args,**kwargs):
            data={'parent_class':'Actor'}
            if command=='blueprint_inspect_graph':
                data=copy.deepcopy(INSPECT)
                if args['graph_name']=='StopCharacterVoice':data['edge_count']=10
            if command=='blueprint_measure_nodes':data=MEASURE
            return dict(ok=True,data=copy.deepcopy(data))
        with tempfile.TemporaryDirectory() as folder, patch.object(layout,'SAVED',folder), \
             patch.object(hayba_call,'call',side_effect=read), patch.object(hayba_call,'connect') as connect, \
             patch.object(layout,'hayba_graph_calls',return_value=([{'name':'blueprint_move_nodes','args':{}}],{'nodes':1})):
            result=layout.drive(PATH,graph_names=('SayCharacter','StopCharacterVoice'))
            self.assertTrue(result['incomplete_snapshot'])
            connect.assert_not_called()

if __name__=='__main__':unittest.main()
