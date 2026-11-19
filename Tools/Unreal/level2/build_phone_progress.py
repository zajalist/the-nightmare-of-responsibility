"""Add Level 2 phone context and bars in place, preserving original L1 graph paths.

Offline imports are safe. Native steps require the coordinator's writer grant.
Build skeleton, tree, phone bodies, progress bodies, journey bodies, then hooks
AFTER the Journey owner's final graph rebuild. Structural key bindings are in
phone_progress_setup.py and never clear the existing Journey event graph.
"""
import os
import sys
from pathlib import Path
sys.path[:0] = [str(Path(__file__).parent), 'P:/FoA/Tools/Unreal/player', 'P:/FoA/Tools/Unreal']
import build_drive as b
from build_drive import G, call, cls, GS, SL, A
from held_tool_graphs import Batch, inspect
from build_cv import norm
import phone_progress_data as D

PHONE = '/Game/FoA/UI/Game/BP_Phone'
WIDGET = '/Game/FoA/UI/Game/WBP_Phone'
JOURNEY = '/Game/FoA/Level2/Journey/BP_L2Journey'
JHUD = '/Game/FoA/Level2/Journey/WBP_L2Journey'
BATTLE = '/Game/FoA/Gameplay/Encounter/WBP_Encounter'
ENCOUNTER = '/Game/FoA/Gameplay/Encounter/BP_Encounter'
FRONT = '/Game/FoA/UI/Framework/BP_FoAFrontEnd'
PLAYER = '/Game/FoA/Characters/Player/BP_FoAPlayer'
SAND_BUTTON = '/Game/FoA/UI/Widgets/Common/WBP_SandButton'
TB = '/Script/UMG.TextBlock:'
UW = '/Script/UMG.Widget:'
TEXT = '/Script/Engine.KismetTextLibrary:'
STR = '/Script/Engine.KismetStringLibrary:'
PB = '/Script/UMG.ProgressBar:'
FONT = '/Game/FoA/UI/Fonts/F_FoA_UI.F_FoA_UI'
CACHED_TEXT = ('Txt_Notif0Body', 'Txt_Notif1Body', 'Txt_Sender0', 'Txt_Sender1', 'Txt_Sender2', 'Heading_Messages',
               'Txt_Message','Txt_ThreadName')
INK_BORDERS=('Brd_Screen','Brd_Bubble')
WIDGETS = (WIDGET, JHUD, b.HUD, BATTLE)


def declare(path, functions, variables=()):
    info = call('blueprint_get_info', path=path)
    have = {v['name'] for v in info['variables']}
    for name, typ, default in variables:
        if name not in have:
            call('blueprint_add_variable', path=path, variable_name=name, variable_type=typ,
                 default_value=default, category='Level 2 phone')
    for name, inputs in functions.items():
        if name not in info['functions']:
            call('blueprint_add_function', path=path, function_name=name,
                 inputs=[dict(name=n,type=t) for n,t in inputs])
    call('blueprint_compile', path=path, save=True)


def skeleton():
    declare(WIDGET, {**{n:[] for n in ('ResolveL2Phone','CacheL1Phone','RestoreL1Phone','RefreshL2Phone','CloseL2Phone')},
                    'OpenL2Message':[('Index','int')]},
            [('L2Journey','object:'+cls(JOURNEY),''),('bL2Phone','bool','false'),('bL1PhoneCached','bool','false'),
             ('SavedPhonePage','int','0'),('SavedMessageIndex','int','0'),('SavedReadingMessage','bool','false')]
            + [('Saved'+n,'text','') for n in CACHED_TEXT]
            + [('Saved'+name+'Brush','struct:/Script/SlateCore.SlateBrush','') for name in INK_BORDERS])
    for path in WIDGETS:
        declare(path, {'RefreshL2Progress':[('Value','int'),('Show','bool')]})
    declare(BATTLE, {'RefreshL2ProgressContext':[]})
    declare(PHONE, {'NotifyL2PhoneClosed':[]})
    declare(FRONT, {'RestoreL2PhoneHUD':[]})
    declare(JOURNEY, {n:[] for n in ('OpenPhone','PhoneClosed','RefreshProgressDisplays','ClearPhoneContext',
                                    'RefreshJourneyProgress','RefreshCarProgress','RefreshPhoneProgress','RefreshBattleProgress',
                                    'NotifyJobHunt')},
            [('PhoneSession','bool','false'),('JobMessageDelivered','bool','false')])
    info=call('blueprint_get_info',path=JOURNEY)
    assert 'StopBusy' in {v['name'] for v in info['variables']}, 'Journey owner must declare StopBusy first'
    if 'CanOpenPhone' not in info['functions']:
        call('blueprint_add_function',path=JOURNEY,function_name='CanOpenPhone',pure=True,const=True,
             outputs=[dict(name='Allowed',type='bool')])
    call('blueprint_compile',path=JOURNEY,save=True)


