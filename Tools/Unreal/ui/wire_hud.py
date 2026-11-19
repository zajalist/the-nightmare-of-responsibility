"""WBP_HUD graph (run via ue_remote.py). Event-driven: the HUD only changes when gameplay says so.
  OnBeatChanged(Beat, Objective, ShowPhone)  (BP_BeatDirector, contract) -> HandleBeatChanged -> objective line
Prompt (BPC_Interactor.OnFocusChanged), toast (BPC_Inventory.OnInventoryChanged) and subtitles (OnNarration) bind
here too once their widgets exist in the tree."""
exec(open('P:/FoA/Tools/Unreal/ui/bp_graph.py').read())
import unreal

P_ = '/Game/FoA/UI/Game/WBP_HUD'
BD_C = '/Game/FoA/Gameplay/BP_BeatDirector.BP_BeatDirector_C'
GS = '/Script/Engine.GameplayStatics'

drop_function(P_, 'HandleBeatChanged')
f = Graph.function(P_, 'HandleBeatChanged', inputs=[('Beat', ptype('name')), ('Objective', ptype('text')),
                                                     ('ShowPhone', ptype('bool'))])
e = f.at(entry_node(f), 0, 0)
txt = f.get('Txt_Objective', 224, 160)
st = f.call('/Script/UMG.TextBlock:SetText', 288, 0)
f.exec_chain(e, st)
f.link(txt, 'Txt_Objective', st, 'self'); f.link(e, 'Objective', st, 'InText')
obj_nodes = [e, txt, st]

# FadeInStep: 30 Hz timer while fading in (after the wake-up cinematic hands over); clears itself at full opacity
KML = '/Script/Engine.KismetMathLibrary'
drop_function(P_, 'FadeInStep')
f = Graph.function(P_, 'FadeInStep')
e = f.at(entry_node(f), 0, 0)
cur = f.call('/Script/UMG.Widget:GetRenderOpacity', 160, 160)
add = f.call(f'{KML}:Add_DoubleDouble', 416, 160, B=0.042)            # about 0.8 s from 0 to 1
cl = f.call(f'{KML}:FClamp', 672, 160, Min=0.0, Max=1.0)
seto = f.call('/Script/UMG.Widget:SetRenderOpacity', 928, 0)
done = f.call(f'{KML}:GreaterEqual_DoubleDouble', 928, 224, B=1.0)
br = f.branch(1184, 0)
stop = f.call('/Script/Engine.KismetSystemLibrary:K2_ClearTimer', 1440, -96, FunctionName='FadeInStep')
f.exec_chain(e, seto, br)
f.link(cur, 'ReturnValue', add, 'A'); f.link(add, 'ReturnValue', cl, 'Value'); f.link(cl, 'ReturnValue', seto, 'InOpacity')
f.link(cl, 'ReturnValue', done, 'A'); f.link(done, 'ReturnValue', br, 'Condition'); f.link(br, 'True', stop, 'execute')
f.comment('Fade in', 'Steps render opacity to 1 and stops its own timer (no Tick)', [e, cur, add, cl, seto, done, br, stop],
          C_VISUAL)

# HandleBeatChanged also starts the fade (harmless when already visible: the first step clamps to 1 and stops)
f = Graph(P_, 'HandleBeatChanged')
st_nodes = [n for n in f.ed.list_all_nodes() if n.get_class().get_name() == 'K2Node_CallFunction']
tmr = f.call('/Script/Engine.KismetSystemLibrary:K2_SetTimer', 576, 0, FunctionName='FadeInStep', Time=0.033,
             bLooping='true')
f.link(st_nodes[0], 'then', tmr, 'execute')
f.comment('Objective line', "Shows the beat director's objective and fades the HUD in", obj_nodes + [tmr], C_VISUAL)
# ShowPhone (T0, T10): the front end opens the diegetic phone (BP_Phone)
FE_C = '/Game/FoA/UI/Framework/BP_FoAFrontEnd.BP_FoAFrontEnd_C'
ent = entry_node(f)
pbr = f.branch(864, 0)
ffind = f.call(f'{GS}:GetActorOfClass', 1088, -96, ActorClass=FE_C)
fcasts = [n for n in f.ed.list_available_nodes([]) if n.replace(' ', '').endswith('CastToBP_FoAFrontEnd')]
fcast = f.at(f.ed.create_node_from_name(fcasts[0], V2(1440, -96), []), 1440, -96)
openp = f.call(FE_C + ':OpenPhone', 1792, -96)
f.link(tmr, 'then', pbr, 'execute'); f.link(ent, 'ShowPhone', pbr, 'Condition')
f.link(pbr, 'True', ffind, 'execute'); f.link(ffind, 'then', fcast, 'execute'); f.link(ffind, 'ReturnValue', fcast, 'Object')
f.link(fcast, 'then', openp, 'execute'); f.link(fcast, 'AsBP_FoAFrontEnd', openp, 'self')
f.comment('Phone time', 'ShowPhone: the front end opens the phone on the nightstand', [pbr, ffind, fcast, openp], C_EVENT)

g = Graph(P_).clear()
con = g.event('Construct', 0, 0)
find = g.call(f'{GS}:GetActorOfClass', 256, 160, ActorClass=BD_C)
casts = [n for n in g.ed.list_available_nodes([]) if n.endswith('CastToBP_BeatDirector')]
cast = g.at(g.ed.create_node_from_name(casts[0], V2(576, 0), []), 576, 0)
g.exec_chain(con, find, cast)
g.link(find, 'ReturnValue', cast, 'Object')
bind, mk = bind_function(g, cast, 'AsBP_BeatDirector', 'OnBeatChanged', 'HandleBeatChanged', 928, 0)
g.link(cast, 'then', bind, 'execute')
g.comment('Listen to the beat director', 'Objective updates arrive by event; nothing on screen ticks',
          [con, find, cast, bind, mk], C_EVENT)
compile_save(P_)

# Keep the existing interaction consumers when the baseline Construct graph is regenerated.
_feedback_tree = f'{P_}.WBP_HUD:WidgetTree'
if all(unreal.find_object(None, f'{_feedback_tree}.{name}') for name in ('Txt_Prompt', 'Txt_Narration')):
    from pathlib import Path as _FeedbackPath
    import runpy as _feedback_runpy
    _feedback_runpy.run_path(str(_FeedbackPath(__file__).with_name('wire_hud_feedback.py')), run_name='__main__')
else:
    print('HUD feedback skipped: Txt_Prompt and Txt_Narration must exist in the designer first')

# Preserve the centred aim marker when regenerating the HUD's event graph.
if unreal.find_object(None, f'{_feedback_tree}.Size_AimDot'):
    import runpy
    runpy.run_path('P:/FoA/Tools/Unreal/ui/add_aim_dot.py', run_name='__main__')
    compile_save(P_)
