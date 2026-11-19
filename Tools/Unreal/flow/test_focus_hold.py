"""Offline regression: a scan miss must not evaluate bounds on an invalid held target."""
import unittest
from unittest.mock import patch

import patch_focus_hold as focus


class FocusHoldTest(unittest.TestCase):
    def setUp(self):
        self.nodes = [dict(node_id=key, title=title) for key, title in (
            ('best', 'FindBest'), ('set', 'SetFocus'), ('cur', 'Get Target'),
            ('valid', 'Is Valid'), ('found', 'Branch'), ('hold', 'Branch'))]
        self.edges = [dict(from_node=a, from_pin=ap, to_node=b, to_pin=bp) for a, ap, b, bp in (
            ('best', 'then', 'found', 'execute'), ('found', 'then', 'set', 'execute'),
            ('found', 'else', 'hold', 'execute'), ('cur', 'Target', 'valid', 'Object'),
            ('keep', 'ReturnValue', 'hold', 'Condition'),
            ('hold', 'then', 'refresh', 'execute'), ('hold', 'else', 'set', 'execute'))]

    def run_scan(self, found, valid, keep):
        """Model eager pure-node inputs when the execution reaches their consuming branch."""
        node = 'found'
        while node not in ('set', 'refresh'):
            if node == 'found':
                condition = found
            elif node == 'hold':
                if not valid:
                    raise AssertionError('GetActorBounds read an invalid Target')
                condition = keep
            else:
                condition_edge = next(e for e in self.edges if e['to_node'] == node and e['to_pin'] == 'Condition')
                self.assertEqual(condition_edge['from_node'], 'valid')
                condition = valid
            node = next(e['to_node'] for e in self.edges if e['from_node'] == node
                        and e['from_pin'] == ('then' if condition else 'else') and e['to_pin'] == 'execute')
        return node

    def apply(self, batch):
        for op in batch.ops:
            if op['op'] == 'disconnect':
                self.edges = [e for e in self.edges if not (
                    e['from_node'] == op['node_id'] and e['from_pin'] == op['pin_name']
                    and e['to_node'] == op['to_node'] and e['to_pin'] == op['to_pin'])]
            elif op['op'] == 'connect':
                self.edges.append({k: op[k] for k in ('from_node', 'from_pin', 'to_node', 'to_pin')})

    def test_missing_target_clears_without_reading_geometry_and_valid_focus_still_holds(self):
        with self.assertRaisesRegex(AssertionError, 'invalid Target'):
            self.run_scan(False, False, False)
        with patch.object(focus.Batch, 'run', lambda batch: self.apply(batch)):
            focus.guard_hold(self.nodes, self.edges)
        self.assertEqual(self.run_scan(False, False, False), 'set')
        self.assertEqual(self.run_scan(False, True, True), 'refresh')
        self.assertEqual(self.run_scan(False, True, False), 'set')
        self.assertEqual(self.run_scan(True, False, False), 'set')
        with patch.object(focus.Batch, 'run') as run:
            focus.guard_hold(self.nodes, self.edges)
            run.assert_not_called()


if __name__ == '__main__':
    unittest.main()
