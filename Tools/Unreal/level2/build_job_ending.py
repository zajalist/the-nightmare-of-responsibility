"""Real bedroom wake-up and rolling credits after the final dialogue fight."""

import os
from pathlib import Path

import build_drive as b
import build_threshold as t
from job_dream_look import COMPONENT as MOTION
from job_wake_scene import ROOM_SAND, SEQUENCE, WAKE_LENGTH

BP=t.BP
ROLL=t.D.ROOT+'/WBP_L2CreditsRoll'
POST='/Script/Engine.PostProcessComponent'
VOLUME='/Script/Engine.PostProcessVolume'
ROLL_SECONDS=30.
WAKE_CREDITS_FADE=.85
FUNCTIONS={
    'BeginWakeCredits':(), 'FadeWakeToCredits':(), 'TickWakeCredits':(), 'RestoreWakeLook':(),
    'HideWakeSand':(('Index','int'),), 'RestoreWakeSand':(('Index','int'),),
    'HideWakeActor':(('Target','object:/Script/Engine.Actor'),),
    'RememberWakeSand':(('Target','object:/Script/Engine.Actor'),), 'FindWakeGrade':(),
}
CREDITS=(
    ('The Nightmare of Responsibility',78),
    ('Unreal Engine and MetaHuman\nEpic Games',43),
    ('Built with Lux3D by Manycore and Hayba',43),
    ('Dream worlds generated with Aholo SpatialGen by Manycore',43),
    ('Toronto city scan\nLiDAR Point Clouds, CanElevation Series, Natural Resources Canada\nToronto and Region Conservation Authority, GTA 2023 acquisition\nContains information licensed under the Open Government Licence – Canada.',36),
    ('Toronto building footprints\n3D Massing, City of Toronto\nContains information licensed under the Open Government Licence – Toronto.',36),
    ('Environment assets\nPoly Haven, CC0\nAnimation by Quaternius, CC0',40),
    ('Sound\nSonniss Game Audio GDC bundles and Kenney',40),
    ('Darker Grotesque\nGabriel Lam and Viet Anh Nguyen, SIL Open Font License 1.1',39),
    ('Man Black Business Suit\nStyle3D CG, adapted under CC BY 4.0',39),
    ('Battle icons\nLorc and Delapouite, game-icons.net, CC BY 3.0',39),
    ('Thank you for playing',54),
)


def credits_widget():
    if not b.h.call('blueprint_get_info',{'path':ROLL}).get('ok'):
        b.call('ui_create_widget',path=t.D.ROOT,name='WBP_L2CreditsRoll')
    if not b.call('ui_query',path=ROLL,name_pattern='CreditsBlack').get('matches'):
        b.call('ui_build_tree',widget_blueprint_path=ROLL,parent_widget_name='RootCanvas',tree=[dict(
            name='CreditsBlack',**{'class':'Border'},properties={'BrushColor':[0,0,0,1],'Visibility':'HitTestInvisible'},
            slot_props=dict(anchors_min=[0,0],anchors_max=[1,1],position=[0,0],size=[0,0],z_order=-1))])
    if not b.call('ui_query',path=ROLL,name_pattern='CreditNames').get('matches'):
        children=[]
        for i,(copy,size) in enumerate(CREDITS):
            children.append(dict(name=f'Credit{i}',**{'class':'TextBlock'},
                properties={'Text':copy,'Justification':'Center','AutoWrapText':True,
                    'Font':{'FontObject':'/Game/FoA/UI/Fonts/F_FoA_UI.F_FoA_UI',
                            'TypefaceFontName':'ExtraBold' if i in (0,len(CREDITS)-1) else 'SemiBold','Size':size},
                    'ColorAndOpacity':{'SpecifiedColor':[.96,.94,.9,1.]},'Visibility':'HitTestInvisible'},
                slot_props={'padding':[0,0,0,66],'horizontal_alignment':'Fill'}))
        b.call('ui_build_tree',widget_blueprint_path=ROLL,parent_widget_name='RootCanvas',tree={
            'name':'CreditNames','class':'VerticalBox','children':children,
            'slot_props':{'anchors_min':[.5,.5],'anchors_max':[.5,.5],'alignment':[.5,0.],'position':[0,585],'size':[1360,2800]}})
        b.call('ui_set_variable',widget_blueprint_path=ROLL,widget_name='CreditNames',is_variable=True)
    if not b.h.call('blueprint_inspect_graph',{'path':ROLL,'graph_name':'SetScroll'}).get('ok'):
        b.call('blueprint_add_function',path=ROLL,function_name='SetScroll',inputs=[dict(name='Offset',type='float')])
    b.call('ui_compile_widget',widget_blueprint_path=ROLL)
    g=b.G(ROLL,'SetScroll')
    g.do('/Script/UMG.Widget:SetRenderTranslation',self=g.getv('CreditNames'),
         Translation=g.math('MakeVector2D',X=0,Y=g.arg('Offset')));g.finish()


