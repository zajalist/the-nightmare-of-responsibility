"""Approved battle B, in-place Hayba presentation patch. Caller holds battle-ui UI + WBP lease.

Steps are small, compile/save before returning. Never run the old encounter tree builders afterwards.
The original buttons, handlers, roster and prompt are retained. No encounter rules are authored here.
"""
import json
import math
import os
from pathlib import Path
import sys

sys.path[:0] = ['P:/FoA/Tools/Unreal', 'P:/FoA/Tools/Unreal/ui']
import hayba_call as hc
from hayba_batch import B as BaseBatch, graph as paged_graph

WBP = '/Game/FoA/Gameplay/Encounter/WBP_Encounter'
SB = '/Game/FoA/UI/Widgets/Common/WBP_SandButton.WBP_SandButton_C'
ENC = '/Game/FoA/Gameplay/Encounter/BP_Encounter.BP_Encounter_C'
GAR = '/Game/FoA/Gameplay/Encounter/BP_Garment.BP_Garment_C'
MOVE = '/Game/FoA/Gameplay/Encounter/PDA_Move.PDA_Move_C'
MAT = '/Game/FoA/UI/Materials'
MI = MAT + '/MI_UI_BattleCardGrain'
ICONS = '/Game/FoA/Gameplay/Encounter/Icons'
OUT = Path('P:/FoA/Saved/UIShots/battle_ui_b')
K = '/Script/Engine.KismetMathLibrary'
U = '/Script/UMG.'
CARDS = ('Act0', 'Act1', 'Act2', 'Breathe', 'Mirror', 'Items', 'Flee')


def graph(path,name):
    d=c('blueprint_inspect_graph',path=path,graph_name=name)
    if 'page' in d:return paged_graph(path,name)
    assert len(d['nodes'])==d['node_count'] and len(d['edges'])==d['edge_count'],d.keys()
    return d['nodes'],d['edges']


class B(BaseBatch):
    def run(self):
        before,edges=graph(self.path,self.g)
        try:
            result=super().run()
            compile_result=c('blueprint_compile',path=self.path)
            assert compile_result.get('error_count')==0,compile_result
            return result
        except Exception:
            # Hayba batches are not atomic: restore this graph before the lease can be released.
            after,_=graph(self.path,self.g)
            ids={n['node_id'] for n in before}
            added=[n['node_id'] for n in after if n['node_id'] not in ids]
            if added:c('blueprint_remove_nodes',path=self.path,graph_name=self.g,node_ids=added)
            ops=[dict(op='connect',**edge) for edge in edges]
            if ops:c('blueprint_graph_batch',path=self.path,graph_name=self.g,ops=ops)
            restored=c('blueprint_compile',path=self.path,save=True)
            assert restored.get('error_count')==0,restored
            raise


def c(cmd, **params):
    r = hc.call(cmd, params)
    d = r.get('data') or {}
    assert r.get('ok') and d.get('ok', True), (cmd, r)
    assert not any(d.get(k) for k in ('failed_properties', 'unknown_slot_props', 'failed')), (cmd, d)
    return d


def finish():
    assert not c('editor_get_state')['pie_running']
    r = c('blueprint_compile', path=WBP, save=True)
    assert r.get('error_count') == 0, r
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / ('compile_' + sys.argv[1] + '.json')).write_text(json.dumps(r, indent=2))
    print('WBP_Encounter compiled and saved', r.get('error_count'), r.get('warning_count'))


def props(n, p=None, s=None):
    return c('ui_set_widget_properties', widget_blueprint_path=WBP, widget_name=n,
             **({'properties': p} if p else {}), **({'slot_props': s} if s else {}))


def add(n, parent='RootCanvas'):
    if not c('ui_query', path=WBP, name_pattern=n['name']).get('matches'):
        c('ui_build_tree', widget_blueprint_path=WBP, parent_widget_name=parent, tree=n)


def move(n, parent, **slot):
    match = c('ui_query', path=WBP, name_pattern=n)['matches']
    exact = next(w for w in match if w['name'] == n)
    if exact['parent'] != parent:
        c('ui_mutate_tree', operation='reparent', widget_blueprint_path=WBP,
          widget_name=n, new_parent_name=parent, slot_props=slot)
    elif slot:
        props(n, s=slot)


def var(n):
    c('ui_set_variable', widget_blueprint_path=WBP, widget_name=n, is_variable=True)


def slot(x, y, w, h, anchor=(0, 0), align=(0, 0)):
    return dict(anchors_min=list(anchor), anchors_max=list(anchor), alignment=list(align),
                position=[x, y], size=[w, h], auto_size=False)


def text(n, t='', size=22, mono=False):
    font = '/Game/FoA/UI/Fonts/F_FoA_Mono.F_FoA_Mono' if mono else '/Game/FoA/UI/Fonts/F_FoA_UI.F_FoA_UI'
    return dict(name=n, **{'class': 'TextBlock'}, properties=dict(Text=t,
        Font=dict(FontObject=font, TypefaceFontName='Regular' if mono else 'SemiBold', Size=size),
        ColorAndOpacity={'SpecifiedColor': [.9, .9, .9, 1]}, AutoWrapText=True,
        Justification='Center', Visibility='HitTestInvisible'))


