"""Author the job loop on BP_L2Journey. Unreal Blueprints own all play state."""

import os
import sys
from pathlib import Path
from shutil import copy2

import build_drive as b
import build_interview as ui
import build_journey as j
from job_hunt_data import JOBS, PITCH, TIME_SKIP, SHIFT, RESULT, HIRE_SCORE, CV_PER_JOB, BOSS_MINIMUM

BP, UI, G = j.BP, ui.UI, b.G
CARD = j.D.ROOT+'/WBP_L2ShiftTimeCard'
SHIFT_TIMES = ('Next morning   06:00', 'That night   23:40', 'Two days later   07:15')
W = '/Script/UMG.Widget:'
USER = '/Script/UMG.UserWidget:'
PC = '/Script/Engine.Controller:'
SOUND = '/Game/FoA/Audio/SFX/UI_FrontEnd/'
SHOT_NAMES = ('BeginJob','RenderJob','ConfirmJob','BeginShift','TickShift','FinishJob','AwardJob','ExitJob','ClearJob',
              'RenderPitch','ScorePitch','RenderShift')
VARIABLES = [('JobBeat','int','0'),('JobTrust','int','0'),('JobReply','text',''),('JobOrder','int','0'),
             ('JobMistakes','int','0'),('JobSeconds','int','0'),('JobWon','bool','false'),
             ('JobCarTransform','transform',''),('JobTimeCard','object:'+b.cls(CARD),''),('CVPriorEcho','float','0')]


def declare():
    if not b.h.call('blueprint_get_info',{'path':CARD}).get('ok'):
        b.call('ui_create_widget',path=j.D.ROOT,name='WBP_L2ShiftTimeCard')
    import json
    script=(f'import unreal,json\nbp=unreal.load_asset({BP!r})\n'
            'print(json.dumps([str(n) for n in unreal.BlueprintEditorLibrary.list_member_variable_names(bp,False)]))')
    names=set(json.loads(b.call('python_run',script=script)['stdout'].strip()))
    changed=False
    for name,kind,value in VARIABLES:
        if name in names:continue
        changed=True
        b.call('blueprint_add_variable',path=BP,variable_name=name,variable_type=kind,default_value=value,
               category='Job hunt',update_existing=True)
    for name in SHOT_NAMES:
        if not b.h.call('blueprint_inspect_graph',{'path':BP,'graph_name':name}).get('ok'):
            changed=True
            b.call('blueprint_add_function',path=BP,function_name=name,inputs=[dict(name='Won',type='bool')] if name=='FinishJob' else [])
    if changed:b.call('blueprint_compile',path=BP,save=True)


def time_card():
    if not b.call('ui_query',path=CARD,name_pattern='TimeBlack').get('matches'):
        b.call('ui_build_tree',widget_blueprint_path=CARD,parent_widget_name='RootCanvas',tree=[dict(
            name='TimeBlack',**{'class':'Border'},properties={'BrushColor':[0,0,0,1],'Visibility':'HitTestInvisible'},
            slot_props=dict(anchors_min=[0,0],anchors_max=[1,1],position=[0,0],size=[0,0],z_order=-1))])
    if not b.call('ui_query',path=CARD,name_pattern='TimeTitle').get('matches'):
        labels=[]
        for name,copy,size,y,h,font in (('TimeTitle','First shift',84,-56,108,'F_FoA_Display'),
                                        ('TimeClock','NEXT MORNING    06:00',25,54,42,'F_FoA_UI')):
            labels.append(dict(name=name,**{'class':'TextBlock'},properties={'Text':copy,'Justification':'Center',
                'Font':{'FontObject':f'/Game/FoA/UI/Fonts/{font}.{font}','TypefaceFontName':'ExtraBold','Size':size},
                'ColorAndOpacity':{'SpecifiedColor':[1,1,1,1]},'Visibility':'HitTestInvisible'},
                slot_props=dict(anchors_min=[.5,.5],anchors_max=[.5,.5],alignment=[.5,.5],position=[0,y],size=[720,h])))
        b.call('ui_build_tree',widget_blueprint_path=CARD,parent_widget_name='RootCanvas',tree=labels)
    for name in ('TimeTitle','TimeClock'):
        b.call('ui_set_variable',widget_blueprint_path=CARD,widget_name=name,is_variable=True)
    b.call('ui_compile_widget',widget_blueprint_path=CARD);b.call('ui_save_widget',widget_blueprint_path=CARD)