def bar(name='Bar_L2Employability'):
    return dict(class_='ProgressBar',name=name,properties={
        'Percent':0.,'Visibility':'Collapsed',
        'WidgetStyle':'(BackgroundImage=(DrawAs=Box,TintColor=(SpecifiedColor=(R=.86,G=.86,B=.86,A=.16))),'
                      'FillImage=(DrawAs=Box,TintColor=(SpecifiedColor=(R=1,G=1,B=1,A=1))),MarqueeImage=(DrawAs=NoDrawType))',
        'FillColorAndOpacity':'(R=.86,G=.86,B=.86,A=1)'})


def text_node(name, value='', size=26):
    return {'class':'TextBlock','name':name,'properties':{'Text':value,'AutoWrapText':True,
        'Font':{'FontObject':FONT,'TypefaceFontName':'SemiBold','Size':size},
        'ColorAndOpacity':{'SpecifiedColor':[.9,.9,.9,1]}}}


def tree():
    # The phone has 89 widgets; an unfiltered query is truncated to 50 matches.
    existing={row['name'] for pattern in ('Txt_','Heading_','HB_Task','VB_Tasks','L2CV')
              for row in call('ui_query',path=WIDGET,name_pattern=pattern).get('matches',[])}
    required={*CACHED_TEXT,'VB_Tasks','HB_Task0','HB_Task1','HB_Task2','HB_Task3'}
    assert required<=existing,('Missing phone widgets',sorted(required-existing))
    if 'L2CVBlock' not in existing:
        meter=bar();meter['class']=meter.pop('class_')
        children=[text_node('Txt_L2Employability','Employability 0',24),
            {'class':'SizeBox','name':'Size_L2Employability','properties':{'HeightOverride':5.},
             'slot_props':{'padding':[0,4,0,6]},'children':[meter]}]
        for i,row in enumerate(D.STOPS):
            item=text_node('Txt_L2CV'+str(i),row['truth'],25)
            item['slot_props']={'padding':[0,0,0,4]};children.append(item)
        call('ui_build_tree',widget_blueprint_path=WIDGET,parent_widget_name='VB_Tasks',tree={
            'class':'VerticalBox','name':'L2CVBlock','properties':{'Visibility':'Collapsed'},
            'slot_props':{'padding':[0,0,0,0]},'children':children})
    for n in ('L2CVBlock','Txt_L2Employability','Bar_L2Employability','Txt_L2CV0','Txt_L2CV1','Txt_L2CV2',
              'HB_Task1','HB_Task2','HB_Task3',*CACHED_TEXT,*INK_BORDERS):
        call('ui_set_variable',widget_blueprint_path=WIDGET,widget_name=n,is_variable=True)
    for path, slot in ((JHUD,dict(anchors_min=[0,1],anchors_max=[0,1],alignment=[0,1],position=[48,-404],size=[572,4])),
                       (b.HUD,dict(position=[44,164],size=[392,5])),
                       (BATTLE,dict(anchors_min=[.5,0],anchors_max=[.5,0],alignment=[.5,0],position=[0,94],size=[400,5]))):
        if not call('ui_query',path=path,name_pattern='Bar_L2Employability').get('matches'):
            meter=bar();meter['class']=meter.pop('class_');meter['slot_props']=dict(slot,z_order=3,auto_size=False)
            call('ui_build_tree',widget_blueprint_path=path,parent_widget_name='RootCanvas',tree=meter)
        else:
            call('ui_set_widget_properties',widget_blueprint_path=path,widget_name='Bar_L2Employability',
                 slot_props=dict(slot,z_order=3,auto_size=False))
        call('ui_set_variable',widget_blueprint_path=path,widget_name='Bar_L2Employability',is_variable=True)
    for path in WIDGETS:
        result=call('blueprint_compile',path=path,save=True)
        assert not result.get('error_count') and not result.get('warning_count'),result


