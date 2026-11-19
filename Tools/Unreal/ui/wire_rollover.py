"""WBP_DayRollover graph (run via ue_remote.py after rollover_calls.py built the tree). No Tick: Play starts a 30 Hz
timer (Step) that drives everything from Elapsed.
  Play(NewDay, Learned)  texts ("Day N" struck through as N - 1), the Learned line collapsed when empty, the wipe MID
  Step                   Cover = Elapsed / WipeSeconds; after the wipe: card in, strike draws, new day, then the line
  Ramp(Start, Dur)       pure: saturate((Elapsed - WipeSeconds - Start) / Dur), one ramp per beat after the wipe
The front end owns the timing contract (OnRolloverCovered at WipeSeconds, hard cut <= 2.5 s later)."""
exec(open('P:/FoA/Tools/Unreal/ui/bp_graph.py').read())
import unreal

BP = '/Game/FoA/UI/Game/WBP_DayRollover'
KML = '/Script/Engine.KismetMathLibrary'
KSTR = '/Script/Engine.KismetStringLibrary'
KTXT = '/Script/Engine.KismetTextLibrary'
R = ptype('real')
ensure_vars(BP, [('Elapsed', R, '0.0', 'Rollover|State', False),
                 ('WipeMID', ptype(unreal.MaterialInstanceDynamic), '', 'Rollover|State', False),
                 ('WipeSeconds', R, '1.4', 'Rollover', True)])
Graph.function(BP, 'RolloverRamp', pure=True, inputs=[('Start', R), ('Dur', R)], outputs=[('Alpha', R)])
Graph.function(BP, 'PlayRollover', inputs=[('NewDay', ptype('int')), ('Learned', ptype('text'))])
Graph.function(BP, 'StepRollover')

# ---- Ramp
f = Graph(BP, 'RolloverRamp'); e = f.at(entry_node(f), 0, 0)
ret = f.at(f.ed.list_nodes_of_class(unreal.K2Node_FunctionResult)[0], 1024, 0)
el = f.get('Elapsed', 0, 160); ws = f.get('WipeSeconds', 0, 240)
s1 = f.call(f'{KML}:Subtract_DoubleDouble', 224, 160); s2 = f.call(f'{KML}:Subtract_DoubleDouble', 448, 160)
dv = f.call(f'{KML}:Divide_DoubleDouble', 640, 160); cl = f.call(f'{KML}:FClamp', 832, 160, Min=0.0, Max=1.0)
f.link(e, 'then', ret, 'execute')
f.link(el, 'Elapsed', s1, 'A'); f.link(ws, 'WipeSeconds', s1, 'B'); f.link(s1, 'ReturnValue', s2, 'A')
f.link(e, 'Start', s2, 'B'); f.link(s2, 'ReturnValue', dv, 'A'); f.link(e, 'Dur', dv, 'B')
f.link(dv, 'ReturnValue', cl, 'Value'); f.link(cl, 'ReturnValue', ret, 'Alpha')
f.comment('Beat ramp', 'saturate((Elapsed - WipeSeconds - Start) / Dur)', [e, ret, el, ws, s1, s2, dv, cl], C_LOGIC)

# ---- Play
f = Graph(BP, 'PlayRollover'); e = f.at(entry_node(f), 0, 0)
nodes = [e]


def day_text(x, y, minus):
    """'Day ' + NewDay (- minus) as Text."""
    n = [e]
    src = ('NewDay', e)
    if minus:
        sub = f.call(f'{KML}:Subtract_IntInt', x, y + 160, B=1)
        f.link(e, 'NewDay', sub, 'A')
        src = ('ReturnValue', sub)
        n.append(sub)
    its = f.call(f'{KSTR}:Conv_IntToString', x + 192, y + 160)
    cat = f.call(f'{KSTR}:Concat_StrStr', x + 384, y + 160, A='Day ')
    txt = f.call(f'{KTXT}:Conv_StringToText', x + 576, y + 160)
    f.link(src[1], src[0], its, 'InInt'); f.link(its, 'ReturnValue', cat, 'B'); f.link(cat, 'ReturnValue', txt, 'InString')
    return txt, n[1:] + [its, cat, txt]


