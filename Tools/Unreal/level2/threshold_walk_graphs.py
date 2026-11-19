"""Native dream-walk bodies; bound to the existing threshold builder namespace.

The dream room (dreamroom lane): white marks lead to a glowing white EXIT. As he walks, his anxieties rise out of
black sand (Lux3D splats on M_SplatMesh, CPD SandEvent: no tick, no MID): the clock and the bills beside the path,
hands at his feet. Pressure (Torment) slows his walk, sways the room (BP_SplatFXDirector.AmbientIntensity), raises the
heartbeat and shakes the camera. At the peak a headache stops him: hold to breathe in (the room calms as the bar fills),
let go to breathe out, and that segment's fears crumble. Segment two closes a gate of fears in front of EXIT; the
second breath crumbles it and the walk to the light is free. ReduceMotion scales shakes and sway to zero.
"""

SC = '/Script/Engine.SceneComponent:'
PRIM = '/Script/Engine.PrimitiveComponent:'
AU = '/Script/Engine.AudioComponent:'
CM = '/Script/Engine.CharacterMovementComponent'
MPC_DREAM = '/Game/FoA/PostProcess/MPC_Dream'
SHAKE = '/Game/FoA/VFX/CS_SandHit.CS_SandHit_C'
SAND = '/Game/FoA/VFX/Sand/BPL_SandFX.BPL_SandFX_C:'
TEXT = '/Script/Engine.KismetTextLibrary:Conv_StringToText'
TEXT_TO_STRING = '/Script/Engine.KismetTextLibrary:Conv_TextToString'
STR = '/Script/Engine.KismetStringLibrary:'
SANDLINE = '/Game/FoA/UI/Widgets/Common/WBP_SandLine'  # the ui lane's kit: Play(Line, Mood, Hold), Dismiss()


def asset(path):return path+'.'+path.rsplit('/',1)[1]


PRESSURE = asset('/Game/FoA/Audio/MetaSounds/Story/S_Story_HeadPressure')
CRUMBLE = asset('/Game/FoA/Audio/MetaSounds/Sand/S_Sand_Crumble')
EXHALE = asset('/Game/FoA/Audio/MetaSounds/Breath/S_Breath_Effort')
STING = asset('/Game/FoA/Audio/SFX/Horror/SFX_Horror_Stinger_01')


def eq(g,name,value):return g.math('EqualEqual_IntInt',A=g.getv(name),B=value)
def both(g,a,b):return g.math('BooleanAND',A=a,B=b)
def mul(g,a,b):return g.math('Multiply_DoubleDouble',A=a,B=b)
def phase(g):
    branch=g.branch(eq(g,'Phase',3));g.side(branch)


def motion(g):
    """1, or 0 under ReduceMotion. The MPC read is impure, so it sits on the exec path."""
    rm=g.do(ML+'GetScalarParameterValue',Collection=MPC_DREAM,ParameterName='ReduceMotion')
    return g.math('Subtract_DoubleDouble',A=1,B=g.math('FClamp',Value=rm,Min=0,Max=1))


def shake(g,scale):
    cam=g.f(GS+'GetPlayerCameraManager',PlayerIndex=0)
    g.do('/Script/Engine.PlayerCameraManager:StartCameraShake',self=cam,ShakeClass=SHAKE,Scale=scale)


def walk_speed(g,value):
    r=g.ref();g.get(r,'CharacterMovement',0,0,'/Script/Engine.Character');g.put(r,'self',g.getv('Player'))
    external(g,'MaxWalkSpeed',value,(r,'CharacterMovement'),CM)


def sand_event(g,comp,start,seconds,end):
    """M_SplatMesh SandEvent (custom primitive data 0-3): dissolve from start to end over seconds; 1 = all sand."""
    now=g.f(GS+'GetTimeSeconds')
    g.do(PRIM+'SetVectorParameterForCustomPrimitiveData',self=comp,ParameterName='SandEvent',
         Value=g.math('MakeVector4',X=start,Y=now,Z=seconds,W=end))


