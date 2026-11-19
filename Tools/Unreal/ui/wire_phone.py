"""WBP_Phone graph (run via hayba_replay.py; tree from phone_calls.py). Event-driven, no Tick.
  Construct      find BP_FoAFrontEnd (Host) and BP_BeatDirector (Director), bind OnPhoneChanged -> Refresh, Refresh,
                 bind the action button, focus it
  Refresh        GetPhoneTasks -> the four task rows (ticked ones dim), day and crossed-out days from GI_FoA.DayCount,
                 the action's label: "Wake up" until that task is ticked, then "Put the phone away"
  HandleAction   Wake up reports PhoneWakeUp to the director; either way the front end closes the phone
Contract: docs/mechanics/contract.md, "Phone data"."""
exec(open('P:/FoA/Tools/Unreal/ui/bp_graph.py').read())
import unreal

P_ = '/Game/FoA/UI/Game/WBP_Phone'
FE_C = '/Game/FoA/UI/Framework/BP_FoAFrontEnd.BP_FoAFrontEnd_C'
BD_C = '/Game/FoA/Gameplay/BP_BeatDirector.BP_BeatDirector_C'
GI_C = '/Game/FoA/Gameplay/GI_FoA.GI_FoA_C'
BTN_C = '/Game/FoA/UI/Widgets/Common/WBP_SandButton.WBP_SandButton_C'
GS, KML, KTL = '/Script/Engine.GameplayStatics', '/Script/Engine.KismetMathLibrary', '/Script/Engine.KismetTextLibrary'
T_TEXT, T_BOOL = ptype('text'), ptype('bool')

ensure_vars(P_, [
    ('Host', ptype(unreal.load_class(None, FE_C)), '', 'Phone|State', False),
    ('Director', ptype(unreal.load_class(None, BD_C)), '', 'Phone|State', False),
    ('TaskLabels', BEL.get_array_type(T_TEXT), '', 'Phone|State', False),
    ('TaskTicked', BEL.get_array_type(T_BOOL), '', 'Phone|State', False),
])
for f in ('Refresh', 'ShowTask'):
    drop_function(P_, f)
Graph.function(P_, 'Refresh'); Graph.function(P_, 'DoAction')
Graph.function(P_, 'ShowTask', inputs=[('Index', ptype('int')), ('Row', ptype(unreal.TextBlock))])


def cast_node(g, cls_name, x, y):
    names = [n for n in g.ed.list_available_nodes([]) if n.replace(' ', '').endswith('CastTo' + cls_name)]
    assert names, cls_name
    return g.at(g.ed.create_node_from_name(names[0], V2(x, y), []), x, y)


def array_get(g, x, y):
    names = sorted((n for n in g.ed.list_available_nodes([]) if n.replace(' ', '').endswith('|Get(acopy)')), key=len)  # 5.8: 'Get(acopy)'
    assert names, 'no array Get node'
    return g.at(g.ed.create_node_from_name(names[0], V2(x, y), []), x, y)


# ---- ShowTask(Index, Row): label and tick state of one row
f = Graph(P_, 'ShowTask'); e = f.at(entry_node(f), 0, 0)
labels = f.get('TaskLabels', 160, 160); ticked = f.get('TaskTicked', 160, 320)
gl = array_get(f, 384, 160); gt = array_get(f, 384, 320)
st = f.call('/Script/UMG.TextBlock:SetText', 640, 0)
dim = f.call(f'{KML}:SelectFloat', 640, 320, A=0.35, B=1.0)
op = f.call('/Script/UMG.Widget:SetRenderOpacity', 896, 0)
f.exec_chain(e, st, op)
f.link(labels, 'TaskLabels', gl, 'Array'); f.link(e, 'Index', gl, 'Dimension 1'); f.link(gl, 'Output', st, 'InText')
f.link(ticked, 'TaskTicked', gt, 'Array'); f.link(e, 'Index', gt, 'Dimension 1'); f.link(gt, 'Output', dim, 'bPickA')
f.link(e, 'Row', st, 'self'); f.link(e, 'Row', op, 'self'); f.link(dim, 'ReturnValue', op, 'InOpacity')
f.comment('Show one task', 'Label from GetPhoneTasks; a ticked task dims to 35%', [e, labels, ticked, gl, gt, st, dim, op],
          C_VISUAL)

