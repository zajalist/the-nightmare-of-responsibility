"""Offline: the Lux3D smartphone v2 GLB put into SM_Phone's frame, so it can replace /Game/FoA/Props/Phone/SM_Phone in
place (every BP_Phone / nightstand / intro use keeps its transform):
  glTF (as SM_Phone.glb was): long axis +X = up the screen, thin axis Y with the glass at -Y, width Z; pivot at the
  bounding-box centre; 147 x 71 mm, ~8 mm body. In UE (glTF x, y, z -> UE x, z, y) that is: X up the screen, screen normal -Z.
  python Tools/Lux3D/phone_v2_prep.py   ->  P:/FoA-Assets/lux3d/smartphone_v2/body_oriented.glb
Then: python Tools/Lux3D/phone_screen_slot.py body_oriented.glb SM_Phone.glb --screen -y --top +x"""
import numpy as np
import trimesh

SRC = 'P:/FoA-Assets/lux3d/smartphone_v2/textured.glb'
DST = 'P:/FoA-Assets/lux3d/smartphone_v2/body_oriented.glb'
LENGTH_M = 0.147
WIDTH_M = 0.071
THICK_SCALE = 0.8   # Lux3D's slab is ~10 mm at 147 mm long; 0.8 gives ~8 mm, the bump stays proud of the back

scene = trimesh.load(SRC, force='scene')
body = scene.to_geometry()
lo, hi = body.bounds
ext = hi - lo
# Lux3D frame (measured): long axis +Y (camera bump at the top), thin axis Z with the glass at -Z and the bump at +Z.
assert np.argmax(ext) == 1 and np.argmin(ext) == 2, ext
v = body.vertices - (lo + hi) / 2
v = np.stack([v[:, 1], v[:, 2], v[:, 0]], axis=1)          # cyclic (x,y,z) <- (y,z,x): a rotation, faces keep their winding
k = LENGTH_M / ext[1]
v *= np.array([k, k * THICK_SCALE, WIDTH_M / ext[0]])   # new axes: long, thin, wide
body.vertices = v
lo2, hi2 = body.bounds
bump_side = body.vertices[:, 1] > 0.8 * hi2[1]
print('extent mm', np.round((hi2 - lo2) * 1000, 1), 'tris', len(body.faces),
      'bump at +Y' if bump_side.sum() and body.vertices[bump_side, 0].mean() > 0 else 'CHECK bump side')
out = trimesh.Scene()
out.add_geometry(body, geom_name='Body')
open(DST, 'wb').write(out.export(file_type='glb'))
print('->', DST)
