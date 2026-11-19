"""Layout only: separate painting clock input and enclose the intro ink preview."""
import json,sys,os
from pathlib import Path
sys.path.insert(0,'P:/FoA/Tools/Unreal')
import hayba_call as h
os.environ['HAYBA_AGENT_ID']='room-takeover'
P='/Game/FoA/Art/Materials/M_SandPainting'
I='/Game/FoA/UI/Materials/M_UI_Panel'
def c(n,**p):
 r=h.call(n,p);assert r.get('ok'),r
 return r['data']
assert not c('editor_get_state')['pie_running']
lease=h.lease_acquire('room-takeover',['asset:'+P,'asset:'+I],ttl_s=30,wait_s=10)
try:
 assert not c('editor_get_state')['pie_running']
 info=c('material_get_info',path=P)
 for node in info['expressions']:
  y=None
  if node['class']=='MaterialExpressionTime':y=380
  elif node.get('parameter_name')=='PaintingStage':y=520
  elif node.get('parameter_name')=='PaintingPulse':y=680
  elif node['class']=='MaterialExpressionCollectionParameter':y=840
  if y is not None:c('material_set_node',material_path=P,node_id=node['id'],node_pos=[-1000,y])
 for box in info['comments']:c('material_set_comment',material_path=P,comment_id=box['id'],size=[1130,1100])
 info=c('material_get_info',path=I)
 for box in info['comments']:
  if box['text']=='Actual frame and ink':c('material_set_comment',material_path=I,comment_id=box['id'],size=[350,900])
 c('asset_save',asset_paths=[P,I])
 result={p:c('material_get_info',path=p) for p in (P,I)}
 Path('P:/FoA/Saved/GraphShots/RoomTakeover/layout_readback.json').write_text(json.dumps(result,indent=1))
finally:h.release('room-takeover',lease)
