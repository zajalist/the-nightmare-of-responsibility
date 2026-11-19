"""Tool-owned contextual status in the existing HUD prompt; normal interactor clears cannot erase it."""
import os
exec(open('P:/FoA/Tools/Unreal/ui/bp_graph.py').read())
HUD='/Game/FoA/UI/Game/WBP_HUD'
INTERACTOR='/Game/FoA/Gameplay/BPC_Interactor.BPC_Interactor_C'
if os.environ.get('FOA_PHASE')=='declare':
    ensure_vars(HUD,[('bToolStatus',ptype('bool'),'false','HUD|Context',False)])
    Graph.function(HUD,'ShowToolStatus',inputs=[('LineText',ptype('text'))])
    Graph.function(HUD,'HideToolStatus')
else:
    g=Graph.function(HUD,'ShowToolStatus');e=g.at(entry_node(g),0,0)
    active=g.set('bToolStatus',256,0);g.default(active,'bToolStatus',True)
    text=g.get('Txt_Prompt',1216,224);show=g.call('/Script/UMG.TextBlock:SetText',1536,0)
    clear=g.call(self_call(HUD,'ClearNarration'),1856,0)
    size=g.get('Size_ContextPrompt',256,224);plate=g.get('Brd_ToolPrompt',576,448)
    width=g.call('/Script/UMG.SizeBox:SetWidthOverride',576,0,InWidthOverride=720.)
    pad=g.call('/Script/UMG.Border:SetPadding',896,0,InPadding='(Left=20,Top=12,Right=20,Bottom=12)')
    shade=g.call('/Script/UMG.Border:SetBrushColor',1216,0,InBrushColor='(R=0.006,G=0.006,B=0.006,A=0.9)')
    g.link(size,'Size_ContextPrompt',width,'self');g.link(plate,'Brd_ToolPrompt',pad,'self');g.link(plate,'Brd_ToolPrompt',shade,'self')
    g.link(text,'Txt_Prompt',show,'self');g.link(e,'LineText',show,'InText');g.exec_chain(e,active,width,pad,shade,show,clear)
    g.comment('Show the physical task','',g.ed.list_all_nodes(),C_VISUAL)
    g=Graph.function(HUD,'HideToolStatus');e=g.at(entry_node(g),0,0)
    off=g.set('bToolStatus',256,0);text=g.get('Txt_Prompt',256,224)
    clear=g.call('/Script/UMG.TextBlock:SetText',576,0,InText='')
    pawn=g.call('/Script/Engine.GameplayStatics:GetPlayerPawn',896,224,PlayerIndex=0)
    component=g.call('/Script/Engine.Actor:GetComponentByClass',1216,224,ComponentClass=INTERACTOR)
    names=[n for n in g.ed.list_available_nodes([]) if n.replace(' ','').endswith('CastToBPC_Interactor')]
    cast=g.at(g.ed.create_node_from_name(names[0],V2(1856,0),[]),1856,0)
    paused=g.call('/Script/Engine.KismetSystemLibrary:K2_IsTimerPaused',1856,224,FunctionName='Scan')
    gate=g.branch(2176,0);refresh=g.call(INTERACTOR+':Refresh',2496,0,bForce=True)
    g.link(text,'Txt_Prompt',clear,'self');g.link(pawn,'ReturnValue',component,'self');g.link(component,'ReturnValue',cast,'Object')
    g.link(cast,'AsBPC_Interactor',refresh,'self');g.link(cast,'AsBPC_Interactor',paused,'Object')
    size=g.get('Size_ContextPrompt',576,-224);plate=g.get('Brd_ToolPrompt',896,-448)
    width=g.call('/Script/UMG.SizeBox:ClearWidthOverride',896,0)
    pad=g.call('/Script/UMG.Border:SetPadding',1216,0,InPadding='(Left=0,Top=0,Right=0,Bottom=0)')
    shade=g.call('/Script/UMG.Border:SetBrushColor',1536,0,InBrushColor='(R=0,G=0,B=0,A=0)')
    g.link(size,'Size_ContextPrompt',width,'self');g.link(plate,'Brd_ToolPrompt',pad,'self');g.link(plate,'Brd_ToolPrompt',shade,'self')
    g.link(paused,'ReturnValue',gate,'Condition');g.exec_chain(e,off,clear,width,pad,shade,cast,gate);g.link(gate,'False',refresh,'execute')
    g.comment('Return the normal prompt','',g.ed.list_all_nodes(),C_EVENT)
    g=Graph(HUD,'HandleFocusChanged')
    if not any(str(BEL.get_comment_text(n))=='Keep tool instructions' for n in g.ed.list_comment_nodes()):
        e=entry_node(g);old=list(PIN.list_connected_pins(BEL.find_then_pin(e)));assert len(old)==1
        active=g.get('bToolStatus',-640,224);gate=g.branch(-320,0)
        g.link(active,'bToolStatus',gate,'Condition');PIN.break_pin_links(BEL.find_then_pin(e));g.exec_chain(e,gate)
        assert PIN.try_create_connection(g.pin(gate,'False','out'),old[0])
        g.comment('Keep tool instructions','',[active,gate],C_LOGIC)
unreal.EditorAssetLibrary.save_loaded_asset(unreal.load_asset(HUD),False)
print('Tool HUD',os.environ.get('FOA_PHASE'),'saved; C++ compile in same lease')