tn = f.get('Txt_New', 704, 96); setn = f.call('/Script/UMG.TextBlock:SetText', 768, 0)
dn, dnn = day_text(0, 0, False)
to = f.get('Txt_Old', 1216, 96); seto = f.call('/Script/UMG.TextBlock:SetText', 1280, 0)
do, don = day_text(512, 160, True)
tl = f.get('Txt_Learned', 1728, 96); setl = f.call('/Script/UMG.TextBlock:SetText', 1792, 0)
empty = f.call(f'{KTXT}:TextIsEmpty', 1984, 160); br = f.branch(2048, 0)
tl2 = f.get('Txt_Learned', 2240, 160); hide = f.call('/Script/UMG.Widget:SetVisibility', 2304, -96, InVisibility='Collapsed')
img = f.get('Img_Wipe', 2560, 160); mid = f.call('/Script/UMG.Image:GetDynamicMaterial', 2624, 160)
setm = f.set('WipeMID', 2880, 0)
sete = f.set('Elapsed', 3136, 0); f.default(sete, 'Elapsed', '0.0')
step = f.call(self_call(BP, 'StepRollover'), 3392, 0)
tmr = f.call('/Script/Engine.KismetSystemLibrary:K2_SetTimer', 3648, 0, FunctionName='StepRollover', Time=0.0333, bLooping='true')
f.exec_chain(e, setn, seto, setl, br)
f.link(br, 'True', hide, 'execute')
f.link(hide, 'then', mid, 'execute'); f.link(br, 'False', mid, 'execute')  # GetDynamicMaterial is impure: on the exec path
f.exec_chain(mid, setm, sete, step, tmr)
f.link(tn, 'Txt_New', setn, 'self'); f.link(dn, 'ReturnValue', setn, 'InText')
f.link(to, 'Txt_Old', seto, 'self'); f.link(do, 'ReturnValue', seto, 'InText')
f.link(tl, 'Txt_Learned', setl, 'self'); f.link(e, 'Learned', setl, 'InText')
f.link(e, 'Learned', empty, 'InText'); f.link(empty, 'ReturnValue', br, 'Condition'); f.link(tl2, 'Txt_Learned', hide, 'self')
f.link(img, 'Img_Wipe', mid, 'self'); f.link(mid, 'ReturnValue', setm, 'WipeMID')
f.comment('Day texts', 'Day N large, Day N - 1 struck through, the learned line only when there is one',
          [e, tn, setn, to, seto, tl, setl, empty, br, tl2, hide] + dnn + don, C_VISUAL)
f.comment('Start the wipe', 'Dynamic wipe material, clock at zero, first frame now, then 30 Hz',
          [img, mid, setm, sete, step, tmr], C_LOGIC)

# ---- Step
f = Graph(BP, 'StepRollover'); e = f.at(entry_node(f), 0, 0)
el = f.get('Elapsed', 160, 160); add = f.call(f'{KML}:Add_DoubleDouble', 224, 160, B=0.0333)
sete = f.set('Elapsed', 448, 0)
ws = f.get('WipeSeconds', 640, 224); cov = f.call(f'{KML}:Divide_DoubleDouble', 704, 160)
clc = f.call(f'{KML}:FClamp', 896, 160, Min=0.0, Max=1.0)
mid = f.get('WipeMID', 896, 288)
setc = f.call('/Script/Engine.MaterialInstanceDynamic:SetScalarParameterValue', 1152, 0, ParameterName='Cover')
f.exec_chain(e, sete, setc)
f.link(el, 'Elapsed', add, 'A'); f.link(add, 'ReturnValue', sete, 'Elapsed')
f.link(sete, 'Elapsed', cov, 'A'); f.link(ws, 'WipeSeconds', cov, 'B'); f.link(cov, 'ReturnValue', clc, 'Value')
f.link(clc, 'ReturnValue', setc, 'Value'); f.link(mid, 'WipeMID', setc, 'self')
f.comment('Sand covers', 'Elapsed += 1/30; Cover = Elapsed / WipeSeconds into the wipe material',
          [e, el, add, sete, ws, cov, clc, mid, setc], C_VISUAL)
prev, beats, x = setc, [], 1600
for var, start, dur, kind in (('VB_Card', 0.05, 0.35, 'opacity'), ('Img_Strike', 0.35, 0.3, 'scale'),
                              ('Txt_New', 0.45, 0.35, 'opacity'), ('Txt_Learned', 0.8, 0.45, 'opacity')):
    w = f.get(var, x, 224)
    ramp = f.call(self_call(BP, 'RolloverRamp'), x, 304, Start=start, Dur=dur)
    if kind == 'opacity':
        s = f.call('/Script/UMG.Widget:SetRenderOpacity', x + 128, 0)
        f.link(ramp, 'Alpha', s, 'InOpacity'); extra = []
    else:
        mk = f.call(f'{KML}:MakeVector2D', x + 96, 400, Y=1.0)
        s = f.call('/Script/UMG.Widget:SetRenderScale', x + 128, 0)
        f.link(ramp, 'Alpha', mk, 'X'); f.link(mk, 'ReturnValue', s, 'Scale'); extra = [mk]
    f.link(w, var, s, 'self'); f.link(prev, 'then', s, 'execute')
    beats += [w, ramp, s] + extra
    prev, x = s, x + 448
f.comment('Card after the wipe', 'Card, then the strike draws across the old day, the new day, the learned line',
          beats, C_VISUAL)
compile_save(BP)
