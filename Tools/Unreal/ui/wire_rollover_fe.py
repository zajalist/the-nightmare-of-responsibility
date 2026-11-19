"""BP_FoAFrontEnd side of the P13 day rollover (docs/mechanics/contract.md, "Day rollover"). Run via ue_remote.py
after WBP_DayRollover compiles (wire_rollover.py). Idempotent: functions are reused and cleared, never deleted.
  PlayDayRollover(NewDay, Learned)  the card over everything (Z 40), Play, then RolloverCovered at WipeSeconds
  RolloverCovered (timer)           broadcast OnRolloverCovered once (the screen is opaque black), arm the cut
  EndRollover (timer)               hard cut: the card leaves the viewport, no fade (inside LS_WakeUp's 3 s black)
Input mode and pause are left alone (the director froze input). RolloverHoldSeconds 2.4 keeps the cut under 2.5 s."""
exec(open('P:/FoA/Tools/Unreal/ui/bp_graph.py').read())
import unreal

PATH = '/Game/FoA/UI/Framework/BP_FoAFrontEnd'
ROLL_C = '/Game/FoA/UI/Game/WBP_DayRollover.WBP_DayRollover_C'
KSL = '/Script/Engine.KismetSystemLibrary'
R = ptype('real')
assert unreal.load_class(None, ROLL_C), 'compile WBP_DayRollover first (wire_rollover.py)'
bp = unreal.load_asset(PATH)
ensure_vars(PATH, [('Rollover', ptype(unreal.UserWidget), '', 'Front End|State', False),
                   ('RolloverWipeSeconds', R, '1.4', 'Front End|Rollover', True),
                   ('RolloverHoldSeconds', R, '2.4', 'Front End|Rollover', True)])
if 'OnRolloverCovered' not in [str(n) for n in BEL.list_event_dispatchers(bp)]:
    BEL.add_event_dispatcher(bp, 'OnRolloverCovered')
Graph.function(PATH, 'PlayDayRollover', inputs=[('NewDay', ptype('int')), ('Learned', ptype('text'))])
Graph.function(PATH, 'RolloverCovered')
Graph.function(PATH, 'EndRollover')
SELF = lambda f: self_call(PATH, f)  # noqa: E731

# ---- PlayDayRollover
g = Graph(PATH, 'PlayDayRollover'); e = g.at(entry_node(g), 0, 0)
cw = g.node('UserInterface|CreateWidget', 256, 0)
assert PIN.set_pin_value(g.pin(cw, 'Class', 'in'), ROLL_C)
pc = g.get('PC', 192, 192)
names = [n for n in g.ed.list_available_nodes([]) if n.replace(' ', '').endswith('CastToWBP_DayRollover')]
cast = g.at(g.ed.create_node_from_name(names[0], V2(576, 0), []), 576, 0)
setv = g.set('Rollover', 896, 0)
add = g.call('/Script/UMG.UserWidget:AddToViewport', 1152, 0, ZOrder=40)
play = g.call(ROLL_C + ':PlayRollover', 1408, 0)
ws = g.get('RolloverWipeSeconds', 1600, 192)
tmr = g.call(f'{KSL}:K2_SetTimer', 1664, 0, FunctionName='RolloverCovered')
g.exec_chain(e, cw); g.link(cw, 'then', cast, 'execute'); g.link(cast, 'then', setv, 'execute')
g.exec_chain(setv, add, play, tmr)
g.link(pc, 'PC', cw, 'OwningPlayer'); g.link(cw, 'ReturnValue', cast, 'Object')
g.link(cast, 'AsWBP_DayRollover', setv, 'Rollover'); g.link(setv, 'Rollover', add, 'self')
g.link(cast, 'AsWBP_DayRollover', play, 'self'); g.link(e, 'NewDay', play, 'NewDay'); g.link(e, 'Learned', play, 'Learned')
g.link(ws, 'RolloverWipeSeconds', tmr, 'Time')
g.comment('Play day rollover', 'Card over everything, wipe starts; the covered broadcast fires when the sand is opaque',
          [e, cw, pc, cast, setv, add, play, ws, tmr], C_EVENT)

# ---- RolloverCovered (timer)
g = Graph(PATH, 'RolloverCovered'); e = g.at(entry_node(g), 0, 0)
calls = [n for n in g.ed.list_available_nodes([]) if n.replace(' ', '').endswith('CallOnRolloverCovered')]
assert calls, 'no Call OnRolloverCovered node (compile the dispatcher first)'
bc = g.at(g.ed.create_node_from_name(calls[0], V2(256, 0), []), 256, 0)
hud = g.get('HUD', 448, 192); hok = g.call(f'{KSL}:IsValid', 512, 256); hbr = g.branch(576, 0)
hid = g.call('/Script/UMG.Widget:SetRenderOpacity', 832, -96, InOpacity=0.0)  # as FinishWake: T0's OnBeatChanged fades it back
hs = g.get('RolloverHoldSeconds', 1088, 192)
tmr = g.call(f'{KSL}:K2_SetTimer', 1152, 0, FunctionName='EndRollover')
g.exec_chain(e, bc, hbr); g.link(hbr, 'True', hid, 'execute'); g.link(hid, 'then', tmr, 'execute'); g.link(hbr, 'False', tmr, 'execute')
g.link(hud, 'HUD', hok, 'Object'); g.link(hok, 'ReturnValue', hbr, 'Condition'); g.link(hud, 'HUD', hid, 'self')
g.link(hs, 'RolloverHoldSeconds', tmr, 'Time')
g.comment('Rollover covered', 'Screen is opaque black: the HUD hides for the wake-up, the director resets, the cut follows',
          [e, bc, hud, hok, hbr, hid, hs, tmr], C_EVENT)

# ---- EndRollover (timer): hard cut
g = Graph(PATH, 'EndRollover'); e = g.at(entry_node(g), 0, 0)
get = g.get('Rollover', 160, 160); ok = g.call(f'{KSL}:IsValid', 224, 224); br = g.branch(320, 0)
rm = g.call('/Script/UMG.Widget:RemoveFromParent', 576, -96)
clr = g.set('Rollover', 864, 0)
g.exec_chain(e, br); g.link(get, 'Rollover', ok, 'Object'); g.link(ok, 'ReturnValue', br, 'Condition')
g.link(br, 'True', rm, 'execute'); g.link(get, 'Rollover', rm, 'self')
g.link(rm, 'then', clr, 'execute'); g.link(br, 'False', clr, 'execute')
g.comment('Hard cut', 'No fade: the card leaves inside the wake-up black', [e, get, ok, br, rm, clr], C_LOGIC)
compile_save(PATH)
