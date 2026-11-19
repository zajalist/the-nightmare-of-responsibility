"""Compact action hierarchy and physical tool feedback. Native, scoped, no PIE.

Prepared offline; run only after the coordinator releases the editor.
Preserves the HUD's subtitle settings, headache borders and interaction guards.
"""
import os,sys
from pathlib import Path
sys.path.insert(0,'P:/FoA/Tools/Unreal');import hayba_call as h
sys.path.insert(0,'P:/FoA/Tools/Unreal/player');from held_tool_graphs import Batch,inspect,find
HUD='/Game/FoA/UI/Game/WBP_HUD';DOOR='/Game/FoA/Gameplay/BP_Door'
HC=HUD+'.WBP_HUD_C';DC=DOOR+'.BP_Door_C'
K='/Script/Engine.KismetMathLibrary:';T='/Script/UMG.TextBlock:';W='/Script/UMG.Widget:'
OWNER='clothing_search';TOKEN=None

def call(name,**kw):
    r=h.call(name,kw,owner=OWNER,lease=TOKEN);assert r.get('ok'),r
    d=r.get('data',{});assert d.get('ok',True) and not d.get('failed'),d
    return d

def widget(name,properties=None,slot=None):
    return call('ui_set_widget_properties',widget_blueprint_path=HUD,widget_name=name,
        **({'properties':properties} if properties else {}),**({'slot_props':slot} if slot else {}))

def font(size,face='Regular'):
    return f'(FontObject="/Script/Engine.Font\'/Game/FoA/UI/Fonts/F_FoA_UI.F_FoA_UI\'",TypefaceFontName="{face}",Size={size})'

def layout():
    exists=call('ui_query',path=HUD,name_pattern='VB_Context')['matches']
    if not exists:
        call('ui_mutate_tree',operation='reparent',widget_blueprint_path=HUD,widget_name='Txt_Prompt',new_parent_name='Ovl_Frame')
        call('ui_build_tree',widget_blueprint_path=HUD,parent_widget_name='Brd_ToolPrompt',tree={'class':'VerticalBox','name':'VB_Context'})
        call('ui_mutate_tree',operation='reparent',widget_blueprint_path=HUD,widget_name='Txt_Prompt',new_parent_name='VB_Context')
        call('ui_build_tree',widget_blueprint_path=HUD,parent_widget_name='VB_Context',tree={
            'class':'TextBlock','name':'Txt_ContextSecondary','properties':{'Text':''},
            'slot_props':{'padding':[0,5,0,0]}})
        call('ui_build_tree',widget_blueprint_path=HUD,parent_widget_name='VB_Context',tree={
            'class':'SizeBox','name':'Size_ToolProgress','properties':{'HeightOverride':5.,'bOverride_HeightOverride':True,'Visibility':'Collapsed'},
            'slot_props':{'padding':[0,10,0,10]},'children':[{'class':'ProgressBar','name':'Progress_Tool',
                'properties':{'Percent':0.,'IsMarquee':False,'BarFillType':'LeftToRight'}}]})
        call('ui_build_tree',widget_blueprint_path=HUD,parent_widget_name='VB_Context',tree={
            'class':'TextBlock','name':'Txt_ToolControls','properties':{'Text':'','Visibility':'Collapsed'}})
        for name in ('Txt_ContextSecondary','Size_ToolProgress','Progress_Tool','Txt_ToolControls'):
            call('ui_set_variable',widget_blueprint_path=HUD,widget_name=name,is_variable=True)
    for name,size,face in [('Txt_Prompt',22,'SemiBold'),('Txt_ContextSecondary',18,'Regular'),
        ('Txt_ToolControls',18,'Regular'),('Txt_Objective',22,'Regular')]:
        widget(name,dict(Font=font(size,face),AutoWrapText=False,WrapTextAt=480.,
            ShadowOffset='(X=0,Y=1)',ShadowColorAndOpacity='(R=0,G=0,B=0,A=0.95)',
            ColorAndOpacity='(SpecifiedColor=(R=0.92,G=0.91,B=0.87,A=1))'))
    widget('Txt_ContextSecondary',dict(ColorAndOpacity='(SpecifiedColor=(R=0.64,G=0.63,B=0.59,A=1))'))
    widget('Txt_ToolControls',dict(ColorAndOpacity='(SpecifiedColor=(R=0.68,G=0.67,B=0.63,A=1))'))
    widget('Size_ToolProgress',dict(HeightOverride=5.,bOverride_HeightOverride=True))
    widget('Brd_ToolPrompt',dict(BrushColor='(R=0,G=0,B=0,A=0)',Padding='(Left=0,Top=0,Right=0,Bottom=0)'))
    widget('Size_ContextPrompt',slot=dict(horizontal_alignment='Center',vertical_alignment='Bottom',padding=[48,0,48,200]))
    widget('Txt_Objective',slot=dict(horizontal_alignment='Left',vertical_alignment='Top',padding=[48,38,48,0]))
    widget('Brd_Narration',dict(BrushColor='(R=0.003,G=0.003,B=0.003,A=0.58)',Padding='(Left=14,Top=7,Right=14,Bottom=7)'),
        dict(horizontal_alignment='Center',vertical_alignment='Bottom',padding=[48,0,48,48]))
    # Font size stays under ApplySubtitleSettings; this only bounds the subtitle line.
    widget('Txt_Narration',dict(AutoWrapText=False,WrapTextAt=760.,ShadowOffset='(X=0,Y=1)'))
    widget('Progress_Tool',dict(WidgetStyle='(BackgroundImage=(DrawAs=Image,TintColor=(SpecifiedColor=(R=0.08,G=0.08,B=0.07,A=0.8))),FillImage=(DrawAs=Image,TintColor=(SpecifiedColor=(R=1,G=1,B=1,A=1))))'))
    call('blueprint_compile',path=HUD,save=True)

