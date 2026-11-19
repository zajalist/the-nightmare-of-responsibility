"""mech_flow step 2: GI_FoA graphs (day count, knowledge, notebook, save and load through SG_FoA). Idempotent, in phases
with Hayba's C++ blueprint_compile between them (editor-rules: no BlueprintEditorLibrary compiles; CDO writes last):
    ue_remote build_gi.py FOA_PHASE=declare  ->  Hayba blueprint_compile GI_FoA
    ue_remote build_gi.py FOA_PHASE=body     ->  Hayba blueprint_compile GI_FoA
    ue_remote build_gi.py FOA_PHASE=defaults    (errors report, class defaults, save without compiling)
Public API (contract.md): DayCount, HasKnowledge(Flag) -> Known, Learn(Flag), GetNotebook() -> Lines, StartNewDay(),
SaveProgress(), LoadProgress(), ResetProgress(). No loop macros (editor-rules 19:40): the notebook grows as flags are
learned, so reading it is a plain getter. Impure nodes (DoesSaveGameExist) sit on the exec path."""
import os
exec(open('P:/FoA/Tools/Unreal/flow/flow_common.py').read())
PHASE = os.environ.get('FOA_PHASE', 'body')

SG_C, NAME, TEXT = cls_path(SG), ptype('name'), ptype('text')
unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(unreal.load_asset(GI))
if PHASE == 'declare':  # functions other graphs call; Hayba compiles before the bodies are built
    FGraph.function(GI, 'LoadProgress')
    FGraph.function(GI, 'SaveProgress')
FIELDS = ('DayCount', 'Knowledge', 'Notebook')  # what SG_FoA carries


