"""Patch only doorway replacement timing through Hayba; no full director rebuild."""
import json,os,sys
from pathlib import Path
sys.path.insert(0,'P:/FoA/Tools/Unreal');import hayba_call as hc
os.environ['HAYBA_AGENT_ID']='world_progression'
P='/Game/FoA/Gameplay/BP_BeatDirector';OUT=Path('P:/FoA/Saved/Integration/door_wall_atomic');OUT.mkdir(exist_ok=True)
def call(name,**args):
 r=hc.call(name,args,timeout=15);assert r.get('ok'),r;return r['data']
ops=[]
for graph,enable in [('WardrobeVanish',True),('ResetWardrobeTransition',False)]:
 d=call('blueprint_inspect_graph',path=P,graph_name=graph);(OUT/(graph+'_before.json')).write_text(json.dumps(d,indent=2))
 door=next(n['node_id']for n in d['nodes']if n['title']=='SetDoorHidden')
 walls=[n for n in d['nodes']if n['title']=='SetOldWall']
 if walls:
  assert any(e['from_node']==door and e['to_node']==walls[0]['node_id']for e in d['edges']),'Unexpected existing wall connection'
  continue
 targets=[e for e in d['edges']if e['from_node']==door and e['from_pin']=='then'];assert len(targets)==(0 if enable else 1)
 ref='fill'if enable else'reset_fill'
 ops.extend([dict(op='add_node',graph_name=graph,ref=ref,node_type='call_function',function_name=P+'.BP_BeatDirector_C:SetOldWall',x=2080 if enable else 1152,y=0),dict(op='set_pin',graph_name=graph,node_id=ref,pin_name='Enable',value='true'if enable else'false')])
 if targets:ops.append(dict(op='disconnect',graph_name=graph,node_id=door,pin_name='then',to_node=targets[0]['to_node'],to_pin='execute'))
 ops.append(dict(op='connect',graph_name=graph,from_node=door,to_node=ref))
 if targets:
  ops.append(dict(op='connect',graph_name=graph,from_node=ref,to_node=targets[0]['to_node']))
  timers=[n['node_id']for n in d['nodes']if n['title']=='Clear Timer by Function Name']
  for i,n in enumerate(timers):ops.append(dict(op='move',graph_name=graph,node_id=n,x=1472+320*i,y=0))
 ops.append(dict(op='fit_comments',graph_name=graph))
if ops:
 r=call('blueprint_graph_batch',path=P,ops=ops,compile=True,save=True);(OUT/'mutation.json').write_text(json.dumps(r,indent=2));assert r.get('ok',True)and r.get('applied')==len(ops),r
 print('Applied',r.get('applied'),'ops',r.get('compile'),r.get('compile_error'))
layout=[]
for graph in ('WardrobeVanish','ResetWardrobeTransition'):
 d=call('blueprint_inspect_graph',path=P,graph_name=graph)
 box=next(n['node_id']for n in d['nodes']if n['title']=='Comment')
 layout.append(dict(op='fit_comments',graph_name=graph,members={box:[n['node_id']for n in d['nodes']if n['title']!='Comment']},title_only=True))
call('blueprint_graph_batch',path=P,ops=layout,compile=True,save=True)
for graph in ('WardrobeVanish','ResetWardrobeTransition'):
 d=call('blueprint_inspect_graph',path=P,graph_name=graph);(OUT/(graph+'_after.json')).write_text(json.dumps(d,indent=2));door=next(n['node_id']for n in d['nodes']if n['title']=='SetDoorHidden');wall=next(n['node_id']for n in d['nodes']if n['title']=='SetOldWall');assert any(e['from_node']==door and e['to_node']==wall for e in d['edges']);assert not d['dirty'];print('Verified',graph,d['node_count'],'nodes',d['edge_count'],'edges, saved')
