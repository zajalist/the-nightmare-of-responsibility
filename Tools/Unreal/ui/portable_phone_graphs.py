"""Native Hayba graph edits for the portable phone. Existing story and notebook functions stay intact."""
import json
import sys
from pathlib import Path

sys.path.insert(0, 'P:/FoA/Tools/Unreal')
from hayba_call import call

W = '/Game/FoA/UI/Game/WBP_Phone'
P = '/Game/FoA/UI/Game/BP_Phone'
WC = W + '.WBP_Phone_C'
PC = P + '.BP_Phone_C'
PLAYER = '/Game/FoA/Characters/Player/BP_FoAPlayer.BP_FoAPlayer_C'
HOLD = '/Game/FoA/Characters/Player/Montages/AM_FoA_PhoneHold.AM_FoA_PhoneHold'
M = '/Script/Engine.KismetMathLibrary:'
GS = '/Script/Engine.GameplayStatics:'


def run(cmd, **params):
    result = call(cmd, params)
    assert result.get('ok'), result
    data = result.get('data', {})
    assert data.get('ok', True) and not data.get('failed'), data
    assert not data.get('compile_error') and data.get('compile', {}).get('ok', True), data
    if cmd == 'blueprint_inspect_graph':
        page = data.get('page', {})
        for key, offset_key in [('nodes', 'offset'), ('edges', 'edge_offset')]:
            offset = page.get(key, {}).get('next_offset')
            while offset is not None:
                extra = call(cmd, dict(params, **{offset_key: offset}))
                assert extra.get('ok'), extra
                data[key].extend(extra['data'][key])
                next_offset = extra['data']['page'][key]['next_offset']
                assert next_offset is None or next_offset > offset
                offset = next_offset
    return data


class Graph:
    def __init__(self, path, name, inputs=(), clear=True):
        self.path, self.name, self.ops, self.refs = path, name, [], []
        inspected = call('blueprint_inspect_graph', {'path':path,'graph_name':name})
        if not inspected.get('ok'):
            assert 'graph not found' in inspected.get('error','').lower(), inspected
            run('blueprint_add_function', path=path, function_name=name,
                inputs=[{'name': n, 'type': t} for n, t in inputs])
            inspected = call('blueprint_inspect_graph', {'path':path,'graph_name':name})
        assert inspected.get('ok'), inspected
        graph = run('blueprint_inspect_graph', path=path, graph_name=name)
        self.entry = next(n['node_id'] for n in graph['nodes'] if n['title'].replace(' ', '') == name)
        if clear:
            ids = [n['node_id'] for n in graph['nodes'] if n['node_id'] != self.entry]
            if ids:
                self.ops.append(dict(op='remove', node_ids=ids))

    def add(self, name, kind, x, y, **args):
        self.ops.append(dict(op='add_node', ref=name, node_type=kind, x=x, y=y, **args))
        self.refs.append(name)
        return name

    def get(self, name, x=0, y=240, ref=None, **args):
        ref=ref or 'get_' + name
        if len(ref)==22:ref+='_value'
        return self.add(ref, 'variable_get', x, y, variable_name=name, **args)

    def set(self, name, x=300, y=0, ref=None, **args):
        ref=ref or 'set_' + name
        if len(ref)==22:ref+='_value'
        return self.add(ref, 'variable_set', x, y, variable_name=name, **args)

    def fn(self, ref, function, x, y, **defaults):
        self.add(ref, 'call_function', x, y, function_name=function)
        for k, v in defaults.items():
            self.default(ref, k, v)
        return ref

    def default(self, ref, pin, value):
        self.ops.append(dict(op='set_pin', node_id=ref, pin_name=pin,
                             value=str(value).lower() if isinstance(value, bool) else str(value)))

    def link(self, a, b, ap='then', bp='execute'):
        ap = {'True': 'then', 'False': 'else'}.get(ap, ap)
        self.ops.append(dict(op='connect', from_node=a, from_pin=ap, to_node=b, to_pin=bp))

    def chain(self, *nodes):
        for a, b in zip(nodes, nodes[1:]):
            self.link(a, b)

    def text(self, ref, widget, x, y, value=None):
        target = self.get(widget, x, y+180, ref=ref+'_target')
        self.fn(ref, '/Script/UMG.TextBlock:SetText', x+220, y)
        if value is not None:
            literal = self.fn(ref+'_literal', '/Script/Engine.KismetTextLibrary:Conv_StringToText', x, y+340, InString=value)
            self.link(literal, ref, 'ReturnValue', 'InText')
        self.link(target, ref, widget, 'self')
        return ref

    def visible(self, ref, widget, visible, x, y):
        target = self.get(widget, x, y+180, ref=ref+'_target')
        self.fn(ref, '/Script/UMG.Widget:SetVisibility', x+220, y, InVisibility=visible)
        self.link(target, ref, widget, 'self')
        return ref

    def save(self, title):
        self.ops.append(dict(op='comment', title=title, node_ids=self.refs, color=[.12,.26,.16], bubble=True))
        result = run('blueprint_graph_batch', path=self.path, graph_name=self.name, ops=self.ops, compile=True, save=True)
        assert result['compile']['ok'] and result['compile']['error_count']==result['compile']['warning_count']==0 and result['compile']['saved'], result
        Path('Saved/UIShots/phone_' + self.name + '.json').write_text(json.dumps(result, indent=2))
        print(self.name, 'saved')