def controller(g):return g.f(b.GS+'GetPlayerController',PlayerIndex=0)


def text_string(g,value):return g.f('/Script/Engine.KismetTextLibrary:Conv_TextToString',InText=value)


def display(g,name,question,choices,evidence='',keys=None,voice=False,voice_text=None):
    # level2 2026-11-18: key caps instead of hint text (the fonts have no arrow glyphs): build_l2_stop_look.SetKeys
    from build_l2_stop_look import PICK
    status=ui.cat(g,'Employability ',ui.num(g,g.getv('Employability')))
    g.do(b.cls(UI)+':Refresh',self=g.getv('InterviewHUD'),Speaker=name,Question=question,
         Answer0=choices[0] if choices else '',Answer1=choices[1] if len(choices)>1 else '',
         Answer2=choices[2] if len(choices)>2 else '',Evidence=evidence,Status=ui.textvalue(g,status),Hint='',
         Selected=g.getv('DialogueSelected'),Count=len(choices),CanChoose=g.getv('DialogueReady'))
    arrows,choose,key_a,label_a,key_b,label_b=keys or PICK
    g.do(b.cls(UI)+':SetKeys',self=g.getv('InterviewHUD'),Arrows=arrows,Choose=choose,KeyA=key_a,LabelA=label_a,
         KeyB=key_b,LabelB=label_b)
    if voice:
        g.own('SayCharacter',Text=question if voice_text is None else voice_text,
              Speaker=g.math('Add_IntInt',A=g.getv('Stop'),B=1),Emotion=0)


def pick(g,kind,values,index):
    selected=values[0]
    for i,value in enumerate(values[1:],1):
        branch='bSelectA' if kind=='Object' else 'bPickA'
        selected=g.math('Select'+kind,A=value,B=selected,**{branch:g.math('EqualEqual_IntInt',A=index,B=i)})
    return selected


def state(g,mode,dialogue_state=0,ready=True):
    for name,value in [('DialogueMode',mode),('DialogueState',dialogue_state),('DialogueSelected',0),('DialogueReady',ready)]:
        g.setv(name,value)


def begin():
    g=G(BP,'BeginJob');j.phase(g,4)
    g.own('ClearJob');g.own('ReleaseStop')
    car=g.getv('Car');p=g.getv('Player')
    g.setv('JobCarTransform',g.f(b.A+'GetTransform',self=car))
    g.do(b.cls(b.CAR)+':Deactivate',self=car)
    g.do(b.A+'K2_SetActorTransform',self=p,NewTransform=g.getv('StreetTransform'),bSweep=False,bTeleport=True)
    heading=g.math('BreakRotator',InRot=g.f(b.A+'K2_GetActorRotation',self=car))  # level2: face the way the car arrived
    g.do(PC+'SetControlRotation',self=controller(g),NewRotation=g.math('MakeRotator',Pitch=-4,Yaw=(heading[0],'Yaw')))
    j.cinematic(g,True);j.stage_colour(g,.42)
    g.setv('StopBusy',False);g.setv('JobBeat',0);g.setv('JobTrust',0);g.setv('JobReply','');g.setv('DialogueHeld',False)
    state(g,PITCH,ready=False)
    g.own('EnsureDialogue');g.own('RenderJob');ui.timer(g,'DialogueUnlock',.4)
    g.setv('EmployerEntrance',g.f(b.GS+'GetTimeSeconds'))
    g.do(b.cls(UI)+':PaintEmployer',self=g.getv('InterviewHUD'),Index=g.getv('Stop'),Alpha=0.)
    g.do(b.SL+'K2_SetTimer',FunctionName='TickEmployer',Time=.033,bLooping=True)
    g.own('FormStopSand')  # level2 2026-11-18: Lux3D sand objects in the street (build_l2_stop_sand.py)
    g.own('OpenStopLine')  # round 3: his lines over the shift (build_l2_round3.py)
    j.stop_fade(g,1,0,.46);g.finish()


