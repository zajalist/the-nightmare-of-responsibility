"""Typed MPC default update only. Retains parameter IDs/order; edits no material graphs."""
import json
from pathlib import Path
import re
import unreal

collection = unreal.load_asset('/Game/FoA/PostProcess/MPC_Dream')
before, after = {}, {}
def identities(parameters):
    values = []
    for parameter in parameters:
        text = parameter.export_text()
        guid = re.search(r'Id=(\([^)]*\)|[^,)]+)', text)
        assert guid, text
        values.append((str(parameter.get_editor_property('parameter_name')), guid.group(0)))
    return values
for property_name, target, value in (
        ('scalar_parameters', 'EchoStrength', .08),
        ('vector_parameters', 'LensLook', unreal.LinearColor(.08, .10, .16, .08))):
    parameters = list(collection.get_editor_property(property_name))
    ids = identities(parameters)
    parameter = next(p for p in parameters if str(p.get_editor_property('parameter_name')) == target)
    before[target] = str(parameter.get_editor_property('default_value'))
    parameter.set_editor_property('default_value', value)
    collection.set_editor_property(property_name, parameters)
    actual = list(collection.get_editor_property(property_name))
    assert identities(actual) == ids
    after[target] = str(next(p for p in actual if str(p.get_editor_property('parameter_name')) == target).get_editor_property('default_value'))
Path('P:/FoA/Saved/Integration/clarity_defaults.json').write_text(json.dumps(dict(before=before, after=after, ids_preserved=True), indent=2))
print('MPC look defaults updated; all IDs and order preserved')
