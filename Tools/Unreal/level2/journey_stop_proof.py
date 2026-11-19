"""Bounded async job-stop fixture for the parent's existing QA tick.

create_stop_proof(world, journey, request_input=None, through_stop=2,
                  finish_in_car=False, cap_seconds=22)
tick(dt), done/result/state/close(). Parent owns PIE, save context and teardown.
With request_input(dict), every action/confirmation uses actual E/Enter keys.
Without it, UseStop/Confirm are native API setup for CV/ending/reset fixtures.
Travel uses Journey.Arrive(index) as an explicit setup fixture, not driving proof.
State action_hold/revision_hold gives the parent a stable screenshot opportunity.
"""
import time

FLAGS=('Knows.L2Experience','Knows.L2Logistics','Knows.L2Reliability')


class StopProof:
    def __init__(self,world,journey,request_input=None,through_stop=2,finish_in_car=False,
                 cap_seconds=22,engine=None,now=None):
        if engine is None:
            import unreal as engine
        self.u,self.world,self.journey=engine,world,journey
        self.request_input=request_input;self.now=now or time.monotonic
        self.started=self.now();self.cap=min(60.,max(3.,cap_seconds))
        assert through_stop in (0,1,2)
        self.through_stop,self.finish_in_car=through_stop,finish_in_car
        self.done,self.state=False,'start';self.pending=None;self.probe=None;self.after=0
        self.gated=set();self.actions=set();self.revisions=set()
        self.result=dict(passed=False,trace=[],real_stop_keys=request_input is not None,
            scope='Journey.Arrive(index) travel fixture; '+('actual keyboard contact/task inputs' if request_input else 'native contact/task APIs'))
        assert self.alive(),'Current QA PIE required'
        self.gi=engine.GameplayStatics.get_game_instance(world)
        assert self.valid(self.gi) and str(self.get(self.gi,'SaveSlot'))=='FoA_QA_Play','Isolate QA save first'
        self.day=self.get(self.gi,'DayCount');self.notes=list(map(str,self.get(self.gi,'Notebook')))
        self.car=self.get(journey,'Car');assert self.valid(self.car)
        assert self.get(journey,'Phase') in (1,2,3),'Start before the first stop'

    @staticmethod
    def get(obj,key):return obj.get_editor_property(key)
    def valid(self,obj):return obj is not None and self.u.SystemLibrary.is_valid(obj)
    def alive(self):
        return (self.valid(self.world) and self.valid(self.journey)
            and self.u.get_editor_subsystem(self.u.UnrealEditorSubsystem).get_game_world()==self.world
            and self.journey.get_world()==self.world)
    def snapshot(self):
        j=self.journey
        return dict(phase=int(self.get(j,'Phase')),stop=int(self.get(j,'Stop')),busy=bool(self.get(j,'StopBusy')),
            action=int(self.get(j,'StopActionState')),action_done=bool(self.get(j,'StopActionDone')),
            score=int(self.get(j,'Employability')),edits=[bool(self.get(j,'Edited'+str(i))) for i in range(3)],
            car_active=bool(self.get(self.car,'Active')),leg=int(self.get(self.car,'Leg')),
            dialogue=int(self.get(j,'DialogueMode')),response=int(self.get(j,'DialogueState')),
            selected=int(self.get(j,'DialogueSelected')),ready=bool(self.get(j,'DialogueReady')))
    def signature(self,s):return tuple(s[k] for k in ('phase','stop','busy','action','action_done','score','car_active','dialogue','response','selected'))
    def mark(self,event,**fields):self.result['trace'].append(dict(t=round(self.now()-self.started,3),event=event,**fields))
    def invoke(self,action,s,expect_change=True):
        if self.request_input:
            self.request_input(dict(key='E' if action=='UseStop' else 'Enter',event='pressed_and_released',held_ms=90))
        else:
            self.journey.call_method(action,())
            self.journey.call_method('DialogueRelease',())
        self.mark('input' if self.request_input else 'api',action=action,snapshot=s)
        if self.request_input:self.after=self.now()+.44
        if expect_change:self.pending=(self.signature(s),self.now())
    def finish(self,reason,passed=False):
        self.done=True;self.state='done';self.result.update(passed=passed,reason=reason,elapsed=round(self.now()-self.started,3))
    def close(self):
        # No held key, modified time dilation, callbacks or engine objects to restore.
        pass

    def tick(self,_dt=0):
        if self.done:return
        try:
            if not self.alive() or not self.valid(self.gi) or not self.valid(self.car):return self.finish('world_or_actor_gone')
            assert str(self.get(self.gi,'SaveSlot'))=='FoA_QA_Play','QA save isolation changed'
            assert self.get(self.gi,'DayCount')==self.day,'Stop changed Level 1 day'
            assert all(n in list(map(str,self.get(self.gi,'Notebook'))) for n in self.notes),'Existing note lost'
            if self.now()-self.started>self.cap:return self.finish('timeout')
            s=self.snapshot()
            if self.pending:
                if self.signature(s)==self.pending[0]:
                    assert self.now()-self.pending[1]<3,'Requested stop input did not advance'
                    return
                self.mark('input_observed',snapshot=s)
                self.pending=None
            if self.probe:
                assert self.signature(s)==self.probe[0],'Confirm bypassed mandatory stop action'
                if self.now()<self.probe[1]:return
                self.probe=None
            if self.now()<self.after:return
            if s['busy']:self.state='waiting';return
            if s['phase']==2 and self.request_input:
                paper=self.get(self.journey,'CVPaper')
                if self.valid(paper):
                    self.state='paper_close'
                    if not hasattr(self,'paper_close_at'):
                        assert self.get(paper,'bOpen'),'Expected an open paper after actual Enter'
                        self.request_input(dict(key='E',event='pressed_and_released',held_ms=90))
                        self.paper_close_at=self.now();self.after=self.now()+.44
                        self.mark('actual_paper_close_requested')
                    else:assert self.now()-self.paper_close_at<3,'Actual E did not close paper'
                    return
            if s['phase'] in (1,2):self.state='street';self.invoke('Confirm',s);return
            if s['phase']==3 and s['car_active']:
                if self.finish_in_car and sum(s['edits'])==self.through_stop+1:
                    self.mark('ready_for_road_reset',snapshot=s);return self.finish('passed',True)
                self.state='travel_fixture'
                self.journey.call_method('Arrive',(s['stop'],))
                self.mark('arrival_setup_fixture',stop=s['stop']);return
            if s['phase']==4:
                stage=self.get(self.journey,'StopSet');assert self.valid(stage),'Missing physical stop set'
                assert not s['car_active'] and not self.get(self.get(self.car,'Meteor'),'Active'),'Driving hazard active inside stop'
                if s['action_done'] and s['stop'] not in self.actions:
                    if s['stop']==0:assert self.get(stage,'TicketTaken'),'Ticket never reached hand'
                    if s['stop']==1:
                        for i in range(3):
                            rotation=self.get(self.get(stage,'Label'+str(i)),'relative_rotation')
                            assert abs(rotation.roll)<.1,'Shelf label is still crooked'
                    if s['stop']==2:assert self.get(stage,'Seated'),'Office seat never used'
                    self.actions.add(s['stop']);self.mark('action_completed',snapshot=s)
                    self.state='action_hold';self.after=self.now()+.5;return
                if s['dialogue'] in (1,2):
                    assert s['dialogue']==1 or s['action_done'],'Debrief bypassed task'
                    if not s['ready']:self.state='contact_settle';return
                    if s['response']==0 and s['selected']!=s['stop']:
                        self.mark('contact_select',snapshot=s)
                        if self.request_input:
                            self.request_input(dict(key='Down' if s['selected']<s['stop'] else 'Up',event='pressed_and_released',held_ms=90))
                            self.after=self.now()+.44
                        else:self.journey.call_method('DialogueSelect',(s['stop'],))
                        self.pending=(self.signature(s),self.now());self.state='contact_choose';return
                    self.state='contact_reply' if s['response']==1 else 'contact_answer'
                    self.mark('contact_exchange',mode=s['dialogue'],response=s['response'],choice=s['selected'])
                    self.invoke('Confirm',s);return
                if s['action']==1:
                    if s['stop'] not in self.gated:
                        self.gated.add(s['stop']);self.invoke('Confirm',s,False)
                        self.probe=(self.signature(s),self.now()+.4);self.state='checking_action_gate';return
                    self.state='using_stop';self.invoke('UseStop',s);return
                assert s['action_done'],'Dialogue reached without physical action'
                if s['action']==10:
                    merge=self.get(self.journey,'Merge');assert self.valid(merge)
                    assert abs(float(self.get(merge,'MergeAmount'))-s['score']/100)<.001,'Rejection preview leaked into committed merge'
                self.state='dialogue';self.invoke('Confirm',s);return
            if s['phase']==5:
                assert s['action_done'] and s['action']==10,'Revision bypassed stop action/rejection'
                self.state='revision';self.invoke('Confirm',s);return
            if s['phase']==11:
                count=sum(s['edits']);assert s['score']==20*count and s['edits']==[i<count for i in range(3)],s
                known=set(map(str,self.get(self.gi,'Knowledge')));assert set(FLAGS[:count])<=known,'Stop notes not learned'
                if count not in self.revisions:
                    before=self.snapshot();self.journey.call_method('ConfirmEdit',());assert self.snapshot()==before,'Repeated revision awarded twice'
                    self.revisions.add(count);self.mark('revision_committed',snapshot=s)
                    self.state='revision_hold';self.after=self.now()+.5;return
                if count==self.through_stop+1 and not self.finish_in_car:return self.finish('passed',True)
                self.state='returning_to_car';self.invoke('Confirm',s);return
            raise AssertionError(('Unexpected stop fixture state',s))
        except Exception as exc:
            self.mark('error',message=str(exc),state=self.state,snapshot=self.snapshot() if self.alive() else None);self.finish('error: '+str(exc))


def create_stop_proof(world,journey,request_input=None,through_stop=2,finish_in_car=False,cap_seconds=22):
    return StopProof(world,journey,request_input,through_stop,finish_in_car,cap_seconds)
