"""M_SplatWorld_Lean (docs/design/level2/splat_budget_ours.md section 7): the static world-splat material for lean
splat meshes (ply_to_splatmesh.py --lean: POSITION = centre, UV0 = corner +-1, UV1 = (radius cm, seed), COLOR_0 = DC
sRGB + opacity). Unlit, Masked with a seeded IGN dither (TSR resolves it), no sort, no SH, no flow: a camera-facing
quad in the vertex shader, the Gaussian footprint and the colour in the pixel shader. Material graphs are Hayba-only.
  python Tools/Splats/build_splat_world_lean.py            (world lane; leases the Level2 folder for one run)
Also builds M_L2_PanoSky in place as a dark procedural atmosphere (legacy asset name retained)."""
import sys
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parent))
sys.path.insert(0, 'P:/FoA/Tools/Unreal')
import hayba_call as h  # noqa: E402
import dream_sky

ROOT = '/Game/FoA/Level2'
MAT, SKY, CITY = f'{ROOT}/M_SplatWorld_Lean', f'{ROOT}/Dream/M_L2_PanoSky', f'{ROOT}/M_SplatCity_Lean'

BILLBOARD = """// Camera-facing quad: this corner's offset from the splat centre (the mesh carries centres only).
float s = length(TransformLocalVectorToWorld(Parameters, float3(1.0, 0.0, 0.0)));
float3 R = ResolvedView.ViewToTranslatedWorld[0].xyz, U = ResolvedView.ViewToTranslatedWorld[1].xyz;
return (R * Corner.x + U * Corner.y) * (RS.x * Scale * s);"""
COVERAGE = """// Gaussian footprint windowed to 0 at the rim, then a per-splat seeded IGN dither (overlaps add up under TSR).
float e = exp(-K);
float a = A * max((exp(-K * dot(Corner, Corner)) - e) / (1.0 - e), 0.0);
return a > InterleavedGradientNoise(Parameters.SvPosition.xy + RS.y * 117.0, View.StateFrameIndexMod8) ? 1.0 : 0.0;"""
COLOUR = """// COLOR_0 holds display (sRGB) values and VertexColor returns them unchanged: decode to linear for emissive.
return pow(saturate(C), 2.2) * G;"""


def call(cmd, **p):
    r = h.call(cmd, p)
    assert r.get('ok'), r
    d = r.get('data', {})
    assert d.get('ok', True) and not d.get('errors') and not d.get('failed') and not d.get('has_errors'), d
    return d


def nodes(mat, specs):
    """specs: (key, class, pos, props). Reuses a node already at that position (re-run safe)."""
    info = call('material_get_info', path=mat)
    ids = {}
    for key, cls, pos, props in specs:
        old = next((e for e in info['expressions'] if [e['x'], e['y']] == pos), None)
        if old:
            ids[key] = old['id']
            if props:
                call('material_set_node', material_path=mat, node_id=old['id'], properties=props)
        else:
            ids[key] = call('material_add_node', material_path=mat, expression_class='MaterialExpression' + cls,
                            node_pos=pos, properties=props)['node_id']
    return ids, info


def link(mat, ids, a, b, pin, index=0):
    call('material_connect_nodes', material_path=mat, from_node=ids[a], from_output_index=index, to_node=ids[b], to_input=pin)


def custom(desc, out, ins, code):
    return {'Description': desc, 'OutputType': out, 'Inputs': [{'InputName': n} for n in ins], 'Code': code}


def lean():
    if not h.call('material_get_info', {'path': MAT}).get('ok'):
        call('material_create', package_path=ROOT, name='M_SplatWorld_Lean')
    ids, info = nodes(MAT, [
        ('uv0', 'TextureCoordinate', [-900, 0], {'CoordinateIndex': 0}),
        ('uv1', 'TextureCoordinate', [-900, 140], {'CoordinateIndex': 1}),
        ('vc', 'VertexColor', [-900, 280], {}),
        ('scale', 'ScalarParameter', [-900, 440], {'ParameterName': 'RadiusScale', 'DefaultValue': 1.04}),
        ('hard', 'ScalarParameter', [-900, 540], {'ParameterName': 'Hardness', 'DefaultValue': 2.0}),
        ('gain', 'ScalarParameter', [-900, 640], {'ParameterName': 'EmissiveGain', 'DefaultValue': 1.0}),
        ('bb', 'Custom', [-500, 0], custom('Billboard', 'CMOT_Float3', ('Corner', 'RS', 'Scale'), BILLBOARD)),
        ('cov', 'Custom', [-500, 260], custom('Coverage', 'CMOT_Float1', ('Corner', 'RS', 'A', 'K'), COVERAGE)),
        ('col', 'Custom', [-500, 520], custom('Colour', 'CMOT_Float3', ('C', 'G'), COLOUR))])
    for a, b, pin, idx in (('uv0', 'bb', 'Corner', 0), ('uv1', 'bb', 'RS', 0), ('scale', 'bb', 'Scale', 0),
                           ('uv0', 'cov', 'Corner', 0), ('uv1', 'cov', 'RS', 0), ('vc', 'cov', 'A', 4), ('hard', 'cov', 'K', 0),
                           ('vc', 'col', 'C', 0), ('gain', 'col', 'G', 0)):
        link(MAT, ids, a, b, pin, idx)
    for a, prop in (('bb', 'world_position_offset'), ('cov', 'opacity_mask'), ('col', 'emissive_color')):
        call('material_connect_nodes', material_path=MAT, from_node=ids[a], from_output_index=0, to_property=prop)
    call('material_set_property', material_path=MAT, properties={'blend_mode': 'Masked', 'shading_model': 'Unlit',
                                                                  'two_sided': True, 'opacity_mask_clip_value': 0.5})
    if not info.get('comments'):
        call('material_add_comment', material_path=MAT, text='Lean world splat', node_pos=[-960, -80], size=[900, 820],
             color=[0.12, 0.26, 0.16])
    call('material_compile', material_path=MAT)


