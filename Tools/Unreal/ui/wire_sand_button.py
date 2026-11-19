"""WBP_SandButton graph (run via ue_remote.py). Event-driven: no Tick, no timers.
  ApplyLook   PreConstruct: label text + the sand-letter material on Ret_Sand (designers see it in parent widgets)
  PushState   one SetVectorParameterValue(State) + the word's opacity, called only when hover/press/focus changes
  SetHovered  mouse hover and keyboard/gamepad focus share one path (moodboard: "gamepad focus must look like hover")
  SetPressed  pressed state into the material
The words are sand letters: Ret_Sand (RetainerBox) renders Txt_Label once and M_UI_SandText animates grains, rim
erosion, peel and the echo from its own Time node, so nothing ticks here.
Clicks fire immediately (OnSandClicked)."""
exec(open('P:/FoA/Tools/Unreal/ui/bp_graph.py').read())
import unreal

BP = '/Game/FoA/UI/Widgets/Common/WBP_SandButton'
KML = '/Script/Engine.KismetMathLibrary'
bp = unreal.load_asset(BP)
T_BOOL, T_TEXT = ptype('bool'), ptype('text')

ensure_vars(BP, [
    ('Label', T_TEXT, 'Wake Up', 'Sand Button', True, True),
    ('SandMaterial', ptype(unreal.MaterialInterface),
     '/Game/FoA/UI/Materials/MI_UI_SandText_Menu.MI_UI_SandText_Menu', 'Sand Button', True),
    ('HoverSound', ptype(unreal.SoundBase), '', 'Sand Button|Audio', True),
    ('ClickSound', ptype(unreal.SoundBase), '', 'Sand Button|Audio', True),
    ('TextAlphaRest', ptype('real'), '0.62', 'Sand Button|Style', True),
    ('TextAlphaHover', ptype('real'), '1.0', 'Sand Button|Style', True),
    ('TextAlphaDisabled', ptype('real'), '0.25', 'Sand Button|Style', True),
    ('bHovered', T_BOOL, 'false', 'Sand Button|State', False),
    ('bPressed', T_BOOL, 'false', 'Sand Button|State', False),
    ('SandMID', ptype(unreal.MaterialInstanceDynamic), '', 'Sand Button|State', False),
])
for stale in ('HoverAlpha', 'PressPhase', 'FlowPhase', 'TextRest', 'TextHover', 'TextDisabled'):   # tick-era state, superseded by the material's Time node
    if stale in [str(n) for n in BEL.list_member_variable_names(bp)]:
        GE.get_graph_editor_by_name(bp, 'EventGraph').remove_member_variable(stale)
if 'OnSandClicked' not in [str(n) for n in BEL.list_event_dispatchers(bp)]:
    BEL.add_event_dispatcher(bp, 'OnSandClicked')
for f in ('ApplyLook', 'PushState', 'SetHovered', 'SetPressed', 'SetLabel', 'FocusButton', 'UpdateSand'):
    drop_function(BP, f)
Graph.function(BP, 'ApplyLook'); Graph.function(BP, 'PushState'); Graph.function(BP, 'FocusButton')
Graph.function(BP, 'SetHovered', inputs=[('bNewHovered', T_BOOL)])
Graph.function(BP, 'SetPressed', inputs=[('bNewPressed', T_BOOL)])
Graph.function(BP, 'SetLabel', inputs=[('NewLabel', T_TEXT)])
Graph.function(BP, 'SetReveal', inputs=[('Alpha', ptype('real'))])

# ---- ApplyLook: label + variant material
f = Graph(BP, 'ApplyLook'); e = f.at(entry_node(f), 0, 0)
txt = f.get('Txt_Label', 224, 160); lbl = f.get('Label', 224, 240)
set_text = f.call('/Script/UMG.TextBlock:SetText', 288, 0)
ret = f.get('Ret_Sand', 544, 160); mat = f.get('SandMaterial', 544, 240)
set_fx = f.call('/Script/UMG.RetainerBox:SetEffectMaterial', 608, 0)
f.exec_chain(e, set_text, set_fx)
f.link(txt, 'Txt_Label', set_text, 'self'); f.link(lbl, 'Label', set_text, 'InText')
f.link(ret, 'Ret_Sand', set_fx, 'self'); f.link(mat, 'SandMaterial', set_fx, 'EffectMaterial')
f.comment('Apply look', 'Label text, and the sand-letter material on the retainer that draws it',
          [e, txt, lbl, set_text, ret, mat, set_fx], C_VISUAL)

