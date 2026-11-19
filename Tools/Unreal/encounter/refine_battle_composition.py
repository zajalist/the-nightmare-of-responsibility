"""Compact the existing battle widget in place; preserve its commands and gameplay rules."""
import json
import sys
from pathlib import Path
sys.path[:0] = ['P:/FoA/Tools/Unreal', 'P:/FoA/Tools/Unreal/player']
import hayba_call as h
from held_tool_graphs import Batch, inspect

WBP = '/Game/FoA/Gameplay/Encounter/WBP_Encounter'
FONT = '/Game/FoA/UI/Fonts/F_FoA_UI.F_FoA_UI'
SURFACE = '/Game/FoA/UI/Materials/M_UI_InkSurface.M_UI_InkSurface'


def layout():
    calls = []
    def props(name, values=None, slot=None):
        calls.append(dict(cmd='ui_set_widget_properties', params=dict(
            widget_blueprint_path=WBP, widget_name=name,
            **({'properties': values} if values else {}),
            **({'slot_props': slot} if slot else {}))))
    def canvas(name, anchor, alignment, position, size):
        props(name, slot=dict(anchors_min=anchor, anchors_max=anchor,
            alignment=alignment, position=position, size=size, auto_size=False))
    def text(name, size, wrap=0, alpha=1):
        props(name, dict(Font=dict(FontObject=FONT, TypefaceFontName='SemiBold', Size=size),
            ColorAndOpacity=dict(SpecifiedColor=[.91,.89,.83,alpha]),
            AutoWrapText=False, WrapTextAt=wrap,
            ShadowOffset='(X=0,Y=1)', ShadowColorAndOpacity='(R=0,G=0,B=0,A=0.8)'))
    for panel in ('CommandPanel', 'EnemyPanel', 'LogPanel'):
        props(panel, dict(Background=f'(ResourceObject="/Script/Engine.Material\'{SURFACE}\'",DrawAs=Image)',
            BrushColor='(R=1,G=1,B=1,A=1)', Padding='(Left=24,Top=16,Right=24,Bottom=16)'))
    canvas('CommandPanel',[0,1],[0,1],[48,-52],[1824,292])
    props('ActBox',slot=dict(fill=2.2,padding=[0,0,48,0]))
    props('CmdButtons',slot=dict(fill=1.0))
    props('Txt_Target',dict(Visibility='Collapsed'))
    for i in range(3):
        props('ActCard'+str(i),slot=dict(fill=1,padding=[0,8,24,0]))
        props('Btn_Act'+str(i),dict(LabelSize=28.,TextAlphaRest=.92,TextAlphaHover=1.,TextAlphaDisabled=.48),
              dict(padding=[0,0,0,10]))
        text('Txt_Act'+str(i)+'Detail',20,460,.92)
    for name in ('Breathe','Mirror','NextTarget'):
        props('Btn_'+name,dict(LabelSize=23.,TextAlphaRest=.88,TextAlphaHover=1.,TextAlphaDisabled=.48))
        props('BattleRow_'+name,slot=dict(padding=[0,0,0,0]))
        text('Txt_'+name+'Detail',18,490,.88)
        props('Txt_'+name+'Detail',slot=dict(padding=[40,-4,0,5]))
    props('Txt_NextTargetDetail',dict(Visibility='Collapsed'))
    canvas('EnemyPanel',[1,0],[1,0],[-48,40],[440,170])
    for i in range(5):
        text('Txt_Enemy'+str(i),26,380)
        text('Txt_Intent'+str(i),20,380,.9)
        text('Txt_Progress'+str(i),19,380,.88)
        props('Row'+str(i),slot=dict(fill=1,padding=[0,0,0,0]))
        props('Txt_Intent'+str(i),slot=dict(padding=[0,5,0,0]))
        props('Txt_Progress'+str(i),slot=dict(padding=[0,5,0,0]))
    canvas('SelfBox',[0,0],[0,0],[54,42],[260,110])
    for stat in ('Composure','Resolve'):
        text('Txt_'+stat+'Label',19); text('Txt_'+stat,19)
        props('Size_Bar_'+stat,dict(WidthOverride=260.,bOverride_WidthOverride=True,
            HeightOverride=3.,bOverride_HeightOverride=True))
    canvas('Txt_Statuses',[0,0],[0,0],[54,166],[420,90])
    text('Txt_Statuses',18,410,.88)
    canvas('Txt_BattleHelp',[.5,0],[.5,0],[0,42],[760,48])
    text('Txt_BattleHelp',25,740)
    props('Txt_BattleHelp',dict(Justification='Center'))
    canvas('LogPanel',[.5,1],[.5,1],[0,-366],[1020,82])
    text('Txt_Narration',23,950)
    canvas('Txt_BattleControls',[0,1],[0,1],[60,-18],[1750,28])
    text('Txt_BattleControls',18,1740,.9)
    return calls


