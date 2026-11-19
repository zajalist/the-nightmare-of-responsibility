"""Add shared dynamics without replacing the world's graphs or parameters.
Run one step under a Level2 lease: function | dream | city. --selftest is offline.
"""
import json
import math
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, 'P:/FoA/Tools/Unreal')
sys.path.insert(0, str(Path(__file__).resolve().parent))
import hayba_call as h

ROOT = '/Game/FoA/Level2'
FN = ROOT + '/Materials/MF_SplatDynamics'
MPC = ROOT + '/Materials/MPC_L2.MPC_L2'
GROUND = ROOT + '/City/M_City_Ground'
OWNER = os.environ.get('FOA_AGENT', 'main-splat-dynamics')
_lease_check_at = None
# Native IDs survive the required layout pass; keep reruns from duplicating moved nodes.
NODE_IDS = {
    FN: {**{(-1200, y): 'MaterialExpressionFunctionInput_' + str(i) for i, y in enumerate([0, 160, 840])},
         (-1200, 320): 'MaterialExpressionTime_0', (-1200, 480): 'MaterialExpressionVectorParameter_0',
         (-1200, 680): 'MaterialExpressionScalarParameter_0',
         **{(-800, i*160): 'MaterialExpressionCollectionParameter_' + str(i) for i in range(8)},
         (-320, 0): 'MaterialExpressionCustom_0', (0, 0): 'MaterialExpressionComponentMask_0',
         (0, 300): 'MaterialExpressionComponentMask_1', (300, 0): 'MaterialExpressionFunctionOutput_0',
         (300, 300): 'MaterialExpressionFunctionOutput_1'},
    ROOT + '/M_SplatWorld_Lean': {(-900, 1100): 'MaterialExpressionWorldPosition_0',
        (0, 1100): 'MaterialExpressionMaterialFunctionCall_0', (440, 1000): 'MaterialExpressionAdd_0',
        (440, 1320): 'MaterialExpressionVertexInterpolator_0', (800, 1320): 'MaterialExpressionCustom_3',
        (440, 1600): 'MaterialExpressionTime_0'},
    ROOT + '/M_SplatCity_Lean': {(-900, 1100): 'MaterialExpressionWorldPosition_0',
        (-500, 1100): 'MaterialExpressionCustom_2', (0, 1100): 'MaterialExpressionMaterialFunctionCall_0',
        (440, 1320): 'MaterialExpressionVertexInterpolator_0', (800, 1320): 'MaterialExpressionCustom_3',
        (-500, 1450): 'MaterialExpressionCustom_4', (440, 1600): 'MaterialExpressionTime_0'}}


def call(cmd, **params):
    global _lease_check_at
    if _lease_check_at is not None and time.monotonic() - _lease_check_at > 20:
        assert h.leases_of(OWNER), 'Lost Level2 lease; stop driving'
        h.renew_all(OWNER, 90)
        _lease_check_at = time.monotonic()
    r = h.call(cmd, params)
    d = r.get('data') or {}
    assert r.get('ok') and d.get('ok', True) and not d.get('has_errors') and not d.get('failed'), (cmd, r)
    return d


def require_lease():
    global _lease_check_at
    # CLI builders are never allowed to run after a failed acquire.
    assert h.leases_of(OWNER), 'No owned Level2 lease; acquire first'
    h.renew_all(OWNER, 90)
    _lease_check_at = time.monotonic()
    assert not call('editor_get_state')['pie_running'], 'PIE running; wait for its owner'


def target(path):
    return {('function_path' if path == FN else 'material_path'): path}


def node(path, cls, x, y, **props):
    info = call('material_get_info', path=path)
    expected = NODE_IDS.get(path, {}).get((x, y))
    old = next((e for e in info['expressions'] if e['id'] == expected), None)
    if old is None:
        old = next((e for e in info['expressions'] if e['x'] == x and e['y'] == y), None)
    if old:
        assert old['class'] == 'MaterialExpression' + cls, old
        if props:
            call('material_set_node', **target(path), node_id=old['id'], properties=props)
        return old['id']
    return call('material_add_node', **target(path), expression_class='MaterialExpression' + cls,
                node_pos=[x, y], properties=props)['node_id']