def path_complete(g):
    at=g.f(A+'K2_GetActorLocation',self=g.getv('Player'))
    near=g.math('LessEqual_DoubleDouble',A=g.math('Vector_Distance',V1=at,V2=','.join(map(str,D.EXIT))),B=100)
    earned=both(g,eq(g,'RouteBeat',2),eq(g,'BreathState',0))
    return both(g,earned,both(g,near,g.math('GreaterEqual_DoubleDouble',A=g.getv('Age'),B=D.PATH_MIN)))


def hide_path():
    g=G(BP,'HidePath')
    for n,v in [('BreathState',0),('BreathAge',0),('ReleaseAge',0),('BreathArmed',False),('Torment',0),('TormentGoal',0)]:g.setv(n,v)
    for name in ('RouteGuide','FearsA','FearsB'):
        g.do(SC+'SetVisibility',self=g.getv(name),bNewVisibility=False,bPropagateToChildren=True)
    for name in ('DreadAudio','TickAudio'):g.do(AU+'Stop',self=g.getv(name))
    g.do(cls(HUD)+':RefreshPath',self=g.getv('HUD'),Thought='',Hint='',Progress=0,ShowMeter=False,Active=False)
    # The room's sway goes back to its resting value (the director may already be gone on a restore).
    valid=g.branch(g.f(SL+'IsValid',Object=g.getv('Splat')));g.side(valid)
    external(g,'AmbientIntensity',.8,g.getv('Splat'),cls(FX))
    g.finish()


def reset_path():
    g=G(BP,'ResetPath')
    for n in ('RouteBeat','Stage'):g.setv(n,0)
    g.setv('StageAge',0);g.own('HidePath');g.finish()


def start_headache():
    g=G(BP,'StartHeadache');phase(g)
    gate=g.branch(both(g,eq(g,'BreathState',0),g.math('Less_IntInt',A=g.getv('RouteBeat'),B=2)));g.side(gate)
    for n,v in [('BreathState',1),('BreathAge',0),('ReleaseAge',0),('BreathArmed',False),('TormentGoal',1)]:g.setv(n,v)
    movement(g,False)
    g.do(cls(DREAM)+':TriggerGlitchBurst',self=g.getv('Grade'),Strength=D.GLITCH[0],Seconds=D.GLITCH[1])
    g.do(GS+'PlaySound2D',Sound=PRESSURE,VolumeMultiplier=.8)
    at=g.f(A+'K2_GetActorLocation',self=g.getv('Player'))
    fx(g,5,D.PULSE_RADIUS,g.math('Conv_VectorToLinearColor',InVec=at))  # the floor around him gives way, then re-forms
    g.do(SAND+'SpawnSandBloom',Location=g.math('Subtract_VectorVector',A=at,B='0,0,90'),Size=2.4,Seconds=5,Crumble=True)
    g.own('RefreshPath');g.finish()


def finish_breath():
    g=G(BP,'FinishBreath');phase(g)
    gate=g.branch(both(g,eq(g,'BreathState',4),g.math('GreaterEqual_DoubleDouble',A=g.getv('ReleaseAge'),B=D.BREATH_RELEASE)));g.side(gate)
    g.setv('RouteBeat',g.math('Clamp',Value=g.math('Add_IntInt',A=g.getv('RouteBeat'),B=1),Min=0,Max=2))
    for n,v in [('BreathState',0),('BreathAge',0),('ReleaseAge',0),('BreathArmed',False),('TormentGoal',0),('StageAge',0)]:g.setv(n,v)
    g.setv('Stage',g.math('Multiply_IntInt',A=g.getv('RouteBeat'),B=len(D.SEGMENTS[0])))
    g.own('CrumbleFears',Segment=g.math('Subtract_IntInt',A=g.getv('RouteBeat'),B=1))
    g.do(GS+'PlaySound2D',Sound=CRUMBLE,VolumeMultiplier=.9)
    g.do(GS+'PlaySound2D',Sound=EXHALE,VolumeMultiplier=.7)
    timer(g,'SettleFears',D.CRUMBLE_SECONDS+.5)
    movement(g,True);g.own('RefreshPath');g.finish()


