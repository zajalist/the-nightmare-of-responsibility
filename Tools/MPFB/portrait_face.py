"""Reversible face-only portrait variant, with clean neutral-light comparisons.
Run on foa_teen_hair.blend. Does not overwrite source MHM/blends or touch Unreal.
"""
import sys,json,hashlib,math
from pathlib import Path
import bpy,numpy as np
from mathutils import Vector
sys.path.insert(0,'P:/FoA/Tools/MPFB')
from export_ue import FaceService,ARKIT,bake_shape
from stage import stage,shoot

OUT=Path('P:/FoA/Saved/CharacterShots/mpfb/portrait_face');OUT.mkdir(parents=True,exist_ok=True)
DEST='P:/FoA-Assets/character/mpfb/teen/foa_teen_portrait_v1.blend'
rig=next(o for o in bpy.data.objects if o.type=='ARMATURE');body=bpy.data.objects['Human']
for p in rig.pose.bones:p.matrix_basis.identity()
bones_before=[(b.name,[list(row) for row in b.matrix_local]) for b in rig.data.bones]
if not any(k.name=='eyeBlinkLeft' for k in body.data.shape_keys.key_blocks):
    FaceService.load_targets(body,load_microsoft_visemes=False,load_arkit_faceunits=True)
    FaceService.interpolate_targets(body)
count=bake_shape(body);assert count==52,count
for o in rig.children:
    if o.type=='MESH' and o is not body and o.data.shape_keys and any(token in o.name.lower() for token in ('eye','tongue','teeth')):
        bake_shape(o)
for o in bpy.data.objects:
    if o.name.startswith('TMP_') or o.name=='Curves':o.hide_render=True
cards=bpy.data.objects.get('Human.short01')
if cards:cards.hide_render=True
groom=bpy.data.objects['basic_short_hair'];groom.hide_render=False
groom_points=np.empty(len(groom.data.points)*3,dtype=np.float32)
groom.data.points.foreach_get('position',groom_points)
groom_hash=hashlib.sha256(groom_points.tobytes()).hexdigest()
base=np.array([v.co[:] for v in body.data.vertices])
keys_before={k.name:np.array([v.co[:] for v in k.data])-base for k in body.data.shape_keys.key_blocks if k.name in ARKIT}
head_index=body.vertex_groups['head'].index
scalp_index=body.vertex_groups.get('FoA_scalp')
skin_index=body.vertex_groups['body'].index
eligible=np.zeros(len(base));scalp=np.zeros(len(base))
for v in body.data.vertices:
    w={g.group:g.weight for g in v.groups}
    eligible[v.index]=float(w.get(head_index,0)>.995 and w.get(skin_index,0)>0)
    if scalp_index:scalp[v.index]=float(w.get(scalp_index.index,0)>0)

cam=stage(res=(768,896));scene=bpy.context.scene
scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=32;scene.cycles.use_denoising=True
scene.render.threads_mode='FIXED';scene.render.threads=8
target=Vector((0,-.05,1.75))
for light,offset,power,size in [('key',(-.7,-1.0,.65),60,1.0),('fill',(.8,-.7,.2),35,1.2),('rim',(.4,.6,.5),45,.9)]:
    obj=bpy.data.objects[light];obj.location=target+Vector(offset);obj.data.energy=power;obj.data.size=size
    obj.rotation_euler=(target-obj.location).to_track_quat('-Z','Y').to_euler()
scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.18,.18,.18,1)
scene.world.node_tree.nodes['Background'].inputs[1].default_value=.3
for label,yaw in [('front',0),('profile',90),('threequarter',35)]:
    shoot(cam,target,.78,yaw,75,str(OUT/('before_'+label+'.png')))

def smooth(a,b,x):
    t=np.clip((x-a)/(b-a),0,1);return t*t*(3-2*t)