def image(n, resource, s, tint=1):
    return dict(name=n, **{'class': 'Image'}, slot_props=s, properties=dict(
        Brush=f'(ResourceObject="{resource}",DrawAs=Image)',
        ColorAndOpacity=f'(R={tint},G={tint},B={tint},A=1)', Visibility='HitTestInvisible'))


def textures():
    # Original procedural masks, generated outside Content and imported once. No external assets.
    from PIL import Image, ImageDraw
    import random
    dst = Path(os.environ['TEMP']) / 'hayba-asset-connectors/foa/battle_torn'
    dst.mkdir(parents=True, exist_ok=True)
    mask = Image.new('RGBA', (256, 320))
    d = ImageDraw.Draw(mask)
    d.rectangle((14, 14, 241, 305), fill='white')
    rng = random.Random(180)
    for _ in range(14000):
        side = rng.randrange(4)
        x, y = [(rng.uniform(8,248),14),(rng.uniform(8,248),305),(14,rng.uniform(8,312)),(241,rng.uniform(8,312))][side]
        x, y = round(x+rng.gauss(0,4)), round(y+rng.gauss(0,4))
        if 0 <= x < 256 and 0 <= y < 320:
            mask.putpixel((x,y), (255,255,255,0 if rng.random()<.6 else 255))
    mask.save(dst / 'T_Battle_TornMask.png')
    button = Image.new('RGBA',(128,128)); d=ImageDraw.Draw(button)
    d.ellipse((17,17,111,111),outline='white',width=5)
    for x in (48,80):
        for y in (48,80): d.ellipse((x-5,y-5,x+5,y+5),fill='white')
    button.save(dst/'T_Battle_Button.png')
    for name in ('TornMask','Button'):
        if not Path(f'P:/FoA/Content/FoA/Gameplay/Encounter/Icons/T_Battle_{name}.uasset').exists():
            c('asset_import',source_file=str(dst/f'T_Battle_{name}.png'),destination_path=ICONS,asset_type='texture')
    if not Path('P:/FoA/Content/FoA/UI/Materials/MI_UI_BattleCardGrain.uasset').exists():
        c('material_create_instance', parent_material_path=MAT+'/M_UI_SandText', package_path=MAT, name='MI_UI_BattleCardGrain')
    for n,v in {'Ink':[.018,.018,.018,1], 'Calm':[.55,1,0,0], 'Scale':2.2, 'Reveal':1, 'Glint':.08}.items():
        c('material_set_param',instance_path=MI,param_name=n,value=v)
    c('python_exec_file',path='P:/FoA/Tools/Unreal/ui/battle_torn_prepare.py',
      env={'FOA_TORN_SAVE':'1'},resources=['asset:'+WBP,'asset:'+MI,'asset:'+ICONS])


