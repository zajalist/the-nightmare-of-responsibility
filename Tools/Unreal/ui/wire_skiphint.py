"""WBP_SkipHint (for the wake-up lane's BP_WakeUpCinematic): one function, SetHoldProgress(Alpha 0..1).
The hint brightens as the skip key is held (opacity 0.55 -> 1); no bars or lines. Run via ue_remote.py."""
exec(open('P:/FoA/Tools/Unreal/ui/bp_graph.py').read())

P_ = '/Game/FoA/UI/Game/WBP_SkipHint'
f = Graph.function(P_, 'SetHoldProgress', inputs=[('Alpha', ptype('real'))])
e = f.at(entry_node(f), 0, 0)
lerp = f.call('/Script/Engine.KismetMathLibrary:Lerp', 224, 160, A=0.55, B=1.0)
txt = f.get('Txt_Hint', 480, 160)
op = f.call('/Script/UMG.Widget:SetRenderOpacity', 544, 0)
f.exec_chain(e, op)
f.link(e, 'Alpha', lerp, 'Alpha'); f.link(lerp, 'ReturnValue', op, 'InOpacity'); f.link(txt, 'Txt_Hint', op, 'self')
f.comment('Hold progress', 'The hint brightens from 55% to full while the skip key is held', [e, lerp, txt, op], C_VISUAL)
compile_save(P_)
