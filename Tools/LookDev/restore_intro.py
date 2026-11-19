"""Restore the surviving eight-beat intro in place through native Hayba commands.

Uses only actual in-game captures. No concept artwork is referenced.
Run `python Tools/LookDev/restore_intro.py tree|graphs|verify`; never starts PIE.
"""
import json
import os
from pathlib import Path
import shutil
import sys

sys.path.insert(0, 'P:/FoA/Tools/Unreal')
import hayba_call as hc
import editor_lock

W = '/Game/FoA/UI/Intro/WBP_IntroStory'
WC = W + '.WBP_IntroStory_C:'
HOST = '/Game/FoA/UI/Framework/BP_FoAFrontEnd.BP_FoAFrontEnd_C'
TEX = '/Game/FoA/UI/Intro/Textures'
K = '/Script/Engine.KismetMathLibrary:'
S = '/Script/Engine.KismetSystemLibrary:'
U = '/Script/UMG.Widget:'
LANE = 'intro_resume'
OUT = Path('P:/FoA/Saved/LookDev/intro_restored')
LINES = [
    'You have slept through too many mornings.',
    'Something waits at the foot of your bed. It is patient.',
    'Seventeen mornings. The clock keeps going. You stay here.',
    'Homework. The cup. The shirt on the chair. Everything waits.',
    'Here, the chores have grown teeth. They are completely serious.',
    'Today, you will get dressed.',
    'Today, you will leave the house.',
    '',
]
SECONDS = [6., 7., 6., 7., 7., 5., 5., 3.]
PANELS = ['Game01_Sleep','Game02_BedFoot','Game03_Clock','Game04_Desk',
          'Game05_Chores','Game06_Wardrobe','Game07_Door','Game08_Window']
SOURCES = {name: f'P:/FoA/Saved/LookDev/intro_ingame/{name}.png' for name in PANELS}
NEARS = [name+'_Near' for name in PANELS]
SOURCES.update({name:f'P:/FoA/Saved/LookDev/intro_ingame/{name}.png' for name in NEARS})


def call(cmd, **params):
    r = hc.call(cmd, params)
    assert r.get('ok'), (cmd, r)
    d = r.get('data', {})
    assert d.get('ok', True), (cmd, d)
    assert not d.get('failed'), (cmd, d)
    return d


def tex(name):
    return f'{TEX}/T_Intro_{name}'


def ui(cmd, **params):
    # The MCP conveniences resolve to this native property writer on this editor.
    if cmd == 'ui_set_slot_layout':
        name=params.pop('widget_name')
        if 'anchors' in params:
            a=params.pop('anchors')
            params.update(anchors_min=a[:2],anchors_max=a[2:])
        cmd,params='ui_set_widget_properties',dict(widget_name=name,slot_props=params)
    elif cmd == 'ui_set_brush':
        name=params.pop('widget_name')
        brush={'DrawAs':params.get('draw_as','Image')}
        if 'resource' in params: brush['ResourceObject']=params['resource']
        if 'tint' in params: brush['TintColor']={'SpecifiedColor':dict(zip('RGBA',params['tint']))}
        cmd,params='ui_set_widget_properties',dict(widget_name=name,properties={'Brush':brush})
    elif cmd == 'ui_set_text_style':
        name=params.pop('widget_name')
        props={'Font':{'FontObject':params['font_asset'],'TypefaceFontName':params['typeface'],'Size':params['size']},
               'ColorAndOpacity':{'SpecifiedColor':dict(zip('RGBA',params['color']))},
               'Text':params['text'],'Justification':params['justification']}
        if 'shadow_offset' in params:props['ShadowOffset']=dict(zip('XY',params['shadow_offset']))
        if 'shadow_color' in params:props['ShadowColorAndOpacity']=dict(zip('RGBA',params['shadow_color']))
        cmd,params='ui_set_widget_properties',dict(widget_name=name,properties=props)
    return call(cmd, widget_blueprint_path=W, **params)