def render_pitch(jobs):
    g=G(BP,'RenderPitch')
    for i,job in enumerate(jobs):
        branch=ui.guard(g,ui.eq(g,'Stop',i))
        for beat,pitch in enumerate(job.pitch):
            step=ui.guard(g,ui.eq(g,'JobBeat',beat))
            previous=job.role+'\n'+SHIFT_TIMES[i] if beat==0 else g.getv('JobReply')
            display(g,job.employer,pitch.question,pitch.options,previous,voice=True)
            g.side(step,False)
        offered=ui.guard(g,g.math('GreaterEqual_IntInt',A=g.getv('JobTrust'),B=HIRE_SCORE))
        display(g,job.employer,('Come in at six. I’ll put you on the first orders.',
                'Be here at eleven forty. I’ll give you a route sheet.',
                'Come in at seven fifteen. We’ll start with the stock count.')[i],('Take the shift',),
                g.getv('JobReply'),keys=(0,'','Enter','Confirm','',''),voice=True)
        g.side(offered,False)
        display(g,job.employer,'I’m going to hold the opening for now.',('Try the conversation again','Back to the car'),
                g.getv('JobReply'),voice=True)
        g.side(branch,False)
    g.finish()


def score_pitch(jobs):
    g=G(BP,'ScorePitch')
    for i,job in enumerate(jobs):
        job_branch=ui.guard(g,ui.eq(g,'Stop',i))
        for beat,pitch in enumerate(job.pitch):
            branch=ui.guard(g,ui.eq(g,'JobBeat',beat));selection=g.getv('DialogueSelected')
            points=pick(g,'Int',pitch.points,selection)
            reply=pick(g,'String',pitch.replies,selection)
            g.setv('JobTrust',g.math('Add_IntInt',A=g.getv('JobTrust'),B=points))
            g.setv('JobReply',ui.textvalue(g,reply));g.setv('JobBeat',beat+1)
            style=0 if beat==0 else g.math('SelectInt',A=1,B=2,bPickA=g.math('GreaterEqual_IntInt',A=g.getv('JobTrust'),B=HIRE_SCORE))
            state(g,PITCH,style,False);g.own('RenderJob');ui.timer(g,'DialogueUnlock',.3)
            g.side(branch,False)
        g.side(job_branch,False)
    g.finish()


def start_time_skip(g):
    state(g,TIME_SKIP,ready=False);g.setv('StopBusy',True)
    g.own('StopCharacterVoice');g.do(USER+'RemoveFromParent',self=g.getv('InterviewHUD'))
    j.stop_fade(g,1,1,0)
    widget=g.ref();g.node(widget,'create_widget',0,0,class_path=b.cls(CARD));g.put(widget,'OwningPlayer',controller(g))
    g.chain(g.tail,widget);g.tail=widget;g.setv('JobTimeCard',(widget,'ReturnValue'))
    for name,choices in (('TimeTitle',tuple(job.employer for job in JOBS)),('TimeClock',SHIFT_TIMES)):
        value=ui.textvalue(g,pick(g,'String',choices,g.getv('Stop')))
        g.do('/Script/UMG.TextBlock:SetText',self=g.getv(name,g.getv('JobTimeCard'),CARD),InText=value)
    g.do(USER+'AddToViewport',self=g.getv('JobTimeCard'),ZOrder=65)
    ui.timer(g,'BeginShift',1.6)