# ---- PushState: (Hover, Press, Disabled, 0) in one vector; label colour from the same state
f = Graph(BP, 'PushState'); e = f.at(entry_node(f), 0, 0)
hov = f.get('bHovered', 160, 224); prs = f.get('bPressed', 160, 320)
hov_f = f.call(f'{KML}:Conv_BoolToDouble', 352, 224)
prs_f = f.call(f'{KML}:SelectFloat', 352, 320, A=0.5, B=0.0)       # pressed holds the dissolve at its peak
enabled = f.call('/Script/UMG.Widget:GetIsEnabled', 352, 448)
dis = f.call(f'{KML}:Not_PreBool', 608, 448)
dis_f = f.call(f'{KML}:Conv_BoolToDouble', 800, 448)
mk = f.call(f'{KML}:MakeColor', 800, 224, A=0.0)
mid = f.get('SandMID', 960, 128)
setp = f.call('/Script/Engine.MaterialInstanceDynamic:SetVectorParameterValue', 1056, 0, ParameterName='State')
rest = f.get('TextAlphaRest', 1056, 384); hot = f.get('TextAlphaHover', 1056, 464)
off = f.get('TextAlphaDisabled', 1312, 544)
pick = f.call(f'{KML}:SelectFloat', 1312, 384)
pick2 = f.call(f'{KML}:SelectFloat', 1568, 384)
ret = f.get('Txt_Label', 1568, 224)  # dim the word inside the retainer: a RetainerBox below render opacity 1 all but erases its effect
setc = f.call('/Script/UMG.Widget:SetRenderOpacity', 1824, 0)
mok = f.call('/Script/Engine.KismetSystemLibrary:IsValid', 864, 288)
mbr = f.branch(864, 0)  # the plain-word fallback has no effect material, so no SandMID: skip the material, keep the opacity
f.exec_chain(e, mbr); f.link(mbr, 'True', setp, 'execute'); f.link(setp, 'then', setc, 'execute')
f.link(mbr, 'False', setc, 'execute'); f.link(mid, 'SandMID', mok, 'Object'); f.link(mok, 'ReturnValue', mbr, 'Condition')
f.link(hov, 'bHovered', hov_f, 'InBool'); f.link(prs, 'bPressed', prs_f, 'bPickA')
f.link(enabled, 'ReturnValue', dis, 'A'); f.link(dis, 'ReturnValue', dis_f, 'InBool')
f.link(hov_f, 'ReturnValue', mk, 'R'); f.link(prs_f, 'ReturnValue', mk, 'G'); f.link(dis_f, 'ReturnValue', mk, 'B')
f.link(mid, 'SandMID', setp, 'self'); f.link(mk, 'ReturnValue', setp, 'Value')
f.link(hot, 'TextAlphaHover', pick, 'A'); f.link(rest, 'TextAlphaRest', pick, 'B'); f.link(hov, 'bHovered', pick, 'bPickA')
f.link(pick, 'ReturnValue', pick2, 'A'); f.link(off, 'TextAlphaDisabled', pick2, 'B')
f.link(enabled, 'ReturnValue', pick2, 'bPickA')
f.link(ret, 'Txt_Label', setc, 'self'); f.link(pick2, 'ReturnValue', setc, 'InOpacity')
# the selection grains (M_UI_SandVortex on Img_Vortex) show only while hovered or focused (page: the vortex + falling grains)
vtx = f.get('Img_Vortex', 2080, 224)
setv = f.call('/Script/UMG.Widget:SetRenderOpacity', 2080, 0)
f.link(setc, 'then', setv, 'execute'); f.link(vtx, 'Img_Vortex', setv, 'self'); f.link(hov_f, 'ReturnValue', setv, 'InOpacity')
f.comment('Material state', 'Hover, press and disabled packed into State; the grain flows on its own in the material',
          [e, hov, prs, hov_f, prs_f, enabled, dis, dis_f, mk, mid, mok, mbr, setp], C_VISUAL)
f.comment('Word opacity', 'The whole sand word: rest 62%, hover 100%, disabled 25%; grains only when selected',
          [rest, hot, off, pick, pick2, ret, setc, vtx, setv], C_VISUAL)

