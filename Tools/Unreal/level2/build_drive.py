"""Native Hayba authoring. Run one step per lease: skeleton, or BlueprintName.Function.
Structural input/component setup is in drive_setup.py. No runtime Python is needed.
"""
import json
import os
from pathlib import Path
import sys
import time

sys.path[:0] = [str(Path(__file__).parent), 'P:/FoA/Tools/Unreal', 'P:/FoA/Tools/Unreal/player']
import drive_data as D
import hayba_call as h
import editor_lock
from held_tool_graphs import Batch, inspect

K = '/Script/Engine.KismetMathLibrary:'
A = '/Script/Engine.Actor:'
SC = '/Script/Engine.SceneComponent:'
GS = '/Script/Engine.GameplayStatics:'
SL = '/Script/Engine.KismetSystemLibrary:'
SP = '/Script/Engine.SplineComponent:'
CAR, ROAD, MET = [D.ROOT + '/' + n for n in ('BP_L2Car', 'BP_L2RoadNetwork', 'BP_Meteor')]
HUD = D.ROOT + '/WBP_L2Drive'
JOURNEY = '/Game/FoA/Level2/Journey/BP_L2Journey'
CITY_MPC = '/Game/FoA/Level2/Materials/MPC_L2.MPC_L2'
ML = '/Script/Engine.KismetMaterialLibrary:'


def cls(path):
    return path + '.' + path.rsplit('/', 1)[1] + '_C'


def call(cmd, **args):
    if 'variable_type' in args and args['variable_type']=='real':args['variable_type']='float'
    for p in args.get('inputs',[]):
        if p['type']=='real':p['type']='float'
    r = h.call(cmd, args, timeout=300)
    assert r.get('ok'), (cmd, r)
    data = r.get('data') or {}
    assert data.get('ok', True), (cmd, data)
    print(cmd,args.get('variable_name') or args.get('function_name') or args.get('path',''),flush=True)
    return data


VARIABLES = {
    CAR: [('Active','bool','false'), ('Employability','int','0'), ('ReturnPawn','object:/Script/Engine.Pawn',''),
          ('Journey','object:/Script/Engine.Actor',''),
          ('Composure','int','100'), ('Leg','int','0'), ('RailIndex','int','0'),
          ('Distance','real','0'), ('Speed','real','0'), ('Lane','real','1'), ('LaneOffset','real','180'),
          ('Throttle','bool','false'), ('BrakeHeld','bool','false'), ('TurnQueued','bool','false'),
          ('Clock','real','0'), ('NextMeteor','real','3'), ('MeteorsLeft','int','1'),
          ('Failed','bool','false'), ('Arrived','bool','false'), ('RestartAt','real','0'),
          ('Road','object:'+cls(ROAD),''), ('Meteor','object:'+cls(MET),''),
          ('Rail','object:/Script/Engine.SplineComponent',''), ('HUD','object:'+cls(HUD),''),
          ('Place','text','Queen Street'), ('Cue','text',''), ('LastOutcome','name','None'),
          ('HitsResolved','int','0'), ('LaneChanges','int','0'), ('JunctionChoices','int','0'),
          ('RoadAttempts','int','0'),('Destination','vector','15535,80,2'),('NearDestination','bool','false'),('PreviousDriveTransform','transform','')],
    MET: [('Car','object:'+cls(CAR),''), ('Age','real','0'), ('ImpactStarted','real','-10'), ('Active','bool','false'),
          ('Impacted','bool','false'), ('Inside','bool','false'), ('Braced','bool','false'),
          ('Late','bool','false'), ('NearStrike','bool','false')],
    ROAD: [], HUD: [],
}
SIGNATURES = {
    CAR: {'Begin':[], 'Activate':[('Index','int')], 'Deactivate':[],
          'SetRail':[('Index','int')], 'StartLeg':[('Index','int')],
          'DriveStep':[('Delta','real')], 'Move':[('Delta','real')], 'AdvanceRail':[],
          'Schedule':[], 'Brace':[], 'ChangeLane':[('Side','real')], 'QueueTurn':[],
          'ResolveHit':[('Cost','int'),('Outcome','name')], 'Restart':[], 'RefreshHUD':[], 'Continue':[], 'PlaceAtCheckpoint':[], 'CheckDestination':[]},
    MET: {'Arm':[('Driver','object:'+cls(CAR)),('Position','vector')],
          'Step':[('Delta','real')], 'Impact':[], 'Resolve':[], 'AcceptBrace':[], 'Hide':[], 'UpdateImpact':[], 'ResetImpact':[]},
    ROAD: {}, HUD: {'Refresh':[('Value','int'),('Location','text'),('Prompt','text')],
                   'RefreshProgress':[('Value','int')]},
}

# Keep canonical skeleton rebuilds aware of the small, independently applied wave helper.
VARIABLES[CAR] += [('ShockwaveStamp','real','-10'),('ShockwaveGap','real','0'),
    ('ShockwaveFired','bool','false'),('ShockwaveVelocity','vector','0,0,0'),('ShockwaveOffset','vector','0,0,0'),
    ('RouteMarkerIndex','int','-1'),('UsedShelter','bool','false')]
SIGNATURES[CAR].update({'UpdateShockwave':[('Delta','real')],'ResetShockwave':[],'CheckShelter':[]})


