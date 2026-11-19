"""Connect existing interaction events to the HUD without rebuilding its objective flow.
Run via hayba_replay.py under a declared UI lease, after adding Txt_Prompt/Txt_Narration.
"""
exec(open('P:/FoA/Tools/Unreal/ui/bp_graph.py', encoding='utf-8').read())

HUD = '/Game/FoA/UI/Game/WBP_HUD'
INTERACTOR = '/Game/FoA/Gameplay/BPC_Interactor.BPC_Interactor_C'
GS = '/Script/Engine.GameplayStatics'
KTL = '/Script/Engine.KismetTextLibrary'
KSL = '/Script/Engine.KismetSystemLibrary'

g = Graph.function(HUD, 'HandleFocusChanged', inputs=[('Target', ptype(unreal.Actor)), ('Prompt', ptype('text')),
                   ('Verbs', BEL.get_array_type(ptype('name'))), ('VerbIndex', ptype('int'))])
e = g.at(entry_node(g), 0, 0)
prompt = g.call(KTL + ':Conv_TextToString', 200, 240)
empty = g.call(KTL + ':TextIsEmpty', 200, 400)
prefix = g.call('/Script/Engine.KismetMathLibrary:SelectString', 480, 400, A='', B='E  ')
line = g.call('/Script/Engine.KismetStringLibrary:Concat_StrStr', 740, 240)
text = g.call(KTL + ':Conv_StringToText', 1000, 240)
widget = g.get('Txt_Prompt', 1000, 400)
set_text = g.call('/Script/UMG.TextBlock:SetText', 1280, 0)
g.link(e, 'Prompt', prompt, 'InText'); g.link(e, 'Prompt', empty, 'InText')
g.link(empty, 'ReturnValue', prefix, 'bPickA'); g.link(prefix, 'ReturnValue', line, 'A')
g.link(prompt, 'ReturnValue', line, 'B'); g.link(line, 'ReturnValue', text, 'InString')
g.link(widget, 'Txt_Prompt', set_text, 'self'); g.link(text, 'ReturnValue', set_text, 'InText')
g.exec_chain(e, set_text)
g.comment('Interaction prompt', '', [e, prompt, empty, prefix, line, text, widget, set_text], C_VISUAL)

g = Graph.function(HUD, 'ClearNarration')
e = g.at(entry_node(g), 0, 0)
widget = g.get('Txt_Narration', 200, 200)
clear = g.call('/Script/UMG.TextBlock:SetText', 480, 0, InText='')
g.link(widget, 'Txt_Narration', clear, 'self'); g.exec_chain(e, clear)
if unreal.find_object(None, HUD + '.WBP_HUD:WidgetTree.Brd_Narration'):
    plate = g.get('Brd_Narration', 480, 220)
    hide = g.call('/Script/UMG.Widget:SetVisibility', 760, 0, InVisibility='Collapsed')
    g.link(plate, 'Brd_Narration', hide, 'self'); g.exec_chain(clear, hide)
g.comment('Clear narration', '', [e, widget, clear], C_VISUAL)

g = Graph.function(HUD, 'HandleNarration', inputs=[('Line', ptype('text'))])
e = g.at(entry_node(g), 0, 0)
widget = g.get('Txt_Narration', 200, 200)
show = g.call('/Script/UMG.TextBlock:SetText', 480, 0)
timer = g.call(KSL + ':K2_SetTimer', 800, 0, FunctionName='ClearNarration', Time=4.0, bLooping='false')
g.link(e, 'Line', show, 'InText'); g.link(widget, 'Txt_Narration', show, 'self'); g.exec_chain(e, show, timer)
g.comment('Action narration', '', [e, widget, show, timer], C_VISUAL)

g = Graph(HUD)
bind_title = lambda n: BEL.get_node_title(n).replace(' ', '').replace('\n', '')
existing = [n for n in g.ed.list_all_nodes() if 'BindEventtoOnFocusChanged' in bind_title(n)]
if not existing:
    beat = [n for n in g.ed.list_all_nodes() if 'BindEventtoOnBeatChanged' in bind_title(n)]
    assert len(beat) == 1 and not PIN.list_connected_pins(BEL.find_then_pin(beat[0])), 'Unexpected HUD Construct tail'
    pawn = g.call(GS + ':GetPlayerPawn', 1500, 240, PlayerIndex=0)
    comp = g.call('/Script/Engine.Actor:GetComponentByClass', 1780, 240, ComponentClass=INTERACTOR)
    names = [n for n in g.ed.list_available_nodes([]) if n.replace(' ', '').endswith('CastToBPC_Interactor')]
    assert names, 'Interactor cast missing'
    cast = g.at(g.ed.create_node_from_name(names[0], V2(2100, 0), []), 2100, 0)
    g.link(pawn, 'ReturnValue', comp, 'self'); g.link(comp, 'ReturnValue', cast, 'Object')
    g.exec_chain(beat[0], cast)
    focus, df = bind_function(g, cast, 'AsBPC_Interactor', 'OnFocusChanged', 'HandleFocusChanged', 2440, 0)
    narration, dn = bind_function(g, cast, 'AsBPC_Interactor', 'OnNarration', 'HandleNarration', 2800, 0)
    refresh = g.call(INTERACTOR + ':Refresh', 3160, 0, bForce='true')
    g.link(cast, 'AsBPC_Interactor', refresh, 'self'); g.exec_chain(cast, focus, narration, refresh)
    g.comment('Listen to interaction', '', [pawn, comp, cast, focus, df, narration, dn, refresh], C_EVENT)
compile_save(HUD)

# Keep the separately declared subtitle preferences when rebuilding the narration consumer.
_subtitle_bp = unreal.load_asset(HUD)
if ('bSubtitlesEnabled' in [str(n) for n in BEL.list_member_variable_names(_subtitle_bp)]
        and 'ApplySubtitleSettings' in [str(n) for n in BEL.list_graph_names(_subtitle_bp)]):
    from pathlib import Path as _SubtitlePath
    import os as _subtitle_os
    import runpy as _subtitle_runpy
    _subtitle_phase = _subtitle_os.environ.get('FOA_PHASE')
    try:
        _subtitle_os.environ['FOA_PHASE'] = 'body'
        _subtitle_runpy.run_path(str(_SubtitlePath(__file__).with_name('wire_subtitles.py')), run_name='__main__')
    finally:
        if _subtitle_phase is None:
            _subtitle_os.environ.pop('FOA_PHASE', None)
        else:
            _subtitle_os.environ['FOA_PHASE'] = _subtitle_phase

# Retain the physical-task ownership guard when rebuilding the normal focus consumer.
if ('bToolStatus' in [str(n) for n in BEL.list_member_variable_names(unreal.load_asset(HUD))]
        and 'ShowToolStatus' in [str(n) for n in BEL.list_graph_names(unreal.load_asset(HUD))]):
    from pathlib import Path as _ToolPath
    import os as _tool_os
    import runpy as _tool_run
    _tool_phase=_tool_os.environ.get('FOA_PHASE')
    try:
        _tool_os.environ['FOA_PHASE']='body'
        _tool_run.run_path(str(_ToolPath(__file__).with_name('wire_tool_status.py')),run_name='__main__')
    finally:
        if _tool_phase is None:_tool_os.environ.pop('FOA_PHASE',None)
        else:_tool_os.environ['FOA_PHASE']=_tool_phase