def context_split():
    ns,es=inspect(HUD,'HandleFocusChanged')
    if any(n['title']=='Get Txt_ContextSecondary' for n in ns):return
    setter=next(n['node_id'] for n in ns if n['title'].startswith('SetText'))
    final=next(e for e in es if e['to_node']==setter and e['to_pin']=='InText')
    convert=next(e for e in es if e['to_node']==final['from_node'] and e['to_pin']=='InString')
    combined=convert['from_node']
    primary=next(e for e in es if e['to_node']==combined and e['to_pin']=='A')
    secondary=next(e for e in es if e['to_node']==combined and e['to_pin']=='B')
    b=Batch(HUD,'HandleFocusChanged')
    b.cut(combined,convert['from_pin'],convert['to_node'],convert['to_pin'])
    b.link(primary['from_node'],primary['from_pin'],convert['to_node'],convert['to_pin'])
    b.fn('trim','/Script/Engine.KismetStringLibrary:Trim',0,1600);b.link(secondary['from_node'],secondary['from_pin'],'trim','SourceString')
    b.fn('secondary_text','/Script/Engine.KismetTextLibrary:Conv_StringToText',300,1600);b.link('trim','ReturnValue','secondary_text','InString')
    b.get('secondary','Txt_ContextSecondary',600,1600)
    b.fn('secondary_set',T+'SetText',900,1600);b.link('secondary','Txt_ContextSecondary','secondary_set','self');b.link('secondary_text','ReturnValue','secondary_set','InText')
    outgoing=[x for x in es if x['from_node']==setter and x['from_pin']=='then'];assert not outgoing,outgoing
    b.chain(setter,'secondary_set');b.comment('A clear action and quieter alternate verb',['trim','secondary_text','secondary','secondary_set']);b.run()

