"""Read-only saved-asset check: all sixteen controls have their actual delegate and valid row template."""
import json
import runpy

import unreal

spec = runpy.run_path('P:/FoA/Tools/Unreal/ui/settings_calls.py')
path = '/Game/FoA/UI/Widgets/Menus/WBP_Settings'
bp = unreal.load_asset(path)
assert bp, path
BEL = unreal.BlueprintEditorLibrary
GE = unreal.BlueprintGraphEditor
PIN = unreal.BlueprintGraphPinLibrary
expected = {'On' + row[1][4:] + 'Changed' for row in spec['ROWS']}
event = GE.get_graph_editor_by_name(bp, 'EventGraph')
bound = {str(BEL.get_create_delegate_function(node))
         for node in event.list_nodes_of_class(unreal.K2Node_CreateDelegate)}
assert expected == bound, dict(expected=sorted(expected), bound=sorted(bound))
# Generated BindWidget members are not explicit Blueprint members; actual template lookup below verifies them.
templates = []
for _, name, label, value in spec['ROWS']:
    row = unreal.find_object(None, path + '.WBP_Settings:WidgetTree.' + name)
    assert row and str(row.get_editor_property('Label')) == label, name
    if isinstance(value, list):
        assert len(row.get_editor_property('Options')) == len(value), name
    else:
        assert row.get_editor_property('MinValue') < row.get_editor_property('MaxValue'), name
    templates.append(name)
errors = []
for asset in (path, '/Game/FoA/UI/Widgets/Common/WBP_SettingRow_Slider',
              '/Game/FoA/UI/Widgets/Common/WBP_SettingRow_Switcher'):
    owned = unreal.load_asset(asset)
    assert owned and owned.generated_class(), asset
    for name in BEL.list_graph_names(owned):
        graph = GE.get_graph_editor_by_name(owned, str(name))
        if graph:
            errors += [(asset, str(name), str(BEL.get_node_title(n))) for n in graph.list_nodes_with_errors()]
            for node in graph.list_all_nodes():
                if str(BEL.get_node_title(node)).replace(' ', '').startswith('SetText('):
                    target = BEL.find_input_pin(node, 'self')
                    assert PIN.list_connected_pins(target), (asset, str(name), 'unwired TextBlock target')
    if asset.endswith('WBP_SettingRow_Slider'):
        graph = GE.get_graph_editor_by_name(owned, 'HandleSliderChanged')
        entry = graph.list_nodes_of_class(unreal.K2Node_FunctionEntry)[0]
        source = next(p for p in BEL.list_output_pins(entry) if str(PIN.get_pin_name(p)) != 'then')
        assert 'PinSubCategory="float"' in PIN.get_pin_type(source).export_text(), 'Native Slider callback must remain float'
        assert PIN.list_connected_pins(source), 'Native Slider value must reach its stored row value'
assert not errors, errors
result = dict(result='PASS', rows=len(templates), callbacks=sorted(bound), compiler_errors=errors)
with open('P:/FoA/Saved/UIShots/settings_selfcheck.json', 'w') as f:
    json.dump(result, f, indent=2)
print('SETTINGS SELF-CHECK', result)
