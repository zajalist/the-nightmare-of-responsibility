"""Read-only probe: BlueprintEditorLibrary methods about variable flags, and SleepEyeClosure's property flags."""
import unreal
print('BEL', [n for n in dir(unreal.BlueprintEditorLibrary) if 'variable' in n])
bp = unreal.load_asset('/Game/FoA/Characters/Player/BP_FoAPlayer')
cdo = unreal.get_default_object(bp.generated_class())
for n in ('SleepEyeClosure', 'bCinematic'):
    try:
        print(n, cdo.get_editor_property(n))
    except Exception as e:
        print(n, 'ERR', e)
