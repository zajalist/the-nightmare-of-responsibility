"""WBP_IntroStory v3 (story lane): the existing widget, edited in place through Hayba, now drives M_IntroPlate.
  python Tools/LookDev/intro_widget_v3.py
- EnsureInkMaterials: both images take M_IntroPlate (Img_Near stays collapsed; the old ink masters are left unused).
- UpdateInkReveal: feeds the plate material its clock (Age = PanelTime, Motion, Panel = Index).
- ApplyLayer: the widget no longer slides or scales the image (the shader moves the camera through real depth).
- UpdateFrame: the cross fades are 0.2 s, not 1 s (the shader forms the image in and crumbles it out).
- NextPanel: as many panels as intro_plates.PANELS.
- Tree: black backdrop, no paper band, white Darker Grotesque line low on the frame, a quiet Skip.
Idempotent: every edit checks the current graph first. Lifecycle graphs (Finish, FocusSkip, EventGraph) are untouched."""
import json
import os
import sys
from pathlib import Path

sys.path[:0] = ['P:/FoA/Tools/Unreal', 'P:/FoA/Tools/Unreal/player', 'P:/FoA/Tools/LookDev']
import hayba_call as h  # noqa: E402
from held_tool_graphs import Batch, inspect  # noqa: E402
from intro_plates import PANELS  # noqa: E402

W = '/Game/FoA/UI/Intro/WBP_IntroStory'
WC = W + '.WBP_IntroStory_C'
MAT = '/Game/FoA/UI/Intro/M_IntroPlate.M_IntroPlate'
TEX = '/Game/FoA/UI/Intro/Textures/T_IntroPlate_'
K = '/Script/Engine.KismetMathLibrary:'
KS = '/Script/Engine.KismetSystemLibrary:'
MID = '/Script/Engine.MaterialInstanceDynamic:'
OWNER = 'story'
TEXT = [0.87, 0.88, 0.89, 1.0]  # linear; about #F0F0F2 on screen


def c(cmd, **params):
    r = h.call(cmd, params, timeout=120)
    assert r.get('ok'), (cmd, r)
    d = r.get('data', {})
    assert d.get('ok', True) and not d.get('failed'), (cmd, d)
    return d


def pinval(n, name):
    return next((p.get('default_value') or p.get('default_object') for p in n['pins'] if p['name'] == name), None)


def num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def graphs():
    # EnsureInkMaterials: both brushes from the plate material
    ns, _ = inspect(W, 'EnsureInkMaterials')
    b = Batch(W, 'EnsureInkMaterials')
    for n in ns:
        if n['title'] == 'SetBrushFromMaterial' and 'M_IntroPlate' not in str(pinval(n, 'Material')):
            b.pin(n['node_id'], 'Material', MAT)
    if b.ops:
        b.run()
    # UpdateInkReveal: the plate clock
    ns, _ = inspect(W, 'UpdateInkReveal')
    if not any(pinval(n, 'ParameterName') == 'Panel' for n in ns):
        entry = next(n['node_id'] for n in ns if n['title'] == 'UpdateInkReveal')
        b = Batch(W, 'UpdateInkReveal')
        b.ops.append(dict(op='remove', node_ids=[n['node_id'] for n in ns if n['node_id'] != entry]))
        b.get('far', 'FarInk', 250, 250)
        b.fn('valid', KS + 'IsValid', 500, 250)
        b.link('far', 'FarInk', 'valid', 'Object')
        b.node('guard', 'branch', 750, 0)
        b.link('valid', 'ReturnValue', 'guard', 'Condition')
        b.link(entry, 'then', 'guard', 'execute')
        prev, x = ('guard', 'then'), 1050
        for ref, param, var in (('age', 'Age', 'PanelTime'), ('motion', 'Motion', 'Motion'), ('panel', 'Panel', 'Index')):
            b.get(ref + 'v', var, x, 300)
            src = (ref + 'v', var)
            if var == 'Index':
                b.fn('tofloat', K + 'Conv_IntToDouble', x + 120, 420)
                b.link(ref + 'v', var, 'tofloat', 'InInt')
                src = ('tofloat', 'ReturnValue')
            b.fn(ref, MID + 'SetScalarParameterValue', x, 0, ParameterName=param)
            b.link('far', 'FarInk', ref, 'self')
            b.link(src[0], src[1], ref, 'Value')
            b.link(prev[0], prev[1], ref, 'execute')
            prev, x = (ref, 'then'), x + 320
        b.comment('Plate clock', [o['ref'] for o in b.ops if o.get('op') == 'add_node'])
        b.run()
    # ApplyLayer: no widget-level slide or zoom
    ns, _ = inspect(W, 'ApplyLayer')
    b = Batch(W, 'ApplyLayer')
    for n in ns:
        v = num(pinval(n, 'B'))
        if n['title'] in ('float * float', 'double * double') and v in (260.0, 0.06, -36.0):
            b.pin(n['node_id'], 'B', 0)
        if n['title'] in ('float + float', 'double + double') and v in (1.18, 1.045):
            b.pin(n['node_id'], 'B', 1.0)
    if b.ops:
        b.run()
    # UpdateFrame: 0.2 s fades
    ns, es = inspect(W, 'UpdateFrame')
    mn = next(n['node_id'] for n in ns if n['title'] == 'Min (Float)')
    cl = next(n['node_id'] for n in ns if n['title'] == 'Clamp (Float)' and num(pinval(n, 'Max')) == 1.0)
    direct = [e for e in es if e['from_node'] == mn and e['to_node'] == cl]
    if direct:
        b = Batch(W, 'UpdateFrame')
        b.fn('quick', K + 'Multiply_DoubleDouble', 1650, 1150, B=5)
        b.cut(mn, direct[0]['from_pin'], cl, direct[0]['to_pin'])
        b.link(mn, direct[0]['from_pin'], 'quick', 'A')
        b.link('quick', 'ReturnValue', cl, direct[0]['to_pin'])
        b.comment('Quick fades', ['quick'])
        b.run()
    # NextPanel: panel count
    ns, _ = inspect(W, 'NextPanel')
    less = next(n for n in ns if n['title'] == 'integer < integer')
    if num(pinval(less, 'B')) != len(PANELS):
        b = Batch(W, 'NextPanel')
        b.pin(less['node_id'], 'B', len(PANELS))
        b.run()


