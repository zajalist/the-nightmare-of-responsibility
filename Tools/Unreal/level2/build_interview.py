"""Scoped conversation widget and Journey dialogue graphs. Offline import is safe.

No shared battle widget, player Blueprint, threshold, car, splat or map edits.
Native authoring requires the coordinator's explicit sole-writer window.
"""
import os
import json
from pathlib import Path
import sys
sys.path[:0]=[str(Path(__file__).parent),'P:/FoA/Tools/Unreal']
import interview_data as D
import journey_data as JD
import build_journey as j
from build_drive import G,call,cls,GS,SL,A,SC
import hayba_call as h
import editor_lock

BP=JD.BP
UI=D.WIDGET
TB='/Script/UMG.TextBlock:'
UW='/Script/UMG.Widget:'
PC='/Script/Engine.PlayerController'
GRADE='/Game/FoA/PostProcess/BP_DreamDirector'
FONT='/Game/FoA/UI/Fonts/F_FoA_UI.F_FoA_UI'
VARS=(('DialogueMode','int','0'),('DialogueState','int','0'),('DialogueStep','int','0'),
      ('DialogueSelected','int','0'),('DialoguePrior','int','0'),('DialogueLast','int','0'),
      ('DialogueReady','bool','false'),('DialogueHeld','bool','false'),('DialogueNotes','bool','false'),
      ('DialogueCost','int','0'),('DialogueReply','text',''),('DialoguePlayerLine','text',''),
      ('GamepadNavAt','float','0'),
      ('InterviewComposure','int','100'),('InterviewStageActive','bool','false'),
      ('InterviewHUD','object:'+cls(UI),''))
SIG={n:[] for n in ('EnsureDialogue','BeginStopContact','FinishStopContact','RenderDialogue','RenderContact',
    'RenderInterview','RenderDialogueFeedback','DialogueConfirm','DialogueRelease','DialogueUnlock',
    'DialogueAdvance','ApplyDialogueAnswer','ApplyContactAnswer','ApplyInterviewAnswer','HideDialogue',
    'ReleaseDialogue','StageInterview','InterviewWon','InterviewLost','UnlockStopTask','ToggleDialogueNotes')}
SIG.update(DialogueSelect=[('Index','int')],DialogueMove=[('Delta','int')],GamepadDialogueMove=[('Delta','int')],DialogueClick=[('Index','int')])
SIG.update({f'RenderInterview{i}':[] for i in range(6)})
SIG.update({f'AnswerInterview{i}':[] for i in range(6)})
SIG.update(SayCharacter=[('Text','text'),('Speaker','int'),('Emotion','int')],StopCharacterVoice=[])
FIELDS=('Speaker','Question','Answer0','Answer1','Answer2','Evidence','Status','Hint')


def declare(path,functions,variables=()):
    info=call('blueprint_get_info',path=path);have={v['name'] for v in info['variables']}
    known=set(info['functions'])
    if any(row.get('path') in ('functions','variables') for row in info.get('_truncated',[])):
        script='\n'.join(('import unreal,json',f'bp=unreal.load_asset({path!r})',
            'cdo=unreal.get_default_object(bp.generated_class())',
            'have=[]',f'for name in {[v[0] for v in variables]!r}:',
            ' try: cdo.get_editor_property(name);have.append(name)',
            ' except Exception: pass',
            'print(json.dumps(dict(functions=[str(g.get_name()) for g in unreal.BlueprintEditorLibrary.list_graphs(bp)],variables=have)))'))
        complete=json.loads(call('python_run',script=script)['stdout'].strip())
        known.update(complete['functions']);have.update(complete['variables'])
    for name,typ,value in variables:
        if name not in have:call('blueprint_add_variable',path=path,variable_name=name,variable_type=typ,default_value=value,category='Conversation')
    for name,inputs in functions.items():
        if name not in known:call('blueprint_add_function',path=path,function_name=name,inputs=[dict(name=n,type=t) for n,t in inputs])
    call('blueprint_compile',path=path,save=True)


def skeleton():
    if not h.call('blueprint_get_info',{'path':UI}).get('ok'):
        call('ui_create_widget',path=D.ROOT,name='WBP_L2Interview')
    declare(UI,{'Refresh':[(n,'text') for n in FIELDS]+[('Selected','int'),('Count','int'),('CanChoose','bool')],
                'Click':[('Index','int')],'Hover':[('Index','int')]},[('Journey','object:'+cls(BP),'')])
    declare(BP,SIG,VARS)


