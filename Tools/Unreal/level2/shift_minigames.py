"""Author the three 2D shift boards through the existing dialogue input routes."""
import build_drive as b
import build_interview as ui
import build_job_hunt as jobs
import build_l2_stop_look as look
from job_hunt_data import MAX_MISSES
from shift_minigame_data import PERIOD, WINDOW_START, WINDOW_END, RECIPES, BAYS, LEDGER, PACKED, TITLES

BP, UI, G = jobs.BP, jobs.UI, jobs.G
SHIFT, RESULT = jobs.SHIFT, jobs.RESULT
W = '/Script/UMG.Widget:'
BAR = '/Script/UMG.ProgressBar:'
FONT = ui.FONT
PACK = ('Rice', 'Tea', 'Oat milk')
ROUTE = ('Bay 03', 'Bay 08', 'Bay 12')
AUDIT = ('Subtract one', 'Add one', 'Post count')
VARS = (
    ('PackedRice','int','0'), ('PackedTea','int','0'), ('PackedOat','int','0'),
    ('LedgerCount','int','0'), ('ShiftFeedback','text',''), ('ShiftStarted','float','0'),
)
FUNCS = ('ResetShiftRound', 'SubmitShiftAction', 'AcceptShiftRound', 'MissShiftRound', 'TickShiftBoard')


def widget():
    """The mechanics' own pieces; build_l2_stop_look draws the rest (card, status, keys) in one style."""
    for name, kind, props in (
        ('ShiftZone','Border',{'BrushColor':[1,1,1,.4]}),
        ('ShiftMarker','Border',{'BrushColor':[1,1,1,.95]}),
        ('ShiftRail','Border',{'BrushColor':[1,1,1,.22]}),
        ('LedgerGauge','ProgressBar',{'Percent':0,'FillColorAndOpacity':'(R=1,G=1,B=1,A=.9)'}),
        ('LedgerTarget','Border',{'BrushColor':[1,1,1,.95]}),
        ('ShiftReadout','TextBlock',{'Font':{'FontObject':FONT,'TypefaceFontName':'Medium','Size':26},
                                   'Justification':'Left','ColorAndOpacity':{'SpecifiedColor':[.87,.87,.87,1]}}),
    ):
        if not b.call('ui_query',path=UI,name_pattern=name).get('matches'):
            b.call('ui_build_tree',widget_blueprint_path=UI,parent_widget_name='RootCanvas',tree=[{
                'name':name,'class':kind,'properties':dict(props,Visibility='Collapsed'),
                'slot_props':dict(anchors_min=[.5,.5],anchors_max=[.5,.5],alignment=[.5,.5],
                                  size=[1,1],z_order=5)}])
        b.call('ui_set_variable',widget_blueprint_path=UI,widget_name=name,is_variable=True)
    look.widget()


def declare():
    for name,kind,value in VARS:
        b.call('blueprint_add_variable',path=BP,variable_name=name,variable_type=kind,
               default_value=value,update_existing=True)
    for name in FUNCS:
        if not b.h.call('blueprint_inspect_graph',{'path':BP,'graph_name':name}).get('ok'):
            b.call('blueprint_add_function',path=BP,function_name=name)
    ui.declare(UI,{'PaintShiftBoard':[('Mode','int'),('Readout','text'),('Notice','text')],
                   'PaintLedger':[('Count','int'),('Target','int')],
                   'MoveShiftMarker':[('Progress','float'),('Entrance','float')]})
    widget()
    look.wdeclare()
    look.declare()


def mode(g,index):
    return ui.eq(g,'Stop',index)


def math(g,op,a,c):
    return g.math(op,A=a,B=c)


def plus(g,a,c):
    return math(g,'Add_DoubleDouble',a,c)


def choose(g,kind,yes,no,condition):
    return g.math('Select'+kind,A=yes,B=no,bPickA=condition)


def row(g,values):
    return jobs.pick(g,'Int',values,g.getv('JobOrder'))


def turn_clock(g):
    return math(g,'Subtract_DoubleDouble',g.f(b.GS+'GetTimeSeconds'),g.getv('ShiftStarted'))


def timing(g):
    return math(g,'Percent_FloatFloat',math(g,'Divide_DoubleDouble',turn_clock(g),PERIOD),1)


