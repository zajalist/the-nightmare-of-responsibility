"""Run in the coordinator's free-roam PIE; restores saved preferences and never writes the settings slot."""
import unreal

world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
fe = unreal.GameplayStatics.get_actor_of_class(world, unreal.load_class(
    None, '/Game/FoA/UI/Framework/BP_FoAFrontEnd.BP_FoAFrontEnd_C'))
assert fe and fe.get_editor_property('HUD'), 'Run after the wake-up handoff'
hud = fe.get_editor_property('HUD')
narration = hud.get_editor_property('Txt_Narration')
prompt = hud.get_editor_property('Txt_Prompt')
original_prompt = str(prompt.get_text())
settings = unreal.GameplayStatics.create_save_game_object(unreal.load_class(
    None, '/Game/FoA/UI/Framework/SG_FoASettings.SG_FoASettings_C'))
try:
    for index, expected in ((0, 22), (1, 28), (2, 34), (-10, 22), (50, 34)):
        settings.set_editor_property('bSubtitles', True)
        settings.set_editor_property('SubtitleSize', index)
        hud.call_method('ApplySubtitleSettings', (settings,))
        hud.call_method('HandleNarration', ('The wardrobe has blocked the door.',))
        assert str(narration.get_text()) == 'The wardrobe has blocked the door.'
        assert abs(narration.get_font_size() - expected) < 0.01, (index, narration.get_font_size())
    settings.set_editor_property('bSubtitles', False)
    hud.call_method('ApplySubtitleSettings', (settings,))
    assert not str(narration.get_text()), 'Turning subtitles off must clear the current line'
    hud.call_method('HandleNarration', ('Hidden narration',))
    assert not str(narration.get_text()), 'Disabled subtitles must remain hidden'
    assert str(prompt.get_text()) == original_prompt, 'Accessibility toggle hid an action prompt'
    print('PASS subtitles: on/off, immediate clear, three sizes, clamped indices, action prompt preserved')
finally:
    hud.call_method('ClearNarration')
    hud.call_method('RefreshSubtitleSettings')
