from pathlib import Path
setup=Path('Tools/Unreal/ui/fit_phone_support.py').read_text().split('report={}')[0];exec(setup)
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
axes={}
for digit in angles:
 axes[digit]=[]
 for j in (1,2,3):
  n=f'{digit}_0{j}_r';par=names[parent[idx[n]]]
  def q(k):return R.from_quat(retarget[k][par]['q']).inv()*R.from_quat(retarget[k][n]['q'])
  a=(q('neutral').inv()*q('relaxed')).as_rotvec();axes[digit].append(a/np.linalg.norm(a))
handids=[idx[n] for n in names if n.endswith('_r') and n.startswith(('hand','thumb','index','middle','ring','pinky'))]
hw=np.zeros(len(verts));np.add.at(hw,iv,c['weight_values']*np.isin(c['weight_bones'],handids));keep=hw>.6;tris=c['triangles'][np.all(keep[c['triangles']],axis=1)]
def geom(curls):
 posed=bm.copy()
 for digit,new in curls.items():
  for j,(axis,prior,now) in enumerate(zip(axes[digit],angles[digit],new),1):
   i=idx[f'{digit}_0{j}_r'];rot=np.eye(4);rot[:3,:3]=R.from_rotvec(axis*np.radians(now-prior)).as_matrix();posed[i]=posed[parent[i]]@local[i]@rot
 deform=posed@inverse;v=np.zeros((len(verts),4));np.add.at(v,iv,np.einsum('nij,nj->ni',deform[c['weight_bones']],verts[iv])*c['weight_values'][:,None]);return (v@case.T)[:,:3]
variants={'original':angles,'rejected':{d:r['curls'] for d,r in json.loads((root/'phone_support_rejected_contact_fit/phone_support_candidate.json').read_text())['digits'].items()},'consistent':{'middle':[40,45,27],'ring':[45,50,30],'pinky':[50,55,33]}}
fig,axs=plt.subplots(1,3,figsize=(15,7));eye=np.array([-14,20,24]);target=np.array([-8,2,-2]);z=(eye-target)/np.linalg.norm(eye-target);x=np.cross([1,0,0],z);x/=np.linalg.norm(x);y=np.cross(z,x);view=np.array([x,y,z])
for ax,(label,curls) in zip(axs,variants.items()):
 v=geom(curls);p=v@view.T;t=p[tris];depth=t[:,:,2].mean(1);normal=np.cross(v[tris][:,1]-v[tris][:,0],v[tris][:,2]-v[tris][:,0]);normal/=np.maximum(np.linalg.norm(normal,axis=1)[:,None],1e-9);shade=.3+.6*np.abs(normal@z);order=np.argsort(depth)
 ax.add_collection(PolyCollection(t[order,:,:2],facecolors=np.stack([shade]*3,axis=1)[order],edgecolors='none'))
 ax.autoscale();ax.set_aspect('equal');ax.set_title(label);ax.axis('off')
fig.tight_layout();fig.savefig(root/'phone_support_offline_compare.png',dpi=150)