def declare():
    credits_widget()
    info=b.call('blueprint_get_info',path=BP);have={row['name'] for row in info['variables']}
    for name,kind,default,container in (
        ('WakeGrade','object:'+VOLUME,'',''),('WakeGradeWasEnabled','bool','true',''),
        ('WakeActive','bool','false',''),('WakeSandTargets','object:/Script/Engine.Actor','','array'),
        ('WakeSandHidden','object:/Script/Engine.Actor','','array'),('WakeCredits','object:'+b.cls(ROLL),'',''),
        ('WakeCreditsStart','float','0',''),
    ):
        if name not in have:
            b.call('blueprint_add_variable',path=BP,variable_name=name,variable_type=kind,default_value=default,container=container,update_existing=True)
    for name,params in FUNCTIONS.items():
        if not b.h.call('blueprint_inspect_graph',{'path':BP,'graph_name':name}).get('ok'):
            outputs=[dict(name='Target',type='object:/Script/Engine.Actor')] if name=='FindWakeGrade' else []
            b.call('blueprint_add_function',path=BP,function_name=name,inputs=[dict(name=n,type=kind) for n,kind in params],outputs=outputs)
    b.call('blueprint_compile',path=BP)


def body(g,target,variable,native):
    ref=g.ref();g.get(ref,variable,0,0,native);g.put(ref,'self',target)
    return ref,variable


def valid(g,object_):
    gate=g.branch(g.f(b.SL+'IsValid',Object=object_));g.side(gate);return gate


def hide_actor():
    g=b.G(BP,'HideWakeActor');actor=g.arg('Target');valid(g,actor)
    hidden=body(g,actor,'bHidden','/Script/Engine.Actor')
    shown=g.branch(g.math('Not_PreBool',A=hidden));g.side(shown)
    g.own('RememberWakeSand',Target=actor)
    g.do(b.A+'SetActorHiddenInGame',self=actor,bNewHidden=True);g.finish()


def start_wake():
    g=b.G(BP,'EndingColour');g.setv('Phase',8);g.setv('WakeActive',True)
    t.external(g,'BlendWeight',0.,g.getv(MOTION),POST)
    g.do('/Script/Engine.LevelStreaming:SetShouldBeVisible',self=g.getv('Stream'),bInShouldBeVisible=False)
    g.do('/Script/Engine.LevelStreaming:SetShouldBeVisible',self=g.getv('CityStream'),bInShouldBeVisible=False)
    g.do('/Script/Engine.PrimitiveComponent:SetCollisionEnabled',self=g.getv('Floor'),NewType='NoCollision')
    g.do(b.A+'SetActorHiddenInGame',self=g.getv('Player'),bNewHidden=True)
    merge=g.getv('Merge',g.getv('Journey'),b.JOURNEY)
    g.do(b.A+'SetActorHiddenInGame',self=merge,bNewHidden=True)
    g.do(b.A+'K2_SetActorLocation',self=g.getv('Player'),NewLocation='238,-191,155',bSweep=False,bTeleport=True)
    grade=g.own('FindWakeGrade')
    obj=g.cast((grade[0],'Target'),VOLUME,'Post Process Volume');g.setv('WakeGrade',obj)
    g.setv('WakeGradeWasEnabled',body(g,obj,'bEnabled',VOLUME));t.external(g,'bEnabled',False,obj,VOLUME)
    sand=g.do(b.GS+'GetAllActorsWithTag',Tag=ROOM_SAND);g.setv('WakeSandTargets',(sand[0],'OutActors'))
    g.own('HideWakeSand',Index=0)
    pool=g.do(b.GS+'GetActorOfClass',ActorClass=b.cls('/Game/FoA/VFX/Sand/BP_SandFX'))
    g.own('HideWakeActor',Target=pool)
    t.music(g,'None');t.text(g)
    seq=g.do(t.LSP+'CreateLevelSequencePlayer',LevelSequence=SEQUENCE,
             Settings='(bDisableMovementInput=True,bDisableLookAtInput=True,bHideHud=True,bPauseAtEnd=True)')
    g.setv('Sequence',seq);g.setv('SequenceActor',(seq[0],'OutActor'))
    g.do(t.MSP+'Play',self=seq);t.timer(g,'FadeWakeToCredits',WAKE_LENGTH+.65);g.finish()