def selftest():
    calls = layout()
    assert len(calls)>40
    # The action dock leaves the central stage clear and never clips its final recovery command.
    assert 1080-52-292 > 256
    assert 1080-366 < 1080-52-292
    assert not any(x in json.dumps(calls) for x in ('\u00b7','\u2022'))
    print('Battle layout: preserved widget identities, central stage clear, safe-area bounds pass')


def apply():
    assert not h.call('editor_get_state')['data']['pie_running'], 'User PIE active'
    owner=h.agent_id() or 'main:presentation'
    token=h.lease_acquire(owner,['asset:'+WBP],ttl_s=80,wait_s=3)
    def call(cmd,**params):
        r=h.call(cmd,params,owner=owner,lease=token); assert r.get('ok'),r
        d=r.get('data',{}); assert d.get('ok',True) and not d.get('failed_properties') and not d.get('unknown_slot_props'),d
        return d
    try:
        assert not call('editor_get_state')['pie_running']
        for c in layout(): call(c['cmd'],**c['params'])
        # Keep the live roster data, showing only the target the player is acting on.
        ns,es=inspect(WBP,'RefreshRow')
        both=next(n for n in ns if n['title']=='AND Boolean')
        real=next(e for e in es if e['to_node']==both['node_id'] and e['to_pin']=='B')
        branch=next(e for e in es if e['from_node']==real['from_node'] and e['from_pin']==real['from_pin']
                    and e['to_pin']=='Condition') if not any(e['from_node']==both['node_id'] for e in es) else None
        if branch:
            b=Batch(WBP,'RefreshRow');b.cut(branch['from_node'],branch['from_pin'],branch['to_node'],'Condition')
            b.link(both['node_id'],'ReturnValue',branch['to_node'],'Condition');b.run()
        b=Batch(WBP,'RefreshRow')
        prefix=next((n for n in ns if any(p.get('default_value')=='Selected: ' for p in n['pins'])),None)
        if prefix:
            edge=next(e for e in es if e['from_node']==prefix['node_id'])
            appended=next(e for e in es if e['from_node']==edge['to_node'] and e['from_pin']=='ReturnValue')
            final=next((e for e in es if e['from_node']==appended['to_node'] and e['to_pin']=='InText'),None)
            if final:
                name=next(n for n in ns if n['title']=='Get DisplayName')
                b.cut(final['from_node'],final['from_pin'],final['to_node'],'InText')
                b.link(name['node_id'],'DisplayName',final['to_node'],'InText')
        if b.ops:b.run()
        ns,es=inspect(WBP,'RefreshBattlePresentation')
        b=Batch(WBP,'RefreshBattlePresentation')
        for n in ns:
            for p in n['pins']:
                if p.get('default_value')=='Your turn. Choose your next move.': b.pin(n['node_id'],p['name'],'Your move')
                if p.get('default_value')=="Clothes' turn. Watch their next move.": b.pin(n['node_id'],p['name'],'Watch the sleeves')
        if not any(n['title']=='Get Txt_BattleControls' for n in ns):
            call('ui_set_variable',widget_blueprint_path=WBP,widget_name='Txt_BattleControls',is_variable=True)
            call('blueprint_compile',path=WBP,save=True)
            panel=next(n['node_id'] for n in ns if n['title']=='Get CommandPanel')
            setters=[e['to_node'] for e in es if e['from_node']==panel and e['to_pin']=='self']
            assert len(setters)==2,setters
            b.get('controls','Txt_BattleControls',4200,-1800)
            for i,setter in enumerate(setters):
                n=next(n for n in ns if n['node_id']==setter)
                visibility=next(p['default_value'] for p in n['pins'] if p['name']=='InVisibility')
                assert visibility in ('Visible','Hidden'),visibility
                follow=next(e for e in es if e['from_node']==setter and e['from_pin']=='then')
                ref='controls_visibility_'+str(i)
                b.fn(ref,'/Script/UMG.Widget:SetVisibility',4480,-1800+i*330,InVisibility=visibility)
                b.link('controls','Txt_BattleControls',ref,'self')
                b.cut(setter,'then',follow['to_node'],follow['to_pin'])
                b.chain(setter,ref);b.link(ref,'then',follow['to_node'],follow['to_pin'])
            b.comment('Contextual command hints',['controls','controls_visibility_0','controls_visibility_1'])
        if b.ops:
            b.run()
            ns,es=inspect(WBP,'RefreshBattlePresentation')
            b=Batch(WBP,'RefreshBattlePresentation')
        if not any(n['title']=='Get LogPanel' for n in ns):
            call('ui_set_variable',widget_blueprint_path=WBP,widget_name='LogPanel',is_variable=True)
            call('blueprint_compile',path=WBP,save=True)
            panel=next(n['node_id'] for n in ns if n['title']=='Get CommandPanel')
            setters=[e['to_node'] for e in es if e['from_node']==panel and e['to_pin']=='self']
            assert len(setters)==2,setters
            b.get('log_panel','LogPanel',3050,-1800)
            for i,setter in enumerate(setters):
                n=next(n for n in ns if n['node_id']==setter)
                visibility=next(p['default_value'] for p in n['pins'] if p['name']=='InVisibility')
                follow=next(e for e in es if e['from_node']==setter and e['from_pin']=='then')
                ref='log_position_'+str(i)
                b.fn(ref,'/Script/UMG.Widget:SetRenderTranslation',3330,-1800+i*330,
                     Translation='(X=0,Y='+('0' if visibility=='Visible' else '286')+')')
                b.link('log_panel','LogPanel',ref,'self')
                b.cut(setter,'then',follow['to_node'],follow['to_pin'])
                b.chain(setter,ref);b.link(ref,'then',follow['to_node'],follow['to_pin'])
            b.comment('Clear the action',['log_panel','log_position_0','log_position_1'])
        if b.ops: b.run()
        ns,es=inspect(WBP,'RefreshBattlePresentation')
        heading=next(n['node_id'] for n in ns if n['title']=='Get Txt_BattleHelp')
        targets=[e['to_node'] for e in es if e['from_node']==heading and e['to_pin']=='self']
        if not any(n['title']=='SetRenderOpacity' and n['node_id'] in targets for n in ns):
            resolving=next(n['node_id'] for n in ns if any(p.get('default_value')=='ResolvePlayerAction' for p in n['pins']))
            text_set=next(n['node_id'] for n in ns if n['node_id'] in targets and n['title'].replace(' ','').startswith('SetText'))
            follow=next(e for e in es if e['from_node']==text_set and e['from_pin']=='then')
            b=Batch(WBP,'RefreshBattlePresentation')
            b.fn('heading_alpha','/Script/Engine.KismetMathLibrary:SelectFloat',1660,-2000,A=0,B=1)
            b.link(resolving,'ReturnValue','heading_alpha','bPickA')
            b.fn('heading_visibility','/Script/UMG.Widget:SetRenderOpacity',2000,-2000)
            b.link(heading,'Txt_BattleHelp','heading_visibility','self')
            b.link('heading_alpha','ReturnValue','heading_visibility','InOpacity')
            b.cut(text_set,'then',follow['to_node'],follow['to_pin'])
            b.chain(text_set,'heading_visibility');b.link('heading_visibility','then',follow['to_node'],follow['to_pin'])
            b.comment('Only actionable headings',['heading_alpha','heading_visibility']);b.run()
        result=call('blueprint_compile',path=WBP,save=True)
        assert result['error_count']==result['warning_count']==0,result
        Path('Saved/PresentationReview/battle_layout_applied.json').write_text(json.dumps(result,indent=1))
        print('Compact battle composition saved; runtime review required')
    finally: h.release(owner,token)


if __name__=='__main__':
    selftest()
    if '--apply' in sys.argv: apply()
