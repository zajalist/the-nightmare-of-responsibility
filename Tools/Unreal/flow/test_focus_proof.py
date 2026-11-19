"""Exercise the focus driver's gates without importing Unreal or starting its callback."""
import ast
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock


class FocusProofTest(unittest.TestCase):
    def setUp(self):
        world = object()
        self.env = dict(S=dict(done=False, t0=0, phase=8, dts=[], after=0), w=world,
                        time=SimpleNamespace(time=Mock(return_value=20)), free=Mock(return_value=False),
                        stand=Mock(), aim=Mock(), close_inspect=Mock(), finish=Mock(), log=Mock(),
                        D=Mock(), P=Mock(), IA=Mock(), BAG=Mock(), pc=Mock(), BED=Mock(), CASE='boot',
                        ACT={'Wardrobe': Mock()}, cls=lambda path: path,
                        prop=lambda obj, key, default=None: getattr(obj, key, default),
                        INPUTS=Mock(), json=json)
        self.env['unreal'] = SimpleNamespace(
            UnrealEditorSubsystem=object(),
            get_editor_subsystem=lambda _: SimpleNamespace(get_game_world=lambda: world),
            SystemLibrary=SimpleNamespace(is_valid=lambda _: True),
            GameplayStatics=SimpleNamespace(get_actor_of_class=Mock()))
        tree = ast.parse(Path(__file__).with_name('pie_focus_repro.py').read_text())
        self.functions = {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}

    def load(self, name):
        exec(compile(ast.Module(body=[self.functions[name]], type_ignores=[]), 'pie_focus_repro.py', 'exec'), self.env)
        return self.env[name]

    def test_locked_navigation_never_times_out_into_a_teleport(self):
        tick = self.load('tick')
        for phase in (8, 10):
            with self.subTest(phase=phase):
                self.env['S'].update(phase=phase, searched=1, walk_wait=1)
                tick(.016)
                self.env['stand'].assert_not_called()
                self.env['finish'].assert_not_called()

    def test_inspection_requests_one_real_e_after_open_animation(self):
        inspector = SimpleNamespace(bOpen=True)
        self.env['unreal'].GameplayStatics.get_actor_of_class.return_value = inspector
        close = self.load('close_inspect')
        close()
        self.env['INPUTS'].write_text.assert_not_called()
        self.env['time'].time.return_value = 20.7
        close()
        close()
        self.env['INPUTS'].write_text.assert_called_once()
        self.assertEqual(json.loads(self.env['INPUTS'].write_text.call_args.args[0]), {'id': 1, 'key': 'E'})
        inspector.bOpen = False
        close()
        self.assertNotIn('inspect_close_sent', self.env['S'])

    def test_bed_fixture_uses_real_wardrobe_notify_before_waiting_for_transition(self):
        self.env.update(CASE='bed')
        self.env['S']['phase'] = 6
        self.env['free'].return_value = True
        self.load('tick')(.016)
        self.env['D'].call_method.assert_called_once_with('EnterBeat', (6,))
        self.env['ACT']['Wardrobe'].call_method.assert_called_once_with('Interact', ('Notify', 'HandleOff'))
        self.assertEqual(self.env['S']['phase'], 9)
        self.env['stand'].assert_not_called()

    def test_bed_pose_tracks_current_bounds_and_aims_near_surface(self):
        bed=self.env['BED']
        bed.get_actor_bounds.return_value=(SimpleNamespace(x=270,y=-190,z=44),SimpleNamespace(x=100,y=57,z=44))
        at,look=self.load('bed_focus_pose')()
        self.assertEqual(at,(123,-117,92))
        self.assertEqual(look,(170,-149,44))
        self.assertLess(sum((a-b)**2 for a,b in zip(at,look))**.5,100)
        bed.get_actor_bounds.return_value=(SimpleNamespace(x=300,y=-170,z=50),SimpleNamespace(x=100,y=60,z=45))
        self.assertEqual(self.env['bed_focus_pose'](),((153,-94,92),(200,-126,50)))

    def test_blocked_stand_fails_before_claiming_an_aim_position(self):
        self.env['free'].return_value=True
        self.env['P'].teleport.return_value=False
        self.env['unreal'].Vector=lambda *v:v
        self.env['unreal'].Rotator=lambda *v:v
        with self.assertRaisesRegex(RuntimeError,'stand blocked'):
            self.load('stand')((123,-117,92),(170,-149,44))
        self.assertEqual(self.env['P'].teleport.call_count,7)
        self.assertNotIn('aim',self.env['S'])

    def test_watch_does_not_count_focus_before_camera_settles(self):
        self.env['S'].update(phase=11,after=21)
        self.env.update(CASE='bed',steady_then_e=Mock(),focus_scan=Mock())
        self.load('tick')(.016)
        self.env['steady_then_e'].assert_not_called()
        self.env['focus_scan'].assert_not_called()


class FocusRunnerCleanupTest(unittest.TestCase):
    def load(self, original, failed=False):
        tree=ast.parse(Path(__file__).with_name('run_chase_final.py').read_text())
        node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='cleanup')
        call=Mock(side_effect=RuntimeError('END transport failed')) if failed else Mock(return_value={'pie_running':False})
        env=dict(call=call,owner='story',time=Mock(),original=original,prefs=Mock(),before='hash',digest=Mock(return_value='hash'))
        exec(compile(ast.Module(body=[node],type_ignores=[]),'runner','exec'),env)
        return env

    def test_failed_end_still_restores_settings_and_checks_save(self):
        env=self.load(b'original',True)
        with self.assertRaisesRegex(RuntimeError,'END transport failed'):env['cleanup'](True)
        env['prefs'].write_bytes.assert_called_once_with(b'original')
        env['digest'].assert_called_once_with()
        self.assertEqual(env['call'].call_args.kwargs['env'],{'FOA_CALL':'END','FOA_CALLER':'story'})

    def test_absent_settings_restored_and_no_lease_release(self):
        env=self.load(None)
        env['cleanup'](True)
        env['prefs'].unlink.assert_called_once_with()
        env['digest'].assert_called_once_with()
        self.assertFalse(any('lease' in call.args[0] for call in env['call'].call_args_list))


if __name__ == '__main__':
    unittest.main()