def widget():
    # One dialogue surface, reused at contacts and interview. Text is the action;
    # no icon cards, borrowed clothing motifs, UI dividers or new art assets.
    existing=call('ui_query',path=UI,name_pattern='ConversationPanel').get('matches',[])
    if not existing:
        def label(name,size,text=''):
            return dict(name=name,**{'class':'TextBlock'},properties=dict(Text=text,AutoWrapText=True,
                Font={'FontObject':FONT,'TypefaceFontName':'SemiBold','Size':size},
                ColorAndOpacity={'SpecifiedColor':[.95,.95,.93,1]}))
        def slot(x,y,w,height):return dict(anchors_min=[0,1],anchors_max=[0,1],alignment=[0,1],position=[x,y],size=[w,height])
        tree=[dict(name='ConversationPanel',**{'class':'Border'},slot_props=slot(48,-42,1260,570),
                   properties={'BrushColor':[.008,.01,.016,.88],'Visibility':'HitTestInvisible'}),
              dict(name='EvidencePanel',**{'class':'Border'},slot_props=slot(1336,-66,488,438),
                   properties={'BrushColor':[.008,.01,.016,.88],'Visibility':'HitTestInvisible'})]
        for name,size,position in [('Speaker',30,(80,-552,1160,42)),('Question',30,(80,-360,1160,176)),
                                   ('Status',22,(80,-618,1120,36)),('Evidence',22,(1360,-90,440,390)),
                                   ('Hint',20,(80,-56,1160,36))]:
            node=label('Txt_'+name,size);node['slot_props']=slot(*position);tree.append(node)
        for index,y in enumerate((-270,-184,-98)):
            child=label('Txt_Answer'+str(index),27)
            tree.append(dict(name='Btn_Answer'+str(index),**{'class':'Button'},slot_props=slot(72,y,1200,78),
                properties={'IsFocusable':False,'BackgroundColor':[.12,.13,.15,.6],
                            'WidgetStyle':'(Normal=(DrawAs=NoDrawType),Hovered=(DrawAs=NoDrawType),Pressed=(DrawAs=NoDrawType))'},
                children=[dict(name='AnswerPad'+str(index),**{'class':'Border'},
                    properties={'BrushColor':[0,0,0,0],'Padding':[12,8,12,8]},children=[child])]))
        call('ui_build_tree',widget_blueprint_path=UI,parent_widget_name='RootCanvas',tree=tree)
    for name in ('ConversationEdge','SpeakerBack','SpeakerTag'):
        if not call('ui_query',path=UI,name_pattern=name).get('matches'):
            call('ui_build_tree',widget_blueprint_path=UI,parent_widget_name='RootCanvas',tree=[
                dict(name=name,**{'class':'Border'},properties=dict(BrushColor=[1,1,1,1],Visibility='HitTestInvisible'))])
    for name in ('ConversationEdge','ConversationPanel','SpeakerBack','SpeakerTag','EvidencePanel',*('Txt_'+field for field in FIELDS),*('Btn_Answer'+str(i) for i in range(3)),*('AnswerPad'+str(i) for i in range(3))):
        call('ui_set_variable',widget_blueprint_path=UI,widget_name=name,is_variable=True)
    call('ui_compile_widget',widget_blueprint_path=UI);call('ui_save_widget',widget_blueprint_path=UI)


def guard(g,condition):
    branch=g.branch(condition);g.side(branch);return branch


def eq(g,name,value):return g.math('EqualEqual_IntInt',A=g.getv(name),B=value)
def textvalue(g,value):return g.f('/Script/Engine.KismetTextLibrary:Conv_StringToText',InString=value)
def num(g,value):return g.f('/Script/Engine.KismetStringLibrary:Conv_IntToString',InInt=value)
def cat(g,a,b):return g.f('/Script/Engine.KismetStringLibrary:Concat_StrStr',A=a,B=b)
def timer(g,fn,seconds=D.SETTLE_SECONDS):g.do(SL+'K2_SetTimer',FunctionName=fn,Time=seconds,bLooping=False)
def valid(g,obj):return guard(g,g.f(SL+'IsValid',Object=obj))


