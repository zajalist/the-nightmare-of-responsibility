"""Actual Enter/E paper inspection; parent owns the isolated QA PIE and input queue.

Second pass explicitly uses Car.Deactivate + Journey.ResumeRun as a retry fixture.
No direct Open/Close/Confirm calls establish a successful player interaction.
"""
import time
from pathlib import Path


def check_rect(points,viewport):
    width,height=viewport
    assert width>=640 and height>=360,('Missing actual game viewport',viewport)
    xs,ys=zip(*points);rect=(min(xs),min(ys),max(xs),max(ys))
    assert rect[0]>0 and rect[1]>0 and rect[2]<width and rect[3]<height,('Paper clipped',rect,viewport)
    fraction=(rect[3]-rect[1])/height
    assert .55<fraction<.85,('Paper is not a readable page',fraction)
    assert abs((rect[0]+rect[2])/2-width/2)<width*.06,'Paper not horizontally centered'
    assert abs((rect[1]+rect[3])/2-height/2)<height*.06,'Paper not vertically centered'
    return dict(rect_px=rect,viewport_px=list(viewport),height_fraction=fraction)


class PaperProof:
    def __init__(self,world,journey,request_input,cap_seconds=20,engine=None,now=None):
        if engine is None:
            import unreal as engine
        self.u,self.world,self.journey=engine,world,journey
        self.request,self.now=request_input,now or time.monotonic
        self.started=self.now();self.cap=min(20.,max(3.,cap_seconds));self.after=0
        self.state='start';self.done=False;self.cycle=0;self.inspector=None
        self.result=dict(passed=False,trace=[],scope='Actual Enter open, E close, Enter car twice; second visit uses explicit Deactivate/ResumeRun fixture')
        assert self.alive(),'Current QA world required'
        self.pc=engine.GameplayStatics.get_player_controller(world,0)
        self.gi=engine.GameplayStatics.get_game_instance(world)
        assert self.valid(self.gi) and str(self.get(self.gi,'SaveSlot'))=='FoA_QA_Play','QA save isolation required'
        self.day=self.get(self.gi,'DayCount')
        self.front=engine.GameplayStatics.get_actor_of_class(world,engine.load_class(None,
            '/Game/FoA/UI/Framework/BP_FoAFrontEnd.BP_FoAFrontEnd_C'))
        assert self.valid(self.front),'Actual frontend required for L1 HUD visibility checks'
        assert self.get(journey,'Phase')==1,'Start at earned street arrival'

    @staticmethod
    def get(obj,name):return obj.get_editor_property(name)

    def valid(self,obj):
        try:return obj is not None and self.u.SystemLibrary.is_valid(obj)
        except TypeError as exc:
            if 'ObjectInstance is null' in str(exc):return False
            raise

    def alive(self):
        return (self.valid(self.world) and self.valid(self.journey)
            and self.u.get_editor_subsystem(self.u.UnrealEditorSubsystem).get_game_world()==self.world)

    def mark(self,event,**fields):
        self.result['trace'].append(dict(t=round(self.now()-self.started,3),cycle=self.cycle,event=event,**fields))

    def send(self,key):
        self.request(dict(key=key,event='pressed_and_released',held_ms=100))
        self.mark('actual_input',key=key);self.after=self.now()+.5

    def l1_hud_snapshot(self):
        assert self.valid(self.front),'Frontend destroyed during paper proof'
        hud=self.get(self.front,'HUD');assert self.valid(hud),'Missing L1 HUD cannot prove suppression'
        row=dict(in_viewport=bool(hud.is_in_viewport()),visible=bool(hud.is_visible()),
                 opacity=float(hud.get_render_opacity()),visibility=str(hud.get_visibility()))
        # Inspect actual runtime widget state. Screenshots independently verify paint.
        assert not (row['in_viewport'] and row['visible'] and row['opacity']>.01),('L1 HUD leaks into Level2',row)
        return row

    def view(self,paper):
        u=self.u;gs=u.GameplayStatics
        assert self.get(self.journey,'Phase')==2 and gs.is_game_paused(self.world),'Paper must pause in phase2'
        hud=self.get(self.journey,'HUD');assert self.valid(hud) and not hud.is_in_viewport(),'Journey panel covers paper'
        mesh=self.get(paper,'ItemMesh');assert self.valid(mesh) and mesh.is_visible() and not self.get(mesh,'hidden_in_game')
        asset=self.get(mesh,'static_mesh');assert self.valid(asset) and asset.get_name()=='SM_L2CVPaper','Wrong inspect mesh'
        assert 'NO_COLLISION' in str(mesh.get_collision_enabled()),'Paper blocks gameplay collision'
        bounds=asset.get_bounds();origin=bounds.origin;extent=bounds.box_extent
        transform=mesh.get_world_transform();points=[]
        for sy,sz in ((-1,-1),(1,-1),(1,1),(-1,1)):
            corner=transform.transform_location(u.Vector(origin.x-extent.x,origin.y+sy*extent.y,origin.z+sz*extent.z))
            projected=gs.project_world_to_screen(self.pc,corner,False)
            ok,screen=projected if isinstance(projected,tuple) else (projected is not None,projected)
            assert ok,'Paper corner behind camera'
            points.append((screen.x,screen.y))
        rect=check_rect(points,tuple(self.pc.get_viewport_size()))
        widget=self.get(paper,'Widget');assert self.valid(widget) and widget.is_in_viewport()
        for name in ('Txt_ItemName','Txt_ItemLine'):
            assert 'COLLAPSED' in str(self.get(widget,name).get_visibility()),'Duplicate inspect label visible'
        assert mesh.get_material(0) and mesh.get_material(1),'Missing paper material'
        return dict(rect,mesh=asset.get_path_name(),paused=True,journey_hud_visible=False,l1_hud=self.l1_hud_snapshot(),
                    materials=[mesh.get_material(i).get_path_name() for i in range(2)],
                    camera=self.pc.player_camera_manager.get_camera_location().to_tuple())

    def finish(self,reason,passed=False):
        self.done=True;self.state='done';self.result.update(reason=reason,passed=passed,elapsed=self.now()-self.started)

    def close(self):
        # Teardown only; actual close in the proof is always E. Guard dead wrappers.
        if self.alive():
            paper=self.get(self.journey,'CVPaper')
            if self.valid(paper) and self.get(paper,'bOpen'):
                self.journey.call_method('ReleaseCVPaper',())

    def tick(self,_dt=0):
        if self.done:return
        try:
            if not self.alive() or not all(self.valid(x) for x in (self.gi,self.pc)):return self.finish('world_or_actor_gone')
            assert str(self.get(self.gi,'SaveSlot'))=='FoA_QA_Play' and self.get(self.gi,'DayCount')==self.day,'Proof changed player progression'
            now=self.now()
            if now-self.started>self.cap:return self.finish('timeout')
            if now<self.after:return
            gs=self.u.GameplayStatics;phase=self.get(self.journey,'Phase')
            if self.state=='start':
                assert phase==1 and not gs.is_game_paused(self.world)
                self.mark('street_hud',l1_hud=self.l1_hud_snapshot())
                self.send('Enter');self.state='opening'
            elif self.state=='opening':
                paper=self.get(self.journey,'CVPaper')
                if not self.valid(paper) or not self.get(paper,'bOpen'):return
                self.inspector=paper;self.state='settled';self.after=now+.65
            elif self.state=='settled':
                assert self.valid(self.inspector),'Inspector destroyed before capture'
                snapshot=self.view(self.inspector)
                path=Path('P:/FoA/Saved/Codex/dream_transition')/f'paper_inspect_{self.cycle}.png'
                self.u.SystemLibrary.execute_console_command(self.world,'Shot showui filename='+str(path).replace('\\','/')+' -nosuffix',self.pc)
                self.mark('paper_visible',path=str(path),**snapshot)
                self.state='capture_hold';self.after=now+.9
            elif self.state=='capture_hold':
                self.view(self.inspector);self.send('E');self.state='closing'
            elif self.state=='closing':
                if gs.is_game_paused(self.world) or self.valid(self.get(self.journey,'CVPaper')):return
                assert phase==2,'Close skipped the ready-to-drive phase'
                assert self.valid(self.inspector) and not self.get(self.inspector,'bOpen')
                closed_widget=self.get(self.inspector,'Widget')
                assert not self.valid(closed_widget) or not closed_widget.is_in_viewport(),'Closed inspector widget leaked'
                assert not self.get(self.get(self.inspector,'ItemMesh'),'static_mesh'),'Closed inspector retained mesh'
                hud=self.get(self.journey,'HUD');assert self.valid(hud) and hud.is_in_viewport(),'Ready hint missing'
                assert 'get in the car' in str(self.get(hud,'Txt_Hint').get_text())
                self.mark('closed_to_ready_hint',paused=False,phase=phase,l1_hud=self.l1_hud_snapshot())
                self.send('Enter');self.state='entering_car'
            elif self.state=='entering_car':
                car=self.get(self.journey,'Car');assert self.valid(car)
                if phase!=3 or not self.get(car,'Active'):return
                assert gs.get_player_pawn(self.world,0)==car and not gs.is_game_paused(self.world),'Car handoff failed'
                self.mark('actual_car_handoff',phase=phase)
                if self.cycle==1:return self.finish('passed',True)
                # Explicit retry setup, not claimed as a player-earned restart.
                car.call_method('Deactivate',());self.journey.call_method('ResumeRun',())
                self.mark('retry_fixture',methods=['Car.Deactivate','Journey.ResumeRun'],genuine_progress=False)
                self.cycle=1;self.state='start';self.after=now+.6
        except Exception as exc:
            self.mark('error',state=self.state,error=repr(exc));self.finish('error: '+str(exc))
