"""Credits lane: Lux3D objects turning in the left and right thirds of the ending credits roll (WBP_L2CreditsRoll).

The roll's Construct spawns two BP_CreditsShowcase actors (left, right) far above the map and switches the game view off
(the roll is opaque); its Destruct switches it back on. Each actor shows one Lux3D mesh at a time to its own
SceneCaptureComponent2D (show-only list, scene colour HDR, view lighting channel 1 only) and calls CaptureScene each tick
while its side shows (a bCaptureEveryFrame capture would wait for the game view). The runtime render target is sampled by
its Image through M_UI_CreditsShowcase (monochrome tone, alpha from the capture). An actor fades its Image in, turns the
mesh on a tilted axis, fades out and swaps to the next mesh; the right side runs half a cycle behind, so the two sides
never change together. Each actor destroys itself as soon as the roll leaves the viewport.

  python Tools/Unreal/ui/build_credits_showcase.py selftest          # offline: the timing curve and the mesh rotation
  python Tools/Unreal/ui/build_credits_showcase.py material|material_layout|skeleton|graphs|widget   # one step per lease
  Component templates (capture flags, lights, mesh list): Tools/Unreal/ui/credits_showcase_templates.py
  Every step compiles and saves what it edits before it returns.
"""
import math
import sys

sys.path[:0] = ['P:/FoA/Tools/Unreal', 'P:/FoA/Tools/Unreal/player']

ROOT = '/Game/FoA/UI/Credits'
MAT = ROOT + '/M_UI_CreditsShowcase'
BP = ROOT + '/BP_CreditsShowcase'
BP_C = BP + '.BP_CreditsShowcase_C'
ROLL = '/Game/FoA/Level2/Transition/WBP_L2CreditsRoll'
L3 = '/Game/FoA/Lux3D/'
MESHES = [L3 + p for p in (  # left side shows the even entries, right side the odd ones (picked from lookdev_v9)
    'alarm_clock_hero/SM_Lux3D_AlarmClock', 'the_shirt_enemy/SM_Lux3D_ShirtEnemy', 'door_key/SM_Lux3D_DoorKey',
    'school_backpack/SM_Lux3D_Backpack', 'cold_coffee_mug/SM_Lux3D_CoffeeMug', 'wire_hanger/SM_Lux3D_WireHanger',
    'bedside_book_stack/SM_Lux3D_BedsideBookStack', 'wall_calendar/SM_Lux3D_WallCalendar',
    'radiator/SM_Lux3D_Radiator', 'worksheet_stack/SM_Lux3D_Worksheets')]
PERIOD, FADE, GAP = 7.2, 1.4, 0.2   # seconds per object, fade in and out, dark gap before the swap
SPIN, FIT = 30.0, 48.0              # degrees per second about the tilted axis, bounding-sphere radius in cm
CAPTURE = 640                       # render target size: as sharp as 768 at the 500 px image (1080p), 512 stair-steps thin wire
DELAY = (0.6, 0.6 + PERIOD / 2)     # left, right
K = '/Script/Engine.KismetMathLibrary:'


# ---- the behaviour, in plain Python, mirrored node for node by graphs() -------------------------------------------
def alpha(local):
    """Image opacity at `local` seconds into one side's sequence."""
    if local < 0:
        return 0.0
    phase = local - math.floor(local / PERIOD) * PERIOD
    a = min(max(min(phase, PERIOD - GAP - phase) / FADE, 0.0), 1.0)
    return 0.5 * (2 * a) ** 2 if a < 0.5 else 1 - 0.5 * (2 - 2 * a) ** 2  # FInterpEaseInOut(0, 1, a, 2)


def index(local, first):
    return (first + 2 * max(math.floor(local / PERIOD), 0)) % len(MESHES)


def axis(i):
    x, y = math.sin(i * 2.3) * 0.6, math.cos(i * 1.7) * 0.6
    n = math.sqrt(x * x + y * y + 1)
    return x / n, y / n, 1 / n


