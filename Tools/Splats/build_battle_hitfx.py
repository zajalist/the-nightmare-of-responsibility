"""Assets for BP_BattleSand's stronger hit reads (world lane, plan approved 2026-11-10). Hayba for materials:
  python Tools/Splats/build_battle_hitfx.py            (leases /Game/FoA/VFX/Sand for one run)
MI_Sand_BurstDir   child of MI_Sand_Burst: up-bias 4 turns the radial burst into a cone (the component's +Z is the
                   throw direction), gravity 0.3, a little faster. Placed and aimed by BP_BattleSand.Blast.
M_PP_SandVignette  post-process (after tonemapping): the frame's edges sink into dark sand grain (T_SandGrain, no new
                   texture). BP_BattleSand pulses its own PostProcessComponent's blend weight 0 -> 1 -> 0 on a hero hit.
CS_SandHit         a legacy camera shake, about 0.6 deg for 0.15 s (skipped by BP_BattleSand when MPC ReduceMotion = 1)."""
import sys

sys.path.insert(0, 'P:/FoA/Tools/Unreal')
import hayba_call as h  # noqa: E402

D = '/Game/FoA/VFX/Sand'
MI = f'{D}/MI_Sand_BurstDir'
PP = f'{D}/M_PP_SandVignette'
SHAKE = '/Game/FoA/VFX/CS_SandHit'   # blueprint_create puts it one folder up
VIGNETTE = """// Edges sink into dark sand grain; W = pulse strength from the blend weight (the component does the 0..1 fade).
float2 p = (UV - 0.5) * float2(View.ViewSizeAndInvSize.x * View.ViewSizeAndInvSize.w, 1.0) * 2.0;
float edge = smoothstep(0.55, 1.25, length(p));
float g = Tex.SampleLevel(TexSampler, UV * float2(View.ViewSizeAndInvSize.x * View.ViewSizeAndInvSize.w, 1.0) * 6.0, 0).r;
float sand = saturate(edge * (0.75 + 0.5 * g));
return Col * (1.0 - 0.85 * sand);"""


def call(cmd, **p):
    r = h.call(cmd, p)
    assert r.get('ok'), r
    d = r.get('data', {})
    assert d.get('ok', True) and not d.get('errors') and not d.get('failed') and not d.get('has_errors'), d
    return d


def mi():
    if not h.call('material_get_info', {'path': MI}).get('ok'):
        call('material_create_instance', parent_material_path='/Game/FoA/VFX/Splats/Instances/MI_Sand_Burst', package_path=D,
             name='MI_Sand_BurstDir')
    call('material_set_param', instance_path=MI, param_name='Tune', value=[1.4, 4.0, 0.3, 10.0])


def pp():
    if not h.call('material_get_info', {'path': PP}).get('ok'):
        call('material_create', package_path=D, name='M_PP_SandVignette')
    info = call('material_get_info', path=PP)
    have = {(e['x'], e['y']): e['id'] for e in info['expressions']}

    def node(pos, cls, props):
        return have.get(tuple(pos)) or call('material_add_node', material_path=PP, expression_class='MaterialExpression' + cls,
                                            node_pos=pos, properties=props)['node_id']
    st = node([-900, 0], 'SceneTexture', {'SceneTextureId': 'PPI_PostProcessInput0'})
    uv = node([-900, 200], 'ScreenPosition', {})
    tex = node([-900, 360], 'TextureObject', {'Texture': '/Game/FoA/VFX/Sand/Textures/T_SandGrain.T_SandGrain'})
    cu = node([-500, 100], 'Custom', {'Description': 'Sand edge', 'OutputType': 'CMOT_Float3', 'Code': VIGNETTE,
                                      'Inputs': [{'InputName': n} for n in ('Col', 'UV', 'Tex')]})
    for src, pin in ((st, 'Col'), (uv, 'UV'), (tex, 'Tex')):
        call('material_connect_nodes', material_path=PP, from_node=src, from_output_index=0, to_node=cu, to_input=pin)
    call('material_connect_nodes', material_path=PP, from_node=cu, from_output_index=0, to_property='emissive_color')
    call('material_set_property', material_path=PP, properties={'domain': 'MD_PostProcess'})   # default location: after tonemapping
    call('material_compile', material_path=PP)


def shake():
    if not h.call('blueprint_get_info', {'path': SHAKE}).get('ok'):
        call('blueprint_create', package_path='/Game/FoA/VFX', name='CS_SandHit', parent_class_path='/Script/EngineCameras.LegacyCameraShake')
    call('blueprint_set_defaults', path=SHAKE, properties={
        'OscillationDuration': 0.15, 'OscillationBlendInTime': 0.02, 'OscillationBlendOutTime': 0.08,
        'RotOscillation': '(Pitch=(Amplitude=0.6,Frequency=24.0,Waveform=SineWave),Yaw=(Amplitude=0.4,Frequency=19.0,'
                          'Waveform=SineWave),Roll=(Amplitude=0.0,Frequency=0.0,Waveform=SineWave))'})
    call('blueprint_compile', path=SHAKE)


if __name__ == '__main__':
    import time
    while h.call('editor_get_state', {}).get('data', {}).get('pie_running'):   # material and asset edits refuse during PIE
        time.sleep(5)
    token = h.lease_acquire(h.agent_id(), [f'asset:{D}'], ttl_s=90, wait_s=120)
    try:
        for step in sys.argv[1:] or ('mi', 'pp', 'shake'):
            {'mi': mi, 'pp': pp, 'shake': shake}[step]()
        call('asset_save', asset_paths=[MI, PP, SHAKE])
        print('HITFX OK')
    finally:
        h.release(h.agent_id(), token)
