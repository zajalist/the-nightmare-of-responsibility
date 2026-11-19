"""Additive native UI delegates and keys. No graph clearing or shared player edits."""
def main():
    import sys
    import unreal
    sys.path.insert(0,'P:/FoA/Tools/Unreal/level2')
    import interview_data as d
    import journey_data as jd
    assert unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world() is None
    scope={};exec(open('P:/FoA/Tools/Unreal/ui/bp_graph.py',encoding='utf-8').read(),scope)
    Graph,BEL,V2,bind=scope['Graph'],scope['BEL'],scope['V2'],scope['bind_event']
    normal=lambda value:''.join(c.lower() for c in str(value) if c.isalnum())
    widget=Graph(d.WIDGET)
    names={normal(BEL.get_node_title(n)) for n in widget.ed.list_all_nodes()}
    if 'dialogueclick0' not in names:
        construct=next((n for n in widget.ed.list_all_nodes() if normal(BEL.get_node_title(n))=='eventconstruct'),None)
        if construct is None:construct=widget.event('Construct',0,0)
        previous=construct
        for i in range(3):
            button=widget.get('Btn_Answer'+str(i),i*850,250)
            for j,(delegate,fn) in enumerate((('OnClicked','Click'),('OnHovered','Hover'))):
                binding,event=bind(widget,button,'Btn_Answer'+str(i),delegate,'Dialogue'+fn+str(i),i*850,500+j*450)
                widget.link(previous,'then',binding,'execute');previous=binding
                action=widget.call(d.WIDGET+'.WBP_L2Interview_C:'+fn,i*850+340,700+j*450,Index=i)
                widget.link(event,'then',action,'execute')
        widget.comment('Conversation choices','',list(widget.ed.list_all_nodes()),scope['C_EVENT'])
    assert unreal.EditorAssetLibrary.save_loaded_asset(widget.bp,False)

    journey=Graph(jd.BP)
    nodes=journey.ed.list_all_nodes();available=journey.ed.list_available_nodes([])
    bindings=[('Up','DialogueMove',dict(Delta=-1)),('Down','DialogueMove',dict(Delta=1)),
              ('Gamepad_DPad_Up','DialogueMove',dict(Delta=-1)),('Gamepad_DPad_Down','DialogueMove',dict(Delta=1)),
              ('Tab','ToggleDialogueNotes',{})]
    # Existing E/A/Enter enhanced input routes through UseStop/Confirm, and X
    # through RetryWithoutTiming. No second binding competes for the same press.
    for index,(key,function,args) in enumerate(bindings):
        existing=next((n for n in nodes if normal(str(BEL.get_node_title(n)).split('\n')[0])==normal(key)),None)
        if existing:
            connected=scope['PIN'].list_connected_pins(journey.pin(existing,'Pressed'))
            if any(normal(str(BEL.get_node_title(scope['PIN'].get_owning_node(pin))).split('\n')[0])==normal(function) for pin in connected):continue
            assert not connected,('Preserve unrelated key binding',key)
        x,y=index*700,9000
        if existing is None:
            hits=[n for n in available if n.startswith('Input|') and normal(n.split('|')[-1])==normal(key)]
            assert len(hits)==1,(key,hits)
            event=journey.at(journey.ed.create_node_from_name(hits[0],V2(x,y),[]),x,y)
        else:event=existing
        action=journey.call(jd.BP+'.BP_L2Journey_C:'+function,x+300,y,**args)
        journey.link(event,'Pressed',action,'execute')
        journey.comment('Conversation '+key,'',[event,action],scope['C_EVENT'])
    # Enter/Y comes from the existing enhanced-input action. Its Completed and
    # Canceled outputs supply the required release without duplicate Enter binds.
    for index,name in enumerate(('IA_L2Continue','IA_Interact','IA_L2Brace')):
        action=next(n for n in journey.ed.list_all_nodes() if name in str(BEL.get_node_title(n)))
        for pin in ('Completed','Canceled'):
            if not scope['PIN'].list_connected_pins(journey.pin(action,pin)):
                release=journey.call(jd.BP+'.BP_L2Journey_C:DialogueRelease',300+index*500,14500+(pin=='Canceled')*250)
                journey.link(action,pin,release,'execute')
    assert unreal.EditorAssetLibrary.save_loaded_asset(journey.bp,False)
    print('Conversation mouse/keyboard/gamepad delegates appended; native compile next')


if __name__=='__main__':main()