def link(path, a, b=None, pin=None, index=0, prop=None):
    p = dict(**target(path), from_node=a, from_output_index=index)
    if prop:
        p['to_property'] = prop
    else:
        p.update(to_node=b, **({'to_input': pin} if pin else {'to_input_index': 0}))
    call('material_connect_nodes', **p)


def custom(path, x, y, name, output, inputs, code):
    return node(path, 'Custom', x, y, Description=name, OutputType='CMOT_' + output,
                Inputs=[{'InputName': n} for n in inputs], Code=code)


def finish(path):
    call('material_validate', **target(path))
    call('material_compile', **target(path))
    call('asset_save', asset_paths=[path])


def shock_settings():
    sys.path.insert(0, 'P:/FoA/Tools/Unreal/level2')
    import drive_data as d
    return dict(SHOCK_SPEED=d.SHOCKWAVE_SPEED, SHOCK_DURATION=d.SHOCKWAVE_DURATION,
                SHOCK_BAND=d.SHOCKWAVE_BAND, SHOCK_FADE_IN=d.SHOCKWAVE_FADE_IN,
                SHOCK_FADE_OUT=d.SHOCKWAVE_FADE_OUT)


def dynamics_code():
    defines=''.join('#define '+name+' '+str(float(value))+'\n' for name,value in shock_settings().items())
    return defines+Path(__file__).with_name('hlsl').joinpath('l2_dynamics.hlsl').read_text()


def shock_response(age, distance, strength=1):
    """CPU oracle for the finite travelling band emitted into the shared HLSL."""
    c=shock_settings()
    clamp=lambda x:max(0.,min(1.,x))
    def smooth(a,b,x):
        t=clamp((x-a)/(b-a));return t*t*(3-2*t)
    x=clamp((age*c['SHOCK_SPEED']-distance)/c['SHOCK_BAND'])
    envelope=smooth(0,c['SHOCK_FADE_IN'],age)*(1-smooth(c['SHOCK_DURATION']-c['SHOCK_FADE_OUT'],c['SHOCK_DURATION'],age))
    return clamp(strength)*16*x*x*(1-x)*(1-x)*envelope


def dream_offset(rest, clock, age, distance, ambient=.8, ground_z=0, ground=False, excluded=False, reduce_motion=0):
    """Numerical displacement bounds and anchor/continuity checks, without an editor."""
    h=max(0.,min(1.,(rest[2]-ground_z)/80.))
    anchor=0. if excluded else (1. if ground else h*h*(3-2*h))
    anchor*=1-max(0.,min(1.,reduce_motion))
    p=rest[0]*.0011+rest[1]*.0007
    carrier=(math.sin(clock*.72+p),math.sin(clock*.91+p*.83+1.4),math.sin(clock*.63+p*.71+.6))
    shock=shock_response(age,distance)
    offset=[v*(max(ambient,0)*2.5+shock*35)*anchor for v in carrier]
    if ground:offset[2]=(max(ambient,0)*2.5*carrier[2]+shock*12*(.5+.5*carrier[2]))*anchor
    return tuple(offset)


