"""Offline regression: native node, edge and measurement pages all reach layout."""
import copy
import tempfile
import unittest
from unittest.mock import patch

import bp_layout
import hayba_call


class Pagination(unittest.TestCase):
    def test_independent_pages(self):
        for nested_measure in (False, True):
            with self.subTest(nested_measure=nested_measure), tempfile.TemporaryDirectory() as saved:
                seen=[]
                def call(command, params, **unused):
                    if command=='blueprint_get_info':
                        return {'ok':True,'data':{'functions':[]}}
                    def chunk(kind, param, count):
                        start=params.get(param,0)
                        return list(range(start,min(start+50,count))), {'next_offset':50 if start==0 else None}
                    if command=='blueprint_inspect_graph':
                        nodes,np=chunk('nodes','offset',73)
                        edges,ep=chunk('edges','edge_offset',91)
                        result={'nodes':nodes,'edges':edges,'page':{'nodes':np,'edges':ep}}
                    elif command=='blueprint_measure_nodes':
                        nodes,page=chunk('nodes','offset',73)
                        result={'nodes':[{'node_id':n,'rect':[0,0,100,60]} for n in nodes],
                                'measured':True,'page':{'nodes':page} if nested_measure else page}
                    else:
                        raise AssertionError(command)
                    return {'ok':True,'data':copy.deepcopy(result)}
                def parse(ins,meas):
                    seen.append((ins,meas))
                    self.assertEqual(ins['nodes'],list(range(73)))
                    self.assertEqual(ins['edges'],list(range(91)))
                    self.assertEqual([n['node_id'] for n in meas['nodes']],list(range(73)))
                    return {}
                with patch.object(hayba_call,'call',call), patch.object(bp_layout,'SAVED',saved), \
                     patch.object(bp_layout,'from_hayba',parse), \
                     patch.object(bp_layout,'hayba_graph_calls',return_value=([],{})):
                    result=bp_layout.drive('/Game/Test/BP_Test',dry_run=True)
                self.assertEqual(len(seen),1)
                self.assertNotIn('error',result)


if __name__=='__main__':
    unittest.main()