def widget_graphs():
    info = run('blueprint_get_info', path=W)
    variables = {v['name'] for v in info['variables']}
    for name, typ in [('CurrentPage','int'), ('MessageIndex','int'), ('bReadingMessage','bool')]:
        if name not in variables:
            run('blueprint_add_variable', path=W, variable_name=name, variable_type=typ, category='Phone')
    for name, inputs in [('SetPage',[('Index','int')]), ('BrowsePage',[('Delta','int')]),
                         ('OpenMessage',[('Index','int')]), ('MoveSelection',[('Delta','int')]),
                         ('Confirm',[]), ('Back',[])]:
        if name not in info['functions']:
            run('blueprint_add_function', path=W, function_name=name, inputs=[{'name': n,'type':t} for n,t in inputs])

    g=Graph(W,'SetPage'); e=g.entry
    clamp=g.fn('clamp',M+'Clamp',0,240,Min=0,Max=2); g.link(e,clamp,'Index','Value')
    store=g.set('CurrentPage'); g.link(clamp,store,'ReturnValue','CurrentPage')
    pages=g.get('Pages',300,300); show=g.fn('show','/Script/UMG.WidgetSwitcher:SetActiveWidgetIndex',620,0)
    g.link(pages,show,'Pages','self'); g.link(clamp,show,'ReturnValue','Index')
    reading=g.set('bReadingMessage',940); g.default(reading,'bReadingMessage',False)
    inbox=g.visible('inbox','Inbox','Visible',1240,0)
    detail=g.visible('detail','ReadMessage','Collapsed',1700,0)
    g.chain(e,store,show,reading,inbox,detail)
    prev=detail
    for i,name in enumerate(('Tasks','Messages','Notes')):
        x=2200+i*700
        eq=g.fn('eq'+name,M+'EqualEqual_IntInt',x,250,B=i);g.link(clamp,eq,'ReturnValue','A')
        alpha=g.fn('alpha'+name,M+'SelectFloat',x,400,A=1,B=.38);g.link(eq,alpha,'ReturnValue','bPickA')
        label=g.get('Tab_'+name,x,550)
        dim=g.fn('dim'+name,'/Script/UMG.Widget:SetRenderOpacity',x+300,0)
        g.link(label,dim,'Tab_'+name,'self');g.link(alpha,dim,'ReturnValue','InOpacity');g.chain(prev,dim);prev=dim
    selected=g.fn('selection',WC+':MoveSelection',4400,0,Delta=0);g.chain(prev,selected)
    g.save('Choose phone page')

    g=Graph(W,'BrowsePage');e=g.entry
    page=g.get('CurrentPage');add=g.fn('add',M+'Add_IntInt',250,240);bias=g.fn('bias',M+'Add_IntInt',500,240,B=3)
    mod=g.fn('wrap',M+'Percent_IntInt',750,240,B=3);show=g.fn('show',WC+':SetPage',1000,0)
    g.link(page,add,'CurrentPage','A');g.link(e,add,'Delta','B');g.link(add,bias,'ReturnValue','A')
    g.link(bias,mod,'ReturnValue','A');g.link(mod,show,'ReturnValue','Index');g.chain(e,show);g.save('Browse phone pages')

    g=Graph(W,'OpenMessage');e=g.entry
    index=g.set('MessageIndex');g.link(e,index,'Index','MessageIndex')
    reading=g.set('bReadingMessage',620);g.default(reading,'bReadingMessage',True)
    hide=g.visible('hide','Inbox','Collapsed',900,0);show=g.visible('show','ReadMessage','Visible',1400,0)
    g.chain(e,index,reading,hide,show)
    last=show
    # final text: docs/design/story/script.md section 3 (North American version)
    messages=["Mom\n\nMorning! Your shirt's in the wardrobe, I ironed it.\n\nEat something before you go. Love you",
              "Career Center\n\nReminder: your drop-in appointment is today at 10:30. Reply C to cancel.",
              "Draft\n\nim up"]
    later=["Mom\n\nProud of you. Call me when you're out. Love you",
           "Career Center\n\nWe missed you on Tuesday. Drop in any weekday, 9 to 4. No appointment needed.",
           "Draft\n\nsorry about yesterday. and the day before. today's different i promise"]
    director=g.get('Director',1500,1150)
    beat=g.get('BeatIndex',1800,1150,class_path='/Game/FoA/Gameplay/BP_BeatDirector.BP_BeatDirector_C')
    advanced=g.fn('advanced',M+'GreaterEqual_IntInt',2100,1150,B=3)
    g.link(director,beat,'Director','self');g.link(beat,advanced,'BeatIndex','A')
    for i,body in enumerate(messages):
        x=2000+i*900
        eq=g.fn('is'+str(i),M+'EqualEqual_IntInt',x,240,B=i);g.link(e,eq,'Index','A')
        br=g.add('branch'+str(i),'branch',x,0);g.link(eq,br,'ReturnValue','Condition')
        g.link(last,br, 'then' if i==0 else 'False')
        text=g.text('body'+str(i),'Txt_Message',x+280,-180);g.link(br,text,'True')
        selected=g.fn('message'+str(i),M+'SelectString',x+280,450,A=later[i],B=body)
        conversion=g.fn('text'+str(i),'/Script/Engine.KismetTextLibrary:Conv_StringToText',x+280,850)
        g.link(advanced,selected,'ReturnValue','bPickA');g.link(selected,conversion,'ReturnValue','InString')
        g.link(conversion,text,'ReturnValue','InText')
        last=br
    g.save('Read a message')

    g=Graph(W,'MoveSelection');e=g.entry
    page=g.get('CurrentPage');eq=g.fn('messages',M+'EqualEqual_IntInt',200,240,B=1);g.link(page,eq,'CurrentPage','A')
    br=g.add('branch','branch',480,0);g.link(eq,br,'ReturnValue','Condition');g.chain(e,br)
    index=g.get('MessageIndex',600,300);add=g.fn('add',M+'Add_IntInt',850,240);bias=g.fn('bias',M+'Add_IntInt',1100,240,B=3)
    mod=g.fn('wrap',M+'Percent_IntInt',1350,240,B=3);store=g.set('MessageIndex',1650)
    g.link(index,add,'MessageIndex','A');g.link(e,add,'Delta','B');g.link(add,bias,'ReturnValue','A')
    g.link(bias,mod,'ReturnValue','A');g.link(mod,store,'ReturnValue','MessageIndex');g.link(br,store,'True')
    prev=store
    for i in range(3):
        x=2000+i*650
        eq=g.fn('selected'+str(i),M+'EqualEqual_IntInt',x,250,B=i);g.link(index,eq,'MessageIndex','A')
        alpha=g.fn('alpha'+str(i),M+'SelectFloat',x,400,A=1,B=.4);g.link(eq,alpha,'ReturnValue','bPickA')
        label=g.get('Txt_Sender'+str(i),x,550)
        dim=g.fn('dim'+str(i),'/Script/UMG.Widget:SetRenderOpacity',x+250,0)
        g.link(label,dim,'Txt_Sender'+str(i),'self');g.link(alpha,dim,'ReturnValue','InOpacity');g.chain(prev,dim);prev=dim
    notes=g.get('NotesScroll',600,900);offset=g.fn('offset','/Script/UMG.ScrollBox:GetScrollOffset',850,900)
    delta=g.fn('delta',M+'Multiply_IntInt',600,1100,B=130);g.link(e,delta,'Delta','A')
    conv=g.fn('float',M+'Conv_IntToDouble',850,1100);g.link(delta,conv,'ReturnValue','InInt')
    total=g.fn('total',M+'Add_DoubleDouble',1100,900);g.link(offset,total,'ReturnValue','A');g.link(conv,total,'ReturnValue','B')
    scroll=g.fn('scroll','/Script/UMG.ScrollBox:SetScrollOffset',1400,700)
    g.link(notes,offset,'NotesScroll','self');g.link(notes,scroll,'NotesScroll','self');g.link(total,scroll,'ReturnValue','NewScrollOffset');g.link(br,scroll,'False')
    g.save('Browse screen content')

    g=Graph(W,'Confirm');e=g.entry;page=g.get('CurrentPage')
    eq=g.fn('messages',M+'EqualEqual_IntInt',250,240,B=1);br=g.add('branch','branch',500,0)
    idx=g.get('MessageIndex',700,240);read=g.fn('read',WC+':OpenMessage',950,-120)
    action=g.fn('action',WC+':DoAction',950,120)
    g.link(page,eq,'CurrentPage','A');g.link(eq,br,'ReturnValue','Condition');g.chain(e,br)
    g.link(br,read,'True');g.link(idx,read,'MessageIndex','Index');g.link(br,action,'False');g.save('Confirm phone choice')

    g=Graph(W,'Back');e=g.entry;reading=g.get('bReadingMessage')
    br=g.add('branch','branch',300,0);g.link(reading,br,'bReadingMessage','Condition');g.chain(e,br)
    inbox=g.fn('inbox',WC+':SetPage',650,-120,Index=1);close=g.fn('close',WC+':DoAction',650,120)
    g.link(br,inbox,'True');g.link(br,close,'False');g.save('Back or put away')

    from refine_phone_layout import patch_message_navigation,selection_cue
    patch_message_navigation();selection_cue()
    notebook=run('blueprint_inspect_graph',path=W,graph_name='AppendNotebookLine')
    if not any(n['title'].replace(' ','')=='SelectString' for n in notebook['nodes']):
        raise AssertionError('Notebook formatter changed; inspect before patching its empty state')
    target=next(n for n in notebook['nodes'] if any(p['name']=='InString' for p in n['pins']))
    incoming=next(e for e in notebook['edges'] if e['to_node']==target['node_id'] and e['to_pin']=='InString')
    # Leave the existing newline selector intact; only supply an empty-state sentence at final render.
    if not any(n.get('title')=='Notebook empty state' for n in notebook['nodes']):
        ops=[dict(op='add_node',ref='empty',node_type='call_function',function_name='/Script/Engine.KismetStringLibrary:EqualEqual_StrStr',x=1200,y=1400),
             dict(op='add_node',ref='select',node_type='call_function',function_name=M+'SelectString',x=1500,y=1400),
             dict(op='set_pin',node_id='select',pin_name='A',value='No notes yet.'),
             dict(op='connect',from_node=incoming['from_node'],from_pin=incoming['from_pin'],to_node='empty',to_pin='A'),
             dict(op='connect',from_node=incoming['from_node'],from_pin=incoming['from_pin'],to_node='select',to_pin='B'),
             dict(op='connect',from_node='empty',from_pin='ReturnValue',to_node='select',to_pin='bPickA'),
             dict(op='disconnect',node_id=target['node_id'],pin_name='InString'),
             dict(op='connect',from_node='select',from_pin='ReturnValue',to_node=target['node_id'],to_pin='InString'),
             dict(op='comment',title='Notebook empty state',node_ids=['empty','select'],bubble=True)]
        # Detect the data-path shape on reruns because graph exports omit comment text on older tool builds.
        if incoming['from_pin']=='NotebookText':
            result=run('blueprint_graph_batch',path=W,graph_name='AppendNotebookLine',ops=ops,compile=True,save=True)
            assert result['compile']['error_count']==0


