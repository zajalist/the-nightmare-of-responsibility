"""Offline policy and bounded-driver safety tests. No Unreal import or editor calls."""
import ast
import copy
from pathlib import Path
import unittest

import cv_proof as p
from cv_data import OPPONENTS


def state():
    return dict(composure=100, resolve=40, statuses=[], target=1, free_preview=False,
        sections=[dict(id=n, progress=0, state='Idle', intent='CVWait', actions=d['ActMoves'])
                  for n, d in OPPONENTS.items()])


class Policy(unittest.TestCase):
    def test_respects_block_and_cost(self):
        s = state()
        s.update(resolve=0, statuses=['Constricted', 'SleeveLabyrinth', 'Mismatched'])
        before = copy.deepcopy(s)
        target, move = p.choose_action(s)
        self.assertIsNotNone(p.predict(s, target, move))
        self.assertEqual(s, before)
        self.assertNotIn(move, ('DeepBreath', 'CheckMirror', 'CVRewriteExperience',
                                'CVRewriteLogistics', 'CVRewriteReliability'))

    def test_takes_real_winning_action(self):
        s = state()
        for g in s['sections']:
            g['progress'] = 4
        s['sections'][2]['progress'] = 3
        self.assertEqual(p.choose_action(s), (2, 'CVRewriteReliability'))

    def test_stun_prevents_lethal_intent(self):
        s = state()
        s.update(composure=10, resolve=0)
        s['sections'][2]['intent'] = 'CVOriginalReliability'
        self.assertEqual(p.choose_action(s), (2, 'CVLoosenClaim'))

    def test_free_preview_mirror_can_save_low_health(self):
        s = state()
        s.update(composure=1, resolve=0, free_preview=True)
        self.assertGreater(p.predict(s, None, 'CheckMirror'), -10000)

    def test_assist_does_not_repeat_widen_only_action(self):
        s = state()
        s['statuses'] = ['ArmholeFound']
        self.assertNotEqual(p.choose_action(s)[1], 'CVFindDetail')

    def test_selected_pool_has_bounded_assisted_simulation(self):
        from sim_cv import run
        result = run(1,4,2,4)
        self.assertEqual((result['wins'], result['losses'], result['caps']), (100,0,0))
        self.assertLessEqual(result['median'], 30)
        self.assertLessEqual(result['p90'], 40)

    def test_driver_never_assigns_battle_properties_or_registers_callback(self):
        tree = ast.parse(Path(p.__file__).read_text())
        methods = {n.func.attr for n in ast.walk(tree) if isinstance(n, ast.Call)
                   and isinstance(n.func, ast.Attribute)}
        self.assertFalse(methods & {'set_editor_property', 'register_slate_post_tick_callback',
                                    'editor_play_simulate', 'editor_end_play', 'save_loaded_asset'})

    def test_forced_fixture_is_separate_from_action_play(self):
        source = Path(p.__file__).read_text()
        play = source.split("if self.state == 'play_retry':", 1)[1]
        self.assertNotIn("'ApplySelf'", play)
        self.assertNotIn("'ApplyPlayerMove'", play)
        self.assertNotIn("'FinaleWon'", play)
        self.assertIn("'ChooseMove'", play)
        self.assertIn("'CycleTarget'", play)

    def test_close_never_touches_dead_world(self):
        d = object.__new__(p.CVProof)
        d.alive = lambda: False
        d.close()  # Engine deliberately absent: any engine call would fail.

    def test_early_finish_skips_only_widget_cleanup(self):
        import build_cv as c
        chain = ['entry','cancel','actor_timer','widget_timer0','widget_timer1','restore','remove','party','done']
        widget_calls = {'cancel':'Cancel Latent Actions','widget_timer0':'Clear Timer by Function Name',
                        'widget_timer1':'Clear Timer by Function Name','remove':'Remove from Parent'}
        nodes = [dict(node_id=n,title=widget_calls.get(n,n)) for n in chain]
        edges = [dict(from_node=a,from_pin='then',to_node=b,to_pin='execute') for a,b in zip(chain,chain[1:])]
        edges += [dict(from_node='widget',from_pin='Widget',to_node=n,
                       to_pin='Object' if n.startswith('widget_timer') else 'self') for n in widget_calls]
        plan = c.widget_cleanup_plan(nodes, edges)
        available = {n['node_id'] for n in nodes} | {'widget'}
        for op in plan.ops:
            if op['op']=='add_node':
                self.assertNotIn(op['ref'], available)
                available.add(op['ref'])
            for key in ('from_node','to_node','node_id'):
                if key in op:self.assertIn(op[key], available, (op, 'forward or unknown reference'))
            for ref in op.get('node_ids', []):self.assertIn(ref, available)
        runtime = [e.copy() for e in edges]
        branches = set()
        for op in plan.ops:
            if op['op']=='add_node' and op.get('node_type')=='branch':branches.add(op['ref'])
            if op['op']=='disconnect':
                runtime.remove(dict(from_node=op['node_id'],from_pin=op['pin_name'],
                                    to_node=op['to_node'],to_pin=op['to_pin']))
            if op['op']=='connect':runtime.append({k:op[k] for k in ('from_node','from_pin','to_node','to_pin')})
        def walk(valid):
            current, visited = 'entry', []
            for _ in range(30):
                visited.append(current)
                if current=='done':return visited
                pin = 'then' if current not in branches or valid else 'else'
                successors = [e['to_node'] for e in runtime if e['from_node']==current and e['from_pin']==pin]
                self.assertEqual(len(successors), 1)
                current = successors[0]
            self.fail('Cleanup chain did not terminate')
        self.assertEqual([n for n in walk(True) if n not in branches], chain)
        self.assertEqual([n for n in walk(False) if n not in branches],
                         [n for n in chain if n not in widget_calls])
        self.assertIsNone(c.widget_cleanup_plan(nodes+[dict(node_id='comment',title='Widget cleanup readiness')], edges))


if __name__ == '__main__':
    unittest.main()
