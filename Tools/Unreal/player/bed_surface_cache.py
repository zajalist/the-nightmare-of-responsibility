"""Offline bedding triangle reconstruction, accepted only against measured editor surface traces."""
import json
from pathlib import Path
import numpy as np
def heights(vertices,triangles,xy):
    t=vertices[triangles];a=t[:,0,:2];u=t[:,1,:2]-a;v=t[:,2,:2]-a
    det=u[:,0]*v[:,1]-u[:,1]*v[:,0];valid=np.abs(det)>1e-8
    out=[]
    for p in xy:
        d=p-a
        s=np.divide(d[:,0]*v[:,1]-d[:,1]*v[:,0],det,out=np.zeros(len(det)),where=valid)
        r=np.divide(u[:,0]*d[:,1]-u[:,1]*d[:,0],det,out=np.zeros(len(det)),where=valid)
        mask=valid&(s>=-1e-5)&(r>=-1e-5)&(s+r<=1.00001)
        z=t[:,0,2]+s*(t[:,1,2]-t[:,0,2])+r*(t[:,2,2]-t[:,0,2])
        out.append(float(z[mask].max()) if np.any(mask) else float('nan'))
    return np.array(out)
def main():
    file=Path('P:/FoA-Assets/blender/Bedding_Lux3D_Fixed/Bedding_Lux3D_Fixed.gltf')
    g=json.loads(file.read_text());raw=(file.parent/g['buffers'][0]['uri']).read_bytes()
    def accessor(i):
        a=g['accessors'][i];b=g['bufferViews'][a['bufferView']];n={'VEC3':3,'SCALAR':1}[a['type']]
        dtype={5126:'<f4',5123:'<u2',5125:'<u4'}[a['componentType']]
        return np.frombuffer(raw,dtype=dtype,count=a['count']*n,offset=b.get('byteOffset',0)+a.get('byteOffset',0)).reshape(-1,n)
    source=accessor(0).astype(float);triangles=accessor(3).reshape(-1,3)
    ctr=(source.max(0)+source.min(0))*.5;ext=(source.max(0)-source.min(0))*.5
    bounds=json.loads(Path('P:/FoA/Saved/CharacterShots/wake_capsule_static.json').read_text())['bed']
    target_ctr=np.array(bounds['origin']);target_ext=np.array(bounds['extent'])
    samples=json.loads(Path('P:/FoA/Saved/CharacterShots/sleep_side/20261107_033151/support_clearance.json').read_text())[::11]
    xy=np.array([s['skin'][:2] for s in samples]);z=np.array([s['surface_z'] for s in samples]);best=None
    for sx in (-1,1):
        for sy in (-1,1):
            world=((source-ctr)/ext)[:,[2,0,1]]*np.array([sx,sy,1])*target_ext+target_ctr
            actual=heights(world,triangles,xy);error=np.abs(actual-z)
            score=float(np.nanmax(error))
            if best is None or score<best[0]:best=(score,world,(sx,sy),float(np.nanmedian(error)))
    print('Bedding reconstruction max/median error cm',best[0],best[3],'orientation',best[2])
    # This is an offline pose-planning surface, not a final contact verdict.
    # The imported render mesh and editor trace triangles differ by millimetres.
    assert best[0]<.3,'Surface discrepancy exceeds the3mm pose-planning tolerance'
    np.savez_compressed('P:/FoA/Saved/CharacterShots/bedding_surface_world.npz',vertices=best[1],triangles=triangles,
        max_trace_error_cm=best[0],median_trace_error_cm=best[3])
if __name__=='__main__':main()
