"""level1 lane: no head in his own view at the door tool. BP_FoAPlayer.UpdateFirstPersonVisibility called the camera
"close" (Face, Hair and Eyebrows hidden, UpdateHeadHidden hiding the head parts) only while the view target is the
pawn or something attached to it. The door tool's view target is BP_Door's camera, 60 cm from his head (S1s), so his
head and the face blur filled the right of the frame. Close now also means the rendered camera is within 70 cm of his
head bone; story shots stay far (the T9 hero shot 190 cm, the under-bed toss view about 130 cm) and keep his face.
One Hayba batch, compiled and saved; idempotent (skips when the distance test exists).
  $env:HAYBA_AGENT_ID='level1'; python Tools/Unreal/level1/head_close_view.py   (inside an asset lease on BP_FoAPlayer)"""
import os
import sys

sys.path[:0] = ['P:/FoA/Tools/Unreal', 'P:/FoA/Tools/Unreal/player']
os.environ.setdefault('HAYBA_AGENT_ID', 'level1')
from held_tool_graphs import Batch, inspect  # noqa: E402

BP = '/Game/FoA/Characters/Player/BP_FoAPlayer'
G = 'UpdateFirstPersonVisibility'
NEAR = 70.0
ns, es = inspect(BP, G)
if any(n['title'] in ('Distance (Vector)', 'Vector_Distance') for n in ns):
    print('HEAD kept')
    sys.exit(0)
ids = {n['node_id']: n['title'] for n in ns}
setc = next(n['node_id'] for n in ns if n['title'] == 'Set bCameraClose')
old_or = next(e['from_node'] for e in es if e['to_node'] == setc and e['to_pin'] == 'bCameraClose')
users = [(e['to_node'], e['to_pin']) for e in es if e['from_node'] == old_or and e['from_pin'] == 'ReturnValue']
assert len(users) == 2, users  # Set bCameraClose and the NOT that shows the face, hair and brows
body = next(n['node_id'] for n in ns if n['title'] == 'Get Body')
b = Batch(BP, G)
for n, p in users:
    b.cut(old_or, 'ReturnValue', n, p)
b.fn('pcm', '/Script/Engine.GameplayStatics:GetPlayerCameraManager', 0, 700, PlayerIndex=0)
b.fn('eye', '/Script/Engine.PlayerCameraManager:GetCameraLocation', 200, 700); b.link('pcm', 'ReturnValue', 'eye', 'self')
b.fn('head', '/Script/Engine.SceneComponent:GetSocketLocation', 200, 850, InSocketName='head'); b.link(body, 'Body', 'head', 'self')
b.fn('gap', '/Script/Engine.KismetMathLibrary:Vector_Distance', 400, 750); b.link('eye', 'ReturnValue', 'gap', 'V1'); b.link('head', 'ReturnValue', 'gap', 'V2')
b.fn('near', '/Script/Engine.KismetMathLibrary:Less_DoubleDouble', 600, 750, B=NEAR); b.link('gap', 'ReturnValue', 'near', 'A')
b.fn('close', '/Script/Engine.KismetMathLibrary:BooleanOR', 800, 650); b.link(old_or, 'ReturnValue', 'close', 'A'); b.link('near', 'ReturnValue', 'close', 'B')
for n, p in users:
    b.link('close', 'ReturnValue', n, p)
b.comment('Camera at his head', ['pcm', 'eye', 'head', 'gap', 'near', 'close'])
b.run()
print('HEAD added')
