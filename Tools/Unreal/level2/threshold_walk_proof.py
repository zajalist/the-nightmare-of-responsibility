"""Parent-ticked actual W/E route proof. No PIE/timer/lease/save lifecycle.

Start in Phase3, FoA_QA_Play, global time dilation1. request_input accepts the
editor_pie_press_key argument dictionary. One outstanding request at a time;
native PlayerController key state acknowledges delivery. Parent must release
W and E in its outer cleanup even when the world disappears or this fails.
"""
import time


class WalkProof:
    def __init__(self, world, threshold, request_input, cap_seconds=35, engine=None, now=None):
        if engine is None:
            import unreal as engine
        self.u,self.world,self.th=engine,world,threshold
        self.request_input,self.now=request_input,now or time.monotonic
        self.started=self.now();self.cap=min(45.,max(10.,cap_seconds))
        self.state='start';self.done=False;self.pending=None;self.held=set();self.after=0
        self.result=dict(passed=False,trace=[],scope='Actual W/E input; no gameplay calls or phase writes')
        self.gi=engine.GameplayStatics.get_game_instance(world)
        self.pc=engine.GameplayStatics.get_player_controller(world,0)
        self.keys={}
        for name in ('W','E'):
            key=engine.Key();key.set_editor_property('key_name',name);self.keys[name]=key
        self.day=self.get(self.gi,'DayCount')
        assert self.alive() and self.get(self.th,'Phase')==3,'Current Phase3 QA world required'
        assert str(self.get(self.gi,'SaveSlot'))=='FoA_QA_Play','Normal isolated QA slot required; debug bypass is not input proof'
        assert self.get(self.th,'RouteBeat')==0 and self.get(self.th,'BreathState')==0,'Fresh walk required'
        assert not any(self.down(k) for k in self.keys),'Release W/E before proof'

    @staticmethod
    def get(obj,name):return obj.get_editor_property(name)

    def alive(self):
        valid=self.u.SystemLibrary.is_valid
        try:
            return (all(valid(x) for x in (self.world,self.th,self.gi,self.pc))
                and self.u.get_editor_subsystem(self.u.UnrealEditorSubsystem).get_game_world()==self.world
                and self.th.get_world()==self.world)
        except TypeError as exc:
            # GC can invalidate the Python wrapper before IsValid can receive it.
            if 'ObjectInstance is null' in str(exc):return False
            raise

    def down(self,key):return self.pc.is_input_key_down(self.keys[key])

    def mark(self,event,**fields):
        self.result['trace'].append(dict(t=round(self.now()-self.started,3),event=event,**fields))

    def send(self,key,down):
        assert self.pending is None,'Only one outstanding input request'
        self.request_input(dict(key=key,event='pressed' if down else 'released'))
        self.pending=(key,down,self.now())
        if down:self.held.add(key)
        else:self.held.discard(key)
        self.mark('input_requested',key=key,down=down)

    def close(self):
        # Only a single request fits the parent's mailbox. The outer runner always
        # releases BOTH keys on any failure; normally E is already up here.
        if self.alive():
            key=next((k for k in ('E','W') if k in self.held),None)
            if key:self.request_input(dict(key=key,event='released'))

    def finish(self,reason,passed=False):
        if self.done:return
        self.done=True;self.state='done'
        self.result.update(passed=passed,reason=reason,elapsed=round(self.now()-self.started,3))
        self.close()

    def tick(self,_dt=0):
        if self.done:return
        try:
            if not self.alive():return self.finish('world_or_actor_gone')
            assert str(self.get(self.gi,'SaveSlot'))=='FoA_QA_Play','QA isolation changed'
            assert self.get(self.gi,'DayCount')==self.day,'Dream walk changed day progress'
            if self.now()-self.started>self.cap:return self.finish('timeout')
            if self.pending:
                key,down,sent=self.pending
                if self.down(key)!=down:
                    assert self.now()-sent<4,'Input was not acknowledged: '+key
                    return
                self.mark('input_ack',key=key,down=down);self.pending=None
            phase,beat,breath=[self.get(self.th,n) for n in ('Phase','RouteBeat','BreathState')]
            age=self.get(self.th,'BreathAge');armed=self.get(self.th,'BreathArmed')
            if self.state not in ('exit','release_walk'):
                assert phase==3,'Fall began before proof earned both beats'
            if self.state=='start':self.send('E',True);self.state='start_walk'
            elif self.state=='start_walk':self.send('W',True);self.state='first_headache'
            elif self.state=='first_headache' and breath==1:
                assert beat==0 and not armed
                self.after=self.now()+.45;self.state='preheld'
            elif self.state=='preheld':
                assert beat==0 and breath==1 and age==0,'Preheld E advanced a breath'
                if self.now()>=self.after:self.send('E',False);self.state='arm_early'
            elif self.state=='arm_early' and armed:
                self.send('E',True);self.state='early_hold'
            elif self.state=='early_hold' and breath==2 and age>=.25:
                self.send('E',False);self.state='early_release'
            elif self.state=='early_release' and breath==1:
                assert age==0 and beat==0,'Early release awarded progress'
                self.mark('early_release_reset');self.send('E',True);self.state='full_hold'
            elif self.state=='full_hold' and breath==3:
                self.after=self.now()+.45;self.state='held_full'
            elif self.state=='held_full':
                assert beat==0 and breath==3,'Held E completed or repeated a beat'
                if self.now()>=self.after:
                    self.mark('full_hold_waited_for_release');self.send('E',False);self.state='first_settle'
            elif self.state=='first_settle' and beat==1:
                assert breath==0;self.mark('beat_completed',beat=1);self.state='second_headache'
            elif self.state=='second_headache' and breath==1 and armed:
                assert beat==1;self.send('E',True);self.state='second_hold'
            elif self.state=='second_hold' and breath==3:
                assert beat==1;self.send('E',False);self.state='second_settle'
            elif self.state=='second_settle' and beat==2:
                assert breath==0;self.mark('beat_completed',beat=2);self.state='exit'
            elif self.state=='exit' and phase==4:
                assert beat==2 and breath==0
                self.mark('earned_fall');self.send('W',False);self.state='release_walk'
            elif self.state=='release_walk':
                assert not self.down('W') and not self.down('E'),'Proof input still held'
                self.finish('earned_route_passed',True)
        except Exception as exc:self.finish('assertion: '+str(exc))


def create_walk_proof(world,threshold,request_input,cap_seconds=35):
    return WalkProof(world,threshold,request_input,cap_seconds)