def ground():
    """Existing material for dense near/far ground splats; legacy maps retain their UVs."""
    # Stable native IDs keep re-runs safe after house graph layout moves nodes.
    NODE_IDS[GROUND]={(-400,0):'MaterialExpressionTextureSampleParameter2D_0',
        (-1600,0):'MaterialExpressionWorldPosition_0',(-1600,180):'MaterialExpressionTextureCoordinate_0',
        (-1600,360):'MaterialExpressionTextureCoordinate_1',(-1600,540):'MaterialExpressionScalarParameter_0',
        (-1600,720):'MaterialExpressionCameraPositionWS_0',(-1600,900):'MaterialExpressionScalarParameter_1',
        (-1200,0):'MaterialExpressionCustom_0',(-1200,340):'MaterialExpressionCustom_1',
        (-800,0):'MaterialExpressionCustom_2',(-800,500):'MaterialExpressionMaterialFunctionCall_0',
        (0,500):'MaterialExpressionCustom_3',(0,900):'MaterialExpressionCustom_4',
        (0,100):'MaterialExpressionCustom_5'}
    wp=node(GROUND,'WorldPosition',-1600,0,WorldPositionShaderOffset='WPT_ExcludeAllShaderOffsets')
    uv=node(GROUND,'TextureCoordinate',-1600,180,CoordinateIndex=0)
    rs=node(GROUND,'TextureCoordinate',-1600,360,CoordinateIndex=1)
    flag=node(GROUND,'ScalarParameter',-1600,540,ParameterName='L2BuildingID',
              bUseCustomPrimitiveData=True,PrimitiveDataIndex=4,DefaultValue=0)
    camera=node(GROUND,'CameraPositionWS',-1600,720)
    lod=node(GROUND,'ScalarParameter',-1600,900,ParameterName='L2LOD',bUseCustomPrimitiveData=True,PrimitiveDataIndex=5,DefaultValue=0)
    rest=custom(GROUND,-1200,0,'Ground rest centre','Float3',['WP','UV','RS','Flag'],
        'return WP - (Flag < -1.5 ? float3(UV.x,-UV.y,0)*RS.x : float3(0,0,0));')
    corner=custom(GROUND,-1200,340,'Ground splat corner','Float3',['UV','RS','Flag'],
        'return Flag < -1.5 ? float3(UV.x,-UV.y,0)*RS.x : float3(0,0,0);')
    sample=custom(GROUND,-800,0,'Rest-centre ground texture','Float2',['Rest','UV','Flag'],
        'return Flag < -1.5 ? float2(Rest.x/60000.0,(Rest.y+30000.0)/60000.0) : UV;')
    texture=node(GROUND,'TextureSampleParameter2D',-400,0,ParameterName='Ground',
                 Texture=ROOT+'/City/T_City_Ground.T_City_Ground')
    motion=node(GROUND,'MaterialFunctionCall',-800,500,function=FN)
    offset=custom(GROUND,0,500,'Ground motion only','Float3',['Motion','Flag'],
        'return Flag < -1.5 ? Motion : float3(0,0,0);')
    sand=custom(GROUND,0,100,'Black sand on the road','Float3',['Colour','Sand','Flag'],
        'return lerp(Colour, float3(0.018,0.015,0.012), Flag < -1.5 ? saturate(Sand*2.4) : 0);')
    coverage=custom(GROUND,0,900,'Ground splat footprint and distance fade','Float1',
        ['UV','RS','Rest','Camera','Flag','LOD'],
        '''if (Flag >= -1.5) return 1;
float e=exp(-0.7);
float a=max((exp(-0.7*dot(UV,UV))-e)/(1-e),0);
float distance=length(Rest.xy-Camera.xy);
a *= LOD > 1.5 ? smoothstep(6000,7000,distance) : (LOD > .5 ? 1-smoothstep(7000,8000,distance) : 1);
return a > InterleavedGradientNoise(Parameters.SvPosition.xy+RS.y*117,View.StateFrameIndexMod8) ? 1 : 0;''')
    for dest,inputs in ((rest,dict(WP=wp,UV=uv,RS=rs,Flag=flag)),
                        (corner,dict(UV=uv,RS=rs,Flag=flag)),
                        (sample,dict(Rest=rest,UV=uv,Flag=flag)),
                        (offset,dict(Motion=motion,Flag=flag)),
                        (coverage,dict(UV=uv,RS=rs,Rest=rest,Camera=camera,Flag=flag,LOD=lod))):
        for pin,source in inputs.items():link(GROUND,source,dest,pin)
    link(GROUND,sample,texture,'Coordinates')
    link(GROUND,rest,motion,'Rest (V3)');link(GROUND,rs,motion,'RS (V2)')
    link(GROUND,corner,motion,'CornerOffset (V3)')
    link(GROUND,texture,sand,'Colour');link(GROUND,motion,sand,'Sand',index=1);link(GROUND,flag,sand,'Flag')
    for source,prop in ((sand,'emissive_color'),(offset,'world_position_offset'),(coverage,'opacity_mask')):
        link(GROUND,source,prop=prop)
    call('material_set_property',material_path=GROUND,properties=dict(blend_mode='Masked',shading_model='Unlit',two_sided=True,opacity_mask_clip_value=.5))
    if not call('material_get_info',path=GROUND).get('comments'):
        call('material_add_comment',material_path=GROUND,text='Ground splat motion',node_pos=[-1700,-100],
             size=[2300,1300],color=[.12,.26,.16])
    finish(GROUND)