def set_text(g, widget, value):
    if isinstance(value, tuple):
        value=g.f(TEXT+'Conv_StringToText',InString=value)
    g.do(TB+'SetText',self=g.getv(widget),InText=value)


def visible(g, widget, show):
    g.do(UW+'SetVisibility',self=g.getv(widget),InVisibility='Visible' if show else 'Collapsed')


def find(g, path, cast_name):
    actor=g.do(GS+'GetActorOfClass',ActorClass=cls(path))
    return g.cast(actor,cls(path),cast_name)


def valid(g, value):
    gate=g.branch(g.f(SL+'IsValid',Object=value));g.side(gate);return gate


def resolve_phone():
    g=G(WIDGET,'ResolveL2Phone');g.setv('bL2Phone',False)
    journey=find(g,JOURNEY,'BP L2Journey');g.setv('L2Journey',journey)
    g.setv('bL2Phone',g.math('Greater_IntInt',A=g.getv('Phase',journey,JOURNEY),B=0));g.finish()


def cache_phone():
    g=G(WIDGET,'CacheL1Phone');gate=g.branch(g.getv('bL1PhoneCached'));g.side(gate,False)
    for name in CACHED_TEXT:g.setv('Saved'+name,g.f(TB+'GetText',self=g.getv(name)))
    for name in INK_BORDERS:
        prop=g.ref();g.get(prop,'Background',0,0,'/Script/UMG.Border');g.put(prop,'self',g.getv(name))
        g.setv('Saved'+name+'Brush',(prop,'Background'))
    for saved,field in (('SavedPhonePage','CurrentPage'),('SavedMessageIndex','MessageIndex'),('SavedReadingMessage','bReadingMessage')):
        g.setv(saved,g.getv(field))
    g.setv('bL1PhoneCached',True)
    g.own('SetPage',Index=0)
    g.finish()


def restore_phone():
    g=G(WIDGET,'RestoreL1Phone');visible(g,'L2CVBlock',False)
    gate=g.branch(g.getv('bL1PhoneCached'));g.side(gate)
    for i in range(1,4):visible(g,'HB_Task'+str(i),True)
    for name in CACHED_TEXT:g.do(TB+'SetText',self=g.getv(name),InText=g.getv('Saved'+name))
    for name in INK_BORDERS:g.do('/Script/UMG.Border:SetBrush',self=g.getv(name),InBrush=g.getv('Saved'+name+'Brush'))
    g.setv('bL1PhoneCached',False)
    g.own('SetPage',Index=g.getv('SavedPhonePage'));g.setv('MessageIndex',g.getv('SavedMessageIndex'))
    reading=g.branch(g.getv('SavedReadingMessage'));g.side(reading)
    g.own('OpenMessage',Index=g.getv('SavedMessageIndex'));g.finish()


def refresh_phone():
    g=G(WIDGET,'RefreshL2Phone');g.own('CacheL1Phone');journey=g.getv('L2Journey');valid(g,journey)
    for name in INK_BORDERS:g.do('/Script/UMG.Border:SetBrushFromTexture',self=g.getv(name),Texture='/Game/FoA/Level2/UI/T_L2InkPanel.T_L2InkPanel')
    visible(g,'L2CVBlock',True)
    for i in range(1,4):visible(g,'HB_Task'+str(i),False)
    set_text(g,'Txt_Task0',D.GOAL)
    g.do(UW+'SetRenderOpacity',self=g.getv('Txt_Task0'),InOpacity=1.)
    g.own('ShowRowCheck',Index=0,Done=False)
    for i,row in enumerate(D.STOPS):
        line=g.math('SelectString',A=D.PHONE_REVISIONS[i],B=row['truth'],
                    bPickA=g.getv('Edited'+str(i),journey,JOURNEY))
        set_text(g,'Txt_L2CV'+str(i),line)
    set_text(g,'Txt_Notif0Body',D.MOM);set_text(g,'Txt_Notif1Body','Drop-in appointments')
    set_text(g,'Heading_Messages','Messages')
    for i,(sender,body) in enumerate(D.MESSAGES):set_text(g,'Txt_Sender'+str(i),sender+'\n'+body)
    day=g.math('Add_IntInt',A=g.getv('RoadAttempts',journey,JOURNEY),B=1)
    set_text(g,'Txt_DayNum',g.f(STR+'Conv_IntToString',InInt=day))
    set_text(g,'Txt_Crossed',g.f(STR+'Conv_IntToString',InInt=g.getv('RoadAttempts',journey,JOURNEY)))
    g.do(cls(SAND_BUTTON)+':SetLabel',self=g.getv('Btn_Action'),NewLabel='Put the phone away')
    g.own('RefreshNotebook')
    g.own('RefreshL2Progress',Value=g.getv('Employability',journey,JOURNEY),Show=True)
    g.finish()