def crumble_fears():
    g=G(BP,'CrumbleFears')
    first=g.branch(g.math('EqualEqual_IntInt',A=g.arg('Segment'),B=0));g.side(first)
    for f in D.SEGMENTS[0]:sand_event(g,g.getv(f[0]),0,D.CRUMBLE_SECONDS,1)
    g.do(AU+'Stop',self=g.getv('TickAudio'))
    g.own('Think',Line='Okay. Walk.',Seconds=2.5)
    g.side(first,False)
    for f in D.SEGMENTS[1]:sand_event(g,g.getv(f[0]),0,D.CRUMBLE_SECONDS,1)
    g.finish()


def settle_fears():
    """After the crumble has fallen, hide the finished segment so its collapsed splats cost nothing."""
    g=G(BP,'SettleFears')
    second=g.branch(g.math('Greater_IntInt',A=g.getv('RouteBeat'),B=1));g.side(second)
    g.do(SC+'SetVisibility',self=g.getv('FearsB'),bNewVisibility=False,bPropagateToChildren=True)
    g.side(second,False)
    g.do(SC+'SetVisibility',self=g.getv('FearsA'),bNewVisibility=False,bPropagateToChildren=True)
    g.finish()


def rise_fear():
    g=G(BP,'RiseFear')
    item=None
    for i,f in reversed(list(enumerate(D.FEARS))):
        v=g.getv(f[0])
        item=v if item is None else g.math('SelectObject',A=v,B=item,bSelectA=g.math('EqualEqual_IntInt',A=g.arg('Index'),B=i))
    comp=g.cast(item,'/Script/Engine.StaticMeshComponent','Static Mesh Component')
    g.do(SC+'SetVisibility',self=comp,bNewVisibility=True,bPropagateToChildren=False)
    sand_event(g,comp,1,D.RISE_SECONDS,0)
    g.do(SAND+'SpawnSandBurst',Location=g.f(SC+'K2_GetComponentLocation',self=comp),Scale=1.6)
    shake(g,mul(g,.3,motion(g)))
    g.finish()


def think():
    g=G(BP,'Think');g.setv('ThoughtLine',g.arg('Line'))
    g.setv('ThoughtUntil',g.math('Add_DoubleDouble',A=g.getv('Age'),B=g.arg('Seconds')));g.finish()


def advance():
    """The next torment stage, once he has walked to it (or stood still too long); one stage per call."""
    g=G(BP,'Advance')
    ys=None
    for k,(y,*_) in reversed(list(enumerate(D.STAGES))):
        ys=y if ys is None else g.math('SelectFloat',A=y,B=ys,bPickA=eq(g,'Stage',k))
    at=g.f(A+'K2_GetActorLocation',self=g.getv('Player'));xyz=g.f(K+'BreakVector',InVec=at)
    walked=g.math('GreaterEqual_DoubleDouble',A=(xyz[0],'Y'),B=g.math('Add_DoubleDouble',A=D.OFFSET[1],B=ys))
    age=g.getv('StageAge')
    due=both(g,g.math('GreaterEqual_DoubleDouble',A=age,B=D.STAGE_GAP[0]),
             g.math('BooleanOR',A=walked,B=g.math('GreaterEqual_DoubleDouble',A=g.getv('StageAge'),B=D.STAGE_GAP[1])))
    ready=both(g,both(g,g.math('Less_IntInt',A=g.getv('Stage'),B=len(D.STAGES)),eq(g,'BreathState',0)),due)
    go=g.branch(ready);g.side(go)
    for k,(y,fears,goal,thought) in enumerate(D.STAGES):
        stage=g.branch(eq(g,'Stage',k));g.side(stage)
        g.setv('Stage',k+1);g.setv('StageAge',0)
        if fears is None:g.own('StartHeadache')
        else:
            g.setv('TormentGoal',goal)
            for f in fears:
                if f in D.HAND_AHEAD:  # hands break out of the floor at his feet, wherever he stands
                    dx,dy=D.HAND_AHEAD[f]
                    p=g.f(K+'BreakVector',InVec=g.f(A+'K2_GetActorLocation',self=g.getv('Player')))
                    spot=g.math('MakeVector',X=g.math('Add_DoubleDouble',A=(p[0],'X'),B=dx),
                                Y=g.math('Add_DoubleDouble',A=(p[0],'Y'),B=dy),Z=D.OFFSET[2]-6)
                    g.do(SC+'K2_SetWorldLocation',self=g.getv(f),NewLocation=spot,bSweep=False,bTeleport=True)
                g.own('RiseFear',Index=D.FEAR_INDEX[f])
            if fears[0] in D.HAND_AHEAD:g.do(GS+'PlaySound2D',Sound=STING,VolumeMultiplier=.55)
            if 'FearClock' in fears:g.do(AU+'Play',self=g.getv('TickAudio'),StartTime=0)
            if thought:g.own('Think',Line=thought,Seconds=3)
        g.side(stage,False)
    g.finish()


