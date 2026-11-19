"""Apply the four native screwdriver grips without rebuilding shared door functions."""
import json,sys
sys.path[:0]=['P:/FoA/Tools/Unreal','P:/FoA/Tools/Unreal/player']
from hayba_call import call
from held_tool_graphs import Batch,inspect,find,PLAYER as P,DOOR,K,SC,MH_C as MH,PLAYER_C as PC
ACT='/Script/Engine.Actor:'
ROWS=json.load(open('P:/FoA/Saved/AnimShots/screw_runtime.json'))
def vec(v):return ','.join(str(x) for x in v)
def xf(t):return '(Rotation=(X=%r,Y=%r,Z=%r,W=%r),Translation=(X=%r,Y=%r,Z=%r),Scale3D=(X=%r,Y=%r,Z=%r))'%(*t[1],*t[0],*t[2])
def ensure():
 for name,typ in [('ScrewGripIndex','int'),('ScrewGripAlpha','float'),('ScrewRootInTip','vector'),('ScrewRelease','float'),('ScrewDriverTransform','transform')]:
  r=call('blueprint_add_variable',dict(path=P,variable_name=name,variable_type=typ,instance_editable=False,update_existing=True,category='Grip'));assert r.get('ok'),r
 have=call('blueprint_get_info',dict(path=P))['data']['functions']
 for name,inputs in [('ApplyScrewGrip',[dict(name='Index',type='int'),dict(name='Weight',type='float'),dict(name='TipWorld',type='vector')]),('UpdateScrewGrip',[dict(name='Dt',type='float')])]:
  if name not in have:
   r=call('blueprint_add_function',dict(path=P,function_name=name,inputs=inputs));assert r.get('ok'),r
 Batch(P,'ApplyScrewGrip').run()

def fresh(fn):
 n,e=inspect(P,fn);entry=find(n,fn);b=Batch(P,fn)
 old=[v['node_id'] for v in n if v['node_id']!=entry and v['title']!='Return Node']
 if old:b.ops.append(dict(op='remove',node_ids=old))
 return b,entry

def apply():
 b,e=fresh('ApplyScrewGrip')
 b.get('held','bHoldingTool',0,250);b.fn('ready',K+'Greater_DoubleDouble',250,250,B=.5);b.link(e,'Weight','ready','A')
 b.fn('and',K+'BooleanAND',500,250);b.link('held','bHoldingTool','and','A');b.link('ready','ReturnValue','and','B');b.node('gate','branch',750,0);b.link('and','ReturnValue','gate','Condition');b.chain(e,'gate')
 b.set('index','ScrewGripIndex',1000,0);b.link(e,'Index','index','ScrewGripIndex');b.chain('gate','index')
 prev='index'
 for i,row in enumerate(ROWS):
  y=i*650;x=1300
  if i<3:
   b.fn(f'eq{i}',K+'EqualEqual_IntInt',x,y+180,B=i);b.link(e,'Index',f'eq{i}','A');b.node(f'br{i}','branch',x,y);b.link(f'eq{i}','ReturnValue',f'br{i}','Condition')
   b.link(prev,'else' if i else 'then',f'br{i}','execute');prev=f'br{i}'
  chain=[]
  for j,(var,value) in enumerate([('ToolGripOffset',xf(row['grip_offset'])),('ScrewRootInTip',vec(row['root_in_tip'])),('ScrewDriverTransform',xf(row['driver_transform']))]):
   ref=f's{i}_{j}';b.set(ref,var,x+300+j*300,y);b.pin(ref,var,value);chain.append(ref)
  b.link(prev,'else' if i==3 else 'then',chain[0],'execute');b.chain(*chain)
  b.link(chain[-1],'then','palm','execute')
 b.get('offset','ToolGripOffset',2600,2800);b.get('grip','HeldToolGrip',2600,2950)
 b.fn('palm',SC+'K2_SetRelativeTransform',2900,0);b.link('offset','ToolGripOffset','palm','NewTransform');b.link('grip','HeldToolGrip','palm','self')
 b.get('driver','ScrewDriverTransform',2900,2800);b.fn('tip',K+'MakeTransform',2900,2950,Location='16,0,0');b.fn('compose',K+'ComposeTransforms',3200,2800);b.link('driver','ScrewDriverTransform','compose','A');b.link('tip','ReturnValue','compose','B')
 b.get('tool','HeldTool',3200,2950);b.fn('toolxf',SC+'K2_SetRelativeTransform',3200,0);b.link('tool','HeldTool','toolxf','self');b.link('compose','ReturnValue','toolxf','NewTransform')
 b.get('root','ScrewRootInTip',3500,2800);b.fn('stand',K+'Add_VectorVector',3800,2800);b.link(e,'TipWorld','stand','A');b.link('root','ScrewRootInTip','stand','B')
 b.fn('xy',K+'BreakVector',4100,2800);b.link('stand','ReturnValue','xy','InVec');b.fn('loc',ACT+'K2_GetActorLocation',3500,3100);b.fn('z',K+'BreakVector',3800,3100);b.link('loc','ReturnValue','z','InVec')
 b.fn('pos',K+'MakeVector',4400,2800);b.link('xy','X','pos','X');b.link('xy','Y','pos','Y');b.link('z','Z','pos','Z')
 b.fn('warp',ACT+'K2_SetActorLocation',3500,0,bSweep='false',bTeleport='true');b.link('pos','ReturnValue','warp','NewLocation');b.chain('palm','toolxf','warp')
 # Resolve forward references before sending the non-atomic graph batch.
 links=[op for op in b.ops if op['op']=='connect'];b.ops=[op for op in b.ops if op['op']!='connect']+links
 b.comment('Native screwdriver placement',[o['ref'] for o in b.ops if o['op']=='add_node']);b.run()

