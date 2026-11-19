import sys
sys.path.insert(0,'Tools/Splats')
from build_room_takeover import *
assert not call('editor_get_state')['pie_running']
lease=h.lease_acquire(h.agent_id(),['asset:'+P,'actor:/Game/FoA/Maps/L_Tutorial_Bedroom.RoomTakeover'],ttl_s=30,wait_s=10)
try:
 for n,*_ in [row for row in PARTS if row[2]==MOUND]:
  for path in [C+':'+n+'_GEN_VARIABLE','/Game/FoA/Maps/L_Tutorial_Bedroom.L_Tutorial_Bedroom:PersistentLevel.BP_RoomTakeover_C_1.'+n]:
   print(path,call('object_set_property',path=path,properties={'OverrideMaterials':['/Game/FoA/VFX/Sand/MI_SandSpill_Mound']}))
 print(call('blueprint_compile',path=P));call('asset_save',asset_paths=[P]);call('level_save')
finally:h.release(h.agent_id(),lease)