def step_torment():
    g=G(BP,'StepTorment');phase(g)
    dt=g.math('FClamp',Value=g.arg('Delta'),Min=0,Max=D.MAX_STEP)
    # Holding the breath eases the pressure as the bar fills; breathing out settles it.
    goal=g.getv('TormentGoal')
    easing=g.math('Subtract_DoubleDouble',A=1,B=mul(g,.6,g.math('Divide_DoubleDouble',A=g.getv('BreathAge'),B=D.BREATH_HOLD)))
    held=g.math('SelectFloat',A=mul(g,g.getv('TormentGoal'),easing),B=goal,bPickA=eq(g,'BreathState',2))
    target=g.math('SelectFloat',A=D.CALM_PRESSURE,B=held,bPickA=g.math('GreaterEqual_IntInt',A=g.getv('BreathState'),B=3))
    g.setv('Torment',g.math('FInterpTo',Current=g.getv('Torment'),Target=target,DeltaTime=dt,InterpSpeed=1.8))
    walk_speed(g,g.math('Lerp',A=D.PATH_SPEED,B=D.PATH_HEAVY,Alpha=g.getv('Torment')))
    free=motion(g)
    sway=g.math('Add_DoubleDouble',A=.8,B=mul(g,5,mul(g,g.getv('Torment'),free)))
    external(g,'AmbientIntensity',sway,g.getv('Splat'),cls(FX))
    # Never silent: an AudioComponent started at volume 0 is culled and does not come back (run_20261118_0029).
    g.do(AU+'SetVolumeMultiplier',self=g.getv('DreadAudio'),NewVolumeMultiplier=g.math('Add_DoubleDouble',A=.12,B=mul(g,g.getv('Torment'),1.1)))
    for n in ('StageAge','ShakeAge'):g.setv(n,g.math('Add_DoubleDouble',A=g.getv(n),B=dt))
    tremor=g.branch(both(g,g.math('GreaterEqual_DoubleDouble',A=g.getv('ShakeAge'),B=D.SHAKE_EVERY),
                          g.math('Greater_DoubleDouble',A=g.getv('Torment'),B=D.SHAKE_FROM)))
    g.side(tremor);g.setv('ShakeAge',0);shake(g,mul(g,mul(g,g.getv('Torment'),.45),free));g.own('Advance')
    g.side(tremor,False);g.own('Advance');g.finish()