def begin_shift(jobs):
    g=G(BP,'BeginShift');j.phase(g,4)
    valid=g.branch(g.f(b.SL+'IsValid',Object=g.getv('JobTimeCard')));g.side(valid)
    g.do(USER+'RemoveFromParent',self=g.getv('JobTimeCard'))
    join=g.setv('JobTimeCard','');g.link(valid,'else',join[0],'execute')
    g.setv('StopBusy',False);g.setv('JobOrder',0);g.setv('JobMistakes',0);g.setv('JobWon',False)
    g.setv('JobSeconds',pick(g,'Int',(52,42,52),g.getv('Stop')))
    g.setv('ShiftFeedback','');g.own('ResetShiftRound')
    g.setv('DialogueHeld',False);state(g,SHIFT);g.own('EnsureDialogue');g.own('RenderJob')
    g.own('PlaceCrate')  # Queen Market: the crate in front of him, his eyes down on it (build_l2_stop_look.py)
    g.do(b.cls(UI)+':PaintEmployer',self=g.getv('InterviewHUD'),Index=-1,Alpha=0.)
    g.do(b.SL+'K2_SetTimer',FunctionName='TickShiftBoard',Time=.033,bLooping=True)
    j.stop_fade(g,1,0,.42);j.stop_timer(g,'TickShift',1.)
    g.finish()


def clock(g):
    completed=ui.cat(g,ui.num(g,g.getv('JobOrder')),' of 4 orders')
    seconds=ui.cat(g,ui.num(g,g.getv('JobSeconds')),' s remaining')
    mistakes=ui.cat(g,ui.num(g,g.getv('JobMistakes')),' of 2 mistakes')
    return ui.textvalue(g,ui.cat(g,ui.cat(g,ui.cat(g,ui.cat(g,completed,'\n'),seconds),'\n'),mistakes))


def tick_shift():
    g=G(BP,'TickShift');ui.guard(g,ui.eq(g,'DialogueMode',SHIFT))
    g.setv('JobSeconds',g.math('Max',A=0,B=g.math('Subtract_IntInt',A=g.getv('JobSeconds'),B=1)))
    empty=ui.guard(g,ui.eq(g,'JobSeconds',0));g.own('FinishJob',Won=False)
    g.side(empty,False);g.own('RenderShift');j.stop_timer(g,'TickShift',1.);g.finish()


def confirm():
    g=G(BP,'ConfirmJob')
    pitch=ui.guard(g,ui.eq(g,'DialogueMode',PITCH))
    ask=ui.guard(g,ui.eq(g,'DialogueState',0));g.own('ScorePitch')
    g.side(ask,False);hired=ui.guard(g,ui.eq(g,'DialogueState',1));start_time_skip(g)
    g.side(hired,False);retry=ui.guard(g,ui.eq(g,'DialogueSelected',0));g.own('BeginJob')
    g.side(retry,False);g.own('ExitJob')
    g.side(pitch,False);shift=ui.guard(g,ui.eq(g,'DialogueMode',SHIFT));g.own('SubmitShiftAction')
    g.side(shift,False);ui.guard(g,ui.eq(g,'DialogueMode',RESULT))
    passed=ui.guard(g,g.getv('JobWon'));g.own('ExitJob')
    g.side(passed,False);try_again=ui.guard(g,ui.eq(g,'DialogueSelected',0));start_time_skip(g)
    g.side(try_again,False);g.own('ExitJob');g.finish()


def finish():
    g=G(BP,'FinishJob');ui.guard(g,ui.eq(g,'DialogueMode',SHIFT))
    g.own('SettleCrate')  # the tick stops here: nothing left hanging mid-drop
    g.do(b.SL+'K2_ClearTimer',FunctionName='TickShift')
    g.do(b.SL+'K2_ClearTimer',FunctionName='TickShiftBoard')
    g.setv('JobWon',g.arg('Won'));state(g,RESULT,g.math('SelectInt',A=1,B=2,bPickA=g.arg('Won')),False)
    won=ui.guard(g,g.arg('Won'));g.own('AwardJob')
    end=g.own('RenderJob');g.link(won,'else',end[0],'execute');ui.timer(g,'DialogueUnlock',.36);g.finish()


