"""BPC_Interactor.FindBest, second fix for QA #16 (from 53-60 cm the bedroom door never focused): measured in approach7,
the sweep DOES hit Door_Bedroom from 55 cm (not start-penetrating; the first fix's theory was wrong), but the hit was
dropped by the "in front of me" test, which measured from the pawn's capsule centre: looking steeply down at the lock
(pitch -63), the hit point sits above the capsule centre, so (hit - pawn) . view <= 0. The test now measures from the
camera, which is what "in front of the view" means. Backs up the asset first; Hayba batch, compiled and saved only clean.
  $env:HAYBA_AGENT_ID='anim'; python Tools/Unreal/player/interactor_scan_fix2.py"""
import datetime
import shutil
import sys
from pathlib import Path

sys.path[:0] = ['P:/FoA/Tools/Unreal', 'P:/FoA/Tools/Unreal/player']
import hayba_call as h  # noqa: E402
from held_tool_graphs import Batch, inspect  # noqa: E402

P = '/Game/FoA/Gameplay/BPC_Interactor'
assert not h.call('editor_get_state')['data']['pie_running'], 'PIE running'
nodes, edges = inspect(P, 'FindBest')
title = {n['node_id']: n['title'] for n in nodes}
cam = next(n['node_id'] for n in nodes if n['title'] == 'GetCameraLocation')
dots = [n['node_id'] for n in nodes if n['title'] == 'Dot Product']
# the in-front test: a Dot Product whose result feeds "float > float" and whose A is (point - something)
front = next(x for x in edges if x['from_node'] in dots and title[x['to_node']] == 'float > float')['from_node']
sub = next(x['from_node'] for x in edges if x['to_node'] == front and x['to_pin'] == 'A')
old_b = next(x for x in edges if x['to_node'] == sub and x['to_pin'] == 'B')
if old_b['from_node'] == cam:
    sys.exit('in-front test already measures from the camera')
assert title[old_b['from_node']] == 'Get Actor Location', title[old_b['from_node']]
backup = Path('P:/FoA/Saved/Backups/interactor_scan') / datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
backup.mkdir(parents=True)
shutil.copy2('P:/FoA/Content/FoA/Gameplay/BPC_Interactor.uasset', backup / 'BPC_Interactor.uasset')
lease = h.lease_acquire('anim', ['asset:' + P], ttl_s=60)
try:
    b = Batch(P, 'FindBest')
    b.cut(old_b['from_node'], old_b['from_pin'], sub, 'B')
    b.link(cam, 'ReturnValue', sub, 'B')
    b.run()
finally:
    h.release('anim', lease)
print('SCAN_FIX2 done, backup', backup)
