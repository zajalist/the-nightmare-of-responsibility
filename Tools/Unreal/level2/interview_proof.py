"""Parent-owned QA PIE driver for real conversation input. No editor effects.

create_interview_proof(world, journey, request_input, cap_seconds=85)
tick(dt), done/result/state, close(). Starts after three stop revisions at60.
The optional request_click(index) callback may provide a real pointer click on
the painted answer row. Without it, mouse coverage is explicitly unverified.
Travel is the parent's Arrive(index) fixture, never claimed as driving proof.
"""
import time
import interview_data as data


class InterviewProof:
    def __init__(self,world,journey,request_input=None,request_click=None,cap_seconds=85,
                 failure_runs=2,engine=None,now=None):
        if engine is None:
            import unreal as engine
        self.u,self.world,self.journey=engine,world,journey
        self.request_input,self.request_click=request_input,request_click
        self.now=now or time.monotonic;self.started=self.now();self.cap=min(100,max(5,cap_seconds))
        self.failure_runs=max(0,min(2,failure_runs));self.attempt=0
        self.done,self.state=False,'start';self.pending=None;self.after=0;self.expected=None
        self.hold_tested=False;self.clicked=False;self.seen=set()
        self.capture_tag=None
        self.pose_samples=[]
        self.result=dict(passed=False,trace=[],actual_input=request_input is not None,
            mouse_input=False,keyboard_input=False,gamepad_input=False,
            scope='Actual answers and local retries; no forced composure, progress or outcome. Parent supplies completed-stop setup.')
        assert self.alive(),'Parent-owned QA PIE required'
        self.gi=engine.GameplayStatics.get_game_instance(world)
        assert str(self.get(self.gi,'SaveSlot'))=='FoA_QA_Play','Isolate QA save first'
        self.player=self.get(journey,'Player');self.encounter=self.get(journey,'Encounter')
        assert self.get(journey,'Phase')==11 and self.get(journey,'Employability')==60
        assert all(self.get(journey,'Edited'+str(i)) for i in range(3))
        self.baseline=self.persistent();self.clothing=self.clothes();self.clothing_checks=0

    @staticmethod
    def get(obj,key):return obj.get_editor_property(key)
    def valid(self,obj):return obj is not None and self.u.SystemLibrary.is_valid(obj)
    def alive(self):
        return (self.valid(self.world) and self.valid(self.journey) and self.journey.get_world()==self.world
                and self.u.get_editor_subsystem(self.u.UnrealEditorSubsystem).get_game_world()==self.world)
    def persistent(self):
        return dict(day=int(self.get(self.gi,'DayCount')),notes=list(map(str,self.get(self.gi,'Notebook'))),
                    knowledge=sorted(map(str,self.get(self.gi,'Knowledge'))))
    def clothes(self):
        return {c.get_name():bool(c.is_visible()) for c in self.player.get_components_by_class(self.u.MeshComponent) if self.valid(c)}
    def snapshot(self):
        names={'phase':'Phase','mode':'DialogueMode','response':'DialogueState','step':'DialogueStep',
               'prior':'DialoguePrior','selected':'DialogueSelected','composure':'InterviewComposure','score':'Employability'}
        result={key:int(self.get(self.journey,value)) for key,value in names.items()}
        result.update(ready=bool(self.get(self.journey,'DialogueReady')),busy=bool(self.get(self.journey,'StopBusy')))
        return result

    def observe_voice(self,question):
        front=self.u.GameplayStatics.get_actor_of_class(self.world,self.u.load_class(None,
            '/Game/FoA/UI/Framework/BP_FoAFrontEnd.BP_FoAFrontEnd_C'))
        assert self.valid(front),'Dialogue voice owner is missing'
        assert self.get(front,'VoiceSpeaker')==4,'Interview used another character voice'
        assert str(self.get(front,'VoiceLine'))==question,'Visible question did not reach the voice hook'
        phrase=self.get(front,'VoicePhrase');assert self.valid(phrase),'Question did not select a voice phrase'
        audio=self.get(front,'VoiceAudio')
        self.result['voice']=dict(speaker=4,line=question,clip=phrase.get_path_name(),
            component_valid=self.valid(audio),playing=bool(audio.is_playing()) if self.valid(audio) else False)
        self.mark('interview_voice_verified',**self.result['voice'])

    def verify_colour(self):
        collection=self.u.load_asset('/Game/FoA/PostProcess/MPC_Dream.MPC_Dream')
        assert self.valid(collection),'Dream material parameter collection is missing'
        amount=self.u.MaterialLibrary.get_scalar_parameter_value(self.world,collection,'ColorReveal')
        assert amount>=.99,('Interview is not in full color',amount)
        self.result['color_reveal']=float(amount)

    def sample_pose(self,stage):
        row={}
        body=self.get(stage,'InterviewBody');face=self.get(stage,'InterviewFace')
        assert self.get(body,'leader_pose_component') is None,'Interviewer still copies another character'
        assert 'ANIMATION_SINGLE_NODE' in str(body.get_animation_mode()),'Interviewer needs its owned idle'
        instance=body.get_anim_instance();assert self.valid(instance),'Missing idle AnimInstance'
        clip=instance.get_animation_asset();assert self.valid(clip)
        assert clip.get_path_name().split('.')[0]==data.IDLE,('Wrong interviewer idle',clip.get_path_name())
        assert 'ALWAYS_TICK_POSE_AND_REFRESH_BONES' in str(self.get(body,'visibility_based_anim_tick_option')),'Offscreen idle can freeze'
        assert self.get(face,'leader_pose_component')==body,'Face must follow the interviewer body'
        suit=self.get(stage,'InterviewSuit')
        assert self.valid(suit) and suit.is_visible(),'Interviewer suit is hidden'
        assert self.get(suit,'leader_pose_component')==body,'Suit must follow the interviewer body'
        assert self.get(suit,'skeletal_mesh_asset').get_path_name().split('.')[0]==data.SUIT,'Wrong interviewer suit'
        assert suit.get_material(0).get_path_name().split('.')[0]==data.SUIT_MATERIAL,'Wrong interviewer suit material'
        space=self.u.RelativeTransformSpace.RTS_COMPONENT
        for component,name,bone in ((body,'InterviewBody','hand_r'),(face,'InterviewFace','head'),(suit,'InterviewSuit','hand_r')):
            assert component.get_bone_index(bone)>=0,('Missing idle bone',bone)
            row[name]=component.get_socket_transform(bone,space).translation.to_tuple()
        head=body.get_socket_transform('head',space).translation.to_tuple()
        assert sum((a-b)**2 for a,b in zip(head,row['InterviewFace']))<1,'Face diverged from interviewer idle'
        assert sum((a-b)**2 for a,b in zip(row['InterviewBody'],row['InterviewSuit']))<1,'Suit diverged from interviewer idle'
        for side in ('r','l'):
            shoulder=body.get_socket_transform('upperarm_'+side,space).translation.z
            hand=body.get_socket_transform('hand_'+side,space).translation.z
            assert shoulder-hand>20,('Interviewer arm is raised',side,shoulder,hand)
        self.pose_samples.append(row)

    def pose_result(self):
        assert len(self.pose_samples)>=3,'Insufficient idle pose samples'
        first=self.pose_samples[0]
        motion={name:max(sum((x-y)**2 for x,y in zip(row[name],first[name]))**.5 for row in self.pose_samples)
                for name in first}
        assert all(value>.01 for value in motion.values()), ('Static interview pose',motion)
        return dict(samples=len(self.pose_samples),component_space_motion_cm=motion,
                    independent_idle=data.IDLE,face_follows_interviewer=True,arms_relaxed=True,suit=data.SUIT)
    def signature(self,s):return tuple(s[k] for k in ('phase','mode','response','step','selected','composure'))
    def mark(self,event,**fields):self.result['trace'].append(dict(t=round(self.now()-self.started,3),event=event,**fields))
    def finish(self,reason,passed=False):
        self.done,self.state=True,'done';self.result.update(passed=passed,reason=reason,elapsed=round(self.now()-self.started,3))
    def close(self):pass # No held keys, timers, time dilation or engine writes to restore.

    def press(self,key,s,held=90):
        if self.request_input:
            self.request_input(dict(key=key,event='pressed_and_released',held_ms=held))
            self.result['gamepad_input' if key.startswith('Gamepad') else 'keyboard_input']=True
        elif key in ('Down','Gamepad_DPad_Down'):self.journey.call_method('DialogueMove',(1,))
        elif key in ('Up','Gamepad_DPad_Up'):self.journey.call_method('DialogueMove',(-1,))
        else:
            self.journey.call_method('Confirm',())
            self.journey.call_method('DialogueRelease',())
        self.pending=(self.signature(s),self.now());self.after=self.now()+held/1000+.35
        self.mark('key' if self.request_input else 'native_api',key=key,held_ms=held,snapshot=s)

    def choose(self,index,s):
        controller=self.attempt>=self.failure_runs
        if s['selected']!=index:
            direction='Down' if s['selected']<index else 'Up'
            self.press(('Gamepad_DPad_'+direction) if controller else direction,s);return False
        return True

    def hold(self,tag,state):
        if tag in self.seen:return False
        self.seen.add(tag);self.capture_tag=tag;self.state=state;self.after=self.now()+.6
        return True

    def tick(self,_dt=0):
        if self.done:return
        try:
            if not self.alive():return self.finish('world_or_actor_gone')
            assert str(self.get(self.gi,'SaveSlot'))=='FoA_QA_Play','QA isolation changed'
            if self.now()-self.started>self.cap:return self.finish('timeout')
            s=self.snapshot()
            if self.pending:
                if self.signature(s)==self.pending[0]:
                    assert self.now()-self.pending[1]<4,'Requested conversation input did not advance'
                    return
                self.pending=None
            if self.now()<self.after:return
            if s['phase']==9:
                assert self.get(self.journey,'Submitted') and s['score']==100
                assert self.get(self.gi,'DayCount')==self.baseline['day']
                assert all(note in list(map(str,self.get(self.gi,'Notebook'))) for note in self.baseline['notes'])
                assert self.get(self.journey,'DialogueMode')==0
                assert self.clothing_checks>0,'No interview clothing checks ran'
                self.result.update(submitted=True,notes_retained=True,local_failures=self.attempt,
                    clothing_unchanged=True,clothing_checks=self.clothing_checks,
                    clothing_check_scope='Interview before BeginEnding handoff',
                    post_submit_clothing_unchanged=self.clothes()==self.clothing,
                    mouse_input=self.clicked,animation=self.pose_result())
                return self.finish('passed',True)
            assert self.persistent()==self.baseline,'Conversation changed L1 day or collected notes'
            assert self.clothes()==self.clothing,'Interview changed clothing visibility'
            self.clothing_checks+=1
            if self.valid(self.encounter):assert not self.get(self.encounter,'bLevel2CV'),'Interview entered legacy clothing battle'
            if s['phase']==11:self.press('Enter',s);return
            if s['busy'] or not s['ready']:self.state='settling';return
            assert s['mode']==3 and s['phase'] in (6,7,8),s
            pc=self.u.GameplayStatics.get_player_controller(self.world,0)
            stage=self.get(self.journey,'StopSet')
            assert pc.get_view_target()==stage,'Interview camera ownership is incorrect'
            assert bool(self.get(stage,'InterviewBackdrop').is_visible()),'Generated colored atrium is hidden'
            self.sample_pose(stage)
            hud=self.get(self.journey,'InterviewHUD')
            assert self.valid(hud) and hud.is_in_viewport() and hud.is_visible(),'Conversation widget is not visible'
            self.verify_colour()
            assert not self.journey.call_method('CanOpenPhone',()),'Phone can interrupt a conversation'
            if self.expected:
                e=self.expected
                assert s['response']==1 and s['step']==e['step'] and s['composure']==e['composure'],(s,e)
                assert str(self.get(self.journey,'DialoguePlayerLine'))==e['player']
                assert str(self.get(self.journey,'DialogueReply'))==e['reply']
                self.mark('answer_verified',player=e['player'],reply=e['reply'],snapshot=s)
                self.expected=None
            if s['response']==1:
                if s['step']==1 and self.hold('reply_'+str(self.attempt),'response_hold'):return
                self.state='response_hold'
                self.press('Gamepad_FaceButton_Bottom' if self.attempt>=self.failure_runs else 'Enter',s);return
            if s['response']==2:
                assert s['score']==60 and s['composure']==0,'Local failure must keep all three revisions at60'
                assert self.attempt<self.failure_runs,'Evidence policy unexpectedly failed'
                if self.hold('loss_'+str(self.attempt),'loss_hold'):return
                retry=0 if self.attempt==0 else 1
                if not self.choose(retry,s):return
                self.mark('local_retry',assisted=bool(retry),snapshot=s)
                self.attempt+=1;self.state='retry';self.press('Enter',s);return
            if s['response']==3:
                assert s['step']==6 and s['score']==100 and self.get(self.journey,'FinaleComplete')
                if self.hold('win','win_hold'):return
                self.state='win_hold';self.mark('six_turn_success',snapshot=s)
                self.press('Gamepad_FaceButton_Bottom',s);return
            assert s['response']==0 and 0<=s['step']<6
            if s['step']==0:
                assert s['composure']==100 and s['score']==60
                assert bool(self.get(self.journey,'DialogueNotes'))==(self.attempt>=2),'Normal versus notes-open retry is wrong'
            row=data.question(s['step'],s['prior'])
            assert str(self.get(hud,'Txt_Question').get_text())==row['question'],'Visible follow-up does not match the previous answer'
            if 'voice' not in self.result:self.observe_voice(row['question'])
            if self.hold('question_'+str(self.attempt)+'_'+str(s['step']),'question_hold'):return
            policy=max if self.attempt<self.failure_runs else min
            index=policy(range(3),key=lambda n:row['choices'][n]['cost'])
            self.state='question_hold'
            if not self.choose(index,s):return
            self.expected=data.resolve(s['step'],s['prior'],index,s['composure'])
            self.mark('question',question=row['question'],choice=index,snapshot=s)
            if self.request_click and not self.clicked and self.attempt>=self.failure_runs:
                self.request_click(index);self.clicked=True
                self.pending=(self.signature(s),self.now());self.after=self.now()+.6;return
            held=900 if not self.hold_tested else 90
            self.hold_tested=True
            self.press('Gamepad_FaceButton_Bottom' if self.attempt>=self.failure_runs else 'Enter',s,held)
        except Exception as exc:
            self.mark('error',message=str(exc),state=self.state);self.finish('error: '+str(exc))


def create_interview_proof(world,journey,request_input=None,request_click=None,cap_seconds=85,failure_runs=2):
    import importlib
    importlib.reload(data)
    return InterviewProof(world,journey,request_input,request_click,cap_seconds,failure_runs)