def award(jobs):
    g=G(BP,'AwardJob')
    for i,job in enumerate(jobs):
        branch=ui.guard(g,ui.eq(g,'Stop',i));var=f'Edited{i}'
        ui.guard(g,g.math('Not_PreBool',A=g.getv(var)))
        g.setv(var,True)
        g.setv('Employability',g.math('Add_IntInt',A=g.getv('Employability'),B=CV_PER_JOB))
        g.own('RefreshProgressDisplays')
        g.side(branch,False)
    g.finish()


def render(jobs):
    g=G(BP,'RenderJob')
    pitch=ui.guard(g,ui.eq(g,'DialogueMode',PITCH));g.own('RenderPitch')
    g.side(pitch,False);shift=ui.guard(g,ui.eq(g,'DialogueMode',SHIFT));g.own('RenderShift')
    g.side(shift,False);ui.guard(g,ui.eq(g,'DialogueMode',RESULT))
    g.do(b.cls(UI)+':PaintShiftBoard',self=g.getv('InterviewHUD'),Mode=-1,Readout='',Notice='')
    won=ui.guard(g,g.getv('JobWon'))
    line=pick(g,'String',tuple(job.evidence for job in jobs),g.getv('Stop'))
    # level2 2026-11-18: say when the C.V is enough for the interview, the level's last goal
    ready=g.math('GreaterEqual_IntInt',A=g.getv('Employability'),B=BOSS_MINIMUM)
    box=ui.textvalue(g,g.math('SelectString',A='C.V. updated\nCentral Personnel will interview you today.',B='C.V. updated',bPickA=ready))
    leave=ui.textvalue(g,g.math('SelectString',A='Drive to the interview',B='Back to the car',bPickA=ready))
    display(g,'Shift complete',ui.textvalue(g,line),(leave,),box,keys=(0,'','C','Read the C.V.','Enter','Continue'))
    g.side(won,False)
    reason=g.math('SelectString',A='The shift ended before you finished.',B='You made two mistakes.',bPickA=ui.eq(g,'JobSeconds',0))
    display(g,'Shift incomplete',ui.textvalue(g,reason),('Retry the shift','Back to the car'),
            '')
    g.finish()


def clear():
    g=G(BP,'ClearJob');g.own('HideStopSand');g.own('CloseStopLine');g.own('HideCrate')
    for fn in ('BeginShift','TickShift','TickShiftBoard','TickEmployer'):g.do(b.SL+'K2_ClearTimer',FunctionName=fn)
    card=g.getv('JobTimeCard');ui.valid(g,card)
    g.do(USER+'RemoveFromParent',self=card);g.setv('JobTimeCard','');g.finish()


def exit_job(all_jobs=False):
    g=G(BP,'ExitJob');j.phase(g,4)
    g.own('ClearJob');g.own('ReleaseDialogue')
    if all_jobs:
        from job_route import next_job
        g.setv('Stop',next_job(g))
    g.own('ActivateCar')
    car=g.getv('Car')
    g.do(b.A+'K2_SetActorTransform',self=car,NewTransform=g.getv('JobCarTransform'),bSweep=False,bTeleport=True)
    g.do(b.cls(b.CAR)+':CheckDestination',self=car)
    g.finish()