def update():
 b,e=fresh('UpdateScrewGrip');b.get('held','bHoldingTool',0,250);b.get('weight','ToolGripWeight',0,400);b.get('alpha','ScrewGripAlpha',0,550)
 b.fn('target',K+'SelectFloat',300,300,B=0);b.link('held','bHoldingTool','target','bPickA');b.link('weight','ToolGripWeight','target','A')
 b.fn('ease',K+'FInterpTo',600,300,InterpSpeed=8);b.link('alpha','ScrewGripAlpha','ease','Current');b.link('target','ReturnValue','ease','Target');b.link(e,'Dt','ease','DeltaTime')
 b.set('save','ScrewGripAlpha',300,0);b.link('ease','ReturnValue','save','ScrewGripAlpha');b.chain(e,'save')
 b.get('body','Body',600,600);b.fn('anim','/Script/Engine.SkeletalMeshComponent:GetAnimInstance',900,600);b.link('body','Body','anim','self');b.node('mh','cast',600,0,class_path=MH);b.link('anim','ReturnValue','mh','Object');b.chain('save','mh')
 b.get('index','ScrewGripIndex',900,800);prev='mh'
 for i in range(4):
  x=1000+i*350;b.fn(f'eq{i}',K+'EqualEqual_IntInt',x,800,B=i);b.link('index','ScrewGripIndex',f'eq{i}','A');b.fn(f'w{i}',K+'SelectFloat',x,1000,B=0);b.link(f'eq{i}','ReturnValue',f'w{i}','bPickA');b.link('ease','ReturnValue',f'w{i}','A')
  v=f'RightGrip_Screwdriver{i}';b.set(f's{i}',v,x,0,MH);b.link('mh','AsABP Fo APlayer MH',f's{i}','self');b.link(f'w{i}','ReturnValue',f's{i}',v);b.chain(prev,f's{i}');prev=f's{i}'
 b.get('release','ScrewRelease',2400,800);b.fn('opening',K+'Multiply_DoubleDouble',2700,800);b.link('release','ScrewRelease','opening','A');b.link('ease','ReturnValue','opening','B');b.set('open','ScrewReleaseWeight',2400,0,MH);b.link('opening','ReturnValue','open','ScrewReleaseWeight');b.link('mh','AsABP Fo APlayer MH','open','self');b.chain(prev,'open')
 b.comment('Ease native screwdriver stance',[o['ref'] for o in b.ops if o['op']=='add_node']);b.run()

