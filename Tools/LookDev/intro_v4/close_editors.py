"""Close the intro assets' editors after graph captures (intro lane):
  python Tools/Unreal/ue_remote.py Tools/LookDev/intro_v4/close_editors.py FOA_AREAS=/Game/FoA/UI/Intro"""
import unreal

aes = unreal.get_editor_subsystem(unreal.AssetEditorSubsystem)
for p in ('/Game/FoA/UI/Intro/WBP_IntroStory', '/Game/FoA/UI/Intro/M_IntroPlate'):
    aes.close_all_editors_for_asset(unreal.load_asset(p))
print('closed')