def tool_visibility(graph,shown):
    ns,es=inspect(HUD,graph)
    if any(n['title']=='Get Size_ToolProgress' for n in ns):return
    # Existing status ownership/refresh stays intact; prepend visual state only.
    e=find(ns,graph);edge=next(x for x in es if x['from_node']==e and x['from_pin']=='then')
    b=Batch(HUD,graph);last=e
    b.cut(e,'then',edge['to_node'],edge['to_pin'])
    for i,(name,visible) in enumerate([('Size_ToolProgress',shown),('Txt_ToolControls',shown),('Txt_ContextSecondary',not shown)]):
        b.get('w'+str(i),name,-1200+i*400,500)
        b.fn('vis'+str(i),W+'SetVisibility',-1200+i*400,0,InVisibility='HitTestInvisible' if visible else 'Collapsed')
        b.link('w'+str(i),name,'vis'+str(i),'self');b.chain(last,'vis'+str(i));last='vis'+str(i)
    b.get('context','Size_ContextPrompt',0,1000)
    b.fn('slot','/Script/UMG.WidgetLayoutLibrary:SlotAsOverlaySlot',300,1000);b.link('context','Size_ContextPrompt','slot','Widget')
    b.fn('align','/Script/UMG.OverlaySlot:SetHorizontalAlignment',0,-400,InHorizontalAlignment='HAlign_Right' if shown else 'HAlign_Center');b.link('slot','ReturnValue','align','self')
    # Slot alignment is presentation only; ownership and scan refresh are unchanged.
    b.chain(last,'align');b.link('align','then',edge['to_node'],edge['to_pin'])
    for n in ns:
        if n['title']=='SetWidthOverride':b.pin(n['node_id'],'InWidthOverride',320.)
        if n['title']=='SetPadding':b.pin(n['node_id'],'InPadding','(Left=0,Top=0,Right=0,Bottom=0)')
        if n['title']=='SetBrushColor':b.pin(n['node_id'],'InBrushColor','(R=0,G=0,B=0,A=0)')
        if shown and n['title']=='ClearNarration':
            for link in [x for x in es if x['to_node']==n['node_id'] and x['to_pin']=='execute']:
                b.cut(link['from_node'],link['from_pin'],n['node_id'],'execute')
    b.run()

def independent_subtitles():
    ns,es=inspect(HUD,'HandleNarration')
    tool=[n for n in ns if n['title']=='Get bToolStatus']
    if not tool:return
    neg=next(x['to_node'] for x in es if x['from_node']==tool[0]['node_id'])
    andnode=next(x['to_node'] for x in es if x['from_node']==neg)
    output=[x for x in es if x['from_node']==andnode and x['to_pin']=='Condition']
    if not output:return
    original=next(x for x in es if x['to_node']==andnode and x['to_pin']=='A')
    b=Batch(HUD,'HandleNarration');edge=output[0]
    b.cut(andnode,edge['from_pin'],edge['to_node'],'Condition')
    b.link(original['from_node'],original['from_pin'],edge['to_node'],'Condition');b.run()

def context_clearance():
    """Leave a two-line subtitle safe area below the normal interaction prompt."""
    widget('Size_ContextPrompt',slot=dict(padding=[48,0,48,200]))
    for graph,bottom in [('ShowToolStatus',132),('HideToolStatus',200)]:
        ns,es=inspect(HUD,graph)
        slot=next(n['node_id'] for n in ns if n['title']=='SlotAsOverlaySlot')
        if any(x['from_node']==slot and x['to_pin']=='self' and next(n['title'] for n in ns if n['node_id']==x['to_node'])=='SetPadding' for x in es):continue
        align=next(n['node_id'] for n in ns if n['title']=='SetHorizontalAlignment')
        edge=next(x for x in es if x['from_node']==align and x['from_pin']=='then')
        b=Batch(HUD,graph);b.cut(align,'then',edge['to_node'],edge['to_pin'])
        b.fn('safe_padding','/Script/UMG.OverlaySlot:SetPadding',400,-400,InPadding=f'(Left=48,Top=0,Right=48,Bottom={bottom})')
        b.link(slot,'ReturnValue','safe_padding','self');b.chain(align,'safe_padding')
        b.link('safe_padding','then',edge['to_node'],edge['to_pin']);b.run()