def hooks():
 n,edges=inspect(P,'EventGraph')
 if not any(v['title']=='UpdateScrewGrip' for v in n):
  old=find(n,'UpdateGrip');tick=find(n,'Event Tick');assert not any(x['from_node']==old and x['from_pin']=='then' for x in edges)
  b=Batch(P,'EventGraph');b.fn('screw',PC+':UpdateScrewGrip',300,0);b.link(old,'then','screw','execute');b.link(tick,'DeltaSeconds','screw','Dt');b.run()
 n,edges=inspect(P,'SetToolHandRotation')
 if not any(v['title']=='Set ScrewGripTime' for v in n):
  frame=next(v['node_id'] for v in n if v['title']=='MakeTransform' and any(x['to_node']==v['node_id'] and x['from_pin']=='ToolGripWorld' for x in edges))
  # Only the held-tool branch; the key's separate writer is left alone.
  compose=next(x['to_node'] for x in edges if x['from_node']==frame and x['to_pin']=='B')
  broken=next(x['to_node'] for x in edges if x['from_node']==compose and x['to_pin']=='InTransform')
  target=next(x['to_node'] for x in edges if x['from_node']==broken and x['to_pin']=='ToolHandTarget')
  elbow=next(x['to_node'] for x in edges if x['from_node']==target and x['from_pin']=='then')
  old=next(x for x in edges if x['to_node']==elbow and x['to_pin']=='ToolElbowTarget')
  turn=json.load(open('P:/FoA/Saved/AnimShots/screwdriver_screw0_turn.json'))
  b=Batch(P,'SetToolHandRotation');b.cut(old['from_node'],old['from_pin'],elbow,'ToolElbowTarget')
  b.fn('along',K+'GreaterGreater_VectorRotator',4000,2000,A=vec(turn['hand_direction_local']));b.link(broken,'Rotation','along','B')
  b.fn('axis',ACT+'GetActorForwardVector',4000,2200);b.fn('bisect',K+'Add_VectorVector',4300,2000);b.link('along','ReturnValue','bisect','A');b.link('axis','ReturnValue','bisect','B')
  b.fn('normal',K+'Normal',4600,2000);b.link('bisect','ReturnValue','normal','A');b.fn('forearm',K+'Multiply_VectorFloat',4900,2000,B=-turn['lower_length_cm']);b.link('normal','ReturnValue','forearm','A')
  b.fn('world',K+'Add_VectorVector',5200,2000);b.link(broken,'Location','world','A');b.link('forearm','ReturnValue','world','B');b.link('world','ReturnValue',elbow,'ToolElbowTarget')
  def upstream(node,pin):return next(x['from_node'] for x in edges if x['to_node']==node and x['to_pin']==pin)
  rot=upstream(frame,'Rotation');twistrot=upstream(rot,'A');twist=upstream(twistrot,'Roll');netdeg=upstream(twist,'A');net=upstream(netdeg,'A')
  mh=upstream(target,'self');start=next(x for x in edges if x['to_node']==target and x['to_pin']=='execute')
  fingers=find(n,'Set GripWeight');closed=upstream(fingers,'GripWeight')
  b.cut(start['from_node'],start['from_pin'],target,'execute');b.set('time','ScrewGripTime',4800,-800,MH);b.link(mh,'AsABP Fo APlayer MH','time','self');b.link(net,'ReturnValue','time','ScrewGripTime')
  b.fn('release',K+'Subtract_DoubleDouble',4800,-500,A=1);b.link(closed,'ReturnValue','release','B');b.set('save_release','ScrewRelease',5100,-800);b.link('release','ReturnValue','save_release','ScrewRelease')
  b.link(start['from_node'],start['from_pin'],'time','execute');b.chain('time','save_release');b.link('save_release','then',target,'execute')
  b.comment('Follow the ratchet stroke',['along','axis','bisect','normal','forearm','world','time','release','save_release']);b.run()
 n,edges=inspect(DOOR,'RefreshDoorTool')
 if not any(v['title']=='ApplyScrewGrip' for v in n):
  target=find(n,'SetToolHandTarget');old=next(x for x in edges if x['to_node']==target and x['to_pin']=='execute');pawn=next(x for x in edges if x['to_node']==target and x['to_pin']=='self');weight=next(x for x in edges if x['to_node']==target and x['to_pin']=='Weight')
  contact=find(n,'Get ToolContact');world=next(x['to_node'] for x in edges if x['from_node']==contact and x['to_pin']=='self' and next(v for v in n if v['node_id']==x['to_node'])['title']=='Get World Location')
  index=next(v['node_id'] for v in n if v['title']=='Get ToolStepIndex')
  b=Batch(DOOR,'RefreshDoorTool');b.cut(old['from_node'],old['from_pin'],target,'execute');b.fn('screw',PC+':ApplyScrewGrip',4500,-600);b.link(pawn['from_node'],pawn['from_pin'],'screw','self');b.link(weight['from_node'],weight['from_pin'],'screw','Weight');b.link(world,'ReturnValue','screw','TipWorld');b.link(index,'ToolStepIndex','screw','Index');b.link(old['from_node'],old['from_pin'],'screw','execute');b.link('screw','then',target,'execute');b.comment('Place native screwdriver',['screw']);b.run()
if __name__=='__main__':{'ensure':ensure,'apply':apply,'update':update,'hooks':hooks}[sys.argv[1]]()