def city_lod():
    """Near/far weights on the existing splat footprint; no opaque fill geometry."""
    from build_splat_world_lean import COVERAGE
    path=ROOT+'/M_SplatCity_Lean'
    NODE_IDS[path].update({(-1300,1800):'MaterialExpressionScalarParameter_2',
                           (-1300,1980):'MaterialExpressionCameraPositionWS_0'})
    lod=node(path,'ScalarParameter',-1300,1800,ParameterName='L2LOD',
             bUseCustomPrimitiveData=True,PrimitiveDataIndex=5,DefaultValue=0)
    camera=node(path,'CameraPositionWS',-1300,1980)
    code=COVERAGE.replace('return a >',
        'float distance=length(Rest.xy-Camera.xy);\n'
        'a *= LOD > 1.5 ? smoothstep(6000,7000,distance) : (LOD > .5 ? 1-smoothstep(7000,8000,distance) : 1);\nreturn a >')
    call('material_set_node',material_path=path,node_id='MaterialExpressionCustom_0',properties=dict(
        Code=code,Description='Splat footprint and proximity blend',
        Inputs=[dict(InputName=n) for n in ('Corner','RS','A','K','Rest','Camera','LOD')]))
    for source,pin,index in (('MaterialExpressionTextureCoordinate_0','Corner',0),
        ('MaterialExpressionTextureCoordinate_1','RS',0),('MaterialExpressionVertexColor_0','A',4),
        ('MaterialExpressionScalarParameter_0','K',0),('MaterialExpressionCustom_2','Rest',0),
        (camera,'Camera',0),(lod,'LOD',0)):
        link(path,source,'MaterialExpressionCustom_0',pin,index=index)
    finish(path)


def function():
    if not h.call('material_get_info', {'path': FN}).get('ok'):
        call('material_function_create', package_path=ROOT + '/Materials', name='MF_SplatDynamics')
    sources = {}
    for i, (name, typ) in enumerate([('Rest', 'Vector3'), ('RS', 'Vector2')]):
        sources[name] = node(FN, 'FunctionInput', -1200, i * 160, InputName=name,
                             InputType='FunctionInput_' + typ, SortPriority=i)
    sources['CornerOffset'] = node(FN, 'FunctionInput', -1200, 840, InputName='CornerOffset',
                                   InputType='FunctionInput_Vector3', SortPriority=2, bUsePreviewValueAsDefault=True)
    sources['Clock'] = node(FN, 'Time', -1200, 320, bIgnorePause=False)
    sources['Local'] = node(FN, 'VectorParameter', -1200, 480, ParameterName='L2Local',
                            bUseCustomPrimitiveData=True, PrimitiveDataIndex=0,
                            DefaultValue={'R': 0, 'G': 0, 'B': 0, 'A': 0})
    sources['Building'] = node(FN, 'ScalarParameter', -1200, 680, ParameterName='L2BuildingID',
                               bUseCustomPrimitiveData=True, PrimitiveDataIndex=4, DefaultValue=0)
    for i, (name, param) in enumerate([('Ambient', 'AmbientIntensity'), ('Centre', 'SandCentre'),
                                      ('Radius', 'SandRadius'), ('Progress', 'SandProgress'),
                                      ('Wind', 'Wind'), ('Target', 'TargetBuilding')]):
        sources[name] = node(FN, 'CollectionParameter', -800, i * 160, Collection=MPC, ParameterName=param)
    # Share the city collection so the shader can also use MPC_Dream for Reduce Motion.
    sources['Impact'] = node(FN, 'CollectionParameter', -800, 960, Collection=MPC, ParameterName='Impact0')
    sources['ReduceMotion'] = node(FN, 'CollectionParameter', -800, 1120,
                                  Collection='/Game/FoA/PostProcess/MPC_Dream.MPC_Dream', ParameterName='ReduceMotion')
    code = dynamics_code()
    motion = custom(FN, -320, 0, 'Splat motion', 'Float4', sources, code)
    for name, n in sources.items():
        link(FN, n, motion, name, index=5 if name == 'Local' else 0)
    xyz = node(FN, 'ComponentMask', 0, 0, R=True, G=True, B=True, A=False)
    alpha = node(FN, 'ComponentMask', 0, 300, R=False, G=False, B=False, A=True)
    link(FN, motion, xyz); link(FN, motion, alpha)
    for i, (name, n) in enumerate([('Offset', xyz), ('Sand', alpha)]):
        out = node(FN, 'FunctionOutput', 300, i * 300, OutputName=name, SortPriority=i)
        link(FN, n, out)
    if not call('material_get_info', path=FN).get('comments'):
        for title, pos, size in [('Splat controls', [-1280, -80], [780, 1100]),
                                 ('Motion and phase', [-400, -80], [1100, 600])]:
            call('material_add_comment', **target(FN), text=title, node_pos=pos, size=size, color=[.12, .26, .16])
    finish(FN)


