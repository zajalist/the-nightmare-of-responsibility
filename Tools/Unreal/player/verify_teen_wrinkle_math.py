"""Compare the shipped Blueprint bend helper to the cloth reference at rest, mid-bend and full flexion."""
import json,math,sys
from pathlib import Path
import unreal
sys.path.insert(0,'P:/FoA/Tools/Cloth')
import wrinkle_driver as reference
cdo=unreal.get_default_object(unreal.load_asset('/Game/FoA/Characters/Player/BP_FoAPlayer').generated_class())
rows=[]
for limits in (reference.ELBOW,reference.ARM,reference.SPINE,reference.HIP,reference.KNEE):
    for angle in (0,(limits[0]+limits[1])*.5,limits[1],180):
        direction=unreal.Vector(math.cos(math.radians(angle)),math.sin(math.radians(angle)),0)
        actual=cdo.call_method('ClothBendWeight',(unreal.Vector(1,0,0),direction,*limits))
        expected=reference._smooth(limits,angle)
        assert abs(actual-expected)<1e-5,(limits,angle,actual,expected)
        rows.append(dict(limits=limits,angle=angle,actual=actual,expected=expected))
Path('P:/FoA/Saved/AnimShots/teen_wrinkle_math_verified.json').write_text(json.dumps(rows,indent=1))
print('Shipped Blueprint matches reference for all 20 bend cases')
