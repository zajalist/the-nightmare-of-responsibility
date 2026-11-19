"""Staged physical clothing clues on the existing takeover actor; native asset edits only.

Requires the read-only clothing_clue_surfaces.json. No timers, cameras, collision,
new materials, or changes to the user's furniture. Existing meshes are reused.
"""
import json,math,sys,os
from pathlib import Path
sys.path.insert(0,'P:/FoA/Tools/Splats')
from build_room_takeover import P,C,K,SC,call,h,Batch,inspect,find
OUT=Path('P:/FoA/Saved/Integration')
CYL='/Engine/BasicShapes/Cylinder'
PLANE='/Engine/BasicShapes/Plane'
PALE='/Game/FoA/Materials/MI_Trim_Paint'
CLOTH='/Game/FoA/Characters/Teen/Cloth/MI_Teen_Polo'
DARK='/Game/FoA/Materials/MI_DarkSand_Black'
CRUMBS='/Game/FoA/VFX/Splats/Meshes/SM_SandCrumbs_Path/SM_SandCrumbs_Path/StaticMeshes/SM_SandCrumbs_Path'
CRUMBMAT='/Game/FoA/VFX/Splats/Instances/MI_Sand_Crumbs'
SPLINTER='/Game/FoA/Props/Clues/SM_WardrobeSplinter'
CABINET='/Game/FoA/Props/GothicCabinet_01/GothicCabinet_01_1k/Materials/GothicCabinet_01'

def layout(data):
 parts=[];marks={}
 def part(name,group,mesh,loc,rot,size,mat=None):
  parts.append(dict(name=name,group=group,mesh=mesh,loc=loc,rot=rot,size=size,mat=mat))
 def strand(name,group,points,radius=.075):
  for i,(a,b) in enumerate(zip(points,points[1:])):
   delta=[b[k]-a[k] for k in range(3)];length=math.sqrt(sum(v*v for v in delta))
   # UE positive pitch tilts local Z toward negative X; use negative pitch
   # so each cylinder's axis follows this segment, including the hanging end.
   pitch=-math.degrees(math.atan2(math.hypot(*delta[:2]),delta[2]))
   yaw=math.degrees(math.atan2(delta[1],delta[0]))
   part(name+str(i),group,CYL,[(a[k]+b[k])/2 for k in range(3)],(pitch,yaw,0),(radius/50,radius/50,length/100),CLOTH)
 low=data['Wardrobe']['fallen_min'];high=data['Wardrobe']['fallen_max']
 # Short fine thread catches on a raised splinter, then falls over the cabinet edge.
 x,y,z=low[0]+15,low[1]+35,high[2]+.16
 part('ClueWoodSplinter',1,SPLINTER,(low[0]+8,y,z-.14),(0,0,0),(1,1,1),CABINET)
 points=[]
 for i in range(13):
  t=i/12;px=x-18*t
  snag=math.exp(-((px-(low[0]+5.3))/1.8)**2)
  lift=.68*snag
  points.append((px,y+.7*math.sin(t*math.pi*1.2)*(1-snag),z+lift-2.0*max(0,(t-.78)/.22)**2))
 strand('ClueThread',1,points,.035)
 strand('ClueFray',1,[points[6],(points[6][0]-1,points[6][1]+.65,points[6][2]-.15),(points[6][0]-2.2,points[6][1]+.8,points[6][2]-.4)],.022)
 focus=(low[0]+7,y,z+.15)
 marks['ClueFocusWardrobe']=focus;marks['ClueViewWardrobe']=(focus[0]-54,focus[1]-40,focus[2]+48)
 desk=data['Desk']['components'][0];lo,hi=desk['min'],desk['max']
 x,y,z=hi[0]-18,(lo[1]+hi[1])/2,hi[2]+.18
 # Two plain paper sheets are owned clue props, with the button peeking past an edge.
 part('CluePaperBack',2,PLANE,(x-5,y+3,z),(0,-7,0),(.20,.145,1),PALE)
 part('CluePaperFront',2,PLANE,(x-3,y+2,z+.06),(0,7,0),(.19,.135,1),PALE)
 button=(x+5.8,y-3.5,z+.22)
 part('ClueButton',2,CYL,button,(0,0,0),(.028,.028,.0035),PALE)
 for i,(dx,dy) in enumerate([(-.4,-.4),(.4,-.4),(-.4,.4),(.4,.4)]):
  part('ClueButtonHole'+str(i),2,CYL,(button[0]+dx,button[1]+dy,button[2]+.18),(0,0,0),(.004,.004,.00025),DARK)
 # Existing authored sand grain clusters form short scuffs toward the bed.
 part('ClueDeskDust',2,CRUMBS,(x+3,y-6,z+.08),(0,-30,0),(.023,.018,.08),CRUMBMAT)
 part('ClueDeskTrail',2,CRUMBS,(hi[0]+26,y-40,.3),(0,-30,0),(.12,.09,.25),CRUMBMAT)
 focus=(button[0],button[1],button[2])
 marks['ClueFocusDesk']=focus;marks['ClueViewDesk']=(focus[0]+42,focus[1]-32,focus[2]+40)
 bed=data['Bed']['components'][0];lo,hi=bed['min'],bed['max']
 src=data['Shirt_T7']['components'][0]
 center=((lo[0]+hi[0])/2,hi[1]-17,0)
 # Lay the real shirt on its back: its original 14 cm depth becomes the vertical extent.
 # The mesh is centered on the original actor, and the existing yaw is -90 degrees.
 depth=src['max'][0]-src['min'][0]
 scale=(.62,.62,.62)
 loc=[center[0],center[1],.35+depth*.31]
 part('ClueSnaggedShirt',3,src['mesh'],loc,(0,-90,90),scale,None)
 part('ClueBedDust',3,CRUMBS,(center[0]-15,hi[1]+8,.3),(0,-100,0),(.10,.07,.2),CRUMBMAT)
 focus=(center[0],center[1],15)
 marks['ClueFocusBed']=focus;marks['ClueViewBed']=(focus[0]-25,hi[1]+72,32)
 return parts,marks

