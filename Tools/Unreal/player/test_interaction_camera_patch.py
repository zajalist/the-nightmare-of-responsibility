"""Offline patch contracts: keep existing camera work and never commandeer authored views."""
import unittest
from unittest.mock import patch
import patch_interaction_camera as camera
import first_person_graphs as builder


def graph():
    return ([dict(node_id='entry',title=camera.F),dict(node_id='snapshot',title='Set FPViewRotation'),
             dict(node_id='lean',title='Existing turn lean'),dict(node_id='control',title='SetControlRotation'),
             dict(node_id='head',title='UpdateHeadHidden')],
            [dict(from_node='snapshot',from_pin='then',to_node='lean',to_pin='execute'),
             dict(from_node='snapshot',from_pin='Output_Get',to_node='control',to_pin='NewRotation')])


class InteractionCameraPatchTest(unittest.TestCase):
    def test_live_contact_without_actor_target_is_guarded_and_bounds_safe(self):
        saved=dict(nodes=[dict(node_id=i,title=t) for i,t in (
            ('target','Get InteractLook'),('valid','IsValid'),('bounds','Get Actor Bounds'),
            ('mesh','Get EnvironmentContactMesh'),('live','IsValid'),('held','AND Boolean'))],
            edges=[dict(from_node=a,from_pin=ap,to_node=b,to_pin=bp) for a,ap,b,bp in (
                ('target','InteractLook','valid','Object'),('target','InteractLook','bounds','self'),
                ('mesh','EnvironmentContactMesh','live','Object'),('valid','ReturnValue','held','B'))])
        ops=camera.contact_guard_plan(saved['nodes'],saved['edges']).ops
        links={(o['from_node'],o['from_pin'],o['to_node'],o['to_pin']) for o in ops if o['op']=='connect'}
        self.assertIn(('camera_self','self','safeactor','Option 0'),links)
        self.assertTrue(any(a=='safeactor' and p=='ReturnValue' and q=='self' for a,p,b,q in links))
        self.assertTrue(any(a=='hascontact' for a,p,b,q in links))
        self.assertTrue(any(o['op']=='set_pin' and o['pin_name']=='bOnlyCollidingComponents' and o['value']=='true' for o in ops))
        saved['nodes'].append(dict(node_id='safe',title='Select'))
        saved['edges'].append(dict(from_node='target',from_pin='InteractLook',to_node='safe',to_pin='Option 1'))
        self.assertFalse(camera.contact_guard_plan(saved['nodes'],saved['edges']).ops)

    def test_existing_camera_extensions_and_successor_survive(self):
        ops=camera.camera_plan(*graph()).ops
        self.assertFalse(any(o['op']=='remove' for o in ops))
        connects={(o['from_node'],o['from_pin'],o['to_node'],o['to_pin']) for o in ops if o['op']=='connect'}
        self.assertIn(('look','then','lean','execute'),connects)
        self.assertIn(('guard','else','lean','execute'),connects)
        self.assertIn(('viewnow','FPViewRotation','control','NewRotation'),connects)
        self.assertIn(('current','ReturnValue','ease','Current'),connects)

    def test_existing_hook_is_left_for_diagnosis(self):
        nodes,edges=graph();nodes.append(dict(node_id='legacy',title='Get InteractLook'))
        self.assertEqual(camera.camera_plan(nodes,edges).ops,[])

    def test_legacy_easing_does_not_reapply_torso_clamp_each_tick(self):
        nodes=[dict(node_id=i,title=t) for i,t in (('snapshot','Set FPViewRotation'),('look','FindLookAtRotation'),
               ('ease','RInterpTo'),('control','GetControlRotation'))]
        edges=[dict(from_node='snapshot',from_pin='Output_Get',to_node='ease',to_pin='Current'),
               dict(from_node='look',from_pin='ReturnValue',to_node='ease',to_pin='Target')]
        ops=camera.legacy_feedback_plan(nodes,edges).ops
        self.assertEqual(len(ops),2)
        self.assertEqual(ops[1],dict(op='connect',from_node='control',from_pin='ReturnValue',to_node='ease',to_pin='Current'))
        edges[0].update(from_node='control',from_pin='ReturnValue')
        self.assertEqual(camera.legacy_feedback_plan(nodes,edges).ops,[])

    def test_guard_requires_valid_target_owned_view_and_no_authored_camera(self):
        ops=camera.camera_plan(*graph()).ops
        connects={(o['from_node'],o['from_pin'],o['to_node'],o['to_pin']) for o in ops if o['op']=='connect'}
        for edge in (('valid','ReturnValue','held','B'),('locked','bInteractionLocked','held','A'),
                     ('cine','bCinematic','authored','A'),('battle','bBattleActive','authored','B'),
                     ('authored','ReturnValue','available','A'),('direct','ReturnValue','owns','B'),
                     ('available','ReturnValue','owns','A'),('held','ReturnValue','allowed','A'),
                     ('owns','ReturnValue','allowed','B'),('allowed','ReturnValue','guard','Condition'),
                     ('guard','then','look','execute')):
            self.assertIn(edge,connects)

    def test_base_builder_preserves_populated_graph_before_any_mutation(self):
        nodes,_=graph()
        with patch.object(builder.h,'call',side_effect=[dict(data={'pie_running':False}),dict(ok=True,data={'nodes':nodes})]) as call,\
             patch.object(builder.h,'lease_acquire') as acquire:
            builder.run()
        acquire.assert_not_called()
        self.assertEqual([c.args[0] for c in call.call_args_list],['editor_get_state','blueprint_inspect_graph'])


if __name__=='__main__':unittest.main()
