"""Read-only shoulder fit/weight audit of the currently exported chest variant. No rendering or saves."""
import json,sys,os
from pathlib import Path
import bpy,numpy as np
from mathutils import Matrix,Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0,'P:/FoA/Tools/MPFB')
from poses import reset,chain,DOWN,v
sys.path.insert(0,'P:/FoA/Tools/Unreal/player')
from sleep_skin_contact import matrix
outdir=Path(os.environ.get('FOA_SHOULDER_OUTPUT','P:/FoA/Saved/Integration/cinematic_audit'));outdir.mkdir(parents=True,exist_ok=True)
rig=next(o for o in bpy.data.objects if o.type=='ARMATURE')
body=bpy.data.objects['Human'];shirt=next(o for o in bpy.data.objects if o.name.endswith('.foa_polo_layered'))
for obj in (body,shirt):
    for mod in obj.modifiers:
        if mod.type in ('MASK','SUBSURF'):
            mod.show_viewport=False
            mod.show_render=False
rest=np.array([x.co[:] for x in shirt.data.vertices])
shoulder=np.flatnonzero((rest[:,2]>1.44)&(rest[:,2]<1.64)&(abs(rest[:,0])>.07)&(abs(rest[:,0])<.29))
if os.environ.get('FOA_FIT_REGION')=='underarm':
    shoulder=np.flatnonzero((rest[:,2]>1.28)&(rest[:,2]<1.46)&(abs(rest[:,0])>.13)&(abs(rest[:,0])<.32))