def layout():
    # Native horizontal layout shrinks when RefreshAct collapses an unavailable action.
    add(dict(name='TornDeck', **{'class':'HorizontalBox'}, slot_props=slot(0,-100,0,236,(.5,1),(.5,1))))
    props('TornDeck',s={'auto_size':True}); var('TornDeck')
    move('ActCards','TornDeck',padding=[0,0,0,0],fill=0)
    props('ActCards',{'Visibility':'SelfHitTestInvisible'})
    for i,name in enumerate(CARDS):
        host='TornCard_'+name
        panel={'class':'Overlay','name':host,'properties':{'Clipping':'Inherit'},'children':[
            {'class':'SizeBox','name':'TornSize_'+name,'properties':{'WidthOverride':174.,'HeightOverride':236.,
                'bOverride_WidthOverride':True,'bOverride_HeightOverride':True,'Visibility':'HitTestInvisible'},'children':[
                {'class':'CanvasPanel','name':'TornFace_'+name,'children':[
                    {'class':'RetainerBox','name':'TornGrain_'+name,'slot_props':slot(-6,-6,186,248),
                     'properties':{'EffectMaterial':MI+'.MI_UI_BattleCardGrain','TextureParameter':'Texture','Visibility':'HitTestInvisible'},
                     'children':[image('TornMask_'+name,ICONS+'/T_Battle_TornMask.T_Battle_TornMask',{})]},
                    image('TornGlyph_'+name,ICONS+'/T_Battle_'+('Button' if name=='Act1' else 'Act' if name.startswith('Act') else name)+'.T_Battle_'+('Button' if name=='Act1' else 'Act' if name.startswith('Act') else name),slot(51,62,72,72),.86),
                    {'class':'HorizontalBox','name':'TornPips_'+name,'slot_props':slot(63,25,54,10),'properties':{'Visibility':'HitTestInvisible'},'children':[
                        {'class':'SizeBox','name':f'TornPipSize_{name}{j}','slot_props':{'padding':[3,0,3,0]},
                         'properties':{'WidthOverride':8.,'HeightOverride':8.,'bOverride_WidthOverride':True,'bOverride_HeightOverride':True},
                         'children':[image(f'TornPip_{name}{j}','/Engine/EngineResources/WhiteSquareTexture.WhiteSquareTexture',{})]} for j in range(3)]}
                ]}]}]}
        add(panel,'ActCards' if name.startswith('Act') else 'TornDeck')
        if name.startswith('Act'):
            move('ActCard'+str(i),host,Padding={'Left':0,'Top':0,'Right':0,'Bottom':0},HorizontalAlignment='HAlign_Fill',VerticalAlignment='VAlign_Fill')
            props('Btn_'+name,s={'fill':1,'padding':[0,0,0,0]})
            props('Txt_'+name+'Detail',{'Visibility':'Collapsed'})
        else:
            move('Btn_'+name,host,Padding={'Left':0,'Top':0,'Right':0,'Bottom':0},HorizontalAlignment='HAlign_Fill',VerticalAlignment='VAlign_Fill')
            # These remain disabled by RefreshCommands; keep their existing handlers and availability.
            props('Btn_'+name,{'Visibility':'Visible'})
        props(host,s={'fill':0,'padding':[5,0,5,0]})
        props('Btn_'+name,{'bPlainLabel':True,'LabelSize':25.,'TextAlphaRest':.82,'TextAlphaHover':1.,'TextAlphaDisabled':.35,
            'HoverSound':"/Script/MetasoundEngine.MetaSoundSource'/Game/FoA/Audio/MetaSounds/Battle/S_Battle_Select.S_Battle_Select'",
            'ClickSound':"/Script/MetasoundEngine.MetaSoundSource'/Game/FoA/Audio/MetaSounds/Battle/S_Battle_Confirm.S_Battle_Confirm'",'Clipping':'Inherit'})
        for n in (host,'TornGrain_'+name,'TornPips_'+name,'TornGlyph_'+name):var(n)
    for i in range(3):
        c('ui_mutate_tree',operation='move',widget_blueprint_path=WBP,widget_name='TornCard_Act'+str(i),index=i)
    for n in ('Txt_BreatheDetail','Txt_MirrorDetail','Txt_NextTargetDetail'):
        props(n,{'Visibility':'Collapsed'})
    # Keep Change target available independently of the hand, under the unchanged target list.
    move('Btn_NextTarget','RootCanvas',**slot(-48,210,400,52,(1,0),(1,0)))
    props('Btn_NextTarget',{'bPlainLabel':True,'LabelSize':23.})
    props('CommandPanel',{'RenderOpacity':0.,'Visibility':'HitTestInvisible'})
    detail=text('Txt_TornDetail','',22,True);detail['slot_props']=slot(0,-380,1120,72,(.5,1),(.5,1))
    add(detail);var('Txt_TornDetail')
    # Intent belongs to the garment, independently of command visibility.
    add({'class':'CanvasPanel','name':'TornIntent','slot_props':slot(800,300,190,180),'properties':{'Visibility':'HitTestInvisible'},'children':[
        image('TornIntentBody',MAT+'/M_UI_InkSurface.M_UI_InkSurface',slot(25,0,140,140)),
        image('TornIntentGlyph',ICONS+'/T_Battle_Act.T_Battle_Act',slot(66,28,58,58),.8),
        dict(text('Txt_TornIntent','',20),slot_props=slot(-30,130,250,72))]})
    var('TornIntent');var('Txt_TornIntent')
    finish()


