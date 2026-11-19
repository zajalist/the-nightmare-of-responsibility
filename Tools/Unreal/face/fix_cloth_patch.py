"""The black square on the polo chest (wake film, from ~14 s): the cloth corruption patch (M_FoA_TeenCloth,
CorruptionPulse from BP_FoAPlayer.UpdateClothCorruption, chest site every 32 s) darkened the cloth to 12% and,
above pulse 0.6, clipped UV-grid 'sand' holes through it. The skin under the polo is a hidden section, so the holes
showed the unlit inside of the shirt: a hard black square. Now: no holes (opacity mask 1), a damp stain at 45%.
Hayba only; run inside a lease on Teen/Cloth:  python Tools/Unreal/face/fix_cloth_patch.py"""
import sys

sys.path.insert(0, 'P:/FoA/Tools/Unreal')
import hayba_call as hc  # noqa: E402

M = '/Game/FoA/Characters/Teen/Cloth/M_FoA_TeenCloth'


def call(cmd, **kw):
    r = hc.call(cmd, kw)
    assert r.get('ok'), (cmd, r)
    d = r.get('data', {})
    assert not d.get('errors'), (cmd, d)
    return d


info = call('material_get_info', path=M)
desc = {e['id']: e for e in info['expressions'] if e['class'] == 'MaterialExpressionCustom'}
assert [i['name'] for i in desc['MaterialExpressionCustom_4']['inputs']] == ['F', 'Mask']
assert [i['name'] for i in desc['MaterialExpressionCustom_6']['inputs']] == ['Mask', 'Pulse', 'Grain']
call('material_set_node', material_path=M, node_id='MaterialExpressionCustom_4',
     properties={'Code': 'return lerp(F, F * 0.45, Mask * 0.85);'})
call('material_set_node', material_path=M, node_id='MaterialExpressionCustom_6', properties={'Code': 'return 1.0;'})
print(call('material_validate', material_path=M))
c = call('material_compile', material_path=M)
assert c.get('compiled_clean'), c
print('cloth patch: stain only, no holes; compiled and saved', c.get('saved'))
