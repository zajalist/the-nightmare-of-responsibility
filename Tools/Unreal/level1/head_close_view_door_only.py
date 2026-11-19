"""level1 lane: narrow head_close_view.py (10:56). The 70 cm "camera at his head" rule also fired for the T10 threshold
cinematic (LS_DreamThreshold's Cam_Perspective dolly passes his head), so the body played headless. Close by distance
now also requires the view target's class to be BP_Door (the door tool camera); sequences and cine cameras never hide
his head. Class by display name, so BP_FoAPlayer gains no hard reference to BP_Door (BP_Door already references the
pawn). One Hayba batch, compiled and saved; idempotent (skips when the class test exists).
  $env:HAYBA_AGENT_ID='level1'; python Tools/Unreal/level1/head_close_view_door_only.py  (inside an asset lease on BP_FoAPlayer)"""
import os
import sys

sys.path[:0] = ['P:/FoA/Tools/Unreal', 'P:/FoA/Tools/Unreal/player']
os.environ.setdefault('HAYBA_AGENT_ID', 'level1')
from held_tool_graphs import Batch, inspect  # noqa: E402

BP = '/Game/FoA/Characters/Player/BP_FoAPlayer'
G = 'UpdateFirstPersonVisibility'
ns, es = inspect(BP, G)
if any(n['title'] in ('GetClassDisplayName', 'Get Class Display Name') for n in ns):
    print('DOOR_ONLY kept')
    sys.exit(0)
near = next(n['node_id'] for n in ns if n['title'] in ('float < float', 'Less_DoubleDouble') and
            any(p['name'] == 'B' and str(p.get('default_value', '')).startswith('70') for p in n['pins']))
close = next(e['to_node'] for e in es if e['from_node'] == near and e['from_pin'] == 'ReturnValue')
vt = next(n['node_id'] for n in ns if n['title'] == 'GetViewTarget')
b = Batch(BP, G)
b.cut(near, 'ReturnValue', close, 'B')
b.fn('cls', '/Script/Engine.GameplayStatics:GetObjectClass', 600, 950); b.link(vt, 'ReturnValue', 'cls', 'Object')
b.fn('clsname', '/Script/Engine.KismetSystemLibrary:GetClassDisplayName', 800, 950); b.link('cls', 'ReturnValue', 'clsname', 'Class')
b.fn('isdoor', '/Script/Engine.KismetStringLibrary:Contains', 1000, 950, SubString='BP_Door'); b.link('clsname', 'ReturnValue', 'isdoor', 'SearchIn')
b.fn('doornear', '/Script/Engine.KismetMathLibrary:BooleanAND', 1200, 850); b.link(near, 'ReturnValue', 'doornear', 'A'); b.link('isdoor', 'ReturnValue', 'doornear', 'B')
b.link('doornear', 'ReturnValue', close, 'B')
b.comment('Only the door tool camera', ['cls', 'clsname', 'isdoor', 'doornear'])
b.run()
print('DOOR_ONLY added')
