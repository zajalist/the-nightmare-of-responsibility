"""Read the existing startup warning preference once, after the splash timer starts.
The designer TextBlock must already exist; no widget tree is rebuilt here.
"""
exec(open('P:/FoA/Tools/Unreal/ui/bp_graph.py', encoding='utf-8').read())

SPLASH = '/Game/FoA/UI/Widgets/Menus/WBP_BootSplash'
SG = '/Game/FoA/UI/Framework/SG_FoASettings.SG_FoASettings_C'
LIB = '/Game/FoA/UI/Framework/BPFL_FoASettings.BPFL_FoASettings_C'
g = Graph(SPLASH)
title = lambda n: BEL.get_node_title(n).replace(' ', '').replace('\n', '')
if not any('TxtPhotoWarning' in title(n) for n in g.ed.list_all_nodes()):
    timers = [n for n in g.ed.list_all_nodes() if title(n).startswith('SetTimerbyFunctionName')]
    assert len(timers) == 1 and not PIN.list_connected_pins(BEL.find_then_pin(timers[0])), 'Unexpected splash tail'
    load = g.call(LIB + ':LoadSettings', 2000, 0)
    enabled = g.get('bShowPhotoWarning', 2280, 240, class_path=SG)
    br = g.branch(2560, 0)
    warning = g.get('Txt_PhotoWarning', 2560, 260)
    show = g.call('/Script/UMG.Widget:SetVisibility', 2860, -80, InVisibility='HitTestInvisible')
    hide = g.call('/Script/UMG.Widget:SetVisibility', 2860, 420, InVisibility='Collapsed')
    g.exec_chain(timers[0], load, br); g.link(load, 'Settings', enabled, 'self')
    g.link(enabled, 'bShowPhotoWarning', br, 'Condition')
    g.link(warning, 'Txt_PhotoWarning', show, 'self'); g.link(warning, 'Txt_PhotoWarning', hide, 'self')
    g.link(br, 'True', show, 'execute'); g.link(br, 'False', hide, 'execute')
    g.comment('Startup warning', '', [load, enabled, br, warning, show, hide], C_DATA)
compile_save(SPLASH)
