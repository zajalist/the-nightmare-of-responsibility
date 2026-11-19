"""Offline checks for C's timed-door and original-pawn arrival assertions."""
import ast
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock


class HandoffProofTest(unittest.TestCase):
    def setUp(self):
        self.pawn = object()
        self.stream = SimpleNamespace(is_level_visible=Mock(return_value=True))
        self.threshold = SimpleNamespace(Phase=1, Stream=self.stream, Player=self.pawn)
        self.front = SimpleNamespace(bInGameplay=True)
        self.door = 'Closed'
        self.clock = 0
        def wait(predicate):
            while not predicate():
                yield
        self.env = dict(S={}, W=lambda: object(), pawn=lambda: self.pawn, wait=wait,
                        threshold_phase=lambda: self.threshold.Phase, free=lambda: True,
                        one=lambda key: self.threshold if key == 'threshold' else self.front,
                        prop=lambda obj, key, default=None: getattr(obj, key, default),
                        state_of=lambda _: self.door, log=Mock(), shot=lambda _: 'proof.png', Miss=RuntimeError,
                        unreal=SimpleNamespace(GameplayStatics=SimpleNamespace(get_time_seconds=lambda _: self.clock)))
        tree = ast.parse(Path(__file__).with_name('pie_play.py').read_text(encoding='utf-8'))
        nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef)
                 and n.name in ('g_threshold_open', 'g_threshold_arrival', 'fixture_wardrobe')]
        exec(compile(ast.Module(body=nodes, type_ignores=[]), 'pie_play.py', 'exec'), self.env)

    def test_door_waits_for_cinematic_notification(self):
        proof = self.env['g_threshold_open']()
        next(proof)
        self.door, self.clock = 'Open', 3
        with self.assertRaises(StopIteration):
            next(proof)
        self.assertEqual(self.env['log'].call_args.kwargs['result'], 'PASS')

    def test_immediately_open_door_fails(self):
        self.door = 'Open'
        with self.assertRaisesRegex(RuntimeError, 'not immediately'):
            next(self.env['g_threshold_open']())

    def test_arrival_requires_stream_and_original_pawn(self):
        self.threshold.Phase = 3
        self.env['S']['threshold_pawn'] = self.pawn
        with self.assertRaises(StopIteration):
            next(self.env['g_threshold_arrival']())
        self.threshold.Player = object()
        with self.assertRaisesRegex(RuntimeError, 'original pawn'):
            next(self.env['g_threshold_arrival']())
        self.threshold.Player = self.pawn
        self.stream.is_level_visible.return_value = False
        with self.assertRaisesRegex(RuntimeError, 'visible Level 2'):
            next(self.env['g_threshold_arrival']())

    def test_wardrobe_fixture_uses_handle_notification(self):
        director, wardrobe = Mock(), Mock()
        self.env.update(one=lambda _: director, actor=lambda _: wardrobe)
        self.env['fixture_wardrobe']()
        director.call_method.assert_called_once_with('EnterBeat', (6,))
        wardrobe.call_method.assert_called_once_with('Interact', ('Notify', 'HandleOff'))

    def test_boot_continuation_does_not_precomplete_wearing(self):
        tree=ast.parse(Path(__file__).with_name('pie_play.py').read_text(encoding='utf-8'))
        fixture=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='fixture_t4_unworn')
        director,inventory,boot=Mock(),Mock(),Mock()
        env=dict(one=lambda _:director,comp=lambda _:inventory,actor=lambda _:boot)
        exec(compile(ast.Module(body=[fixture],type_ignores=[]),'fixture','exec'),env)
        env['fixture_t4_unworn']()
        director.call_method.assert_called_once_with('EnterBeat',(4,))
        inventory.call_method.assert_called_once_with('Add',('Key',))
        boot.call_method.assert_called_once_with('SetState',('Searched',True))

    def test_boot_continuation_waits_for_release_after_worn(self):
        tree=ast.parse(Path(__file__).with_name('pie_play.py').read_text(encoding='utf-8'))
        plans=next(n.value for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='PLANS' for t in n.targets))
        plan=next(v for k,v in zip(plans.keys,plans.values) if ast.literal_eval(k)=='A1b')
        use=Mock();state={'worn':False,'free':False}
        env=dict(boot=lambda:[],do=Mock(),fixture_t4_unworn=Mock(),use=use,sleep=Mock(),
                 state_of=lambda _: 'Worn' if state['worn'] else 'Searched',free=lambda:state['free'])
        eval(compile(ast.Expression(plan),'plan','eval'),env)
        use.assert_called_once()
        self.assertEqual(use.call_args.args,('Boot_L','Use'))
        done=use.call_args.kwargs['until']
        self.assertFalse(done());state['worn']=True;self.assertFalse(done())
        state['free']=True;self.assertTrue(done())


if __name__ == '__main__':
    unittest.main()
