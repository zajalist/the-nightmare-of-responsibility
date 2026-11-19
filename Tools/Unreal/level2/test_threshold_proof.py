"""Offline fault injection for proof teardown and stable stop capture."""
import ast
import json
import tempfile
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock


def functions(filename,names):
    tree=ast.parse(Path(__file__).with_name(filename).read_text(encoding='utf-8'))
    return compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names],type_ignores=[]),filename,'exec')


class ThresholdProofTest(unittest.TestCase):
    def test_mouse_dispatch_requires_exact_enabled_button(self):
        request=dict(kind='click',match='An authored answer',prefer_type='SButton')
        target=dict(type='SButton',text=request['match'],enabled=True,interactive=True,center_x=300,center_y=500)
        calls=[];focus=Mock();translate=Mock(return_value=(310,520))
        def call(command,**args):
            calls.append((command,args))
            if command=='editor_pie_widget_tree':return {'widgets':[target]}
            if command=='editor_pie_press_key':return {'dispatched':True}
            return {'dispatched':True}
        env=dict(call=call,focus_owned_editor=focus,preview_click_point=translate)
        exec(functions('run_threshold_proof.py',{'dispatch_input'}),env)
        reply=env['dispatch_input'](request)
        self.assertEqual(reply['clicked_text'],request['match']);focus.assert_called_once_with()
        self.assertEqual(calls[-1],('editor_pie_mouse',dict(action='click',x=310,y=520,coordinate_space='absolute',button='left')))
        target['enabled']=False
        with self.assertRaisesRegex(AssertionError,'exact enabled'):env['dispatch_input'](request)
        env['dispatch_input'](dict(key='E',event='pressed'))
        self.assertEqual(calls[-1],('editor_pie_press_key',dict(key='E',event='pressed')))

    def test_mouse_request_uses_the_painted_answer_label(self):
        request=Mock();label=SimpleNamespace(get_text=lambda:'Visible answer')
        hud=SimpleNamespace(get_editor_property=lambda key:label if key=='Txt_Answer1' else None)
        env=dict(s={'journey':SimpleNamespace(get_editor_property=lambda _:hud),'rows':[]},
                 unreal=SimpleNamespace(SystemLibrary=SimpleNamespace(is_valid=bool)),request_input=request)
        exec(functions('threshold_proof.py',{'request_interview_click'}),env)
        env['request_interview_click'](1)
        request.assert_called_once_with(dict(kind='click',match='Visible answer',prefer_type='SButton'))
        self.assertEqual(env['s']['rows'][0]['index'],1)

    def test_case_budgets_allow_measured_arrival_and_normal_speed_stages(self):
        env={}
        exec(functions('threshold_data.py',{'proof_budget'}),env)
        budget=env['proof_budget']
        for case,stage in [('stops',36),('drive',15),('phone',22),('paper',20),('reset',15),('ending',42),('cleanup',3),('debug',12)]:
            with self.subTest(case=case):
                self.assertGreater(budget(case),43.38+stage)
                self.assertLessEqual(budget(case),90)
        self.assertEqual(budget('cv'),116)
        self.assertEqual(budget('transition',True),57)

    def test_runner_leaves_four_seconds_after_driver_deadline(self):
        env={}
        exec(functions('threshold_data.py',{'proof_budget'}),env)
        runner=ast.parse(Path(__file__).with_name('run_threshold_proof.py').read_text())
        assignment=next(n for n in ast.walk(runner) if isinstance(n,ast.Assign)
                        and any(isinstance(t,ast.Name) and t.id=='budget' for t in n.targets))
        for case in ('stops','drive','phone','paper','reset','cleanup','ending','debug','cv'):
            env.update(case=case,realtime='0')
            exec(compile(ast.Module(body=[assignment],type_ignores=[]),'budget','exec'),env)
            self.assertEqual(env['budget']-env['proof_budget'](case),4)

    def test_stop_capture_yields_before_shot_and_holds_afterward(self):
        stage=SimpleNamespace(get_path_name=lambda:'/PIE/StopSet')
        journey=SimpleNamespace(get_editor_property=lambda key:0 if key=='Stop' else stage)
        pc=SimpleNamespace(get_view_target=lambda:stage)
        command=Mock()
        state=dict(journey=journey,shots=set(),rows=[])
        stops=SimpleNamespace(state='action_hold',after=10.5,snapshot=lambda:{'action':3})
        env=dict(s=state,OUT=Path('captures'),w=object(),time=SimpleNamespace(monotonic=lambda:10.3),
            unreal=SimpleNamespace(SystemLibrary=SimpleNamespace(is_valid=bool,execute_console_command=command)))
        exec(functions('threshold_proof.py',{'capture_stop_hold'}),env)
        self.assertTrue(env['capture_stop_hold'](stops,pc,1))
        command.assert_not_called();self.assertEqual(state['next'],1.3)
        self.assertTrue(env['capture_stop_hold'](stops,pc,1.3))
        command.assert_called_once();self.assertAlmostEqual(state['next'],1.7)
        self.assertAlmostEqual(stops.after,10.7)
        self.assertEqual(state['rows'][0]['snapshot'],{'action':3})
        self.assertFalse(env['capture_stop_hold'](stops,pc,1.7))

    def test_results_replace_complete_json_after_serialization(self):
        env=dict(json=json)
        exec(functions('threshold_proof.py',{'publish'}),env)
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'proof.json'
            path.write_text('{"old":true}')
            env['publish'](path,{'reason':'arrived','rows':[{'phase':6}]})
            self.assertEqual(json.loads(path.read_text())['reason'],'arrived')
            self.assertFalse(path.with_suffix('.pending').exists())

    def test_child_close_error_still_restores_and_publishes_result(self):
        restore=Mock();publish=Mock();world=object()
        state=dict(done=False,handle=4,walk=SimpleNamespace(close=Mock(side_effect=RuntimeError('destroyed'))),rows=[],seen=set())
        env=dict(s=state,w=world,ctx={},proof_save=SimpleNamespace(restore=restore),publish=publish,RESULT='proof',CASE='cleanup',
            UES=SimpleNamespace(get_game_world=lambda:world),
            unreal=SimpleNamespace(unregister_slate_post_tick_callback=Mock(),SystemLibrary=SimpleNamespace(is_valid=bool),
                GameplayStatics=SimpleNamespace(set_global_time_dilation=Mock())))
        exec(functions('threshold_proof.py',{'finish'}),env)
        env['finish']('cleanup_passed')
        restore.assert_called_once();self.assertEqual(publish.call_args.args[1]['reason'],'close_error')

    def test_cleanup_attempts_every_safeguard_after_input_or_end_failure(self):
        for failed in ('editor_pie_press_key','editor_stop_pie',None):
            with self.subTest(failed=failed):
                calls=[];keys=[]
                def call(command,**kwargs):
                    calls.append(command)
                    if command=='editor_pie_press_key':keys.append(kwargs['key'])
                    if command==failed:raise RuntimeError('injected')
                    return {'pie_running':False,'pie':'agent:test'}
                prefs=Mock();release=Mock();digest=Mock(return_value='unchanged')
                env=dict(call=call,owner='test',prefs=prefs,h=SimpleNamespace(release=release),digest=digest,time=Mock())
                exec(functions('run_threshold_proof.py',{'cleanup'}),env)
                if failed:
                    with self.assertRaisesRegex(RuntimeError,'injected'):
                        env['cleanup'](True,'drive',b'original','token','unchanged')
                else:env['cleanup'](True,'drive',b'original','token','unchanged')
                self.assertIn('editor_stop_pie',calls)
                self.assertEqual(keys,['W','E','S','Enter','SpaceBar','A','D'])
                prefs.write_bytes.assert_called_once_with(b'original')
                release.assert_called_once_with('test','token');digest.assert_called_once_with()

    def test_hash_still_checked_when_lease_release_fails(self):
        digest=Mock(return_value='changed')
        env=dict(call=Mock(),owner='test',prefs=Mock(),time=Mock(),digest=digest,
                 h=SimpleNamespace(release=Mock(side_effect=RuntimeError('release failed'))))
        exec(functions('run_threshold_proof.py',{'cleanup'}),env)
        with self.assertRaisesRegex(AssertionError,'Player save changed'):
            env['cleanup'](False,'transition',b'original','token','original hash')
        digest.assert_called_once_with()

    def test_cleanup_releases_stop_confirm_and_phone_keys(self):
        for case,extra in [('stops',['Enter','Up','Down']),('phone',['P']),('paper',['Enter'])]:
            keys=[]
            def call(command,**kwargs):
                if command=='editor_pie_press_key':keys.append(kwargs['key'])
                return {'pie_running':False,'pie':'agent:test'}
            env=dict(call=call,owner='test',prefs=Mock(),time=Mock(),digest=lambda:'same',h=SimpleNamespace(release=Mock()))
            exec(functions('run_threshold_proof.py',{'cleanup'}),env)
            env['cleanup'](True,case,b'original','token','same')
            self.assertEqual(keys,['W','E']+extra)

    def test_audio_records_actual_components_and_placed_track_map(self):
        sound=SimpleNamespace(get_path_name=lambda:'/Game/Audio/Dream')
        component=SimpleNamespace(get_editor_property=lambda _:sound,is_playing=lambda:True)
        props={'MusicState':'Dream','Tracks':{'Dream':sound,'City':sound},'Music':component,'Music2':component}
        room=SimpleNamespace(get_editor_property=lambda name:props[name])
        env=dict(actor=lambda _:room,unreal=SimpleNamespace(SystemLibrary=SimpleNamespace(is_valid=bool)))
        exec(functions('threshold_proof.py',{'audio_snapshot'}),env)
        sample=env['audio_snapshot']()
        self.assertEqual(sample['tracks']['Dream'],'/Game/Audio/Dream')
        self.assertEqual(sample['Music'],{'sound':'/Game/Audio/Dream','playing':True})
        self.assertEqual(sample['Music2'],sample['Music'])

    def test_stops_capture_waits_at_confirmed_sixty_percent(self):
        source=Path(__file__).with_name('threshold_proof.py').read_text(encoding='utf-8')
        tree=ast.parse(source)
        tick=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='tick')
        phase9=next(n for n in ast.walk(tick) if isinstance(n,ast.If) and ast.unparse(n.test)=="s['phase'] == 9")
        branch=ast.unparse(phase9)
        self.assertIn("get_editor_property('Phase') == 11",branch)
        self.assertIn("get_editor_property('Employability') == 60",branch)
        self.assertIn("OUT / 'stops60.png'",branch)
        self.assertIn("s.update(phase=9, next=elapsed + 0.8)",ast.unparse(tick))
        self.assertIn("journey.get_editor_property('Phase') == 4 and (not journey.get_editor_property('StopBusy'))",ast.unparse(tick))


if __name__=='__main__':unittest.main()
