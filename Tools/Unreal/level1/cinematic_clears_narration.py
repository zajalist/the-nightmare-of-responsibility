"""level1 lane: no stale thought line over a cinematic. SetCinematic(true) already suspends the interactor (focus,
outline and prompt cleared), but a line he had just said stayed up for its full 3.5 to 8.5 s, e.g. the bed's "Still
warm. It would be so easy." over the whole T10 threshold and the "Day one." card (DPL, 11:22). BP_FoAPlayer.SetCinematic
now also asks the HUD (BP_FoAFrontEnd.HUD) to ClearNarration (its own fade-out) when a cinematic starts. Lines said
during the cinematic still show; only the one left over from play goes. General: every cinematic calls SetCinematic.
One Hayba batch, compiled and saved; idempotent.
  $env:HAYBA_AGENT_ID='level1'; python Tools/Unreal/level1/cinematic_clears_narration.py  (inside an asset lease on BP_FoAPlayer)"""
import os
import sys

sys.path[:0] = ['P:/FoA/Tools/Unreal', 'P:/FoA/Tools/Unreal/player']
os.environ.setdefault('HAYBA_AGENT_ID', 'level1')
from held_tool_graphs import Batch, inspect  # noqa: E402

BP = '/Game/FoA/Characters/Player/BP_FoAPlayer'
FE = '/Game/FoA/UI/Framework/BP_FoAFrontEnd.BP_FoAFrontEnd_C'
HUD = '/Game/FoA/UI/Game/WBP_HUD.WBP_HUD_C'
ns, es = inspect(BP, 'SetCinematic')
if any(n['title'] == 'ClearNarration' for n in ns):
    print('CLEAR kept')
    sys.exit(0)
entry = next(n['node_id'] for n in ns if n['title'] == 'SetCinematic')
first = next(e['to_node'] for e in es if e['from_node'] == entry and e['from_pin'] == 'then')
b = Batch(BP, 'SetCinematic')
b.cut(entry, 'then', first, 'execute')
b.node('on', 'branch', -600, -300); b.link(entry, 'bEnable', 'on', 'Condition'); b.link(entry, 'then', 'on', 'execute')
b.fn('fe', '/Script/Engine.GameplayStatics:GetActorOfClass', -400, -150, ActorClass=FE)
b.link('on', 'then', 'fe', 'execute')
b.get('hud', 'HUD', -150, -100, FE); b.link('fe', 'ReturnValue', 'hud', 'self')
b.fn('ok', '/Script/Engine.KismetSystemLibrary:IsValid', -250, -450); b.link('fe', 'ReturnValue', 'ok', 'Object')
b.node('fev', 'branch', -100, -300); b.link('ok', 'ReturnValue', 'fev', 'Condition'); b.link('fe', 'then', 'fev', 'execute')
b.node('has', 'cast', 150, -300, class_path=HUD); b.link('hud', 'HUD', 'has', 'Object'); b.link('fev', 'then', 'has', 'execute')  # no front end (Level 2 maps): skip
b.fn('clear', HUD + ':ClearNarration', 400, -300); b.link('has', 'AsWBP HUD', 'clear', 'self'); b.link('has', 'then', 'clear', 'execute')
for src, pin in (('on', 'else'), ('fev', 'else'), ('has', 'CastFailed'), ('clear', 'then')):
    b.link(src, pin, first, 'execute')
b.comment('Clear the leftover line', ['on', 'fe', 'ok', 'fev', 'hud', 'has', 'clear'])
b.run()
print('CLEAR added')
