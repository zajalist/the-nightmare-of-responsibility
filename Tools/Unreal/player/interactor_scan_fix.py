"""BPC_Interactor.FindBest: focus survives standing close (QA #16: from 53-60 cm the bedroom door never focused; from
about 1 m it did). The scan sweeps a sphere out from the camera. Standing close, the sweep starts inside the door's
collision; such a start-penetrating hit carries no real impact point (it sits at the sweep start, the camera), so the
"in front of me" test (impact point minus the pawn, dotted with the view) failed and the hit was dropped. Now, for a
hit with bInitialOverlap, the point the tests and the cost use is the hit component's bounds centre instead.
Backs up the asset first. Hayba batch, compiled and saved only when clean.
  $env:HAYBA_AGENT_ID='anim'; python Tools/Unreal/player/interactor_scan_fix.py"""
import datetime
import shutil
import sys
from pathlib import Path

sys.path[:0] = ['P:/FoA/Tools/Unreal', 'P:/FoA/Tools/Unreal/player']
import hayba_call as h  # noqa: E402
from held_tool_graphs import Batch, inspect  # noqa: E402

P = '/Game/FoA/Gameplay/BPC_Interactor'
K = '/Script/Engine.KismetMathLibrary:'
assert not h.call('editor_get_state')['data']['pie_running'], 'PIE running'
nodes, edges = inspect(P, 'FindBest')
if any(n['title'] == 'GetComponentBounds' for n in nodes):
    sys.exit('scan fix already in')
brk = next(n['node_id'] for n in nodes if n['title'] == 'BreakHitResult')
uses = [x for x in edges if x['from_node'] == brk and x['from_pin'] == 'ImpactPoint']
assert len(uses) == 3, uses  # the reach distance, the in-front test and the view angle
backup = Path('P:/FoA/Saved/Backups/interactor_scan') / datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
backup.mkdir(parents=True)
shutil.copy2('P:/FoA/Content/FoA/Gameplay/BPC_Interactor.uasset', backup / 'BPC_Interactor.uasset')
lease = h.lease_acquire('anim', ['asset:' + P], ttl_s=60)
try:
    b = Batch(P, 'FindBest')
    for x in uses:
        b.cut(brk, 'ImpactPoint', x['to_node'], x['to_pin'])
    b.fn('bounds', '/Script/Engine.KismetSystemLibrary:GetComponentBounds', 2600, 900)
    b.link(brk, 'HitComponent', 'bounds', 'Component')
    b.fn('point', K + 'SelectVector', 2900, 800); b.link('bounds', 'Origin', 'point', 'A'); b.link(brk, 'ImpactPoint', 'point', 'B')
    b.link(brk, 'bInitialOverlap', 'point', 'bPickA')
    for x in uses:
        b.link('point', 'ReturnValue', x['to_node'], x['to_pin'])
    b.comment('Standing close: a sweep that starts inside the collider has no impact point; use its bounds centre', ['bounds', 'point'])
    b.run()
finally:
    h.release('anim', lease)
print('SCAN_FIX done, backup', backup)
