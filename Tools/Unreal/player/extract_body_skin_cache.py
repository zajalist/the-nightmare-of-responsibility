"""Light read of existing binary FBX into a numeric leg/hip skin cache; no UE/Blender/export process."""
import struct,zlib,json,itertools,time,os
from pathlib import Path
import numpy as np
START=time.monotonic();SRC=Path(os.environ.get('FOA_BODY_FBX','P:/FoA-Assets/character/metahuman/MHC_Protagonist_Body.fbx'));OUT=Path('P:/FoA/Saved/CharacterShots/body_leg_skin_cache')
FULL=os.environ.get('FOA_FULL_BODY_CACHE')=='1'
if FULL:OUT=OUT.with_name('body_full_skin_cache')
if os.environ.get('FOA_SKIN_CACHE_OUT'):OUT=Path(os.environ['FOA_SKIN_CACHE_OUT'])
f=SRC.open('rb');assert f.read(23)==b'Kaydara FBX Binary  \x00\x1a\x00';version=struct.unpack('<I',f.read(4))[0];assert version<7500
scalar={'Y':'h','C':'?','I':'i','F':'f','D':'d','L':'q'};arrays={'f':'<f4','d':'<f8','i':'<i4','l':'<i8','b':'u1','c':'u1'}
def prop():
 t=f.read(1).decode()
 if t in scalar:
  fmt='<'+scalar[t];return struct.unpack(fmt,f.read(struct.calcsize(fmt)))[0]
 if t in ('S','R'):
  n=struct.unpack('<I',f.read(4))[0];b=f.read(n);return b.decode('utf8',errors='replace')if t=='S'else b
 assert t in arrays,t
 n,enc,size=struct.unpack('<III',f.read(12));raw=f.read(size)
 if enc:raw=zlib.decompress(raw)
 return np.frombuffer(raw,dtype=arrays[t],count=n)
def node():
 end,n,length,size=struct.unpack('<IIIB',f.read(13))
 if end==0:return None
 name=f.read(size).decode();p=[prop()for _ in range(n)];kids=[]
 while f.tell()<end-13:
  child=node()
  if child:kids.append(child)
 f.seek(end);return {'type':name,'p':p,'c':kids}
top=[]
while True:
 n=node()
 if n is None:break
 top.append(n)
f.close()
objects=next(n['c']for n in top if n['type']=='Objects');connections=next(n['c']for n in top if n['type']=='Connections')
byid={n['p'][0]:n for n in objects};pairs=[(n['p'][1],n['p'][2])for n in connections if n['type']=='C'and n['p'][0]=='OO']
def child(n,name):return next(k['p'][0]for k in n['c']if k['type']==name)
geo=max((n for n in objects if n['type']=='Geometry'and n['p'][2]=='Mesh'),key=lambda n:len(child(n,'Vertices')))
vertices=child(geo,'Vertices').reshape(-1,3).astype(float);N=len(vertices)
skins={a for a,b in pairs if b==geo['p'][0]and byid.get(a,{}).get('type')=='Deformer'}
clusters=[byid[a]for a,b in pairs if b in skins and byid.get(a,{}).get('p',[None,None,None])[2]=='Cluster']
ref_record=json.loads(Path(os.environ.get('FOA_BODY_REF_JSON','P:/FoA/Saved/CharacterShots/ref_pose_after.json')).read_text())[os.environ.get('FOA_BODY_REF_LABEL','original_body')]
refs=ref_record['bones']
def mat(t):
 x,y,z,w=t['rotation'];sx,sy,sz=t['scale'];q=np.array([[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)],[2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)],[2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)]])
 m=np.eye(4);m[:3,:3]=q@np.diag((sx,sy,sz));m[:3,3]=t.get('position',t.get('translation'));return m
refm={}
def reference(n):
 if n not in refm:
  b=refs[n];refm[n]=reference(b['parent'])@mat(b)if b['parent']!='None'else mat(b)
 return refm[n]