def message():
    g=G(WIDGET,'OpenL2Message');g.setv('MessageIndex',g.arg('Index'));g.setv('bReadingMessage',True)
    visible(g,'Inbox',False);visible(g,'ReadMessage',True)
    for i,(sender,body) in enumerate(D.MESSAGES):
        gate=g.branch(g.math('EqualEqual_IntInt',A=g.arg('Index'),B=i));g.side(gate)
        set_text(g,'Txt_ThreadName',sender);set_text(g,'Txt_Message',body)
        g.side(gate,False)
    g.finish()


def close_phone():
    g=G(WIDGET,'CloseL2Phone');host=g.getv('Host');valid(g,host)
    g.do(cls(FRONT)+':ClosePhone',self=host);g.finish()


def progress_body(path):
    g=G(path,'RefreshL2Progress');shown=g.branch(g.arg('Show'));g.side(shown)
    visible(g,'Bar_L2Employability',True)
    if path in (JHUD,b.HUD):visible(g,'Txt_Progress' if path==JHUD else 'Txt_Employability',True)
    value=g.math('Clamp',Value=g.arg('Value'),Min=0,Max=100)
    amount=g.math('Multiply_DoubleDouble',A=g.math('Conv_IntToDouble',InInt=value),B=.01)
    g.do(PB+'SetPercent',self=g.getv('Bar_L2Employability'),InPercent=amount)
    target={WIDGET:'Txt_L2Employability',JHUD:'Txt_Progress',b.HUD:'Txt_Employability',BATTLE:'Txt_BattleHelp'}[path]
    prefix={JHUD:'Find a job     Employability ',b.HUD:'Find a job   Employability ',
            BATTLE:'Write the C.V.   Employability '}.get(path,'Employability ')
    line=g.f(STR+'Concat_StrStr',A=prefix,B=g.f(STR+'Conv_IntToString',InInt=value))
    set_text(g,target,line)
    g.side(shown,False);visible(g,'Bar_L2Employability',False)
    if path in (JHUD,b.HUD):visible(g,'Txt_Progress' if path==JHUD else 'Txt_Employability',False)
    g.finish()


def battle_progress():
    g=G(BATTLE,'RefreshL2ProgressContext');enc=g.getv('Encounter');valid(g,enc)
    context=g.branch(g.getv('bLevel2CV',enc,ENCOUNTER));g.side(context)
    journey=g.getv('CVJourney',enc,ENCOUNTER);valid(g,journey)
    journey=g.cast(journey,cls(JOURNEY),'BP L2Journey')
    g.own('RefreshL2Progress',Value=g.getv('Employability',journey,JOURNEY),Show=True)
    g.side(context,False);g.own('RefreshL2Progress',Value=0,Show=False);g.finish()


def allowed_phone():
    nodes,_=inspect(JOURNEY,'CanOpenPhone')
    entry=next(n['node_id'] for n in nodes if norm(n['title'])=='canopenphone')
    result=next(n['node_id'] for n in nodes if norm(n['title'])=='returnnode')
    g=Batch(JOURNEY,'CanOpenPhone')
    old=[n['node_id'] for n in nodes if n['node_id'] not in (entry,result)]
    if old:g.ops.append(dict(op='remove',node_ids=old))
    g.get('phase','Phase',0,200);g.get('busy','StopBusy',0,400);g.get('session','PhoneSession',0,600)
    previous=None
    for i,phase in enumerate(D.PHONE_PHASES):
        ref='p'+str(i);g.fn(ref,b.K+'EqualEqual_IntInt',300,i*180,B=phase);g.link('phase','Phase',ref,'A')
        if previous:
            merged='m'+str(i);g.fn(merged,b.K+'BooleanOR',600,i*180)
            g.link(previous,'ReturnValue',merged,'A');g.link(ref,'ReturnValue',merged,'B');previous=merged
        else:previous=ref
    g.fn('not_busy',b.K+'Not_PreBool',900,200);g.link('busy','StopBusy','not_busy','A')
    g.fn('not_open',b.K+'Not_PreBool',900,400);g.link('session','PhoneSession','not_open','A')
    g.fn('free',b.K+'BooleanAND',1200,200);g.link('not_busy','ReturnValue','free','A');g.link('not_open','ReturnValue','free','B')
    g.fn('allowed',b.K+'BooleanAND',1500,200);g.link(previous,'ReturnValue','allowed','A');g.link('free','ReturnValue','allowed','B')
    g.get('dialogue','DialogueMode',1200,600)
    g.fn('no_dialogue',b.K+'EqualEqual_IntInt',1500,600,B=0);g.link('dialogue','DialogueMode','no_dialogue','A')
    g.fn('resting',b.K+'BooleanAND',1800,200);g.link('allowed','ReturnValue','resting','A');g.link('no_dialogue','ReturnValue','resting','B')
    g.link('resting','ReturnValue',result,'Allowed');g.chain(entry,result)
    g.comment('Resting phone access',[o['ref'] for o in g.ops if o['op']=='add_node']);g.run()


