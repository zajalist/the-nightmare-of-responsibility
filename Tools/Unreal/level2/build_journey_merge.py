"""One collision-free Nightmare visual shell; no Nightmare pawn, AI, timers or player mutation.

Build steps: material, skeleton, components, Initialize, SetAmount, SetVisible, Restore.
Journey spawns BP_L2Merge once, Initialize(Player), then SetAmount(0..1).
SetVisible(false) while driving; Restore() before leaving L2. Human overlay remains Journey-owned.
The two shell surfaces follow the visible Body and Face final poses, avoiding retarget offsets.
"""
import os
from pathlib import Path
import sys

sys.path[:0] = [str(Path(__file__).parent), 'P:/FoA/Tools/Unreal']
import hayba_call as h
from build_drive import G, call, cls, A, SC, SL

ROOT = '/Game/FoA/Level2/Journey'
BP = ROOT + '/BP_L2Merge'
MAT = ROOT + '/M_L2MergeShell'
PLAYER = '/Game/FoA/Characters/Player/BP_FoAPlayer'
SKIN = '/Script/Engine.SkinnedMeshComponent:'
MESH = '/Script/Engine.MeshComponent:'
SIGNATURES = {'Initialize': [('Player', 'object:' + cls(PLAYER))],
              'SetAmount': [('Amount', 'float')], 'SetVisible': [('Visible', 'bool')], 'Restore': []}

# Rest-pose regions stay on their bones; no clock, flash or shared world MPC is required.
SHADER = '''
float a = saturate(Amount);
float height = saturate((P.z - HeightMin) / max(HeightRange, 1.0));
float side = max(abs(P.x), abs(P.y)) / max(SideRange, 1.0);
float hands = step(0.52, side) * step(0.32, height) * (1.0-step(0.82, height));
float shoulders = step(0.22, side) * step(0.66, height) * (1.0-step(0.86, height));
float head = step(0.82, height);
float coverage = saturate((a-0.6)/0.4);
coverage = max(coverage, hands*saturate(a/0.2));
coverage = max(coverage, shoulders*saturate((a-0.2)/0.2));
coverage = max(coverage, head*saturate((a-0.4)/0.2));
uint3 c = uint3(int3(floor(P * 7.0)));
uint h = c.x*73856093u ^ c.y*19349663u ^ c.z*83492791u;
h = ((h >> 16u)^h)*2246822519u;
float grain = float(h >> 8u)*(1.0/16777216.0);
float mask = a <= 0.0 ? 0.0 : (a >= 0.999 ? 1.0 : step(grain,coverage));
return float4((0.002 + grain*0.004).xxx,mask);
'''


def material():
    if not h.call('material_get_info', {'path': MAT}).get('ok'):
        call('material_create', package_path=ROOT, name='M_L2MergeShell')
    expressions = call('material_get_info', path=MAT).get('expressions', [])
    call('material_set_property', material_path=MAT, properties={
        'blend_mode': 'Masked', 'shading_model': 'DefaultLit', 'opacity_mask_clip_value': .35})
    call('material_set_property', material_path=MAT, properties={'used_with_skeletal_meshes': True})

    def node(kind, position, **properties):
        old = next((n for n in expressions if n['class'].endswith(kind)
                    and [n.get('x'), n.get('y')] == position), None)
        if old:
            if properties:
                call('material_set_node', material_path=MAT, node_id=old['id'], properties=properties)
            return old['id']
        return call('material_add_node', material_path=MAT, expression_class=kind,
                    node_pos=position, properties=properties)['node_id']

    pos = node('MaterialExpressionPreSkinnedPosition', [-1200, 0])
    local = node('MaterialExpressionVertexInterpolator', [-960, 0])
    call('material_connect_nodes', material_path=MAT, from_node=pos, to_node=local, to_input_index=0)
    inputs = [('P', local)]
    for index, (name, value) in enumerate((('Amount', 0), ('HeightMin', 0), ('HeightRange', 180), ('SideRange', 85))):
        inputs.append((name, node('MaterialExpressionScalarParameter', [-1200, 180 + index*180],
                                 ParameterName=name, DefaultValue=value)))
    shell = node('MaterialExpressionCustom', [-700, 0], Description='Merge silhouette',
                 OutputType='CMOT_Float4', Code=SHADER, Inputs=[{'InputName': name} for name, _ in inputs])
    for name, source in inputs:
        call('material_connect_nodes', material_path=MAT, from_node=source, to_node=shell, to_input=name)
    rgb = node('MaterialExpressionComponentMask', [-400, 0], R=True, G=True, B=True, A=False)
    alpha = node('MaterialExpressionComponentMask', [-400, 180], R=False, G=False, B=False, A=True)
    rough = node('MaterialExpressionConstant', [-400, 360], R=.9)
    for target in (rgb, alpha):
        call('material_connect_nodes', material_path=MAT, from_node=shell, to_node=target, to_input='Input')
    for source, output in ((rgb, 'base_color'), (alpha, 'opacity_mask'), (rough, 'roughness')):
        call('material_connect_nodes', material_path=MAT, from_node=source, to_property=output)
    if not call('material_get_info', path=MAT).get('comments'):
        call('material_add_comment', material_path=MAT, text='Hands shoulders head',
             node_pos=[-1260, -80], size=[1140, 990], color=[.15, .18, .22])
    valid = call('material_validate', material_path=MAT)
    assert valid.get('ok') and not valid.get('problems'), valid
    result = call('material_compile', material_path=MAT)
    assert result.get('saved') and not result.get('has_errors') and not result.get('errors'), result


