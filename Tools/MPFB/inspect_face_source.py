"""Read actual layered source head landmarks before the portrait variant."""
import bpy,json
from pathlib import Path
from mathutils import Vector
rig=next(o for o in bpy.data.objects if o.type=='ARMATURE')
for p in rig.pose.bones:p.matrix_basis.identity()
body=bpy.data.objects['Human']
report={'file':bpy.data.filepath,'bones':{n:[list(row) for row in rig.data.bones[n].matrix_local] for n in ('neck_01','head')},
        'keys':[(k.name,k.value) for k in body.data.shape_keys.key_blocks], 'objects':[]}
for o in bpy.data.objects:
    if o.type in ('MESH','CURVES'):
        report['objects'].append({'name':o.name,'type':o.type,'modifiers':[(m.name,m.type) for m in o.modifiers],
            'minimum':list(map(min,zip(*(o.matrix_world@Vector(c) for c in o.bound_box)))),
            'maximum':list(map(max,zip(*(o.matrix_world@Vector(c) for c in o.bound_box))))})
Path('P:/FoA/Saved/CharacterShots/mpfb/face_source_inventory.json').write_text(json.dumps(report,indent=2))
print('FACE_SOURCE',json.dumps(report))