def open_phone():
    g=G(JOURNEY,'OpenPhone');allowed=g.f(cls(JOURNEY)+':CanOpenPhone')
    gate=g.branch((allowed[0],'Allowed'));g.side(gate)
    phone=find(g,PHONE,'BP Phone');closed=g.branch(g.math('Not_PreBool',A=g.getv('bOpen',phone,PHONE)));g.side(closed)
    host=find(g,FRONT,'BP Fo AFront End')
    player=g.getv('Player');valid(g,player)
    g.setv('PhoneSession',True);g.own('DisableConfirm')
    g.do(UW+'SetVisibility',self=g.getv('HUD'),InVisibility='Collapsed')
    # The portable phone is held relative to FollowCamera; it deliberately owns
    # no camera. Staged stops must yield their exterior view before raising it.
    g.do('/Script/Engine.PlayerController:SetViewTargetWithBlend',
         self=g.f(GS+'GetPlayerController',PlayerIndex=0),NewViewTarget=player,BlendTime=.2)
    g.do(cls(FRONT)+':OpenPhone',self=host);g.finish()


def phone_closed():
    g=G(JOURNEY,'PhoneClosed');session=g.branch(g.getv('PhoneSession'));g.side(session)
    g.setv('PhoneSession',False);allowed=g.f(cls(JOURNEY)+':CanOpenPhone')
    gate=g.branch((allowed[0],'Allowed'));g.side(gate)
    g.own('ReapplyStageView');g.own('EnableConfirm')
    hud=g.getv('HUD');valid(g,hud);g.do(UW+'SetVisibility',self=hud,InVisibility='Visible')
    g.own('RefreshProgressDisplays');g.finish()


def notify_closed():
    g=G(PHONE,'NotifyL2PhoneClosed');journey=find(g,JOURNEY,'BP L2Journey')
    g.do(cls(JOURNEY)+':PhoneClosed',self=journey);g.finish()


def clear_phone():
    g=G(JOURNEY,'ClearPhoneContext');g.setv('PhoneSession',False);g.setv('JobMessageDelivered',False)
    phone=find(g,PHONE,'BP Phone');g.do(cls(PHONE)+':ClosePhone',self=phone)
    g.do(cls(PHONE)+':RefreshScreen',self=phone);g.finish()


def frontend_hud():
    g=G(FRONT,'RestoreL2PhoneHUD');journey=find(g,JOURNEY,'BP L2Journey')
    active=g.branch(g.math('Greater_IntInt',A=g.getv('Phase',journey,JOURNEY),B=0));g.side(active)
    hud=g.getv('HUD');valid(g,hud);g.do(UW+'SetVisibility',self=hud,InVisibility='Collapsed');g.finish()


def notify_job():
    g=G(JOURNEY,'NotifyJobHunt');once=g.branch(g.getv('JobMessageDelivered'));g.side(once,False)
    g.setv('JobMessageDelivered',True)
    g.do(GS+'PlaySound2D',Sound='/Game/FoA/Audio/MetaSounds/Phone/S_Phone_Buzz.S_Phone_Buzz',
         VolumeMultiplier=.55)
    g.finish()


