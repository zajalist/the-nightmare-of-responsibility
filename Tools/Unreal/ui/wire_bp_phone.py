"""BP_Phone graph (run via hayba_replay.py; components from phone_bp_calls.py). The phone is diegetic: WBP_Phone is drawn
on the phone's screen by a world-space WidgetComponent, and opening it pushes the view in to a close shot.
  OpenPhone   view blends 0.8 s to PhoneCam (CineCamera, focus on the screen, the room behind falls soft); the player
              stops; the phone takes the Enter / E / Space / gamepad A keys
  ClosePhone  view blends back to the pawn; movement and look come back
  keys        while open, the action key runs WBP_Phone.DoAction (Wake up reports PhoneWakeUp; then it closes)
No Tick. BP_FoAFrontEnd.OpenPhone/ClosePhone route here (and hide/show the HUD)."""
exec(open('P:/FoA/Tools/Unreal/ui/bp_graph.py').read())
import unreal

P_ = '/Game/FoA/UI/Game/BP_Phone'
WBP_C = '/Game/FoA/UI/Game/WBP_Phone.WBP_Phone_C'
GS, KSL = '/Script/Engine.GameplayStatics', '/Script/Engine.KismetSystemLibrary'
PCC = '/Script/Engine.PlayerController'

ensure_vars(P_, [('bOpen', ptype('bool'), 'false', 'Phone|State', False),
                 ('BlendSeconds', ptype('real'), '0.8', 'Phone', True)])
for f in ('OpenPhone', 'ClosePhone'):
    Graph.function(P_, f)


def pc(g, x, y):
    return g.call(f'{GS}:GetPlayerController', x, y, PlayerIndex=0)


# ---- OpenPhone
f = Graph(P_, 'OpenPhone'); e = f.at(entry_node(f), 0, 0)
so = f.set('bOpen', 256, 0); f.default(so, 'bOpen', 'true')
p1 = pc(f, 448, 192)
hits = sorted((n for n in f.ed.list_available_nodes([]) if 'getareferencetoself' in n.replace(' ', '').lower()), key=len)
me = f.at(f.ed.create_node_from_name(hits[0], V2(448, 288), []), 448, 288)
blend = f.call(f'{PCC}:SetViewTargetWithBlend', 576, 0, BlendFunc='VTBlend_EaseInOut', BlendExp=2.0)
bt = f.get('BlendSeconds', 512, 352)
inp = f.call('/Script/Engine.Actor:EnableInput', 960, 0)
mv = f.call('/Script/Engine.Controller:SetIgnoreMoveInput', 1280, 0, bNewMoveInput='true')
lk = f.call('/Script/Engine.Controller:SetIgnoreLookInput', 1600, 0, bNewLookInput='true')
buzz = f.call(f'{GS}:PlaySound2D', 1920, 0, Sound='/Game/FoA/Audio/MetaSounds/Phone/S_Phone_Buzz.S_Phone_Buzz', bIsUISound='true')
f.exec_chain(e, so, blend, inp, mv, lk, buzz)
for n in (blend, mv, lk):
    f.link(p1, 'ReturnValue', n, 'self')
f.link(bt, 'BlendSeconds', blend, 'BlendTime'); f.link(p1, 'ReturnValue', inp, 'PlayerController')
f.link(me, 'self', blend, 'NewViewTarget')
f.comment('Open the phone', 'The view pushes in to PhoneCam; the player stops; keys go to the phone',
          [e, so, p1, me, blend, bt, inp, mv, lk, buzz], C_EVENT)