def skeleton():
    for path, parent in ((ROAD,'Actor'), (CAR,'Pawn'), (MET,'Actor')):
        if not h.call('blueprint_get_info',{'path':path}).get('ok'):
            call('blueprint_create', package_path=path, name=path.rsplit('/',1)[1], parent_class_path='/Script/Engine.'+parent)
    if not h.call('blueprint_get_info',{'path':HUD}).get('ok'):
        call('ui_create_widget', path=D.ROOT, name='WBP_L2Drive')
    for path in (ROAD, CAR, MET, HUD):
        h.renew_all(D.OWNER,180)
        info = call('blueprint_get_info', path=path)
        have = {v['name'] for v in info['variables']}
        for name, typ, default in VARIABLES[path]:
            if name not in have:
                call('blueprint_add_variable', path=path, variable_name=name, variable_type=typ,
                     default_value=default, category='Drive', instance_editable=name in ('Leg','Distance'))
        for name, inputs in SIGNATURES[path].items():
            if name not in info['functions']:
                call('blueprint_add_function', path=path, function_name=name,
                     inputs=[dict(name=n,type=t) for n,t in inputs])
        call('blueprint_compile', path=path)
        call('asset_save', asset_paths=[path])


def components():
    specs={ROAD:[('Root','SceneComponent',None),('CityCollision','StaticMeshComponent',None),
                 ('DestinationMarker','StaticMeshComponent',None),('CitySky','StaticMeshComponent',None)]
                 +[(name,'StaticMeshComponent',None) for name in ('DestinationPost','BayEdgeLeft','BayEdgeRight')]
                 +[(name,'TextRenderComponent',None) for name in ('DestinationLabel','ShelterSouth','ShelterNorth')]
                 +[('Rail'+str(i),'SplineComponent',None) for i in range(8)],
           CAR:[('Root','SceneComponent',None),('Collision','BoxComponent',None),('Body','StaticMeshComponent',None),('Roof','StaticMeshComponent',None),
                ('CameraBoom','SpringArmComponent',None),('FollowCamera','CameraComponent','CameraBoom')],
           MET:[('Root','SceneComponent',None),('Shadow','StaticMeshComponent',None),('Ring','StaticMeshComponent',None)]}
    for path,items in specs.items():
        info=call('blueprint_get_info',path=path)
        component_names={c['name'] for c in info.get('components',[])}
        for name,typ,parent in items:
            if name not in component_names:
                call('blueprint_add_component',path=path,component_name=name,
                     component_class_path='/Script/Engine.'+typ)
        call('blueprint_compile',path=path);call('asset_save',asset_paths=[path])


def compile_all():
    for path in (ROAD,CAR,MET,HUD):
        result=call('blueprint_compile',path=path)
        print(json.dumps(result),flush=True)
        assert result.get('error_count',0)==0,result


def lifecycle_defaults():
    call('blueprint_set_defaults',path=CAR,properties={'AutoPossessPlayer':'Disabled'})
    call('asset_save',asset_paths=[CAR])


def capture(name):
    call('python_exec_file',path='P:/FoA/Tools/Unreal/level2/drive_verify.py',
         env={'FOA_CAPTURE_ASSET':name},resources=['asset:'+D.ROOT])
    out=Path('P:/FoA/Saved/Codex/l2_drive')
    graphs=json.loads((out/'graph_audit.json').read_text())
    expected=[out/'graphs'/(name+'_'+row['graph']+'.png') for row in graphs if row['asset']==name]
    deadline=time.monotonic()+30
    while not all(p.exists() for p in expected):
        assert time.monotonic()<deadline,'Graph capture did not finish before compilation'
        time.sleep(.1)