def display(g,speaker,question,answers=(),evidence='',hint=None,voice_text=None,emotion=0):
    status=cat(g,'Employability ',num(g,g.getv('Employability')))
    interview=eq(g,'DialogueMode',3)
    full=cat(g,cat(g,status,'     Composure '),num(g,g.getv('InterviewComposure')))
    status=g.math('SelectString',A=full,B=status,bPickA=interview)
    args={field:'' for field in FIELDS}
    # level2 2026-11-18: no footer hint in the interview (the coordinator's minimal-UI call).
    args.update(Speaker=speaker,Question=question,Evidence=evidence,Status=textvalue(g,status),Hint=hint or '')
    for i,answer in enumerate(answers):args['Answer'+str(i)]=answer
    # Literal text pins accept text directly; dynamic tuples already contain FText.
    g.do(cls(UI)+':Refresh',self=g.getv('InterviewHUD'),**args,Selected=g.getv('DialogueSelected'),
         Count=len(answers),CanChoose=g.getv('DialogueReady'))
    voice=g.math('SelectInt',A=4,B=g.math('Add_IntInt',A=g.getv('Stop'),B=1),bPickA=interview)
    g.own('SayCharacter',Text=question if voice_text is None else voice_text,Speaker=voice,Emotion=emotion)


def refresh_widget():
    g=G(UI,'Refresh')
    for field in FIELDS:g.do(TB+'SetText',self=g.getv('Txt_'+field),InText=g.arg(field))
    single=g.math('EqualEqual_IntInt',A=g.arg('Count'),B=1)
    def layout(name,x,y,height=None,width=None):
        slot=g.f('/Script/UMG.WidgetLayoutLibrary:SlotAsCanvasSlot',Widget=g.getv(name))
        g.do('/Script/UMG.CanvasPanelSlot:SetPosition',self=slot,InPosition=g.math('MakeVector2D',X=x,Y=y))
        if height is not None:g.do('/Script/UMG.CanvasPanelSlot:SetSize',self=slot,InSize=g.math('MakeVector2D',X=width,Y=height))
    choose=lambda a,b:g.math('SelectFloat',A=a,B=b,bPickA=single)
    layout('ConversationEdge',16,-18,choose(352,392),16)
    layout('ConversationPanel',24,-26,choose(336,376),24)
    layout('SpeakerBack',44,choose(-334,-374))
    layout('SpeakerTag',40,choose(-344,-384))
    layout('Txt_Speaker',96,choose(-350,-390))
    layout('Txt_Question',96,choose(-154,-300),choose(176,72),96)
    layout('Txt_Hint',96,-40,32,96)
    layout('Btn_Answer0',56,choose(-84,-226),choose(56,64),92)
    evidence=g.f('/Script/Engine.KismetTextLibrary:Conv_TextToString',InText=g.arg('Evidence'))
    length=g.f('/Script/Engine.KismetStringLibrary:Len',S=evidence)
    alpha=g.math('SelectFloat',A=1.,B=0.,bPickA=g.math('Greater_IntInt',A=length,B=0))
    g.do(UW+'SetRenderOpacity',self=g.getv('EvidencePanel'),InOpacity=alpha)
    for i in range(3):
        button=g.getv('Btn_Answer'+str(i));label=g.getv('Txt_Answer'+str(i))
        show=g.math('Less_IntInt',A=i,B=g.arg('Count'))
        # Visibility enums use explicit branches to avoid unsafe int-to-enum wiring.
        branch=g.branch(show);g.side(branch)
        g.do(UW+'SetVisibility',self=button,InVisibility='Visible')
        g.side(branch,False);g.do(UW+'SetVisibility',self=button,InVisibility='Collapsed')
        join=g.do(UW+'SetIsEnabled',self=button,bInIsEnabled=g.arg('CanChoose'))
        # Join both visibility branches before selection styling.
        true_set=next(o['to_node'] for o in reversed(g.ops) if o.get('from_node')==branch and o.get('from_pin')=='then')
        g.link(true_set,'then',join[0],'execute')
        selected=g.math('EqualEqual_IntInt',A=g.arg('Selected'),B=i)
        alpha=g.math('SelectFloat',A=1.,B=.95,bPickA=selected)
        g.do(UW+'SetRenderOpacity',self=label,InOpacity=alpha)
        nudge=g.math('SelectFloat',A=12,B=0,bPickA=selected)
        g.do(UW+'SetRenderTranslation',self=button,Translation=g.math('MakeVector2D',X=nudge,Y=0))
        texture=g.math('SelectObject',A='/Game/FoA/Level2/UI/T_L2InkTag.T_L2InkTag',B='/Game/FoA/Level2/UI/T_L2InkPanel.T_L2InkPanel',bSelectA=selected)
        texture=g.cast(texture,'/Script/Engine.Texture2D','Texture 2D')
        g.do('/Script/UMG.Border:SetBrushFromTexture',self=g.getv('AnswerPad'+str(i)),Texture=texture)
        tint=g.math('SelectColor',A='(R=.62,G=0,B=0,A=1)',B='(R=1,G=1,B=1,A=1)',bPickA=selected)
        g.do('/Script/UMG.Border:SetBrushColor',self=g.getv('AnswerPad'+str(i)),InBrushColor=tint)
    g.finish()


