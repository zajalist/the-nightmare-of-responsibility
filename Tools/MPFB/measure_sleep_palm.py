"""Read-only shirt/palm contact reconstruction from a captured Teen component pose."""
import json,sys
from pathlib import Path
import bpy
import numpy as np
from mathutils import Matrix
sys.path.insert(0,'P:/FoA/Tools/Unreal/player')
from sleep_skin_contact import matrix

args=sys.argv[sys.argv.index('--')+1:]
pose_path=Path(args[0]);pose=json.loads(pose_path.read_text())
rig=next(o for o in bpy.data.objects if o.type=='ARMATURE')
C=np.diag([1,-1,1,1])
for row in pose['bones']:
    if row['name'] not in rig.pose.bones:continue
    tr=C@matrix(row['position'],row['rotation'],row['scale'])@C
    tr[:3,3]/=100
    rig.pose.bones[row['name']].matrix=Matrix(tr.tolist())
    bpy.context.view_layer.update()
world=pose['world'];world_m=matrix(world['position'],world['rotation'],world['scale'])

def mesh_points(obj):
    ev=obj.evaluated_get(bpy.context.evaluated_depsgraph_get());me=ev.to_mesh()
    pts=np.array([(obj.matrix_world@v.co)[:] for v in me.vertices])*[100,-100,100]
    pts=(np.column_stack((pts,np.ones(len(pts))))@world_m.T)[:,:3]
    me.calc_loop_triangles();tris=np.array([t.vertices[:] for t in me.loop_triangles])
    ev.to_mesh_clear()
    return pts,tris

body=bpy.data.objects['Human']
for mod in body.modifiers:
    if mod.type in ('MASK','SUBSURF'):mod.show_viewport=False
bpy.context.view_layer.update()
body_pts,_=mesh_points(body)
landmark=json.loads(Path('P:/FoA/Saved/CharacterShots/mpfb/shirt_palm_diagnostic.json').read_text())['palms']['r']
palms=body_pts[landmark['vertices']]
shirt=next(o for o in bpy.data.objects if o.name.endswith('.foa_polo_layered'))
pts,tris=mesh_points(shirt);t=pts[tris]
gaps=[]
for p in palms:
    a=t[:,0,:2];v0=t[:,1,:2]-a;v1=t[:,2,:2]-a;v2=p[:2]-a
    den=v0[:,0]*v1[:,1]-v0[:,1]*v1[:,0]
    valid=abs(den)>1e-8
    u=np.zeros(len(t));v=u.copy()
    u[valid]=(v2[valid,0]*v1[valid,1]-v2[valid,1]*v1[valid,0])/den[valid]
    v[valid]=(v0[valid,0]*v2[valid,1]-v0[valid,1]*v2[valid,0])/den[valid]
    mask=valid&(u>=0)&(v>=0)&(u+v<=1)
    if not mask.any():continue
    z=t[mask,0,2]+u[mask]*(t[mask,1,2]-t[mask,0,2])+v[mask]*(t[mask,2,2]-t[mask,0,2])
    gaps.append(float(p[2]-z.max()))
assert len(gaps)>=10,('Palm does not overlap shirt',len(gaps))
out=dict(pose=str(pose_path),palm_centroid_cm=palms.mean(axis=0).tolist(),samples=len(gaps),
         prediction_only=bool(pose.get('prediction_only',False)),
         vertical_gap_cm_percentiles=np.percentile(gaps,[0,25,50,75,100]).tolist(),
         limitation='Captured bone skinning on source garment; excludes GPU wrinkle displacement.')
path=pose_path.with_name('sleep_palm_contact.json');path.write_text(json.dumps(out,indent=2));print('wrote',path,json.dumps(out))