def widget():
    if 'Txt_Place' not in str(call('ui_query',path=HUD)):
        children=[]
        for name,text,size,y in [('Txt_Place','Queen Street',38,28),('Txt_Composure','Composure 100',24,78),
                                 ('Txt_Cue','',30,120),('Txt_Controls','W drive    S brake / reverse    A D steer    Q look back    Space brace',22,170)]:
            children.append({'class':'TextBlock','name':name,
                'slot_props':{'position':[32,y],'size':[1100,52]},
                'properties':{'Text':text,'Font':{'FontObject':'/Game/FoA/UI/Fonts/F_FoA_UI.F_FoA_UI','TypefaceFontName':'SemiBold','Size':size},
                              'ColorAndOpacity':{'SpecifiedColor':[.95,.95,.95,1]},'ShadowOffset':{'X':1,'Y':2},
                              'ShadowColorAndOpacity':[0,0,0,1]}})
        call('ui_build_tree',widget_blueprint_path=HUD,parent_widget_name='RootCanvas',tree=children)
        for name in ('Txt_Place','Txt_Composure','Txt_Cue'):
            call('ui_set_variable',widget_blueprint_path=HUD,widget_name=name,is_variable=True)
        call('ui_compile_widget',widget_blueprint_path=HUD)
    if 'Txt_Employability' not in str(call('ui_query',path=HUD)):
        call('ui_build_tree',widget_blueprint_path=HUD,parent_widget_name='RootCanvas',tree=[{
            'class':'TextBlock','name':'Txt_Employability','slot_props':{'position':[32,228],'size':[1100,40]},
            'properties':{'Text':'Employability 0','Font':{'FontObject':'/Game/FoA/UI/Fonts/F_FoA_UI.F_FoA_UI',
                          'TypefaceFontName':'SemiBold','Size':22},'ColorAndOpacity':{'SpecifiedColor':[.95,.95,.95,1]},
                          'ShadowOffset':{'X':1,'Y':2},'ShadowColorAndOpacity':[0,0,0,1]}}])
        call('ui_set_variable',widget_blueprint_path=HUD,widget_name='Txt_Employability',is_variable=True)
        call('ui_compile_widget',widget_blueprint_path=HUD)
    g=G(HUD,'RefreshProgress')
    value=g.f('/Script/Engine.KismetStringLibrary:Conv_IntToString',InInt=g.arg('Value'))
    line=g.f('/Script/Engine.KismetStringLibrary:Concat_StrStr',A='Employability ',B=value)
    text=g.f('/Script/Engine.KismetTextLibrary:Conv_StringToText',InString=line)
    g.do('/Script/UMG.TextBlock:SetText',self=g.getv('Txt_Employability'),InText=text);g.finish()
    g=G(HUD,'Refresh')
    value=g.f('/Script/Engine.KismetStringLibrary:Conv_IntToString',InInt=g.arg('Value'))
    line=g.f('/Script/Engine.KismetStringLibrary:Concat_StrStr',A='Composure ',B=value)
    text=g.f('/Script/Engine.KismetTextLibrary:Conv_StringToText',InString=line)
    for name,val in [('Txt_Composure',text),('Txt_Place',g.arg('Location')),('Txt_Cue',g.arg('Prompt'))]:
        g.do('/Script/UMG.TextBlock:SetText',self=g.getv(name),InText=val)
    g.finish()
    widget_polish()


def widget_polish():
    """In-place HUD contrast/layout only; keep all text variables and graph bindings."""
    existing=str(call('ui_query',path=HUD))
    names=('Txt_Place','Txt_Composure','Txt_Employability','Txt_Cue','Txt_Controls')
    assert all(name in existing for name in names),'Build the existing drive widget first'
    plates=[('Brd_DriveStatus',dict(position=[24,24],size=[440,232])),
            ('Brd_DriveControls',dict(anchors_min=[.5,1],anchors_max=[.5,1],alignment=[.5,1],
                                      position=[0,-24],size=[900,56]))]
    for name,slot in plates:
        slot.update(z_order=0,auto_size=False)
        properties=dict(BrushColor=[.012,.012,.012,.9],Visibility='HitTestInvisible')
        if name not in existing:
            call('ui_build_tree',widget_blueprint_path=HUD,parent_widget_name='RootCanvas',tree=[{
                'class':'Border','name':name,'properties':properties,'slot_props':slot}])
        else:
            result=call('ui_set_widget_properties',widget_blueprint_path=HUD,widget_name=name,
                        properties=properties,slot_props=slot)
            assert not result.get('unknown_slot_props') and not result.get('rejected_properties'),result
    rows=[('Txt_Place',30,36,44,.96),('Txt_Composure',28,86,38,1.),
          ('Txt_Employability',22,128,32,.76),('Txt_Cue',26,174,64,1.)]
    for name,size,y,height,grey in rows+[('Txt_Controls',22,0,30,.92)]:
        slot=dict(anchors_min=[0,0],anchors_max=[0,0],alignment=[0,0],
                  position=[44,y],size=[400,height],z_order=1,auto_size=False)
        if name=='Txt_Controls':
            slot.update(anchors_min=[.5,1],anchors_max=[.5,1],alignment=[.5,1],
                        position=[0,-37],size=[860,30])
        result=call('ui_set_widget_properties',widget_blueprint_path=HUD,widget_name=name,
            slot_props=slot,properties=dict(Font={'FontObject':'/Game/FoA/UI/Fonts/F_FoA_UI.F_FoA_UI',
                'TypefaceFontName':'SemiBold','Size':size},ColorAndOpacity={'SpecifiedColor':[grey,grey,grey,1]},
                AutoWrapText=name=='Txt_Cue',ShadowOffset={'X':0,'Y':0},ShadowColorAndOpacity=[0,0,0,0],
                Visibility='HitTestInvisible'))
        assert not result.get('unknown_slot_props') and not result.get('rejected_properties'),result
    call('ui_set_widget_properties',widget_blueprint_path=HUD,widget_name='Txt_Controls',properties={'Text':'W drive    S brake / reverse    A D steer    Q look back    Space brace'})
    call('ui_compile_widget',widget_blueprint_path=HUD)
    call('ui_save_widget',widget_blueprint_path=HUD)