# ---- SetHovered / SetPressed
f = Graph(BP, 'SetHovered'); e = f.at(entry_node(f), 0, 0)
setv = f.set('bHovered', 256, 0)
br = f.branch(512, 0)
snd = f.call('/Script/Engine.GameplayStatics:PlaySound2D', 768, -96, bIsUISound='true')
hs = f.get('HoverSound', 704, 96)
push = f.call(self_call(BP, 'PushState'), 1088, 64)
f.link(e, 'then', setv, 'execute'); f.link(e, 'bNewHovered', setv, 'bHovered')
f.link(setv, 'then', br, 'execute'); f.link(e, 'bNewHovered', br, 'Condition')
f.link(br, 'True', snd, 'execute'); f.link(hs, 'HoverSound', snd, 'Sound')
f.link(snd, 'then', push, 'execute'); f.link(br, 'False', push, 'execute')
f.comment('Hover / focus', 'One path for mouse hover and gamepad focus; the tick sound only when it starts',
          [e, setv, br, snd, hs, push], C_LOGIC)

f = Graph(BP, 'SetPressed'); e = f.at(entry_node(f), 0, 0)
setv = f.set('bPressed', 256, 0)
push = f.call(self_call(BP, 'PushState'), 512, 0)
f.exec_chain(e, setv, push); f.link(e, 'bNewPressed', setv, 'bPressed')
f.comment('Press state', 'Pressed state into the sand material while the button is down', [e, setv, push], C_LOGIC)

# ---- SetReveal(Alpha): the sand reveal (0 hidden .. 1 shown) for uimotion's Anim_PauseIn (via Motion_PauseIn)
f = Graph(BP, 'SetReveal'); e = f.at(entry_node(f), 0, 0)
mid = f.get('SandMID', 224, 160)
sr = f.call('/Script/Engine.MaterialInstanceDynamic:SetScalarParameterValue', 288, 0, ParameterName='Reveal')
rok = f.call('/Script/Engine.KismetSystemLibrary:IsValid', 160, 240); rbr = f.branch(160, 0)
f.exec_chain(e, rbr); f.link(rbr, 'True', sr, 'execute'); f.link(mid, 'SandMID', rok, 'Object'); f.link(rok, 'ReturnValue', rbr, 'Condition')
f.link(mid, 'SandMID', sr, 'self'); f.link(e, 'Alpha', sr, 'Value')
f.comment('Set the reveal', 'Sand letters appear from the noise as Alpha goes 0 to 1', [e, mid, rok, rbr, sr], C_VISUAL)

# ---- SetLabel / FocusButton (called by screens)
f = Graph(BP, 'SetLabel'); e = f.at(entry_node(f), 0, 0)
setl = f.set('Label', 256, 0)
apply_l = f.call(self_call(BP, 'ApplyLook'), 512, 0)
f.exec_chain(e, setl, apply_l); f.link(e, 'NewLabel', setl, 'Label')
f.comment('Set label', 'Runtime relabel (dialogs reuse one button with different copy)', [e, setl, apply_l], C_LOGIC)

f = Graph(BP, 'FocusButton'); e = f.at(entry_node(f), 0, 0)
hit = f.get('Btn_Hit', 224, 160)
foc = f.call('/Script/UMG.Widget:SetFocus', 288, 0)
f.exec_chain(e, foc); f.link(hit, 'Btn_Hit', foc, 'self')
f.comment('Focus button', 'Screens put keyboard/gamepad focus on their default button', [e, hit, foc], C_LOGIC)

# ---- Event graph
g = Graph(BP).clear()
pre = g.event('PreConstruct', 0, 0)
apply_ = g.call(self_call(BP, 'ApplyLook'), 288, 0)
g.link(pre, 'then', apply_, 'execute')
g.comment('Design time + runtime', "Show this instance's label and variant", [pre, apply_], C_EVENT)

