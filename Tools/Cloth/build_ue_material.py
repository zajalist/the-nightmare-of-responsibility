"""Teen fabric and sliding wrinkle normals, authored through Hayba C++ commands.
Run plain Python with imports|master|instances. Each step holds only Teen/Cloth.
The four wrinkle channels are elbow, arm, torso and knee; runtime vectors come from wrinkle_driver.py.
"""
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile

sys.path.insert(0, 'P:/FoA/Tools/Unreal')
import hayba_call as hc

ROOT = '/Game/FoA/Characters/Teen/Cloth'
MESH = '/Game/FoA/Characters/Teen/Mesh/'
MAT = ROOT + '/M_FoA_TeenCloth'
OWNER = 'character_finish'
BAKE = Path('P:/FoA-Assets/character/cloth/bake_v2')
FABRICS = {
    'Polo': ('foa_polo_layered', 'Pique', 'T_Teen_Polo_Base_Color', 18.8, 0.4, 0.86),
    'Pants': ('toigo_wool_pants', 'Flannel', 'T_Teen_Pants_wool', 8.06, 0.6, 0.9),
    'Suit': ('male_elegantsuit01', 'Wool', 'T_Teen_male_elegantsuit01_diffuse', 10.0, 0.45, 0.84),
    'Socks': (None, 'Pique', 'T_Teen_CrudeLowSocksDiffuse', 8.0, 0.3, 0.9),
    'Shoes': (None, 'Leather', 'T_Teen_shoes03_diffuse', 3.0, 0.25, 0.68),
}


def call(cmd, **params):
    r = hc.call(cmd, params, owner=OWNER, timeout=45)
    assert r.get('ok'), r
    d = r.get('data', {})
    assert d.get('ok', True), d
    assert not d.get('unknown_props'), d
    return d


def imports():
    stage = Path(tempfile.gettempdir()) / 'hayba-asset-connectors/FoA/teen_cloth'
    stage.mkdir(parents=True, exist_ok=True)
    files = {p.stem: p for p in Path('P:/FoA-Assets/character/cloth/ue').glob('T_Cloth_Micro_*.png')
             if p.stem.rsplit('_', 1)[-1] in ('Pique', 'Flannel', 'Wool', 'Leather')}
    for garment in [v[0] for v in FABRICS.values() if v[0]]:
        for suffix in ('channels_dx', 'mask'):
            files['T_' + garment + '_' + suffix] = BAKE / (garment + '_' + suffix + '.png')
    for name, src in files.items():
        target = stage / (name + '.png')
        assert src.is_file(), src
        shutil.copy2(src, target)
        if not Path('P:/FoA/Content/FoA/Characters/Teen/Cloth/' + name + '.uasset').exists():
            call('asset_import', source_file=str(target), destination_path=ROOT, asset_type='texture')
        call('texture_set_settings', path=ROOT + '/' + name,
             properties={'compression_settings': 'BC7', 'srgb': False, 'max_texture_size': 2048 if name.endswith('channels_dx') else 1024})
        call('asset_save',asset_paths=[ROOT+'/'+name])
    print('Imported', len(files), 'packed textures')


