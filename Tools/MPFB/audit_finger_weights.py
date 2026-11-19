"""Offline skin-weight audit: finger cross-influence and bind-space distances."""
import bpy,json,numpy as np
from pathlib import Path
rig=next(o for o in bpy.data.objects if o.type=='ARMATURE');body=bpy.data.objects['Human']
for p in rig.pose.bones:p.matrix_basis.identity()
for m in body.modifiers:
 if m.type in ('MASK','SUBSURF'):m.show_viewport=False
bpy.context.view_layer.update();e=body.evaluated_get(bpy.context.evaluated_depsgraph_get());me=e.to_mesh()
names={g.index:g.name for g in body.vertex_groups};digits=('thumb','index','middle','ring','pinky')
rows=[];max_cross=0;counts={}
for v in body.data.vertices:
 weights={names[g.group]:g.weight for g in v.groups if g.weight>1e-4 and names[g.group] in rig.data.bones}
 dw={d:sum(w for n,w in weights.items() if n.startswith(d+'_')) for d in digits}
 ordered=sorted(dw.items(),key=lambda x:-x[1])
 if ordered[0][1]<.25:continue
 counts[ordered[0][0]]=counts.get(ordered[0][0],0)+1
 cross=sum(v for k,v in ordered[1:]);max_cross=max(max_cross,cross)
 if cross>.12:rows.append({'vertex':v.index,'position':list(me.vertices[v.index].co),'weights':weights,'cross_digit_weight':cross})
e.to_mesh_clear()
out={'counts':counts,'cross_digit_vertices_over_12_percent':len(rows),'max_cross_digit_weight':max_cross,'worst':sorted(rows,key=lambda r:-r['cross_digit_weight'])[:35]}
Path('P:/FoA/Saved/Integration/finger_weight_audit.json').write_text(json.dumps(out,indent=2))
print('FINGER_WEIGHT_AUDIT',len(rows),max_cross)