class G(Batch):
    """Typed wires over the existing house Batch; each function is a small owned graph."""
    def __init__(self, path, name):
        super().__init__(path, name)
        ns, _ = inspect(path, name)
        self.e = next(n['node_id'] for n in ns if n['title'].replace(' ','') == name)
        old = [n['node_id'] for n in ns if n['node_id'] != self.e]
        if old:
            self.ops.append(dict(op='remove', node_ids=old))
        self.i, self.tail = 0, self.e

    def ref(self):
        self.i += 1
        return 'd' + str(self.i)

    def arg(self, n):
        return (self.e, n)

    def put(self, ref, name, value):
        if isinstance(value, tuple):
            self.link(value[0], value[1], ref, name)
        elif value != '':
            self.pin(ref, name, str(value).lower() if isinstance(value,bool) else value)

    def getv(self, name, target=None, path=None):
        r=self.ref(); self.get(r,name,(self.i%5)*280,300+(self.i//5)*180,cls(path) if path else None)
        if target: self.put(r,'self',target)
        return r,name

    def f(this, fn, **pins):
        r=this.ref(); this.fn(r,fn,(this.i%5)*280,300+(this.i//5)*180)
        for n,v in pins.items(): this.put(r,n,v)
        return r,'ReturnValue'

    def math(self, name, **pins):
        return self.f(K+name,**pins)

    def do(this, fn, **pins):
        r=this.f(fn,**pins)[0]; this.chain(this.tail,r); this.tail=r
        return r,'ReturnValue'

    def own(self, name, **pins):
        return self.do(cls(self.path)+':'+name,**pins)

    def cast(self, value, classpath, result_name):
        r=self.ref();self.node(r,'cast',self.i*220,0,class_path=classpath)
        self.put(r,'Object',value);self.chain(self.tail,r);self.tail=r
        return r,'As'+result_name

    def setv(self, name, value):
        r=self.ref();self.set(r,name,self.i*220,0);self.put(r,name,value);self.chain(self.tail,r);self.tail=r
        return r,name

    def branch(self, condition):
        r=self.ref();self.node(r,'branch',self.i*220,0);self.put(r,'Condition',condition);self.chain(self.tail,r)
        return r

    def side(self, branch, yes=True):
        # An empty function call keeps the branch output explicit without manufacturing a sequence node.
        self.tail=branch
        self._side='then' if yes else 'else'

    def chain(self,*refs):
        for a,b in zip(refs,refs[1:]):
            self.link(a,getattr(self,'_side','then'),b,'execute')
            self._side='then'

    def finish(self):
        # Batch handles failed partial edits; also compile its rollback before leaving the lease.
        exec_refs={o['to_node'] for o in self.ops if o['op']=='connect' and o['to_pin']=='execute'}
        data_index=exec_index=0
        for o in self.ops:
            if o['op']=='add_node':
                if o['ref'] in exec_refs:
                    exec_index+=1;o.update(x=exec_index*320,y=0)
                else:
                    o.update(x=320+(data_index//4)*400,y=280+(data_index%4)*240);data_index+=1
        self.comment(' '.join(__import__('re').findall('[A-Z][a-z]*',self.graph))+' flow',
                     [o['ref'] for o in self.ops if o['op']=='add_node'])
        return self.run()


def set_rail():
    g=G(CAR,'SetRail');idx=g.arg('Index');g.setv('RailIndex',idx);g.setv('Distance',0)
    road=g.getv('Road')
    for i in range(len(D.RAILS)):
        b=g.branch(g.math('EqualEqual_IntInt',A=idx,B=i));g.side(b)
        g.setv('Rail',g.getv('Rail'+str(i),road,ROAD))
        g.side(b,False)
    g.finish()


def begin():
    g=G(CAR,'Begin')
    for path,var in ((ROAD,'Road'),(MET,'Meteor')):
        found=g.do(GS+'GetActorOfClass',ActorClass=cls(path))
        typed=g.cast(found,cls(path),'BP L2Road Network' if path==ROAD else 'BP Meteor');g.setv(var,typed)
    me=g.ref();g.node(me,'self',0,500)
    car=g.ref();g.set(car,'Car',2400,0,cls(MET));g.put(car,'self',g.getv('Meteor'));g.put(car,'Car',(me,'self'))
    g.chain(g.tail,car);g.tail=car
    g.finish()


def activate():
    g=G(CAR,'Activate')
    ready=g.branch(g.math('Not_PreBool',A=g.getv('Active')));g.side(ready)
    g.own('Begin')
    g.setv('ReturnPawn',g.f(GS+'GetPlayerPawn',PlayerIndex=0))
    pc=g.f(GS+'GetPlayerController',PlayerIndex=0)
    sub=g.f('/Script/Engine.SubsystemBlueprintLibrary:GetLocalPlayerSubSystemFromPlayerController',
            PlayerController=pc,Class='/Script/EnhancedInput.EnhancedInputLocalPlayerSubsystem')
    sub=g.cast(sub,'/Script/EnhancedInput.EnhancedInputLocalPlayerSubsystem','Enhanced Input Local Player Subsystem')
    g.do('/Script/EnhancedInput.EnhancedInputSubsystemInterface:AddMappingContext',self=sub,
         MappingContext=D.ROOT+'/Input/IMC_L2Drive.IMC_L2Drive',Priority=1)
    me=g.ref();g.node(me,'self',0,500)
    g.do('/Script/Engine.Controller:Possess',self=pc,InPawn=(me,'self'))
    g.do('/Script/Engine.Controller:ResetIgnoreMoveInput',self=pc)
    g.do('/Script/Engine.Controller:ResetIgnoreLookInput',self=pc)
    g.do('/Script/UMG.WidgetBlueprintLibrary:SetInputMode_GameOnly',PlayerController=pc,bFlushInput=True)
    widget=g.ref();g.node(widget,'create_widget',2700,0,class_path=cls(HUD));g.put(widget,'OwningPlayer',pc)  # 5.9 Hayba: the class is typed at creation
    g.chain(g.tail,widget);g.tail=widget;g.setv('HUD',(widget,'ReturnValue'))
    g.do('/Script/UMG.UserWidget:AddToViewport',self=g.getv('HUD'))
    g.do('/Script/Engine.PlayerController:SetViewTargetWithBlend',self=pc,NewViewTarget=(me,'self'),BlendTime=0)
    g.setv('Active',True)
    g.own('StartLeg',Index=g.arg('Index'));g.own('RefreshHUD');g.finish()


def deactivate():
    g=G(CAR,'Deactivate')
    gate=g.branch(g.getv('Active'));g.side(gate)
    for name,value in [('Active',False),('Throttle',False),('BrakeHeld',False),('TurnQueued',False),('Speed',0)]:g.setv(name,value)
    g.own('ResetShockwave')
    g.do(cls(MET)+':Hide',self=g.getv('Meteor'))
    g.do(cls(MET)+':ResetImpact',self=g.getv('Meteor'))
    reset_storm(g)
    from free_drive import hide_sign
    hide_sign(g)
    pc=g.f(GS+'GetPlayerController',PlayerIndex=0)
    sub=g.f('/Script/Engine.SubsystemBlueprintLibrary:GetLocalPlayerSubSystemFromPlayerController',
            PlayerController=pc,Class='/Script/EnhancedInput.EnhancedInputLocalPlayerSubsystem')
    sub=g.cast(sub,'/Script/EnhancedInput.EnhancedInputLocalPlayerSubsystem','Enhanced Input Local Player Subsystem')
    g.do('/Script/EnhancedInput.EnhancedInputSubsystemInterface:RemoveMappingContext',self=sub,
         MappingContext=D.ROOT+'/Input/IMC_L2Drive.IMC_L2Drive')
    g.do('/Script/UMG.Widget:RemoveFromParent',self=g.getv('HUD'))
    valid=g.branch(g.f(SL+'IsValid',Object=g.getv('ReturnPawn')));g.side(valid)
    g.do('/Script/Engine.Controller:Possess',self=pc,InPawn=g.getv('ReturnPawn'))
    g.do('/Script/Engine.PlayerController:SetViewTargetWithBlend',self=pc,NewViewTarget=g.getv('ReturnPawn'),BlendTime=.2)
    g.finish()


def start_leg(job_hunt=False):
    import drive_rails
    return drive_rails.start_leg()


def move():
    from free_drive import move as free_move
    free_move()



def schedule():
    from free_drive import schedule as free_schedule
    free_schedule()


def drive_step():
    g=G(CAR,'DriveStep');dt=g.arg('Delta')
    active=g.branch(g.getv('Active'));g.side(active)
    g.setv('Clock',g.math('Add_DoubleDouble',A=g.getv('Clock'),B=dt))
    b=g.branch(g.getv('Failed'));g.side(b)
    due=g.branch(g.math('GreaterEqual_DoubleDouble',A=g.getv('Clock'),B=g.getv('RestartAt')));g.side(due)
    integrated=g.branch(g.f(SL+'IsValid',Object=g.getv('Journey')));g.side(integrated)
    journey=g.cast(g.getv('Journey'),cls(JOURNEY),'BP L2Journey')
    g.do(cls(JOURNEY)+':RestartRun',self=journey)
    g.side(integrated,False);g.own('StartLeg',Index=0)
    g.side(b,False);moving=g.branch(g.math('Not_PreBool',A=g.getv('Arrived')));g.side(moving)
    g.own('Move',Delta=dt)
    still=g.branch(g.math('BooleanAND',A=g.getv('Active'),B=g.math('Not_PreBool',A=g.getv('Arrived'))));g.side(still)
    g.do(cls(ROAD)+':StepTraffic',self=g.getv('Road'),Delta=dt,Driver=g.f(A+'K2_GetActorLocation'))
    g.own('Schedule');g.own('RefreshHUD');g.finish()


def resolve_hit():
    g=G(CAR,'ResolveHit')
    g.setv('Composure',g.math('Max',A=0,B=g.math('Subtract_IntInt',A=g.getv('Composure'),B=g.arg('Cost'))))
    g.setv('LastOutcome',g.arg('Outcome'));g.setv('HitsResolved',g.math('Add_IntInt',A=g.getv('HitsResolved'),B=1))
    value=g.f('/Script/Engine.KismetStringLibrary:Conv_IntToString',InInt=g.getv('Composure'))
    line=g.f('/Script/Engine.KismetStringLibrary:Concat_StrStr',A='L2 impact Composure ',B=value)
    g.do(SL+'PrintString',InString=line,bPrintToScreen=False,bPrintToLog=True)
    b=g.branch(g.math('LessEqual_IntInt',A=g.getv('Composure'),B=0));g.side(b);g.own('Restart');g.finish()


def restart():
    g=G(CAR,'Restart');gate=g.branch(g.math('Not_PreBool',A=g.getv('Failed')));g.side(gate)
    g.own('ResetShockwave')
    for n,v in [('Failed',True),('Speed',0),('Throttle',False),('BrakeHeld',False),('TurnQueued',False),
                ('Place','Another morning.'),('Cue','')]:g.setv(n,v)
    g.setv('RestartAt',g.math('Add_DoubleDouble',A=g.getv('Clock'),B=2))
    g.setv('RoadAttempts',g.math('Add_IntInt',A=g.getv('RoadAttempts'),B=1))
    g.do(cls(MET)+':Hide',self=g.getv('Meteor'));g.own('RefreshHUD')
    cam=g.f(GS+'GetPlayerCameraManager',PlayerIndex=0)
    g.do('/Script/Engine.PlayerCameraManager:StartCameraFade',self=cam,FromAlpha=0,ToAlpha=1,Duration=.7,Color='(R=0,G=0,B=0,A=1)',bShouldFadeAudio=False,bHoldWhenFinished=False)
    g.finish()


def simple(name):
    if name=='Continue':
        from free_drive import park
        return park()
    g=G(CAR,name)
    if name=='Brace':g.do(cls(MET)+':AcceptBrace',self=g.getv('Meteor'))
    if name=='QueueTurn':g.setv('TurnQueued',False)  # Q is held look-behind in UpdateCamera.
    if name=='ChangeLane':
        g.setv('Lane',g.math('FClamp',Value=g.arg('Side'),Min=-1,Max=1))
        g.setv('LaneChanges',g.math('Add_IntInt',A=g.getv('LaneChanges'),B=1))
    if name=='RefreshHUD':
        g.do(cls(HUD)+':RefreshProgress',self=g.getv('HUD'),Value=g.getv('Employability'))
        met=g.getv('Meteor');age=g.getv('Age',met,MET)
        cue=g.math('SelectString',A='Brace now [Space or A]',B='Sand incoming. Steer clear.',
                bPickA=g.math('GreaterEqual_DoubleDouble',A=age,B=D.TELEGRAPH-D.BRACE_WINDOW))
        text=g.f('/Script/Engine.KismetTextLibrary:Conv_StringToText',InString=cue)
        active=g.branch(g.getv('Active',met,MET));g.side(active)
        g.do(cls(HUD)+':Refresh',self=g.getv('HUD'),Value=g.getv('Composure'),Location=g.getv('Place'),Prompt=text)
        g.side(active,False)
        g.do(cls(HUD)+':Refresh',self=g.getv('HUD'),Value=g.getv('Composure'),Location=g.getv('Place'),Prompt=g.getv('Cue'))
    g.finish()


def meteor_arm():
    g=G(MET,'Arm')
    for n,v in [('Age',0),('Active',True),('Impacted',False),('Inside',False),('Braced',False),('Late',False),('NearStrike',False)]:g.setv(n,v)
    g.do(A+'K2_SetActorLocation',NewLocation=g.arg('Position'),bSweep=False,bTeleport=True)
    g.do(SC+'K2_SetRelativeLocation',self=g.getv('Shadow'),NewLocation=f'0,0,{D.FALL_HEIGHT}',bSweep=False,bTeleport=True)
    for name in ('Shadow','Ring'):
        g.do(SC+'SetVisibility',self=g.getv(name),bNewVisibility=True,bPropagateToChildren=False)
    g.do(A+'SetActorHiddenInGame',bNewHidden=False)
    g.do(GS+'PlaySound2D',Sound='/Game/FoA/Audio/SFX/Dream/SFX_Dream_ReverseSwell_01.SFX_Dream_ReverseSwell_01',VolumeMultiplier=.3)
    g.finish()


def meteor_step():
    g=G(MET,'Step');g.own('UpdateImpact');b=g.branch(g.getv('Active'));g.side(b)
    g.setv('Age',g.math('Add_DoubleDouble',A=g.getv('Age'),B=g.arg('Delta')))
    progress=g.math('FClamp',Value=g.math('Divide_DoubleDouble',A=g.getv('Age'),B=D.TELEGRAPH),Min=0,Max=1)
    descent=g.math('Multiply_DoubleDouble',A=progress,B=progress)
    height=g.math('Lerp',A=D.FALL_HEIGHT,B=D.FALL_CONTACT,Alpha=descent)
    g.do(SC+'K2_SetRelativeLocation',self=g.getv('Shadow'),NewLocation=g.math('MakeVector',X=0,Y=0,Z=height),bSweep=False,bTeleport=True)
    # Spin about the vertical: the sand trail rides on the body and must stay a column above it (a roll swung it sideways).
    g.do(SC+'K2_SetRelativeRotation',self=g.getv('Shadow'),NewRotation=g.math('MakeRotator',Yaw=g.math('Multiply_DoubleDouble',A=g.getv('Age'),B=90)),bSweep=False,bTeleport=True)
    radius=g.math('Lerp',A=8,B=4.8,Alpha=progress)
    scale=g.math('MakeVector',X=radius,Y=radius,Z=1)
    g.do(SC+'SetRelativeScale3D',self=g.getv('Ring'),NewScale3D=scale)
    impact=g.branch(g.math('BooleanAND',A=g.math('Not_PreBool',A=g.getv('Impacted')),B=g.math('GreaterEqual_DoubleDouble',A=g.getv('Age'),B=D.TELEGRAPH)))
    g.side(impact);g.own('Impact')
    # Resolve is also called from the false branch so the post-impact grace can elapse.
    g.own('Resolve');g.side(impact,False);g.own('Resolve');g.finish()


def meteor_impact():
    g=G(MET,'Impact');g.setv('Impacted',True)
    car=g.getv('Car');pos=g.f(A+'K2_GetActorLocation');at=g.f(A+'K2_GetActorLocation',self=car)
    distance=g.math('Vector_Distance2D',V1=pos,V2=at)
    g.setv('Inside',g.math('LessEqual_DoubleDouble',A=distance,B=240))
    g.setv('NearStrike',g.math('BooleanAND',A=g.math('LessEqual_DoubleDouble',A=distance,B=D.CITY_PRESSURE_RADIUS),
                             B=g.math('Less_IntInt',A=g.getv('MeteorsLeft',car,CAR),B=0)))
    split=g.f(K+'BreakVector',InVec=pos)
    clock=g.f(GS+'GetTimeSeconds')
    color=g.math('MakeColor',R=(split[0],'X'),G=(split[0],'Y'),B=clock,A=1)
    g.do('/Script/Engine.KismetMaterialLibrary:SetVectorParameterValue',Collection=CITY_MPC,ParameterName='Impact0',ParameterValue=color)
    g.setv('ImpactStarted',clock)
    for name in ('Shadow','Ring'):
        g.do(SC+'SetVisibility',self=g.getv(name),bNewVisibility=False,bPropagateToChildren=False)
    sand=cls('/Game/FoA/VFX/Sand/BPL_SandFX')
    g.do(sand+':SpawnSandBurst',Location=pos,Scale=3.2)
    g.do(sand+':SpawnSandBloom',Location=pos,Size=5.5,Seconds=2.6,Crumble=True)
    g.do(GS+'PlaySound2D',Sound='/Game/FoA/Audio/SFX/Dream/SFX_Dream_LowImpact_01.SFX_Dream_LowImpact_01',VolumeMultiplier=.4)
    g.finish()


def reset_storm(g):
    for parameter in ('SandProgress','SandRadius'):
        g.do(ML+'SetScalarParameterValue',Collection=CITY_MPC,ParameterName=parameter,ParameterValue=0)


def meteor_resolve():
    g=G(MET,'Resolve');b=g.branch(g.math('GreaterEqual_DoubleDouble',A=g.getv('Age'),B=D.TELEGRAPH+D.LATE_GRACE));g.side(b)
    cost=g.math('SelectInt',A=15,B=40,bPickA=g.getv('Late'))
    near=g.math('SelectInt',A=D.CITY_PRESSURE_COST,B=0,bPickA=g.getv('NearStrike'))
    cost=g.math('SelectInt',A=cost,B=near,bPickA=g.getv('Inside'))
    cost=g.math('SelectInt',A=0,B=cost,bPickA=g.getv('Braced'))
    # Outcome is the cost name in logs; avoided/braced remain distinct through the meteor flags.
    outcome=g.f('/Script/Engine.KismetStringLibrary:Conv_IntToString',InInt=cost)
    outcome=g.f('/Script/Engine.KismetStringLibrary:Conv_StringToName',InString=outcome)
    g.do(cls(CAR)+':ResolveHit',self=g.getv('Car'),Cost=cost,Outcome=outcome)
    g.own('Hide');g.finish()


def meteor_brace():
    g=G(MET,'AcceptBrace');gate=g.branch(g.getv('Active'));g.side(gate)
    age=g.getv('Age')
    valid=g.math('BooleanAND',A=g.math('GreaterEqual_DoubleDouble',A=age,B=D.TELEGRAPH-D.BRACE_WINDOW),B=g.math('Less_DoubleDouble',A=age,B=D.TELEGRAPH))
    b=g.branch(valid);g.side(b);g.setv('Braced',True);g.side(b,False)
    late=g.branch(g.math('BooleanAND',A=g.math('GreaterEqual_DoubleDouble',A=age,B=D.TELEGRAPH),B=g.math('LessEqual_DoubleDouble',A=age,B=D.TELEGRAPH+D.LATE_GRACE)))
    g.side(late);g.setv('Late',True);g.finish()


def meteor_hide():
    g=G(MET,'Hide');g.setv('Active',False);g.do(A+'SetActorHiddenInGame',bNewHidden=True);g.finish()


def meteor_update_impact():
    g=G(MET,'UpdateImpact')
    running=g.branch(g.math('GreaterEqual_DoubleDouble',A=g.getv('ImpactStarted'),B=0));g.side(running)
    age=g.math('Subtract_DoubleDouble',A=g.f(GS+'GetTimeSeconds'),B=g.getv('ImpactStarted'))
    # Let the short shockwave race ahead of the creeping sand.
    stage=g.math('Clamp',Value=g.getv('HitsResolved',g.getv('Car'),CAR),Min=0,Max=5)
    stage=g.math('Divide_DoubleDouble',A=g.math('Conv_IntToDouble',InInt=stage),B=5)
    radius=g.math('Lerp',A=D.STORM_MIN_RADIUS,B=D.STORM_MAX_RADIUS,Alpha=stage)
    spread=g.math('FClamp',Value=g.math('Divide_DoubleDouble',A=age,B=D.SHOCKWAVE_DURATION),Min=0,Max=1)
    g.do(ML+'SetVectorParameterValue',Collection=CITY_MPC,ParameterName='SandCentre',
         ParameterValue=g.math('Conv_VectorToLinearColor',InVec=g.f(A+'K2_GetActorLocation')))
    g.do(ML+'SetScalarParameterValue',Collection=CITY_MPC,ParameterName='SandRadius',
         ParameterValue=g.math('Multiply_DoubleDouble',A=radius,B=spread))
    g.do(ML+'SetScalarParameterValue',Collection=CITY_MPC,ParameterName='SandProgress',
         ParameterValue=g.math('Lerp',A=.25,B=.65,Alpha=stage))
    # Vertex dynamics owns propagation; Blueprint only expires the shared hit.
    ended=g.branch(g.math('GreaterEqual_DoubleDouble',A=age,B=D.SHOCKWAVE_DURATION));g.side(ended)
    g.own('ResetImpact');g.finish()


def meteor_reset_impact():
    g=G(MET,'ResetImpact');g.setv('ImpactStarted',-10)
    cleared=g.math('MakeColor',R=0,G=0,B=-10000,A=0)
    g.do(ML+'SetVectorParameterValue',Collection=CITY_MPC,
         ParameterName='Impact0',ParameterValue=cleared)
    g.finish()


STEPS = {'skeleton':skeleton,'components':components,'compile':compile_all,'widget':widget,'BP_L2Car.Begin':begin,'BP_L2Car.SetRail':set_rail,'BP_L2Car.StartLeg':start_leg,
         'BP_L2Car.Activate':activate,'BP_L2Car.Deactivate':deactivate,
         'BP_L2Car.Move':move,'BP_L2Car.Schedule':schedule,
         'BP_L2Car.DriveStep':drive_step,'BP_L2Car.ResolveHit':resolve_hit,'BP_L2Car.Restart':restart,
         'BP_Meteor.Arm':meteor_arm,'BP_Meteor.Step':meteor_step,'BP_Meteor.Impact':meteor_impact,
         'BP_Meteor.Resolve':meteor_resolve,'BP_Meteor.AcceptBrace':meteor_brace,'BP_Meteor.Hide':meteor_hide}
STEPS.update({'BP_Meteor.UpdateImpact':meteor_update_impact,'BP_Meteor.ResetImpact':meteor_reset_impact})
STEPS['distance_editable']=lambda:call('blueprint_add_variable',path=CAR,variable_name='Distance',variable_type='float',instance_editable=True,update_existing=True)
STEPS['roads']=lambda:call('python_exec_file',path='P:/FoA/Tools/Unreal/level2/drive_setup.py',env={'FOA_DRIVE_SETUP':'roads'},resources=['asset:'+D.ROOT])
STEPS['lifecycle_defaults']=lifecycle_defaults
STEPS['widget_polish']=widget_polish
STEPS['free_setup']=lambda:__import__('free_drive').setup()
STEPS['shockwave_setup']=lambda:__import__('car_shockwave').setup()
STEPS['BP_L2Car.UpdateShockwave']=lambda:__import__('car_shockwave').update()
STEPS['BP_L2Car.ResetShockwave']=lambda:__import__('car_shockwave').reset()
STEPS['BP_L2Car.PlaceAtCheckpoint']=lambda:__import__('free_drive').checkpoint()
STEPS['BP_L2Car.CheckDestination']=lambda:__import__('free_drive').destination()
STEPS['BP_L2Car.CheckShelter']=lambda:__import__('free_drive').shelter()
STEPS['camera']=lambda:__import__('drive_camera').build()
STEPS['camera_wire']=lambda:__import__('drive_camera').wire()
for _name in ('Brace','QueueTurn','ChangeLane','Continue','RefreshHUD'):
    STEPS['BP_L2Car.'+_name] = lambda name=_name:simple(name)
for _name in ('BP_L2Car','BP_L2RoadNetwork','BP_Meteor','WBP_L2Drive'):
    STEPS['capture.'+_name]=lambda name=_name:capture(name)
# Rails/QTE drive (drive lane, 2026-11-17): drive_rails.py owns these graphs; the free-drive builders above would
# bring the steering back. AdvanceRail and QueueTurn are no longer called by anything.
for _key in ('Move','Schedule','StartLeg','PlaceAtCheckpoint','CheckDestination','DriveStep','ResolveHit','RefreshHUD',
             'UpdateCamera','Deactivate','ChangeLane','AutoPark'):
    STEPS['BP_L2Car.'+_key]=lambda key=_key:__import__('drive_rails').STEPS['BP_L2Car.'+key]()
for _key in ('Arm','Impact','Resolve','AcceptBrace'):
    STEPS['BP_Meteor.'+_key]=lambda key=_key:__import__('drive_rails').STEPS['BP_Meteor.'+key]()
STEPS['camera']=STEPS['BP_L2Car.UpdateCamera']


if __name__=='__main__':
    D.OWNER=os.environ.get('FOA_AGENT',D.OWNER)
    os.environ['FOA_AGENT']=os.environ['HAYBA_AGENT_ID']=D.OWNER
    step=sys.argv[1]
    editor_lock.acquire(D.OWNER,wait_s=300,ttl=180,areas=[D.ROOT])
    try:
        assert not call('editor_get_state')['pie_running']
        STEPS[step]()
    finally:
        # Even a failed batch must leave all our Blueprints compiling before another lane gets PIE.
        for p in (ROAD,CAR,MET,HUD):
            if Path('P:/FoA/Content'+p[5:]+'.uasset').exists():
                result=h.call('blueprint_compile',{'path':p})
                assert result.get('ok') and not result.get('data',{}).get('error_count'),result
        editor_lock.release(D.OWNER)