def apply(jobs):
    from finalize_l2_graphs import checked_compile
    import employer_portraits
    import shift_minigames
    declare();time_card()
    employer_portraits.install()
    shift_minigames.install()
    original=G.run

    def apply_body(graph):
        graph.ops.append(dict(op='fit_comments'))
        result=b.h.call('blueprint_graph_batch',dict(path=graph.path,graph_name=graph.graph,ops=graph.ops,compile=False,save=False),timeout=120)
        data=result.get('data') or {}
        if not result.get('ok'):
            made=list((data.get('refs') or {}).values())
            if made:b.call('blueprint_remove_nodes',path=graph.path,graph_name=graph.graph,node_ids=made)
            index=data.get('failed_index')
            raise RuntimeError((graph.graph,result.get('error'),graph.ops[index] if index is not None else None))
        print(graph.graph,data.get('applied'),'operations',flush=True)

    G.run=apply_body
    try:
        for fn in (clear,lambda:exit_job(len(jobs)>1),begin,tick_shift,confirm,finish):
            b.h.renew_all(os.environ['FOA_AGENT'],240);fn()
        for fn in (render_pitch,score_pitch,begin_shift,award,render):
            b.h.renew_all(os.environ['FOA_AGENT'],240);fn(jobs)
    finally:
        G.run=original
        print(checked_compile(BP))


