"""Offline safety checks. No editor connection or lease is taken."""
import tempfile
import unittest
import csv
from pathlib import Path
from unittest.mock import patch

import build_splat_dynamics as dynamics
import run_splat_dynamics_map as runner
import splat_dynamics_media as media


class SplatChecks(unittest.TestCase):
    def test_csv_keeps_states_separate(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'proof.csv'
            with path.open('w', newline='') as stream:
                writer = csv.writer(stream); writer.writerow(['EVENTS', 'GPUTime'])
                for state, gpu in [('off_rest', 2), ('on_sand', 4)]:
                    writer.writerow([f'Cmd: Shot dream_{state}_before.png', 999])
                    writer.writerows([['', gpu]] * 40)
                    writer.writerow([f'Cmd: Shot dream_{state}_after.png', 999])
            result = media.summarize(path)
            self.assertEqual(result['dream_off_rest']['gpu_ms_median'], 2)
            self.assertEqual(result['dream_on_sand']['gpu_ms_p95'], 4)

    def test_motion_boundaries(self):
        dynamics.selftest()

    def test_layout_rerun_reuses_native_node(self):
        native = 'MaterialExpressionFunctionInput_2'
        def call(name, **args):
            if name == 'material_get_info':
                return {'expressions': [{'id': native, 'class': 'MaterialExpressionFunctionInput', 'x': 123, 'y': 456}]}
            self.assertEqual(name, 'material_set_node')
            self.assertEqual(args['node_id'], native)
            return {}
        with patch.object(dynamics, 'call', call):
            self.assertEqual(dynamics.node(dynamics.FN, 'FunctionInput', -1200, 840, InputName='CornerOffset'), native)

    def test_dirty_bedroom_never_switches(self):
        calls = []
        def call(name, **args):
            calls.append(name)
            return {'pie_running': False, 'map': runner.BED, 'dirty_packages': [runner.BED]}
        with tempfile.TemporaryDirectory() as folder, patch.object(runner, 'OUT', Path(folder)), \
             patch.object(runner, 'call', call), patch.object(runner.subprocess, 'run') as shell:
            with self.assertRaisesRegex(AssertionError, 'dirty bedroom'):
                runner.run('dream', 'build')
            self.assertEqual(calls, ['editor_get_state'])
            self.assertEqual(shell.call_args.args[0][-2:], ['release', 'splat-vfx'])

    def test_failed_placement_returns_and_verifies(self):
        loads = []
        def call(name, **args):
            if name == 'editor_get_state':
                return {'pie_running': False, 'map': runner.BED, 'dirty_packages': []}
            if name == 'level_load':
                loads.append(args['path']); return {}
            if name == 'actor_list':
                return {'actors': []}
            if name == 'actor_spawn':
                raise RuntimeError('placement failed')
            raise AssertionError(name)
        with tempfile.TemporaryDirectory() as folder, patch.object(runner, 'OUT', Path(folder)), \
             patch.object(runner, 'call', call), patch.object(runner, 'count', return_value='bedroom 123 enc True beat True ps True') as count, \
             patch.object(runner.subprocess, 'run') as shell:
            with self.assertRaisesRegex(RuntimeError, 'placement failed'):
                runner.run('dream', 'build')
            self.assertEqual(loads[-1], runner.BED)
            self.assertEqual(count.call_count, 2)
            self.assertEqual(shell.call_args.args[0][-2:], ['release', 'splat-vfx'])

    def test_failed_pie_cleanup_still_attempts_return(self):
        loads = []
        def call(name, **args):
            if name == 'editor_get_state':
                return {'pie_running': False, 'map': runner.BED, 'dirty_packages': []}
            if name == 'level_load':
                loads.append(args['path']); return {}
            raise AssertionError(name)
        def script(path, **args):
            if args.get('FOA_CALL') == 'BEGIN':
                return 'begin'
            raise RuntimeError('capture or cleanup failed')
        with tempfile.TemporaryDirectory() as folder, patch.object(runner, 'OUT', Path(folder)), \
             patch.object(runner, 'call', call), patch.object(runner, 'script', script), \
             patch.object(runner, 'count', return_value='same bedroom'), patch.object(runner.time, 'sleep'), \
             patch.object(runner.subprocess, 'run') as shell:
            with self.assertRaisesRegex(RuntimeError, 'capture or cleanup failed'):
                runner.run('dream', 'proof')
            self.assertEqual(loads[-1], runner.BED)
            self.assertEqual(shell.call_args.args[0][-2:], ['release', 'splat-vfx'])


if __name__ == '__main__':
    unittest.main()
