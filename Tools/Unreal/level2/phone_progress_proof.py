"""Parent-owned QA PIE phone contract driver; no registration, PIE or save lifecycle.

Create PhoneProof(world,journey,request_input=parent_input_queue), tick it from the parent's bounded callback, read
done/result, and close() before PIE teardown. This proves native method routing;
optional request_input queues actual P presses for open/close. Page navigation
uses native widget methods; rendering and additional controller keys need captures.
"""
import time
import importlib
import phone_progress_data
importlib.reload(phone_progress_data)
from phone_progress_data import can_open_phone, phone_lines


class PhoneProof:
    def __init__(self,world,journey,cap_seconds=10,request_input=None):
        import unreal
        self.u,self.world,self.journey=unreal,world,journey
        self.t0=time.monotonic();self.next=self.t0+.6
        self.cap=min(12.,max(1.,cap_seconds));self.request_input=request_input
        self.done,self.state=False,'open'
        self.result=dict(passed=False,scope='Actual P open/close plus native page methods' if request_input else
                         'Native phone methods; real keys and visual reading require parent proof',trace=[])
        assert self.alive(),'Parent QA PIE required'
        self.gi=unreal.GameplayStatics.get_game_instance(world)
        assert str(self.get(self.gi,'SaveSlot'))=='FoA_QA_Play','Use isolated progress first'
        self.phone=self.actor('/Game/FoA/UI/Game/BP_Phone')
        self.front=self.actor('/Game/FoA/UI/Framework/BP_FoAFrontEnd')
        self.director=self.actor('/Game/FoA/Gameplay/BP_BeatDirector')
        self.player=self.get(journey,'Player')
        assert all(self.valid(x) for x in (self.phone,self.front,self.director,self.player))
        assert can_open_phone(self.get(journey,'Phase'),self.get(journey,'StopBusy'),self.get(journey,'PhoneSession'))
        self.pc=unreal.GameplayStatics.get_player_controller(world,0)
        self.before=self.baseline()
        self.view=self.pc.get_view_target()

    @staticmethod
    def get(obj,name):return obj.get_editor_property(name)

    def valid(self,obj):return obj is not None and self.u.SystemLibrary.is_valid(obj)

    def alive(self):
        return self.valid(self.world) and self.valid(self.journey) and \
            self.u.get_editor_subsystem(self.u.UnrealEditorSubsystem).get_game_world()==self.world

    def actor(self,path):
        return self.u.GameplayStatics.get_actor_of_class(self.world,self.u.load_class(None,path+'.'+path.rsplit('/',1)[-1]+'_C'))

    def baseline(self):
        return dict(phase=self.get(self.journey,'Phase'),score=self.get(self.journey,'Employability'),
                    edits=[bool(self.get(self.journey,'Edited'+str(i))) for i in range(3)],
                    notes=list(map(str,self.get(self.gi,'Notebook'))),knowledge=sorted(map(str,self.get(self.gi,'Knowledge'))),
                    day=self.get(self.gi,'DayCount'),beat=self.get(self.director,'BeatIndex'),
                    cinematic=self.get(self.player,'bCinematic'),move_ignored=self.pc.is_move_input_ignored())

    def widget(self):
        screen=self.get(self.phone,'Screen');assert self.valid(screen)
        widget=screen.get_user_widget_object();assert self.valid(widget)
        return widget

    def line(self,widget,name):
        text=self.get(widget,name);assert self.valid(text)
        return str(text.get_text())

    def phone_view(self):
        view=self.pc.get_view_target()
        assert view==self.player,('Phone must use the player camera',view.get_name() if self.valid(view) else None)
        assert self.get(self.player,'bCameraClose'),'Player first-person visibility did not settle'
        raised=float(self.get(self.player,'PhoneRaise'))
        assert raised>=.99,('Phone hold has not settled',raised)
        return dict(view=view.get_name(),phone_raise=round(raised,3))

    def pages_ready(self,widget):
        pages=self.get(widget,'Pages');lock=self.get(widget,'Ovl_Lock')
        assert self.valid(pages) and self.valid(lock)
        # SetPage selects an app under the independent lock-screen overlay.
        # The authored unlock finishes at 1.5s; its Tick live window is 1.7s.
        return float(self.get(widget,'LockT'))>=1.7 and \
            float(pages.get_render_opacity())>=.99 and float(lock.get_render_opacity())<=.01

    def page_view(self,widget,index,reading=False):
        assert self.pages_ready(widget),'App page is still covered by the lock screen'
        assert self.get(widget,'CurrentPage')==index,'Wrong phone app selected'
        assert self.get(widget,'Pages').get_active_widget_index()==index,'Wrong phone app is drawing'
        assert bool(self.get(widget,'bReadingMessage'))==reading,'Wrong message detail state'
        return dict(page=index,reading=reading,lock_t=round(float(self.get(widget,'LockT')),3))

    def finish(self,reason,passed=False):
        self.result.update(reason=reason,passed=passed,elapsed=round(time.monotonic()-self.t0,3))
        self.done=True

    def close(self):
        if self.alive() and self.valid(self.phone) and self.get(self.phone,'bOpen'):
            self.phone.call_method('PhonePutAway',())

    def tick(self,_dt=0):
        if self.done:return
        try:
            if not self.alive() or not all(self.valid(x) for x in (self.phone,self.front,self.player,self.director,self.gi,self.pc)):
                return self.finish('world_or_actor_gone')
            now=time.monotonic()
            if now-self.t0>self.cap:return self.finish('cap')
            if now<self.next:return
            if self.state=='open':
                self.view=self.pc.get_view_target()
                if self.request_input:self.request_input(dict(key='P',event='pressed_and_released',held_ms=100))
                else:self.journey.call_method('OpenPhone',())
                self.state='opening'
                return
            if self.state=='opening':
                if not self.get(self.phone,'bOpen'):return
                assert self.get(self.journey,'PhoneSession')
                # Do not enter a capture state until both the camera blend and
                # the existing .35-second phone hold have visibly settled.
                if not hasattr(self,'opened_at'):self.opened_at=now
                if now-self.opened_at<.6:return
                if not self.pages_ready(self.widget()):return
                self.result['trace'].append(dict(event='phone_view',**self.phone_view()))
                self.widget().call_method('SetPage',(0,))
                self.next,self.state=now+.6,'inspect'
                return
            if self.state=='inspect':
                self.phone_view()
                widget=self.widget()
                page=self.page_view(widget,0)
                assert self.get(widget,'bL2Phone')
                assert 'visible' in str(self.get(widget,'L2CVBlock').get_visibility()).lower()
                assert self.line(widget,'Txt_Task0')=='Find a job'
                assert self.line(widget,'Txt_Notif0Body')=='Did you go out?'
                lines=[self.line(widget,'Txt_L2CV'+str(i)) for i in range(3)]
                assert lines==phone_lines(self.before['edits']),(lines,self.before)
                bar=self.get(widget,'Bar_L2Employability');assert self.valid(bar)
                assert abs(float(self.get(bar,'Percent'))-self.before['score']/100.)<.0001
                self.result['trace'].append(dict(event='phone_tasks',score=self.before['score'],lines=lines,**page))
                widget.call_method('SetPage',(1,));widget.call_method('OpenMessage',(0,))
                self.next,self.state=now+.6,'message'
                return
            if self.state=='message':
                self.phone_view()
                widget=self.widget()
                page=self.page_view(widget,1,reading=True)
                assert self.line(widget,'Txt_Message')=='Did you go out?'
                assert self.line(widget,'Txt_ThreadName')=='Mom'
                assert self.get(self.director,'BeatIndex')==self.before['beat']
                self.result['trace'].append(dict(event='mom_message',body=self.line(widget,'Txt_Message'),**page))
                widget.call_method('SetPage',(2,))
                self.next,self.state=now+.6,'notes'
                return
            if self.state=='notes':
                self.phone_view()
                widget=self.widget()
                page=self.page_view(widget,2)
                notebook=self.line(widget,'Txt_Notebook')
                assert all(line in notebook for line in self.before['notes'])
                self.result['trace'].append(dict(event='phone_notes',notes=notebook,**page))
                if self.request_input:self.request_input(dict(key='P',event='pressed_and_released',held_ms=100))
                else:self.phone.call_method('PhonePutAway',())
                self.state='closing'
                return
            if self.state=='closing':
                if self.get(self.phone,'bOpen'):return
                assert not self.get(self.journey,'PhoneSession')
                self.next,self.state=now+.6,'restored'
                return
            if self.state=='restored':
                assert self.baseline()==self.before,('Phone mutated journey/story/input',self.before,self.baseline())
                assert self.pc.get_view_target()==self.view,'Phone did not restore current stage view'
                hud=self.get(self.front,'HUD')
                if self.valid(hud):assert 'collapsed' in str(hud.get_visibility()).lower(),'Bedroom HUD became visible'
                self.result['trace'].append(dict(event='restored',state=self.baseline(),view=self.view.get_name()))
                return self.finish('passed',True)
        except Exception as exc:
            self.finish('error: '+str(exc))
