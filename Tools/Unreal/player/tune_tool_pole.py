"""Anim lane: retunes the elbow pole of SetToolHandRotation's tool branch (pin literals only, no structure change).
  FOA_AREAS=Characters python Tools/Unreal/ue_remote.py Tools/Unreal/player/tune_tool_pole.py FOA_BACK=-30 FOA_OUT=28 FOA_DOWN=-5
The pole is hand + forward*BACK + right*OUT + (0,0,DOWN): the elbow sits behind and outside the fist, so the forearm runs
along the screwdriver instead of rising to it from below."""
import os
import unreal
BEL, PIN = unreal.BlueprintEditorLibrary, unreal.BlueprintGraphPinLibrary
bp = unreal.load_asset('/Game/FoA/Characters/Player/BP_FoAPlayer')
unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(bp)
ed = unreal.BlueprintGraphEditor.get_graph_editor_by_name(bp, 'SetToolHandRotation')
want = {'GetActorForwardVector': os.environ.get('FOA_BACK', '-30'), 'GetActorRightVector': os.environ.get('FOA_OUT', '28')}
hits = 0
for n in ed.list_all_nodes():
    title = str(BEL.get_node_title(n)).replace(' ', '')
    pins = {str(PIN.get_pin_name(p)): p for p in BEL.list_all_pins(n)}
    if title == 'vector*float':  # Multiply_VectorFloat: which actor vector feeds A decides the term
        src = [str(BEL.get_node_title(PIN.get_owning_node(q))).replace(' ', '') for q in PIN.list_connected_pins(pins['A'])]
        for k, v in want.items():
            if src == [k]:
                assert PIN.set_pin_value(pins['B'], v); hits += 1
    if title == 'vector+vector' and not PIN.list_connected_pins(pins['B']):
        assert PIN.set_pin_value(pins['B'], '0,0,' + os.environ.get('FOA_DOWN', '-5')); hits += 1
assert hits == 3, hits
unreal.EditorAssetLibrary.save_loaded_asset(bp, False)
print('POLE set', want, os.environ.get('FOA_DOWN', '-5'))