def board(g,mode_,readout='',notice=''):
    g.do(b.cls(UI)+':PaintShiftBoard',self=g.getv('InterviewHUD'),Mode=mode_,Readout=readout,Notice=notice)


def paint_ledger():
    g=G(UI,'PaintLedger')
    count=g.math('Conv_IntToDouble',InInt=g.arg('Count'))
    target=g.math('Conv_IntToDouble',InInt=g.arg('Target'))
    percent=math(g,'Divide_DoubleDouble',count,12)
    g.do(BAR+'SetPercent',self=g.getv('LedgerGauge'),InPercent=percent)
    x=math(g,'Multiply_DoubleDouble',target,37)
    g.do(W+'SetRenderTranslation',self=g.getv('LedgerTarget'),Translation=g.math('MakeVector2D',X=x,Y=0))
    g.finish()


def tick_board():
    g=G(BP,'TickShiftBoard')
    ui.guard(g,ui.eq(g,'DialogueMode',SHIFT))
    ui.valid(g,g.getv('InterviewHUD'))
    entrance=g.math('FClamp',Value=math(g,'Divide_DoubleDouble',turn_clock(g),.24),Min=0,Max=1)
    g.do(b.cls(UI)+':MoveShiftMarker',self=g.getv('InterviewHUD'),Progress=timing(g),Entrance=entrance)
    g.own('CrateTick')  # Queen Market's crate: drops, the spill, the full case going (build_l2_stop_look.py)
    g.finish()


def feedback(g, accepted):
    suffix='Confirm' if accepted else 'Select'
    sound=jobs.SOUND+f'SFX_FE_{suffix}.SFX_FE_{suffix}'
    g.do(b.GS+'PlaySound2D',Sound=sound,VolumeMultiplier=.55,
         PitchMultiplier=1.1 if accepted else .62,bIsUISound=True)


def reset_round():
    g=G(BP,'ResetShiftRound')
    for name in PACKED:g.setv(name,0)
    g.setv('LedgerCount',row(g,tuple(start for start,_ in LEDGER)))
    g.setv('ShiftStarted',g.f(b.GS+'GetTimeSeconds'))
    g.finish()


def render_shift():
    """Order card, status, choices and key caps for the three shifts (look: build_l2_stop_look.py). No glyph hints."""
    g=G(BP,'RenderShift')
    order=ui.num(g,g.math('Min',A=math(g,'Add_IntInt',g.getv('JobOrder'),1),B=4))
    status=ui.textvalue(g,ui.cat(g,ui.cat(g,'Order ',order),' of 4'))
    total=jobs.pick(g,'Float',(52.,42.,52.),g.getv('Stop'))
    remaining=math(g,'Divide_DoubleDouble',g.math('Conv_IntToDouble',InInt=g.getv('JobSeconds')),total)
    for i,job in enumerate(jobs.JOBS):
        branch=ui.guard(g,mode(g,i))
        if i==0:
            readout=''
        elif i==1:
            readout=ui.textvalue(g,jobs.pick(g,'String',tuple('Parcel for '+ROUTE[index]+'\nSend it while the marker is in the band.'
                                                         for index in BAYS),g.getv('JobOrder')))
        else:
            target=row(g,tuple(target for _,target in LEDGER))
            count=g.getv('LedgerCount')
            facts=ui.cat(g,ui.cat(g,'Shelf count  ',ui.num(g,target)),ui.cat(g,'\nLedger  ',ui.num(g,count)))
            readout=ui.textvalue(g,ui.cat(g,facts,'\nMatch them, then post the count.'))
            g.do(b.cls(UI)+':PaintLedger',self=g.getv('InterviewHUD'),Count=count,Target=target)
        jobs.display(g,TITLES[i],'',(PACK,ROUTE,AUDIT)[i],status,keys=look.SHIFT_KEYS[i])
        if i==0:
            g.do(b.cls(UI)+':PaintOrder',self=g.getv('InterviewHUD'),
                 **{name:row(g,targets) for name,targets in zip(('Rice','Tea','Oat'),zip(*RECIPES))},
                 **{name:g.getv(var) for name,var in zip(('PackedRice','PackedTea','PackedOat'),PACKED)})
        g.do(b.cls(UI)+':PaintShiftStatus',self=g.getv('InterviewHUD'),Remaining=remaining,Mistakes=g.getv('JobMistakes'))
        board(g,i,readout,TITLES[i])
        g.side(branch,False)
    g.finish()