def lookup():
    ns,es=graph(WBP,'RefreshAct')
    cards=next(n['node_id'] for n in ns if n['title']=='Get ActCards')
    child=next(n['node_id'] for n in ns if n['title']=='GetChildAt' and
               any(e['from_node']==cards and e['to_node']==n['node_id'] and e['to_pin']=='self' for e in es))
    outer=next(e['to_node'] for e in es if e['from_node']==child and e['to_pin']=='Object')
    oldout=next(p['name'] for n in ns if n['node_id']==outer for p in n['pins'] if p['name'].startswith('As'))
    button=next(n['node_id'] for n in ns if n['title']=='Cast To WBP_SandButton')
    button_child=next(e['from_node'] for e in es if e['to_node']==button and e['to_pin']=='Object')
    inner_cast=next(e['from_node'] for e in es if e['to_node']==button_child and e['to_pin']=='self')
    if inner_cast!=outer:
        # Comments are not returned by graph inspection. Verify wiring, and flatten old duplicate wraps.
        getter=next(e['from_node'] for e in es if e['to_node']==inner_cast and e['to_pin']=='Object')
        extras=[n['node_id'] for n in ns if n['title']=='Cast To PanelWidget' and n['node_id'] not in (outer,inner_cast)]
        if not extras:return
        remove=extras+[e['from_node'] for e in es if e['to_node'] in extras and e['to_pin']=='Object']
        b=B(WBP,'RefreshAct');b.ops.append(dict(op='remove',node_ids=remove))
        b.link(outer,oldout,getter,'self');b.chain(outer,inner_cast);b.run();finish();return
    b=B(WBP,'RefreshAct')
    inner=b.fn(U+'PanelWidget:GetChildAt',self=(outer,oldout),Index=1)
    cast=b.node('cast',class_path=U+'PanelWidget',pins={'Object':inner})
    # Native cast output is AsPanelWidget; keep both original button/detail indices intact.
    consumers=[e for e in es if e['from_node']==outer and e['from_pin']==oldout]
    for e in consumers:
        b.ops.append(dict(op='disconnect',node_id=e['to_node'],pin_name=e['to_pin']))
        b.link(cast,'AsPanel Widget',e['to_node'],e['to_pin'])
    follow=next(e for e in es if e['from_node']==outer and e['from_pin']=='then')
    b.ops.append(dict(op='disconnect',node_id=outer,pin_name='then'))
    b.chain(outer,cast);b.link(cast,'then',follow['to_node'],follow['to_pin'])
    b.ops.append(dict(op='comment',title='Torn card lookup',node_ids=[inner,cast],color=[.3,.22,.1]))
    b.run();finish()


def stubs():
    for name in ('Txt_BreatheDetail','Txt_MirrorDetail','Txt_NextTargetDetail'):
        var(name)
    info=c('blueprint_get_info',path=WBP)
    variables={v['name'] for v in info['variables']}
    for n,t,d in [('TornAge','double','0'),('TornDepart','double','1'),('TornDelta','double','0'),
                  ('TornChosen','int','-1'),('TornTargetX','double','800'),('TornTargetY','double','400'),
                  ('TornViewX','double','1920'),('TornViewY','double','1080'),
                  ('TornFromX','double','0'),('TornFromY','double','0'),('TornOffsetY','double','0')]+[
                  ('TornLift'+n,'double','0') for n in CARDS]+[('TornCost'+str(i),'int','0') for i in range(3)]:
        if n not in variables:
            c('blueprint_add_variable',path=WBP,variable_name=n,variable_type=t,default_value=d,category='Torn cards')
    obj=lambda cls:'object:'+cls
    specs={'TornTick':[('Delta','double')], 'TornTrackIntent':[], 'TornConfigureAll':[],
           'TornRememberCard':[('Index','int'),('Card',obj(U+'Widget')),('FromY','double')],
           'TornCost':[('Index','int'),('Cost','int')], 'TornConfigure':[('Button',obj(SB))],
           'TornStep':[('Card',obj(U+'Widget')),('Button',obj(SB)),('Grain',obj(U+'RetainerBox')),
                       ('Pips',obj(U+'PanelWidget')),('Detail',obj(U+'TextBlock')),('Index','int'),
                       ('Tilt','double'),('Lift','double'),('Cost','int')]}
    for name,inputs in specs.items():
        if name not in info['functions']:
            c('blueprint_add_function',path=WBP,function_name=name,inputs=[{'name':n,'type':t} for n,t in inputs],
              **({'outputs':[{'name':'NewLift','type':'double'}]} if name=='TornStep' else {}))
    finish()


def newgraph(name):
    ns,es=graph(WBP,name)
    e=next(n['node_id'] for n in ns if n['title'].replace(' ','')==name)
    bodies=[n for n in ns if n['node_id']!=e and not n['title'].startswith('Return')]
    assert not bodies, f'{name} already contains a body; inspect before changing it'
    return B(WBP,name),e,next((n['node_id'] for n in ns if n['title'].startswith('Return')),None)


def run(b,title):
    b.ops.append(dict(op='comment',title=title,node_ids=[o['ref'] for o in b.ops if o['op']=='add_node'],color=[.3,.22,.1]))
    b.run();finish()