def tree():
    quality=json.loads(Path('P:/FoA/Saved/LookDev/intro_ingame/layers_assembled.json').read_text())
    assert {row['name'] for row in quality}==set(PANELS[1:]),'All seven actual render layers must pass first'
    assert all(Path(src).is_file() for src in SOURCES.values()),'Missing actual-game intro image'
    stage = Path(os.environ['TEMP'])/'hayba-asset-connectors'/'intro_resume'/'textures'
    stage.mkdir(parents=True, exist_ok=True)
    for name, src in SOURCES.items():
        dst = stage/f'T_Intro_{name}.png'
        shutil.copyfile(src, dst)
        if not (Path('P:/FoA/Content')/(tex(name).removeprefix('/Game/')+'.uasset')).exists():
            call('asset_import', source_file=dst.as_posix(), destination_path=TEX, asset_type='texture')
        call('texture_set_settings', path=tex(name), properties={
            'lod_group':'UI', 'max_texture_size':2048, 'never_stream':True})
        call('object_set_property',path=tex(name),properties={'AdjustSaturation':0.0,
             'AdjustBrightness':1.0})
    q = call('ui_query', path=W)
    def names(n):
        return [n['name']] + [x for c in n.get('children', []) for x in names(c)]
    have = names(q['root'])
    for n, cls, parent in [('Img_Mid','Image','Cvs_Root'), ('Img_Figure','Image','Cvs_Root'),
                           ('Img_Fx','Image','Cvs_Root'), ('Img_Near','Image','Cvs_Root'),
                           ('Img_Foot','Image','Cvs_Root'), ('Txt_Skip','TextBlock','Btn_Skip')]:
        if n not in have:
            ui('ui_add_element', name=n, child_class=cls, parent_widget_name=parent)
    for n, z in [('Cvs_Root',0), ('Img_Black',0), ('Img_Panel',1), ('Img_Mid',2),
                 ('Img_Figure',3), ('Img_Fx',4), ('Img_Near',5)]:
        ui('ui_set_slot_layout', widget_name=n, anchors=[0,0,1,1], position=[0,0], size=[0,0], z_order=z)
    ui('ui_set_slot_layout', widget_name='Img_Foot', anchors=[0,.80,1,1], position=[0,0], size=[0,0], z_order=6)
    ui('ui_set_brush', widget_name='Img_Black', tint=[0,0,0,1], draw_as='Image')
    ui('ui_set_brush', widget_name='Img_Foot', tint=[0,0,0,.78], draw_as='Image')
    for n in ('Img_Panel','Img_Mid','Img_Figure','Img_Fx','Img_Near'):
        ui('ui_set_brush', widget_name=n, resource=tex(PANELS[0]) if n=='Img_Panel' else tex(NEARS[0]) if n=='Img_Near' else 'None',
           tint=[1,1,1,1], draw_as='Image')
        ui('ui_set_widget_properties', widget_name=n, properties={
            'Visibility':'HitTestInvisible' if n in ('Img_Panel','Img_Near') else 'Collapsed',
            'RenderTransform':{'Scale':{'X':1.045,'Y':1.045}},
            'RenderTransformPivot':{'X':.5,'Y':.5}})
        ui('ui_set_variable', widget_name=n, is_variable=True)
    ui('ui_set_widget_properties', widget_name='Img_Figure', properties={'RenderOpacity':0})
    ui('ui_set_widget_properties', widget_name='Img_Fx', properties={'RenderOpacity':.25})
    ui('ui_set_widget_properties', widget_name='Cvs_Root', properties={'Clipping':'ClipToBounds'})
    ui('ui_set_slot_layout', widget_name='Txt_Sub', anchors=[.08,1,.92,1], position=[0,-154], size=[0,76], z_order=7)
    ui('ui_set_text_style', widget_name='Txt_Sub', text=LINES[0],
       font_asset='/Game/FoA/UI/Fonts/F_FoA_UI', typeface='Medium', size=30,
       color=[.9,.9,.9,1], justification='Center', shadow_offset=[1,2], shadow_color=[0,0,0,.8])
    ui('ui_set_widget_properties', widget_name='Txt_Sub', properties={'AutoWrapText':True,'Visibility':'HitTestInvisible'})
    ui('ui_set_slot_layout', widget_name='Btn_Skip', anchors=[1,1,1,1], position=[-168,-72], size=[120,44], z_order=8)
    style = {k:{'DrawAs':'Image', 'TintColor':{'SpecifiedColor':{'R':v,'G':v,'B':v,'A':a}}}
             for k,v,a in [('Normal',0,.25),('Hovered',.16,.9),('Pressed',.25,1)]}
    ui('ui_set_widget_properties', widget_name='Btn_Skip', properties={'WidgetStyle':style,'IsFocusable':True})
    ui('ui_set_text_style', widget_name='Txt_Skip', text='Skip',
       font_asset='/Game/FoA/UI/Fonts/F_FoA_UI', typeface='Medium', size=24,
       color=[.75,.75,.75,1], justification='Center')
    for n in ('Txt_Sub','Btn_Skip'):
        ui('ui_set_variable', widget_name=n, is_variable=True)
    call('blueprint_set_defaults',path=W,properties={
        'Panels':[tex(n)+'.T_Intro_'+n for n in PANELS], 'Lines':LINES,'Seconds':SECONDS})
    ui('ui_compile_widget')
    ui('ui_save_widget')
    call('asset_save', asset_paths=[tex(n) for n in SOURCES])