def step_breath():
    g=G(BP,'StepBreath');phase(g)
    dt=g.math('FClamp',Value=g.arg('Delta'),Min=0,Max=D.MAX_STEP)
    first=g.branch(eq(g,'BreathState',1));g.side(first)
    down=g.branch(g.arg('Down'));g.side(down)
    armed=g.branch(g.getv('BreathArmed'));g.side(armed)
    g.setv('BreathState',2);g.setv('BreathAge',0);g.own('RefreshPath')
    g.side(down,False);g.setv('BreathArmed',True);g.own('RefreshPath')
    g.side(first,False)
    hold=g.branch(eq(g,'BreathState',2));g.side(hold)
    held=g.branch(g.arg('Down'));g.side(held)
    g.setv('BreathAge',g.math('FClamp',Value=g.math('Add_DoubleDouble',A=g.getv('BreathAge'),B=dt),Min=0,Max=D.BREATH_HOLD))
    full=g.branch(g.math('GreaterEqual_DoubleDouble',A=g.getv('BreathAge'),B=D.BREATH_HOLD));g.side(full)
    g.setv('BreathState',3);g.own('RefreshPath')
    g.side(full,False);g.own('RefreshPath')
    g.side(held,False);g.setv('BreathAge',0);g.setv('BreathState',1);g.setv('BreathArmed',True);g.own('RefreshPath')
    g.side(hold,False)
    release=g.branch(eq(g,'BreathState',3));g.side(release)
    up=g.branch(g.math('Not_PreBool',A=g.arg('Down')));g.side(up)
    g.setv('BreathState',4);g.setv('ReleaseAge',0);g.own('RefreshPath')
    g.side(release,False)
    settle=g.branch(eq(g,'BreathState',4));g.side(settle)
    again=g.branch(g.arg('Down'));g.side(again)
    g.setv('BreathState',3);g.setv('ReleaseAge',0);g.own('RefreshPath')
    g.side(again,False);g.setv('ReleaseAge',g.math('Add_DoubleDouble',A=g.getv('ReleaseAge'),B=dt))
    complete=g.branch(g.math('GreaterEqual_DoubleDouble',A=g.getv('ReleaseAge'),B=D.BREATH_RELEASE));g.side(complete)
    g.own('FinishBreath');g.side(complete,False);g.own('RefreshPath');g.finish()


def recover_path():
    g=G(BP,'RecoverPath');phase(g)
    for n,v in [('BreathState',0),('BreathAge',0),('ReleaseAge',0),('BreathArmed',False)]:g.setv(n,v)
    y=g.math('SelectFloat',A=D.SAFE_Y[2],B=D.SAFE_Y[1],bPickA=eq(g,'RouteBeat',2))
    y=g.math('SelectFloat',A=D.SAFE_Y[0],B=y,bPickA=eq(g,'RouteBeat',0))
    at=g.math('MakeVector',X=D.OFFSET[0],Y=g.math('Add_DoubleDouble',A=D.OFFSET[1],B=y),Z=92)
    g.do(A+'K2_SetActorLocation',self=g.getv('Player'),NewLocation=at,bSweep=False,bTeleport=True)
    movement(g,True)
    g.do(PC+'SetControlRotation',self=g.f(GS+'GetPlayerController',PlayerIndex=0),NewRotation=g.math('MakeRotator',Yaw=90))
    g.own('RefreshPath');g.finish()


def step_path():
    g=G(BP,'StepPath');phase(g)
    phone=g.branch(g.math('Not_PreBool',A=g.getv('bOpen',g.getv('Phone'),PHONE)));g.side(phone)
    loc=g.f(A+'K2_GetActorLocation',self=g.getv('Player'));xyz=g.f(K+'BreakVector',InVec=loc)
    outside=g.math('BooleanOR',A=g.math('Less_DoubleDouble',A=(xyz[0],'Z'),B=-20),
        B=g.math('Greater_DoubleDouble',A=g.math('Vector_Distance2D',V1=loc,V2=','.join(map(str,D.OFFSET))),B=520))
    edge=g.branch(outside);g.side(edge);g.own('RecoverPath');g.side(edge,False)
    pc=g.f(GS+'GetPlayerController',PlayerIndex=0)
    keys=[g.f('/Script/Engine.PlayerController:IsInputKeyDown',self=pc,Key=k) for k in ('E','SpaceBar','Gamepad_FaceButton_Bottom')]
    down=g.math('BooleanOR',A=keys[0],B=g.math('BooleanOR',A=keys[1],B=keys[2]))
    g.own('StepTorment',Delta=g.arg('Delta'))
    active=g.branch(g.math('Greater_IntInt',A=g.getv('BreathState'),B=0));g.side(active)
    g.own('StepBreath',Delta=g.arg('Delta'),Down=down);g.side(active,False)
    done=g.branch(path_complete(g));g.side(done);g.own('BeginFall')
    g.side(done,False);g.own('RefreshPath');g.finish()


