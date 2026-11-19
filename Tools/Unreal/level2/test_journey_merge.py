"""Offline shell-region and graph-plan checks; engine compilation/visual alignment still require PIE."""
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import build_drive
import build_journey_merge as merge


def coverage(amount, position):
    # Evaluate the actual shader's scalar region expressions, before its integer grain hash.
    values = dict(Amount=amount, P=SimpleNamespace(x=position[0], y=position[1], z=position[2]),
                  HeightMin=0, HeightRange=180, SideRange=85, max=max, abs=abs,
                  saturate=lambda x: min(1, max(0, x)), step=lambda edge, x: float(x >= edge))
    for line in merge.SHADER.split('uint3')[0].splitlines():
        line = line.strip().removeprefix('float ')
        if line:
            name, expression = line.rstrip(';').split('=', 1)
            values[name.strip()] = eval(expression, {'__builtins__': {}}, values)
    return values['coverage']


class JourneyMergeTest(unittest.TestCase):
    def test_teen_wrist_and_thumb_covered_before_forearm(self):
        # Measured rest joints: Saved/AnimShots/teen_hand_frame.json, centimetres.
        wrist=(-51.248725,22.139488,116.139111)
        thumb=(-48.798730,30.269253,114.222301)
        lowerarm=(-37.508066,2.368153,129.456866)
        for point in (wrist,thumb):
            self.assertEqual(coverage(0,point),0)
            self.assertEqual(coverage(.2,point),1)
            self.assertEqual(coverage(.6,point),1)
        self.assertEqual(coverage(.2,lowerarm),0)

    def test_regions_reveal_in_order_and_reverse_on_truth_loss(self):
        points = [(70, 0, 90), (30, 0, 140), (0, 0, 165), (0, 0, 90)]
        for amount, expected in [(-1, (0, 0, 0, 0)), (0, (0, 0, 0, 0)),
                                 (.2, (1, 0, 0, 0)), (.4, (1, 1, 0, 0)),
                                 (.6, (1, 1, 1, 0)), (1, (1, 1, 1, 1)), (2, (1, 1, 1, 1))]:
            with self.subTest(amount=amount):
                for point, value in zip(points, expected):
                    self.assertAlmostEqual(coverage(amount, point), value)
        for point in points:
            self.assertGreaterEqual(coverage(.8, point), coverage(.6, point))
        self.assertNotIn('Clock', merge.SHADER)
        self.assertNotIn('MPC', merge.SHADER)

    def test_graphs_have_valid_wires_and_never_activate_a_nightmare_pawn(self):
        plans = []
        with patch.object(build_drive, 'inspect', lambda path, name: ([dict(node_id='entry', title=name)], [])), \
                patch.object(build_drive.G, 'run', lambda graph: plans.append(graph)):
            for build in (merge.initialize, merge.set_amount, merge.set_visible, merge.restore):
                build()
        self.assertEqual(len(plans), 4)
        for plan in plans:
            refs = {'entry'}
            for op in plan.ops:
                if op['op'] == 'add_node':
                    self.assertNotIn(op['ref'], refs)
                    refs.add(op['ref'])
                    fn = op.get('function_name', '')
                    self.assertFalse(any(word in fn for word in ('Appear', 'Stalk', 'SpawnActor', 'SetTimer', 'SetSandTransition')))
                elif op['op'] == 'connect':
                    self.assertIn(op['from_node'], refs)
                    self.assertIn(op['to_node'], refs)
        initialize = plans[0].ops
        self.assertEqual(sum(op.get('function_name', '').endswith(':SetLeaderPoseComponent') for op in initialize),2)
        variables={op.get('variable_name') for op in initialize if op.get('node_type')=='variable_get'}
        self.assertTrue({'Body','Face','Shell','HeadShell'}<=variables)
        self.assertNotIn('Mesh',variables,'Hidden Manny pose reintroduces the detached second body')
        self.assertEqual(sum(op.get('pin_name')=='NewScale3D' and op.get('value')=='(X=1.02,Y=1.02,Z=1.0)' for op in initialize),2)
        self.assertEqual(sum(op.get('function_name','').endswith(':SetScalarParameterValueOnMaterials') for op in plans[1].ops),2)
        self.assertTrue(any(op.get('pin_name') == 'bNewActorEnableCollision' and op['value'] == 'false' for op in initialize))
        restore = plans[-1].ops
        self.assertTrue(any(op.get('function_name', '').endswith(':K2_DetachFromActor') for op in restore))
        self.assertTrue(any(op.get('function_name', '').endswith(':K2_DetachFromComponent') for op in restore))
        self.assertTrue(any(op.get('pin_name') == 'Amount' and op['value'] == '0' for op in restore))


if __name__ == '__main__':
    unittest.main()