skin=body.vertex_groups['body'].index
valid={x.index for x in body.data.vertices if any(g.group==skin and g.weight>0 for g in x.groups)}
tri=[tuple(f.vertices) for f in body.data.polygons if all(i in valid for i in f.vertices)]
deform={b.name for b in rig.data.bones if b.use_deform}
def weights(obj,index):return {obj.vertex_groups[g.group].name:g.weight for g in obj.data.vertices[index].groups if obj.vertex_groups[g.group].name in deform}
report={'source':bpy.data.filepath,'vertices':len(rest),'shoulder_vertices':len(shoulder),'poses':{}}
for name in ('rest','idle','reach','battle_command','battle_reach'):
    reset(rig)
    if name in ('idle','reach'):chain(rig,DOWN)
    if name=='reach':chain(rig,(('upperarm_l',v(.10,-1,-.05)),('lowerarm_l',v(.05,-1,0))))
    if name.startswith('battle_'):
        record=json.loads(Path('P:/FoA/Saved/Integration/cinematic_audit/live_'+name+'.json').read_text())['components']['Body']
        ref=np.load('P:/FoA/Saved/WakeUp/teen_body_full_skin_cache.npz')
        references=dict(zip(ref['bone_names'].tolist(),ref['reference_matrices']))
        xf=lambda t:matrix(t['position'],t['rotation'],t['scale'])
        component_inverse=np.linalg.inv(xf(record['world']));conversion=np.diag((100,-100,100,1))
        override=os.environ.get('FOA_SHOULDER_POSE') if name=='battle_command' else None
        if override:
            snapshot=json.loads(Path(override).read_text())
            if 'components' in snapshot:
                record=snapshot['components']['Body'];component_inverse=np.linalg.inv(xf(record['world']))
            else:
                component_inverse=np.eye(4);record={'bones':{b['name']:b for b in snapshot['bones']}}
            report['pose_override']=override
        for bone in rig.pose.bones:
            key='root' if bone.name=='Root' else bone.name
            if key not in references:continue
            deform_matrix=component_inverse@xf(record['bones'][key])@np.linalg.inv(references[key])
            bone.matrix=Matrix((np.linalg.inv(conversion)@deform_matrix@conversion).tolist())@bone.bone.matrix_local
            bpy.context.view_layer.update()
    bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get()
    eb=body.evaluated_get(dg);es=shirt.evaluated_get(dg);bm=eb.to_mesh();sm=es.to_mesh()
    assert len(sm.vertices)==len(rest)
    tree=BVHTree.FromPolygons([x.co[:] for x in bm.vertices],tri);rows=[]
    for i in shoulder:
        p=sm.vertices[int(i)].co;point,normal,index,d=tree.find_nearest(p)
        if point is None:continue
        face=tri[index];nearest=min(face,key=lambda j:(bm.vertices[j].co-point).length)
        a=weights(shirt,int(i));b=weights(body,nearest)
        rows.append({'vertex':int(i),'rest_cm':(rest[i]*100).tolist(),'pose_cm':[float(x*100) for x in p],
            'clearance_mm':float((p-point).dot(normal)*1000),'distance_mm':float(d*1000),
            'body_vertex':nearest,'weight_l1':sum(abs(a.get(k,0)-b.get(k,0)) for k in a.keys()|b.keys()),'shirt_weights':a,'body_weights':b})
    gaps=[r['clearance_mm'] for r in rows]
    report['poses'][name]={'clearance_mm_percentiles':np.percentile(gaps,[0,10,50,90,100]).tolist(),
        'inward_over_2mm':sum(g< -2 for g in gaps),'outward_over_20mm':sum(g>20 for g in gaps),'rows':rows}
    if name=='battle_command' and os.environ.get('FOA_SHOULDER_RENDER')=='1':
        from stage import stage,shoot
        for o in bpy.data.objects:o.hide_render=True
        tempmesh=bpy.data.meshes.new('TMP_audit_skin');tempmesh.from_pydata([x.co[:] for x in bm.vertices],[],tri);tempmesh.update()
        skinobj=bpy.data.objects.new('TMP_audit_skin',tempmesh);bpy.context.scene.collection.objects.link(skinobj)
        for face in tempmesh.polygons:face.use_smooth=True
        for obj,color in ((skinobj,(.55,.24,.20,1)),(shirt,(.17,.28,.42,1))):
            mat=bpy.data.materials.new('TMP_audit_clay');mat.use_nodes=True
            bs=mat.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=color;bs.inputs['Roughness'].default_value=.8
            for i in range(len(obj.data.materials)):obj.data.materials[i]=mat
            if not obj.data.materials:obj.data.materials.append(mat)
            obj.hide_render=False
        cam=stage(res=(640,640));sc=bpy.context.scene;sc.render.engine='CYCLES';sc.cycles.device='CPU';sc.cycles.samples=16;sc.cycles.use_denoising=True
        aim=Vector((0,-.04,1.25 if os.environ.get('FOA_FIT_REGION')=='underarm' else 1.46))
        if os.environ.get('FOA_FIT_AUTO_AIM')=='1':aim=rig.pose.bones['spine_03'].head.copy()
        def render(path):
            if os.environ.get('FOA_MATCH_BED_CAMERA')=='1':
                import math
                scene=bpy.context.scene;scene.render.resolution_x=960;scene.render.resolution_y=540
                snapshot=json.loads(Path(os.environ['FOA_SHOULDER_POSE']).read_text())
                world=matrix(snapshot['world']['position'],snapshot['world']['rotation'],snapshot['world']['scale'])
                inv=np.linalg.inv(world@np.diag((100,-100,100,1)))
                eye=np.array([133.60699189534589,-56.754752971372184,120.0,1])
                yaw=math.radians(-21.601507);pitch=math.radians(-1.141632)
                forward=np.array([math.cos(pitch)*math.cos(yaw),math.cos(pitch)*math.sin(yaw),math.sin(pitch),0])
                cam.location=Vector((inv@eye)[:3]);direction=Vector((inv@forward)[:3])
                cam.rotation_euler=direction.to_track_quat('-Z','Y').to_euler();cam.data.lens=40;cam.data.sensor_width=36
                scene.render.filepath=str(path);bpy.ops.render.render(write_still=True)
            else:shoot(cam,aim,1.1,-45,55,str(path),lift=.06)
        render(outdir/'shoulder_clay_cpu.png')
        report['normal_flags']={'custom':shirt.data.has_custom_normals,'flat_faces':sum(not f.use_smooth for f in shirt.data.polygons),'sharp_edges':sum(e.use_edge_sharp for e in shirt.data.edges)}
        for face in shirt.data.polygons:face.use_smooth=True
        for edge in shirt.data.edges:edge.use_edge_sharp=False
        if shirt.data.has_custom_normals:shirt.data.normals_split_custom_set([(0,0,0)]*len(shirt.data.loops))
        shirt.data.update()
        render(outdir/'shoulder_recomputed_normals_cpu.png')
        skinobj.hide_render=True
    eb.to_mesh_clear();es.to_mesh_clear()
out=outdir/'shoulder_fit.json';out.write_text(json.dumps(report,indent=2))
print('wrote',out)
for name,r in report['poses'].items():print(name,r['clearance_mm_percentiles'],r['inward_over_2mm'],r['outward_over_20mm'])
