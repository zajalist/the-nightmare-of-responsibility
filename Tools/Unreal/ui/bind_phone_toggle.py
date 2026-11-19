"""Structural fallback for the single unsupported input-key node; keeps the player's event graph."""
exec(open('P:/FoA/Tools/Unreal/ui/bp_graph.py',encoding='utf-8').read())


def main():
    path='/Game/FoA/Characters/Player/BP_FoAPlayer';g=Graph(path)
    existing=[n for n in g.ed.list_all_nodes() if n.get_class().get_name()=='K2Node_InputKey' and str(BEL.get_node_title(n))=='P']
    if existing:
        assert len(existing)==1
        links=PIN.list_connected_pins(g.pin(existing[0],'Pressed'))
        assert links and 'TogglePhone' in str(BEL.get_node_title(PIN.get_owning_node(links[0]))).replace(' ','')
        print('P already opens the phone');return
    names=[n for n in g.ed.list_available_nodes([]) if n.startswith('Input|') and n.split('|')[-1]=='P'];assert names
    event=g.at(g.ed.create_node_from_name(names[0],V2(0,11000),[]),0,11000)
    toggle=g.call(self_call(path,'TogglePhone'),350,11000)
    g.link(event,'Pressed',toggle,'execute');g.comment('Take out phone','',[event,toggle],C_EVENT)
    unreal.EditorAssetLibrary.save_loaded_asset(g.bp,False)
    print('P binding staged; native compile/save next')


main()
