"""CPU-only red/green scalp-spot test on the saved candidate; never writes the blend."""
import json
import os
import sys
import bpy
from mathutils import Vector
sys.path.insert(0,os.path.dirname(__file__))
from build_hair import check_scalp, ObjectService
from mpfb_common import SHOTS
from stage import stage

body=next(o for o in bpy.data.objects if o.type=='MESH' and ObjectService.get_object_type(o)=='Basemesh')
hair=bpy.data.objects['basic_short_hair']
cam=stage(engine='CYCLES',res=(600,600))
bpy.context.scene.cycles.device='CPU'
eyes=ObjectService.find_object_of_type_amongst_nearest_relatives(body,'Eyes')
head=sum((eyes.matrix_world @ Vector(c) for c in eyes.bound_box),Vector())/8+Vector((0,.02,.05))
out=os.path.join(SHOTS,'hair')
green=check_scalp(body,hair,cam,head,out,'short01_final')
hair.hide_render=True
red=check_scalp(body,hair,cam,head,out,'short01_final_nohair')
report={'interior_erosion_rings':2,'minimum_spot_width_pixels':3,'with_hair':green,'without_hair':red}
with open(os.path.join(out,'short01_scalp_validation.json'),'w') as f:
    json.dump(report,f,indent=2)
assert all(v[0]>1000 for v in red.values()), 'Red control did not expose a measurable scalp'
assert all(green[v][1] < max(100,red[v][1]*.01) for v in green), report
print('SCALP_SPOTS_PASS',report)