def selftest():
    for first, delay in ((0, DELAY[0]), (1, DELAY[1])):
        assert alpha(-delay) == 0 and alpha(0) == 0, 'dark before the side starts'
        assert alpha(FADE + 0.01) == 1 and alpha(PERIOD / 2) == 1, 'fully in after the fade'
        assert alpha(PERIOD - GAP) == 0 and alpha(PERIOD - 0.05) == 0, 'dark through the swap gap'
        assert index(0, first) == first and index(PERIOD + 0.01, first) == (first + 2) % len(MESHES)
    # the two sides never change together: whenever one is mid-fade, the other is fully in
    t = 0.0
    while t < 60:
        l, r = alpha(t - DELAY[0]), alpha(t - DELAY[1])
        if t > DELAY[1] + FADE:
            assert l == 1 or r == 1, ('both sides changing at', t, l, r)
        t += 0.01
    seen = {index(t - DELAY[0], 0) for t in range(0, 31)} | {index(t - DELAY[1], 1) for t in range(5, 31)}
    assert len(seen) >= 8, seen  # the 30 s ending roll shows at least eight different objects
    tilts = [math.degrees(math.acos(axis(i)[2])) for i in range(len(MESHES))]
    assert all(15 < d < 45 for d in tilts), tilts
    print('selftest ok: fades, stagger, swaps, %d objects in 30 s, axis tilts %.0f..%.0f deg'
          % (len(seen), min(tilts), max(tilts)))


# ---- editor steps (Hayba) -----------------------------------------------------------------------------------------
def call(cmd, **args):
    from hayba_call import call as hc
    r = hc(cmd, args, timeout=300)
    assert r.get('ok'), (cmd, r)
    data = r.get('data') or {}
    assert data.get('ok', True), (cmd, data)
    return data


def material():
    """Capture -> luminance -> exposure and soft shoulder -> contrast -> warm paper tint; opacity from the capture."""
    have = call('material_get_info', path=MAT)
    if have.get('material_outputs') and any(o['connected'] for o in have['material_outputs']):
        print('material already built')
        return
    for e in have.get('expressions', []) + have.get('comments', []):  # a half-built graph of this step: start over
        call('material_delete_node', material_path=MAT, node_id=e['id'])
    m = dict(material_path=MAT)
    def node(cls, x, y, **props):
        return call('material_add_node', expression_class='MaterialExpression' + cls, node_pos=[x, y], properties=props, **m)['node_id']
    def link(a, b, pin=None, out=None, prop=None):
        args = dict(from_node=a, **m)
        if out:
            args['from_output'] = out
        else:
            args['from_output_index'] = 0
        if prop:
            args['to_property'] = prop
        else:
            args.update(to_node=b, to_input=pin)
        r = call('material_connect_nodes', **args)
        assert r.get('connected', True), r
    tex = node('TextureSampleParameter2D', -1300, -40, ParameterName='Capture', Texture='/Engine/EngineResources/Black.Black')
    weights = node('Constant3Vector', -1300, 240, Constant=[0.2126, 0.7152, 0.0722, 1.0])
    lum = node('DotProduct', -1000, 40)
    expo = node('ScalarParameter', -1000, 200, ParameterName='Exposure', DefaultValue=1.0)
    lit = node('Multiply', -780, 40)
    one = node('Add', -560, 140, ConstB=1.0)
    soft = node('Divide', -340, 40)
    contrast = node('ScalarParameter', -340, 200, ParameterName='Contrast', DefaultValue=1.3)
    curve = node('Power', -120, 40)
    tint = node('VectorParameter', -120, 200, ParameterName='Tint', DefaultValue=[0.96, 0.94, 0.9, 1.0])
    color = node('Multiply', 100, 40)
    clear = node('OneMinus', 100, 300)
    link(tex, lum, 'A', 'RGB'); link(weights, lum, 'B')
    link(lum, lit, 'A'); link(expo, lit, 'B')
    link(lit, soft, 'A'); link(lit, one, 'A'); link(one, soft, 'B')
    link(soft, curve, 'Base'); link(contrast, curve, 'Exponent')
    link(curve, color, 'A'); link(tint, color, 'B', 'RGB')
    link(color, None, prop='emissive_color')
    link(tex, clear, 'Input', 'A'); link(clear, None, prop='opacity')
    for title, x, y, w, h, col in (('Capture', -1340, -110, 260, 520, [0.18, 0.22, 0.30]),
                                   ('Monochrome tone', -1040, -30, 1330, 330, [0.30, 0.22, 0.10]),
                                   ('Opacity', 60, 240, 230, 150, [0.12, 0.26, 0.16])):
        call('material_add_comment', text=title, node_pos=[x, y], size=[w, h], color=col, show_bubble=True, color_bubble=True, **m)
    v = call('material_validate', **m)
    print('validate', {k: v.get(k) for k in ('ok', 'errors', 'warnings') if k in v})
    c = call('material_compile', **m)
    assert not c.get('has_errors'), c
    print('material compiled', c.get('stats'), 'saved', c.get('saved'))