def widget_click():
    g=G(UI,'Click');valid(g,g.getv('Journey'));g.do(cls(BP)+':DialogueClick',self=g.getv('Journey'),Index=g.arg('Index'));g.finish()


def widget_hover():
    g=G(UI,'Hover');valid(g,g.getv('Journey'));g.do(cls(BP)+':DialogueSelect',self=g.getv('Journey'),Index=g.arg('Index'));g.finish()


def ensure():
    g=G(BP,'EnsureDialogue')
    exists=g.branch(g.f(SL+'IsValid',Object=g.getv('InterviewHUD')));g.side(exists,False)
    r=g.ref();g.node(r,'create_widget',0,0);g.put(r,'Class',cls(UI));g.put(r,'OwningPlayer',g.f(GS+'GetPlayerController',PlayerIndex=0))
    g.chain(g.tail,r);g.tail=r;g.setv('InterviewHUD',(r,'ReturnValue'))
    j.external(g,'Journey',j.me(g),g.getv('InterviewHUD'),cls(UI))
    # The existing HUD is always valid after StartJourney. Both branches join.
    joined=g.do(UW+'SetVisibility',self=g.getv('HUD'),InVisibility='Collapsed');g.link(exists,'then',joined[0],'execute')
    missing=g.branch(g.math('Not_PreBool',A=g.f('/Script/UMG.UserWidget:IsInViewport',self=g.getv('InterviewHUD'))));g.side(missing)
    g.do('/Script/UMG.UserWidget:AddToViewport',self=g.getv('InterviewHUD'),ZOrder=40)
    g.side(missing,False)
    pc=g.f(GS+'GetPlayerController',PlayerIndex=0)
    mode=g.do('/Script/UMG.WidgetBlueprintLibrary:SetInputMode_GameAndUIEx',PlayerController=pc,bHideCursorDuringCapture=False)
    added=next(o['to_node'] for o in reversed(g.ops) if o.get('from_node')==missing and o.get('from_pin')=='then')
    g.link(added,'then',mode[0],'execute')
    j.external(g,'bShowMouseCursor',True,pc,PC)
    g.own('EnableConfirm');g.finish()


def begin_contact(after=False):
    g=G(BP,'FinishStopContact' if after else 'BeginStopContact');j.phase(g,4)
    g.setv('DialogueMode',2 if after else 1);g.setv('DialogueState',0);g.setv('DialogueSelected',0)
    g.setv('DialogueHeld',False);g.setv('DialogueReady',False)
    g.setv('StopActionState',3 if after else 0)
    g.own('EnsureDialogue');g.own('RenderDialogue');timer(g,'DialogueUnlock');g.finish()


def render_contact():
    g=G(BP,'RenderContact')
    for index,row in enumerate(D.CONTACTS):
        branch=g.branch(eq(g,'Stop',index));g.side(branch)
        after=g.branch(eq(g,'DialogueMode',2));g.side(after)
        display(g,row['speaker'],row['debrief'],[x['text'] for x in row['responses']])
        g.side(after,False);display(g,row['speaker'],row['question'],[x['text'] for x in row['choices']])
        g.side(branch,False)
    g.finish()