def configure():
    b,e,_=newgraph('TornConfigure');button=(e,'Button')
    size=b.get('SizeBox_0',SB,button)
    height=b.fn(U+'SizeBox:SetHeightOverride',self=size,InHeightOverride=252.)
    width=b.fn(U+'SizeBox:SetWidthOverride',self=size,InWidthOverride=202.)
    label=b.get('Txt_Label',SB,button)
    just=b.fn(U+'TextBlock:SetJustification',self=label,InJustification='Center')
    wrap=b.fn(U+'TextBlock:SetAutoWrapText',self=label,InAutoTextWrap=True)
    ret=b.get('Ret_Sand',SB,button)
    rs=b.fn(U+'WidgetLayoutLibrary:SlotAsOverlaySlot',Widget=ret)
    align=b.fn(U+'OverlaySlot:SetHorizontalAlignment',self=rs,InHorizontalAlignment='HAlign_Fill')
    fill=b.fn(U+'OverlaySlot:SetVerticalAlignment',self=rs,InVerticalAlignment='VAlign_Fill')
    down=b.fn(U+'OverlaySlot:SetPadding',self=rs,InPadding='(Left=0,Top=140,Right=0,Bottom=0)')
    ls=b.fn(U+'WidgetLayoutLibrary:SlotAsOverlaySlot',Widget=label)
    label_h=b.fn(U+'OverlaySlot:SetHorizontalAlignment',self=ls,InHorizontalAlignment='HAlign_Fill')
    label_v=b.fn(U+'OverlaySlot:SetVerticalAlignment',self=ls,InVerticalAlignment='VAlign_Fill')
    label_pad=b.fn(U+'OverlaySlot:SetPadding',self=ls,InPadding='(Left=10,Top=0,Right=10,Bottom=4)')
    hide=[]
    for n in ('Img_Vortex',):
        hide.append(b.fn(U+'Widget:SetVisibility',self=b.get(n,SB,button),InVisibility='Collapsed'))
    focus=b.fn(U+'Widget:SetVisibility',self=b.get('Img_CommandFocus',SB,button),InVisibility='HitTestInvisible')
    b.chain(e,height,width,just,wrap,align,fill,down,label_h,label_v,label_pad,*hide,focus);run(b,'Card hit area')


def costs():
    b,e,_=newgraph('TornCost');prev=e
    for i in range(3):
        eq=b.fn(K+':EqualEqual_IntInt',A=(e,'Index'),B=i)
        gate=b.node('branch',pins={'Condition':eq})
        put=b.set('TornCost'+str(i),(e,'Cost'))
        b.chain(prev,gate,put);prev=(gate,'else')
    run(b,'Read command cost')


def configureall():
    b,e,_=newgraph('TornConfigureAll')
    calls=[b.fn(WBP+'.WBP_Encounter_C:TornConfigure',Button=b.get('Btn_'+n)) for n in CARDS]
    b.chain(e,*calls);run(b,'Fit command buttons')


def commit():
    b,e,_=newgraph('TornRememberCard')
    geo=b.fn(U+'Widget:GetCachedGeometry',self=(e,'Card'))
    absolute=b.fn(U+'SlateBlueprintLibrary:LocalToAbsolute',Geometry=geo,LocalCoordinate='(X=87,Y=118)')
    root=b.fn(U+'Widget:GetCachedGeometry')
    local=b.fn(U+'SlateBlueprintLibrary:AbsoluteToLocal',Geometry=root,AbsoluteCoordinate=absolute)
    xy=b.fn(K+':BreakVector2D',InVec=local)
    b.chain(e,b.set('TornChosen',(e,'Index')),b.set('TornDepart',0.),
            b.set('TornFromX',(xy,'X')),b.set('TornFromY',(xy,'Y')),b.set('TornOffsetY',(e,'FromY')))
    run(b,'Remember focused card')


