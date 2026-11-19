"""Paper inspection ownership and native graph contracts, without editor access."""
import unittest
from unittest.mock import patch
import build_drive as b
import build_journey as j


class PaperInspectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plans={}
        with patch.object(b,'inspect',lambda path,name:([dict(node_id='entry',title=name)],[])), \
             patch.object(b.G,'run',lambda g:cls.plans.update({g.graph:g.ops})):
            for name in ('ShowCVPaper','OpenCVPaper','CheckCVPaper','ReleaseCVPaper',
                         'Confirm','Abort','ResumeRun','ActivateCar','RestartRun'):
                j.GRAPHS[name]()

    def calls(self,name):
        return [op.get('function_name','').rsplit(':',1)[-1] for op in self.plans[name]
                if op['op']=='add_node' and op.get('function_name')]

    def test_repeated_inspection_uses_existing_turntable_without_first_seen_gate(self):
        self.assertIn('ShowCVPaper',self.calls('Confirm'))
        self.assertIn('GetActorOfClass',self.calls('ShowCVPaper'))
        self.assertIn('Open',self.calls('OpenCVPaper'))
        self.assertNotIn('Request',self.calls('OpenCVPaper'))
        self.assertTrue(any(o.get('pin_name')=='Item' and o.get('value')=='L2CVPaper'
                            for o in self.plans['OpenCVPaper']))
        self.assertIn('RemoveFromParent',self.calls('ShowCVPaper'))
        ops=self.plans['OpenCVPaper']
        gate=next(o['ref'] for o in ops if o.get('node_type')=='branch')
        refresh=next(o['ref'] for o in ops if o.get('function_name','').endswith(':Refresh'))
        def reachable(pin):
            edges=[o for o in ops if o['op']=='connect' and o['to_pin']=='execute']
            reached={o['to_node'] for o in edges if o['from_node']==gate and o['from_pin']==pin}
            while True:
                expanded=reached|{o['to_node'] for o in edges if o['from_node'] in reached}
                if expanded==reached:return reached
                reached=expanded
        self.assertNotIn(refresh,reachable('then'))
        self.assertIn(refresh,reachable('else'),'Only the failed-open path may show an error panel')

    def test_put_away_returns_to_journey_without_auto_driving(self):
        ops=self.plans['CheckCVPaper']
        self.assertTrue(any(o.get('variable_name')=='bOpen' for o in ops))
        self.assertIn('K2_ClearTimer',self.calls('CheckCVPaper'))
        self.assertIn('Refresh',self.calls('CheckCVPaper'))
        self.assertNotIn('EnterCar',self.calls('CheckCVPaper'))

    def test_all_journey_exit_paths_release_only_owned_inspection(self):
        for name in ('Abort','ResumeRun','ActivateCar','RestartRun'):
            self.assertIn('ReleaseCVPaper',self.calls(name),name)
        release=self.calls('ReleaseCVPaper')
        self.assertLess(release.index('K2_ClearTimer'),release.index('Finish'))
        self.assertIn('IsValid',release)
        self.assertNotIn('GetActorOfClass',release)
        self.assertNotIn('K2_DestroyActor',release)
        self.assertFalse(any(o.get('pin_name')=='CVPaper' and o.get('op')=='set_pin'
                             for o in self.plans['ReleaseCVPaper']),
                         'Leave object setter unconnected: Hayba treats literal None as an asset path')

    def test_native_exec_getter_and_edges_are_wired(self):
        for name,ops in self.plans.items():
            refs={'entry'};inputs=set()
            for op in ops:
                if op['op']=='add_node':
                    self.assertNotIn(op['ref'],refs);refs.add(op['ref'])
                if op['op']=='connect':
                    self.assertIn(op['from_node'],refs,name);self.assertIn(op['to_node'],refs,name)
                    if op['to_pin']!='execute':
                        dest=(op['to_node'],op['to_pin']);self.assertNotIn(dest,inputs,name);inputs.add(dest)
            for op in ops:
                if op.get('function_name','').endswith(':GetActorOfClass'):
                    self.assertTrue(any(edge.get('to_node')==op['ref'] and edge.get('to_pin')=='execute' for edge in ops))


if __name__=='__main__':unittest.main()
