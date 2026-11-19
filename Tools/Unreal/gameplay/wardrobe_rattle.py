"""Delay only the real wardrobe pivot animation for a two-second rattle. Existing fall sends Arrived normally."""
exec(open('P:/FoA/Tools/Unreal/ui/bp_graph.py').read())
PATH='/Game/FoA/Gameplay/BP_Interactable'
g=Graph(PATH)
norm=lambda n:str(BEL.get_node_title(n)).replace(' ','').replace('\n','').lower()
events=g.ed.list_nodes_of_class(unreal.K2Node_CustomEvent)
if not any(norm(n)=='wardrobebeginfall' for n in events):
    start=next(n for n in events if norm(n)=='animatepivot')
    out=BEL.find_then_pin(start);old=list(PIN.list_connected_pins(out));assert len(old)==1
    key=g.get('InteractionKey',0,1840)
    wardrobe=g.call('/Script/Engine.KismetMathLibrary:EqualEqual_NameName',256,1840,B='Wardrobe')
    gate=g.branch(544,1360)
    timer=g.call('/Script/Engine.KismetSystemLibrary:K2_SetTimer',832,1840,FunctionName='WardrobeBeginFall',Time=2.,bLooping=False)
    g.link(key,'InteractionKey',wardrobe,'A');g.link(wardrobe,'ReturnValue',gate,'Condition')
    PIN.break_pin_links(out);g.exec_chain(start,gate);g.link(gate,'True',timer,'execute')
    assert PIN.try_create_connection(g.pin(gate,'False','out'),old[0])
    begin=g.custom_event('WardrobeBeginFall',0,2256)
    state=g.get('State',256,2480)
    falling=g.call('/Script/Engine.KismetMathLibrary:EqualEqual_NameName',544,2480,B='Falling')
    valid=g.branch(832,2256);g.link(state,'State',falling,'A');g.link(falling,'ReturnValue',valid,'Condition')
    g.exec_chain(begin,valid);assert PIN.try_create_connection(g.pin(valid,'True','out'),old[0])
    g.comment('Rattle before the fall','',[key,wardrobe,gate,timer,begin,state,falling,valid],C_VISUAL)
    reset=next(n for n in g.ed.list_all_nodes() if 'resetfornewday' in norm(n) and isinstance(n,unreal.K2Node_Event))
    old=list(PIN.list_connected_pins(BEL.find_then_pin(reset)));assert len(old)==1
    clear=g.call('/Script/Engine.KismetSystemLibrary:K2_ClearTimer',-960,1000,FunctionName='WardrobeBeginFall')
    names=[n for n in g.ed.list_available_nodes([]) if n.replace(' ','').lower().endswith('|sequence')]
    sequence=g.at(g.ed.create_node_from_name(names[0],V2(-640,1000),[]),-640,1000)
    move=next(n for n in g.ed.list_all_nodes() if norm(n).startswith('movecomponentto'))
    stop=g.custom_event('StopPivotMotion',-960,1600)
    g.link(stop,'then',move,'Stop')
    PIN.break_pin_links(BEL.find_then_pin(reset));g.exec_chain(reset,clear,sequence)
    g.link(sequence,'then_0',move,'Stop')
    assert PIN.try_create_connection(g.pin(sequence,'then_1','out'),old[0])
    g.comment('Cancel a pending fall','',[clear,sequence],C_LOGIC)

# Manny is the hidden pose driver for the visible MetaHuman. React on the same existing delayed fall event;
# Character.PlayAnimMontage targets that driver without acquiring another movement lock or creating a timer.
startle='/Game/FoA/Characters/Player/Montages/AM_FoA_Startle.AM_FoA_Startle'
plays=[n for n in g.ed.list_all_nodes() if norm(n).startswith('playanimmontage')
       and (str(PIN.get_pin_value(g.pin(n,'AnimMontage','in'))).find('AM_FoA_Startle')>=0
            or BEL.get_node_pos(n).y==2256)]
if not plays:
    begin=next(n for n in g.ed.list_nodes_of_class(unreal.K2Node_CustomEvent) if norm(n)=='wardrobebeginfall')
    gate=PIN.get_owning_node(PIN.list_connected_pins(BEL.find_then_pin(begin))[0])
    old=list(PIN.list_connected_pins(g.pin(gate,'True','out')));assert len(old)==1
    pawn=g.call('/Script/Engine.GameplayStatics:GetPlayerCharacter',1152,2480,PlayerIndex=0)
    react=g.call('/Script/Engine.Character:PlayAnimMontage',1472,2256,AnimMontage=startle)
    g.link(pawn,'ReturnValue',react,'self');PIN.break_pin_links(g.pin(gate,'True','out'))
    g.link(gate,'True',react,'execute');assert PIN.try_create_connection(BEL.find_then_pin(react),old[0])
    g.comment('React to the falling wardrobe','',[pawn,react],C_VISUAL)
unreal.EditorAssetLibrary.save_loaded_asset(g.bp,False)
print('Wardrobe rattle delay saved; C++ compile in same lease')