def displacement(points):
    x,y,z=points.T
    # Visible facial contour only: skull, eye sockets, ears and neck remain locked.
    face=smooth(.075,.125,-y)*smooth(1.615,1.645,z)*(1-smooth(1.728,1.748,z))
    cheek=np.exp(-((z-1.710)/.030)**2)
    jaw=np.exp(-((z-1.660)/.025)**2)
    chin=np.exp(-((z-1.642)/.018)**2)*np.exp(-(x/.035)**2)
    nose=np.exp(-((z-1.729)/.016)**2)*np.exp(-(x/.020)**2)*smooth(.165,.185,-y)
    delta=np.zeros_like(points)
    delta[:,0]=-x*face*(.09*cheek+.15*jaw+.06*chin)
    delta[:,1]=face*(.0035*cheek*np.minimum(abs(x)/.035,1)-.0035*chin-.001*nose)
    delta[:,2]=face*(-.0015*chin-.001*nose)
    return delta

delta=displacement(base)*eligible[:,None]*(1-scalp[:,None])
for key in body.data.shape_keys.key_blocks:
    coords=np.array([v.co[:] for v in key.data]);key.data.foreach_set('co',(coords+delta).astype(np.float32).ravel())
body.data.vertices.foreach_set('co',(base+delta).astype(np.float32).ravel());body.data.update()
# Interior mouth geometry follows the same lower-face adjustment, retaining its existing expression deltas.
for obj in rig.children:
    if obj.type!='MESH' or not any(t in obj.name.lower() for t in ('tongue','teeth')):continue
    points=np.array([v.co[:] for v in obj.data.vertices]);shift=displacement(points)
    if obj.data.shape_keys:
        for key in obj.data.shape_keys.key_blocks:
            coords=np.array([v.co[:] for v in key.data]);key.data.foreach_set('co',(coords+shift).astype(np.float32).ravel())
    obj.data.vertices.foreach_set('co',(points+shift).astype(np.float32).ravel());obj.data.update()
bpy.context.view_layer.update()
after=np.array([v.co[:] for v in body.data.vertices])
locked=(eligible==0)|(scalp>0)|(base[:,2]>=1.748)|(base[:,2]<=1.615)
assert np.max(np.abs(after[locked]-base[locked]))==0,'Protected body/skull/scalp/neck moved'
errors=[]
for key in body.data.shape_keys.key_blocks:
    if key.name in keys_before:
        d=np.array([v.co[:] for v in key.data])-after
        errors.append(float(np.max(np.abs(d-keys_before[key.name]))))
assert max(errors)<3e-7,errors
assert bones_before==[(b.name,[list(row) for row in b.matrix_local]) for b in rig.data.bones]
verify=np.empty_like(groom_points);groom.data.points.foreach_get('position',verify)
assert hashlib.sha256(verify.tobytes()).hexdigest()==groom_hash
report={'source':'foa_teen_hair.blend','variant':DEST,'morph_count':count,'morph_delta_max_error_m':max(errors),
        'affected_skin_vertices':int(np.count_nonzero(np.linalg.norm(delta,axis=1)>1e-8)),
        'maximum_shift_mm':float(np.linalg.norm(delta,axis=1).max()*1000),'protected_vertices':int(locked.sum()),
        'protected_geometry_max_error':0,'bone_transforms_unchanged':True,'groom_sha256':groom_hash,
        'notes':'Visible contour interpretation only; no ancestry/body macro changes. Existing eye/lid shapes and cranial pillow/groom fit unchanged.'}
(OUT/'validation.json').write_text(json.dumps(report,indent=2))
for label,yaw in [('front',0),('profile',90),('threequarter',35)]:
    shoot(cam,target,.78,yaw,75,str(OUT/('after_'+label+'.png')))
for o in list(bpy.data.objects):
    if o.type in ('LIGHT','CAMERA'):bpy.data.objects.remove(o,do_unlink=True)
bpy.ops.wm.save_as_mainfile(filepath=DEST)
print('PORTRAIT_VARIANT',json.dumps(report))