# ---- ClosePhone
f = Graph(P_, 'ClosePhone'); e = f.at(entry_node(f), 0, 0)
sc = f.set('bOpen', 256, 0); f.default(sc, 'bOpen', 'false')
p2 = pc(f, 448, 224)
pawn = f.call('/Script/Engine.Controller:K2_GetPawn', 704, 224)
back = f.call(f'{PCC}:SetViewTargetWithBlend', 832, 0, BlendFunc='VTBlend_EaseInOut', BlendExp=2.0)
bt2 = f.get('BlendSeconds', 768, 352)
dis = f.call('/Script/Engine.Actor:DisableInput', 1216, 0)
rm = f.call('/Script/Engine.Controller:ResetIgnoreMoveInput', 1536, 0)
rl = f.call('/Script/Engine.Controller:ResetIgnoreLookInput', 1856, 0)
f.exec_chain(e, sc, back, dis, rm, rl)
for n in (back, rm, rl):
    f.link(p2, 'ReturnValue', n, 'self')
f.link(p2, 'ReturnValue', pawn, 'self'); f.link(pawn, 'ReturnValue', back, 'NewViewTarget')
f.link(bt2, 'BlendSeconds', back, 'BlendTime'); f.link(p2, 'ReturnValue', dis, 'PlayerController')
f.comment('Close the phone', 'The view blends back to the pawn; movement and look return', [e, sc, p2, pawn, back, bt2, dis, rm, rl],
          C_EVENT)

# ---- Event graph: the action keys while open (needs WBP_Phone.DoAction: run wire_phone.py, then this script again)
g = Graph(P_).clear()
keys = []
probe = g.ed.add_call_function_node(WBP_C + ':DoAction')
KEYS = ('Enter', 'E', 'SpaceBar', 'Gamepad_FaceButton_Bottom') if probe else ()
if probe:
    g.ed.remove_nodes([probe])
else:
    print('WBP_Phone.DoAction not compiled yet: phone keys wired on the next run')
for i, key in enumerate(KEYS):
    y = i * 224
    names = [n for n in g.ed.list_available_nodes([]) if n.startswith('Input|')
             and n.split('|')[-1].replace(' ', '') in (key, key.replace('_', ''))]
    assert names, 'no InputKey node for ' + key
    ev = g.at(g.ed.create_node_from_name(names[0], V2(0, y), []), 0, y)
    op = g.get('bOpen', 224, y + 112)
    br = g.branch(320, y)
    scr = g.get('Screen', 480, y + 112)
    wid = g.call('/Script/UMG.WidgetComponent:GetUserWidgetObject', 544, y + 160)
    casts = [n for n in g.ed.list_available_nodes([]) if n.replace(' ', '').endswith('CastToWBP_Phone')]
    cast = g.at(g.ed.create_node_from_name(casts[0], V2(800, y), []), 800, y)
    act = g.call(WBP_C + ':DoAction', 1152, y)
    tap = g.call(f'{GS}:PlaySound2D', 1440, y, Sound='/Game/FoA/Audio/MetaSounds/Phone/S_Phone_Tap.S_Phone_Tap', bIsUISound='true')
    g.link(act, 'then', tap, 'execute')
    g.link(ev, 'Pressed', br, 'execute'); g.link(op, 'bOpen', br, 'Condition'); g.link(br, 'True', cast, 'execute')
    g.link(scr, 'Screen', wid, 'self'); g.link(wid, 'ReturnValue', cast, 'Object')
    g.link(cast, 'then', act, 'execute'); g.link(cast, 'AsWBP_Phone', act, 'self')
    keys += [ev, op, br, scr, wid, cast, act, tap]
if keys:
    g.comment('Phone keys', 'While open: Enter, E, Space or gamepad A press the screen button', keys, C_EVENT)
bp_ev = g.event('ReceiveBeginPlay', 0, -320)
scr0 = g.get('Screen', 224, -192)
show = g.call('/Script/Engine.SceneComponent:SetVisibility', 288, -320, bNewVisibility='true')
g.link(bp_ev, 'then', show, 'execute'); g.link(scr0, 'Screen', show, 'self')
g.comment('Screen in game', 'The screen widget draws only in game, never in the editor viewport', [bp_ev, scr0, show], C_VISUAL)
compile_save(P_)
