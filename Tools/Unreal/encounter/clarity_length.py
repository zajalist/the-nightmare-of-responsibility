"""Battle lane: wire Array_Length(Garments) into WBP_Encounter.PlaceMark's index guard (B of the Less node that still
holds the 9001 sentinel). Hayba's graph commands leave Array_Length's wildcard untyped (a Hayba gap), so this one node
goes in through editor Python, whose schema connection types it. Run, then compile through Hayba:
  $env:FOA_AREAS='/Game/FoA/Gameplay/Encounter/WBP_Encounter'; python Tools/Unreal/ue_remote.py Tools/Unreal/encounter/clarity_length.py"""
import unreal

exec(open('P:/FoA/Tools/Unreal/ui/bp_graph.py', encoding='utf-8').read())
WBP = '/Game/FoA/Gameplay/Encounter/WBP_Encounter'


def run():
    g = Graph(WBP, 'PlaceMark')
    nodes = list(g.ed.list_all_nodes())
    stale = [n for n in nodes if n.get_class().get_name() == 'K2Node_CallArrayFunction']
    getters = [n for n in nodes if n.get_class().get_name() == 'K2Node_VariableGet'
               and any(str(PIN.get_pin_name(p)) == 'Garments' for p in BEL.list_all_pins(n))]
    less = [n for n in nodes if any(str(PIN.get_pin_name(p)) == 'B' and str(PIN.get_pin_value(p)) == '9001'
                                    for p in BEL.list_all_pins(n))]
    print('stale lengths', len(stale), 'garment getters', len(getters), 'sentinel nodes', len(less))
    if not less:
        for n in nodes:
            bs = [str(PIN.get_pin_value(p)) for p in BEL.list_all_pins(n) if str(PIN.get_pin_name(p)) == 'B']
            if bs:
                print(' ', n.get_class().get_name(), n.get_name(), bs)
    assert getters and len(less) == 1, 'nothing to wire'
    if stale:
        g.ed.remove_nodes(stale)
    ln = g.call('/Script/Engine.KismetArrayLibrary:Array_Length', 600, 1000)
    g.link(getters[0], 'Garments', ln, 'TargetArray')
    g.link(ln, 'ReturnValue', less[0], 'B')
    print('wired Array_Length; TargetArray type:', PIN.get_pin_type(g.pin(ln, 'TargetArray', 'in')) if hasattr(PIN, 'get_pin_type') else '?')


run()