def material_layout(exposure=1.6, contrast=1.4):
    """Left-to-right layout clear of the output node, three titled boxes, and the tone defaults from the PIE frames."""
    info = call('material_get_info', path=MAT)
    m = dict(material_path=MAT)
    by = {}
    for e in info['expressions']:
        key = e.get('parameter_name') or e['class'].replace('MaterialExpression', '')
        if key == 'Multiply':
            key = 'Lit' if any(i.get('from_node', '').startswith('MaterialExpressionDotProduct') for i in e['inputs']) else 'Color'
        by[key] = e['id']
    spots = {'Capture': (-1700, -40), 'Constant3Vector': (-1700, 300), 'DotProduct': (-1380, 40),
             'Exposure': (-1380, 200), 'Lit': (-1160, 40), 'Add': (-940, 170), 'Divide': (-720, 40),
             'Contrast': (-720, 200), 'Power': (-500, 40), 'Tint': (-500, 200), 'Color': (-260, 40),
             'OneMinus': (-260, 460)}
    for key, xy in spots.items():
        props = {'Exposure': {'DefaultValue': exposure}, 'Contrast': {'DefaultValue': contrast}}.get(key)
        call('material_set_node', node_id=by[key], node_pos=list(xy), **(dict(properties=props) if props else {}), **m)
    boxes = {'Capture': ((-1740, -110), (300, 620)), 'Monochrome tone': ((-1420, -30), (1300, 470)),
             'Opacity': ((-300, 400), (240, 160))}
    for c in info['comments']:
        xy, size = boxes[c['text']]
        call('material_set_comment', comment_id=c['id'], node_pos=list(xy), size=list(size), **m)
    c = call('material_compile', **m)
    assert not c.get('has_errors'), c
    print('material laid out, exposure', exposure, 'contrast', contrast, 'saved', c.get('saved'))


COMPONENTS = [('Hero', 'StaticMeshComponent'), ('Capture', 'SceneCaptureComponent2D'),
              ('Key', 'RectLightComponent'), ('Rim', 'RectLightComponent')]
VARIABLES = [  # name, type, default, exposed on spawn
    ('Image', 'object:/Script/UMG.Image', '', True), ('Credits', 'object:/Script/UMG.UserWidget', '', True),
    ('StartDelay', 'float', '0', True), ('FirstIndex', 'int', '0', True),
    ('Meshes', 'array<object:/Script/Engine.StaticMesh>', '', False),
    ('Age', 'float', '0', False), ('Shown', 'int', '-1', False), ('Axis', 'vector', '(X=0,Y=0,Z=1)', False),
    ('Fit', 'float', '1', False)]
FUNCTIONS = {'Step': [dict(name='Delta', type='float')], 'ShowMesh': [dict(name='Index', type='int')]}


def skeleton():
    if not call_ok('blueprint_get_info', path=BP):
        call('blueprint_create', name='BP_CreditsShowcase', package_path=BP, parent_class_path='/Script/Engine.Actor')
    info = call('blueprint_get_info', path=BP)
    have = {c['name'] for c in info.get('components', [])}
    for name, cls in COMPONENTS:
        if name not in have:
            r = call('blueprint_add_component', path=BP, component_name=name, component_class_path='/Script/Engine.' + cls)
            print('component', name, r.get('attached_to'))
    vars_ = {v['name'] for v in info['variables']}
    for name, typ, default, exposed in VARIABLES:
        if name not in vars_:
            call('blueprint_add_variable', path=BP, variable_name=name, variable_type=typ, default_value=default,
                 instance_editable=exposed, expose_on_spawn=exposed, category='Showcase')
    for name, inputs in FUNCTIONS.items():
        if name not in info['functions']:
            call('blueprint_add_function', path=BP, function_name=name, inputs=inputs)
    r = call('blueprint_compile', path=BP)
    print('compile', r.get('error_count', r))
    call('asset_save', asset_paths=[BP])


SC = '/Script/Engine.SceneComponent:'


