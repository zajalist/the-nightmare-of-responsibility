"""level1 lane, round 3: a tactile camera nudge with every interaction sound. BP_Interactable.PlayFeedback plays the
state's sound (drawers, wardrobe doors, the boot, the key, the door stages, the fall); right after it the player's
camera now gets CS_SandHit (the battle's legacy shake, about 0.6 deg for 0.15 s) at scale 0.35, so about 0.2 deg:
felt, not seen. Reduce motion (MPC_Dream ReduceMotion = 1) scales it to 0. One Hayba batch, compiled and saved;
idempotent (skips when PlayFeedback already starts a camera shake).
  $env:HAYBA_AGENT_ID='level1'; python Tools/Unreal/level1/feedback_nudge.py   (inside an asset lease on BP_Interactable)"""
import os
import sys

sys.path[:0] = ['P:/FoA/Tools/Unreal', 'P:/FoA/Tools/Unreal/player']
os.environ.setdefault('HAYBA_AGENT_ID', 'level1')
from held_tool_graphs import Batch, inspect, find  # noqa: E402

BP = '/Game/FoA/Gameplay/BP_Interactable'
SCALE = 0.35

ns, es = inspect(BP, 'PlayFeedback')
if any(n['title'] == 'StartCameraShake' for n in ns):
    print('NUDGE kept')
    sys.exit(0)
sound = find(ns, 'PlaySoundAtLocation')
after = [e for e in es if e['from_node'] == sound and e['from_pin'] == 'then']
assert len(after) == 1, after
b = Batch(BP, 'PlayFeedback')
b.cut(sound, 'then', after[0]['to_node'], 'execute')
b.fn('pcm', '/Script/Engine.GameplayStatics:GetPlayerCameraManager', 600, 500, PlayerIndex=0)
b.fn('calm', '/Script/Engine.KismetMaterialLibrary:GetScalarParameterValue', 600, 650,
     Collection='/Game/FoA/PostProcess/MPC_Dream.MPC_Dream', ParameterName='ReduceMotion')
b.fn('allow', '/Script/Engine.KismetMathLibrary:Subtract_DoubleDouble', 850, 650, A=1.0); b.link('calm', 'ReturnValue', 'allow', 'B')
b.fn('scale', '/Script/Engine.KismetMathLibrary:Multiply_DoubleDouble', 1050, 650, B=SCALE); b.link('allow', 'ReturnValue', 'scale', 'A')
b.fn('nudge', '/Script/Engine.PlayerCameraManager:StartCameraShake', 900, 300, ShakeClass='/Game/FoA/VFX/CS_SandHit.CS_SandHit_C')
b.link('pcm', 'ReturnValue', 'nudge', 'self'); b.link('scale', 'ReturnValue', 'nudge', 'Scale')
b.link(sound, 'then', 'calm', 'execute'); b.link('calm', 'then', 'nudge', 'execute')  # the MPC read is impure: on the exec path
b.link('nudge', 'then', after[0]['to_node'], 'execute')
b.comment('Tactile nudge', ['pcm', 'calm', 'allow', 'scale', 'nudge'])
b.run()
print('NUDGE added')