def build_body():
    def slot(g, x, y):
        return g.get('SaveSlot', x, y)


    # LoadProgress: the FoA slot, or keep the class defaults (day 18, nothing known) on a first run
    g = FGraph(GI, 'LoadProgress'); e = g.at(entry_node(g), 0, 0)
    s = slot(g, 0, 224)
    ex = g.call(f'{GS}:DoesSaveGameExist', 224, 0, UserIndex=0)
    br = g.branch(544, 0)
    ld = g.call(f'{GS}:LoadGameFromSlot', 800, 0, UserIndex=0)
    c = cast_to(g, 'SG_FoA', 1120, 0)
    nodes, prev = [e, s, ex, br, ld, c], c
    for i, var in enumerate(FIELDS):
        st = g.set(var, 1440 + 320 * i, 0); gt = g.get(var, 1184 + 320 * i, 224, class_path=SG_C)
        g.link(c, 'AsSG_FoA', gt, 'self'); g.link(gt, var, st, var); g.link(prev, 'then', st, 'execute')
        nodes += [st, gt]; prev = st
    g.link(s, 'SaveSlot', ex, 'SlotName'); g.link(s, 'SaveSlot', ld, 'SlotName'); g.link(ex, 'ReturnValue', br, 'Condition')
    g.exec_chain(e, ex, br); g.link(br, 'True', ld, 'execute'); g.link(ld, 'ReturnValue', c, 'Object'); g.link(ld, 'then', c, 'execute')
    g.comment('Load progress', 'Day count, knowledge and notebook from the FoA slot; a first run keeps the defaults (day 18, '
              'nothing known)', nodes, C_DATA)

    # SaveProgress: a fresh SG_FoA (already typed by its class pin) with the three fields, written to the slot
    g = FGraph(GI, 'SaveProgress'); e = g.at(entry_node(g), 0, 0)
    mk = g.call(f'{GS}:CreateSaveGameObject', 256, 0, SaveGameClass=SG_C)
    nodes, prev = [e, mk], mk
    for i, var in enumerate(FIELDS):
        st = g.set(var, 640 + 320 * i, 0, class_path=SG_C); gt = g.get(var, 384 + 320 * i, 224)
        g.link(mk, 'ReturnValue', st, 'self'); g.link(gt, var, st, var); g.link(prev, 'then', st, 'execute')
        nodes += [st, gt]; prev = st
    sv = g.call(f'{GS}:SaveGameToSlot', 1600, 0, UserIndex=0); s = slot(g, 1344, 304)
    g.exec_chain(e, mk); g.link(prev, 'then', sv, 'execute')
    g.link(mk, 'ReturnValue', sv, 'SaveGameObject'); g.link(s, 'SaveSlot', sv, 'SlotName')
    g.comment('Save progress', 'Day count, knowledge and notebook to the FoA slot (inventory and settings are saved elsewhere)',
              nodes + [sv, s], C_DATA)

    # Learn(Flag): new flags only (None is ignored); the notebook gains its line; saved at once
    g = fn(GI, 'Learn', inputs=[('Flag', NAME)]); e = entry_node(g)
    k = g.get('Knowledge', 0, 224)
    has = g.call(f'{SET}:Set_Contains', 256, 192)
    none = g.call(f'{KML}:EqualEqual_NameName', 256, 320, B='None')
    skip = g.call(f'{KML}:BooleanOR', 544, 224)
    br = g.branch(800, 0)
    add = g.call(f'{SET}:Set_Add', 1056, 0)
    nl = g.get('NotebookLines', 1056, 224)
    find = g.call(f'{MAP}:Map_Find', 1312, 224)
    b2 = g.branch(1376, 0)
    nb = g.get('Notebook', 1600, 224)
    app = g.call(f'{ARR}:Array_Add', 1632, 0)
    sv = g.call(self_call(GI, 'SaveProgress'), 1952, 0)
    g.link(k, 'Knowledge', has, 'TargetSet'); g.link(e, 'Flag', has, 'ItemToFind'); g.link(e, 'Flag', none, 'A')
    g.link(has, 'ReturnValue', skip, 'A'); g.link(none, 'ReturnValue', skip, 'B'); g.link(skip, 'ReturnValue', br, 'Condition')
    g.link(k, 'Knowledge', add, 'TargetSet'); g.link(e, 'Flag', add, 'NewItem')
    g.link(nl, 'NotebookLines', find, 'TargetMap'); g.link(e, 'Flag', find, 'Key'); g.link(find, 'ReturnValue', b2, 'Condition')
    g.link(nb, 'Notebook', app, 'TargetArray'); g.link(find, 'Value', app, 'NewItem')
    g.exec_chain(e, br); g.link(br, 'False', add, 'execute'); g.exec_chain(add, b2); g.link(b2, 'True', app, 'execute')
    g.exec_chain(app, sv); g.link(b2, 'False', sv, 'execute')
    g.comment('Learn a knowledge flag', 'Knows.* names, once each; its NotebookLines line joins the phone notebook; saved at once. '
              'Only BP_BeatDirector calls this', [e, k, has, none, skip, br, add, nl, find, b2, nb, app, sv], C_DATA)

    # HasKnowledge(Flag) -> Known (pure)
    g = fn(GI, 'HasKnowledge', inputs=[('Flag', NAME)], outputs=[('Known', ptype('bool'))], pure=True); e = entry_node(g)
    k = g.get('Knowledge', 0, 192)
    has = g.call(f'{SET}:Set_Contains', 256, 160)
    ret = g.at(result_node(g), 576, 0)
    g.link(k, 'Knowledge', has, 'TargetSet'); g.link(e, 'Flag', has, 'ItemToFind')
    g.exec_chain(e, ret); g.link(has, 'ReturnValue', ret, 'Known')
    g.comment('Has knowledge', 'Look lines, notebook and shortcuts read this', [e, k, has, ret], C_DATA)

    # StartNewDay: one more crossed-out day on the phone
    g = fn(GI, 'StartNewDay'); e = entry_node(g)
    d = g.get('DayCount', 0, 192)
    inc = g.call(f'{KML}:Add_IntInt', 256, 160, B=1)
    sd = g.set('DayCount', 576, 0)
    sv = g.call(self_call(GI, 'SaveProgress'), 896, 0)
    g.link(d, 'DayCount', inc, 'A'); g.link(inc, 'ReturnValue', sd, 'DayCount'); g.exec_chain(e, sd, sv)
    g.comment('Start a new day', 'Day rollover: the day count goes up and is saved; knowledge stays', [e, d, inc, sd, sv], C_DATA)

    # GetNotebook -> Lines (pure)
    g = fn(GI, 'GetNotebook', outputs=[('Lines', BEL.get_array_type(TEXT))], pure=True); e = entry_node(g)
    if 'Found' in [str(n) for n in g.ed.list_local_variable_names()]:  # left from the old filtering version
        g.ed.remove_local_variable('Found')
    nb = g.get('Notebook', 128, 176)
    ret = g.at(result_node(g), 416, 0)
    g.exec_chain(e, ret); g.link(nb, 'Notebook', ret, 'Lines')
    g.comment('Phone notebook', 'One line per known fact, in the order they were learned (WBP_Phone lists these)', [e, nb, ret], C_DATA)

    # ResetProgress: a brand-new game (dev and a future "new game" option)
    g = fn(GI, 'ResetProgress'); e = entry_node(g)
    s = slot(g, 0, 192)
    dl = g.call(f'{GS}:DeleteGameInSlot', 256, 0, UserIndex=0)
    k = g.get('Knowledge', 320, 224); nb = g.get('Notebook', 640, 224)
    clr = g.call(f'{SET}:Set_Clear', 576, 0)
    cln = g.call(f'{ARR}:Array_Clear', 896, 0)
    sd = g.set('DayCount', 1216, 0); g.default(sd, 'DayCount', STARTING_DAY)
    g.link(s, 'SaveSlot', dl, 'SlotName'); g.link(k, 'Knowledge', clr, 'TargetSet'); g.link(nb, 'Notebook', cln, 'TargetArray')
    g.exec_chain(e, dl, clr, cln, sd)
    g.comment('Reset progress', 'Deletes the slot: day 18, nothing known, an empty notebook', [e, s, dl, k, nb, clr, cln, sd], C_DATA)

    # Event graph: load on boot
    g = FGraph(GI).clear()
    init = g.event('ReceiveInit', 0, 0)
    ld = g.call(self_call(GI, 'LoadProgress'), 288, 0)
    g.exec_chain(init, ld)
    g.comment('Load on boot', 'Load the saved day, knowledge and notebook before any level starts', [init, ld], C_EVENT)


if PHASE == 'body':
    build_body()
elif PHASE == 'defaults':  # after the last Hayba compile of GI_FoA this session (crash safety)
    report(GI)
    set_defaults(GI, {'DayCount': STARTING_DAY, 'SaveSlot': 'FoA',
                      'NotebookLines': {unreal.Name(k): unreal.Text(v) for k, v in NOTEBOOK.items()}})
    save_nocompile(GI)
print('done', PHASE)