class Graph:
    def __init__(self, name):
        self.name, self.ops = name, []
        info = call('blueprint_inspect_graph', path=W, graph_name=name)
        keep = [n for n in info['nodes'] if n['title'] == name]
        self.entry = keep[0]['node_id'] if keep else None
        remove = [n['node_id'] for n in info['nodes'] if n not in keep]
        if remove:
            self.ops.append(dict(op='remove', node_ids=remove))

    def add(self, ref, kind='call_function', x=0, y=0, **kw):
        self.ops.append(dict(op='add_node',ref=ref,node_type=kind,x=x,y=y,**kw))
        return ref

    def fn(self, ref, func, x=0, y=0, **defaults):
        self.add(ref, function_name=func, x=x, y=y)
        for p,v in defaults.items(): self.val(ref,p,v)
        return ref

    def get(self, ref, var, x=0, y=0, **kw):
        return self.add(ref,'variable_get',x,y,variable_name=var,**kw)

    def set(self, ref, var, x=0, y=0):
        return self.add(ref,'variable_set',x,y,variable_name=var)

    def val(self, ref, pin, value):
        self.ops.append(dict(op='set_pin',node_id=ref,pin_name=pin,value=str(value).lower() if isinstance(value,bool) else str(value)))

    def link(self, a, b, ap='then', bp='execute'):
        self.ops.append(dict(op='connect',from_node=a,from_pin=ap,to_node=b,to_pin=bp))

    def chain(self, *refs):
        for a,b in zip(refs, refs[1:]): self.link(a,b)

    def comment(self, title, refs):
        self.ops.append(dict(op='comment',title=title,node_ids=refs,color=[.12,.16,.19]))

    def apply(self):
        selected=set(filter(None,os.environ.get('INTRO_GRAPHS','').split(',')))
        if selected and self.name not in selected:return
        self.ops.append(dict(op='fit_comments'))
        r = call('blueprint_graph_batch',path=W,graph_name=self.name,ops=self.ops,compile=True,save=True)
        (OUT/f'{self.name}_batch.json').write_text(json.dumps(r,indent=2))
        assert r.get('applied') == len(self.ops), r
        assert not r.get('compile_error'), r
        print(self.name, 'applied', len(self.ops), 'operations', flush=True)

    def array(self, ref, name, x, y):
        self.get(ref+'Array',name,x,y)
        self.add(ref,'get_array_item',x+200,y)
        self.link(ref+'Array',ref,name,'Array')
        self.link('index',ref,'Index','Dimension 1')
        return ref


