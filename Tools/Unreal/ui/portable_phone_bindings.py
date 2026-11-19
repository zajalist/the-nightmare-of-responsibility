"""Small structural fallback: Hayba has no input-key or delegate-binding node authoring yet."""
exec(open('P:/FoA/Tools/Unreal/ui/bp_graph.py', encoding='utf-8').read())

PHONE='/Game/FoA/UI/Game/BP_Phone'
WIDGET='/Game/FoA/UI/Game/WBP_Phone'


def run():
    g=Graph(PHONE).clear()
    begin=g.event('ReceiveBeginPlay',0,0)
    screen=g.get('Screen',0,200)
    visible=g.call('/Script/Engine.SceneComponent:SetVisibility',300,0,bNewVisibility=True)
    hidden=g.call('/Script/Engine.Actor:SetActorHiddenInGame',650,0,bNewHidden=True)
    g.link(screen,'Screen',visible,'self');g.exec_chain(begin,visible,hidden)
    g.comment('Pocket the phone','',[begin,screen,visible,hidden],C_EVENT)
    groups=[(('Enter','E','SpaceBar','Gamepad_FaceButton_Bottom'),'PhoneConfirm'),
            (('P',),'PhonePutAway'),(('BackSpace','Gamepad_FaceButton_Right'),'PhoneBack'),
            (('Left','Gamepad_DPad_Left'),'PhonePrevious'),(('Right','Gamepad_DPad_Right'),'PhoneNext'),
            (('Up','Gamepad_DPad_Up'),'PhoneUp'),(('Down','Gamepad_DPad_Down'),'PhoneDown')]
    names=g.ed.list_available_nodes([])
    for row,(keys,func) in enumerate(groups):
        nodes=[]
        for col,key in enumerate(keys):
            x,y=col*1050,500+row*600
            hits=[n for n in names if n.startswith('Input|') and n.split('|')[-1].replace(' ','').replace('_','').replace('-','').lower()==key.replace('_','').lower()]
            assert hits,key
            ev=g.at(g.ed.create_node_from_name(hits[0],V2(x,y),[]),x,y)
            opened=g.get('bOpen',x,y+180);br=g.branch(x+280,y);action=g.call(self_call(PHONE,func),x+600,y)
            g.link(ev,'Pressed',br,'execute');g.link(opened,'bOpen',br,'Condition');g.link(br,'True',action,'execute')
            nodes += [ev,opened,br,action]
        g.comment(func.replace('Phone','Phone '),'',nodes,C_EVENT)
    bp=g.bp
    screen=unreal.find_object(None,PHONE+'.BP_Phone_C:Screen_GEN_VARIABLE')
    screen.set_editor_property('receive_hardware_input',True)
    screen.set_editor_property('window_focusable',False)
    screen.set_editor_property('redraw_time',0.033)
    mesh=unreal.find_object(None,PHONE+'.BP_Phone_C:Mesh_GEN_VARIABLE')
    mesh.set_collision_profile_name('NoCollision')
    unreal.EditorAssetLibrary.save_loaded_asset(bp,False)
    print('Phone keyboard and gamepad bindings staged')

    g=Graph(WIDGET)
    if any(str(BEL.get_node_title(n))=='PhoneChooseTasks' for n in g.ed.list_all_nodes()):
        print('Phone click bindings already installed')
        return
    focus=next(n for n in g.ed.list_all_nodes() if str(BEL.get_node_title(n)).replace(' ','').startswith('FocusButton'))
    previous=PIN.get_owning_node(PIN.list_connected_pins(g.pin(focus,'execute'))[0])
    g.ed.remove_nodes([focus])
    for i,(name,fn,index) in enumerate([('Tasks','SetPage',0),('Messages','SetPage',1),('Notes','SetPage',2),
                                       ('Message0','OpenMessage',0),('Message1','OpenMessage',1),('Message2','OpenMessage',2)]):
        x,y=3600+i*700,0
        button=g.get('Btn_'+name,x,y+180)
        bind,ev=bind_event(g,button,'Btn_'+name,'OnClicked','PhoneChoose'+name,x+250,y)
        g.link(previous,'then',bind,'execute');previous=bind
        action=g.call(self_call(WIDGET,fn),x+250,y+400,Index=index)
        g.link(ev,'then',action,'execute')
        g.comment('Choose '+name,'',[button,bind,ev,action],C_EVENT)
    initial=g.call(self_call(WIDGET,'SetPage'),8200,0,Index=0)
    g.link(previous,'then',initial,'execute')
    unreal.EditorAssetLibrary.save_loaded_asset(g.bp,False)
    print('Phone click bindings staged')


run()