def show_condition(g):
    phase=g.getv('Phase');yes=False
    for value in (2,3,4,5,6,7,8,11):
        check=g.math('EqualEqual_IntInt',A=phase,B=value)
        yes=g.math('BooleanOR',A=yes,B=check)
    return g.math('BooleanAND',A=yes,B=g.math('Not_PreBool',A=g.getv('StopBusy')))


def journey_progress():
    g=G(JOURNEY,'RefreshJourneyProgress');hud=g.getv('HUD');valid(g,hud)
    g.do(cls(JHUD)+':RefreshL2Progress',self=hud,Value=g.getv('Employability'),Show=show_condition(g));g.finish()


def car_progress():
    g=G(JOURNEY,'RefreshCarProgress');car=g.getv('Car');valid(g,car)
    node=g.ref();g.set(node,'Employability',0,0,cls(b.CAR));g.put(node,'self',car)
    g.put(node,'Employability',g.getv('Employability'));g.chain(g.tail,node);g.tail=node
    hud=g.getv('HUD',car,b.CAR);valid(g,hud)
    g.do(cls(b.HUD)+':RefreshL2Progress',self=hud,Value=g.getv('Employability'),Show=show_condition(g));g.finish()


def phone_progress():
    g=G(JOURNEY,'RefreshPhoneProgress');phone=find(g,PHONE,'BP Phone')
    widget=g.f('/Script/UMG.WidgetComponent:GetUserWidgetObject',self=g.getv('Screen',phone,PHONE))
    widget=g.cast(widget,cls(WIDGET),'WBP Phone')
    g.do(cls(WIDGET)+':Refresh',self=widget);g.finish()


def encounter_progress():
    g=G(JOURNEY,'RefreshBattleProgress');enc=g.getv('Encounter');valid(g,enc)
    widget=g.getv('Widget',enc,ENCOUNTER);valid(g,widget)
    widget=g.cast(widget,cls(BATTLE),'WBP Encounter')
    show=g.math('EqualEqual_IntInt',A=g.getv('Phase'),B=6)
    g.do(cls(BATTLE)+':RefreshL2Progress',self=widget,Value=g.getv('Employability'),Show=show);g.finish()


def shared_progress():
    g=G(JOURNEY,'RefreshProgressDisplays')
    for name in ('RefreshJourneyProgress','RefreshCarProgress','RefreshPhoneProgress'):
        g.own(name)
    g.finish()


def route_plan(graph, nodes, edges, destination, inputs=()):
    """L2 context routes around L1 content/action; all authored false-path nodes survive."""
    if any(norm(n['title'])==norm(destination) for n in nodes):return None
    entry=next(n['node_id'] for n in nodes if norm(n['title'])==norm(graph))
    outgoing=[e for e in edges if e['from_node']==entry and e['from_pin']=='then']
    assert len(outgoing)==1,(graph,outgoing)
    edge=outgoing[0];g=Batch(WIDGET,graph)
    g.fn('resolve',cls(WIDGET)+':ResolveL2Phone',-1000,-300)
    g.get('context','bL2Phone',-900,0);g.node('gate','branch',-650,-300)
    g.fn('l2',cls(WIDGET)+':'+destination,-300,-500)
    g.link('context','bL2Phone','gate','Condition')
    for name in inputs:g.link(entry,name,'l2',name)
    g.cut(entry,'then',edge['to_node'],edge['to_pin']);g.chain(entry,'resolve','gate')
    g.link('gate','then','l2','execute')
    if graph=='Refresh':
        g.fn('restore',cls(WIDGET)+':RestoreL1Phone',-300,-100)
        g.link('gate','else','restore','execute');g.link('restore','then',edge['to_node'],edge['to_pin'])
    else:g.link('gate','else',edge['to_node'],edge['to_pin'])
    g.comment('Level 2 phone context',[o['ref'] for o in g.ops if o['op']=='add_node']);return g


def append_tails(path, graph, functions):
    nodes,edges=inspect(path,graph)
    if any(norm(n['title'])==norm(functions[-1]) for n in nodes):return
    tails=[]
    for n in nodes:
        node=n['node_id']
        if any(e['to_node']==node and e['to_pin']=='execute' for e in edges) \
                and any(p['name']=='then' for p in n.get('pins',[])) \
                and not any(e['from_node']==node and e['from_pin']=='then' for e in edges):
            tails.append(node)
    assert tails,(path,graph,'No terminal execution calls')
    g=Batch(path,graph)
    refs=[]
    for i,name in enumerate(functions):
        ref='tail'+str(i);g.fn(ref,cls(path)+':'+name,5000+i*340,-600);refs.append(ref)
    for node in tails:g.chain(node,refs[0])
    g.chain(*refs);g.comment('Level 2 continuity',refs);g.run()