def tool_feedback():
    info=call('blueprint_get_info',path=HUD)
    call('blueprint_add_variable',path=HUD,variable_name='bToolPadInput',variable_type='bool',default_value='false',category='HUD|Context',update_existing=True)
    if 'SetToolFeedback' not in info['functions']:
        call('blueprint_add_function',path=HUD,function_name='SetToolFeedback',inputs=[
            {'name':'Progress','type':'float'},{'name':'bBound','type':'bool'}])
    ns,es=inspect(HUD,'SetToolFeedback');e=find(ns,'SetToolFeedback');b=Batch(HUD,'SetToolFeedback')
    old=[n['node_id'] for n in ns if n['node_id']!=e]
    if old:b.ops.append(dict(op='remove',node_ids=old))
    b.get('bar','Progress_Tool',0,500);b.fn('progress','/Script/UMG.ProgressBar:SetPercent',300,0)
    b.link('bar','Progress_Tool','progress','self');b.link(e,'Progress','progress','InPercent')
    b.fn('color',K+'SelectColor',300,600,A='(R=0.9,G=0.47,B=0.17,A=1)',B='(R=0.82,G=0.8,B=0.72,A=1)');b.link(e,'bBound','color','bPickA')
    b.fn('tint','/Script/UMG.ProgressBar:SetFillColorAndOpacity',600,0);b.link('bar','Progress_Tool','tint','self');b.link('color','ReturnValue','tint','InColor')
    b.fn('pc','/Script/Engine.GameplayStatics:GetPlayerController',0,1100,PlayerIndex=0)
    b.fn('axis','/Script/Engine.PlayerController:GetInputAnalogKeyState',300,1100,Key='Gamepad_RightX');b.link('pc','ReturnValue','axis','self')
    b.fn('magnitude',K+'Abs',600,1100);b.link('axis','ReturnValue','magnitude','A')
    b.fn('pad_active',K+'Greater_DoubleDouble',900,1100,B=.1);b.link('magnitude','ReturnValue','pad_active','A')
    for i,key in enumerate(('D','A')):
        b.fn('key'+str(i),'/Script/Engine.PlayerController:IsInputKeyDown',300,1400+i*200,Key=key);b.link('pc','ReturnValue','key'+str(i),'self')
    b.fn('keys',K+'BooleanOR',600,1500);b.link('key0','ReturnValue','keys','A');b.link('key1','ReturnValue','keys','B')
    b.get('last_pad','bToolPadInput',900,1700)
    b.fn('pad',K+'BooleanOR',1200,1100);b.link('last_pad','bToolPadInput','pad','B');b.link('pad_active','ReturnValue','pad','A')
    b.fn('no_keys',K+'Not_PreBool',1200,1500);b.link('keys','ReturnValue','no_keys','A')
    b.fn('device',K+'BooleanAND',1500,1100);b.link('pad','ReturnValue','device','B');b.link('no_keys','ReturnValue','device','A')
    b.set('remember','bToolPadInput',900,0);b.link('device','ReturnValue','remember','bToolPadInput')
    b.fn('controls',K+'SelectString',600,700,A='Right stick  Turn     B  Release',B='D A Turn    Q Release');b.link('device','ReturnValue','controls','bPickA')
    b.fn('text','/Script/Engine.KismetTextLibrary:Conv_StringToText',900,700);b.link('controls','ReturnValue','text','InString')
    b.get('label','Txt_ToolControls',900,500);b.fn('write',T+'SetText',1200,0);b.link('label','Txt_ToolControls','write','self');b.link('text','ReturnValue','write','InText')
    b.chain(e,'progress','tint','remember','write');b.comment('Physical load, readable bind state and current device controls',list(['bar','progress','color','tint','controls','text','label','write']));b.run()

def main():
    global TOKEN
    os.environ['HAYBA_AGENT_ID']=OWNER
    assert not call('editor_get_state')['pie_running'],'User PIE active'
    clearance_only=sys.argv[1:]==['--clearance-only']
    TOKEN=h.lease_acquire(OWNER,['asset:'+HUD] if clearance_only else ['asset:'+HUD,'asset:'+DOOR],ttl_s=180,wait_s=3);os.environ['FOA_LEASE']=TOKEN
    try:
        if clearance_only:
            context_clearance();call('blueprint_compile',path=HUD,save=True)
            print('HUD prompt/subtitle clearance saved')
            return
        layout();context_split();tool_visibility('ShowToolStatus',True);tool_visibility('HideToolStatus',False);context_clearance();independent_subtitles();tool_feedback()
        # Door producer patch is deliberately separate: it must validate current saved nodes before changing them.
        print('HUD saved; apply door feedback producer before runtime verification')
    finally:h.release(OWNER,TOKEN);os.environ.pop('FOA_LEASE',None)

if __name__=='__main__':main()