for n in refs:reference(n)
rawclusters=[]
for c in clusters:
 if not {'Indexes','Weights'}<={k['type']for k in c['c']}:continue
 model=next(byid[a]for a,b in pairs if b==c['p'][0]and byid.get(a,{}).get('type')=='Model')
 name=model['p'][1].split('\x00')[0].split('::')[-1]
 assert name in refs,name
 link=child(c,'TransformLink').reshape(4,4).T
 rawclusters.append((name,child(c,'Indexes'),child(c,'Weights'),link,child(c,'Transform').reshape(4,4).T))
samples=[(link[:3,3],refm[n][:3,3])for n,idx,w,link,m in rawclusters]
a=np.array([v[0]for v in samples]);b=np.array([v[1]for v in samples]);best=None
for perm in itertools.permutations(range(3)):
 for signs in itertools.product((-1,1),repeat=3):
  for scale in (1,.01,100):
   A=np.eye(3)[list(perm)]*np.array(signs)[:,None]*scale
   err=np.max(np.linalg.norm(a@A.T-b,axis=1))
   if best is None or err<best[0]:best=(err,A)
error,A=best;assert error<.01,('Bone coordinate contract mismatch cm',error,A.tolist())
meshbind=rawclusters[0][3]@rawclusters[0][4]
assert max(np.max(np.abs(c[3]@c[4]-meshbind))for c in rawclusters)<1e-4, "Inconsistent FBX bind transform convention"
vworld=(np.c_[vertices,np.ones(N)]@meshbind.T)[:,:3]@A.T
names=list(refs);indices={n:i for i,n in enumerate(names)};weights=[[]for _ in range(N)]
for n,idx,w,link,m in rawclusters:
 for i,value in zip(idx,w):
  if value>1e-7:weights[int(i)].append((indices[n],float(value)))
legbones={i for n,i in indices.items()if n=='pelvis'or n.startswith(('thigh_','calf_','foot_','ball_','ankle_'))}
keep=np.array([bool(row) if FULL else sum(w for b,w in row if b in legbones)>.2 for row in weights]);ids=np.flatnonzero(keep);remap=np.full(N,-1);remap[ids]=np.arange(len(ids))
triangles=[];poly=[]
for i in child(geo,'PolygonVertexIndex'):
 poly.append(-int(i)-1 if i<0 else int(i))
 if i<0:
  if all(keep[v]for v in poly):
   triangles.extend((remap[poly[0]],remap[poly[j]],remap[poly[j+1]])for j in range(1,len(poly)-1))
  poly=[]
offsets=[0];bones=[];values=[]
for i in ids:
 row=weights[i];total=sum(w for _,w in row);assert abs(total-1)<.001,(i,total)
 for bone,w in row:bones.append(bone);values.append(w/total)
 offsets.append(len(bones))
np.savez_compressed(str(OUT)+'.npz',vertices_cm=vworld[ids].astype('f4'),source_vertex_ids=ids.astype('i4'),triangles=np.array(triangles,dtype='i4'),
 vertex_offsets=np.array(offsets,dtype='i4'),weight_bones=np.array(bones,dtype='i4'),weight_values=np.array(values,dtype='f4'),bone_names=np.array(names),
 reference_matrices=np.array([refm[n]for n in names],dtype='f8'),parent_indices=np.array([indices.get(refs[n]['parent'],-1)for n in names],dtype='i4'))
report={'source':str(SRC),'source_mesh':ref_record['mesh'],'fbx_version':version,'space':'UE Body component bind coordinates, centimetres; already transformed from FBX',
 'fbx_to_ue_matrix':A.tolist(),'max_bone_bind_error_cm':float(error),'vertices':len(ids),'triangles':len(triangles),'bones':len(names),
 'elapsed_s':time.monotonic()-START,'skinning':'sum(weight * evaluated_component_bone_matrix * inverse(reference_matrices[bone]) * bind_vertex_cm). Then apply Body.world for world points.',
 'inactive':'If an evaluated nonroot helper is at component origin while its reference is not, derive pose from nearest active ancestor reference relation. This is a fallback, not a measured corrective.',
 'selection':'All weighted body vertices; original dimensions unchanged.' if FULL else 'Vertices with >0.2 pelvis/thigh/calf/foot/ball/ankle weight; original body dimensions unchanged.'}
OUT.with_suffix('.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