def render_question(index,job_hunt=False):
    import job_boss_data
    data=job_boss_data if job_hunt else D
    g=G(BP,'RenderInterview'+str(index));row=data.SECTIONS[index//2]
    # The advice panel shows only on the notes-open retry; otherwise the screen is the question and three answers.
    note=g.math('SelectString',A=data.NOTES[index//2],B='',bPickA=g.getv('DialogueNotes'))
    if job_hunt and index < 2:
        from job_hunt_data import JOBS
        evidence=''
        for i,job in enumerate(JOBS):
            evidence=g.math('SelectString',A=job.evidence,B=evidence,bPickA=g.getv(f'Edited{i}'))
        note=g.math('SelectString',A=cat(g,'From your C.V.\n',evidence),B=note,bPickA=g.getv('DialogueNotes'))
    if index%2:
        for variant in range(3):
            branch=g.branch(eq(g,'DialoguePrior',variant));g.side(branch)
            follow=row['followups'][variant]
            display(g,'Interviewer',follow['question'],[x['text'] for x in follow['choices']],textvalue(g,note))
            g.side(branch,False)
    else:display(g,'Interviewer',row['question'],[x['text'] for x in row['choices']],textvalue(g,note))
    g.finish()


def render_interview():
    g=G(BP,'RenderInterview')
    for i in range(6):
        branch=g.branch(eq(g,'DialogueStep',i));g.side(branch);g.own('RenderInterview'+str(i));g.side(branch,False)
    g.finish()


def feedback():
    g=G(BP,'RenderDialogueFeedback')
    player=g.f('/Script/Engine.KismetTextLibrary:Conv_TextToString',InText=g.getv('DialoguePlayerLine'))
    reply=g.f('/Script/Engine.KismetTextLibrary:Conv_TextToString',InText=g.getv('DialogueReply'))
    body=textvalue(g,cat(g,cat(g,cat(g,'You: ',player),'\n\n'),reply))
    speaker=D.CONTACTS[0]['speaker']
    for index in (1,2):speaker=g.math('SelectString',A=D.CONTACTS[index]['speaker'],B=speaker,bPickA=eq(g,'Stop',index))
    speaker=g.math('SelectString',A='Interviewer',B=speaker,bPickA=eq(g,'DialogueMode',3))
    display(g,textvalue(g,speaker),body,['Continue.'],hint='',
            voice_text=g.getv('DialogueReply'),emotion=1)
    g.finish()


def render(job_hunt=False):
    g=G(BP,'RenderDialogue');valid(g,g.getv('InterviewHUD'))
    job=guard(g,g.math('GreaterEqual_IntInt',A=g.getv('DialogueMode'),B=4));g.own('RenderJob');g.side(job,False)
    response=g.branch(eq(g,'DialogueState',1));g.side(response);g.own('RenderDialogueFeedback')
    g.side(response,False);lost=g.branch(eq(g,'DialogueState',2));g.side(lost)
    display(g,'Interviewer','Let us stop here. Read what you have, then tell me what you can stand behind.',
            ['Try the interview again.','Try again with my notes open.'],
            '' if job_hunt else 'Three notes kept.\nRetry with notes open to review the advice for each question.',
            hint='' if job_hunt else 'Your three stop notes and 60 employability are kept. Choose how to retry.')
    g.side(lost,False);won=g.branch(eq(g,'DialogueState',3));g.side(won)
    display(g,'Interviewer','You’ve given me enough. We open at six on Monday. Can you be here?' if job_hunt else
            'I have what I need. This is an application, not an offer. Send it when you are ready.',
            ['I’ll be there.' if job_hunt else 'Submit my application.'],hint='' if job_hunt else 'The interview is complete. Your application is ready to send.')
    g.side(won,False);interview=g.branch(eq(g,'DialogueMode',3));g.side(interview);g.own('RenderInterview')
    g.side(interview,False);g.own('RenderContact');g.finish()


def select():
    g=G(BP,'DialogueSelect');guard(g,g.math('Greater_IntInt',A=g.getv('DialogueMode'),B=0));guard(g,g.getv('DialogueReady'))
    maximum=g.math('SelectInt',A=1,B=2,bPickA=eq(g,'DialogueState',2))
    single=g.math('BooleanOR',A=eq(g,'DialogueState',1),B=eq(g,'DialogueState',3))
    maximum=g.math('SelectInt',A=0,B=maximum,bPickA=single)
    chosen=g.math('Clamp',Value=g.arg('Index'),Min=0,Max=maximum)
    guard(g,g.math('NotEqual_IntInt',A=chosen,B=g.getv('DialogueSelected')))
    g.setv('DialogueSelected',chosen)
    g.do(GS+'PlaySound2D',Sound='/Game/FoA/Audio/SFX/UI_FrontEnd/SFX_FE_Select.SFX_FE_Select',VolumeMultiplier=.3,bIsUISound=True)
    g.own('RenderDialogue');g.finish()


def move():
    g=G(BP,'DialogueMove');g.own('DialogueSelect',Index=g.math('Add_IntInt',A=g.getv('DialogueSelected'),B=g.arg('Delta')));g.finish()


def pad_move():
    g=G(BP,'GamepadDialogueMove')
    now=g.f(GS+'GetRealTimeSeconds')
    guard(g,g.math('GreaterEqual_DoubleDouble',A=now,B=g.getv('GamepadNavAt')))
    g.setv('GamepadNavAt',g.math('Add_DoubleDouble',A=now,B=.24))
    g.own('DialogueMove',Delta=g.arg('Delta'));g.finish()


def click():
    g=G(BP,'DialogueClick');g.own('DialogueSelect',Index=g.arg('Index'));g.own('DialogueConfirm');g.own('DialogueRelease');g.finish()


def confirm():
    g=G(BP,'DialogueConfirm');guard(g,g.math('Greater_IntInt',A=g.getv('DialogueMode'),B=0))
    guard(g,g.math('BooleanAND',A=g.getv('DialogueReady'),B=g.math('Not_PreBool',A=g.getv('DialogueHeld'))))
    g.setv('DialogueReady',False);g.setv('DialogueHeld',True)
    g.do(GS+'PlaySound2D',Sound='/Game/FoA/Audio/SFX/UI_FrontEnd/SFX_FE_Confirm.SFX_FE_Confirm',VolumeMultiplier=.4,bIsUISound=True)
    job=guard(g,g.math('GreaterEqual_IntInt',A=g.getv('DialogueMode'),B=4));g.own('ConfirmJob');g.side(job,False)
    question=g.branch(eq(g,'DialogueState',0));g.side(question);g.own('ApplyDialogueAnswer')
    g.side(question,False);feedback=g.branch(eq(g,'DialogueState',1));g.side(feedback);g.own('DialogueAdvance')
    g.side(feedback,False);lost=g.branch(eq(g,'DialogueState',2));g.side(lost)
    g.setv('Assisted',eq(g,'DialogueSelected',1));g.own('StartFinale')
    g.side(lost,False);won=g.branch(eq(g,'DialogueState',3));g.side(won);g.own('Submit')
    g.finish()


def release():
    g=G(BP,'DialogueRelease');g.setv('DialogueHeld',False);g.finish()


def unlock():
    g=G(BP,'DialogueUnlock');guard(g,g.math('Greater_IntInt',A=g.getv('DialogueMode'),B=0))
    g.setv('DialogueReady',True);g.own('RenderDialogue');g.finish()


def assign_answer(g,row):
    for choice,answer in enumerate(row['choices']):
        picked=g.branch(eq(g,'DialogueSelected',choice));g.side(picked)
        g.setv('DialoguePlayerLine',answer['text']);g.setv('DialogueReply',answer['reply']);g.setv('DialogueCost',answer.get('cost',0))
        g.side(picked,False)


def apply_question(index,job_hunt=False):
    import job_boss_data
    g=G(BP,'AnswerInterview'+str(index));row=(job_boss_data.SECTIONS if job_hunt else D.SECTIONS)[index//2]
    if index%2:
        for variant in range(3):
            branch=g.branch(eq(g,'DialoguePrior',variant));g.side(branch);assign_answer(g,row['followups'][variant]);g.side(branch,False)
    else:assign_answer(g,row)
    g.finish()


def apply_interview():
    g=G(BP,'ApplyInterviewAnswer')
    # A helper per authored turn keeps branch graphs bounded and reviewable.
    for i in range(6):
        branch=g.branch(eq(g,'DialogueStep',i));g.side(branch);g.own('AnswerInterview'+str(i))
        if i%2==0:g.setv('DialoguePrior',g.getv('DialogueSelected'))
        g.setv('InterviewComposure',g.math('Max',A=0,B=g.math('Subtract_IntInt',A=g.getv('InterviewComposure'),B=g.getv('DialogueCost'))))
        g.setv('DialogueStep',i+1)
        g.side(branch,False)
    g.finish()


def apply_contact():
    g=G(BP,'ApplyContactAnswer')
    for index,row in enumerate(D.CONTACTS):
        branch=g.branch(eq(g,'Stop',index));g.side(branch)
        after=g.branch(eq(g,'DialogueMode',2));g.side(after);assign_answer(g,dict(choices=row['responses']))
        g.side(after,False);assign_answer(g,row)
        g.side(branch,False)
    g.finish()


def apply_answer():
    g=G(BP,'ApplyDialogueAnswer');g.setv('DialogueLast',g.getv('DialogueSelected'))
    interview=g.branch(eq(g,'DialogueMode',3));g.side(interview)
    g.own('ApplyInterviewAnswer');first=g.own('InterviewReact',Cost=g.getv('DialogueCost'))  # level2 round 3
    g.side(interview,False);second=g.own('ApplyContactAnswer')
    g.setv('DialogueState',1);join=g.tail;g.link(first[0],'then',join,'execute')
    g.setv('DialogueSelected',0);g.own('RenderDialogue');timer(g,'DialogueUnlock');g.finish()


def advance(job_hunt=False):
    g=G(BP,'DialogueAdvance')
    intro=g.branch(eq(g,'DialogueMode',1));g.side(intro)
    g.own('HideDialogue');g.setv('DialogueMode',0);g.setv('StopActionState',1);g.setv('StopBusy',True)
    timer(g,'UnlockStopTask')
    g.side(intro,False);debrief=g.branch(eq(g,'DialogueMode',2));g.side(debrief)
    g.own('HideDialogue');g.setv('DialogueMode',0);g.own('PreviewRejection')
    g.side(debrief,False);dead=g.branch(g.math('LessEqual_IntInt',A=g.getv('InterviewComposure'),B=0));g.side(dead);g.own('InterviewLost')
    g.side(dead,False);done=g.branch(g.math('GreaterEqual_IntInt',A=g.getv('DialogueStep'),B=6));g.side(done);g.own('InterviewWon')
    g.side(done,False)
    if not job_hunt:g.setv('Employability',g.math('Add_IntInt',A=60,B=g.math('Divide_IntInt',A=g.math('Multiply_IntInt',A=40,B=g.getv('DialogueStep')),B=6)))
    j.baseline(g);g.own('RefreshProgressDisplays');g.setv('DialogueState',0);g.setv('DialogueSelected',0)
    g.own('RenderDialogue');timer(g,'DialogueUnlock');g.finish()


def unlock_task():
    g=G(BP,'UnlockStopTask');j.phase(g,4);g.setv('StopBusy',False)
    for index,row in enumerate(D.CONTACTS):
        branch=g.branch(eq(g,'Stop',index));g.side(branch)
        j.text(g,row['speaker'],row['task'],'E or gamepad A to '+JD.SCENES[index]['action'].lower());g.side(branch,False)
    g.finish()


def hide():
    g=G(BP,'HideDialogue');g.own('StopCharacterVoice');valid(g,g.getv('InterviewHUD'))
    g.do(UW+'RemoveFromParent',self=g.getv('InterviewHUD'))
    g.do(UW+'SetVisibility',self=g.getv('HUD'),InVisibility='Visible')
    pc=g.f(GS+'GetPlayerController',PlayerIndex=0);j.external(g,'bShowMouseCursor',False,pc,PC)
    g.do('/Script/UMG.WidgetBlueprintLibrary:SetInputMode_GameOnly',PlayerController=pc,bFlushInput=False);g.finish()


def cleanup():
    g=G(BP,'ReleaseDialogue')
    for fn in ('DialogueUnlock','StageInterview','UnlockStopTask'):g.do(SL+'K2_ClearTimer',FunctionName=fn)
    g.own('ClearJob')
    g.setv('DialogueMode',0);g.setv('DialogueHeld',False);g.setv('DialogueReady',False);g.setv('InterviewStageActive',False)
    g.own('HideDialogue');g.finish()


def start_interview(job_hunt=False):
    g=G(BP,'StartFinale')
    allowed=g.math('BooleanOR',A=eq(g,'Phase',11),B=eq(g,'Phase',7));guard(g,allowed)
    if job_hunt:
        from job_hunt_data import BOSS_MINIMUM
        from job_boss_data import STARTING_COMPOSURE
        guard(g,g.math('GreaterEqual_IntInt',A=g.getv('Employability'),B=BOSS_MINIMUM))
    else:
        STARTING_COMPOSURE=100
        guard(g,g.math('BooleanAND',A=g.getv('Edited0'),B=g.math('BooleanAND',A=g.getv('Edited1'),B=g.getv('Edited2'))))
        g.setv('Employability',60)
    g.setv('Phase',6);g.setv('StopBusy',True);g.setv('InterviewComposure',STARTING_COMPOSURE)
    g.setv('DialogueMode',3);g.setv('DialogueState',0);g.setv('DialogueStep',0);g.setv('DialoguePrior',0)
    g.setv('DialogueSelected',0);g.setv('DialogueReady',False);g.setv('DialogueNotes',g.getv('Assisted'))
    g.own('HideDialogue');g.own('DisableConfirm');j.cinematic(g,True);g.own('ApplyMerge',Amount=.6)
    if job_hunt:g.own('ResetInterviewRoom')  # level2 round 3: a retry starts from a quiet room
    j.stop_fade(g,0,1,.4);timer(g,'StageInterview',.45);g.finish()


def stage():
    g=G(BP,'StageInterview');j.phase(g,6)
    valid(g,g.getv('StopSet'))
    already=g.branch(g.getv('InterviewStageActive'));g.side(already,False)
    j.stop_call(g,'PrepareInterview');g.setv('InterviewStageActive',True)
    g.setv('StopBusy',False);g.link(already,'then',g.tail,'execute')
    g.setv('DialogueHeld',False)
    grade=g.do(GS+'GetActorOfClass',ActorClass=cls(GRADE));grade=g.cast(grade,cls(GRADE),'BP Dream Director')
    g.do(cls(GRADE)+':SetColorReveal',self=grade,Amount=1.,BlendSeconds=.6)
    g.own('SetMusic',Track='Dream');g.own('EnsureDialogue');g.own('RenderDialogue')
    j.stop_fade(g,1,0,.6);timer(g,'DialogueUnlock',.8);g.finish()


def won():
    g=G(BP,'InterviewWon');j.phase(g,6)
    g.setv('Employability',100);g.setv('FinaleComplete',True);g.setv('Phase',8)
    g.setv('DialogueState',3);g.setv('DialogueSelected',0);g.own('ApplyMerge',Amount=1.)
    g.own('RefreshProgressDisplays');g.own('RenderDialogue');timer(g,'DialogueUnlock');g.finish()


def lost(job_hunt=False):
    g=G(BP,'InterviewLost');j.phase(g,6)
    if not job_hunt:g.setv('Employability',60)
    g.setv('Phase',7);g.setv('DialogueState',2);g.setv('DialogueSelected',0)
    g.own('ApplyMerge',Amount=.6);g.own('RefreshProgressDisplays');g.own('RenderDialogue');timer(g,'DialogueUnlock');g.finish()


def toggle_notes():
    g=G(BP,'ToggleDialogueNotes');guard(g,eq(g,'DialogueMode',3))
    g.setv('DialogueNotes',g.math('Not_PreBool',A=g.getv('DialogueNotes')));g.own('RenderDialogue');g.finish()


GRAPHS=dict(EnsureDialogue=ensure,BeginStopContact=lambda:begin_contact(False),FinishStopContact=lambda:begin_contact(True),
    RenderDialogue=render,RenderContact=render_contact,RenderInterview=render_interview,RenderDialogueFeedback=feedback,
    DialogueSelect=select,DialogueMove=move,DialogueClick=click,DialogueConfirm=confirm,DialogueRelease=release,DialogueUnlock=unlock,
    ApplyDialogueAnswer=apply_answer,ApplyInterviewAnswer=apply_interview,ApplyContactAnswer=apply_contact,DialogueAdvance=advance,
    HideDialogue=hide,ReleaseDialogue=cleanup,StageInterview=stage,InterviewWon=won,InterviewLost=lost,GamepadDialogueMove=pad_move,
    UnlockStopTask=unlock_task,ToggleDialogueNotes=toggle_notes)
for _i in range(6):
    GRAPHS['RenderInterview'+str(_i)]=lambda i=_i:render_question(i)
    GRAPHS['AnswerInterview'+str(_i)]=lambda i=_i:apply_question(i)
STEPS=dict(skeleton=skeleton,widget=widget,widget_refresh=refresh_widget,widget_click=widget_click,widget_hover=widget_hover,**GRAPHS)
STEPS['bindings']=lambda:call('python_exec_file',path='P:/FoA/Tools/Unreal/level2/interview_setup.py',env={},resources=['asset:'+BP,'asset:'+UI])


if __name__=='__main__':
    owner='main-level2-interview';os.environ.update(FOA_AGENT=owner,HAYBA_AGENT_ID=owner,FOA_CALLER=owner)
    editor_lock.acquire(owner,wait_s=5,ttl=120,areas=[BP,UI])
    try:
        assert not call('editor_get_state')['pie_running'];STEPS[sys.argv[1]]()
        for path in (BP,UI):
            compiled=call('blueprint_compile',path=path,save=True)
            assert not compiled.get('error_count',0) and not compiled.get('warning_count',0),compiled
    finally:editor_lock.release(owner)