def skeleton():
    if not h.call('blueprint_get_info', {'path': BP}).get('ok'):
        call('blueprint_create', package_path=BP, name='BP_L2Merge', parent_class_path='/Script/Engine.Actor')
    info = call('blueprint_get_info', path=BP)
    variables = {v['name'] for v in info['variables']}
    for name, kind, default in (('MergeAmount', 'float', '0'), ('Visible', 'bool', 'true')):
        if name not in variables:
            call('blueprint_add_variable', path=BP, variable_name=name, variable_type=kind,
                 default_value=default, category='Merge')
    for name, inputs in SIGNATURES.items():
        if name not in info['functions']:
            call('blueprint_add_function', path=BP, function_name=name,
                 inputs=[dict(name=n, type=t) for n, t in inputs])
    for name in ('Shell', 'HeadShell'):
        if not any(c['name'] == name for c in info.get('components', [])):
            call('blueprint_add_component', path=BP, component_name=name,
                 component_class_path='/Script/Engine.SkeletalMeshComponent')
    result = call('blueprint_compile', path=BP)
    assert not result.get('error_count'), result
    call('asset_save', asset_paths=[BP])


def initialize():
    g = G(BP, 'Initialize')
    gate = g.branch(g.f(SL+'IsValid', Object=g.arg('Player'))); g.side(gate)
    source = g.getv('Body', target=g.arg('Player'), path=PLAYER)
    gate = g.branch(g.f(SL+'IsValid', Object=source)); g.side(gate)
    face = g.getv('Face', target=g.arg('Player'), path=PLAYER)
    gate = g.branch(g.f(SL+'IsValid', Object=face)); g.side(gate)
    g.do(A+'SetActorEnableCollision', bNewActorEnableCollision=False)
    g.do(A+'SetOwner', NewOwner=g.arg('Player'))
    g.do(A+'K2_AttachToComponent', Parent=source, LocationRule='SnapToTarget', RotationRule='SnapToTarget',
         ScaleRule='KeepRelative', bWeldSimulatedBodies=False)
    g.do(SC+'SetRelativeScale3D', self=g.getv('Shell'), NewScale3D='(X=1.02,Y=1.02,Z=1.0)')
    g.do(SKIN+'SetLeaderPoseComponent', self=g.getv('Shell'), NewLeaderBoneComponent=source,
         bForceUpdate=True, bInFollowerShouldTickPose=False)
    head = g.getv('HeadShell')
    g.do(SC+'K2_AttachToComponent', self=head, Parent=face, LocationRule='SnapToTarget',
         RotationRule='SnapToTarget', ScaleRule='KeepRelative', bWeldSimulatedBodies=False)
    g.do(SC+'SetRelativeScale3D', self=head, NewScale3D='(X=1.02,Y=1.02,Z=1.0)')
    g.do(SKIN+'SetLeaderPoseComponent', self=head, NewLeaderBoneComponent=face,
         bForceUpdate=True, bInFollowerShouldTickPose=False)
    g.setv('Visible', True)
    g.own('SetAmount', Amount=0)
    g.finish()


def set_amount():
    g = G(BP, 'SetAmount')
    amount = g.math('FClamp', Value=g.arg('Amount'), Min=0, Max=1)
    g.setv('MergeAmount', amount)
    for name in ('Shell', 'HeadShell'):
        g.do(MESH+'SetScalarParameterValueOnMaterials', self=g.getv(name),
             ParameterName='Amount', ParameterValue=amount)
    show = g.math('BooleanAND', A=g.getv('Visible'), B=g.math('Greater_DoubleDouble', A=amount, B=0))
    g.do(A+'SetActorHiddenInGame', bNewHidden=g.math('Not_PreBool', A=show))
    g.finish()


def set_visible():
    g = G(BP, 'SetVisible')
    g.setv('Visible', g.arg('Visible'))
    g.own('SetAmount', Amount=g.getv('MergeAmount'))
    g.finish()


def restore():
    g = G(BP, 'Restore')
    g.setv('Visible', False)
    g.own('SetAmount', Amount=0)
    g.do(SKIN+'SetLeaderPoseComponent', self=g.getv('Shell'), bForceUpdate=True)
    head = g.getv('HeadShell')
    g.do(SKIN+'SetLeaderPoseComponent', self=head, bForceUpdate=True)
    g.do(SC+'K2_DetachFromComponent', self=head, LocationRule='KeepWorld', RotationRule='KeepWorld', ScaleRule='KeepWorld')
    g.do(A+'K2_DetachFromActor', LocationRule='KeepWorld', RotationRule='KeepWorld', ScaleRule='KeepWorld')
    g.finish()


def components():
    try:
        call('python_exec_file', path='P:/FoA/Tools/Unreal/level2/journey_merge_setup.py',
             env={}, resources=['asset:'+ROOT])
    finally:
        result = call('blueprint_compile', path=BP)
        assert not result.get('error_count'), result
    call('asset_save', asset_paths=[BP])


STEPS = {'material': material, 'skeleton': skeleton, 'components': components, 'Initialize': initialize,
         'SetAmount': set_amount, 'SetVisible': set_visible, 'Restore': restore}


if __name__ == '__main__':
    owner = os.environ.get('FOA_AGENT', 'main-level1-merge')
    os.environ['HAYBA_AGENT_ID'] = os.environ['FOA_AGENT'] = owner
    token = h.lease_acquire(owner, ['asset:'+ROOT], ttl_s=60, wait_s=3)
    os.environ['FOA_LEASE'] = token
    try:
        assert not call('editor_get_state')['pie_running'], 'User PIE active'
        STEPS[sys.argv[1]]()
    except BaseException:
        if sys.argv[1] != 'material':
            result = call('blueprint_compile', path=BP)
            assert not result.get('error_count'), result
            call('asset_save', asset_paths=[BP])
        raise
    finally:
        h.release(owner, token)