class Graph:
    """One graph rebuilt in a single Hayba batch, one titled comment box per group (laid out in run())."""

    def __init__(self, graph, path=BP):
        from held_tool_graphs import Batch, inspect
        self.b, self.graph = Batch(path, graph), graph
        nodes, _ = inspect(path, graph)
        keep = {graph} if graph != 'EventGraph' else set()  # a function graph keeps its entry node
        self.entry = next((n['node_id'] for n in nodes if n['title'].replace(' ', '') in keep), None)
        old = [n['node_id'] for n in nodes if n['node_id'] != self.entry]
        if old:
            self.b.ops.append(dict(op='remove', node_ids=old))
        self.n, self.col, self.rows, self.groups, self.y0 = 0, 0, {}, [], 0
        self.exec_refs, self.band_of = set(), {}
        self.xs, self.cw, self.rh = 340, 300, 140  # exec spacing, data column width, data row height

    def _ref(self, is_exec=False):
        self.n += 1
        r = 'n%d' % self.n
        self.band_of[r] = self.y0
        if is_exec:
            self.exec_refs.add(r)
        return r

    def _data_pos(self):
        r = self.rows.get((self.y0, self.col), 0)
        self.rows[(self.y0, self.col)] = r + 1
        return self.col * 340, self.y0 + 220 + r * 150

    def put(self, ref, pin, value):
        if isinstance(value, tuple):
            self.b.link(value[0], value[1], ref, pin)
        else:
            self.b.pin(ref, pin, str(value).lower() if isinstance(value, bool) else value)

    def f(this, fn, out='ReturnValue', **pins):  # pure call ('this': pins may name a 'self' target)
        r = this._ref()
        this.b.fn(r, fn, *this._data_pos())
        for p, v in pins.items():
            this.put(r, p, v)
        this.groups[-1][1].append(r)
        return r, out

    def m(self, name, **pins):
        return self.f(K + name, **pins)

    def get(self, var, cls=None, target=None):
        r = self._ref()
        self.b.get(r, var, *self._data_pos(), cls)
        if target:
            self.put(r, 'self', target)
        self.groups[-1][1].append(r)
        return r, var

    def node(self, kind, out, **args):
        r = self._ref()
        self.b.node(r, kind, *self._data_pos(), **args)
        self.groups[-1][1].append(r)
        return r, out

    def do(this, ref_fn, after, **pins):  # impure call chained after `after`
        this.col += 1
        r = this._ref(True)
        this.b.fn(r, ref_fn, this.col * 340, this.y0)
        for p, v in pins.items():
            this.put(r, p, v)
        this.b.link(after[0], after[1], r, 'execute')
        this.groups[-1][1].append(r)
        return r

    def setv(self, var, value, after, cls=None, target=None):
        self.col += 1
        r = self._ref(True)
        self.b.set(r, var, self.col * 340, self.y0, cls)
        self.put(r, var, value)
        if target:
            self.put(r, 'self', target)
        self.b.link(after[0], after[1], r, 'execute')
        self.groups[-1][1].append(r)
        return r

    def exec_node(self, kind, after, **args):
        self.col += 1
        r = self._ref(True)
        self.b.node(r, kind, self.col * 340, self.y0, **args)
        if after:
            self.b.link(after[0], after[1], r, 'execute')
        self.groups[-1][1].append(r)
        return r

    def event(self, name):
        r = self._ref(True)
        self.b.ops.append(dict(op='add_event', ref=r, event_name=name, x=0, y=self.y0))
        self.groups[-1][1].append(r)
        return r

    def group(self, title):
        self.groups.append((title, []))

    def run(self):
        """Lay each group out in its own region, left to right per band: its exec nodes in a row, its data nodes in a
        grid of five rows below them, so comment boxes never overlap or nest."""
        cursor, pos = {}, {}
        for title, refs in self.groups:
            if not refs:
                continue
            band = self.band_of[refs[0]]
            start = cursor.get(band, 340 if self.entry else 0)
            ex = [r for r in refs if r in self.exec_refs]
            da = [r for r in refs if r not in self.exec_refs]
            for i, r in enumerate(ex):
                pos[r] = (start + i * self.xs, band)
            for j, r in enumerate(da):
                pos[r] = (start + (j // 5) * self.cw, band + 200 + (j % 5) * self.rh)
            cursor[band] = start + max(len(ex) * self.xs, (len(da) + 4) // 5 * self.cw) + 160
            self.b.comment(title, refs)
        for o in self.b.ops:
            if o.get('ref') in pos:
                o['x'], o['y'] = pos[o['ref']]
        return self.b.run()


def graphs():
    me = BP_C + ':'
    # ShowMesh(Index): mesh, fit to the bounding sphere, a tilted turning axis of its own
    g = Graph('ShowMesh')
    e = g.entry
    g.group('Show the mesh')
    mesh = g.node('get_array_item', 'Output')
    g.put(mesh[0], 'Array', g.get('Meshes'))
    g.put(mesh[0], 'Dimension 1', (e, 'Index'))
    s1 = g.do('/Script/Engine.StaticMeshComponent:SetStaticMesh', (e, 'then'), self=g.get('Hero'), NewMesh=mesh)
    bounds = g.f(K + 'BreakBoxSphereBounds', 'SphereRadius', InBoxSphereBounds=g.f('/Script/Engine.StaticMesh:GetBounds', self=mesh))
    s2 = g.setv('Fit', g.m('Divide_DoubleDouble', A=FIT, B=bounds), (s1, 'then'))
    g.group('Tilted axis')
    fi = g.m('Conv_IntToDouble', InInt=(e, 'Index'))
    x = g.m('Multiply_DoubleDouble', A=g.m('Sin', A=g.m('Multiply_DoubleDouble', A=fi, B=2.3)), B=0.6)
    y = g.m('Multiply_DoubleDouble', A=g.m('Cos', A=g.m('Multiply_DoubleDouble', A=fi, B=1.7)), B=0.6)
    axis_ = g.m('Normal', A=g.m('MakeVector', X=x, Y=y, Z=1.0))
    s3 = g.setv('Axis', axis_, (s2, 'then'))
    g.setv('Shown', (e, 'Index'), (s3, 'then'))
    g.run()

    # Step(Delta): fade in, hold, fade out, swap; turn the mesh; capture only while it shows
    g = Graph('Step')
    e = g.entry
    g.group('Fade and swap')
    age = g.setv('Age', g.m('Add_DoubleDouble', A=g.get('Age'), B=(e, 'Delta')), (e, 'then'))
    local = g.m('Subtract_DoubleDouble', A=g.get('Age'), B=g.get('StartDelay'))  # read after Set Age runs
    cycle = g.m('FFloor', A=g.m('Divide_DoubleDouble', A=local, B=PERIOD))
    phase = g.m('Subtract_DoubleDouble', A=local, B=g.m('Multiply_DoubleDouble', A=g.m('Conv_IntToDouble', InInt=cycle), B=PERIOD))
    ramp = g.m('FMin', A=phase, B=g.m('Subtract_DoubleDouble', A=PERIOD - GAP, B=phase))
    eased = g.m('FInterpEaseInOut', A=0.0, B=1.0, Exponent=2.0,
                Alpha=g.m('FClamp', Value=g.m('Divide_DoubleDouble', A=ramp, B=FADE), Min=0.0, Max=1.0))
    alpha_ = g.m('SelectFloat', A=eased, B=0.0, bPickA=g.m('GreaterEqual_DoubleDouble', A=local, B=0.0))
    # shortcut: the count is baked from MESHES (Hayba can't type Array_Length's wildcard); rerun graphs if the list changes
    length = len(MESHES)
    index_ = g.m('Percent_IntInt', A=g.m('Add_IntInt', A=g.m('Multiply_IntInt', A=g.m('Max', A=cycle, B=0), B=2),
                                         B=g.get('FirstIndex')), B=length)
    changed = g.exec_node('branch', (age, 'then'))
    g.put(changed, 'Condition', g.m('NotEqual_IntInt', A=index_, B=g.get('Shown')))
    show = g.do(me + 'ShowMesh', (changed, 'then'), Index=index_)
    g.group('Turn')
    angle = g.m('Add_DoubleDouble', A=g.m('Multiply_DoubleDouble', A=phase, B=SPIN),
                B=g.m('Multiply_DoubleDouble', A=g.m('Conv_IntToDouble', InInt=index_), B=67.0))
    hero = g.get('Hero')
    turn = g.do(SC + 'K2_SetRelativeRotation', (show, 'then'), self=hero,
                NewRotation=g.m('RotatorFromAxisAndAngle', Axis=g.get('Axis'), Angle=angle))
    g.b.link(changed, 'else', turn, 'execute')
    push = g.m('Multiply_DoubleDouble', A=g.get('Fit'),
               B=g.m('Add_DoubleDouble', A=0.94, B=g.m('Multiply_DoubleDouble', A=phase, B=0.06 / PERIOD)))
    grow = g.do(SC + 'SetRelativeScale3D', (turn, 'then'), self=hero, NewScale3D=g.m('Conv_DoubleToVector', InDouble=push))
    g.group('Show and capture')
    fade = g.do('/Script/UMG.Widget:SetRenderOpacity', (grow, 'then'), self=g.get('Image'), InOpacity=alpha_)
    # CaptureScene renders at once; a bCaptureEveryFrame capture waits for the game view, which the roll switches off
    seen = g.exec_node('branch', (fade, 'then'))
    g.put(seen, 'Condition', g.m('Greater_DoubleDouble', A=alpha_, B=0.0))
    g.do('/Script/Engine.SceneCaptureComponent2D:CaptureScene', (seen, 'then'), self=g.get('Capture'))
    g.run()

    # Event graph: render target and material at BeginPlay; Step while the roll is on screen, else go away
    g = Graph('EventGraph')
    g.group('Render target')
    begin = g.event('BeginPlay')
    made = g.do('/Script/Engine.KismetRenderingLibrary:CreateRenderTarget2D', (begin, 'then'), Width=CAPTURE, Height=CAPTURE, Format='RTF_RGBA16f')
    rt = (made, 'ReturnValue')
    cap = g.get('Capture')
    s1 = g.setv('TextureTarget', rt, (made, 'then'), cls='/Script/Engine.SceneCaptureComponent2D', target=cap)
    s2 = g.do('/Script/Engine.SceneCaptureComponent:ShowOnlyComponent', (s1, 'then'), self=cap, InComponent=g.get('Hero'))
    img = g.get('Image')
    got = g.do('/Script/UMG.Image:GetDynamicMaterial', (s2, 'then'), self=img)
    s3 = g.do('/Script/Engine.MaterialInstanceDynamic:SetTextureParameterValue', (got, 'then'), self=(got, 'ReturnValue'),
              ParameterName='Capture', Value=rt)
    g.do('/Script/UMG.Widget:SetRenderOpacity', (s3, 'then'), self=img, InOpacity=0.0)
    g.group('Step while the roll shows')
    g.col, g.y0 = 0, 1300
    tick = g.event('Tick')
    on = g.exec_node('branch', (tick, 'then'))
    g.put(on, 'Condition', g.f('/Script/UMG.UserWidget:IsInViewport', self=g.get('Credits')))
    g.do(me + 'Step', (on, 'then'), Delta=(tick, 'DeltaSeconds'))
    g.do('/Script/Engine.Actor:K2_DestroyActor', (on, 'else'))
    g.run()


FONT = '/Game/FoA/UI/Fonts/F_FoA_UI.F_FoA_UI'
SIDE, IMAGE = 670, 500   # image centres left and right of the screen centre, image size (1920x1080 layout units)
CAPTION = 'Objects made with Lux3D by Aholo'
COLUMN = 900  # text column width
# The roll, top to bottom: (widget, style, text). A role line sits small and dim over its names; names break only at
# phrase boundaries, every line fits the column (no automatic wraps). Licence statements quoted exactly
# (credits_level2.md); the title broken as the title screen's logotype.
ROLL_TEXT = [
    ('Credit0', 'title', 'The Nightmare\nof Responsibility'),
    ('Role1', 'role', 'Engine and characters'), ('Credit1', 'names', 'Unreal Engine and MetaHuman by Epic Games'),
    ('Role2', 'role', 'Built with'), ('Credit2', 'names', 'Lux3D by Manycore and Hayba'),
    ('Role3', 'role', 'Dream worlds generated with'), ('Credit3', 'names', 'Aholo SpatialGen by Manycore'),
    ('Role4', 'role', 'Toronto city scan'),
    ('Credit4', 'names', 'Contains information licensed under the\nOpen Government Licence – Canada.\n'
                         'LiDAR Point Clouds, CanElevation Series,\nNatural Resources Canada\n'
                         '(Toronto and Region Conservation Authority,\nGTA 2023 acquisition)'),
    ('Role5', 'role', 'Toronto building footprints'),
    ('Credit5', 'names', 'Contains information licensed under the\nOpen Government Licence – Toronto.\n'
                         '3D Massing, City of Toronto'),
    ('Role6', 'role', 'Environment assets'), ('Credit6', 'names', 'Poly Haven, CC0'),
    ('Role12', 'role', 'Animation'), ('Credit12', 'names', 'Quaternius, CC0'),
    # Music as shipped (Saved/QA/lanes/credits.md: each MUS_* asset's duration matched to music_meta.json). Only the
    # Metzik sting is CC BY (edited: one phrase cut, faded, hall tail); the nasheed collection states no licence.
    ('Role13', 'role', 'Music'),
    ('Credit13', 'names', 'Throat singing by Metzik (edited), CC BY 4.0\n'
                          'Amwaaj and Last Drop Of Hope by Alaa Wardi\n'
                          'It\'s Pokémon Day! a cappella by Raniel Herco\n'
                          'Background Nasheeds 1, 4, 10 and 26,\nIslamic Background Nasheed Ahat Collection'),
    ('Role7', 'role', 'Sound'),
    ('Credit7', 'names', 'Sonniss Game Audio GDC bundles and Kenney\nBigSoundBank (Joseph Sardin), CC0'),
    ('Role8', 'role', 'Typeface'), ('Credit8', 'names', 'Darker Grotesque\nGabriel Lam and Viet Anh Nguyen\nSIL Open Font License 1.1'),
    ('Role9', 'role', 'Suit'), ('Credit9', 'names', 'Man Black Business Suit by Style3D CG\nAdapted under CC BY 4.0'),
    ('Role10', 'role', 'Battle icons'), ('Credit10', 'names', 'Lorc and Delapouite, game-icons.net, CC BY 3.0'),
    ('Credit11', 'end', 'Thank you for playing')]
STYLES = {  # face, size, line height, opacity, gap below
    'title': ('ExtraBold', 78, .85, 1., 40), 'role': ('SemiBold', 20, .8, .55, 2),
    'names': ('SemiBold', 32, .75, 1., 24), 'end': ('ExtraBold', 54, 1., 1., 0)}
# PIE: names 34 .82 gap 40 gave a 2521 px column (105 px/s, 1 s hold); 34 .78 gap 30, 2289 px (102.6 px/s, 2.5 s hold).
# The music entry adds about 300 px, so names 32 .75 gap 24 and roles 20 (62 %) keep it near 2200 px, about 100 px/s.
# BP_DreamThreshold calls SetScroll with an offset falling 99 px/s for 30 s. SetScroll measures the column, scales the
# offset by (column height + END_CARD) / ARRIVE, clamped to 95..105 px/s, and holds with "Thank you for playing" near
# the centre once it arrives.
ARRIVE, GAIN_RANGE = 99.0 * 28.0, (0.96, 1.06)  # the last card arrives at 28 s, then holds
END_CARD = 585.0  # translation past the column height that puts the end card's top about 470 px from the top


def roll_selftest():
    for name, style, text in ROLL_TEXT:
        face, size, *_ = STYLES[style]
        for line in text.split('\n'):  # Darker Grotesque SemiBold measures about 0.52 em a character (PIE frames)
            assert len(line) * size * .52 < COLUMN - 40, (name, line)
    assert len({n for n, *_ in ROLL_TEXT}) == len(ROLL_TEXT)
    assert not any(c in t for _, _, t in ROLL_TEXT for c in '·•|/'), 'text rules: no decorative separators'
    print('roll text ok:', len(ROLL_TEXT), 'blocks, every line fits', COLUMN, 'px')


def widget():
    """WBP_L2CreditsRoll, edited in place: two showcase images in the side thirds, a quiet caption, a narrower text
    column whose entries take their own height, the Level 2 lines as the research doc words them, and Construct
    spawning the two showcase actors (only with an owning player, so offscreen renders never spawn into the editor)."""
    w = dict(widget_blueprint_path=ROLL)
    have = str(call('ui_get_widget_info', **w))
    tree = []
    for name, x in (('Img_ShowcaseL', -SIDE), ('Img_ShowcaseR', SIDE)):
        if name not in have:
            tree.append({'class': 'Image', 'name': name, 'properties': {
                'Brush': {'ResourceObject': MAT + '.M_UI_CreditsShowcase', 'ImageSize': {'X': IMAGE, 'Y': IMAGE}},
                'Visibility': 'HitTestInvisible', 'RenderOpacity': 0.0},
                'slot_props': dict(anchors_min=[.5, .5], anchors_max=[.5, .5], alignment=[.5, .5], position=[x, 0],
                                   size=[IMAGE, IMAGE], z_order=0)})
    if 'ShowcaseCaption' not in have:
        tree.append({'class': 'TextBlock', 'name': 'ShowcaseCaption', 'properties': {
            'Text': CAPTION, 'Font': {'FontObject': FONT, 'TypefaceFontName': 'SemiBold', 'Size': 22},
            'ColorAndOpacity': {'SpecifiedColor': [.96, .94, .9, .55]}, 'Visibility': 'HitTestInvisible'},
            'slot_props': dict(anchors_min=[0, 1], anchors_max=[0, 1], alignment=[0, 1], position=[64, -48],
                               auto_size=True, z_order=0)})
    if tree:
        r = call('ui_build_tree', parent_widget_name='RootCanvas', tree=tree, **w)
        print('built', r.get('names'))
    for name in ('Img_ShowcaseL', 'Img_ShowcaseR'):
        call('ui_set_variable', widget_name=name, is_variable=True, **w)
    r = call('ui_set_widget_properties', widget_name='CreditNames', slot_props=dict(size=[COLUMN, 2800]), **w)
    assert not r.get('unknown_slot_props'), r
    roll_selftest()
    def names_in(node):
        yield node['name']
        for child in node.get('children', []):
            yield from names_in(child)
    have = set(names_in(call('ui_get_widget_info', **w)['root']))
    new = [{'class': 'TextBlock', 'name': n, 'properties': {'Text': t}} for n, _, t in ROLL_TEXT if n not in have]
    if new:  # appended to the column, then moved into place below
        print('built', call('ui_build_tree', parent_widget_name='CreditNames', tree=new, **w).get('names'))
    for i, (name, style, text) in enumerate(ROLL_TEXT):
        face, size, line, alpha, gap = STYLES[style]
        r = call('ui_set_widget_properties', widget_name=name, properties={
            'Text': text, 'Font': {'FontObject': FONT, 'TypefaceFontName': face, 'Size': size},
            'ColorAndOpacity': {'SpecifiedColor': [.96, .94, .9, alpha]}, 'LineHeightPercentage': line,
            'Justification': 'Center', 'AutoWrapText': True, 'Visibility': 'HitTestInvisible'},
            slot_props=dict(fill=0, padding=[0, 0, 0, gap]), **w)
        assert not r.get('unknown_slot_props') and not r.get('failed_properties'), (name, r)
        call('ui_move_element', widget_name=name, index=i, **w)
    call('ui_compile_widget', **w)

    g = Graph('SetScroll', ROLL)
    g.group('Scroll and hold')
    names = g.get('CreditNames')
    height = g.m('Add_DoubleDouble', A=g.f(K + 'BreakVector2D', 'Y', InVec=g.f('/Script/UMG.Widget:GetDesiredSize', self=names)),
                 B=END_CARD)
    gain = g.m('FClamp', Value=g.m('Divide_DoubleDouble', A=height, B=ARRIVE), Min=GAIN_RANGE[0], Max=GAIN_RANGE[1])
    y = g.m('FMax', A=g.m('Multiply_DoubleDouble', A=(g.entry, 'Offset'), B=gain),
            B=g.m('Multiply_DoubleDouble', A=height, B=-1.0))
    g.do('/Script/UMG.Widget:SetRenderTranslation', (g.entry, 'then'), self=names,
         Translation=g.m('MakeVector2D', X=0.0, Y=y))
    g.run()

    g = Graph('EventGraph', ROLL)
    g.xs, g.cw, g.rh = 460, 460, 240  # spawn and transform nodes are large
    g.group('Lux3D showcase')
    built = g.event('Event Construct')
    owned = g.exec_node('branch', (built, 'then'))
    g.put(owned, 'Condition', g.f('/Script/Engine.KismetSystemLibrary:IsValid',
                                  Object=g.f('/Script/UMG.UserWidget:GetOwningPlayer')))
    after = (owned, 'then')
    for image, y, delay, first in (('Img_ShowcaseL', 0, DELAY[0], 0), ('Img_ShowcaseR', 2000, DELAY[1], 1)):
        spawn = g.exec_node('spawn_actor_from_class', after)
        g.put(spawn, 'Class', BP_C)
        g.put(spawn, 'SpawnTransform', g.m('MakeTransform', Location='0,%d,100000' % y))
        g.put(spawn, 'Image', g.get(image))
        g.put(spawn, 'Credits', g.node('self', 'self'))
        g.put(spawn, 'StartDelay', delay)
        g.put(spawn, 'FirstIndex', first)
        after = (spawn, 'then')
    # the roll covers the screen: skip the game view (the showcase captures render on their own)
    g.do('/Script/Engine.GameplayStatics:SetEnableWorldRendering', after, bEnable=False)
    g.group('World back on')
    g.col, g.y0 = 0, 1100
    gone = g.event('Event Destruct')
    g.do('/Script/Engine.GameplayStatics:SetEnableWorldRendering', (gone, 'then'), bEnable=True)
    g.run()


def call_ok(cmd, **args):
    from hayba_call import call as hc
    return hc(cmd, args, timeout=300).get('ok')


if __name__ == '__main__':
    step = sys.argv[1] if len(sys.argv) > 1 else 'selftest'
    {'selftest': selftest, 'material': material, 'material_layout': material_layout, 'skeleton': skeleton,
     'graphs': graphs, 'widget': widget}[step]()
