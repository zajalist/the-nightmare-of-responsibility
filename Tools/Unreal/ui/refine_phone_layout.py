"""Bound phone content above its footer; retain existing widgets and phone actions."""
import datetime,json,os,shutil,sys
from pathlib import Path
sys.path[:0]=['P:/FoA/Tools/Unreal','P:/FoA/Tools/Unreal/ui']
import hayba_call as h
from portable_phone_graphs import Graph,run,W,M


def patch_message_navigation():
    for name in ('SetPage','OpenMessage'):
        data=run('blueprint_inspect_graph',path=W,graph_name=name)
        if any(n['title'].replace(' ','')=='ScrollToStart' for n in data['nodes']):continue
        g=Graph(W,name,clear=False)
        edge=next(e for e in data['edges'] if e['from_node']==g.entry and e['from_pin']=='then')
        scroll=g.get('MessagesScroll',-700,200)
        start=g.fn('reset_scroll','/Script/UMG.ScrollBox:ScrollToStart',-400,0)
        g.link(scroll,start,'MessagesScroll','self')
        g.ops.append(dict(op='disconnect',node_id=g.entry,pin_name='then'))
        g.ops.append(dict(op='move',node_id=g.entry,x=-1100,y=0))
        g.chain(g.entry,start);g.link(start,edge['to_node'],'then',edge['to_pin'])
        g.save('Reset message scroll')
    data=run('blueprint_inspect_graph',path=W,graph_name='MoveSelection')
    if any(n['title'].replace(' ','')=='ScrollWidgetIntoView' for n in data['nodes']):return
    g=Graph(W,'MoveSelection',clear=False)
    edge=next(e for e in data['edges'] if e['from_node']==g.entry and e['from_pin']=='then')
    reading=g.get('bReadingMessage',-1300,240)
    guard=g.add('reading_guard','branch',-1050,0)
    g.link(reading,guard,'bReadingMessage','Condition')
    scroll=g.get('MessagesScroll',-1300,550)
    offset=g.fn('message_offset','/Script/UMG.ScrollBox:GetScrollOffset',-1050,550)
    delta=g.fn('message_delta',M+'Multiply_IntInt',-1300,800,B=130)
    number=g.fn('message_number',M+'Conv_IntToDouble',-1050,800)
    total=g.fn('message_total',M+'Add_DoubleDouble',-750,550)
    move=g.fn('message_scroll','/Script/UMG.ScrollBox:SetScrollOffset',-450,0)
    g.link(scroll,offset,'MessagesScroll','self');g.link(g.entry,delta,'Delta','A')
    g.link(delta,number,'ReturnValue','InInt');g.link(number,total,'ReturnValue','B')
    g.link(offset,total,'ReturnValue','A');g.link(scroll,move,'MessagesScroll','self')
    g.link(total,move,'ReturnValue','NewScrollOffset')
    g.ops.append(dict(op='disconnect',node_id=g.entry,pin_name='then'))
    g.ops.append(dict(op='move',node_id=g.entry,x=-1650,y=0))
    g.chain(g.entry,guard);g.link(guard,move,'True');g.link(guard,edge['to_node'],'False',edge['to_pin'])
    tails=[n['node_id'] for n in data['nodes'] if n['title'].replace(' ','')=='SetRenderOpacity'
           and not any(e['from_node']==n['node_id'] and e['from_pin']=='then' for e in data['edges'])]
    assert len(tails)==1,tails
    reading_refs=list(g.refs)
    previous=tails[0];index=g.get('MessageIndex',4500,200)
    for i in range(3):
        x=4500+i*900
        eq=g.fn('selected_row'+str(i),M+'EqualEqual_IntInt',x,400,B=i)
        branch=g.add('row_branch'+str(i),'branch',x,0)
        button=g.get('Btn_Message'+str(i),x,600)
        view=g.fn('row_visible'+str(i),'/Script/UMG.ScrollBox:ScrollWidgetIntoView',x+350,-180,AnimateScroll=False,Padding=8)
        g.link(index,eq,'MessageIndex','A');g.link(eq,branch,'ReturnValue','Condition')
        g.link(scroll,view,'MessagesScroll','self');g.link(button,view,'Btn_Message'+str(i),'WidgetToFind')
        g.link(previous,branch,'then' if i==0 else 'False');g.link(branch,view,'True');previous=branch
    g.ops.extend([dict(op='comment',title='Scroll open message',node_ids=reading_refs,bubble=True),
                  dict(op='comment',title='Keep selection visible',node_ids=[r for r in g.refs if r not in reading_refs],bubble=True)])
    run('blueprint_graph_batch',path=W,graph_name='MoveSelection',ops=g.ops,compile=True,save=True)