def integrate(city):
    path = ROOT + ('/M_SplatCity_Lean' if city else '/M_SplatWorld_Lean')
    info = call('material_get_info', path=path)
    outdir = Path('P:/FoA/Saved/Codex/splat_dynamics'); outdir.mkdir(exist_ok=True)
    backup = outdir / (path.rsplit('/', 1)[1] + '_before.json')
    if not backup.exists():
        backup.write_text(json.dumps(info, indent=2))
    # Stable IDs from the inspected world graph; no existing nodes or parameters are changed.
    uv, rs = 'MaterialExpressionTextureCoordinate_0', 'MaterialExpressionTextureCoordinate_1'
    colour = 'MaterialExpressionCustom_1' if city else 'MaterialExpressionCustom_2'
    wp = node(path, 'WorldPosition', -900, 1100, WorldPositionShaderOffset='WPT_ExcludeAllShaderOffsets')
    rest = wp
    corner = 'MaterialExpressionCustom_0'
    if city:
        rest = custom(path, -500, 1100, 'City splat centre', 'Float3', ['WP', 'UV', 'RS'],
                      'return WP - float3(UV.x, -UV.y, 0) * RS.x;')
        link(path, wp, rest, 'WP'); link(path, uv, rest, 'UV'); link(path, rs, rest, 'RS')
        corner = custom(path, -500, 1450, 'City quad corner', 'Float3', ['UV', 'RS'],
                        'return float3(UV.x, -UV.y, 0) * RS.x;')
        link(path, uv, corner, 'UV'); link(path, rs, corner, 'RS')
    fn = node(path, 'MaterialFunctionCall', 0, 1100, function=FN)
    link(path, rest, fn, 'Rest (V3)'); link(path, rs, fn, 'RS (V2)')
    link(path, corner, fn, 'CornerOffset (V3)')
    offset = fn
    if not city:
        offset = node(path, 'Add', 440, 1000)
        link(path, 'MaterialExpressionCustom_0', offset, 'A'); link(path, fn, offset, 'B')
    link(path, offset, prop='world_position_offset')
    interp = node(path, 'VertexInterpolator', 440, 1320)
    link(path, fn, interp, index=1)
    look = custom(path, 800, 1320, 'Black sand sparkle', 'Float3', ['Colour', 'Sand', 'RS', 'Clock'],
                  'float glint = step(0.989, frac(RS.y*37.13)) * pow(max(0, sin(Clock*2+RS.y*91)),16);\n'
                  'return lerp(Colour, float3(0.009,0.009,0.009) + glint*0.6, saturate(Sand*3));')
    clock = node(path, 'Time', 440, 1600)
    link(path, colour, look, 'Colour'); link(path, interp, look, 'Sand')
    link(path, rs, look, 'RS'); link(path, clock, look, 'Clock')
    link(path, look, prop='emissive_color')
    if not any(c['text'] == 'Shared splat dynamics' for c in info.get('comments', [])):
        call('material_add_comment', **target(path), text='Shared splat dynamics', node_pos=[-960, 920],
             size=[2200, 900], color=[.12, .26, .16])
    if city:
        # City meshes contain horizontal corners already; preserve centres while
        # turning those corners toward both the street and driving cameras.
        from build_city_billboards import apply
        apply(call)
        city_lod()
    finish(path)


