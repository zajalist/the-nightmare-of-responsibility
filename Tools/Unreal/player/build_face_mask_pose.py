"""Hayba C++ publisher for the face-front mask; called by the existing 30 Hz player-position timer.
Run outside the editor after PIE stops. Does not rebuild any other player function or component.
"""
import json
from pathlib import Path
import sys

sys.path.insert(0, 'P:/FoA/Tools/Unreal')
import hayba_call as hc

P = '/Game/FoA/Characters/Player/BP_FoAPlayer'
FN = 'UpdateFaceMaskPose'
MPC = '/Game/FoA/PostProcess/MPC_Dream.MPC_Dream'
OWNER = 'face_presentation'
TRACE = []


def command(name, **params):
    r = hc.call(name, params, owner=OWNER, timeout=60)
    TRACE.append(dict(command=name, reply=r))
    assert r.get('ok'), r
    d = r.get('data', {})
    assert d.get('ok', True), d
    if 'compile' in d:
        assert d['compile'].get('error_count', 0) == 0, d
    return d


def main():
    assert not command('editor_get_state')['pie_running']
    lease = hc.lease_acquire(OWNER, ['asset:' + P], ttl_s=120, wait_s=30)
    try:
        info = command('blueprint_get_info', path=P)
        if FN not in info['functions']:
            command('blueprint_add_function', path=P, function_name=FN)
        graph = command('blueprint_inspect_graph', path=P, graph_name=FN)
        entry = next(n['node_id'] for n in graph['nodes'] if n['title'] == FN)
        ops = []
        old = [n['node_id'] for n in graph['nodes'] if n['node_id'] != entry]
        if old:
            ops.append(dict(op='remove', node_ids=old))

        def node(ref, fn, x, y):
            ops.append(dict(op='add_node', ref=ref, node_type='call_function', function_name=fn, x=x, y=y))

        def pin(ref, name, value):
            ops.append(dict(op='set_pin', node_id=ref, pin_name=name, value=str(value)))

        def link(a, ap, b, bp):
            ops.append(dict(op='connect', from_node=a, from_pin=ap, to_node=b, to_pin=bp))

        K = '/Script/Engine.KismetMathLibrary:'
        SC = '/Script/Engine.SceneComponent:'
        ops.append(dict(op='add_node', ref='face', node_type='variable_get', variable_name='Face', x=0, y=300))
        for ref, bone, x, y in (('top', 'FACIAL_C_ForeheadSkin', 260, 140),
                               ('chin', 'FACIAL_C_Chin3', 260, 340),
                               ('eyeL', 'FACIAL_L_Eye', 260, 620), ('eyeR', 'FACIAL_R_Eye', 260, 820)):
            node(ref, SC + 'GetSocketLocation', x, y)
            pin(ref, 'InSocketName', bone)
            link('face', 'Face', ref, 'self')
        node('center', K + 'VLerp', 540, 140)
        link('top', 'ReturnValue', 'center', 'A'); link('chin', 'ReturnValue', 'center', 'B')
        pin('center', 'Alpha', 0.5)
        node('height', K + 'Vector_Distance', 540, 380)
        link('top', 'ReturnValue', 'height', 'V1'); link('chin', 'ReturnValue', 'height', 'V2')
        node('heightRadius', K + 'Multiply_DoubleDouble', 800, 380)
        link('height', 'ReturnValue', 'heightRadius', 'A'); pin('heightRadius', 'B', 0.53)
        node('width', K + 'Vector_Distance', 540, 700)
        link('eyeL', 'ReturnValue', 'width', 'V1'); link('eyeR', 'ReturnValue', 'width', 'V2')
        node('widthRadius', K + 'Multiply_DoubleDouble', 800, 700)
        link('width', 'ReturnValue', 'widthRadius', 'A'); pin('widthRadius', 'B', 0.94)
        node('head', SC + 'GetSocketRotation', 260, 1120)
        link('face', 'Face', 'head', 'self'); pin('head', 'InSocketName', 'head')
        # Reference head rotation is Y=-90deg. Local +Y points out of the face; local -Z is facial right.
        node('forward', K + 'GetRightVector', 540, 1040); link('head', 'ReturnValue', 'forward', 'InRot')
        node('upAxis', K + 'GetUpVector', 540, 1240); link('head', 'ReturnValue', 'upAxis', 'InRot')
        node('right', K + 'Multiply_VectorFloat', 800, 1240)
        link('upAxis', 'ReturnValue', 'right', 'A'); pin('right', 'B', -1)
        for i, (source, name, radius) in enumerate((('center', 'FaceOrigin', 'heightRadius'),
                                                  ('forward', 'FaceForward', None),
                                                  ('right', 'FaceRight', 'widthRadius'))):
            y = i * 440
            node('break' + source, K + 'BreakVector', 1100, y + 140)
            link(source, 'ReturnValue', 'break' + source, 'InVec')
            node('color' + source, K + 'MakeColor', 1360, y + 140)
            for a, b in (('X', 'R'), ('Y', 'G'), ('Z', 'B')):
                link('break' + source, a, 'color' + source, b)
            if radius:
                link(radius, 'ReturnValue', 'color' + source, 'A')
            else:
                pin('color' + source, 'A', 3.2)
            node('set' + source, '/Script/Engine.KismetMaterialLibrary:SetVectorParameterValue', 1640 + i * 300, 0)
            pin('set' + source, 'Collection', MPC); pin('set' + source, 'ParameterName', name)
            link('color' + source, 'ReturnValue', 'set' + source, 'ParameterValue')
        link(entry, 'then', 'setcenter', 'execute')
        link('setcenter', 'then', 'setforward', 'execute'); link('setforward', 'then', 'setright', 'execute')
        for title, refs, color in (
                ('Face landmarks', ['face', 'top', 'chin', 'eyeL', 'eyeR', 'center', 'height', 'heightRadius', 'width', 'widthRadius'], [0.3, 0.3, 0.3]),
                ('Follow the head', ['head', 'forward', 'upAxis', 'right'], [0.16, 0.42, 0.4]),
                ('Publish face bounds', ['breakcenter', 'breakforward', 'breakright', 'colorcenter', 'colorforward', 'colorright',
                                         'setcenter', 'setforward', 'setright'], [0.2, 0.32, 0.55])):
            ops.append(dict(op='comment', title=title, node_ids=refs, color=color))
        ops.append(dict(op='fit_comments'))
        command('blueprint_graph_batch', path=P, graph_name=FN, ops=ops, compile=True, save=True)
        graph = command('blueprint_inspect_graph', path=P, graph_name='UpdatePlayerPos')
        if not any(n['title'] == FN for n in graph['nodes']):
            tail = [n for n in graph['nodes'] if n['title'] == 'SetVectorParameterValue']
            assert len(tail) == 1, graph
            assert not any(e['from_node'] == tail[0]['node_id'] and e['from_pin'] == 'then' for e in graph['edges']), graph
            command('blueprint_graph_batch', path=P, graph_name='UpdatePlayerPos', compile=True, save=True, ops=[
                dict(op='add_node', ref='publish', node_type='call_function', function_name=P + '.BP_FoAPlayer_C:' + FN, x=1320, y=0),
                dict(op='connect', from_node=tail[0]['node_id'], from_pin='then', to_node='publish', to_pin='execute'),
                dict(op='comment', title='Face follows the pose', node_ids=['publish'], color=[0.16, 0.42, 0.4]), dict(op='fit_comments')])
        proof = command('blueprint_inspect_graph', path=P, graph_name='UpdatePlayerPos')
        call = next(n['node_id'] for n in proof['nodes'] if n['title'] == FN)
        assert any(e['to_node'] == call and e['to_pin'] == 'execute' for e in proof['edges'])
        print('Face mask publisher compiled/saved; existing30Hz timer only, source landmarks adapt to face proportions')
    finally:
        hc.release(OWNER, lease)
        Path('P:/FoA/Saved/PPShots/face_pose_build.json').write_text(json.dumps(TRACE, indent=1), encoding='utf-8')


if __name__ == '__main__':
    main()