def actor_graphs():
    info=run('blueprint_get_info',path=P); variables={v['name'] for v in info['variables']}
    for name,typ in [('ReturnViewTarget','object:/Script/Engine.Actor'),('bPreviousCursor','bool'),('bPreviousCinematic','bool')]:
        if name not in variables: run('blueprint_add_variable',path=P,variable_name=name,variable_type=typ,category='Phone')
    for name in ('OpenPhone','ClosePhone'):
        g=Graph(P,name);e=g.entry;opening=name=='OpenPhone'
        opened=g.get('bOpen');gate=g.add('gate','branch',250,0);g.link(opened,gate,'bOpen','Condition');g.chain(e,gate)
        pc=g.fn('pc',GS+'GetPlayerController',250,400,PlayerIndex=0)
        pawn=g.fn('pawn',GS+'GetPlayerPawn',250,600,PlayerIndex=0)
        state=g.set('bOpen',600);g.default(state,'bOpen',opening);g.link(gate,state,'False' if opening else 'True')
        if opening:
            view=g.fn('view','/Script/Engine.PlayerController:GetViewTarget',600,400);g.link(pc,view,'ReturnValue','self')
            save=g.set('ReturnViewTarget',900);g.link(view,save,'ReturnValue','ReturnViewTarget')
            cursor=g.get('bShowMouseCursor',900,400,class_path='/Script/Engine.PlayerController');g.link(pc,cursor,'ReturnValue','self')
            savecursor=g.set('bPreviousCursor',1200);g.link(cursor,savecursor,'bShowMouseCursor','bPreviousCursor')
            attach=g.fn('attach','/Script/Engine.Actor:K2_AttachToComponent',1500,0,SocketName='hand_r',LocationRule='KeepRelative',RotationRule='KeepRelative',ScaleRule='KeepWorld',bWeldSimulatedBodies=False)
            pose=g.fn('pose','/Script/Engine.Actor:K2_SetActorRelativeLocation',1850,0,NewRelativeLocation='(X=-6.308080068,Y=-19.136549006,Z=-3.861813574)',bSweep=False,bTeleport=True)
            rotation=g.fn('rotation',M+'MakeRotator',2200,400,Pitch=-40.6120658235,Yaw=-75.5654733509,Roll=-30.1773004719)
            rotate=g.fn('rotate','/Script/Engine.Actor:K2_SetActorRelativeRotation',2200,0,bSweep=False,bTeleport=True)
            g.link(rotation,rotate,'ReturnValue','NewRelativeRotation')
            visible=g.fn('visible','/Script/Engine.Actor:SetActorHiddenInGame',2550,0,bNewHidden=False)
            character=g.add('character','cast',1200,-1000,class_path=PLAYER);g.link(pawn,character,'ReturnValue','Object')
            gripbody=g.get('Body',1500,650,ref='gripbody',class_path=PLAYER);g.link(character,gripbody,'AsBP Fo APlayer','self');g.link(gripbody,attach,'Body','Parent')
            prior=g.get('bCinematic',1500,-700,class_path=PLAYER);g.link(character,prior,'AsBP Fo APlayer','self')
            savecine=g.set('bPreviousCinematic',1800,-1000);g.link(prior,savecine,'bCinematic','bPreviousCinematic')
            stop=g.fn('stopjump','/Script/Engine.Character:StopJumping',2100,-1000);g.link(character,stop,'AsBP Fo APlayer','self')
            cine=g.fn('cine',PLAYER+':SetCinematic',2450,-1000,bEnable=True);g.link(character,cine,'AsBP Fo APlayer','self')
            hold=g.fn('hold','/Script/Engine.Character:PlayAnimMontage',2800,-1000,AnimMontage=HOLD,InPlayRate=1)
            g.link(character,hold,'AsBP Fo APlayer','self')
            mesh=g.get('Mesh',2800,-650,class_path='/Script/Engine.Character');g.link(character,mesh,'AsBP Fo APlayer','self')
            anim=g.fn('anim','/Script/Engine.SkeletalMeshComponent:GetAnimInstance',3100,-650);g.link(mesh,anim,'Mesh','self')
            loop=g.fn('loop','/Script/Engine.AnimInstance:Montage_SetNextSection',3450,-1000,SectionNameToChange='Default',NextSection='Default',Montage=HOLD)
            g.link(anim,loop,'ReturnValue','self')
            g.chain(state,save,savecursor,character,savecine,stop,cine,hold,loop,attach,pose,rotate,visible)
            last=visible
            target=g.add('self','self',2850,400);target_pin='self'
        else:
            last=state;target=g.get('ReturnViewTarget',900,400);target_pin='ReturnViewTarget'
        view=g.fn('blend','/Script/Engine.PlayerController:SetViewTargetWithBlend',2900,0,BlendTime=.45 if opening else .35,BlendFunc='VTBlend_EaseInOut',BlendExp=2,bLockOutgoing=True)
        g.link(pc,view,'ReturnValue','self');g.link(target,view,target_pin,'NewViewTarget');g.chain(last,view)
        inp=g.fn('input','/Script/Engine.Actor:'+('EnableInput' if opening else 'DisableInput'),3250,0)
        g.link(pc,inp,'ReturnValue','PlayerController')
        move=g.fn('move','/Script/Engine.Controller:SetIgnoreMoveInput',3600,0,bNewMoveInput=opening)
        look=g.fn('look','/Script/Engine.Controller:SetIgnoreLookInput',3950,0,bNewLookInput=opening)
        g.link(pc,move,'ReturnValue','self');g.link(pc,look,'ReturnValue','self')
        cursor=g.set('bShowMouseCursor',4300,class_path='/Script/Engine.PlayerController');g.link(pc,cursor,'ReturnValue','self')
        if opening:g.default(cursor,'bShowMouseCursor',True)
        else:
            old=g.get('bPreviousCursor',4300,400);g.link(old,cursor,'bPreviousCursor','bShowMouseCursor')
        mode=g.fn('mode','/Script/UMG.WidgetBlueprintLibrary:'+('SetInputMode_GameAndUIEx' if opening else 'SetInputMode_GameOnly'),4650,0,bFlushInput=True)
        g.link(pc,mode,'ReturnValue','PlayerController')
        if opening:g.default(mode,'bHideCursorDuringCapture',False)
        g.chain(view,inp,move,look,cursor,mode)
        if not opening:
            character=g.add('character','cast',5000,0,class_path=PLAYER);g.link(pawn,character,'ReturnValue','Object')
            prior=g.get('bPreviousCinematic',5300,300)
            cine=g.fn('cine',PLAYER+':SetCinematic',5300,0);g.link(character,cine,'AsBP Fo APlayer','self');g.link(prior,cine,'bPreviousCinematic','bEnable')
            stop=g.fn('stophold','/Script/Engine.Character:StopAnimMontage',5650,0,AnimMontage=HOLD);g.link(character,stop,'AsBP Fo APlayer','self')
            hide=g.fn('hide','/Script/Engine.Actor:SetActorHiddenInGame',6000,0,bNewHidden=True);g.chain(mode,character,cine,stop,hide)
        else:
            refresh=g.fn('refresh',PC+':RefreshScreen',5000,0);g.chain(mode,refresh)
        g.save('Raise phone' if opening else 'Put phone away')