def master():
    if not Path('P:/FoA/Content/FoA/Characters/Teen/Cloth/M_FoA_TeenCloth.uasset').exists():
        call('material_create', package_path=ROOT, name='M_FoA_TeenCloth')
    info = call('material_get_info', path=MAT)
    for expression in info['expressions'][:]:
        if expression.get('parameter_name') == 'FoldSlopes':
            call('material_delete_node',material_path=MAT,node_id=expression['id'])
            info['expressions'].remove(expression)
    call('material_set_property', material_path=MAT, properties={'two_sided': True})
    call('material_set_property', material_path=MAT, properties={'used_with_skeletal_meshes': True})
    ids = {}
    layout = {'look':[-650,-450], 'WeightsL':[-1000,50], 'WeightsR':[-1000,360],
              'PhasesL':[-1000,670], 'PhasesR':[-1000,980], 'intensity':[-1000,1290]}

    def node(key, cls, pos, **props):
        target = layout.get(key,pos)
        old = next((e for e in info['expressions'] if
                    (props.get('ParameterName') and e.get('parameter_name') == props['ParameterName']) or
                    [e.get('x'), e.get('y')] in (pos,target)), None)
        if old:
            ids[key] = old['id']
            if props:
                call('material_set_node', material_path=MAT, node_id=old['id'], properties=props, node_pos=target)
        else:
            ids[key] = call('material_add_node', material_path=MAT,
                            expression_class='MaterialExpression' + cls, node_pos=target, properties=props)['node_id']

    def link(a, b=None, pin=None, prop=None, out=0):
        p = dict(material_path=MAT, from_node=ids[a], from_output_index=out)
        p.update(dict(to_node=ids[b], to_input=pin) if b else dict(to_property=prop))
        call('material_connect_nodes', **p)

    def tex(key, param, file, pos):
        node(key, 'TextureSampleParameter2D', pos, ParameterName=param, Texture=file, SamplerType='SAMPLERTYPE_LinearColor')

    node('uv', 'TextureCoordinate', [-1400, -700])
    node('tiles', 'ScalarParameter', [-1400, -550], ParameterName='MicroTiles', DefaultValue=18.8)
    node('uvscale', 'Multiply', [-1150, -650])
    tex('micro', 'MicroFabric', ROOT + '/T_Cloth_Micro_Pique', [-900, -650])
    node('alb', 'TextureSampleParameter2D', [-900, -950], ParameterName='Albedo', Texture=MESH + 'T_Teen_Polo_Base_Color')
    node('look', 'VectorParameter', [-900, -350], ParameterName='FabricResponse', DefaultValue=[0.4, 0.86, 0.3, 1])
    node('color', 'Custom', [-400, -950], Description='FabricColour', OutputType='CMOT_Float3',
         Code='return A * lerp(1.0, D * 2.0, 0.25);', Inputs=[{'InputName': x} for x in ('A', 'D')])
    node('rough', 'Custom', [-400, -650], Description='FabricRoughness', OutputType='CMOT_Float1',
         Code='return clamp(P.y + (R - 0.5) * 0.15, 0.4, 0.98);', Inputs=[{'InputName': x} for x in ('P', 'R')])
    node('spec', 'Constant', [-400, -400], R=0.3)
    node('fold','TextureObjectParameter',[-1400,0],ParameterName='FoldChannels',
         Texture=ROOT+'/T_foa_polo_layered_channels_dx',SamplerType='SAMPLERTYPE_LinearColor')
    tex('mask', 'WrinkleMask', ROOT + '/T_foa_polo_layered_mask', [-1400, 300])
    node('pos', 'PreSkinnedPosition', [-1400, 600])
    node('vpos', 'VertexInterpolator', [-1200, 700])
    for i, k in enumerate(('WeightsL', 'WeightsR', 'PhasesL', 'PhasesR')):
        node(k, 'VectorParameter', [-1000, 50 + i * 200], ParameterName='Wrinkle' + k, DefaultValue=[0, 0, 0, 0])
    node('intensity', 'ScalarParameter', [-1000, 900], ParameterName='WrinkleIntensity', DefaultValue=1.0)
    code = '''float side = smoothstep(-3.0, 3.0, Pos.x);
float4 w = lerp(WR, WL, side);
float4 p = lerp(PR, PL, side);
float2 atlasUV = (saturate(UV) * 959.0 + 32.5) / 2048.0;
float2 dx = ddx(UV) * (959.0 / 2048.0);
float2 dy = ddy(UV) * (959.0 / 2048.0);
float4 f0 = Texture2DSampleGrad(Fold, FoldSampler, atlasUV, dx, dy) * 2 - 1;
float4 f1 = Texture2DSampleGrad(Fold, FoldSampler, atlasUV + float2(0.5,0), dx, dy) * 2 - 1;
float4 f2 = Texture2DSampleGrad(Fold, FoldSampler, atlasUV + float2(0,0.5), dx, dy) * 2 - 1;
float4 f3 = Texture2DSampleGrad(Fold, FoldSampler, atlasUV + float2(0.5,0.5), dx, dy) * 2 - 1;
float4 a = saturate(Mask * w);
float2 slope = (f0.rg*cos(p.x)+f0.ba*sin(p.x))*a.x
             + (f1.rg*cos(p.y)+f1.ba*sin(p.y))*a.y
             + (f2.rg*cos(p.z)+f2.ba*sin(p.z))*a.z
             + (f3.rg*cos(p.w)+f3.ba*sin(p.w))*a.w;
// Fade before the mip footprint reaches the 32-texel tile gutters.
float footprint = max(length(dx),length(dy)) * 2048.0;
slope *= (1 - smoothstep(8.0,16.0,footprint)) * Intensity;
slope *= min(1.0, 0.3 / max(length(slope),0.0001));
slope += (Micro.rg * 2 - 1) * Response.x;
return normalize(float3(slope, 1));'''
    inputs = ('Fold', 'UV', 'Mask', 'Pos', 'WL', 'WR', 'PL', 'PR', 'Intensity', 'Micro', 'Response')
    node('normal', 'Custom', [-400, 100], Description='SlidingWrinkles', OutputType='CMOT_Float3',
         Code=code, Inputs=[{'InputName': x} for x in inputs])
    link('uv', 'uvscale', 'A'); link('tiles', 'uvscale', 'B'); link('uvscale', 'micro', 'Coordinates')
    link('alb', 'color', 'A'); link('micro', 'color', 'D', out=3)
    link('look', 'rough', 'P', out=5); link('micro', 'rough', 'R', out=4)
    link('pos', 'vpos', 'VS')
    for src, pin, out in [('fold','Fold',0),('uv','UV',0),('mask','Mask',5),('vpos','Pos',0),('WeightsL','WL',5),
                          ('WeightsR','WR',5),('PhasesL','PL',5),('PhasesR','PR',5),('intensity','Intensity',0),
                          ('micro','Micro',5),('look','Response',5)]:
        link(src, 'normal', pin, out=out)
    for src, prop in [('color','base_color'),('rough','roughness'),('normal','normal'),('spec','specular')]:
        link(src, prop=prop)
    if not info.get('comments'):
        for title, pos, size in [('Fabric surface',[-1480,-1030],[1430,850]),('Joint wrinkles',[-1480,-70],[1430,1190])]:
            call('material_add_comment', material_path=MAT, text=title, node_pos=pos, size=size, color=[0.2,0.3,0.35], font_size=22)
    for comment in call('material_get_info', path=MAT).get('comments', []):
        title = comment.get('text', '')
        call('material_set_comment', material_path=MAT, comment_id=comment['id'], show_bubble=True, color_bubble=True,
             size=[1430,1510 if title == 'Joint wrinkles' else 880])
    valid = call('material_validate', material_path=MAT)
    assert not valid.get('problems'), valid
    compiled = call('material_compile', material_path=MAT)
    assert not compiled.get('has_errors') and not compiled.get('errors'), compiled
    print(json.dumps({'nodes':len(ids),'compile':compiled}))
    Path('P:/FoA/Saved/ClothShots/teen_cloth_compile.json').write_text(json.dumps({'nodes':len(ids),'compile':compiled},indent=2))