def graphs():
    info = call('blueprint_get_info',path=W)
    have = {v['name'] for v in info['variables']}
    for n,t,d,container in [('Host','object:'+HOST,'','none'), ('Index','int','-1','none'),
                            ('bDone','bool','false','none'), ('PanelTime','float','0','none'),
                            ('Motion','float','0','none'), ('Fade','float','0','none'),
                            ('Panels','object:/Script/Engine.Texture2D','','array'),
                            ('NearPanels','object:/Script/Engine.Texture2D','','array'),
                            ('Lines','string','','array'), ('Seconds','float','','array')]:
        if n not in have:
            call('blueprint_add_variable',path=W,variable_name=n,variable_type=t,container=container,
                 default_value=d,category='Intro',instance_editable=n in ('Panels','Lines','Seconds'))
    specs = [('Finish',[]), ('NextPanel',[]), ('FocusSkip',[]), ('UpdateFrame',[{'name':'Delta','type':'float'}]),
             ('ApplyLayer',[{'name':'Image','type':'object:/Script/UMG.Image'}, {'name':'Depth','type':'float'},
                            {'name':'Alpha','type':'float'}])]
    for n,ins in specs:
        if n not in info['functions']:
            call('blueprint_add_function',path=W,function_name=n,inputs=ins)
    # Parameters use the existing game's settings and original pacing.
    call('blueprint_set_defaults',path=W,properties={
        'Panels':[tex(n)+'.T_Intro_'+n for n in PANELS],
        'NearPanels':[tex(n)+'.T_Intro_'+n for n in NEARS],
        'Lines':LINES,'Seconds':SECONDS,'Index':-1,'bDone':False})

    g=Graph('ApplyLayer'); e=g.entry
    g.get('motion','Motion',0,220); g.get('fade','Fade',1180,360)
    g.fn('depthmove',K+'Multiply_DoubleDouble',220,220); g.link('motion','depthmove','Motion','A'); g.link(e,'depthmove','Depth','B')
    g.fn('shift',K+'Multiply_DoubleDouble',430,220,B=42); g.link('depthmove','shift','ReturnValue','A')
    g.fn('xy',K+'MakeVector2D',640,220,Y=0); g.link('shift','xy','ReturnValue','X')
    g.fn('translate',U+'SetRenderTranslation',860,0); g.link(e,'translate','Image','self'); g.link('xy','translate','ReturnValue','Translation')
    g.fn('zoom',K+'Multiply_DoubleDouble',430,480,B=.03); g.link('depthmove','zoom','ReturnValue','A')
    g.fn('overscan',K+'Add_DoubleDouble',640,480,B=1.045); g.link('zoom','overscan','ReturnValue','A')
    g.fn('scalevector',K+'MakeVector2D',860,480); g.link('overscan','scalevector','ReturnValue','X'); g.link('overscan','scalevector','ReturnValue','Y')
    g.fn('scale',U+'SetRenderScale',1120,0); g.link(e,'scale','Image','self'); g.link('scalevector','scale','ReturnValue','Scale')
    g.fn('alpha',K+'Multiply_DoubleDouble',1400,360); g.link('fade','alpha','Fade','A'); g.link(e,'alpha','Alpha','B')
    g.fn('opacity',U+'SetRenderOpacity',1640,0); g.link(e,'opacity','Image','self'); g.link('alpha','opacity','ReturnValue','InOpacity')
    g.chain(e,'translate','scale','opacity')
    g.comment('Depth and drift',[e,'motion','depthmove','shift','xy','translate','zoom','overscan','scalevector','scale'])
    g.comment('Soft exposure',['fade','alpha','opacity']); g.apply()

    g=Graph('Finish'); e=g.entry
    g.get('done','bDone',0,180); g.add('guard','branch',220,0); g.link('done','guard','bDone','Condition'); g.link(e,'guard')
    g.set('mark','bDone',440,0); g.val('mark','bDone',True); g.link('guard','mark','else')
    g.fn('clearFocus',S+'K2_ClearTimer',550,0,FunctionName='FocusSkip')
    g.fn('clear',S+'K2_ClearTimer',660,0,FunctionName='NextPanel'); g.chain('mark','clearFocus','clear')
    g.get('host','Host',660,240); g.fn('valid',S+'IsValid',880,240); g.link('host','valid','Host','Object')
    g.add('hasHost','branch',1100,0); g.link('valid','hasHost','ReturnValue','Condition'); g.link('clear','hasHost')
    g.fn('finish',HOST+':OnStoryFinished',1330,-80); g.link('host','finish','Host','self'); g.link('hasHost','finish')
    g.fn('remove',U+'RemoveFromParent',1330,140); g.link('hasHost','remove','else')
    g.comment('Complete exactly once',[e,'done','guard','mark','clearFocus','clear']); g.comment('Return to morning',['host','valid','hasHost','finish','remove']); g.apply()

    g=Graph('NextPanel'); e=g.entry
    g.get('done','bDone',0,160); g.add('active','branch',220,0); g.link(e,'active'); g.link('done','active','bDone','Condition')
    g.get('old','Index',220,240); g.fn('increment',K+'Add_IntInt',430,240,B=1); g.link('old','increment','Index','A')
    g.set('advance','Index',660,0); g.link('increment','advance','ReturnValue','Index'); g.link('active','advance','else')
    g.get('index','Index',660,220); g.fn('within',K+'Less_IntInt',880,220,B=8); g.link('index','within','Index','A')
    g.add('remaining','branch',1100,0); g.link('within','remaining','ReturnValue','Condition'); g.link('advance','remaining')
    g.fn('finish',WC+'Finish',1340,240); g.link('remaining','finish','else')
    g.set('reset','PanelTime',1340,-80); g.val('reset','PanelTime',0); g.link('remaining','reset')
    g.array('texture','Panels',1340,-440)
    g.get('panel','Img_Panel',1760,-240); g.fn('brush','/Script/UMG.Image:SetBrushFromTexture',1980,-80)
    g.link('panel','brush','Img_Panel','self'); g.link('texture','brush','Output','Texture')
    g.array('nearTexture','NearPanels',1760,-850)
    g.get('nearImage','Img_Near',2200,-650);g.fn('nearBrush','/Script/UMG.Image:SetBrushFromTexture',2420,-850)
    g.link('nearImage','nearBrush','Img_Near','self');g.link('nearTexture','nearBrush','Output','Texture')
    g.array('line','Lines',2200,-440); g.fn('text','/Script/Engine.KismetTextLibrary:Conv_StringToText',2640,-440)
    g.link('line','text','Output','InString'); g.get('sub','Txt_Sub',2640,-240)
    g.fn('caption','/Script/UMG.TextBlock:SetText',2860,-80); g.link('sub','caption','Txt_Sub','self'); g.link('text','caption','ReturnValue','InText')
    g.array('seconds','Seconds',3080,-440); g.fn('timer',S+'K2_SetTimer',3520,-80,FunctionName='NextPanel',bLooping=False)
    g.link('seconds','timer','Output','Time'); g.fn('frame',WC+'UpdateFrame',3780,-80,Delta=0)
    g.get('host','Host',3080,300); g.fn('validHost',S+'IsValid',3300,300); g.link('host','validHost','Host','Object')
    g.add('soundGuard','branch',3080,-80); g.link('validHost','soundGuard','ReturnValue','Condition')
    g.get('cue','SndPanelTransition',3520,300,class_path=HOST); g.link('host','cue','Host','self')
    g.fn('sound',HOST+':PlayUISound',3300,-80); g.link('host','sound','Host','self'); g.link('cue','sound','SndPanelTransition','Cue')
    g.chain('reset','brush','nearBrush','caption','soundGuard','sound','timer','frame'); g.link('soundGuard','timer','else')
    g.comment('Advance eight beats',[e,'done','active','old','increment','advance','index','within','remaining','finish'])
    g.comment('Room and words',['reset','textureArray','texture','panel','brush','nearTextureArray','nearTexture','nearImage','nearBrush','lineArray','line','text','sub','caption'])
    g.comment('Sound and timing',['secondsArray','seconds','timer','frame','host','validHost','soundGuard','cue','sound']); g.apply()

    g=Graph('UpdateFrame'); e=g.entry
    g.get('done','bDone',0,180); g.add('active','branch',220,0); g.link(e,'active'); g.link('done','active','bDone','Condition')
    g.get('age','PanelTime',220,220); g.fn('add',K+'Add_DoubleDouble',440,220); g.link('age','add','PanelTime','A'); g.link(e,'add','Delta','B')
    g.set('ageSet','PanelTime',660,0); g.link('add','ageSet','ReturnValue','PanelTime'); g.link('active','ageSet','else')
    g.get('index','Index',660,480); g.array('seconds','Seconds',880,480)
    g.fn('progress',K+'Divide_DoubleDouble',1320,480); g.link('add','progress','ReturnValue','A'); g.link('seconds','progress','Output','B')
    g.fn('center',K+'Subtract_DoubleDouble',1540,480,B=.5); g.link('progress','center','ReturnValue','A')
    g.fn('reduce','/Script/Engine.KismetMaterialLibrary:GetScalarParameterValue',880,720,
         Collection='/Game/FoA/UI/Style/MPC_UI.MPC_UI',ParameterName='ReduceMotion')
    g.fn('amount',K+'Subtract_DoubleDouble',1320,720,A=1); g.link('reduce','amount','ReturnValue','B')
    g.fn('motion',K+'Multiply_DoubleDouble',1760,480); g.link('center','motion','ReturnValue','A'); g.link('amount','motion','ReturnValue','B')
    g.set('motionSet','Motion',1980,0); g.link('motion','motionSet','ReturnValue','Motion')
    g.fn('tail',K+'Subtract_DoubleDouble',1320,1000); g.link('seconds','tail','Output','A'); g.link('add','tail','ReturnValue','B')
    g.fn('ends',K+'FMin',1540,1000); g.link('add','ends','ReturnValue','A'); g.link('tail','ends','ReturnValue','B')
    g.fn('fade',K+'FClamp',1760,1000,Min=0,Max=1); g.link('ends','fade','ReturnValue','Value')
    g.set('fadeSet','Fade',2200,0); g.link('fade','fadeSet','ReturnValue','Fade')
    g.chain('ageSet','reduce','motionSet','fadeSet')
    g.fn('layered',K+'Greater_IntInt',2200,480,B=0); g.link('index','layered','Index','A')
    g.fn('layerAlpha',K+'Conv_BoolToDouble',2420,480); g.link('layered','layerAlpha','ReturnValue','InBool')
    g.fn('figureOnly',K+'EqualEqual_IntInt',2200,700,B=-1); g.link('index','figureOnly','Index','A')
    g.fn('figureAlpha',K+'Conv_BoolToDouble',2420,700); g.link('figureOnly','figureAlpha','ReturnValue','InBool')
    g.fn('fxAlpha',K+'Multiply_DoubleDouble',2420,920,B=.25); g.link('layerAlpha','fxAlpha','ReturnValue','A')
    prev='fadeSet'
    refs=[]
    for i,(n,depth,alpha) in enumerate([('Img_Panel',.25,None),('Img_Mid',.6,'layerAlpha'),('Img_Figure',.62,'figureAlpha'),('Img_Fx',.7,'fxAlpha'),('Img_Near',1.,'layerAlpha')]):
        x=2700+i*260
        g.get(n,n,x,220); g.fn('apply'+str(i),WC+'ApplyLayer',x,0,Depth=depth,Alpha=1)
        g.link(n,'apply'+str(i),n,'Image')
        if alpha:g.link(alpha,'apply'+str(i),'ReturnValue','Alpha')
        g.link(prev,'apply'+str(i)); prev='apply'+str(i); refs.extend([n,prev])
    g.get('sub','Txt_Sub',4000,220); g.fn('subfade',U+'SetRenderOpacity',4220,0); g.link('sub','subfade','Txt_Sub','self'); g.link('fade','subfade','ReturnValue','InOpacity'); g.link(prev,'subfade')
    g.comment('Panel clock',[e,'done','active','age','add','ageSet','index','secondsArray','seconds'])
    g.comment('Accessible motion',['progress','center','reduce','amount','motion','motionSet','tail','ends','fade','fadeSet'])
    g.comment('Depth layers',['layered','layerAlpha','figureOnly','figureAlpha','fxAlpha']+refs+['sub','subfade']); g.apply()

    g=Graph('FocusSkip'); e=g.entry
    g.get('done','bDone',-1000,220);g.fn('unfinished',K+'Not_PreBool',-750,220);g.link('done','unfinished','bDone','A')
    g.fn('onscreen','/Script/UMG.UserWidget:IsInViewport',-1000,440)
    g.fn('active',K+'BooleanAND',-500,220);g.link('unfinished','active','ReturnValue','A');g.link('onscreen','active','ReturnValue','B')
    g.add('guard','branch',-250,0);g.link('active','guard','ReturnValue','Condition');g.link(e,'guard')
    g.get('button','Btn_Skip',0,200)
    g.fn('pc','/Script/Engine.GameplayStatics:GetPlayerController',220,220,PlayerIndex=0)
    g.fn('mode','/Script/UMG.WidgetBlueprintLibrary:SetInputMode_UIOnlyEx',440,0,bFlushInput=True)
    g.link('pc','mode','ReturnValue','PlayerController'); g.link('button','mode','Btn_Skip','InWidgetToFocus')
    g.fn('focus',U+'SetKeyboardFocus',720,0); g.link('button','focus','Btn_Skip','self'); g.chain('guard','mode','focus')
    g.comment('Only the active story owns focus',[e,'done','unfinished','onscreen','active','guard','button','pc','mode','focus']); g.apply()

    event_graph()