def fade_wake():
    g=b.G(BP,'FadeWakeToCredits')
    active=g.branch(g.getv('WakeActive'));g.side(active)
    t.fade(g,0,1,WAKE_CREDITS_FADE)
    t.timer(g,'BeginWakeCredits',WAKE_CREDITS_FADE)
    g.finish()


def show_credits():
    g=b.G(BP,'BeginWakeCredits');t.fade(g,1,1,0.)
    widget=g.ref();g.node(widget,'create_widget',0,0,class_path=b.cls(ROLL));g.put(widget,'OwningPlayer',g.f(b.GS+'GetPlayerController',PlayerIndex=0))
    g.chain(g.tail,widget);g.tail=widget;g.setv('WakeCredits',(widget,'ReturnValue'))
    g.do('/Script/UMG.UserWidget:AddToViewport',self=g.getv('WakeCredits'),ZOrder=95)
    g.setv('WakeCreditsStart',g.f(b.GS+'GetTimeSeconds'))
    t.timer(g,'TickWakeCredits',.033,True);g.finish()


def tick_credits():
    g=b.G(BP,'TickWakeCredits');widget=g.getv('WakeCredits');valid(g,widget)
    age=g.math('Subtract_DoubleDouble',A=g.f(b.GS+'GetTimeSeconds'),B=g.getv('WakeCreditsStart'))
    done=g.branch(g.math('GreaterEqual_DoubleDouble',A=age,B=ROLL_SECONDS));g.side(done)
    g.do(b.SL+'K2_ClearTimer',FunctionName='TickWakeCredits')
    front=g.do(b.GS+'GetActorOfClass',ActorClass=b.cls(t.FRONT));front=g.cast(front,b.cls(t.FRONT),'BP Fo AFront End')
    g.do(b.cls(t.FRONT)+':ReturnToTitle',self=front)
    g.side(done,False)
    g.do(b.cls(ROLL)+':SetScroll',self=widget,Offset=g.math('Multiply_DoubleDouble',A=age,B=-99.))
    g.finish()


def restore():
    g=b.G(BP,'RestoreWakeLook')
    t.external(g,'BlendWeight',0.,g.getv(MOTION),POST)
    for name in ('FadeWakeToCredits','BeginWakeCredits','TickWakeCredits'):g.do(b.SL+'K2_ClearTimer',FunctionName=name)
    was_wake=g.branch(g.getv('WakeActive'));g.side(was_wake)
    g.setv('WakeActive',False);g.own('RestoreWakeSand',Index=0)
    t.external(g,'bEnabled',g.getv('WakeGradeWasEnabled'),g.getv('WakeGrade'),VOLUME)
    valid(g,g.getv('WakeCredits'));g.do('/Script/UMG.Widget:RemoveFromParent',self=g.getv('WakeCredits'))
    g.setv('WakeCredits','');g.finish()


def install():
    worker=Path(__file__).with_name('job_wake_scene.py').resolve().as_posix()
    state=b.call('editor_get_state')
    assert not any('L_Tutorial_Bedroom' in str(package) for package in state.get('dirty_packages',[])),state.get('dirty_packages')
    for step,resource in (('sequence','asset:'+t.D.ROOT),('tags','world:/Game/FoA/Maps/L_Tutorial_Bedroom')):
        b.call('python_exec_file',path=worker,env={'FOA_WAKE_STEP':step},resources=[resource])
    declare()
    b.call('python_exec_file',path=worker,env={'FOA_WAKE_STEP':'graphs'},resources=['asset:'+BP])
    from finalize_l2_graphs import checked_compile
    print(checked_compile(BP))
    for fn in (hide_actor,restore,show_credits,tick_credits,fade_wake,start_wake):fn()
