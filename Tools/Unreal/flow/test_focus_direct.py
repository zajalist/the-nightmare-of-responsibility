import unittest
import patch_focus_direct as focus

class DirectFocusTest(unittest.TestCase):
    def test_direct_visible_hit_keeps_existing_sweep_and_scoring(self):
        nodes=[dict(node_id=i,title=t) for i,t in (
            ('sphere','Multi Sphere Trace For Objects'),('hit','BreakHitResult'),('store','Set BestCost'),
            ('entry','FindBest'),('cost','float - float'),('less','float < float'))]
        wires=[('entry','then','sphere','execute'),('camera','ReturnValue','sphere','Start'),
               ('end','ReturnValue','sphere','End'),('types','Array','sphere','ObjectTypes'),
               ('cost','ReturnValue','store','BestCost'),('cost','ReturnValue','less','A')]
        edges=[dict(from_node=a,from_pin=ap,to_node=b,to_pin=bp) for a,ap,b,bp in wires]
        ops=focus.plan(nodes,edges).ops
        links={(o['from_node'],o['from_pin'],o['to_node'],o['to_pin']) for o in ops if o['op']=='connect'}
        self.assertIn(('entry','then','direct_ray','execute'),links)
        self.assertIn(('direct_ray','then','sphere','execute'),links)
        self.assertIn(('ray_cost','ReturnValue','store','BestCost'),links)
        self.assertIn(('ray_cost','ReturnValue','less','A'),links)
        self.assertIn(('cost','ReturnValue','ray_cost','A'),links)
        self.assertFalse(any(o['op']=='remove' for o in ops))
        nodes.append(dict(node_id='direct_ray',title='Line Trace For Objects'))
        self.assertFalse(focus.plan(nodes,edges).ops)

if __name__=='__main__':unittest.main()
