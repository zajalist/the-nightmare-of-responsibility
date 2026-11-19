"""Skin calibration after the first PIE look at skin v2 (Hayba only; run inside a lease on Teen/Materials):
  python Tools/Unreal/face/tune_teen_skin.py
v2 read as chalk/plaster in the monochrome grade: the wrap of Preintegrated Skin lifted the shadows and the 22-tile
micro normal at 0.55 showed as grit. Now: scatter 0.35, micro normal 40 tiles at 0.22, and the skin albedo tinted
to 0.66 (pass 2: at 0.8 his arms still out-shone the white polo in PIE; real light skin is not paper white, the
MakeHuman texture is), so he stops being the brightest thing in a moonlit room. Hue untouched (monochrome grade)."""
import sys

sys.path.insert(0, 'P:/FoA/Tools/Unreal')
import hayba_call as hc  # noqa: E402

M = '/Game/FoA/Characters/Teen/Materials/M_FoA_TeenSurface'
SKIN = ('/Game/FoA/Characters/Teen/Materials/MI_Teen_Skin', '/Game/FoA/Characters/Teen/Materials/MI_Teen_Skin_Groom')


def call(cmd, **kw):
    r = hc.call(cmd, kw)
    assert r.get('ok'), (cmd, r)
    d = r.get('data', {})
    assert not d.get('errors'), (cmd, d)
    return d


ids = {e.get('parameter_name'): e['id'] for e in call('material_get_info', path=M)['expressions'] if e.get('parameter_name')}
call('material_set_node', material_path=M, node_id=ids['SkinResponse'],
     properties={'DefaultValue': {'R': 0.5, 'G': 0.35, 'B': 0.35, 'A': 40.0}})
call('material_set_node', material_path=M, node_id=ids['MicroStrength'], properties={'DefaultValue': 0.22})
print(call('material_validate', material_path=M))
c = call('material_compile', material_path=M)
assert c.get('compiled_clean'), c
for mi in SKIN:
    call('material_set_param', instance_path=mi, param_name='Tint', value=[0.66, 0.66, 0.66, 1.0])
print(call('asset_save', asset_paths=list(SKIN)))
