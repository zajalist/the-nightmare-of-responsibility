"""Offline checks for bounded L1 fixtures and strict native interaction proof behavior."""
import ast
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

SOURCE=Path(__file__).with_name('pie_play.py')


def load(names,env):
    tree=ast.parse(SOURCE.read_text(encoding='utf-8'))
    nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names]
    exec(compile(ast.Module(body=nodes,type_ignores=[]),'pie_play.py','exec'),env)


def wait(predicate):
    while not predicate():yield


class ContinuationsTest(unittest.TestCase):
    def test_aim_corrects_rendered_camera_offset_without_forcing_focus(self):
        camera=SimpleNamespace(get_camera_location=lambda:None,get_camera_rotation=lambda:SimpleNamespace(yaw=40,pitch=15))
        control=SimpleNamespace(player_camera_manager=camera,get_control_rotation=lambda:SimpleNamespace(yaw=30,pitch=10),
                                set_control_rotation=Mock())
        env=dict(pc=lambda:control,S={'dt':.1},unreal=SimpleNamespace(
            MathLibrary=SimpleNamespace(find_look_at_rotation=lambda *_:SimpleNamespace(yaw=60,pitch=20)),
            Rotator=lambda **args:SimpleNamespace(**args)))
        load({'turn_toward'},env)
        self.assertFalse(env['turn_toward'](None,10))
        rotation=control.set_control_rotation.call_args.args[0]
        self.assertEqual((rotation.yaw,rotation.pitch),(50,15))

    def test_command_ui_plan_registered_and_requires_native_confirmation(self):
        tree=ast.parse(SOURCE.read_text(encoding='utf-8'))
        plans=next(n.value for n in tree.body if isinstance(n,ast.Assign)
                   and any(isinstance(t,ast.Name) and t.id=='PLANS' for t in n.targets))
        names=[ast.literal_eval(k) for k in plans.keys]
        self.assertIn('B3u',names)
        self.assertIn('g_battle_command_layout',ast.unparse(plans.values[names.index('B3u')]))
        fixture=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='g_battle_command_layout')
        self.assertIn("press('Enter')",ast.unparse(fixture))
        self.assertNotIn("call_method('ChooseMove'",ast.unparse(fixture))
        runner=(SOURCE.parents[2]/'QA'/'playtest_all.py').read_text(encoding='utf-8')
        additions=[name for node in ast.walk(ast.parse(runner)) if isinstance(node,ast.AugAssign)
                   and isinstance(node.target,ast.Name) and node.target.id=='ALL' for name in ast.literal_eval(node.value)]
        self.assertIn('B3u',additions)

    def test_prior_hit_fixture_leaves_positive_composure_for_real_loss(self):
        state={'Composure':100};calls=[];move=object()
        def call(name,args):
            calls.append(name);self.assertEqual(args,(move,));state['Composure']-=12
        enc=SimpleNamespace(call_method=call)
        env=dict(one=lambda _:enc,unreal=SimpleNamespace(load_asset=lambda _:move),Miss=RuntimeError,log=Mock(),
                 prop=lambda obj,key,default=0:-12 if obj is move else state[key])
        load({'fixture_prior_battle_hits'},env)
        env['fixture_prior_battle_hits']()
        self.assertGreater(state['Composure'],0);self.assertLessEqual(state['Composure'],25)
        self.assertEqual(set(calls),{'ApplySelf'})

    def test_clothing_fixture_stops_before_action_under_test(self):
        for wanted in range(1,8):
            with self.subTest(wanted=wanted):
                state={'stage':1,'active':False};called=[]
                advances={'SearchWardrobeClue':2,'SearchDeskClue':3,'SearchBedClue':4,
                          'BeginClothingToss':5,'EscapeClothingOne':6,'EscapeClothingTwo':7}
                def call(name):
                    called.append(name)
                    if name in advances:state['stage']=advances[name]
                d=SimpleNamespace(call_method=call)
                env=dict(one=lambda _:d,stage=lambda:state['stage'],free=lambda:True,wait=wait,
                         prop=lambda *_:False,log=Mock(),Miss=RuntimeError)
                load({'fixture_clothing_before'},env)
                list(env['fixture_clothing_before'](wanted)())
                self.assertEqual(state['stage'],wanted)
                self.assertEqual([n for n in called if n in advances],[n for n,v in advances.items() if v<=wanted])
                self.assertNotIn('ReachClothingVase',called)

    def test_fixture_waits_for_flight_release_before_next_flight(self):
        state={'stage':1,'free':True,'active':False};called=[]
        advances={'SearchWardrobeClue':2,'SearchDeskClue':3,'SearchBedClue':4,
                  'BeginClothingToss':5,'EscapeClothingOne':6}
        def call(name):
            called.append(name)
            if name in advances:state['stage']=advances[name]
            if name in ('BeginClothingToss','EscapeClothingOne'):
                state.update(active=True,free=False)
        d=SimpleNamespace(call_method=call)
        env=dict(one=lambda _:d,stage=lambda:state['stage'],free=lambda:state['free'],wait=wait,
                 prop=lambda *_:state['active'],log=Mock(),Miss=RuntimeError)
        load({'fixture_clothing_before'},env)
        gen=env['fixture_clothing_before'](6)()
        next(gen)
        self.assertEqual(called[-1],'BeginClothingToss')
        state['free']=True
        next(gen)  # Control returning alone cannot overlap an active flight.
        self.assertNotIn('EscapeClothingOne',called)
        state.update(active=False,free=False)
        next(gen)  # Landing alone cannot inherit the outgoing camera/input lock.
        self.assertNotIn('EscapeClothingOne',called)
        state['free']=True
        next(gen)
        self.assertEqual(called[-1],'EscapeClothingOne')
        state.update(active=False,free=True)
        with self.assertRaises(StopIteration):next(gen)

    def test_native_use_refuses_missing_key_relay_without_interact_fallback(self):
        actor=object();clock=[0.0]
        def now():clock[0]+=.2;return clock[0]
        def empty(*_):
            if False:yield
        def press(_):
            if False:yield
            return False
        env=dict(free=lambda:True,actor=lambda _:actor,wait=wait,approach=empty,aim_point=lambda _:object(),
                 select=Mock(),time=SimpleNamespace(time=now),turn_toward=Mock(),prop=lambda *_:actor,
                 comp=lambda _:object(),want_verb=empty,sleep=empty,state_of=lambda _:'Before',
                 log=Mock(),shot=Mock(),press=press,Miss=RuntimeError,S={})
        load({'native_use'},env)
        with self.assertRaisesRegex(RuntimeError,'native E was not dispatched'):
            list(env['native_use']('Wardrobe',until=lambda:False)())
        self.assertFalse(env['S']['inspect_owner'])

    def test_native_use_closes_item_inspection_with_real_key(self):
        actor=object();clock=[0.0];state={'open':False};keys=[]
        def now():clock[0]+=.2;return clock[0]
        def empty(*_):
            if False:yield
        def press(key):
            keys.append(key);state['open']=len(keys)==1
            if False:yield
            return True
        env=dict(free=lambda:True,actor=lambda _:actor,wait=wait,approach=empty,aim_point=lambda _:object(),
                 select=Mock(),time=SimpleNamespace(time=now),turn_toward=Mock(),prop=lambda *_:actor,
                 comp=lambda _:object(),want_verb=empty,sleep=empty,state_of=lambda _:'Before',
                 log=Mock(),shot=Mock(),press=press,Miss=RuntimeError,S={},inspect_open=lambda:state['open'],
                 W=lambda:None,unreal=SimpleNamespace(GameplayStatics=SimpleNamespace(is_game_paused=lambda _:state['open'])))
        load({'native_use'},env)
        list(env['native_use']('Boot_L',until=lambda:True)())
        self.assertEqual(keys,['E','E'])
        self.assertFalse(env['S']['inspect_owner'])

    def test_loss_proof_cannot_fall_back_to_flee(self):
        fallback=Mock();env=dict(prop=lambda *_:None,log=Mock(),PLAN='D1l',Miss=RuntimeError)
        load({'click'},env)
        with self.assertRaisesRegex(RuntimeError,'refusing Flee fallback'):env['click'](None,'Btn_Act0',fallback)
        fallback.assert_not_called()

    def test_all_continuations_registered_in_runner(self):
        tree=ast.parse(SOURCE.read_text(encoding='utf-8'))
        update=next(n.value for n in tree.body if isinstance(n,ast.Expr) and isinstance(n.value,ast.Call)
                    and isinstance(n.value.func,ast.Attribute) and isinstance(n.value.func.value,ast.Name)
                    and n.value.func.value.id=='PLANS' and n.value.func.attr=='update')
        plans={ast.literal_eval(k) for k in update.args[0].keys}
        qa=ast.parse((SOURCE.parents[2]/'QA'/'playtest_all.py').read_text(encoding='utf-8'))
        names=[]
        for n in qa.body:
            if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='ALL' for t in n.targets):names+=ast.literal_eval(n.value)
            if isinstance(n,ast.AugAssign) and isinstance(n.target,ast.Name) and n.target.id=='ALL':names+=ast.literal_eval(n.value)
        self.assertEqual(len(plans),15);self.assertTrue(plans<=set(names))


if __name__=='__main__':unittest.main()
