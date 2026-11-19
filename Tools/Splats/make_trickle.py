"""Sand pours of any height for BP_SandAmbience (world lane): make_sand_splats.py's commode stream rebuilt for a new
drop, so its baked landing pile sits where the column lands (SM_SandStream's pile is baked 121 cm under the lip; a
longer drop in the material alone left that pile hanging in mid-air, PIE 15:40).
  python Tools/Splats/make_trickle.py   -> P:/FoA-Assets/splatmesh/SM_SandTrickle_<drop>.gltf (+ .bin, .splatmesh.json)
Prints the MI values (Shape, Place, Tune) each mesh needs on its M_SplatMesh stream instance."""
import json
import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_sand_splats as m  # noqa: E402

OUT = 'P:/FoA-Assets/splatmesh'
# name: (drop cm, throw cm/s, slide cm, slide height cm, pile scale, lip half width cm)
POURS = {'SM_SandTrickle_Ceiling': (296.0, 4.0, 3.0, 1.0, 0.28, 2.6),   # from the ceiling to the boards (wide lip: a 3 m fall necks it thin)
         'SM_SandTrickle_Clock': (57.0, 3.0, 2.0, 0.5, 0.14, 0.6)}      # from the wall clock onto the mantel


def layout(drop, throw, pile_scale):
    S_C = m.mound_shape(m.MOUND_SEEDS['C'])
    z_land = -drop + S_C[0] * pile_scale
    tf = math.sqrt(2 * (m.STREAM['lift'] - z_land) / m.G)
    return {'x_land': throw * tf, 'z_land': z_land, 'drop': drop, 'shape_C': S_C, 'fall_time': tf}


def main():
    saved = dict(m.STREAM)
    try:
        for name, (drop, throw, slide, slide_h, ps, hw) in POURS.items():
            m.STREAM.update(throw=throw, slide=slide, pile_scale=ps, lip_half_width=hw)
            L = layout(drop, throw, ps)
            assert abs(L['z_land'] + drop - L['shape_C'][0] * ps) < 1e-6 and L['x_land'] < 6.0, L   # lands on its own pile, under the lip
            m.build_stream(random.Random(7), L).write(OUT, name, {'layout': {k: v for k, v in L.items()}})
            mi = {'Shape': [round(x, 4) for x in L['shape_C']], 'Place': [round(L['x_land'], 4), 0.0, ps, 0.0],
                  'Tune': [drop, throw, slide, slide_h]}
            print(name, json.dumps(mi))
    finally:
        m.STREAM.clear()
        m.STREAM.update(saved)


if __name__ == '__main__':
    main()
