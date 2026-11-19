"""Keep the existing prompt ownership and make the E label match the selected Look verb."""
import sys,json
from pathlib import Path
sys.path.insert(0,'P:/FoA/Tools/Unreal');sys.path.insert(0,'P:/FoA/Tools/Unreal/player')
import hayba_call as h
from held_tool_graphs import Batch,inspect,find
P='/Game/FoA/UI/Game/WBP_HUD';K='/Script/Engine.KismetMathLibrary:'
# Interactor contract: [Take/Use,Look], [Look], or [].
for count,index,expected in [(0,0,False),(1,0,True),(2,0,False),(2,1,True)]:assert (index>0 or count==1)==expected

def c(n,**p):
 r=h.call(n,p);assert r.get('ok'),r
 d=r.get('data',{});assert d.get('ok',True) and not d.get('failed'),d
 return d
assert not c('editor_get_state')['pie_running']
lease=h.lease_acquire('room-takeover',['asset:'+P],ttl_s=60,wait_s=30)
try:
 ns,es=inspect(P,'HandleFocusChanged')
 if not any(n['title']=='SelectString' and any(p.get('default_value')=='E  Inspect' for p in n.get('pins',[])) for n in ns):
  count=find(ns,'Length')
  combined=next(n for n in ns if n['title']=='Append' and any(e['to_node']==n['node_id'] and e['to_pin']=='B' and next(v for v in ns if v['node_id']==e['from_node'])['title']=='SelectString' for e in es))
  current=next(e for e in es if e['to_node']==combined['node_id'] and e['to_pin']=='A')
  looking=next(n for n in ns if n['title']=='integer > integer' and any(p.get('name')=='B' and p.get('default_value')=='0' for p in n.get('pins',[])))
  linked={e[k] for e in es for k in ['from_node','to_node']}
  orphan=[n['node_id'] for n in ns if n['title']=='SelectString' and n['node_id'] not in linked]
  b=Batch(P,'HandleFocusChanged')
  if orphan:b.ops.append(dict(op='remove',node_ids=orphan))
  b.fn('onlylook',K+'EqualEqual_IntInt',1200,1450,B=1);b.link(count,'ReturnValue','onlylook','A')
  b.fn('inspectverb',K+'BooleanOR',1500,1300);b.link(looking['node_id'],'ReturnValue','inspectverb','A');b.link('onlylook','ReturnValue','inspectverb','B')
  b.fn('selected',K+'SelectString',1800,1150,A='E  Inspect');b.link('inspectverb','ReturnValue','selected','bPickA');b.link(current['from_node'],current['from_pin'],'selected','B')
  b.cut(current['from_node'],current['from_pin'],current['to_node'],current['to_pin']);b.link('selected','ReturnValue',combined['node_id'],'A')
  b.comment('Show the selected action',['onlylook','inspectverb','selected']);b.run()
 ns,es=inspect(P,'HandleFocusChanged')
 result=c('blueprint_compile',path=P);c('asset_save',asset_paths=[P])
 out=Path('P:/FoA/Saved/LookDev/prompt_audit')
 (out/'selected_verb_fixed.json').write_text(json.dumps({'nodes':ns,'edges':es,'compile':result},indent=1))
 assert result.get('error_count',0)==0 and any(n['title']=='SelectString' and any(p.get('default_value')=='E  Inspect' for p in n.get('pins',[])) for n in ns)
 print('Prompt now follows selected verb; compiled and saved',result)
finally:h.release('room-takeover',lease)