def selection_cue():
    data=run('blueprint_inspect_graph',path=W,graph_name='MoveSelection')
    index=next(n['node_id'] for n in data['nodes'] if n['title']=='Get MessageIndex')
    modulo=next(n['node_id'] for n in data['nodes'] if n['title']=='% (Integer)')
    comparisons={n['node_id'] for n in data['nodes'] if n['title']=='Equal (Integer)'}
    edges=[e for e in data['edges'] if e['from_node']==modulo and e['to_node'] in comparisons]
    if edges:
        # Pure nodes re-evaluate after the assignment; display the stored selection.
        ops=[]
        for edge in edges:
            ops.extend([dict(op='disconnect',node_id=edge['to_node'],pin_name=edge['to_pin']),
                        dict(op='connect',from_node=index,from_pin='MessageIndex',to_node=edge['to_node'],to_pin=edge['to_pin'])])
        run('blueprint_graph_batch',path=W,graph_name='MoveSelection',ops=ops,compile=True,save=True)
    if any(n['title'].replace(' ','')=='SetBackgroundColor' for n in data['nodes']):return
    g=Graph(W,'MoveSelection',clear=False)
    normalized=lambda value:''.join(c.lower() for c in value if c.isalnum())
    for i in range(3):
        label=next(n['node_id'] for n in data['nodes'] if normalized(n['title'])=='gettxtsender'+str(i))
        dim=next(e['to_node'] for e in data['edges'] if e['from_node']==label and e['to_pin']=='self')
        alpha=next(e['from_node'] for e in data['edges'] if e['to_node']==dim and e['to_pin']=='InOpacity')
        selected=next(e['from_node'] for e in data['edges'] if e['to_node']==alpha and e['to_pin']=='bPickA')
        old=next(e for e in data['edges'] if e['from_node']==dim and e['from_pin']=='then')
        x=2000+i*650
        color=g.fn('row_color'+str(i),M+'SelectColor',x,1450,A='(R=4,G=3,B=1,A=1)',B='(R=1,G=1,B=1,A=1)')
        button=g.get('Btn_Message'+str(i),x,1700)
        tint=g.fn('row_tint'+str(i),'/Script/UMG.Button:SetBackgroundColor',x,1200)
        g.link(selected,color,'ReturnValue','bPickA');g.link(color,tint,'ReturnValue','InBackgroundColor')
        g.link(button,tint,'Btn_Message'+str(i),'self')
        g.ops.append(dict(op='disconnect',node_id=dim,pin_name='then'))
        g.chain(dim,tint);g.link(tint,old['to_node'],'then',old['to_pin'])
    g.save('Mark selected message')


def phone_hint():
    p='/Game/FoA/UI/Game/WBP_HUD'
    names={n['name'] for n in run('ui_query',path=p,flatten=True)['matches']}
    if 'Txt_PhoneHint' not in names:
        run('ui_add_element',widget_blueprint_path=p,name='Txt_PhoneHint',child_class='TextBlock',parent_widget_name='Ovl_Frame')
    run('ui_set_widget_properties',widget_blueprint_path=p,widget_name='Txt_PhoneHint',
        properties={'Text':'P Phone    Ctrl Crouch','Visibility':'HitTestInvisible',
          'Font':{'FontObject':'/Game/FoA/UI/Fonts/F_FoA_UI.F_FoA_UI','TypefaceFontName':'Medium','Size':19},
          'ColorAndOpacity':{'SpecifiedColor':{'R':.92,'G':.88,'B':.77,'A':1},'ColorUseRule':'UseColor_Specified'},
          'ShadowOffset':'(X=0,Y=2)','ShadowColorAndOpacity':'(R=0,G=0,B=0,A=.9)'},
        slot_props={'horizontal_alignment':'Left','vertical_alignment':'Bottom','padding':[48,0,40,32]})
    run('ui_compile_widget',widget_blueprint_path=p);run('ui_save_widget',widget_blueprint_path=p)


def main():
    assert not run('editor_get_state')['pie_running']
    owner='main:phone';os.environ['HAYBA_AGENT_ID']=owner
    token=h.lease_acquire(owner,['asset:'+W,'asset:/Game/FoA/UI/Game/WBP_HUD'],ttl_s=120,wait_s=3)
    os.environ['FOA_LEASE']=token
    try:
        backup=Path('Saved/Backups/phone_layout')/datetime.datetime.now().strftime('%Y%m%d_%H%M%S');backup.mkdir(parents=True)
        for name in ('WBP_Phone','WBP_HUD'):shutil.copy2('Content/FoA/UI/Game/'+name+'.uasset',backup/(name+'.uasset'))
        before={x['name']:x.get('guid') for x in run('ui_query',path=W,flatten=True,include_guid=True)['matches']}
        import portable_phone_ui
        portable_phone_ui.main();patch_message_navigation();selection_cue();phone_hint()
        run('ui_compile_widget',widget_blueprint_path=W);run('ui_save_widget',widget_blueprint_path=W)
        after=run('ui_query',path=W,flatten=True,include_guid=True)['matches']
        assert all(next(x for x in after if x['name']==name).get('guid')==guid for name,guid in before.items())
        assert next(x for x in after if x['name']=='Txt_Message')['parent']=='ReadMessage'
        Path('Saved/UIShots/phone_layout_applied.json').write_text(json.dumps({'backup':str(backup),'identities_preserved':True,'widgets':after},indent=1))
    finally:h.release(owner,token);os.environ.pop('FOA_LEASE',None)


if __name__=='__main__':main()
