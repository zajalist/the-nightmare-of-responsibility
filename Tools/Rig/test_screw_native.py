"""Offline regression gates for the prepared native screwdriver runtime."""
import copy,json,sys
from pathlib import Path
import numpy as np
sys.path[:0]=['P:/FoA/Tools/Rig','P:/FoA/Tools/Unreal/player']
from export_screw_runtime import H,ROOT,load,BODY,K
from ue_hand import m
from measure_grip_pose import finger_limits,wrist_rotation
assert not finger_limits(load(2,False)[1],H.ref,'r')['joints_pass'], 'old screw 2 must fail the native thumb limit'
for i in range(4):
 turn=json.loads((ROOT/f'screwdriver_screw{i}_turn.json').read_text());source=json.loads((ROOT/f'screwdriver_screw{i}_native_solution.json').read_text())
 assert min(source['native_clearance_mm'].values())>=1
 assert max(source['native_clearance_mm'].values())<=3
 worst=0
 for a,b in zip(turn['frames'],turn['frames'][1:]):
  p={bone:[m.lerp(v[0],b[bone][0],.5),m.qslerp(v[1],b[bone][1],.5),v[2]] for bone,v in a.items()}
  w=H.world(p);f=m.norm(m.sub(w['hand_r'][0],w['lowerarm_r'][0]));d=m.norm(m.sub(w['middle_01_r'][0],w['hand_r'][0]))
  angles=[np.degrees(np.arccos(np.clip(m.dot(f,v),-1,1))) for v in (d,(0,1,0))]
  assert max(angles)<=20,(i,angles);worst=max(worst,*angles)
  assert finger_limits(p,H.ref,'r')['joints_pass']
  assert wrist_rotation(p,H.ref,'r')['wrist_axial_pass']
 for d in ('thumb','index','middle','ring','pinky'):
  for j in (2,3):assert H.curl_motion(turn['frames'][0],d,j,'r')>0
 print('native turn',i,'interpolated wrist/inline max',worst)
import screw_grip_graphs as g
from held_tool_graphs import Batch
captures=[]
def run(batch):
 existing={n['node_id'] for n in json.loads(Path('Saved/Codex/anim_'+batch.graph+'.json').read_text())['nodes']} if batch.graph in ('EventGraph','SetToolHandRotation','RefreshDoorTool') else {'entry'}
 made=set()
 for op in batch.ops:
  if op['op']=='add_node':assert op['ref'] not in made;made.add(op['ref'])
  if op['op']=='connect':
   assert op['from_node'] in made|existing,op
   assert op['to_node'] in made|existing,op
 captures.append(batch)
g.fresh=lambda fn:(Batch(g.P,fn),'entry');Batch.run=run
g.inspect=lambda path,fn:(lambda x:(x['nodes'],x['edges']))(json.loads(Path('Saved/Codex/anim_'+fn+'.json').read_text()))
g.apply();g.update();g.hooks();assert len(captures)==5
print('five graph batches: all connection endpoints resolve; UE compile still required')
feet=[]
for i,row in enumerate(json.loads((ROOT/'screw_runtime.json').read_text())):
 frame=json.loads((ROOT/row['source'].replace('_native_solution.json','_turn.json')).read_text())['frames'][0]
 world=H.world(frame)
 tip=np.array([373.83,46.4+(4.2 if i%2 else 0),93-(9 if i>=2 else 0)])
 root=tip+row['root_in_tip'];root[2]=3.09445
 assert np.linalg.norm(root[:2]-[310.31610895,23])<.001
 feet.append([root+BODY.apply(np.array(world[b][0])*K) for b in ('foot_l','foot_r')])
assert np.max(np.abs(np.array(feet)-feet[0]))<.001
print('Native column mapping keeps both feet and the body stand fixed across all four screws')