def instances():
    for piece, (garment, fabric, albedo, tiles, strength, rough) in FABRICS.items():
        name = 'MI_Teen_' + piece
        if not Path('P:/FoA/Content/FoA/Characters/Teen/Cloth/'+name+'.uasset').exists():
            call('material_create_instance', parent_material_path=MAT, package_path=ROOT, name=name)
        params = {'Albedo':MESH + albedo, 'MicroFabric':ROOT + '/T_Cloth_Micro_' + fabric,
                  'MicroTiles':tiles, 'FabricResponse':[strength,rough,0.3,1], 'WrinkleIntensity':1.0 if garment else 0.0}
        if garment:
            params.update(FoldChannels=ROOT + '/T_' + garment + '_channels_dx', WrinkleMask=ROOT + '/T_' + garment + '_mask')
        for key,value in params.items():
            call('material_set_param', instance_path=ROOT + '/' + name, param_name=key, value=value)
        call('asset_save',asset_paths=[ROOT+'/'+name])
    print('Configured five garment instances')


if __name__ == '__main__':
    assert sys.argv[1] in ('imports','master','instances')
    assert not call('editor_get_state')['pie_running'], 'Wait until user exits PIE'
    token = hc.lease_acquire(OWNER, ['asset:' + ROOT], ttl_s=180, wait_s=20)
    try:
        globals()[sys.argv[1]]()
    finally:
        hc.release(OWNER, token)