def refresh_path():
    """One key glyph when breath matters, one short line, no paragraphs and no separators."""
    g=G(BP,'RefreshPath');phase(g)
    def show(thought,hint,meter,active):
        progress=g.math('Divide_DoubleDouble',A=g.getv('BreathAge'),B=D.BREATH_HOLD)
        g.do(cls(HUD)+':RefreshPath',self=g.getv('HUD'),Thought=thought,Hint=hint,Progress=progress,ShowMeter=meter,Active=active)
    walking=g.branch(eq(g,'BreathState',0));g.side(walking)
    line=g.math('SelectString',A=g.getv('ThoughtLine'),B='',bPickA=g.math('Less_DoubleDouble',A=g.getv('Age'),B=g.getv('ThoughtUntil')))
    at=g.f(K+'BreakVector',InVec=g.f(A+'K2_GetActorLocation',self=g.getv('Player')))
    still=both(g,g.math('Less_DoubleDouble',A=g.getv('Age'),B=5),g.math('Less_DoubleDouble',A=(at[0],'Y'),B=D.ENTRY[1]+40))
    nudge=g.math('BooleanOR',A=still,B=g.math('GreaterEqual_DoubleDouble',A=g.getv('Age'),B=D.PATH_MAX))
    key=g.math('SelectString',A='W',B='',bPickA=nudge)
    show(g.f(TEXT,InString=line),g.f(TEXT,InString=key),False,nudge)
    g.side(walking,False)
    first=g.branch(eq(g,'BreathState',1));g.side(first)
    armed=g.branch(g.getv('BreathArmed'));g.side(armed)
    show('Hold to breathe','E',True,True)
    g.side(armed,False);show('Let go of E','E',True,True)
    g.side(first,False)
    holding=g.branch(eq(g,'BreathState',2));g.side(holding)
    show('Breathe in','E',True,True)
    g.side(holding,False)
    release=g.branch(eq(g,'BreathState',3));g.side(release)
    show('Let go','E',True,True)
    g.side(release,False);show('Breathe out','E',True,True);g.finish()


GRAPHS=dict(ResetPath=reset_path,StepPath=step_path,StartHeadache=start_headache,StepBreath=step_breath,
            FinishBreath=finish_breath,RecoverPath=recover_path,RefreshPath=refresh_path,HidePath=hide_path,
            StepTorment=step_torment,Advance=advance,RiseFear=rise_fear,Think=think,CrumbleFears=crumble_fears,
            SettleFears=settle_fears)
# New functions (name: inputs) and variables (name, type, default) this module adds to BP_DreamThreshold.
FUNCTIONS={'StepTorment':[('Delta','float')],'Advance':[],'RiseFear':[('Index','int')],
           'Think':[('Line','string'),('Seconds','float')],'CrumbleFears':[('Segment','int')],'SettleFears':[]}
VARIABLES=[('Torment','float','0'),('TormentGoal','float','0'),('Stage','int','0'),('StageAge','float','0'),
           ('ShakeAge','float','0'),('ThoughtLine','string',''),('ThoughtUntil','float','0')]
COMPONENTS=[('FearsA','SceneComponent'),('FearsB','SceneComponent'),('ExitDoor','StaticMeshComponent'),
            ('ExitDoorR','StaticMeshComponent'),('ExitLintel','StaticMeshComponent'),
            ('DreadAudio','AudioComponent'),('TickAudio','AudioComponent')]  # plus one StaticMeshComponent per D.FEARS row