def event_graph():
    g=Graph('EventGraph')
    g.ops.append(dict(op='add_event',ref='construct',event_name='Construct',x=0,y=0))
    g.fn('find','/Script/Engine.GameplayStatics:GetActorOfClass',240,0,ActorClass=HOST)
    g.add('cast','cast',500,0,class_path=HOST); g.link('find','cast','ReturnValue','Object')
    g.set('host','Host',740,0); g.link('cast','host','AsBP Fo AFront End','Host')
    g.fn('first',WC+'NextPanel',1000,0); g.fn('focusTimer',S+'K2_SetTimer',1260,0,FunctionName='FocusSkip',Time=.05,bLooping=False)
    g.chain('construct','find','cast','host','first','focusTimer'); g.link('cast','first','CastFailed')
    g.ops.append(dict(op='add_event',ref='tick',event_name='Tick',x=0,y=700))
    g.fn('frame',WC+'UpdateFrame',300,700); g.link('tick','frame'); g.link('tick','frame','InDeltaTime','Delta')
    g.ops.append(dict(op='add_event',ref='destruct',event_name='Destruct',x=0,y=1100))
    g.fn('clear',S+'K2_ClearTimer',300,1100,FunctionName='NextPanel')
    g.fn('clearFocus',S+'K2_ClearTimer',600,1100,FunctionName='FocusSkip');g.chain('destruct','clear','clearFocus')
    g.comment('Start the story',['construct','find','cast','host','first','focusTimer'])
    g.comment('Live depth motion',['tick','frame']); g.comment('Cancel pending story callbacks',['destruct','clear','clearFocus']); g.apply()