def stepcard():
    b,e,r=newgraph('TornStep')
    inp=lambda n:(e,n)
    mathfn=lambda name,**p:b.fn(K+':'+name,**p)
    hot=b.get('bHovered',SB,inp('Button'))
    target=mathfn('SelectFloat',A=1.,B=0.,bPickA=hot)
    lift=mathfn('FInterpTo',Current=inp('Lift'),Target=target,DeltaTime=b.get('TornDelta'),InterpSpeed=14.)
    enabled=b.fn(U+'Widget:GetIsEnabled',self=inp('Button'))
    player=b.get('bPlayerTurn',ENC,b.get('Encounter'))
    selected=mathfn('EqualEqual_IntInt',A=inp('Index'),B=b.get('TornChosen'))
    flying=mathfn('BooleanAND',A=selected,B=mathfn('Not_PreBool',A=player))
    age=mathfn('FClamp',Value=mathfn('Divide_DoubleDouble',A=b.get('TornAge'),B=.34),Min=0.,Max=1.)
    depart=mathfn('FClamp',Value=mathfn('Divide_DoubleDouble',A=b.get('TornDepart'),B=.42),Min=0.,Max=1.)
    shrink=mathfn('Lerp',A=1.,B=.18,Alpha=depart)
    normalScale=mathfn('Lerp',A=1.,B=1.09,Alpha=lift)
    scale=mathfn('SelectFloat',A=shrink,B=normalScale,bPickA=flying)
    scaling=b.fn(U+'Widget:SetRenderScale',self=inp('Card'),Scale=mathfn('MakeVector2D',X=scale,Y=scale))
    angle=mathfn('Lerp',A=inp('Tilt'),B=0.,Alpha=lift)
    rotation=b.fn(U+'Widget:SetRenderTransformAngle',self=inp('Card'),Angle=angle)
    y=mathfn('Subtract_DoubleDouble',A=mathfn('Multiply_DoubleDouble',A=mathfn('Abs',A=inp('Tilt')),B=2.25),
             B=mathfn('Multiply_DoubleDouble',A=lift,B=24.))
    # Capture the actual card geometry on commit, so collapsed actions and DPI never shift the flight endpoint.
    dx=mathfn('Subtract_DoubleDouble',A=b.get('TornTargetX'),B=b.get('TornFromX'))
    dy=mathfn('Subtract_DoubleDouble',A=b.get('TornTargetY'),B=b.get('TornFromY'))
    flyX=mathfn('Multiply_DoubleDouble',A=dx,B=depart)
    flyY=mathfn('Add_DoubleDouble',A=b.get('TornOffsetY'),B=mathfn('Multiply_DoubleDouble',A=dy,B=depart))
    translation=mathfn('MakeVector2D',X=mathfn('SelectFloat',A=flyX,B=0.,bPickA=flying),
                       Y=mathfn('SelectFloat',A=flyY,B=y,bPickA=flying))
    position=b.fn(U+'Widget:SetRenderTranslation',self=inp('Card'),Translation=translation)
    rest=mathfn('SelectFloat',A=.85,B=.35,bPickA=enabled)
    brightness=mathfn('Lerp',A=rest,B=1.,Alpha=lift)
    fade=mathfn('SelectFloat',A=1.,B=mathfn('Subtract_DoubleDouble',A=1.,B=depart),bPickA=player)
    opacity=b.fn(U+'Widget:SetRenderOpacity',self=inp('Card'),InOpacity=mathfn('Multiply_DoubleDouble',A=brightness,B=fade))
    mid=b.fn(U+'RetainerBox:GetEffectMaterial',self=inp('Grain'))
    reveal=b.fn('/Script/Engine.MaterialInstanceDynamic:SetScalarParameterValue',self=mid,ParameterName='Reveal',
                 Value=mathfn('SelectFloat',A=age,B=1.,bPickA=player))
    crumble=mathfn('SelectFloat',A=0.,B=depart,bPickA=player)
    state=b.fn('/Script/Engine.MaterialInstanceDynamic:SetVectorParameterValue',self=mid,ParameterName='State',
                Value=mathfn('MakeColor',R=lift,G=0.,B=0.,A=crumble))
    pipOpacity=b.fn(U+'Widget:SetRenderOpacity',self=inp('Pips'),InOpacity=mathfn('SelectFloat',A=1.,B=0.,
                  bPickA=mathfn('Greater_IntInt',A=inp('Cost'),B=0)))
    nodes=[]
    for i in range(3):
        pip=b.fn(U+'PanelWidget:GetChildAt',self=inp('Pips'),Index=i)
        lit=mathfn('Greater_IntInt',A=inp('Cost'),B=i*10)
        nodes.append(b.fn(U+'Widget:SetRenderOpacity',self=pip,InOpacity=mathfn('SelectFloat',A=1.,B=.18,bPickA=lit)))
    show=mathfn('BooleanAND',A=hot,B=player)
    gate=b.node('branch',pins={'Condition':show})
    line=b.fn(U+'TextBlock:GetText',self=inp('Detail'))
    desc=b.fn(U+'TextBlock:SetText',self=b.get('Txt_TornDetail'),InText=line)
    remember=b.fn(WBP+'.WBP_Encounter_C:TornRememberCard',Index=inp('Index'),Card=inp('Card'),FromY=y)
    b.chain(e,scaling,rotation,position,opacity,reveal,state,pipOpacity,*nodes,gate,desc,remember)
    if r:
        b.link(lift,'ReturnValue',r,'NewLift');b.chain(remember,r);b.link(gate,'else',r,'execute')
    run(b,'Fan and grain motion')