def widget():
    font='/Game/FoA/UI/Fonts/F_FoA_UI.F_FoA_UI'
    existing=str(call('ui_query',path=HUD))
    anchor={'anchors_min':[.5,1],'anchors_max':[.5,1],'alignment':[.5,.5]}
    tree=[]
    if 'PathBox' not in existing:
        tree.append({'class':'Border','name':'PathBox','slot_props':dict(anchor,position=[0,-132],size=[1040,216],z_order=-1),
                     'properties':{'BrushColor':[.012,.012,.012,.88],'Visibility':'Collapsed'}})
    if 'Txt_Thought' not in existing:
        tree.append({'class':'TextBlock','name':'Txt_Thought','slot_props':dict(anchor,position=[0,-165],size=[1000,44]),
                     'properties':{'Text':'','Justification':'Center','Font':{'FontObject':font,'TypefaceFontName':'SemiBold','Size':28},
                                   'ColorAndOpacity':{'SpecifiedColor':[.96,.96,.96,1]}}})
    if 'Bar_Steady' not in existing:
        tree.append({'class':'ProgressBar','name':'Bar_Steady','slot_props':dict(anchor,position=[0,-126],size=[280,8]),
                     'properties':{'Percent':0.,'Visibility':'Collapsed','FillColorAndOpacity':'(R=.9,G=.9,B=.9,A=1)'}})
    if tree:call('ui_build_tree',widget_blueprint_path=HUD,parent_widget_name='RootCanvas',tree=tree)
    for name in ('PathBox','Txt_Thought','Bar_Steady'):call('ui_set_variable',widget_blueprint_path=HUD,widget_name=name,is_variable=True)
    if 'Line_Thought' not in existing:  # the ui lane's sand line shows the thought; Txt_Thought stays as its data
        call('ui_build_tree',widget_blueprint_path=HUD,parent_widget_name='RootCanvas',tree=[{'class':SANDLINE+'.WBP_SandLine_C','name':'Line_Thought',
             'slot_props':dict(anchor,position=[0,-232],size=[900,52],z_order=3)}])
        call('ui_set_variable',widget_blueprint_path=HUD,widget_name='Line_Thought',is_variable=True)
    # auto size, centred on its anchor: the kit draws the line from its left edge, so a fixed 900 px box put short
    # lines ("Breathe in") off to the left of the key cap (run_20261118_0233)
    call('ui_set_widget_properties',widget_blueprint_path=HUD,widget_name='Line_Thought',
         slot_props=dict(anchor,position=[0,-232],auto_size=True),
         properties={'Scale':2.9,'bLineFont':True,'LineFont':{'FontObject':font,'TypefaceFontName':'SemiBold','Size':32},
                     'Visibility':'HitTestInvisible'})
    padding()
    call('ui_compile_widget',widget_blueprint_path=HUD)
    wi=call('blueprint_get_info',path=HUD)
    if 'LastThought' not in {v['name'] for v in wi['variables']}:
        call('blueprint_add_variable',path=HUD,variable_name='LastThought',variable_type='string',default_value='',category='Dream')
    if 'SyncLine' not in wi['functions']:
        call('blueprint_add_function',path=HUD,function_name='SyncLine',inputs=[dict(name='Line',type='text'),dict(name='Meter',type='bool')])
    call('ui_compile_widget',widget_blueprint_path=HUD)
    sync_line()
    g=G(HUD,'RefreshPath')
    g.own('SyncLine',Line=g.arg('Thought'),Meter=g.arg('ShowMeter'))
    for name,arg in [('Txt_Thought','Thought'),('Txt_Hint','Hint')]:
        g.do('/Script/UMG.TextBlock:SetText',self=g.getv(name),InText=g.arg(arg))
    g.do('/Script/UMG.ProgressBar:SetPercent',self=g.getv('Bar_Steady'),InPercent=g.arg('Progress'))
    full=g.math('GreaterEqual_DoubleDouble',A=g.arg('Progress'),B=.999)
    tint=g.math('MakeColor',R=1,G=g.math('SelectFloat',A=.32,B=.88,bPickA=full),
                B=g.math('SelectFloat',A=.12,B=.70,bPickA=full),A=1)
    g.do('/Script/UMG.ProgressBar:SetFillColorAndOpacity',self=g.getv('Bar_Steady'),InColor=tint)
    meter=g.branch(g.arg('ShowMeter'));g.side(meter)
    g.do('/Script/UMG.Widget:SetVisibility',self=g.getv('Bar_Steady'),InVisibility='HitTestInvisible');yes=g.tail
    g.side(meter,False);g.do('/Script/UMG.Widget:SetVisibility',self=g.getv('Bar_Steady'),InVisibility='Collapsed')
    active=g.branch(g.arg('Active'));g.link(yes,'then',active,'execute');g.side(active)
    g.do('/Script/UMG.Widget:SetVisibility',self=g.getv('PathBox'),InVisibility='HitTestInvisible')
    g.side(active,False);g.do('/Script/UMG.Widget:SetVisibility',self=g.getv('PathBox'),InVisibility='Collapsed');g.finish()
    call('ui_compile_widget',widget_blueprint_path=HUD);call('asset_save',asset_paths=[HUD])


