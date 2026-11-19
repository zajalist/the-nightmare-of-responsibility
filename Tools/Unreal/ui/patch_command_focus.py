"""A clear focus frame on optional plain command buttons, preserving the menu style."""
exec(open('P:/FoA/Tools/Unreal/ui/bp_graph.py').read())
PATH='/Game/FoA/UI/Widgets/Common/WBP_SandButton'
bp=unreal.load_asset(PATH)
focus=unreal.find_object(None,PATH+'.WBP_SandButton:WidgetTree.Img_CommandFocus')
parent=focus.get_parent();children=[parent.get_child_at(i) for i in range(parent.get_children_count())]
if children[0]!=focus:
    saved={w.get_name():{k:w.get_editor_property('slot').get_editor_property(k)
           for k in ('padding','horizontal_alignment','vertical_alignment')} for w in children}
    parent.clear_children()
    for w in [focus]+[w for w in children if w!=focus]:
        slot=parent.add_child(w)
        for key,value in saved[w.get_name()].items():slot.set_editor_property(key,value)
g=Graph(PATH,'PushState')
if not any(str(BEL.get_comment_text(n))=='Only the active command' for n in g.ed.list_comment_nodes()):
    for c in list(g.ed.list_comment_nodes()):
        if str(BEL.get_comment_text(c))=='Command focus frame':g.ed.remove_comment_node(c)
    nodes=[n for n in g.ed.list_all_nodes() if BEL.get_node_pos(n).x>=2400]
    if nodes:g.ed.remove_nodes(nodes)
    tail=next(n for n in g.ed.list_all_nodes() if str(BEL.get_node_title(n)).replace(' ','')=='SetRenderOpacity'
              and not PIN.list_connected_pins(BEL.find_then_pin(n)))
    frame=g.get('Img_CommandFocus',2400,224);plain=g.get('bPlainLabel',2400,448);hover=g.get('bHovered',2400,672)
    both=g.call('/Script/Engine.KismetMathLibrary:BooleanAND',2720,448)
    gate=g.branch(3040,0)
    show=g.call('/Script/UMG.Widget:SetVisibility',3360,-160,InVisibility='HitTestInvisible')
    hide=g.call('/Script/UMG.Widget:SetVisibility',3360,160,InVisibility='Hidden')
    g.link(plain,'bPlainLabel',both,'A');g.link(hover,'bHovered',both,'B');g.link(both,'ReturnValue',gate,'Condition')
    g.link(frame,'Img_CommandFocus',show,'self');g.link(frame,'Img_CommandFocus',hide,'self');g.exec_chain(tail,gate)
    g.link(gate,'True',show,'execute');g.link(gate,'False',hide,'execute')
    g.comment('Only the active command','',[frame,plain,hover,both,gate,show,hide],C_VISUAL)
g=Graph(PATH,'ApplyLook')
if not any(str(BEL.get_comment_text(n))=='Align compact text and focus' for n in g.ed.list_comment_nodes()):
    tail=next(n for n in g.ed.list_all_nodes() if str(BEL.get_node_title(n)).replace(' ','')=='SetMinDesiredWidth')
    ret=g.get('Ret_Sand',3232,224)
    slot=g.call('/Script/UMG.WidgetLayoutLibrary:SlotAsOverlaySlot',3552,224)
    pad=g.call('/Script/UMG.OverlaySlot:SetPadding',3872,0,InPadding='(Left=0,Top=0,Right=0,Bottom=0)')
    g.link(ret,'Ret_Sand',slot,'Widget');g.link(slot,'ReturnValue',pad,'self');g.exec_chain(tail,pad)
    g.comment('Align compact text and focus','',[ret,slot,pad],C_VISUAL)
if not any(str(BEL.get_node_title(n)).replace(' ','')=='SetHeightOverride' and BEL.get_node_pos(n).x==5792
           for n in g.ed.list_all_nodes()):
    tail=next(n for n in g.ed.list_all_nodes() if str(BEL.get_node_title(n)).replace(' ','')=='SetPadding'
              and BEL.get_node_pos(n).x==3872)
    label=g.get('Txt_Label',4192,448);ret=g.get('Ret_Sand',4192,672);shell=g.get('SizeBox_0',4192,896)
    labelslot=g.call('/Script/UMG.WidgetLayoutLibrary:SlotAsOverlaySlot',4512,448)
    retslot=g.call('/Script/UMG.WidgetLayoutLibrary:SlotAsOverlaySlot',4512,672)
    center=g.call('/Script/UMG.OverlaySlot:SetVerticalAlignment',4832,0,InVerticalAlignment='VAlign_Center')
    fill=g.call('/Script/UMG.OverlaySlot:SetVerticalAlignment',5152,0,InVerticalAlignment='VAlign_Fill')
    pad=g.call('/Script/UMG.OverlaySlot:SetPadding',5472,0,InPadding='(Left=12,Top=0,Right=16,Bottom=0)')
    height=g.call('/Script/UMG.SizeBox:SetHeightOverride',5792,0,InHeightOverride=52.)
    g.link(label,'Txt_Label',labelslot,'Widget');g.link(ret,'Ret_Sand',retslot,'Widget')
    g.link(labelslot,'ReturnValue',center,'self');g.link(labelslot,'ReturnValue',pad,'self')
    g.link(retslot,'ReturnValue',fill,'self');g.link(shell,'SizeBox_0',height,'self')
    g.exec_chain(tail,center,fill,pad,height)
    g.comment('Center text inside bounds','',[label,ret,shell,labelslot,retslot,center,fill,pad,height],C_VISUAL)
unreal.EditorAssetLibrary.save_loaded_asset(g.bp,False)
print('Command focus frame saved; compile in same lease')