# ---- Refresh
f = Graph(P_, 'Refresh'); e = f.at(entry_node(f), 0, 0)
dirg = f.get('Director', 160, 192)
tasks = f.call(BD_C + ':GetPhoneTasks', 224, 192)
sl = f.set('TaskLabels', 512, 0); stk = f.set('TaskTicked', 768, 0)
f.exec_chain(e, sl, stk)
f.link(dirg, 'Director', tasks, 'self'); f.link(tasks, 'Labels', sl, 'TaskLabels'); f.link(tasks, 'Ticked', stk, 'TaskTicked')
prev, rows = stk, [e, dirg, tasks, sl, stk]
for i in range(4):
    row = f.get(f'Txt_Task{i}', 960 + i * 288, 192)
    show = f.call(self_call(P_, 'ShowTask'), 1024 + i * 288, 0, Index=i)
    f.link(prev, 'then', show, 'execute'); f.link(row, f'Txt_Task{i}', show, 'Row')
    prev = show
    rows += [row, show]
f.comment('Task rows', 'Re-read the four tasks from the director', rows, C_DATA)

gi = f.call(f'{GS}:GetGameInstance', 2240, 192)
gic = cast_node(f, 'GI_FoA', 2304, 0)
day = f.get('DayCount', 2560, 192, class_path=GI_C)
day_t = f.call(f'{KTL}:Conv_IntToText', 2752, 192)
dnum = f.get('Txt_DayNum', 2752, 288)
sd = f.call('/Script/UMG.TextBlock:SetText', 2944, 0)
crossed = f.call(f'{KML}:Subtract_IntInt', 2944, 288, B=1)
cr_t = f.call(f'{KTL}:Conv_IntToText', 3136, 288)
cnum = f.get('Txt_Crossed', 3136, 384)
sc = f.call('/Script/UMG.TextBlock:SetText', 3328, 0)
f.link(prev, 'then', gic, 'execute'); f.link(gi, 'ReturnValue', gic, 'Object')
f.exec_chain(gic, sd, sc)
f.link(gic, 'AsGI_FoA', day, 'self'); f.link(day, 'DayCount', day_t, 'Value'); f.link(day_t, 'ReturnValue', sd, 'InText')
f.link(dnum, 'Txt_DayNum', sd, 'self')
f.link(day, 'DayCount', crossed, 'A'); f.link(crossed, 'ReturnValue', cr_t, 'Value'); f.link(cr_t, 'ReturnValue', sc, 'InText')
f.link(cnum, 'Txt_Crossed', sc, 'self')
f.comment('Day and crossed days', 'GI_FoA.DayCount; crossed-out days are DayCount minus 1',
          [gi, gic, day, day_t, dnum, sd, crossed, cr_t, cnum, sc], C_DATA)

ticked0 = f.get('TaskTicked', 3520, 192)
g0 = array_get(f, 3712, 192); f.default(g0, 'Dimension 1', 0)
br = f.branch(3712, 0)
btn = f.get('Btn_Action', 3968, 288)
away = f.call(BTN_C + ':SetLabel', 3968, -128, NewLabel='Put the phone away')
wake = f.call(BTN_C + ':SetLabel', 3968, 96, NewLabel='Wake up')
awake=f.get('bWakeDone',3300,500,BD_C);portable=f.call(KML+':BooleanOR',3520,500)
f.link(dirg,'Director',awake,'self');f.link(awake,'bWakeDone',portable,'B');f.link(g0,'Output',portable,'A')
f.link(sc, 'then', br, 'execute'); f.link(ticked0, 'TaskTicked', g0, 'Array'); f.link(portable, 'ReturnValue', br, 'Condition')
f.link(br, 'True', away, 'execute'); f.link(br, 'False', wake, 'execute')
f.link(btn, 'Btn_Action', away, 'self'); f.link(btn, 'Btn_Action', wake, 'self')
f.comment('Action label', 'Wake up until that task is ticked, then Put the phone away', [ticked0, g0, br, btn, away, wake],
          C_LOGIC)