def sync_line():
    """Play the thought as sand when it changes: Shock as the headache asks for breath, Quick for the breath steps,
    Calm for thoughts and the exhale; a cleared line blows away (Dismiss). RefreshPath runs every tick, so compare first."""
    g=G(HUD,'SyncLine')
    line=g.f(TEXT_TO_STRING,InText=g.arg('Line'))
    changed=g.branch(g.f(STR+'NotEqual_StrStr',A=line,B=g.getv('LastThought')));g.side(changed)
    g.setv('LastThought',line)
    blank=g.branch(g.f(STR+'EqualEqual_StrStr',A=g.getv('LastThought')));g.side(blank)
    g.do(SANDLINE+'.WBP_SandLine_C:Dismiss',self=g.getv('Line_Thought'))
    g.side(blank,False)
    said=lambda words:g.f(STR+'EqualEqual_StrStr',A=g.getv('LastThought'),B=words)
    mood=g.math('SelectInt',A=3,B=0,bPickA=g.arg('Meter'))
    mood=g.math('SelectInt',A=0,B=mood,bPickA=said('Breathe out'))
    mood=g.math('SelectInt',A=1,B=mood,bPickA=said('Hold to breathe'))
    g.do(SANDLINE+'.WBP_SandLine_C:Play',self=g.getv('Line_Thought'),Line=g.arg('Line'),Mood=mood,Hold=0)
    g.finish()


def padding():
    """In-place slots only. The ink key cap holds one glyph; the line sits above it and the breath bar under it."""
    anchor={'anchors_min':[.5,1],'anchors_max':[.5,1],'alignment':[.5,.5],'auto_size':False}
    for name,position,size in [('PathBox',[0,-150],[96,88]),('Txt_Thought',[0,-232],[900,52]),
                               ('Bar_Steady',[0,-90],[220,10]),('Txt_Hint',[0,-150],[96,88])]:
        props={}
        if name=='PathBox':
            from l2_ink_style import brush
            props={'Background':brush('T_L2InkPanel'),'BrushColor':[1,1,1,.92]}
        if name=='Txt_Hint':
            props={'AutoWrapText':False,'Justification':'Center','Font':{'FontObject':'/Game/FoA/UI/Fonts/F_FoA_UI.F_FoA_UI',
                    'TypefaceFontName':'ExtraBold','Size':44}}
        if name=='Txt_Thought':  # render opacity 0: Line_Thought draws the words as sand
            props={'RenderOpacity':0.0,'Justification':'Center','ShadowOffset':{'X':1,'Y':2},'ShadowColorAndOpacity':[0,0,0,.9],
                   'Font':{'FontObject':'/Game/FoA/UI/Fonts/F_FoA_UI.F_FoA_UI','TypefaceFontName':'SemiBold','Size':32}}
        call('ui_set_widget_properties',widget_blueprint_path=HUD,widget_name=name,
             slot_props=dict(anchor,position=position,size=size),properties=props)


def bind(context):
    for name in ('G','BP','D','A','PC','GS','K','ML','SL','PHONE','HUD','DREAM','FX','cls','fx','movement','call','external','timer'):
        globals()[name]=context[name]
    return GRAPHS
