"""Hayba's slot whitelist omits ButtonSlot; set six existing slots in place."""
def main():
    import unreal
    path='/Game/FoA/Level2/Journey/WBP_L2Interview'
    assert unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world() is None
    bp=unreal.load_asset(path);assert bp
    unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(bp)
    tree=unreal.find_object(bp,'WidgetTree');assert tree
    for i in range(3):
        for name,vertical in [('AnswerPad'+str(i),unreal.VerticalAlignment.V_ALIGN_FILL),
                              ('Txt_Answer'+str(i),unreal.VerticalAlignment.V_ALIGN_CENTER)]:
            widget=unreal.find_object(tree,name);assert widget,name
            slot=widget.get_editor_property('slot');assert slot,name
            slot.set_horizontal_alignment(unreal.HorizontalAlignment.H_ALIGN_FILL)
            slot.set_vertical_alignment(vertical)
    assert unreal.EditorAssetLibrary.save_loaded_asset(bp,False)
    print('Three existing button frames fill their slots; three text labels remain centered vertically')


if __name__=='__main__':main()
