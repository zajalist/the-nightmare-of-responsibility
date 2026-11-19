"""Fill the existing phone notebook from GI_FoA.GetNotebook, on Refresh only.
Run with hayba_replay.py FOA_AREAS=UI FOA_PHASE=declare, then FOA_PHASE=body.
"""
import os
exec(open('P:/FoA/Tools/Unreal/ui/bp_graph.py', encoding='utf-8').read())

PHONE = '/Game/FoA/UI/Game/WBP_Phone'
GI = '/Game/FoA/Gameplay/GI_FoA.GI_FoA_C'
KAL = '/Script/Engine.KismetArrayLibrary'
KSTR = '/Script/Engine.KismetStringLibrary'
KTL = '/Script/Engine.KismetTextLibrary'


def run():
    if os.environ.get('FOA_PHASE') == 'declare':
        ensure_vars(PHONE, [('NotebookLines', BEL.get_array_type(ptype('text')), '', 'Phone', False),
                            ('NotebookText', ptype('string'), '', 'Phone', False)])
        Graph.function(PHONE, 'RefreshNotebook')
        Graph.function(PHONE, 'AppendNotebookLine', inputs=[('Index', ptype('int'))])
        compile_save(PHONE)
        return

    g = Graph.function(PHONE, 'RefreshNotebook')
    e = g.at(entry_node(g), 0, 0)
    gi = g.call('/Script/Engine.GameplayStatics:GetGameInstance', 200, 220)
    names = [n for n in g.ed.list_available_nodes([]) if n.replace(' ', '').endswith('CastToGI_FoA')]
    assert names
    cast = g.at(g.ed.create_node_from_name(names[0], V2(480, 0), []), 480, 0)
    read = g.call(GI + ':GetNotebook', 760, 220)
    lines = g.set('NotebookLines', 1040, 0)
    clear = g.set('NotebookText', 1320, 0)
    first = g.call(self_call(PHONE, 'AppendNotebookLine'), 1600, 0, Index=0)
    g.link(gi, 'ReturnValue', cast, 'Object'); g.link(cast, 'AsGI_FoA', read, 'self')
    g.link(read, 'Lines', lines, 'NotebookLines'); g.exec_chain(e, cast, lines, clear, first)
    g.comment('Remembered facts', '', g.ed.list_all_nodes(), C_DATA)

    g = Graph.function(PHONE, 'AppendNotebookLine', inputs=[('Index', ptype('int'))])
    e = g.at(entry_node(g), 0, 0)
    lines = g.get('NotebookLines', 0, 260)
    length = g.call(KAL + ':Array_Length', 240, 260)
    less = g.call('/Script/Engine.KismetMathLibrary:Less_IntInt', 500, 260)
    br = g.branch(760, 0)
    g.link(lines, 'NotebookLines', length, 'TargetArray'); g.link(e, 'Index', less, 'A')
    g.link(length, 'ReturnValue', less, 'B'); g.link(less, 'ReturnValue', br, 'Condition'); g.exec_chain(e, br)
    names = sorted((n for n in g.ed.list_available_nodes([]) if n.replace(' ', '').endswith('|Get(acopy)')), key=len)
    assert names
    item = g.at(g.ed.create_node_from_name(names[0], V2(1000, 240), []), 1000, 240)
    g.link(lines, 'NotebookLines', item, 'Array'); g.link(e, 'Index', item, 'Dimension 1')
    text = g.call(KTL + ':Conv_TextToString', 1260, 240)
    zero = g.call('/Script/Engine.KismetMathLibrary:EqualEqual_IntInt', 1000, 500, B=0)
    nl = g.call('/Script/Engine.KismetMathLibrary:SelectString', 1260, 500, A='', B='\n')
    buffer = g.get('NotebookText', 1260, 680)
    join = g.call(KSTR + ':Concat_StrStr', 1540, 440)
    join2 = g.call(KSTR + ':Concat_StrStr', 1800, 240)
    store = g.set('NotebookText', 2080, -120)
    inc = g.call('/Script/Engine.KismetMathLibrary:Add_IntInt', 2080, 400, B=1)
    again = g.call(self_call(PHONE, 'AppendNotebookLine'), 2360, -120)
    g.link(item, 'Output', text, 'InText'); g.link(e, 'Index', zero, 'A'); g.link(zero, 'ReturnValue', nl, 'bPickA')
    g.link(buffer, 'NotebookText', join, 'A'); g.link(nl, 'ReturnValue', join, 'B')
    g.link(join, 'ReturnValue', join2, 'A'); g.link(text, 'ReturnValue', join2, 'B')
    g.link(join2, 'ReturnValue', store, 'NotebookText'); g.link(e, 'Index', inc, 'A'); g.link(inc, 'ReturnValue', again, 'Index')
    g.link(br, 'True', store, 'execute'); g.exec_chain(store, again)
    target = g.get('Txt_Notebook', 1000, 1080)
    result = g.call(KTL + ':Conv_StringToText', 1260, 1080)
    show = g.call('/Script/UMG.TextBlock:SetText', 1540, 920)
    visible = g.call('/Script/UMG.Widget:SetVisibility', 1800, 920, InVisibility='HitTestInvisible')
    g.link(buffer, 'NotebookText', result, 'InString'); g.link(result, 'ReturnValue', show, 'InText')
    g.link(target, 'Txt_Notebook', show, 'self'); g.link(target, 'Txt_Notebook', visible, 'self')
    g.link(br, 'False', show, 'execute'); g.exec_chain(show, visible)
    g.comment('Notebook lines', '', g.ed.list_all_nodes(), C_DATA)

    g = Graph(PHONE, 'Refresh')
    title = lambda n: BEL.get_node_title(n).replace(' ', '').replace('\n', '')
    if not any(title(n).startswith('RefreshNotebook') for n in g.ed.list_all_nodes()):
        labels = [n for n in g.ed.list_all_nodes() if title(n).startswith('SetLabel')]
        assert len(labels) == 2
        call = g.call(self_call(PHONE, 'RefreshNotebook'), 4400, 0)
        for n in labels:
            assert not PIN.list_connected_pins(BEL.find_then_pin(n))
            g.exec_chain(n, call)
        g.comment('Refresh notebook', '', [call], C_DATA)
    compile_save(PHONE)


run()
