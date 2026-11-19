"""Black-sand look for the jumpscare bust, baked into its own two textures (offline, numpy):
  python Tools/Unreal/horror/make_monster_maps.py   (after bake_monster_maps_blender.py)
In:  Saved/HorrorShots/monster/maps/{bc_src,mr_src,ao,curv,pos}.png
Out: Saved/HorrorShots/monster/maps/T_Jumpscare_Monster_BC.png (sRGB), T_Jumpscare_Monster_MR.png (linear,
     G roughness, B metallic 0) and T_Jumpscare_Monster_S.png (linear specular strength), 1024 px.
- Voids: the eye sockets (eyeballs included) and the mouth interior (tongue included) go to zero albedo and roughness 1,
  picked by front projection of the baked object position (ellipses below, in bounding-box units, Blender front view)
  and limited to surfaces within VOID_DEPTH of the frontmost surface, so the back of the head is untouched.
- Cavities darken with the baked AO; roughness follows curvature, so only ridges (brows, cheekbones, teeth tips,
  knuckles) stay glossy enough to catch the key and rim."""
import numpy as np
from PIL import Image

D = 'P:/FoA/Saved/HorrorShots/monster/maps'
N = 1024
# (centre x, centre z, radius x, radius z) in the bust's bounding box, read off front_ao.png
VOIDS = [(0.39, 0.82, 0.07, 0.05), (0.605, 0.82, 0.07, 0.05),  # eye sockets
         (0.50, 0.50, 0.095, 0.11)]                              # mouth interior and tongue, below the upper teeth
MOUTH_TOP = 0.605   # z: upper teeth tips start here, keep them
VOID_DEPTH = 0.25   # of the 26 cm depth: about 6.5 cm behind the frontmost surface


def load(name, mode, size=N):
    return np.asarray(Image.open(f'{D}/{name}.png').convert(mode).resize((size, size), Image.LANCZOS), dtype=np.float64) / 255


def main():
    bc, mr = load('bc_src', 'RGB'), load('mr_src', 'RGB')
    ao, curv, pos = load('ao', 'L'), load('curv', 'L'), load('pos', 'RGB')
    x, y, z = pos[..., 0], pos[..., 1], pos[..., 2]
    covered = pos.sum(2) > 0.01
    # frontmost depth per front-view cell (100 x 100 over the bounding box)
    G = 100
    gx, gz = np.clip((x * (G - 1)).round().astype(int), 0, G - 1), np.clip((z * (G - 1)).round().astype(int), 0, G - 1)
    front = np.full((G, G), 9.0)
    np.minimum.at(front, (gz[covered], gx[covered]), y[covered])
    near_front = y <= front[gz, gx] + VOID_DEPTH
    void = np.zeros((N, N), bool)
    for cx, cz, rx, rz in VOIDS:
        inside = ((x - cx) / rx) ** 2 + ((z - cz) / rz) ** 2 <= 1
        if cz < 0.7:
            inside &= z < MOUTH_TOP
        void |= inside & near_front & covered
    soft = np.asarray(Image.fromarray((void * 255).astype(np.uint8)).resize((N // 4, N // 4), Image.BILINEAR)
                      .resize((N, N), Image.BILINEAR), dtype=np.float64) / 255  # feather the void edge a little
    keep = 1 - np.clip(np.maximum(soft, void), 0, 1)
    cav = np.clip((ao - 0.15) / 0.6, 0, 1) ** 1.5  # AO 0.15 -> black, 0.75+ -> full
    albedo = bc * (cav * keep)[..., None]
    ridge = np.clip((curv - 0.50) / 0.04, 0, 1)
    rough = 0.85 - 0.55 * ridge                      # ridges 0.30, flats 0.85
    rough = np.maximum(rough, 1 - cav * 0.6)          # deep cavities stay matte
    rough = np.where(keep < 0.5, 1.0, rough)
    mr_out = np.dstack([mr[..., 0], rough, np.zeros_like(rough)])
    Image.fromarray((np.clip(albedo, 0, 1) * 255).astype(np.uint8)).save(f'{D}/T_Jumpscare_Monster_BC.png')
    Image.fromarray((np.clip(mr_out, 0, 1) * 255).astype(np.uint8)).save(f'{D}/T_Jumpscare_Monster_MR.png')
    # Specular strength (KHR_materials_specular, every channel): the albedo is so dark that specular IS the look, so
    # only ridges keep full spec; flats get a little, cavities and the voids none (js7: the voids still caught light)
    spec = (0.25 + 0.75 * ridge) * cav * keep
    spec = np.where(keep < 0.5, 0.0, spec)
    s8 = (np.clip(spec, 0, 1) * 255).astype(np.uint8)
    Image.fromarray(np.dstack([s8, s8, s8, s8]), 'RGBA').save(f'{D}/T_Jumpscare_Monster_S.png')
    frac = void[covered].mean()
    print(f'void texels {frac:.3%}, mean albedo {albedo[covered].mean():.3f} (was {bc[covered].mean():.3f}), '
          f'rough ridges {(rough[covered] < 0.45).mean():.1%}')
    assert 0.002 < frac < 0.08, 'void mask covers an implausible share of the bust'
    assert albedo[void].max() < 0.02, 'voids are not black'
    assert spec[void].max() == 0, 'voids still have specular'


main()
