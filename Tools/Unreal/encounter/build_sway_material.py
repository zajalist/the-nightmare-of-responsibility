"""M_OpponentSway: the shared cloth material BP_Garment.Setup puts on the placeholder garment meshes. Hayba C++ material
tools only (editor-rules), from outside the editor:  python Tools/Unreal/encounter/build_sway_material.py
  Base colour  Albedo (default: the Lux3D shirt's texture) x Tint (custom primitive data 1-3, set from the row's Tint)
  WPO          one Custom node: a slow rock about the mesh centre (Sway.x cm per cm of local height, Sway.y rad/s) plus
               a decaying ripple after a hit (custom primitive data 0 = hit time, Sway.z amplitude, Sway.w decay /s)
Creates the asset only if it is missing; reruns stop with a message instead of stacking nodes."""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from hayba_call import call  # noqa: E402

M = '/Game/FoA/Gameplay/Encounter/M_OpponentSway'
ALBEDO = '/Game/FoA/Lux3D/the_shirt_enemy/T_Lux3D_ShirtEnemy_BaseColor.T_Lux3D_ShirtEnemy_BaseColor'
CODE = ('float age = T - Hit;\n'
        'float ripple = sin(age * 28.0) * saturate(1.0 - age * P.w) * P.z;\n'
        'return float3(1.0, 0.35, 0.0) * (sin(T * P.y) * P.x + ripple) * Pos.z;')


def ok(r, what):
    if not r.get('ok') or (isinstance(r.get('data'), dict) and r['data'].get('ok') is False):
        sys.exit(f'{what} failed: {json.dumps(r)[:600]}')
    return r.get('data') or {}


def node(cls, x, y, **props):
    d = ok(call('material_add_node', {'material_path': M, 'expression_class': cls, 'node_pos': [x, y],
                                      'properties': props}), cls)
    return d['node_id']


def link(a, b=None, to_input=None, prop=None, out=0):
    p = {'material_path': M, 'from_node': a, 'from_output_index': out}
    p.update({'to_node': b, 'to_input': to_input} if b else {'to_property': prop})
    ok(call('material_connect_nodes', p), f'{a} -> {b or prop}')


if os.path.exists('P:/FoA/Content/FoA/Gameplay/Encounter/M_OpponentSway.uasset'):
    sys.exit(f'{M} exists: edit it in place (material_set_node), never stack a second graph')
ok(call('material_create', {'package_path': '/Game/FoA/Gameplay/Encounter', 'name': 'M_OpponentSway'}), 'create')
alb = node('MaterialExpressionTextureSampleParameter2D', -640, -160, ParameterName='Albedo', Texture=ALBEDO)
tint = node('MaterialExpressionVectorParameter', -640, 80, ParameterName='Tint', DefaultValue='(R=1,G=1,B=1,A=1)',
            bUseCustomPrimitiveData=True, PrimitiveDataIndex=1)
mul = node('MaterialExpressionMultiply', -320, -40)
rough = node('MaterialExpressionConstant', -320, 160, R=0.85)
tm = node('MaterialExpressionTime', -900, 400)
hit = node('MaterialExpressionScalarParameter', -900, 500, ParameterName='HitTime', DefaultValue=-100.0,
           bUseCustomPrimitiveData=True, PrimitiveDataIndex=0)
pos = node('MaterialExpressionLocalPosition', -900, 600)
sway = node('MaterialExpressionVectorParameter', -900, 700, ParameterName='Sway',
            DefaultValue='(R=0.03,G=1.6,B=0.06,A=1.5)')
cus = node('MaterialExpressionCustom', -560, 520, Code=CODE, OutputType='CMOT_Float3', Description='ClothSway',
           Inputs=[{'InputName': n} for n in ('T', 'Hit', 'Pos', 'P')])
link(alb, mul, 'A'); link(tint, mul, 'B'); link(mul, prop='base_color'); link(rough, prop='roughness')
for src, pin in ((tm, 'T'), (hit, 'Hit'), (pos, 'Pos'), (sway, 'P')):
    link(src, cus, pin, out=5 if src == sway else 0)  # Sway: RGBA (index 5), the code reads P.w
link(cus, prop='world_position_offset')
for text, pos_, size, col in (('Surface', [-680, -220], [560, 480], [0.25, 0.25, 0.3]),
                              ('Cloth sway', [-940, 340], [600, 470], [0.15, 0.3, 0.3])):
    ok(call('material_add_comment', {'material_path': M, 'text': text, 'node_pos': pos_, 'size': size, 'color': col}), text)
print(json.dumps(ok(call('material_validate', {'material_path': M}), 'validate'))[:400])
print(json.dumps(ok(call('material_compile', {'material_path': M}), 'compile'))[:400])
print('nodes', dict(albedo=alb, tint=tint, mul=mul, rough=rough, time=tm, hit=hit, pos=pos, sway=sway, custom=cus))
