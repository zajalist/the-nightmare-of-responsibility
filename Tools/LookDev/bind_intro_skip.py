"""The single UMG delegate-binding gap in Hayba's native graph authoring."""
exec(open('P:/FoA/Tools/Unreal/ui/bp_graph.py').read())


def bind():
    path='/Game/FoA/UI/Intro/WBP_IntroStory'
    g=Graph(path)
    titles=lambda n: str(BEL.get_node_title(n)).replace(' ','').replace('\n','')
    completed=[n for n in g.ed.list_all_nodes() if titles(n)=='SkipClicked'
               and PIN.list_connected_pins(g.pin(n,'then','out'))]
    if completed:
        print('Skip binding already connected')
        return
    for n in list(g.ed.list_all_nodes()):
        if titles(n) in ('SkipClicked','BindEventtoOnClicked','GetBtn_Skip'):
            g.ed.remove_nodes([n])
    construct=next(n for n in g.ed.list_all_nodes()
                   if isinstance(n, unreal.K2Node_Event) and str(BEL.get_node_title(n))=='Event Construct')
    out=g.pin(construct,'then','out')
    targets=PIN.list_connected_pins(out)
    button=g.get('Btn_Skip',0,-480)
    bind_node,clicked=bind_event(g,button,'Btn_Skip','OnClicked','SkipClicked',250,-650)
    # Native Construct remains the owner of startup; bind before it finds the host.
    PIN.break_pin_links(out)
    g.link(construct,'then',bind_node,'execute')
    for p in targets:
        assert PIN.try_create_connection(g.pin(bind_node,'then','out'),p)
    finish=g.call(self_call(path,'Finish'),650,-450)
    g.link(clicked,'then',finish,'execute')
    g.comment('Skip any time','',[button,bind_node,clicked,finish],C_EVENT)
    unreal.EditorAssetLibrary.save_asset(path,only_if_is_dirty=False)
    print('Bound skip; native compile required')


bind()
