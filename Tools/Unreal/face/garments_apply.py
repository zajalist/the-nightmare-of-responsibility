"""Battle garments, step a+b (Hayba only, run outside the editor inside a lease on /Game/FoA/Characters/Garments):
  python Tools/Unreal/face/garments_apply.py
a) import the padded per-garment base colours (garments_pad.py) as T_Garment_<Name>_BaseColor (1024, sRGB);
b) one instance of the existing M_FoA_TeenCloth per garment (no new master): its own Albedo, a micro fabric, matte
   fabric response, wrinkles off. Step c (slots) is garments_assign.py; the old merged material is deleted after.
Why: all four SK_Garment_* shared RetopologyBakedMaterial, which samples the SHIRT's bake, so trousers, socks and
tie showed the shirt atlas on their own UVs (white with black blotches)."""
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, 'P:/FoA/Tools/Unreal')
import hayba_call as hc  # noqa: E402

ROOT = '/Game/FoA/Characters/Garments'
SRC = Path('P:/FoA-Assets/character/garments/rig/padded')
CLOTH = '/Game/FoA/Characters/Teen/Cloth'
# name: (micro fabric, micro tiles, FabricResponse x micro strength, y roughness)
LOOK = {'Shirt': ('Flannel', 14.0, 0.35, 0.88), 'Trousers': ('Wool', 10.0, 0.45, 0.9),
        'Sock': ('Wool', 16.0, 0.5, 0.92), 'Tie': ('Pique', 20.0, 0.3, 0.8)}


def call(cmd, **kw):
    r = hc.call(cmd, kw)
    assert r.get('ok'), (cmd, r)
    d = r.get('data', {})
    assert not d.get('errors') and not d.get('failed'), (cmd, d)
    return d


stage = Path(tempfile.gettempdir()) / 'hayba-asset-connectors/FoA/garments_padded'
stage.mkdir(parents=True, exist_ok=True)
for name, (fabric, tiles, micro, rough) in LOOK.items():
    tex = f'{ROOT}/T_Garment_{name}_BaseColor'
    if not Path(f'P:/FoA/Content/FoA/Characters/Garments/T_Garment_{name}_BaseColor.uasset').exists():
        src = SRC / f'T_Garment_{name}_BaseColor.png'
        shutil.copy2(src, stage / src.name)
        call('asset_import', source_file=str(stage / src.name), destination_path=ROOT, asset_type='texture')
    call('texture_set_settings', path=tex, properties={'srgb': True, 'max_texture_size': 1024})
    mi = f'{ROOT}/MI_Garment_{name}'
    if not Path(f'P:/FoA/Content/FoA/Characters/Garments/MI_Garment_{name}.uasset').exists():
        call('material_create_instance', parent_material_path=f'{CLOTH}/M_FoA_TeenCloth', package_path=ROOT, name=f'MI_Garment_{name}')
    for k, v in (('Albedo', tex), ('MicroFabric', f'{CLOTH}/T_Cloth_Micro_{fabric}'), ('MicroTiles', tiles),
                 ('FabricResponse', [micro, rough, 0.3, 1.0]), ('WrinkleIntensity', 0.0), ('CorruptionPulse', 0.0)):
        call('material_set_param', instance_path=mi, param_name=k, value=v)
    print(call('asset_save', asset_paths=[tex, mi]).get('saved'), name)