def verify():
    info = call('blueprint_get_info',path=W)
    assert all(n in info['functions'] for n in ('Finish','NextPanel','ApplyLayer','UpdateFrame','FocusSkip'))
    for name in ('Finish','NextPanel','ApplyLayer','UpdateFrame','FocusSkip','EventGraph'):
        g=call('blueprint_inspect_graph',path=W,graph_name=name)
        assert g['edge_count'] > 0, name
        (OUT/f'{name}_verified.json').write_text(json.dumps(g,indent=2))
    r=ui('ui_compile_widget'); (OUT/'compile.json').write_text(json.dumps(r,indent=2))
    ui('ui_save_widget')
    print('Verified graph connections and compilation; runtime proof still required.')


def integrate():
    """Coordinator-authorized narrow frontend integration; preserves its sound and wake path."""
    fe='/Game/FoA/UI/Framework/BP_FoAFrontEnd'
    call('blueprint_set_defaults',path=fe,properties={'StoryClass':W+'.WBP_IntroStory_C'})
    call('actor_set_properties',actor_id='BP_FoAFrontEnd_C_0',properties={'StoryClass':W+'.WBP_IntroStory_C'})
    g=call('blueprint_inspect_graph',path=fe,graph_name='AfterWakeFade')
    if not any(n['title']=='DropBlackOverlay' for n in g['nodes']):
        ids={n['title']:n['node_id'] for n in g['nodes']}
        ops=[dict(op='add_node',ref='reveal',node_type='call_function',function_name=HOST+':DropBlackOverlay',x=2640,y=-160),
             dict(op='disconnect',node_id=ids['AddToViewport'],pin_name='then'),
             dict(op='connect',from_node=ids['AddToViewport'],to_node='reveal'),
             dict(op='connect',from_node='reveal',to_node=ids['StartBed']),
             dict(op='move',node_id=ids['StartBed'],x=2940,y=-160),dict(op='fit_comments')]
        call('blueprint_graph_batch',path=fe,graph_name='AfterWakeFade',ops=ops,compile=True,save=True)
    call('asset_save',asset_paths=[fe])


if __name__=='__main__':
    OUT.mkdir(parents=True,exist_ok=True)
    os.environ['HAYBA_AGENT_ID']=os.environ['FOA_AGENT']=LANE
    assert not call('editor_get_state').get('pie_running'), 'PIE belongs to the coordinator'
    areas=['/Game/FoA/UI/Framework/BP_FoAFrontEnd','actor:/Game/FoA/Maps/L_Tutorial_Bedroom.BP_FoAFrontEnd'] if sys.argv[1]=='integrate' else [W,TEX]
    editor_lock.acquire(LANE,wait_s=60,ttl=240,areas=areas)
    try:
        {'tree':tree,'graphs':graphs,'events':event_graph,'verify':verify,'integrate':integrate}[sys.argv[1]]()
    finally:
        editor_lock.release(LANE)
