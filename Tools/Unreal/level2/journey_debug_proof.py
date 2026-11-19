"""Actual F6/F9 input proof inside the parent's existing isolated QA PIE.

create_journey_debug_proof(world, journey, request_input, cap_seconds=12)
request_input receives one editor_pie_press_key argument dict; the parent queues
it with a unique ID. Call tick(dt), inspect done/result/state, and always close().
No own callback, PIE lifecycle, lease, Blueprint call or save write. Parent must
release F6/F9 before ending PIE on failure (queued cleanup may not be serviced).
Starts at Journey phase1 with diagnostics closed; leaves phase2 with them closed.
F6 intentionally changes the isolated slot from FoA_QA_Play to FoA_QA_DebugSkip.
"""
import time

FRONT='/Game/FoA/UI/Framework/BP_FoAFrontEnd.BP_FoAFrontEnd_C'
QA_SLOTS={'FoA_QA_Play','FoA_QA_DebugSkip'}


class JourneyDebugProof:
    def __init__(self, world, journey, request_input, cap_seconds=12, engine=None, now=None):
        if engine is None:
            import unreal as engine
        self.u,self.world,self.journey=engine,world,journey
        self.request_input,self.now=request_input,now or time.monotonic
        self.started=self.now();self.cap=min(15.,max(3.,cap_seconds))
        self.done,self.state,self.key_down=False,'start',False
        self.after=0.;self.result=dict(passed=False,trace=[],scope='Actual F6/F9 key requests; no gameplay method calls')
        assert self.alive(),'Current parent-owned QA PIE required'
        gs=engine.GameplayStatics
        self.gi=gs.get_game_instance(world)
        assert self.valid(self.gi) and str(self.get(self.gi,'SaveSlot'))=='FoA_QA_Play','Isolate QA save first'
        self.fe=gs.get_actor_of_class(world,engine.load_class(None,FRONT))
        self.pc=gs.get_player_controller(world,0)
        self.player,self.car=[self.get(journey,n) for n in ('Player','Car')]
        assert all(self.valid(x) for x in (self.fe,self.pc,self.player,self.car)),'Missing journey references'
        assert self.get(journey,'Phase')==1 and not self.get(journey,'StopBusy') and not self.overlay_visible(),'Resting street phase with diagnostics closed required'
        assert not self.get(self.fe,'bDebugStepHeld'),'Release F6 before starting proof'
        self.baseline=self.snapshot()

    @staticmethod
    def get(obj,name):return obj.get_editor_property(name)

    def valid(self,obj):return obj is not None and self.u.SystemLibrary.is_valid(obj)

    def alive(self):
        return (self.valid(self.world) and self.valid(self.journey)
            and self.u.get_editor_subsystem(self.u.UnrealEditorSubsystem).get_game_world()==self.world
            and self.journey.get_world()==self.world)

    def overlay_visible(self):
        widget=self.get(self.fe,'DebugPanel')
        return self.valid(widget) and widget.is_in_viewport() and widget.is_visible()

    def snapshot(self):
        def fields(obj,names):return {n:self.get(obj,n) for n in names.split()}
        def path(obj):return obj.get_path_name() if self.valid(obj) else None
        gs=self.u.GameplayStatics
        return dict(journey=fields(self.journey,'Phase Stop Employability RoadAttempts Assisted Submitted FinaleComplete Edited0 Edited1 Edited2 StopBusy StopActionState StopActionDone'),
            car=fields(self.car,'Active Leg Failed Arrived Composure'),
            player=fields(self.player,'bCinematic bInteractionLocked'),
            day=self.get(self.gi,'DayCount'),slot=str(self.get(self.gi,'SaveSlot')),
            knowledge=sorted(map(str,self.get(self.gi,'Knowledge'))),notes=list(map(str,self.get(self.gi,'Notebook'))),
            possessed=path(gs.get_player_pawn(self.world,0)),view=path(self.pc.get_view_target()),
            move_ignored=self.pc.is_move_input_ignored(),look_ignored=self.pc.is_look_input_ignored(),
            cursor=bool(self.get(self.pc,'bShowMouseCursor')),paused=gs.is_game_paused(self.world),
            gameplay=bool(self.get(self.fe,'bInGameplay')))

    def send(self,key,event):
        args=dict(key=key,event=event)
        if event=='pressed_and_released':args['held_ms']=100
        self.request_input(args)
        if key=='F6':self.key_down=event=='pressed'
        self.mark('input_requested',input=args)

    def mark(self,event,**fields):
        self.result['trace'].append(dict(t=round(self.now()-self.started,3),event=event,**fields))

    def close(self):
        if self.key_down and self.alive():
            self.send('F6','released')

    def finish(self,reason,passed=False):
        if self.done:return
        self.done=True;self.state='done'
        self.result.update(passed=passed,reason=reason,elapsed=round(self.now()-self.started,3))
        self.close()

    def tick(self,_dt=0):
        if self.done:return
        try:
            if not self.alive() or not all(self.valid(x) for x in (self.gi,self.fe,self.pc,self.player,self.car)):
                return self.finish('world_or_actor_gone')
            assert str(self.get(self.gi,'SaveSlot')) in QA_SLOTS,'QA isolation changed'
            elapsed=self.now()-self.started
            if elapsed>self.cap:return self.finish('timeout')
            current=self.snapshot()
            if self.state=='start':
                assert current==self.baseline,'Gameplay changed before input'
                self.send('F9','pressed_and_released');self.state='opening'
            elif self.state=='opening':
                assert current==self.baseline,'F9 changed gameplay'
                if self.overlay_visible():
                    self.mark('f9_open_unchanged',snapshot=current)
                    self.send('F6','pressed');self.state='pressing'
            elif self.state=='pressing':
                assert current['journey']['Phase'] in (1,2),'F6 advanced more than one step'
                if current['journey']['Phase']==2:
                    expected=dict(self.baseline,journey=dict(self.baseline['journey'],Phase=2),slot='FoA_QA_DebugSkip')
                    assert current==expected,'F6 changed unrelated gameplay or did not isolate debug progress'
                    assert self.get(self.fe,'bDebugStepHeld'),'F6 held latch absent'
                    self.after=elapsed+.8;self.held_state=current;self.state='holding'
                    self.mark('f6_one_step',snapshot=current)
            elif self.state in ('holding','repeated'):
                assert current==self.held_state,'Held F6 advanced or changed gameplay'
                assert self.get(self.fe,'bDebugStepHeld'),'F6 latch cleared before release'
                if elapsed>=self.after:
                    if self.state=='holding':
                        self.send('F6','pressed');self.after=elapsed+.8;self.state='repeated'
                    else:
                        self.mark('held_repeat_ignored',snapshot=current)
                        self.send('F6','released');self.state='releasing'
            elif self.state=='releasing':
                assert current==self.held_state,'F6 release changed gameplay'
                if not self.get(self.fe,'bDebugStepHeld'):
                    self.mark('f6_latch_released')
                    self.send('F9','pressed_and_released');self.state='closing';self.after=elapsed+.5
            elif self.state=='closing':
                assert current==self.held_state,'F9 close changed gameplay'
                if elapsed>=self.after and not self.overlay_visible():
                    self.mark('f9_close_unchanged',snapshot=current)
                    self.result.update(f6_phase=[1,2],held_repeat_ignored=True,f9_preserved_state=True)
                    self.finish('passed',True)
        except Exception as exc:
            self.mark('error',message=str(exc),state=self.state)
            self.finish('error: '+str(exc))


def create_journey_debug_proof(world,journey,request_input,cap_seconds=12):
    return JourneyDebugProof(world,journey,request_input,cap_seconds)