def city():
    """M_SplatCity_Lean: the Toronto meshes carry their quads already built facing +Z (top-down drive camera), so no
    billboard WPO: the same coverage dither and colour as the lean world material."""
    if not h.call('material_get_info', {'path': CITY}).get('ok'):
        call('material_create', package_path=ROOT, name='M_SplatCity_Lean')
    ids, info = nodes(CITY, [
        ('uv0', 'TextureCoordinate', [-900, 0], {'CoordinateIndex': 0}),
        ('uv1', 'TextureCoordinate', [-900, 140], {'CoordinateIndex': 1}),
        ('vc', 'VertexColor', [-900, 280], {}),
        ('hard', 'ScalarParameter', [-900, 540], {'ParameterName': 'Hardness', 'DefaultValue': 2.0}),
        ('gain', 'ScalarParameter', [-900, 640], {'ParameterName': 'EmissiveGain', 'DefaultValue': 1.0}),
        ('cov', 'Custom', [-500, 260], custom('Coverage', 'CMOT_Float1', ('Corner', 'RS', 'A', 'K'), COVERAGE)),
        ('col', 'Custom', [-500, 520], custom('Colour', 'CMOT_Float3', ('C', 'G'), COLOUR))])
    for a, b, pin, idx in (('uv0', 'cov', 'Corner', 0), ('uv1', 'cov', 'RS', 0), ('vc', 'cov', 'A', 4), ('hard', 'cov', 'K', 0),
                           ('vc', 'col', 'C', 0), ('gain', 'col', 'G', 0)):
        link(CITY, ids, a, b, pin, idx)
    for a, prop in (('cov', 'opacity_mask'), ('col', 'emissive_color')):
        call('material_connect_nodes', material_path=CITY, from_node=ids[a], from_output_index=0, to_property=prop)
    call('material_set_property', material_path=CITY, properties={'blend_mode': 'Masked', 'shading_model': 'Unlit',
                                                                   'two_sided': True, 'opacity_mask_clip_value': 0.5})
    if not info.get('comments'):
        call('material_add_comment', material_path=CITY, text='City splat top down', node_pos=[-960, -80], size=[900, 820],
             color=[0.12, 0.26, 0.16])
    call('material_compile', material_path=CITY)


def ground():
    """Existing ground material supports the far plane and reused moving splat tiles."""
    path = f'{ROOT}/City/M_City_Ground'
    if not h.call('material_get_info', {'path': path}).get('ok'):
        call('material_create', package_path=f'{ROOT}/City', name='M_City_Ground')
    from build_splat_dynamics import ground as apply_ground_dynamics
    apply_ground_dynamics()


def sky():
    if not h.call('material_get_info', {'path': SKY}).get('ok'):
        call('material_create', package_path=f'{ROOT}/Dream', name='M_L2_PanoSky')
    # Keep the already-referenced material asset; remove the photograph node and obsolete UV path.
    info=call('material_get_info',path=SKY)
    wanted={(tuple(pos),'MaterialExpression'+cls) for _,cls,pos,_ in dream_sky.specs(custom)}
    obsolete=[e for e in info['expressions'] if ((e['x'],e['y']),e['class']) not in wanted]
    previous=next((o for o in info.get('material_outputs',[]) if ''.join(c.lower() for c in o['property'] if c.isalnum())=='emissivecolor'),None)
    ids, info = nodes(SKY,dream_sky.specs(custom))
    link(SKY, ids, 'cam', 'sky', 'Dir');link(SKY, ids, 'time', 'sky', 'Clock')
    call('material_connect_nodes',material_path=SKY,from_node=ids['sky'],from_output_index=0,to_property='emissive_color')
    call('material_set_property', material_path=SKY, properties={'blend_mode':'Opaque','shading_model': 'Unlit', 'two_sided': True})
    try:
        call('material_compile',material_path=SKY)
    except Exception:
        if previous and obsolete:
            call('material_connect_nodes',material_path=SKY,from_node=previous['from_node'],from_output_index=0,to_property='emissive_color')
            call('material_compile',material_path=SKY)
        raise
    for expression in obsolete:call('material_delete_node',material_path=SKY,node_id=expression['id'])
    if not info.get('comments'):
        call('material_add_comment', material_path=SKY, text='Dark dream atmosphere', node_pos=[-960, -80], size=[900, 450],
             color=[0.10, 0.20, 0.35])
    for comment in call('material_get_info',path=SKY).get('comments',[]):
        call('material_set_comment',material_path=SKY,comment_id=comment['id'],text='Dark dream atmosphere',
             node_pos=[-960,-80],size=[900,450],show_bubble=True,color_bubble=True)
    call('material_compile', material_path=SKY)


if __name__ == '__main__':
    assert not call('editor_get_state')['pie_running']
    token = h.lease_acquire(h.agent_id(), [f'asset:{ROOT}'], ttl_s=90, wait_s=60)
    try:
        for step in sys.argv[1:] or ('lean', 'sky'):
            {'lean': lean, 'sky': sky, 'city': city, 'ground': ground}[step]()
        call('asset_save', asset_paths=[MAT, SKY] if len(sys.argv) < 2 else [{'lean': MAT, 'sky': SKY, 'city': CITY, 'ground': CITY}[s] for s in sys.argv[1:]])
        print('LEAN OK', sys.argv[1:] or 'lean sky')
    finally:
        h.release(h.agent_id(), token)
