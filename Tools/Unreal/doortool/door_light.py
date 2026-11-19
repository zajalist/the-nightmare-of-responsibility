"""Door-tool lane: BP_Door's ToolTaskLight template (the door tool's soft key). At (-24,-79,100) it sat about 10 cm from
the hand and burned the arm white; this moves it and sets its power. Read back, compiled, saved.
  $env:HAYBA_AGENT_ID='doortool'; $env:FOA_AREAS='Gameplay'
  python Tools/Unreal/ue_remote.py Tools/Unreal/doortool/door_light.py FOA_LIGHT=x,y,z FOA_POWER=1.5 [FOA_RADIUS=200]"""
import os

import unreal

DOOR = '/Game/FoA/Gameplay/BP_Door'
bp = unreal.load_asset(DOOR)
sub = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
lib = unreal.SubobjectDataBlueprintFunctionLibrary
light = None
for h in sub.k2_gather_subobject_data_for_blueprint(bp):
    d = lib.get_data(h)
    if str(lib.get_variable_name(d)) == 'ToolTaskLight':
        light = lib.get_object_for_blueprint(d, bp)
assert light, 'ToolTaskLight template not found'
x, y, z = (float(v) for v in os.environ['FOA_LIGHT'].split(','))
light.set_editor_property('relative_location', unreal.Vector(x, y, z))
light.set_editor_property('intensity', float(os.environ['FOA_POWER']))
if os.environ.get('FOA_RADIUS'):
    light.set_editor_property('attenuation_radius', float(os.environ['FOA_RADIUS']))
unreal.BlueprintEditorLibrary.compile_blueprint(bp)
ok = unreal.EditorAssetLibrary.save_asset(DOOR, only_if_is_dirty=False)
print('LIGHT', light.get_editor_property('relative_location'), light.get_editor_property('intensity'),
      light.get_editor_property('intensity_units'), light.get_editor_property('attenuation_radius'), 'saved', ok)
