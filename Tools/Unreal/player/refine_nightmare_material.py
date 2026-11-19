"""Replace the exposed mannequin's white surfaces with the existing black sand material."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'Tools/Unreal'))
import hayba_call as hc

OWNER = 'codex-nightmare'
BP = '/Game/FoA/Characters/Player/BP_Nightmare'
MAT = '/Game/FoA/Materials/M_DarkSand'
MI = '/Game/FoA/Materials/MI_DarkSand_Black.MI_DarkSand_Black'
MESH = BP + '.Default__BP_Nightmare_C:CharacterMesh0'
token = hc.lease_acquire(OWNER, ['asset:' + BP, 'asset:' + MAT, 'actor:Nightmare'], ttl_s=60, wait_s=10)


def call(command, **params):
    reply = hc.call(command, params, owner=OWNER, lease=token, timeout=20)
    assert reply.get('ok'), reply
    return reply.get('data', {})


try:
    assert not call('editor_get_state')['pie_running']
    info = call('material_get_info', path=MAT)
    compiled = None
    if not info['usage_flags']['used_with_skeletal_meshes']:
        call('material_set_property', material_path=MAT, properties={'used_with_skeletal_meshes': True})
        valid = call('material_validate', material_path=MAT)
        assert valid.get('ok') and not valid.get('problems'), valid
        compiled = call('material_compile', material_path=MAT)
        assert compiled.get('saved') and not compiled.get('has_errors') and not compiled.get('errors'), compiled
    materials = [MI, MI]
    call('object_set_property', path=MESH, properties={'OverrideMaterials': materials})
    saved = call('asset_save', asset_paths=[BP])
    assert saved.get('saved_count') == 1 and not saved.get('failed'), saved
    proof = call('object_get_property', path=MESH, names=['OverrideMaterials'])
    assert proof['properties']['OverrideMaterials'].count('MI_DarkSand_Black') == 4, proof
    actors = call('actor_list', class_filter='BP_Nightmare_C')['actors']
    actor = next(a for a in actors if a['label'] == 'Nightmare')
    component = '/Game/FoA/Maps/L_Tutorial_Bedroom.L_Tutorial_Bedroom:PersistentLevel.' + actor['id'] + '.CharacterMesh0'
    call('object_set_property', path=component, properties={'OverrideMaterials': materials})
    placed = call('object_get_property', path=component, names=['OverrideMaterials'])
    assert placed['properties']['OverrideMaterials'].count('MI_DarkSand_Black') == 4, placed
    ROOT.joinpath('Saved/Integration/nightmare_material.json').write_text(json.dumps(dict(compile=compiled, proof=proof, placed=placed, transform=actor['location']), indent=2))
    print('Nightmare black sand material saved and read back')
finally:
    hc.release(OWNER, token)