def hooks():
    for graph,destination,inputs in (('Refresh','RefreshL2Phone',()),('OpenMessage','OpenL2Message',('Index',)),
                                     ('DoAction','CloseL2Phone',())):
        ns,es=inspect(WIDGET,graph);plan=route_plan(graph,ns,es,destination,inputs)
        if plan:plan.run()
    append_tails(PHONE,'ClosePhone',['NotifyL2PhoneClosed'])
    append_tails(FRONT,'ClosePhone',['RestoreL2PhoneHUD'])
    append_tails(BATTLE,'RedrawAll',['RefreshL2ProgressContext'])
    for name in ('ResumeRun','EnterCar','ActivateCar','Arrive','StageStop','StopActionFinished',
                 'AdvanceStopDialogue','PreviewRejection','EndMergePreview','Confirm','ConfirmEdit',
                 'RestartRun','StartFinale','FinaleWon','FinaleLost','RefreshEmployability','Submit'):
        append_tails(JOURNEY,name,['RefreshProgressDisplays'])
    append_tails(JOURNEY,'StartJourney',['NotifyJobHunt','RefreshProgressDisplays'])
    # Close before the original Abort restores player input/cinematic flags. Closing
    # afterward could restore the phone's cached staged cinematic lock into L1.
    nodes,edges=inspect(JOURNEY,'Abort')
    if not any(norm(n['title'])=='clearphonecontext' for n in nodes):
        setter=next(n['node_id'] for n in nodes if norm(n['title'])=='setphase')
        outgoing=[e for e in edges if e['from_node']==setter and e['from_pin']=='then']
        assert len(outgoing)==1,('Abort phase handoff',outgoing)
        edge=outgoing[0];g=Batch(JOURNEY,'Abort')
        g.fn('close_phone',cls(JOURNEY)+':ClearPhoneContext',-300,-900)
        g.cut(setter,'then',edge['to_node'],edge['to_pin']);g.chain(setter,'close_phone')
        g.link('close_phone','then',edge['to_node'],edge['to_pin'])
        g.comment('Release phone before player',['close_phone']);g.run()
    append_tails(JOURNEY,'Abort',['RefreshProgressDisplays'])


def keys():
    call('python_exec_file',path='P:/FoA/Tools/Unreal/level2/phone_progress_setup.py',
         resources=['asset:'+JOURNEY,'asset:'+PHONE])
    for path in (JOURNEY,PHONE):
        result=call('blueprint_compile',path=path,save=True)
        assert not result.get('error_count') and not result.get('warning_count'),result


def verify():
    for path in (*WIDGETS,PHONE,JOURNEY,FRONT):
        result=call('blueprint_compile',path=path,save=True)
        assert not result.get('error_count') and not result.get('warning_count'),result
        print('PHONE COMPILE',path,'0 errors 0 warnings',flush=True)


STEPS={'skeleton':skeleton,'tree':tree,'resolve_phone':resolve_phone,'cache_phone':cache_phone,
       'restore_phone':restore_phone,'refresh_phone':refresh_phone,'message':message,'close_phone':close_phone,
       'battle_progress':battle_progress}
STEPS.update(allowed_phone=allowed_phone,open_phone=open_phone,phone_closed=phone_closed,notify_closed=notify_closed,
             clear_phone=clear_phone,journey_progress=journey_progress,car_progress=car_progress,
             phone_progress=phone_progress,encounter_progress=encounter_progress,shared_progress=shared_progress,
             frontend_hud=frontend_hud,notify_job=notify_job,hooks=hooks,keys=keys,verify=verify)
STEPS.update({'progress_'+name:(lambda p=path:progress_body(p)) for name,path in
             (('phone',WIDGET),('journey',JHUD),('drive',b.HUD),('battle',BATTLE))})


if __name__=='__main__':
    import editor_lock
    step=sys.argv[1];owner=os.environ['FOA_AGENT']
    editor_lock.acquire(owner,wait_s=120,ttl=180,areas=[*WIDGETS,PHONE,JOURNEY,FRONT])
    try:
        assert not call('editor_get_state')['pie_running']
        STEPS[step]()
    finally:
        editor_lock.release(owner)
