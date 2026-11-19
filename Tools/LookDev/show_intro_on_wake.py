"""An explicit menu Wake Up plays the intro, including returning players.
Morning rollover calls the Director directly and does not enter this menu route.
"""
import sys,json
from pathlib import Path
sys.path.insert(0,'P:/FoA/Tools/Unreal');sys.path.insert(0,'P:/FoA/Tools/Unreal/player')
import hayba_call as h
from held_tool_graphs import Batch,inspect,find
P='/Game/FoA/UI/Framework/BP_FoAFrontEnd'
def c(cmd,**args):
 r=h.call(cmd,args);assert r.get('ok'),r
 d=r.get('data',{});assert d.get('ok',True),d
 return d
assert not c('editor_get_state')['pie_running']
lease=h.lease_acquire('room-takeover',['asset:'+P],ttl_s=45,wait_s=20)
try:
 assert not c('editor_get_state')['pie_running']
 ns,es=inspect(P,'AfterWakeFade');b=Batch(P,'AfterWakeFade')
 if any(n['title']=='Get IntroVersionSeen' for n in ns):
  entry=find(ns,'AfterWakeFade');branch=find(ns,'Branch');valid=find(ns,'IsValidClass')
  remove=[find(ns,title) for title in ('LoadSettings','Get IntroVersionSeen','integer < integer','AND Boolean')]
  b.ops.append(dict(op='remove',node_ids=remove));b.chain(entry,branch);b.link(valid,'ReturnValue',branch,'Condition')
  b.comment('Story after Wake Up',[entry,valid,branch]);b.run()
 result=c('blueprint_compile',path=P);c('asset_save',asset_paths=[P])
 ns,es=inspect(P,'AfterWakeFade')
 assert not any(n['title']=='Get IntroVersionSeen' for n in ns)
 Path('Saved/LookDev/intro_restored/explicit_wake_integration.json').write_text(json.dumps(dict(compile=result,nodes=ns,edges=es),indent=1))
 print(result)
finally:h.release('room-takeover',lease)