def actor_controls():
    info=run('blueprint_get_info',path=P)
    funcs=[('RefreshScreen','Refresh',{}),('PhoneConfirm','Confirm',{}),('PhoneBack','Back',{}),
           ('PhonePutAway','DoAction',{}),('PhoneNext','BrowsePage',{'Delta':1}),('PhonePrevious','BrowsePage',{'Delta':-1}),
           ('PhoneDown','MoveSelection',{'Delta':1}),('PhoneUp','MoveSelection',{'Delta':-1})]
    for name,_,_ in funcs:
        if name not in info['functions']:run('blueprint_add_function',path=P,function_name=name)
    for name,func,defaults in funcs:
        g=Graph(P,name);e=g.entry
        screen=g.get('Screen');widget=g.fn('widget','/Script/UMG.WidgetComponent:GetUserWidgetObject',250,240)
        cast=g.add('cast','cast',500,0,class_path=WC)
        action=g.fn('action',WC+':'+func,850,0,**defaults)
        g.link(screen,widget,'Screen','self');g.link(widget,cast,'ReturnValue','Object');g.chain(e,cast,action)
        g.link(cast,action,'AsWBP Phone','self')
        g.save('Screen command')


if __name__ == '__main__':
    if len(sys.argv)>1 and sys.argv[1]=='actor':
        actor_controls()
        actor_graphs()
    else:
        widget_graphs()
        # Widget compilation also regenerates its runtime tree after graph authoring.
        run('ui_compile_widget', widget_blueprint_path=W)
        run('ui_save_widget', widget_blueprint_path=W)

