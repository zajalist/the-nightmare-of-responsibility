"""Offline proof-driver isolation and bounded input checks. No runtime claim."""
from types import SimpleNamespace as NS
import unittest
from interview_proof import InterviewProof


class Obj:
    valid=True
    def __init__(self,**values):self.values=values
    def get_editor_property(self,name):return self.values[name]


def fixture(slot='FoA_QA_Play'):
    world=Obj();current=[world];clock=[0.];requests=[]
    gi=Obj(SaveSlot=slot,DayCount=18,Notebook=['Existing note'],Knowledge=[])
    player=Obj();player.get_components_by_class=lambda _c:[]
    journey=Obj(Phase=11,Employability=60,Edited0=True,Edited1=True,Edited2=True,
        Player=player,Encounter=None,DialogueMode=0,DialogueState=0,DialogueStep=0,DialoguePrior=0,
        DialogueSelected=0,InterviewComposure=100,DialogueReady=False,StopBusy=False)
    journey.get_world=lambda:world
    engine=NS(SystemLibrary=NS(is_valid=lambda o:o.valid),UnrealEditorSubsystem=object,MeshComponent=object,
        get_editor_subsystem=lambda _:NS(get_game_world=lambda:current[0]),
        GameplayStatics=NS(get_game_instance=lambda _:gi))
    driver=InterviewProof(world,journey,requests.append,engine=engine,now=lambda:clock[0])
    return NS(driver=driver,requests=requests,clock=clock,current=current,gi=gi,journey=journey)


class ProofTests(unittest.TestCase):
    def test_clothing_receipt_distinguishes_ending_visibility(self):
        f=fixture();f.driver.clothing_checks=2
        f.driver.clothes=lambda:{'Suit':False};f.driver.pose_result=lambda:{}
        f.journey.values.update(Phase=9,Submitted=True,Employability=100)
        f.driver.tick()
        self.assertTrue(f.driver.result['passed'])
        self.assertTrue(f.driver.result['clothing_unchanged'])
        self.assertFalse(f.driver.result['post_submit_clothing_unchanged'])
        f=fixture();f.driver.clothes=lambda:{'Suit':False};f.driver.tick()
        self.assertIn('Interview changed clothing visibility',f.driver.result['reason'])

    def test_pose_requires_owned_idle_relaxed_arms_and_face_leader(self):
        import interview_data
        f=fixture();positions={'hand_r':(10,0,70),'hand_l':(-10,0,70),
            'upperarm_r':(12,0,130),'upperarm_l':(-12,0,130),'head':(0,0,160)}
        def transform(name,_space):
            xyz=positions[name]
            return NS(translation=NS(z=xyz[2],to_tuple=lambda:xyz))
        clip=Obj();clip.get_path_name=lambda:interview_data.IDLE+'.'+interview_data.IDLE.rsplit('/',1)[1]
        instance=Obj();instance.get_animation_asset=lambda:clip
        body=Obj(leader_pose_component=None,visibility_based_anim_tick_option='ALWAYS_TICK_POSE_AND_REFRESH_BONES')
        body.get_animation_mode=lambda:'ANIMATION_SINGLE_NODE';body.get_anim_instance=lambda:instance
        body.get_bone_index=lambda _:1;body.get_socket_transform=transform
        face=Obj(leader_pose_component=body);face.get_bone_index=lambda _:1;face.get_socket_transform=transform
        mesh=NS(get_path_name=lambda:interview_data.SUIT)
        material=NS(get_path_name=lambda:interview_data.SUIT_MATERIAL)
        suit=Obj(leader_pose_component=body,skeletal_mesh_asset=mesh)
        suit.is_visible=lambda:True;suit.get_material=lambda _:material
        suit.get_bone_index=lambda _:1;suit.get_socket_transform=transform
        f.driver.u.RelativeTransformSpace=NS(RTS_COMPONENT=0)
        stage=Obj(InterviewBody=body,InterviewFace=face,InterviewSuit=suit)
        f.driver.sample_pose(stage)
        positions['hand_r']=(10,0,140)
        with self.assertRaisesRegex(AssertionError,'arm is raised'):f.driver.sample_pose(stage)
        positions['hand_r']=(10,0,70);face.values['leader_pose_component']=Obj()
        with self.assertRaisesRegex(AssertionError,'Face must follow'):f.driver.sample_pose(stage)

    def test_colour_reads_the_live_world_material_parameter(self):
        f=fixture();collection=Obj();calls=[];value=[1.]
        f.driver.u.load_asset=lambda path:collection
        def read(world,asset,parameter):
            calls.append((world,asset,parameter));return value[0]
        f.driver.u.MaterialLibrary=NS(get_scalar_parameter_value=read)
        f.driver.verify_colour()
        self.assertEqual(calls,[(f.driver.world,collection,'ColorReveal')])
        self.assertEqual(f.driver.result['color_reveal'],1.)
        value[0]=.5
        with self.assertRaisesRegex(AssertionError,'not in full color'):f.driver.verify_colour()

    def test_voice_observation_uses_the_real_frontend_owner(self):
        f=fixture();phrase=Obj();phrase.get_path_name=lambda:'/Game/FoA/Audio/Dialogue/Interview'
        front=Obj(VoiceSpeaker=4,VoiceLine='Question',VoicePhrase=phrase,VoiceAudio=None)
        f.driver.u.load_class=lambda *a:object
        f.driver.u.GameplayStatics.get_actor_of_class=lambda *a:front
        f.driver.observe_voice('Question')
        self.assertEqual(f.driver.result['voice']['speaker'],4)
        front.values['VoiceSpeaker']=1
        with self.assertRaisesRegex(AssertionError,'another character'):f.driver.observe_voice('Question')

    def test_only_qa_save_can_receive_input(self):
        with self.assertRaisesRegex(AssertionError,'Isolate QA'):fixture('FoA')
        f=fixture();f.driver.tick()
        self.assertEqual(f.requests,[dict(key='Enter',event='pressed_and_released',held_ms=90)])
        f.clock[0]=5;f.driver.tick()
        self.assertIn('did not advance',f.driver.result['reason'])

    def test_replaced_world_or_expired_budget_stops_without_input(self):
        f=fixture();f.current[0]=Obj();f.driver.tick()
        self.assertEqual(f.driver.result['reason'],'world_or_actor_gone');self.assertEqual(f.requests,[])
        f=fixture();f.clock[0]=86;f.driver.tick()
        self.assertEqual(f.driver.result['reason'],'timeout');self.assertEqual(f.requests,[])

    def test_changed_day_is_a_failure_not_silently_accepted(self):
        f=fixture();f.gi.values['DayCount']+=1;f.driver.tick()
        self.assertIn('changed L1 day',f.driver.result['reason']);self.assertEqual(f.requests,[])


if __name__=='__main__':unittest.main()
