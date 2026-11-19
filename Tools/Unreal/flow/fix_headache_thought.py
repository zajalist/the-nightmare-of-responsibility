"""Show the existing headache reaction before its authored thought; no voice generation or camera changes."""
import sys,json
from pathlib import Path
sys.path.insert(0,'P:/FoA/Tools/Unreal');sys.path.insert(0,'P:/FoA/Tools/Unreal/player')
import hayba_call as h
from held_tool_graphs import Batch,inspect,find
P='/Game/FoA/Gameplay/BP_BeatDirector';C=P+'.BP_BeatDirector_C';KS='/Script/Engine.KismetSystemLibrary:'
INTER='/Game/FoA/Gameplay/BPC_Interactor.BPC_Interactor_C'
def c(n,**p):
 r=h.call(n,p);assert r.get('ok'),r
 d=r.get('data',{});assert d.get('ok',True) and not d.get('failed'),d
 return d
assert not c('editor_get_state')['pie_running']
owner=h.agent_id() or 'room-takeover'
lease=h.lease_acquire(owner,['asset:'+P],ttl_s=90,wait_s=30)
try:
 c('blueprint_add_variable',path=P,variable_name='PendingHeadacheLine',variable_type='text',default_value='',category='Story',update_existing=True)
 if not h.call('blueprint_inspect_graph',{'path':P,'graph_name':'HeadacheThought'}).get('ok'):c('blueprint_add_function',path=P,function_name='HeadacheThought')
 ns,es=inspect(P,'HeadacheThought');e=find(ns,'HeadacheThought');b=Batch(P,'HeadacheThought')
 old=[n['node_id'] for n in ns if n['node_id']!=e]
 if old:b.ops.append(dict(op='remove',node_ids=old))
 b.get('active','bHeadacheActive',0,240);b.node('gate','branch',280,0);b.link('active','bHeadacheActive','gate','Condition');b.chain(e,'gate')
 b.get('player','StoryPlayer',280,300);b.fn('inter','/Script/Engine.Actor:GetComponentByClass',560,300,ComponentClass=INTER);b.link('player','StoryPlayer','inter','self')
 b.fn('valid',KS+'IsValid',840,300);b.link('inter','ReturnValue','valid','Object');b.node('safe','branch',840,0);b.link('valid','ReturnValue','safe','Condition');b.chain('gate','safe')
 b.get('line','PendingHeadacheLine',1120,300);b.fn('say',INTER+':Narrate',1120,0);b.link('inter','ReturnValue','say','self');b.link('line','PendingHeadacheLine','say','Line');b.chain('safe','say')
 b.comment('React before the thought',[o['ref'] for o in b.ops if o.get('op')=='add_node']);b.run()
 ns,es=inspect(P,'TryStoryMoment');by={n['node_id']:n for n in ns}
 links=[e for e in es if e['to_pin']=='execute' and by[e['from_node']]['title']=='StartHeadache' and by[e['to_node']]['title']=='Narrate']
 if links:
  assert len(links)==3,links
  b=Batch(P,'TryStoryMoment')
  for i,edge in enumerate(links):
   old=by[edge['to_node']];line=next(e for e in es if e['to_node']==old['node_id'] and e['to_pin']=='Line')
   x=old.get('x',0);y=old.get('y',0)
   b.set('remember'+str(i),'PendingHeadacheLine',x,y);b.link(line['from_node'],line['from_pin'],'remember'+str(i),'PendingHeadacheLine')
   b.fn('wait'+str(i),KS+'K2_SetTimer',x,y-240,FunctionName='HeadacheThought',Time=.65,bLooping='false')
   b.cut(edge['from_node'],edge['from_pin'],edge['to_node'],edge['to_pin']);b.chain(edge['from_node'],'remember'+str(i),'wait'+str(i))
   b.ops.append(dict(op='remove',node_ids=[old['node_id']]))
   b.comment('A moment to feel it '+str(i+1),['remember'+str(i),'wait'+str(i)])
  b.run()
 # Native inspection omits positions; keep these three authored branches in separate columns.
 ns,es=inspect(P,'TryStoryMoment');by={n['node_id']:n for n in ns};layout=Batch(P,'TryStoryMoment')
 for node in [n for n in ns if n['title']=='Set PendingHeadacheLine']:
  line=next(edge for edge in es if edge['to_node']==node['node_id'] and edge['to_pin']=='PendingHeadacheLine')
  text=next(pin.get('default_value','') for pin in by[line['from_node']]['pins'] if pin['name']=='InString')
  x=4200 if text.startswith('Ow.') else 5100 if text.startswith('Why is it always') else 6000
  wait=next(edge['to_node'] for edge in es if edge['from_node']==node['node_id'] and edge['to_pin']=='execute')
  layout.ops.extend([dict(op='move',node_id=node['node_id'],x=x,y=-1300),dict(op='move',node_id=wait,x=x,y=-1050)])
 layout.run()
 ns,es=inspect(P,'EndHeadache');entry=find(ns,'EndHeadache')
 if not any(n['title']=='Clear Timer by Function Name' and any(p.get('default_value')=='HeadacheThought' for p in n.get('pins',[])) for n in ns):
  edge=next(e for e in es if e['from_node']==entry and e['from_pin']=='then');b=Batch(P,'EndHeadache')
  b.fn('cancelthought',KS+'K2_ClearTimer',-650,0,FunctionName='HeadacheThought');b.set('forget','PendingHeadacheLine',-350,0)
  b.cut(entry,'then',edge['to_node'],edge['to_pin']);b.chain(entry,'cancelthought','forget');b.link('forget','then',edge['to_node'],edge['to_pin'])
  b.ops.append(dict(op='move',node_id=entry,x=-950,y=0))
  b.comment('Cancel the pending thought',['cancelthought','forget']);b.run()
 ns,_=inspect(P,'EndHeadache');c('blueprint_graph_batch',path=P,graph_name='EndHeadache',ops=[dict(op='move',node_id=find(ns,'EndHeadache'),x=-950,y=0),dict(op='fit_comments')],compile=True,save=True)
 result=c('blueprint_compile',path=P);c('asset_save',asset_paths=[P])
 out=Path('P:/FoA/Saved/LookDev/prompt_audit');proof={'compile':result}
 for graph in ('TryStoryMoment','HeadacheThought','EndHeadache'):
  ns,es=inspect(P,graph);proof[graph]={'nodes':ns,'edges':es}
 by={n['node_id']:n for n in proof['TryStoryMoment']['nodes']}
 assert not any(by[e['from_node']]['title']=='StartHeadache' and by[e['to_node']]['title']=='Narrate' for e in proof['TryStoryMoment']['edges'])
 assert result.get('error_count',0)==0
 (out/'headache_thought_fixed.json').write_text(json.dumps(proof,indent=1))
 print('Three headache thoughts delayed .65 seconds, cancellation wired, clean native compile/save')
finally:h.release(owner,lease)
