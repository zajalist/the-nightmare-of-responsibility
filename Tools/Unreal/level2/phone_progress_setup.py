"""Structural keys only, under parent's asset lease. Never clears an existing graph.

Run via ue_remote.py after new Journey functions compile, then native compile both
BP_L2Journey and BP_Phone. No engine access on ordinary offline import.
"""
def main():
    import unreal
    scope={}
    exec(open('P:/FoA/Tools/Unreal/ui/bp_graph.py',encoding='utf-8').read(),scope)
    Graph,BEL,V2=scope['Graph'],scope['BEL'],scope['V2']
    plans={
        '/Game/FoA/Level2/Journey/BP_L2Journey':(
            ('P','OpenPhone'),('Gamepad_Special_Left','OpenPhone'),
            ('R','RetryWithoutTiming'),('Gamepad_FaceButton_Left','RetryWithoutTiming'),
            ('C','ShowCVPaper'),('Gamepad_DPad_Left','ShowCVPaper')),
        '/Game/FoA/UI/Game/BP_Phone':(('Gamepad_Special_Left','PhonePutAway'),),
    }
    normalize=lambda value:value.replace(' ','').replace('_','').replace('-','').lower()
    for path,bindings in plans.items():
        g=Graph(path)
        names=g.ed.list_available_nodes([])
        for index,(key,function) in enumerate(bindings):
            existing=[n for n in g.ed.list_all_nodes() if normalize(str(BEL.get_node_title(n)).split('\n')[0])==normalize(key)]
            if existing:continue
            hits=[n for n in names if n.startswith('Input|') and normalize(n.split('|')[-1])==normalize(key)]
            assert len(hits)==1,(key,hits)
            x,y=index*650,6500
            event=g.at(g.ed.create_node_from_name(hits[0],V2(x,y),[]),x,y)
            action=g.call(path+'.'+path.rsplit('/',1)[-1]+'_C:'+function,x+300,y)
            g.link(event,'Pressed',action,'execute')
            title={'ShowCVPaper':'Inspect C.V.','RetryWithoutTiming':'Optional timing assist'}.get(function,'Phone access')
            g.comment(title,'',[event,action],scope['C_EVENT'])
        assert unreal.EditorAssetLibrary.save_loaded_asset(g.bp,False)
    print('Phone and optional retry keys appended. Native compile Journey and BP_Phone next.')


if __name__=='__main__':main()