# ---- Event graph
g = Graph(P_).clear()
con = g.event('Construct', 0, 0)
find, cast, seth = host_lookup(g, FE_C, 224, 0)
g.link(con, 'then', find, 'execute')
fd = g.call(f'{GS}:GetActorOfClass', 1152, 160, ActorClass=BD_C)
dcast = cast_node(g, 'BP_BeatDirector', 1504, 0)
setd = g.set('Director', 1856, 0)
g.exec_chain(seth, fd, dcast, setd); g.link(fd, 'ReturnValue', dcast, 'Object')
g.link(dcast, 'AsBP_BeatDirector', setd, 'Director')
bind, mk = bind_function(g, setd, 'Director', 'OnPhoneChanged', 'Refresh', 2176, 0)
g.link(setd, 'then', bind, 'execute')
ref = g.call(self_call(P_, 'Refresh'), 2560, 0)
g.link(bind, 'then', ref, 'execute')
btn = g.get('Btn_Action', 2816, 192)
bact, ev = bind_event(g, btn, 'Btn_Action', 'OnSandClicked', 'HandleAction', 2880, 0)
g.link(ref, 'then', bact, 'execute')
focus = g.call(BTN_C + ':FocusButton', 3264, 0)
g.link(bact, 'then', focus, 'execute'); g.link(btn, 'Btn_Action', focus, 'self')
g.comment('Find the director', 'Front end and director lookups; the phone re-reads on OnPhoneChanged',
          [con, find, cast, seth, fd, dcast, setd, bind, mk, ref, btn, bact, focus], C_EVENT)

g.at(ev, 0, 512)
do = g.call(self_call(P_, 'DoAction'), 288, 512)
g.link(ev, 'then', do, 'execute')
g.comment('Screen button', 'A click or the phone keys run DoAction', [ev, do], C_EVENT)

# ---- DoAction (BP_Phone calls it for the keys too): Wake up reports PhoneWakeUp; then the phone closes
f = Graph(P_, 'DoAction'); e = f.at(entry_node(f), 0, 0)
ticked0 = f.get('TaskTicked', 160, 160)
g0 = array_get(f, 352, 160); f.default(g0, 'Dimension 1', 0)
br = f.branch(320, 0)
dget = f.get('Director', 576, 224)
rep_ = f.call(BD_C + ':ReportEvent', 640, 64, Event='PhoneWakeUp')
host = f.get('Host', 896, 160)
close = f.call(FE_C + ':ClosePhone', 960, 0)
f.link(e, 'then', br, 'execute'); f.link(ticked0, 'TaskTicked', g0, 'Array'); f.link(g0, 'Output', br, 'Condition')
f.link(br, 'False', rep_, 'execute'); f.link(dget, 'Director', rep_, 'self')
f.link(rep_, 'then', close, 'execute'); f.link(br, 'True', close, 'execute'); f.link(host, 'Host', close, 'self')
f.comment('Phone action', 'Wake up reports PhoneWakeUp; then the phone closes', [e, ticked0, g0, br, dget, rep_, host, close],
          C_LOGIC)
compile_save(P_, defaults={'bIsFocusable': True})

# The baseline Refresh graph replaces its tails; reconnect the existing notebook after it.
_feedback_tree = f'{P_}.WBP_Phone:WidgetTree'
if unreal.find_object(None, f'{_feedback_tree}.Txt_Notebook'):
    from pathlib import Path as _FeedbackPath
    import os as _feedback_os
    import runpy as _feedback_runpy
    _feedback_phase = _feedback_os.environ.get('FOA_PHASE')
    try:
        _feedback_os.environ['FOA_PHASE'] = 'body'
        _feedback_runpy.run_path(str(_FeedbackPath(__file__).with_name('wire_phone_feedback.py')), run_name='__main__')
    finally:
        if _feedback_phase is None:
            _feedback_os.environ.pop('FOA_PHASE', None)
        else:
            _feedback_os.environ['FOA_PHASE'] = _feedback_phase
else:
    print('Phone notebook skipped: Txt_Notebook must exist in the designer first')
