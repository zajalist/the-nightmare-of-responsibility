"""Honor saved subtitle visibility/size on the HUD; invoke declare then body through hayba_replay.
Action prompts and objectives remain readable when narration subtitles are off.
"""
import os
exec(open('P:/FoA/Tools/Unreal/ui/bp_graph.py', encoding='utf-8').read())

HUD = '/Game/FoA/UI/Game/WBP_HUD'
SG = '/Game/FoA/UI/Framework/SG_FoASettings.SG_FoASettings_C'
LIB = '/Game/FoA/UI/Framework/BPFL_FoASettings.BPFL_FoASettings_C'
TEXT = '/Script/UMG.TextBlock'
KML = '/Script/Engine.KismetMathLibrary'

if os.environ.get('FOA_PHASE') == 'declare':
    ensure_vars(HUD, [('bSubtitlesEnabled', ptype('bool'), 'true', 'Accessibility', False)])
    Graph.function(HUD, 'ApplySubtitleSettings', inputs=[('Settings', ptype(unreal.load_class(None, SG)))])
    Graph.function(HUD, 'RefreshSubtitleSettings')
    compile_save(HUD)
else:
    g = Graph.function(HUD, 'ApplySubtitleSettings')
    e = g.at(entry_node(g), 0, 0)
    enabled = g.get('bSubtitles', 200, 220, class_path=SG)
    size = g.get('SubtitleSize', 200, 420, class_path=SG)
    store = g.set('bSubtitlesEnabled', 500, 0)
    clamp = g.call(KML + ':Clamp', 500, 420, Min=0, Max=2)
    times = g.call(KML + ':Multiply_IntInt', 780, 420, B=6)
    add = g.call(KML + ':Add_IntInt', 1060, 420, B=22)
    narration = g.get('Txt_Narration', 1060, 220)
    font = g.call(TEXT + ':SetFontSize', 1340, 0)
    br = g.branch(1620, 0)
    clear = g.call(self_call(HUD, 'ClearNarration'), 1900, 160)
    g.link(e, 'Settings', enabled, 'self'); g.link(e, 'Settings', size, 'self')
    g.link(enabled, 'bSubtitles', store, 'bSubtitlesEnabled')
    g.link(size, 'SubtitleSize', clamp, 'Value'); g.link(clamp, 'ReturnValue', times, 'A')
    g.link(times, 'ReturnValue', add, 'A'); g.link(add, 'ReturnValue', font, 'DisplayFontSize')
    g.link(narration, 'Txt_Narration', font, 'self'); g.link(enabled, 'bSubtitles', br, 'Condition')
    g.exec_chain(e, store, font, br); g.link(br, 'False', clear, 'execute')
    g.comment('Subtitle preferences', '', g.ed.list_all_nodes(), C_DATA)

    g = Graph.function(HUD, 'RefreshSubtitleSettings')
    e = g.at(entry_node(g), 0, 0)
    load = g.call(LIB + ':LoadSettings', 280, 0)
    apply = g.call(self_call(HUD, 'ApplySubtitleSettings'), 620, 0)
    g.exec_chain(e, load, apply); g.link(load, 'Settings', apply, 'Settings')
    g.comment('Load subtitle preferences', '', g.ed.list_all_nodes(), C_DATA)

    g = Graph.function(HUD, 'HandleNarration')
    e = g.at(entry_node(g), 0, 0)
    enabled = g.get('bSubtitlesEnabled', 200, 220)
    br = g.branch(480, 0)
    widget = g.get('Txt_Narration', 740, 220)
    show = g.call(TEXT + ':SetText', 1020, -80)
    timer = g.call('/Script/Engine.KismetSystemLibrary:K2_SetTimer', 1320, -80,
                   FunctionName='ClearNarration', Time=4.0, bLooping='false')
    clear = g.call(self_call(HUD, 'ClearNarration'), 740, 500)
    g.link(enabled, 'bSubtitlesEnabled', br, 'Condition'); g.exec_chain(e, br)
    g.link(e, 'Line', show, 'InText'); g.link(widget, 'Txt_Narration', show, 'self')
    g.link(br, 'True', show, 'execute'); g.exec_chain(show, timer)
    g.link(br, 'False', clear, 'execute')
    if 'bToolStatus' in [str(n) for n in BEL.list_member_variable_names(unreal.load_asset(HUD))]:
        tool = g.get('bToolStatus', -520, 300)
        inverse = g.call(KML + ':Not_PreBool', -240, 300)
        allowed = g.call(KML + ':BooleanAND', 80, 240)
        PIN.break_pin_links(g.pin(br, 'Condition', 'in'))
        g.link(tool, 'bToolStatus', inverse, 'A'); g.link(inverse, 'ReturnValue', allowed, 'B')
        g.link(enabled, 'bSubtitlesEnabled', allowed, 'A'); g.link(allowed, 'ReturnValue', br, 'Condition')
    if unreal.find_object(None, HUD + '.WBP_HUD:WidgetTree.Brd_Narration'):
        plate = g.get('Brd_Narration', 1020, 440)
        visible = g.call('/Script/UMG.Widget:SetVisibility', 1220, -80, InVisibility='HitTestInvisible')
        PIN.break_pin_links(BEL.find_then_pin(show))
        g.link(plate, 'Brd_Narration', visible, 'self'); g.exec_chain(show, visible, timer)
    g.comment('Optional narration', '', g.ed.list_all_nodes(), C_VISUAL)

    g = Graph(HUD)
    title = lambda n: BEL.get_node_title(n).replace(' ', '').replace('\n', '')
    if not any(title(n).startswith('RefreshSubtitleSettings') for n in g.ed.list_all_nodes()):
        refresh = [n for n in g.ed.list_all_nodes() if title(n).startswith('Refresh')]
        assert len(refresh) == 1 and not PIN.list_connected_pins(BEL.find_then_pin(refresh[0])), 'Unexpected HUD tail'
        call = g.call(self_call(HUD, 'RefreshSubtitleSettings'), 3500, 0)
        g.exec_chain(refresh[0], call)
        g.comment('Subtitle preferences', '', [call], C_DATA)
    compile_save(HUD)
