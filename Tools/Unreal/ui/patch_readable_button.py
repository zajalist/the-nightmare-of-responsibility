"""Add an optional compact, plain-text style to the existing sand button; menu defaults stay authored."""
exec(open('P:/FoA/Tools/Unreal/ui/bp_graph.py').read())
PATH = '/Game/FoA/UI/Widgets/Common/WBP_SandButton'
ensure_vars(PATH, [('bPlainLabel', ptype('bool'), 'false', 'Sand Button|Style', True),
                ('LabelSize', ptype('real'), '38.0', 'Sand Button|Style', True)])
g = Graph(PATH, 'ApplyLook')
if not any('SetFontSize' in str(BEL.get_node_title(n)) for n in g.ed.list_all_nodes()):
    tail = next(n for n in g.ed.list_all_nodes() if str(BEL.get_node_title(n)).replace(' ', '') == 'SetEffectMaterial')
    label = g.get('Txt_Label', 900, 224); size = g.get('LabelSize', 900, 384)
    font = g.call('/Script/UMG.TextBlock:SetFontSize', 1184, 0)
    plain = g.get('bPlainLabel', 1184, 384); branch = g.branch(1472, 0)
    material = g.call('/Script/UMG.TextBlock:SetFontMaterial', 1760, 0)
    retain = g.get('Ret_Sand', 1760, 224)
    native = g.call('/Script/UMG.RetainerBox:SetRetainRendering', 2048, 0, bInRetainRendering=False)
    slot = g.call('/Script/UMG.WidgetLayoutLibrary:SlotAsOverlaySlot', 2048, 384)
    padding = g.call('/Script/UMG.OverlaySlot:SetPadding', 2336, 0, InPadding='(Left=12,Top=0,Right=16,Bottom=0)')
    shell = g.get('SizeBox_0', 2336, 224)
    height = g.call('/Script/UMG.SizeBox:SetHeightOverride', 2624, 0, InHeightOverride=52.0)
    width = g.call('/Script/UMG.SizeBox:SetMinDesiredWidth', 2912, 0, InMinDesiredWidth=0.0)
    g.exec_chain(tail, font, branch); g.link(label, 'Txt_Label', font, 'self'); g.link(size, 'LabelSize', font, 'DisplayFontSize')
    g.link(plain, 'bPlainLabel', branch, 'Condition'); g.link(branch, 'True', material, 'execute')
    g.link(label, 'Txt_Label', material, 'self'); g.link(retain, 'Ret_Sand', native, 'self')
    g.link(label, 'Txt_Label', slot, 'Widget'); g.link(slot, 'ReturnValue', padding, 'self')
    g.link(shell, 'SizeBox_0', height, 'self'); g.link(shell, 'SizeBox_0', width, 'self')
    g.exec_chain(material, native, padding, height, width)
    g.comment('Readable compact commands', '', [label, size, font, plain, branch, material, retain, native,
              slot, padding, shell, height, width], C_VISUAL)
unreal.EditorAssetLibrary.save_loaded_asset(g.bp, False)
print('Readable button style staged; C++ compile and save in same outer lease')