def intent():
    b,e,_=newgraph('TornTrackIntent')
    fn=lambda n,**p:b.fn(K+':'+n,**p)
    enc=b.get('Encounter')
    target=b.fn(ENC+':TargetGarment',self=enc)
    garment=(target,'Garment')
    valid=b.fn('/Script/Engine.KismetSystemLibrary:IsValid',Object=garment)
    gate=b.node('branch',pins={'Condition':valid})
    hide=b.fn(U+'Widget:SetVisibility',self=b.get('TornIntent'),InVisibility='Collapsed')
    bounds=b.fn('/Script/Engine.Actor:GetActorBounds',self=garment,bOnlyCollidingComponents=False,bIncludeFromChildActors=True)
    origin=fn('BreakVector',InVec=(bounds,'Origin'));extent=fn('BreakVector',InVec=(bounds,'BoxExtent'))
    point=fn('MakeVector',X=(origin,'X'),Y=(origin,'Y'),Z=fn('Add_DoubleDouble',A=(origin,'Z'),B=(extent,'Z')))
    pc=b.fn('/Script/Engine.GameplayStatics:GetPlayerController',PlayerIndex=0)
    project=b.fn(U+'WidgetLayoutLibrary:ProjectWorldLocationToWidgetPosition',PlayerController=pc,WorldLocation=point,bPlayerViewportRelative=True)
    xy=fn('BreakVector2D',InVec=(project,'ScreenPosition'))
    size=b.fn(U+'WidgetLayoutLibrary:GetViewportSize')
    dims=fn('BreakVector2D',InVec=size);dpi=b.fn(U+'WidgetLayoutLibrary:GetViewportScale')
    width=fn('Divide_DoubleDouble',A=(dims,'X'),B=dpi);height=fn('Divide_DoubleDouble',A=(dims,'Y'),B=dpi)
    sx=b.set('TornViewX',width);sy=b.set('TornViewY',height)
    tx=b.set('TornTargetX',(xy,'X'));ty=b.set('TornTargetY',(xy,'Y'))
    clamp=lambda coord,dim,offset,space:fn('FClamp',Value=fn('Add_DoubleDouble',A=coord,B=offset),
              Min=fn('Multiply_DoubleDouble',A=dim,B=.05),Max=fn('Subtract_DoubleDouble',A=fn('Multiply_DoubleDouble',A=dim,B=.95),B=space))
    pos=fn('MakeVector2D',X=fn('Add_DoubleDouble',A=clamp((xy,'X'),width,24.,250.),B=30.),
           Y=clamp((xy,'Y'),height,-130.,202.))
    cs=b.fn(U+'WidgetLayoutLibrary:SlotAsCanvasSlot',Widget=b.get('TornIntent'))
    place=b.fn(U+'CanvasPanelSlot:SetPosition',self=cs,InPosition=pos)
    line=b.fn(GAR+':StatusLine',self=garment,bRevealed=b.get('bRevealed',ENC,enc))
    textset=b.fn(U+'TextBlock:SetText',self=b.get('Txt_TornIntent'),InText=(line,'Line'))
    onscreen=b.node('branch',pins={'Condition':project})
    show=b.fn(U+'Widget:SetVisibility',self=b.get('TornIntent'),InVisibility='HitTestInvisible')
    b.chain(e,gate,sx,sy,tx,ty,place,textset,onscreen,show)
    b.link(gate,'else',hide,'execute');b.link(onscreen,'else',hide,'execute')
    run(b,'Follow targeted garment')


def tick():
    b,e,_=newgraph('TornTick')
    delta=b.set('TornDelta',(e,'Delta'))
    enc=b.get('Encounter');valid=b.fn('/Script/Engine.KismetSystemLibrary:IsValid',Object=enc)
    gate=b.node('branch',pins={'Condition':valid})
    player=b.get('bPlayerTurn',ENC,enc)
    adv=b.fn(K+':Add_DoubleDouble',A=b.get('TornAge'),B=(e,'Delta'))
    age=b.set('TornAge',b.fn(K+':SelectFloat',A=adv,B=0.,bPickA=player))
    departure=b.set('TornDepart',b.fn(K+':Add_DoubleDouble',A=b.get('TornDepart'),B=(e,'Delta')))
    clear=b.fn(U+'TextBlock:SetText',self=b.get('Txt_TornDetail'))
    track=b.fn(WBP+'.WBP_Encounter_C:TornTrackIntent')
    b.chain(e,delta,gate,age,departure,clear,track);prev=track
    for i,n in enumerate(CARDS):
        button=b.get('Btn_'+n)
        if n.startswith('Act'):cost=b.get('TornCost'+str(i))
        elif n in ('Breathe','Mirror'):
            read=b.fn(ENC+':MoveCost',self=enc,Move=b.get(n+'Move',ENC,enc));cost=(read,'Cost')
        else:cost=0
        detail='Txt_'+n+'Detail' if n not in ('Items','Flee') else 'Txt_NextTargetDetail'
        step=b.fn(WBP+'.WBP_Encounter_C:TornStep',Card=b.get('TornCard_'+n),Button=button,Grain=b.get('TornGrain_'+n),
                  Pips=b.get('TornPips_'+n),Detail=b.get(detail),Index=i,Tilt=0.,Lift=b.get('TornLift'+n),Cost=cost)
        put=b.set('TornLift'+n,(step,'NewLift'))
        b.chain(prev,step,put);prev=put
    leader=b.get('Leader',ENC,enc)
    for n in ('Composure','Resolve'):
        maximum=b.get('Start'+n,'/Game/FoA/Gameplay/Encounter/PDA_Opponent.PDA_Opponent_C',leader)
        txt=b.fn('/Script/Engine.KismetTextLibrary:Conv_IntToText',Value=maximum)
        put=b.fn(U+'TextBlock:SetText',self=b.get('Txt_TornMax'+n),InText=txt)
        b.chain(prev,put);prev=put
    run(b,'Animate battle presentation')