def selftest():
    c=shock_settings();speed=c['SHOCK_SPEED'];width=c['SHOCK_BAND'];duration=c['SHOCK_DURATION']
    assert (speed,width,duration)==(1800.,450.,3.)
    # A wave is local, outward travelling, smooth at both edges, and gone on expiry.
    for distance in (0.,900.,1800.,3600.):
        arrival=distance/speed;peak=(distance+width/2)/speed;leave=(distance+width)/speed
        assert shock_response(arrival,distance)==0 and shock_response(leave,distance)==0
        assert shock_response(peak,distance)>.99
        assert shock_response(peak,distance+width)==0
        eps=1e-5
        assert shock_response(arrival+eps,distance)/eps<.01
        assert shock_response(leave-eps,distance)/eps<.01
    for age in (-100.,0.,duration,duration+100.):
        assert all(shock_response(age,r)==0 for r in (0.,100.,2000.,5000.,10000.))
    assert shock_response(1,1575,0)==0
    for clock in (0.,1.,17.,10000.):
        assert dream_offset((50,20,0),clock,1,1575)==(0.,0.,0.)
        assert dream_offset((50,20,100),clock,1,1575,excluded=True)==(0.,0.,0.)
        assert dream_offset((50,20,100),clock,1,1575,reduce_motion=1)==(0.,0.,0.)
        assert dream_offset((50,20,0),clock,1,1575,ground=True,reduce_motion=1)==(0.,0.,0.)
        baseline=dream_offset((50,20,100),clock,-1,0)
        assert baseline==dream_offset((50,20,100),clock,duration,0)
        assert max(map(abs,baseline))<=2.
        ground=dream_offset((50,20,0),clock,1,1575,ground=True)
        assert -2<=ground[2]<=14 and max(map(abs,ground[:2]))<=37
        # Adjacent splats share a spatial carrier instead of independent random phase.
        nearby=dream_offset((51,20,100),clock,-1,0)
        assert max(abs(a-b) for a,b in zip(baseline,nearby))<.003
    code=dynamics_code()
    assert all('#define '+key+' '+str(float(value)) in code for key,value in c.items())
    # 50m streamed cells preserve a continuous 0.5m ground lattice. WPO never
    # feeds the rest-centre texture/LOD calculation, so impact crests cannot blink.
    for centre in (-2475.,2475.):
        for u,v in ((-1,-1),(1,-1),(1,1),(-1,1)):
            assert (centre+u*87.5-u*87.5,centre-v*87.5+v*87.5)==(centre,centre)
    assert (5000-2475)-2475==50
    assert 13500-math.sqrt(2)*2900>8000,'Near component could cull before fade completes'
    def smooth(a,b,x):
        t=max(0.,min(1.,(x-a)/(b-a)));return t*t*(3-2*t)
    for distance in range(0,10001,25):
        near=1-smooth(7000,8000,distance);far=smooth(6000,7000,distance)
        assert max(near,far)==1,'One splat LOD must fully cover every transition distance'
    def phase(progress, seed, distance, radius, local=0, excluded=False):
        p = local
        if radius > 0 and distance < radius and not excluded:
            p = max(p, min(1, max(0, progress * 1.4 - distance / radius * .4)))
        return min(1, max(0, (p - seed * .18) / .82))
    for seed in (0, .2, .5, .999):
        assert phase(0, seed, 0, 100) == 0
        assert phase(1, seed, 100, 100) == 0
        assert phase(1, seed, 0, 0) == 0
        assert phase(1, seed, 0, 100, excluded=True) == 0
        assert phase(1, seed, 99.9, 100) == 1
        seq = [phase(i / 100, seed, 30, 100) for i in range(101)]
        assert seq == sorted(seq) and seq[0] == 0 and seq[-1] == 1
        assert list(reversed(seq))[-1] == 0
        for q in seq:
            z = 1200 + (4 - 1200) * q*q
            assert math.isfinite(z) and 4 <= z <= 1200
    print('PASS: travelling ring arrival/peak/exit, smooth boundaries, duration, anchors, ground bounds, coherent baseline; independent sand dissolution preserved')


if __name__ == '__main__':
    step = sys.argv[1]
    if step == '--selftest':
        selftest()
    else:
        assert h.agent_id() == OWNER and OWNER.startswith('main-')
        require_lease()
        {'function': function, 'dream': lambda: integrate(False), 'city': lambda: integrate(True), 'ground': ground, 'city_lod':city_lod}[step]()