def run(step):
    import editor_lock
    from finalize_l2_graphs import checked_compile
    owner='main-job-hunt';os.environ.update(FOA_AGENT=owner,HAYBA_AGENT_ID=owner);b.D.OWNER=owner
    roots=['/Game/FoA/Level2']+(['Level'] if step=='ending' else [])
    token=editor_lock.acquire(owner,wait_s=5,ttl=240,areas=roots)
    os.environ['FOA_LEASE']=token or editor_lock.hayba_leases(owner)[0][0]
    try:
        assert not b.call('editor_get_state')['pie_running']
        directory=Path('Saved/Backups/job-hunt');directory.mkdir(parents=True,exist_ok=True)
        for path in (BP,UI,b.CAR,b.ROAD,j.THRESHOLD):
            asset=Path('Content'+path[5:]+'.uasset')
            if asset.exists() and not (directory/asset.name).exists():copy2(asset,directory/asset.name)
        if step=='slice':
            from job_cv import generate,install
            if not (Path('Content')/j.D.ROOT.removeprefix('/Game/')/'JobRecords/SM_JobRecord1.uasset').is_file():
                generate((1,));install((1,))
            b.h.renew_all(owner,240)
            apply(JOBS[:1])
            ui.GRAPHS['RenderDialogue']();ui.GRAPHS['DialogueConfirm']();ui.GRAPHS['ReleaseDialogue']()
            for name in ('StageStop','ResumeRun','CheckCVPaper','ReleaseCVPaper'):j.GRAPHS[name]()
        if step in ('slice','slice_finish'):
            j.GRAPHS['OpenCVPaper']()
            b.STEPS['BP_L2Car.CheckDestination']()
            print(checked_compile(BP));print(checked_compile(b.CAR))
        elif step=='route':
            import free_drive
            import job_route
            from job_cv import generate,install
            masks=tuple(i for i in range(2,8) if not (Path('Content')/j.D.ROOT.removeprefix('/Game/')/f'JobRecords/SM_JobRecord{i}.uasset').is_file())
            if masks:generate(masks);install(masks)
            b.h.renew_all(owner,240);apply(JOBS)
            job_route.declare();print(checked_compile(b.ROAD));print(checked_compile(b.CAR))
            for function in (free_drive.checkpoint,free_drive.destination,free_drive.park,b.start_leg):
                b.h.renew_all(owner,240);function(True)
            for function in (j.arrive,j.stage_stop,j.open_cv_paper,j.check_cv_paper,j.release_cv_paper,j.restart,ui.start_interview,ui.render,ui.advance,ui.lost):
                b.h.renew_all(owner,240);function(True)
            for index in range(6):
                b.h.renew_all(owner,240);ui.render_question(index,True);ui.apply_question(index,True)
            print(checked_compile(BP));print(checked_compile(b.CAR))
        elif step=='shift_polish':
            import shift_minigames
            import employer_portraits
            employer_portraits.install()
            shift_minigames.install()
            for fn in (begin,lambda:begin_shift(JOBS),confirm,finish,clear,lambda:render(JOBS)):fn()
            print(checked_compile(UI));print(checked_compile(BP))
        elif step=='dialogue_polish':
            ui.refresh_widget()
            ui.render_question(0,True)
            ui.render_question(1,True)
            print(checked_compile(UI));print(checked_compile(BP))
        elif step=='transition_polish':
            import free_drive
            import build_job_ending as ending
            time_card();confirm();render_pitch(JOBS)
            free_drive.destination(True);b.simple('RefreshHUD')
            if not b.h.call('blueprint_inspect_graph',{'path':ending.BP,'graph_name':'FadeWakeToCredits'}).get('ok'):
                b.call('blueprint_add_function',path=ending.BP,function_name='FadeWakeToCredits')
            ending.fade_wake();ending.start_wake();ending.restore()
            print(checked_compile(ending.BP))
            print(checked_compile(BP));print(checked_compile(b.CAR));print(checked_compile(CARD))
        elif step=='look':
            import build_threshold as threshold
            import job_dream_look
            job_dream_look.install();print(checked_compile(j.THRESHOLD));threshold.enter(True)
            print(checked_compile(j.THRESHOLD))
        elif step=='ending':
            import build_threshold as threshold
            import build_job_ending
            build_job_ending.install();threshold.restore(True);print(checked_compile(j.THRESHOLD))
        elif step=='polish':
            import free_drive
            import build_job_ending
            b.call('blueprint_add_variable',path=BP,variable_name='CVPriorEcho',variable_type='float',default_value='0',update_existing=True)
            free_drive.destination(True);j.open_cv_paper(True);j.check_cv_paper();j.release_cv_paper()
            build_job_ending.start_wake()
        elif step=='paper':
            from cv_paper_setup import PRINT_MATERIAL
            from job_cv import sharpen_print
            b.call('python_exec_file',path='P:/FoA/Tools/Unreal/ui/close_ui_editors.py',env={'FOA_ASSETS':PRINT_MATERIAL},resources=['asset:'+PRINT_MATERIAL])
            sharpen_print()
            j.open_cv_paper(True);j.check_cv_paper();j.release_cv_paper()
            print(checked_compile(BP))
        elif step=='gamepad':
            b.call('blueprint_add_variable',path=BP,variable_name='GamepadNavAt',variable_type='float',default_value='0',update_existing=True)
            if not b.h.call('blueprint_inspect_graph',{'path':BP,'graph_name':'GamepadDialogueMove'}).get('ok'):
                b.call('blueprint_add_function',path=BP,function_name='GamepadDialogueMove',inputs=[dict(name='Delta',type='int')])
            ui.pad_move()
            nodes,edges=b.inspect(BP,'EventGraph');lookup={node['node_id']:node for node in nodes}
            batch=b.Batch(BP,'EventGraph')
            for i,direction in enumerate(('Up','Down')):
                source=next(node for node in nodes if node['title']==f'Gamepad D-pad {direction}')
                edge=next(edge for edge in edges if edge['from_node']==source['node_id'] and edge['from_pin']=='Pressed')
                if lookup[edge['to_node']]['title']=='GamepadDialogueMove':continue
                batch.cut(source['node_id'],'Pressed',edge['to_node'],edge['to_pin'])
                batch.ops.append(dict(op='remove',node_ids=[edge['to_node']]))
                ref=f'pad_move_{i}'
                batch.fn(ref,b.cls(BP)+':GamepadDialogueMove',400+i*700,9000,Delta=(-1,1)[i])
                batch.link(source['node_id'],'Pressed',ref,'execute')
            if batch.ops:batch.run()
            print(checked_compile(BP))
        elif step not in ('slice','slice_finish'):raise ValueError(step)
    finally:editor_lock.release(owner)


if __name__=='__main__':run(sys.argv[1])