con = g.event('Construct', 0, 256)
ret = g.get('Ret_Sand', 64, 416)
dyn = g.call('/Script/UMG.RetainerBox:GetEffectMaterial', 288, 256)
set_mid = g.set('SandMID', 608, 256)
push0 = g.call(self_call(BP, 'PushState'), 864, 256)
g.exec_chain(con, set_mid, push0)  # GetEffectMaterial is pure
g.link(ret, 'Ret_Sand', dyn, 'self'); g.link(dyn, 'ReturnValue', set_mid, 'SandMID')
hit = g.get('Btn_Hit', 1088, 448)
binds, events, prev = [], [], push0
for i, (disp, ev_name) in enumerate((('OnHovered', 'HandleHovered'), ('OnUnhovered', 'HandleUnhovered'),
                                     ('OnPressed', 'HandlePressed'), ('OnReleased', 'HandleReleased'),
                                     ('OnClicked', 'HandleClicked'))):
    b, ev = bind_event(g, hit, 'Btn_Hit', disp, ev_name, 1216 + i * 384, 256)
    g.link(prev, 'then', b, 'execute')
    prev = b
    binds.append(b); events.append(ev)
g.comment('Cache material + bind input', 'One dynamic instance per button; the inner Button drives every state change',
          [con, ret, dyn, set_mid, push0, hit] + binds, C_EVENT)

X0, X1 = 1216, 1600
rows = (704, 864, 1024, 1184, 1344)
h_in = g.call(self_call(BP, 'SetHovered'), X1, rows[0], bNewHovered='true')
h_out = g.call(self_call(BP, 'SetHovered'), X1, rows[1], bNewHovered='false')
p_in = g.call(self_call(BP, 'SetPressed'), X1, rows[2], bNewPressed='true')
p_out = g.call(self_call(BP, 'SetPressed'), X1, rows[3], bNewPressed='false')
snd = g.call('/Script/Engine.GameplayStatics:PlaySound2D', X1, rows[4], bIsUISound='true')
cs = g.get('ClickSound', X1 - 64, rows[4] + 160)
names = [n for n in g.ed.list_available_nodes([]) if n.replace(' ', '').endswith('CallOnSandClicked')]
call = g.at(g.ed.create_node_from_name(names[0], V2(X1 + 384, rows[4]), []), X1 + 384, rows[4])
for ev, row, tgt in zip(events, rows, (h_in, h_out, p_in, p_out, snd)):
    g.at(ev, X0, row)
    g.link(ev, 'then', tgt, 'execute')
g.link(cs, 'ClickSound', snd, 'Sound'); g.link(snd, 'then', call, 'execute')
g.comment('Hover, press, click', 'Click fires at once through OnSandClicked; visuals only follow state',
          events + [h_in, h_out, p_in, p_out, snd, cs, call], C_LOGIC)

foc_in = g.event('OnAddedToFocusPath', 0, 1600)
foc_out = g.event('OnRemovedFromFocusPath', 0, 1760)
f_in = g.call(self_call(BP, 'SetHovered'), 384, 1600, bNewHovered='true')
f_out = g.call(self_call(BP, 'SetHovered'), 384, 1760, bNewHovered='false')
g.link(foc_in, 'then', f_in, 'execute'); g.link(foc_out, 'then', f_out, 'execute')
g.comment('Gamepad focus = hover', 'Focus path events reuse SetHovered', [foc_in, foc_out, f_in, f_out], C_EVENT)
SFX = '/Game/FoA/Audio/SFX/UI_FrontEnd'
import os
# FOA_WORDS=plain: the fallback (plain Darker Grotesque words, no retainer effect) until the sand effect draws bright
DEFAULTS = {'SandMaterial': '' if os.environ.get('FOA_WORDS') == 'plain'
            else '/Game/FoA/UI/Materials/MI_UI_SandText_Menu.MI_UI_SandText_Menu'}
DEFAULTS.update({slot: f'{SFX}/{cue}.{cue}' for slot, cue in (('HoverSound', 'SFX_FE_Hover'), ('ClickSound', 'SFX_FE_Select'))
                 if unreal.EditorAssetLibrary.does_asset_exist(f'{SFX}/{cue}')})
# Instances override ClickSound: Wake up has none (the front end plays SFX_FE_WakeUpPress), the dialog's Confirm has none
# (SFX_FE_Confirm plays on accept), and its cancel button uses SFX_FE_Back (Hayba ui_set_widget_properties).
from pathlib import Path as _ButtonPath
import runpy as _ButtonRun
_ButtonRun.run_path(str(_ButtonPath(__file__).with_name('patch_readable_button.py')))
if unreal.find_object(None,BP+'.WBP_SandButton:WidgetTree.Img_CommandFocus'):
    _ButtonRun.run_path(str(_ButtonPath(__file__).with_name('patch_command_focus.py')))
compile_save(BP, defaults=DEFAULTS)