def build():
 assert not call('editor_get_state')['pie_running'],'PIE is active'
 data=json.loads((OUT/'clothing_clue_surfaces.json').read_text());parts,marks=layout(data)
 owner=h.agent_id() or 'room-takeover'
 lease=h.lease_acquire(owner,['asset:'+P],ttl_s=180,wait_s=20)
 try:
  assert not call('editor_get_state')['pie_running'],'PIE started while waiting'
  if '--thread-rotations' in sys.argv:
   for item in parts:
    if item['group']==1:call('object_set_property',path=C+':'+item['name']+'_GEN_VARIABLE',properties={'RelativeRotation':dict(zip(('Pitch','Yaw','Roll'),item['rot']))})
   result=call('blueprint_compile',path=P);call('asset_save',asset_paths=[P])
   proof=json.loads((OUT/'clothing_clues_applied.json').read_text());proof['parts']=parts;proof['compile']=result
   (OUT/'clothing_clues_applied.json').write_text(json.dumps(proof,indent=1))
   print('Thread segment axes corrected and saved',result);return
  info=call('blueprint_get_info',path=P);have={v['name'] for v in info['components']}
  for item in parts:
   n=item['name']
   if n not in have:call('blueprint_add_component',path=P,component_class_path='/Script/Engine.StaticMeshComponent',component_name=n)
   props={'StaticMesh':item['mesh'],'RelativeLocation':dict(zip('XYZ',item['loc'])),
    'RelativeRotation':dict(zip(('Pitch','Yaw','Roll'),item['rot'])),'RelativeScale3D':dict(zip('XYZ',item['size'])),
    'bVisible':False,'CastShadow':True,'Mobility':'Movable','bGenerateOverlapEvents':False,
    'BodyInstance':'(CollisionProfileName="NoCollision",CollisionEnabled=NoCollision)'}
   if item['mat']:props['OverrideMaterials']=[item['mat']]
   call('object_set_property',path=C+':'+n+'_GEN_VARIABLE',properties=props)
  for n,pos in marks.items():
   if n not in have:call('blueprint_add_component',path=P,component_class_path='/Script/Engine.SceneComponent',component_name=n)
   call('object_set_property',path=C+':'+n+'_GEN_VARIABLE',properties={'RelativeLocation':dict(zip('XYZ',pos))})
  fn='ApplyClothingClues'
  if fn not in info['functions']:call('blueprint_add_function',path=P,function_name=fn)
  ns,_=inspect(P,fn);entry=find(ns,fn);b=Batch(P,fn)
  old=[n['node_id'] for n in ns if n['node_id']!=entry]
  if old:b.ops.append(dict(op='remove',node_ids=old))
  b.get('stage','Stage',0,350)
  for group in (1,2,3):
   b.fn('ready'+str(group),K+'GreaterEqual_IntInt',300,200+group*200,B=group)
   b.link('stage','Stage','ready'+str(group),'A')
  b.fn('notfreed',K+'Less_IntInt',600,850,B=5);b.link('stage','Stage','notfreed','A')
  b.fn('snag',K+'BooleanAND',900,700);b.link('ready3','ReturnValue','snag','A');b.link('notfreed','ReturnValue','snag','B')
  prev=entry
  for group in (1,2,3):
   refs=[]
   for i,item in enumerate(p for p in parts if p['group']==group):
    n=item['name'];x=1400+(i%4)*360;y=(group-1)*1500+(i//4)*350
    b.get(n,n,x,y+180);b.fn('show'+n,SC+'SetVisibility',x,y)
    b.link(n,n,'show'+n,'self');b.link('snag' if group==3 else 'ready'+str(group),'ReturnValue','show'+n,'bNewVisibility')
    b.chain(prev,'show'+n);prev='show'+n;refs.extend([n,prev])
   b.comment({1:'Thread in the wood',2:'Button and disturbed dust',3:'Shirt beneath the frame'}[group],refs)
  b.comment('Only after discovery',['stage','ready1','ready2','ready3','notfreed','snag']);b.run()
  # SetStage advances once; Reset zeroes Stage before its existing ApplyStage call.
  for graph,title in [('SetStage','Set Stage'),('Reset','Set Stage')]:
   ns,es=inspect(P,graph)
   if any(n['title']==fn for n in ns):continue
   node=find(ns,title);edge=next(e for e in es if e['from_node']==node and e['from_pin']=='then')
   b=Batch(P,graph);b.fn('clues',C+':'+fn,1800,-650)
   b.cut(node,'then',edge['to_node'],edge['to_pin']);b.chain(node,'clues');b.link('clues','then',edge['to_node'],edge['to_pin'])
   b.comment('Reveal physical evidence',['clues']);b.run()
  compiled=call('blueprint_compile',path=P);call('asset_save',asset_paths=[P])
  ns,es=inspect(P,fn)
  (OUT/'clothing_clues_applied.json').write_text(json.dumps({'compile':compiled,'parts':parts,'markers':marks,'nodes':ns,'edges':es},indent=1))
  print('Physical clue components saved; placement and runtime visibility still need visual proof.')
 finally:h.release(owner,lease)

if __name__=='__main__':build()
