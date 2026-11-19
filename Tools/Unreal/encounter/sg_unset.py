"""Battle lane repair (11-18 15:35): B3d's first run put the editor's sg.* cvars back with plain console sets, which left
them at SetByConsole priority, so every later preset switch (scalability command, GameUserSettings, the Settings menu)
was ignored for sg.*. UnsetCVar drops the console layer; the value falls back to the Scalability one underneath.
  $env:FOA_AREAS='console'; python Tools/Unreal/ue_remote.py Tools/Unreal/encounter/sg_unset.py"""
import unreal

GROUPS = ('ResolutionQuality', 'ViewDistanceQuality', 'AntiAliasingQuality', 'ShadowQuality', 'GlobalIlluminationQuality',
          'ReflectionQuality', 'PostProcessQuality', 'TextureQuality', 'EffectsQuality', 'FoliageQuality', 'ShadingQuality',
          'LandscapeQuality')
S = unreal.SystemLibrary
before = {'ResolutionQuality': 100, **{g: 3 for g in GROUPS[1:]}}  # the editor's levels when B3d first read them (ld_restore 'was')
for g in GROUPS:
    S.execute_console_command(None, 'UnsetCVar sg.' + g)
fell = {g: S.get_console_variable_int_value('sg.' + g) for g in GROUPS}
# the layer underneath held B3d's last `scalability 1`: put the editor's own levels back at Scalability priority
for g, v in before.items():
    S.execute_console_command(None, f'SetCVar sg.{g} {v} -setby=Scalability')
after = {g: S.get_console_variable_int_value('sg.' + g) for g in GROUPS}
print('SG_UNSET before', before)
print('SG_UNSET fell to', fell)
print('SG_UNSET after', after, 'same' if after == before else 'DIFFERENT')
