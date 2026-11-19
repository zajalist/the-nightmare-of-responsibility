"""Wrap the same prompt object, preserving its original normal overlay slot exactly."""
import unreal
P='/Game/FoA/UI/Game/WBP_HUD'
bp=unreal.load_asset(P)
base=P+'.WBP_HUD:WidgetTree.'
prompt=unreal.find_object(None,base+'Txt_Prompt')
size=unreal.find_object(None,base+'Size_ContextPrompt')
border=unreal.find_object(None,base+'Brd_ToolPrompt')
assert prompt and size and border
if prompt.get_parent()!=border:
    parent=prompt.get_parent()
    children=[parent.get_child_at(i) for i in range(parent.get_children_count())]
    props={w.get_name():{k:w.get_editor_property('slot').get_editor_property(k)
                        for k in ('padding','horizontal_alignment','vertical_alignment')} for w in children}
    order=[size if w==prompt else w for w in children if w!=size]
    prompt.remove_from_parent();border.add_child(prompt)
    parent.clear_children()
    for w in order:
        slot=parent.add_child(w)
        for k,v in props['Txt_Prompt' if w==size else w.get_name()].items():slot.set_editor_property(k,v)
unreal.EditorAssetLibrary.save_loaded_asset(bp,False)
print('Original prompt retained with identical normal overlay padding/alignment; compile/save in same lease')