def accept_round():
    g=G(BP,'AcceptShiftRound')
    feedback(g,True)
    g.setv('JobOrder',math(g,'Add_IntInt',g.getv('JobOrder'),1))
    g.own('ShiftReact',Accepted=True)  # level2 round 3: the stop's sand object and his line (build_l2_round3.py)
    complete=ui.guard(g,math(g,'GreaterEqual_IntInt',g.getv('JobOrder'),4))
    g.own('FinishJob',Won=True)
    g.side(complete,False)
    g.setv('ShiftFeedback','')
    g.own('ResetShiftRound')
    # Queen Market: the full case goes in a burst of sand first (CrateTick reopens the choices after CASE_CLEAR s)
    crate=mode(g,0)
    g.setv('DialogueReady',g.math('Not_PreBool',A=crate))
    g.setv('CaseDoneAt',choose(g,'Float',plus(g,g.f(b.GS+'GetTimeSeconds'),look.CASE_CLEAR),-1.,crate))
    g.own('RenderShift')
    g.finish()


def miss_round():
    g=G(BP,'MissShiftRound')
    feedback(g,False)
    g.setv('JobMistakes',math(g,'Add_IntInt',g.getv('JobMistakes'),1))
    g.own('ShiftReact',Accepted=False)
    missed=ui.guard(g,math(g,'GreaterEqual_IntInt',g.getv('JobMistakes'),MAX_MISSES))
    g.own('FinishJob',Won=False)
    g.side(missed,False)
    g.setv('ShiftFeedback','')
    g.own('ResetShiftRound')
    g.setv('DialogueReady',True)
    g.own('RenderShift')
    g.finish()


def submit():
    g=G(BP,'SubmitShiftAction')
    index=g.getv('DialogueSelected')
    pack=ui.guard(g,mode(g,0))
    for i,(var,targets) in enumerate(zip(PACKED,zip(*RECIPES))):
        item=ui.guard(g,math(g,'EqualEqual_IntInt',index,i))
        fits=ui.guard(g,math(g,'Less_IntInt',g.getv(var),row(g,targets)))
        g.setv(var,math(g,'Add_IntInt',g.getv(var),1))
        count=math(g,'Add_IntInt',g.getv(PACKED[0]),math(g,'Add_IntInt',g.getv(PACKED[1]),g.getv(PACKED[2])))
        g.own('DropCrateItem',Kind=i,Slot=math(g,'Subtract_IntInt',count,1))  # into the crate with a thud
        filled=ui.guard(g,math(g,'EqualEqual_IntInt',count,3))
        g.own('AcceptShiftRound')
        g.side(filled,False)
        g.setv('DialogueReady',True)
        g.own('RenderShift')
        g.side(fits,False);g.own('SpillCrateItem',Kind=i);g.own('MissShiftRound')  # over the rim, into black sand
        g.side(item,False)
    g.side(pack,False)
    dispatch=ui.guard(g,mode(g,1))
    aligned=g.math('InRange_FloatFloat',Value=timing(g),Min=WINDOW_START,Max=WINDOW_END)
    route=math(g,'EqualEqual_IntInt',index,row(g,BAYS))
    sent=ui.guard(g,math(g,'BooleanAND',aligned,route))
    g.own('AcceptShiftRound')
    g.side(sent,False);g.own('MissShiftRound')
    g.side(dispatch,False)
    posting=ui.guard(g,math(g,'EqualEqual_IntInt',index,2))
    balanced=ui.guard(g,math(g,'EqualEqual_IntInt',g.getv('LedgerCount'),row(g,tuple(target for _,target in LEDGER))))
    g.own('AcceptShiftRound')
    g.side(balanced,False);g.own('MissShiftRound')
    g.side(posting,False)
    adjustment=choose(g,'Int',-1,1,math(g,'EqualEqual_IntInt',index,0))
    g.setv('LedgerCount',g.math('Clamp',Value=math(g,'Add_IntInt',g.getv('LedgerCount'),adjustment),Min=0,Max=12))
    g.setv('ShiftFeedback','')
    g.setv('DialogueReady',True)
    g.own('RenderShift')
    g.finish()


def install():
    declare()
    look.wgraphs()
    look.crate_graphs()
    for fn in (paint_ledger,tick_board,reset_round,accept_round,miss_round,submit,render_shift):
        fn()


