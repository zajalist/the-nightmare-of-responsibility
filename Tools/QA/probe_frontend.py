"""qa lane, read-only: the placed BP_FoAFrontEnd's boot settings (why a PIE starts where it does)."""
import unreal

w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
fe = unreal.GameplayStatics.get_actor_of_class(w, unreal.load_class(None, '/Game/FoA/UI/Framework/BP_FoAFrontEnd.BP_FoAFrontEnd_C'))
for k in ('bSkipFrontEnd', 'SplashClass', 'TitleClass', 'MainMenuClass', 'StoryClass', 'WakeBlackSeconds'):
    try:
        v = fe.get_editor_property(k)
        print(k, v.get_name() if hasattr(v, 'get_name') else v)
    except Exception as ex:  # property renamed
        print(k, 'n/a', ex)
cdo = unreal.get_default_object(fe.get_class())
print('CDO bSkipFrontEnd', cdo.get_editor_property('bSkipFrontEnd'))