def stats():
    props('SelfBox',s=slot(-64,-350,240,260,(1,1),(1,1)))
    add({'class':'CanvasPanel','name':'TornStats','slot_props':{'fill':1}},'SelfBox')
    for i,n in enumerate(('Composure','Resolve')):
        x=20+i*118
        move('Txt_'+n,'TornStats',**slot(x-20,190,90,30))
        move('Txt_'+n+'Label','TornStats',**slot(x-40,220,130,35))
        props('Txt_'+n+'Label',text('x',n,20)['properties'])
        props('Size_Bar_'+n,{'WidthOverride':16.,'HeightOverride':174.,'bOverride_WidthOverride':True,'bOverride_HeightOverride':True})
        add({'class':'RetainerBox','name':'TornColumn_'+n,'slot_props':slot(x+14,8,16,174),
             'properties':{'EffectMaterial':MAT+'/MI_UI_SandText_HUD.MI_UI_SandText_HUD','TextureParameter':'Texture','Visibility':'HitTestInvisible'}},'TornStats')
        move('Size_Bar_'+n,'TornColumn_'+n)
        props('Bar_'+n,{'BarFillType':'BottomToTop','BarFillStyle':'Scale','FillColorAndOpacity':'(R=0.9,G=0.9,B=0.9,A=1)',
            'WidgetStyle':'(BackgroundImage=(DrawAs=Image,TintColor=(SpecifiedColor=(R=0.05,G=0.05,B=0.05,A=0.2))),FillImage=(DrawAs=Image,ResourceObject="/Script/Engine.Texture2D\''+ICONS+'/T_Battle_TornMask.T_Battle_TornMask\'"))'})
        for suffix,value,y in (('Max','100',0),('Zero','0',164)):
            node=text('Txt_Torn'+suffix+n,value,15,True);node['slot_props']=slot(x+34,y,46,26)
            node['properties']['ColorAndOpacity']={'SpecifiedColor':[.5,.5,.5,1]}
            add(node,'TornStats');var(node['name'])
        props('Box_'+n,{'Visibility':'Collapsed'})
    finish()


def hook():
    # Existing action handlers and all their wires remain untouched. Tick observes the turn transition.
    ns,es=graph(WBP,'EventGraph');b=B(WBP,'EventGraph')
    if not any(n['title'].startswith('Event Tick') for n in ns):
        b.ops.append(dict(op='add_event',ref='torn_tick',event_name='Tick',x=0,y=3000))
        call=b.fn(WBP+'.WBP_Encounter_C:TornTick',Delta=('torn_tick','InDeltaTime'))
        b.chain('torn_tick',call)
    if b.ops:b.run()
    ns,es=graph(WBP,'RedrawAll');b=B(WBP,'RedrawAll')
    if not any(n['title'].replace(' ','')=='TornConfigureAll' for n in ns):
        source=next(n['node_id'] for n in ns if n['title'].replace(' ','')=='RefreshBattlePresentation')
        follow=[e for e in es if e['from_node']==source and e['from_pin']=='then']
        call=b.fn(WBP+'.WBP_Encounter_C:TornConfigureAll')
        b.ops.append(dict(op='disconnect',node_id=source,pin_name='then'))
        b.chain(source,call)
        for edge in follow:b.link(call,'then',edge['to_node'],edge['to_pin'])
        b.run()
    # RefreshAct continues to own availability and data, and now publishes its already-resolved cost.
    ns,es=graph(WBP,'RefreshAct');b=B(WBP,'RefreshAct')
    if not any(n['title'].replace(' ','')=='TornCost' for n in ns):
        entry=next(n['node_id'] for n in ns if n['title']=='RefreshAct' and any(p['name']=='then' for p in n['pins']))
        en=next(n['node_id'] for n in ns if n['title']=='Get Encounter')
        mv=next(n['node_id'] for n in ns if n['title']=='Get')
        cost=b.fn(ENC+':MoveCost',self=(en,'Encounter'),Move=(mv,'Item'))
        put=b.fn(WBP+'.WBP_Encounter_C:TornCost',Index=(entry,'Index'),Cost=(cost,'Cost'))
        source=next(n['node_id'] for n in ns if n['title']=='SetIsEnabled')
        edge=next(e for e in es if e['from_node']==source and e['from_pin']=='then')
        b.ops.append(dict(op='disconnect',node_id=source,pin_name='then'))
        b.chain(source,put);b.link(put,'then',edge['to_node'],edge['to_pin']);b.run()
    # Keep exact Resolve costs in MoveLabel; three coarse pips cannot distinguish 5 from 10.
    finish()


def selftest():
    # Three act slots and two usable recovery commands; unavailable Items/Flee stay collapsed.
    for width,height in ((1920,1080),(1728,1080)):
        total=5*214
        assert (width-total)/2 > width*.05
        assert height-88-252-24 > height-400
    assert len(CARDS)==len(set(CARDS))
    print('Selfcheck: usable cards and focus lift fit 16:9 and 16:10')


if __name__=='__main__':
    step=sys.argv[1]
    if step=='selftest':selftest()
    else:
        assert hc.leases_of('battle-ui'), 'Take an editor_lock.py battle-ui lease first'
        assert not c('editor_get_state')['pie_running'], 'Never mutate during PIE'
        globals()[step]()
