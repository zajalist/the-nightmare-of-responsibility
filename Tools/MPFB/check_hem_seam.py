"""Measure the open panel/trim seam in source rest and sitting poses, before and after repair."""
import sys,json
from pathlib import Path
import bpy,numpy as np
sys.path.insert(0,'P:/FoA/Tools/MPFB')
from poses import reset,POSES
report=json.loads(Path('P:/FoA/Saved/CharacterShots/mpfb/hem_weights.json').read_text())
main=set(report['components'][0]['indices']);band=set(report['components'][1]['indices'])
mainloop=next(x['indices'] for x in report['boundary_loops'] if set(x['indices'])<=main and x['mean'][2]<1.1)
bandloop=set(max((x for x in report['boundary_loops'] if set(x['indices'])<=band),key=lambda x:x['mean'][2])['indices'])
out={}
for version,name in [('before','foa_teen_wake_layered'),('after','foa_teen_wake_hem')]:
    bpy.ops.wm.open_mainfile(filepath='P:/FoA-Assets/character/mpfb/teen/'+name+'.blend')
    rig=next(o for o in bpy.data.objects if o.type=='ARMATURE')
    obj=next(o for o in bpy.data.objects if o.name.endswith('.foa_polo_layered'))
    for mod in obj.modifiers:
        if mod.type in ('MASK','SUBSURF'):mod.show_viewport=False
    edges=[tuple(e.vertices) for e in obj.data.edges if set(e.vertices)<=bandloop]
    out[version]={}
    for pose in ('rest','sit','crouch'):
        reset(rig);POSES[pose](rig);bpy.context.view_layer.update()
        ev=obj.evaluated_get(bpy.context.evaluated_depsgraph_get());me=ev.to_mesh()
        points=np.array([v.co[:] for v in me.vertices]);ev.to_mesh_clear();distances=[]
        for i in mainloop:
            distances.append(min(np.linalg.norm(points[i]-(points[a]+np.clip(np.dot(points[i]-points[a],points[b]-points[a])/np.dot(points[b]-points[a],points[b]-points[a]),0,1)*(points[b]-points[a]))) for a,b in edges)*100)
        out[version][pose]={'maximum_gap_cm':max(distances),'mean_gap_cm':float(np.mean(distances))}
        if version=='after':assert max(distances)<.15,(pose,max(distances))
Path('P:/FoA/Saved/CharacterShots/mpfb/hem_seam_validation.json').write_text(json.dumps(out,indent=2))
print('HEM_SEAM',json.dumps(out))