def tree():
    def ui(name, **props):
        c('ui_set_widget_properties', widget_blueprint_path=W, widget_name=name, **props)
    rgba = lambda v: dict(zip('RGBA', v))  # noqa: E731
    ui('Img_Black', properties={'Brush': {'DrawAs': 'Image', 'TintColor': {'SpecifiedColor': rgba([0, 0, 0, 1])}}})
    for n in ('Img_Foot', 'Img_Near', 'Img_Mid', 'Img_Figure', 'Img_Fx'):  # unused layers: hidden, holding no old art
        ui(n, properties={'Visibility': 'Collapsed', 'Brush': {'ResourceObject': None, 'DrawAs': 'Image'}})  # JSON null clears it
    ui('Img_Panel', properties={'Brush': {'ResourceObject': MAT, 'DrawAs': 'Image'}, 'Visibility': 'HitTestInvisible',
                                'RenderTransform': {'Scale': {'X': 1.0, 'Y': 1.0}}})
    ui('Txt_Sub', properties={'Font': {'FontObject': '/Game/FoA/UI/Fonts/F_FoA_UI', 'TypefaceFontName': 'Medium', 'Size': 34},
                              'ColorAndOpacity': {'SpecifiedColor': rgba(TEXT)}, 'ShadowOffset': {'X': 0, 'Y': 2},
                              'ShadowColorAndOpacity': rgba([0, 0, 0, 0.85]), 'Justification': 'Center', 'AutoWrapText': True},
       slot_props={'anchors_min': [0.12, 1], 'anchors_max': [0.88, 1], 'position': [0, -170], 'size': [0, 100]})
    quiet = {k: {'DrawAs': 'Image', 'TintColor': {'SpecifiedColor': rgba([1, 1, 1, a])}} for k, a in
             (('Normal', 0.0), ('Hovered', 0.08), ('Pressed', 0.14))}
    ui('Btn_Skip', properties={'WidgetStyle': quiet})
    ui('Txt_Skip', properties={'Font': {'FontObject': '/Game/FoA/UI/Fonts/F_FoA_UI', 'TypefaceFontName': 'Medium', 'Size': 22},
                               'ColorAndOpacity': {'SpecifiedColor': rgba([0.32, 0.33, 0.34, 1])}, 'ShadowOffset': {'X': 0, 'Y': 1},
                               'ShadowColorAndOpacity': rgba([0, 0, 0, 0.9])})


def defaults():
    plates = [TEX + p[0] + '.T_IntroPlate_' + p[0] for p in PANELS]
    c('blueprint_set_defaults', path=W, properties={'Panels': plates, 'NearPanels': plates,
                                                    'Lines': [p[1] for p in PANELS], 'Seconds': [p[2] for p in PANELS]})


def main():
    os.environ['HAYBA_AGENT_ID'] = OWNER
    assert not c('editor_get_state')['pie_running'], 'PIE running'
    for p in PANELS:
        assert Path('P:/FoA/Content/FoA/UI/Intro/Textures/T_IntroPlate_%s.uasset' % p[0]).exists(), p[0]
    token = h.lease_acquire(OWNER, ['asset:' + W], ttl_s=240, wait_s=60)
    os.environ['FOA_LEASE'] = token
    try:
        graphs()
        tree()
        defaults()
        r = c('ui_compile_widget', widget_blueprint_path=W)
        c('ui_save_widget', widget_blueprint_path=W)
        proof = {'compile': r, 'defaults': c('object_get_property', path=WC.replace('.WBP_IntroStory_C', '.Default__WBP_IntroStory_C'),
                                             names=['Panels', 'Lines', 'Seconds'])}
        Path('P:/FoA/Saved/StoryShots/intro_widget_v3.json').write_text(json.dumps(proof, indent=1))
        print('WBP_IntroStory v3 compiled and saved', r)
    finally:
        h.release(OWNER, token)
        os.environ.pop('FOA_LEASE', None)


if __name__ == '__main__':
    main()
