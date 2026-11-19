"""Exact helper filters must never inspect, move or capture unrelated graphs."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import bp_layout
import hayba_call
sys.path.insert(0,str(Path(__file__).parent/'level2'))
import final_l2_graph_targets as targets


class FilterTests(unittest.TestCase):
    def run_layout(self,names=None,missing=()):
        seen=[]
        def call(command,params,**unused):
            if command=='blueprint_get_info':
                return {'ok':True,'data':{'functions':['Legacy','Helper'],'parent_class':'Actor'}}
            name=params['graph_name'];seen.append((command,name))
            if name in missing:return {'ok':False,'error':'Graph missing: '+name}
            return {'ok':True,'data':{'nodes':[],'edges':[],'measured':True}}
        with tempfile.TemporaryDirectory() as saved,patch.object(bp_layout,'SAVED',saved), \
             patch.object(hayba_call,'call',call),patch.object(bp_layout,'from_hayba',return_value={}), \
             patch.object(bp_layout,'hayba_graph_calls',side_effect=lambda _,g,*a:([],{'nodes':1})):
            result=bp_layout.drive('/Game/Test/BP_Test',dry_run=True,graph_names=names)
        return result,seen

    def test_filter_inspects_only_exact_requested_names(self):
        result,seen=self.run_layout(('Helper','Helper'))
        self.assertEqual(set(result['graphs']),{'Helper'})
        self.assertEqual({g for _,g in seen},{'Helper'})

    def test_none_preserves_default_and_empty_selects_nothing(self):
        result,_=self.run_layout();self.assertEqual(set(result['graphs']),{'EventGraph','Legacy','Helper'})
        result,seen=self.run_layout([]);self.assertEqual(result['graphs'],{});self.assertEqual(seen,[])

    def test_missing_explicit_graph_fails_before_apply(self):
        result,seen=self.run_layout(('Helper','Typo'),missing=('Typo',))
        self.assertIn('Typo',result['error']);self.assertNotIn('applied',result)
        self.assertNotIn('Legacy',{g for _,g in seen})

    def test_filtered_graph_can_be_beyond_get_info_transport_page(self):
        result,_=self.run_layout(('BeyondFirst50',))
        self.assertEqual(set(result['graphs']),{'BeyondFirst50'})

    def test_shared_capture_filter_matches_layout_and_excludes_legacy(self):
        self.assertEqual(sum(map(len,targets.GRAPH_NAMES.values())),18)
        self.assertEqual(targets.GRAPH_NAMES[targets.TARGETS['player_camera']],('UpdateFirstPersonVisibility',))
        self.assertEqual(targets.GRAPH_NAMES[targets.TARGETS['interactor']],('FindBest','Scan'))
        for path,names in targets.GRAPH_NAMES.items():
            self.assertEqual(targets.capture_names(path,['EventGraph','Legacy',*names]),list(names))
            with self.assertRaisesRegex(AssertionError,'Requested graphs missing'):
                targets.capture_names(path,['EventGraph'])
        journey=targets.TARGETS['journey']
        self.assertEqual(targets.capture_names(journey,['EventGraph','StartJourney']),['EventGraph','StartJourney'])


if __name__=='__main__':unittest.main()
