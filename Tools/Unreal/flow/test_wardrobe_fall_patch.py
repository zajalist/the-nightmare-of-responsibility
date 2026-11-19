"""Offline regression check: sequence ownership ends before the teleport; cleanup remains reachable."""
import unittest
from unittest.mock import patch

import patch_wardrobe_fall as fall


class WardrobePatchTest(unittest.TestCase):
    def capture(self, build):
        batches = []
        with patch.object(fall, 'fresh', return_value='entry'), \
                patch.object(fall.Batch, 'run', lambda batch: batches.append(batch.ops)):
            build()
        return batches[-1]

    def test_reformation_runs_after_sequence_releases_pawn(self):
        ops = self.capture(fall.play)
        pins = {(o['node_id'], o['pin_name']): o['value'] for o in ops if o['op'] == 'set_pin'}
        times = {pins[o['ref'], 'FunctionName']: float(pins[o['ref'], 'Time'])
                 for o in ops if o.get('function_name', '').endswith(':K2_SetTimer')}
        self.assertLess(times['WardrobeFallDone'], times['WardrobeVanish'])
        self.assertLess(times['WardrobeVanish'], times['WardrobeReappear'])
        self.assertLess(times['WardrobeReappear'], times['FinishWardrobeTransition'])
        reached = {'entry'}
        edges = [o for o in ops if o['op'] == 'connect' and o['to_pin'] == 'execute']
        for _ in edges:
            reached.update(o['to_node'] for o in edges if o['from_node'] in reached)
        self.assertTrue({'done', 'sand', 'vanish', 'reappear', 'finish'} <= reached)
        done = self.capture(fall.done)
        self.assertTrue(any(o.get('function_name', '').endswith(':Stop') for o in done))
        self.assertFalse(any(o.get('variable_name') == 'bWardrobeTransition' for o in done))
        self.assertTrue(any(o.get('from_node') == 'stop' and o.get('to_node') == 'top' for o in done))
        stage_delay = next(float(o['value']) for o in done
                           if o.get('node_id') == 'stage' and o.get('pin_name') == 'Time')
        self.assertLess(times['WardrobeFallDone'] + stage_delay, times['WardrobeReappear'])

    def test_old_reset_prefix_no_longer_disables_cleanup(self):
        nodes = [{'node_id': 'player', 'title': 'Get WardrobeFallPlayer'},
                 {'node_id': 'off', 'title': 'Set bWardrobeTransition'}]
        edges = [dict(from_node=a, from_pin=p, to_node=b, to_pin='execute')
                 for a, p, b in [('branch', 'else', 'off'), ('stop', 'then', 'off'), ('off', 'then', 'cleanup')]]
        batches = []
        with patch.object(fall, 'inspect', return_value=(nodes, edges)), \
                patch.object(fall.Batch, 'run', lambda batch: batches.append(batch.ops)):
            fall.reset()
        self.assertEqual(batches[0][0], dict(op='remove', node_ids=['off']))
        self.assertEqual({o['from_node'] for o in batches[0] if o['op'] == 'connect'}, {'branch', 'stop'})
        self.assertTrue(all(o['to_node'] == 'cleanup' for o in batches[0] if o['op'] == 'connect'))


if __name__ == '__main__':
    unittest.main()
