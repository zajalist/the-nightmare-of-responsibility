"""Level 2 stop tasks, redesigned (level2 lane, 2026-11-18, the user's "doesn't look AAA" call on Pack the crate).

What changes, in WBP_L2Interview (one surface for every stop) and BP_L2Journey:
  No slab. The opaque brown ShiftPaper, the colour cells and the centred readout are gone; text sits on the world over
    the existing bottom scrim, in one style (F_FoA_UI, ink or grey, the same soft drop shadow, no outline).
  Order card (top left): the task title, then one row per item IN the order with filled and empty pips; the newest
    pip pulses when it fills. Dispatch and the ledger show their two lines of facts in the same place.
  Status (top right): "Order 2 of 4", the shift's time as a thin draining line, mistakes as two small marks.
  Choices: three across the bottom; the chosen one is full ink, a little larger, with a sliding underline.
  Keys: real key caps (rounded outline, arrow image, "Enter" and the pad's "A"), never arrow characters, which the
    fonts lack. Every job dialogue uses them too (the pitch, the result), instead of "↑ ↓ Choose" hints.
  Pack the crate is a job, not a menu: the wooden crate (Poly Haven, CC0) sits in front of him, each packed item
    (rice basket, tea box, oat milk jug, all CC0 props already in the project) drops in with a wooden thud and a sand
    puff; a wrong pick tumbles over the rim and crumbles to black sand, and the packed items go with it. A full case
    goes in a burst of sand before the next order.
Dispatch and the ledger: same HUD, their timing rail and gauge redrawn as thin monochrome lines.

  python -B build_l2_stop_look.py selftest | textures | widget | declare | wgraphs | graphs | hooks | input | cleanup
  python Tools/Unreal/ue_remote.py Tools/Unreal/level2/build_l2_stop_look.py FOA_LOOK_STEP=import    (PNG import)
  python Tools/Unreal/ue_remote.py Tools/Unreal/level2/build_l2_stop_look.py FOA_LOOK_STEP=templates (crate comps)
  python Tools/Unreal/ue_remote.py Tools/Unreal/level2/build_l2_stop_look.py FOA_LOOK_STEP=keys      (consume off)
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

ROOT = '/Game/FoA/Level2/Journey'
UI = ROOT + '/WBP_L2Interview'
UIC = UI + '.WBP_L2Interview_C'
JOURNEY = ROOT + '/BP_L2Journey'
FONT = '/Game/FoA/UI/Fonts/F_FoA_UI.F_FoA_UI'
TEXDIR = '/Game/FoA/UI/Textures'
PNG_DIR = 'P:/FoA/Tools/Textures/ui'
ARROW = TEXDIR + '/T_UI_KeyArrow.T_UI_KeyArrow'
INK, SUB = .87, .43
# a 1 px drop only: the 2 px .55 one read as a heavy outline on the bright sand (the user's 11-18 screenshot)
SHADOW = dict(ShadowOffset={'X': 0, 'Y': 1}, ShadowColorAndOpacity=[0, 0, 0, .4])
DOT = TEXDIR + '/T_UI_SoftDot.T_UI_SoftDot'  # the HUD subtitle's soft halo: no edges, not a panel
W = '/Script/UMG.Widget:'
TB = '/Script/UMG.TextBlock:'
IMG = '/Script/UMG.Image:'
CS = '/Script/UMG.CanvasPanelSlot:'
LAYOUT = '/Script/UMG.WidgetLayoutLibrary:SlotAsCanvasSlot'
ITEMS = ('Rice', 'Tea', 'Oat milk')
ROW, PIP, PIP_X, PIP_GAP = 40, 16, 150, 26
CHOICE_X = 424  # shift_minigames lays the three choices out 424 px apart along the bottom

# The crate (Queen Market only). He stands at StreetTransform facing the car's heading; the crate stands CRATE_AHEAD cm
# in front of him, broadside, and he looks down PITCH degrees at it. Items: (mesh, uniform scale). Bounds read
# 2026-11-18: crate 82.6 x 40.8 x 32.2 cm, basket 21 x 21 x 20, tea box 24 x 10.6 x 6.4, jug 27.5 x 16.8 x 21.2
# (all pivots at their bases).
PROPS = '/Game/FoA/Props'
CRATE = PROPS + '/wooden_crate_01/wooden_crate_01_2k/StaticMeshes/wooden_crate_01'


def _obj(p):
    return f'{p}.{p.rsplit("/", 1)[1]}'


ITEM_MESH = (
    (_obj(PROPS + '/wicker_basket_02/wicker_basket_02_1k/StaticMeshes/wicker_basket_02_base'), 1.05),
    (_obj(PROPS + '/CheeseBox_01/CheeseBox_01_1k/StaticMeshes/CheeseBox_01'), 1.3),
    (_obj(PROPS + '/jug_01/jug_01_1k/StaticMeshes/jug_01_1k'), .95),
)
# measured 11-18 (run_20261118_1353): his eye is ~196 cm up. At -22 deg the stop's Lux3D bills pile (7.6 m ahead)
# fills the upper third and visibly shrinks with each order; 240 cm puts the crate in the lower half, above the choices.
CRATE_AHEAD, PITCH, SLOT_GAP, DROP_FROM, DROP_SECONDS, SPILL_SECONDS, CASE_CLEAR = 240., -22., 25., 62., .3, .5, .55
THUD = '/Game/FoA/Audio/SFX/Footsteps/SFX_Footsteps_BootsWood_03.SFX_Footsteps_BootsWood_03'
SANDFX = '/Game/FoA/VFX/Sand/BPL_SandFX.BPL_SandFX_C:SpawnSandBurst'
CRATE_COMPS = ('ShiftCrate', 'ShiftItem0', 'ShiftItem1', 'ShiftItem2', 'ShiftSpill')
# Key prompts: (arrows 0 none, 1 up and down, 2 left and right; label; key A; label A; key B; label B)
PICK = (1, 'Choose', 'Enter', 'Confirm', '', '')
SHIFT_KEYS = ((2, 'Choose', 'Enter', 'Pack', '', ''), (2, 'Choose a bay', 'Enter', 'Send', '', ''),
              (2, 'Choose', 'Enter', 'Confirm', '', ''))


def selftest():
    banned = '\u2190\u2191\u2192\u2193\u00b7\u2022|/\u2014\u2013'
    for keys in (PICK, *SHIFT_KEYS):
        assert len(keys) == 6 and keys[0] in (0, 1, 2) and not any(c in str(k) for k in keys for c in banned), keys
    assert len(ITEM_MESH) == len(ITEMS) == 3
    # three items side by side fit the crate's 82.6 cm length, turned so their long side runs front to back
    widths = (21 * ITEM_MESH[0][1], 10.6 * ITEM_MESH[1][1], 16.8 * ITEM_MESH[2][1])
    assert 2 * SLOT_GAP + max(widths) < 82.6 - 6, widths
    assert all(w < 2 * SLOT_GAP for w in widths)
    a = arrow_png()
    assert a.size == (64, 64) and a.getpixel((52, 32))[3] > 200 and a.getpixel((4, 4))[3] == 0
    print('stop look selftest ok')


# ---- textures ------------------------------------------------------------------------------------------------------
def arrow_png():
    """A right-pointing key-cap arrow, white on transparent, drawn 4x and filtered down (rotated in UMG for the rest)."""
    from PIL import Image, ImageDraw
    s = 4
    im = Image.new('RGBA', (64 * s, 64 * s), (255, 255, 255, 0))
    d = ImageDraw.Draw(im)
    d.rectangle((12 * s, 28 * s, 38 * s, 36 * s), fill=(255, 255, 255, 255))           # shaft
    d.polygon([(34 * s, 14 * s), (56 * s, 32 * s), (34 * s, 50 * s)], fill=(255, 255, 255, 255))  # head
    return im.resize((64, 64), Image.LANCZOS)


def textures():
    os.makedirs(PNG_DIR, exist_ok=True)
    arrow_png().save(PNG_DIR + '/T_UI_KeyArrow.png')
    print('wrote', PNG_DIR + '/T_UI_KeyArrow.png')


def import_textures():
    import unreal
    eal = unreal.EditorAssetLibrary
    if not eal.does_asset_exist(TEXDIR + '/T_UI_KeyArrow'):
        t = unreal.AssetImportTask()
        for k, v in (('filename', PNG_DIR + '/T_UI_KeyArrow.png'), ('destination_path', TEXDIR), ('automated', True),
                     ('save', True)):
            t.set_editor_property(k, v)
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([t])
    tex = unreal.load_asset(TEXDIR + '/T_UI_KeyArrow')
    for k, v in (('compression_settings', unreal.TextureCompressionSettings.TC_EDITOR_ICON), ('srgb', True),
                 ('lod_group', unreal.TextureGroup.TEXTUREGROUP_UI), ('never_stream', True),
                 ('mip_gen_settings', unreal.TextureMipGenSettings.TMGS_NO_MIPMAPS)):
        tex.set_editor_property(k, v)
    print('saved', eal.save_loaded_asset(tex, False))


# ---- widget tree ---------------------------------------------------------------------------------------------------
def col(v, a=1.):
    return {'SpecifiedColor': [v, v, v, a]}


def text(typeface, size, v, copy='', just='Left', shadow=True):
    p = {'Text': copy, 'Justification': just, 'ColorAndOpacity': col(v),
         'Font': {'FontObject': FONT, 'TypefaceFontName': typeface, 'Size': size, 'OutlineSettings': {'OutlineSize': 0}}}
    if shadow:
        p.update(SHADOW)
    return p


def dot(size, alpha, radius=None):
    r = radius if radius is not None else size / 2
    return {'Brush': f'(ImageSize=(X={size},Y={size}),DrawAs=RoundedBox,TintColor=(SpecifiedColor=(R=1,G=1,B=1,A=1)),'
                     f'OutlineSettings=(CornerRadii=(X={r},Y={r},Z={r},W={r}),Color=(SpecifiedColor=(R=1,G=1,B=1,A=0)),'
                     'Width=0,RoundingType=FixedRadius))', 'ColorAndOpacity': [1, 1, 1, alpha]}


def cap(name, child):
    """A key cap: rounded outline in light grey over a soft dark fill, one glyph or word inside."""
    return {'class': 'Border', 'name': name, 'slot_props': dict(vertical_alignment='Center', padding=[0, 0, 6, 0]),
            'properties': {'Background': '(DrawAs=RoundedBox,TintColor=(SpecifiedColor=(R=1,G=1,B=1,A=1)),'
                           'OutlineSettings=(CornerRadii=(X=6,Y=6,Z=6,W=6),Color=(SpecifiedColor=(R=0.8,G=0.8,B=0.8,A=0.95)),'
                           'Width=1.5,RoundingType=FixedRadius))', 'BrushColor': [0, 0, 0, .45],
                           'Padding': '(Left=9,Top=4,Right=9,Bottom=5)', 'HorizontalAlignment': 'HAlign_Center',
                           'VerticalAlignment': 'VAlign_Center'},
            'children': [child]}


def arrow(name):
    return {'class': 'Image', 'name': name, 'properties': {
        'Brush': f'(ImageSize=(X=16,Y=16),DrawAs=Image,ResourceObject="{ARROW}")', 'ColorAndOpacity': [1, 1, 1, .92],
        'RenderTransformPivot': '(X=0.5,Y=0.5)'}}


def label(name, copy, pad_left=4, pad_right=26):
    return {'class': 'TextBlock', 'name': name, 'properties': text('Medium', 20, SUB, copy),
            'slot_props': dict(vertical_alignment='Center', padding=[pad_left, 0, pad_right, 0])}


def keyword(name, copy):
    return {'class': 'TextBlock', 'name': name, 'properties': text('SemiBold', 17, INK, copy, 'Center', False)}


def canvas_slot(anchor, align, pos, size, z=6, auto=False):
    return dict(anchors_min=anchor, anchors_max=anchor, alignment=align, position=pos, size=size, z_order=z,
                auto_size=auto)


def widget():
    import build_drive as b
    have = str(b.call('ui_query', path=UI))
    tree = []
    if 'ShiftTitle' not in have:
        tree.append({'class': 'TextBlock', 'name': 'ShiftTitle', 'properties': dict(text('SemiBold', 32, INK), Visibility='Collapsed'),
                     'slot_props': canvas_slot([0, 0], [0, 0], [64, 84], [760, 46])})
    if 'OrderCard' not in have:
        rows = []
        for k, name in enumerate(ITEMS):
            rows.append({'class': 'TextBlock', 'name': f'Txt_Order{k}', 'properties': text('Medium', 26, INK, name),
                         'slot_props': canvas_slot([0, 0], [0, 0], [0, k * ROW], [PIP_X - 8, 36], 0)})
            for j in range(2):
                rows.append({'class': 'Image', 'name': f'Pip{k}{j}', 'properties': dict(dot(PIP, .2), RenderTransformPivot='(X=0.5,Y=0.5)'),
                             'slot_props': canvas_slot([0, 0], [0, 0], [PIP_X + j * PIP_GAP, k * ROW + 10], [PIP, PIP], 0)})
        tree.append({'class': 'CanvasPanel', 'name': 'OrderCard', 'properties': {'Visibility': 'Collapsed'},
                     'slot_props': canvas_slot([0, 0], [0, 0], [64, 142], [420, 3 * ROW]), 'children': rows})
    if 'ShiftStatus' not in have:
        tree.append({'class': 'CanvasPanel', 'name': 'ShiftStatus', 'properties': {'Visibility': 'Collapsed'},
                     'slot_props': canvas_slot([1, 0], [1, 0], [-72, 84], [260, 24]),
                     'children': [
                         {'class': 'Image', 'name': 'TimeTrack', 'properties': dot(2, .2, 0),
                          'slot_props': canvas_slot([0, 0], [0, 0], [0, 1], [260, 2], 0)},
                         {'class': 'Image', 'name': 'TimeFill', 'properties': dict(dot(3, .92, 0), RenderTransformPivot='(X=0,Y=0.5)'),
                          'slot_props': canvas_slot([0, 0], [0, 0], [0, 0], [260, 4], 1)},
                         {'class': 'Image', 'name': 'Mark0', 'properties': dot(4, .2, 0),
                          'slot_props': canvas_slot([0, 0], [0, 0], [208, 16], [22, 4], 0)},
                         {'class': 'Image', 'name': 'Mark1', 'properties': dot(4, .2, 0),
                          'slot_props': canvas_slot([0, 0], [0, 0], [238, 16], [22, 4], 0)}]})
    for name, anchor, pos, size in (('HaloLeft', [0, 0], [200, 120], [1150, 560]), ('HaloRight', [1, 0], [-210, 96], [900, 420])):
        if name not in have:  # type at the top sits on bright sand: the house soft halo under it, edges nowhere
            tree.append({'class': 'Image', 'name': name, 'properties': {
                'Brush': f'(ImageSize=(X=256,Y=256),DrawAs=Image,ResourceObject="{DOT}")', 'ColorAndOpacity': [0, 0, 0, .5],
                'Visibility': 'HitTestInvisible'}, 'slot_props': canvas_slot(anchor, [.5, .5], pos, size, -2)})
    if 'ChoiceLine' not in have:
        tree.append({'class': 'Image', 'name': 'ChoiceLine', 'properties': dict(dot(3, .92, 0), Visibility='Collapsed'),
                     'slot_props': canvas_slot([.5, 1], [.5, 1], [0, -100], [150, 3])})
    if 'KeyRow' not in have:
        tree.append({'class': 'HorizontalBox', 'name': 'KeyRow', 'properties': {'Visibility': 'Collapsed'},
                     'slot_props': canvas_slot([0, 1], [0, 1], [96, -26], [800, 34], 6, True),
                     'children': [cap('CapPrev', arrow('Img_KeyPrev')), cap('CapNext', arrow('Img_KeyNext')),
                                  label('Txt_KeyChoose', 'Choose'),
                                  cap('CapA', keyword('Txt_CapA', 'Enter')), cap('CapPadA', keyword('Txt_CapPadA', 'A')),
                                  label('Txt_KeyA', 'Confirm'),
                                  cap('CapB', keyword('Txt_CapB', 'C')), cap('CapPadB', keyword('Txt_CapPadB', 'A')),
                                  label('Txt_KeyB', 'Continue')]})
    if tree:
        r = b.call('ui_build_tree', widget_blueprint_path=UI, parent_widget_name='RootCanvas', tree=tree)
        print('built', [t['name'] for t in tree], {k: r.get(k) for k in ('unknown_slot_props', 'rejected_properties') if r.get(k)})
    names = ['ShiftTitle', 'OrderCard', 'ShiftStatus', 'TimeFill', 'Mark0', 'Mark1', 'ChoiceLine', 'KeyRow', 'CapPrev',
             'CapNext', 'Img_KeyPrev', 'Img_KeyNext', 'Txt_KeyChoose', 'CapA', 'CapPadA', 'Txt_CapA', 'Txt_KeyA', 'CapB',
             'CapPadB', 'Txt_CapB', 'Txt_KeyB']
    names += [f'Txt_Order{k}' for k in range(3)] + [f'Pip{k}{j}' for k in range(3) for j in range(2)]
    for name in names:
        b.call('ui_set_variable', widget_blueprint_path=UI, widget_name=name, is_variable=True)
    restyle()
    print(b.call('blueprint_compile', path=UI, save=True).get('saved'))


def restyle():
    """The existing pieces in the one style: thin monochrome mechanics, no outline, one shadow, no tinted cells."""
    import build_drive as b

    def setp(name, props=None, slot=None):
        args = dict(widget_blueprint_path=UI, widget_name=name)
        if props:
            args['properties'] = props
        if slot:
            args['slot_props'] = slot
        r = b.call('ui_set_widget_properties', **args)
        bad = {k: r.get(k) for k in ('unknown_slot_props', 'rejected_properties') if r.get(k)}
        assert not bad, (name, bad)
    setp('ShiftReadout', dict(text('Medium', 26, INK, just='Left'), AutoWrapText=True),
         canvas_slot([0, 0], [0, 0], [64, 142], [900, 120]))
    for name, color, pos, size in (('ShiftRail', [1, 1, 1, .22], [0, 250], [544, 2]),
                                   ('ShiftZone', [1, 1, 1, .4], [38, 250], [163, 8]),
                                   ('ShiftMarker', [1, 1, 1, .95], [-270, 250], [4, 30]),
                                   ('LedgerTarget', [1, 1, 1, .95], [-222, 250], [4, 28])):
        setp(name, {'BrushColor': color}, canvas_slot([.5, .5], [.5, .5], pos, size))
    setp('LedgerGauge', {'FillColorAndOpacity': [1, 1, 1, .9], 'WidgetStyle': (
        '(BackgroundImage=(DrawAs=Box,TintColor=(SpecifiedColor=(R=1,G=1,B=1,A=0.18))),'
        'FillImage=(DrawAs=Box,TintColor=(SpecifiedColor=(R=1,G=1,B=1,A=1))))')},
         canvas_slot([.5, .5], [.5, .5], [0, 250], [444, 4]))
    setp('ShiftTitle', text('SemiBold', 32, INK))
    for k, name in enumerate(ITEMS):
        setp(f'Txt_Order{k}', text('Medium', 26, INK, name))
    for name, copy in (('Txt_KeyChoose', 'Choose'), ('Txt_KeyA', 'Confirm'), ('Txt_KeyB', 'Continue')):
        setp(name, text('Medium', 20, SUB, copy))
    setp('Txt_Status', text('SemiBold', 22, SUB))
    setp('Txt_Evidence', text('SemiBold', 22, SUB, just='Right'))
    setp('Txt_Speaker', text('SemiBold', 26, SUB))
    for i in range(3):
        setp(f'Txt_Answer{i}', text('Medium', 26, INK))
        setp(f'AnswerPad{i}', {'BrushColor': [0, 0, 0, 0]}, {'HorizontalAlignment': 'HAlign_Fill'})  # Justification places it


# ---- widget graphs -------------------------------------------------------------------------------------------------
WVARS = [('ShiftMode', 'bool', 'false'), ('ChoiceSelected', 'int', '0'), ('ChoiceX', 'float', '0'),
         ('ChoiceTarget', 'float', '0'), ('TimeShown', 'float', '1'), ('TimeTarget', 'float', '1'),
         ('PulseAt', 'float', '-10'), ('PulseRow', 'int', '-1'), ('PulsePip', 'int', '0'),
         ('LastPacked0', 'int', '0'), ('LastPacked1', 'int', '0'), ('LastPacked2', 'int', '0')]
WFUNCS = {'PaintOrder': [('Rice', 'int'), ('Tea', 'int'), ('Oat', 'int'), ('PackedRice', 'int'), ('PackedTea', 'int'),
                         ('PackedOat', 'int')],
          'PaintShiftStatus': [('Remaining', 'float'), ('Mistakes', 'int')],
          'SetKeys': [('Arrows', 'int'), ('Choose', 'text'), ('KeyA', 'text'), ('LabelA', 'text'), ('KeyB', 'text'),
                      ('LabelB', 'text')],
          'AfterRefresh': [('Selected', 'int')], 'StyleChoices': []}


def lg(path, name):
    """The house graph helper with joins: vis() leaves its 'shown' branch open; the next exec node closes it."""
    from build_drive import G

    class LG(G):
        joins = None

        def chain(self, *refs):
            G.chain(self, *refs)
            if self.joins and len(refs) >= 2:
                for j in self.joins:  # a node ('then') or (node, pin)
                    self.link(*(j if isinstance(j, tuple) else (j, 'then')), refs[-1], 'execute')
                self.joins = []
    return LG(path, name)


def vis(g, target, cond, on='HitTestInvisible'):
    br = g.branch(cond)
    g.side(br)
    seen = g.do(W + 'SetVisibility', self=target, InVisibility=on)
    g.side(br, False)
    g.do(W + 'SetVisibility', self=target, InVisibility='Collapsed')
    g.joins = [seen[0]]


def ieq(g, a, c):
    return g.math('EqualEqual_IntInt', A=a, B=c)


def now(g):
    return g.f('/Script/Engine.GameplayStatics:GetTimeSeconds')  # the world context pin fills itself in a widget


def place(g, widget, anchor, align, pos):
    slot = g.f(LAYOUT, Widget=widget)
    g.do(CS + 'SetAnchors', self=slot, InAnchors=f'(Minimum=(X={anchor[0]},Y={anchor[1]}),Maximum=(X={anchor[0]},Y={anchor[1]}))')
    g.do(CS + 'SetAlignment', self=slot, InAlignment=f'(X={align[0]},Y={align[1]})')
    g.do(CS + 'SetPosition', self=slot, InPosition=f'(X={pos[0]},Y={pos[1]})')


def paint_board():
    """PaintShiftBoard(Mode, Readout, Notice): Mode -1 is the dialogue look; 0 crate, 1 dispatch, 2 ledger.
    Notice carries the task title (the old centred notice is gone; his lines play in the stop's sand line)."""
    g = lg(UI, 'PaintShiftBoard')
    mode = g.arg('Mode')
    shift = g.math('GreaterEqual_IntInt', A=mode, B=0)
    g.setv('ShiftMode', shift)
    g.do(TB + 'SetText', self=g.getv('ShiftTitle'), InText=g.arg('Notice'))
    g.do(TB + 'SetText', self=g.getv('ShiftReadout'), InText=g.arg('Readout'))
    vis(g, g.getv('ShiftTitle'), shift)
    vis(g, g.getv('Txt_Speaker'), g.math('Not_PreBool', A=shift))
    vis(g, g.getv('OrderCard'), ieq(g, mode, 0))
    vis(g, g.getv('ShiftReadout'), g.math('GreaterEqual_IntInt', A=mode, B=1))
    vis(g, g.getv('ShiftStatus'), shift)
    vis(g, g.getv('ChoiceLine'), shift)
    for name in ('ShiftRail', 'ShiftZone', 'ShiftMarker'):
        vis(g, g.getv(name), ieq(g, mode, 1))
    for name in ('LedgerGauge', 'LedgerTarget'):
        vis(g, g.getv(name), ieq(g, mode, 2))
    br = g.branch(shift)
    g.side(br)
    for i in range(3):  # three across the bottom, centred over the key caps
        slot = g.f(LAYOUT, Widget=g.getv(f'Btn_Answer{i}'))
        g.do(CS + 'SetAnchors', self=slot, InAnchors='(Minimum=(X=0.5,Y=1),Maximum=(X=0.5,Y=1))')
        g.do(CS + 'SetAlignment', self=slot, InAlignment='(X=.5,Y=1)')
        g.do(CS + 'SetPosition', self=slot, InPosition=f'(X={(i - 1) * CHOICE_X},Y=-92)')
        g.do(CS + 'SetSize', self=slot, InSize='(X=404,Y=84)')
        g.do(TB + 'SetJustification', self=g.getv(f'Txt_Answer{i}'), InJustification='Center')
    place(g, g.getv('KeyRow'), (.5, 1), (.5, 1), (0, -26))
    shown = g.tail
    g.side(br, False)
    for i, y in enumerate((-226, -154, -82)):  # the dialogue's left column (Refresh moves answer 0 again)
        slot = g.f(LAYOUT, Widget=g.getv(f'Btn_Answer{i}'))
        g.do(CS + 'SetAnchors', self=slot, InAnchors='(Minimum=(X=0,Y=1),Maximum=(X=1,Y=1))')
        g.do(CS + 'SetAlignment', self=slot, InAlignment='(X=0,Y=1)')
        g.do(CS + 'SetPosition', self=slot, InPosition=f'(X=56,Y={y})')
        g.do(CS + 'SetSize', self=slot, InSize='(X=92,Y=64)')
        g.do(TB + 'SetJustification', self=g.getv(f'Txt_Answer{i}'), InJustification='Left')
    place(g, g.getv('KeyRow'), (0, 1), (0, 1), (96, -26))
    g.joins = [shown]
    g.own('StyleChoices')
    g.finish()


def style_choices():
    """The chosen answer: full ink and a little larger; in a shift the underline slides under it (MoveShiftMarker).
    Also clears the red ink tag Refresh still paints behind the chosen answer (a monochrome game)."""
    g = lg(UI, 'StyleChoices')
    shift = g.getv('ShiftMode')
    for i in range(3):
        chosen = ieq(g, g.getv('ChoiceSelected'), i)
        g.do('/Script/UMG.Border:SetBrushColor', self=g.getv(f'AnswerPad{i}'), InBrushColor='(R=0,G=0,B=0,A=0)')
        k = g.math('SelectFloat', A=g.math('SelectFloat', A=1.06, B=1.03, bPickA=shift), B=1., bPickA=chosen)
        g.do(W + 'SetRenderTransformPivot', self=g.getv(f'Txt_Answer{i}'),
             Pivot=g.math('MakeVector2D', X=g.math('SelectFloat', A=.5, B=0., bPickA=shift), Y=.5))
        g.do(W + 'SetRenderScale', self=g.getv(f'Txt_Answer{i}'), Scale=g.math('MakeVector2D', X=k, Y=k))
        g.do(W + 'SetRenderOpacity', self=g.getv(f'Txt_Answer{i}'),
             InOpacity=g.math('SelectFloat', A=1., B=.45, bPickA=chosen))
    br = g.branch(shift)
    g.side(br)
    for i in range(3):  # no sideways nudge in a row of three
        g.do(W + 'SetRenderTranslation', self=g.getv(f'Btn_Answer{i}'), Translation='(X=0,Y=0)')
    g.setv('ChoiceTarget', g.math('Multiply_DoubleDouble', A=g.math('Conv_IntToDouble', InInt=g.math(
        'Subtract_IntInt', A=g.getv('ChoiceSelected'), B=1)), B=float(CHOICE_X)))
    g.finish()


def after_refresh():
    """Refresh's tail: no key caps unless the caller asks (SetKeys after Refresh), and the chosen answer is styled."""
    g = lg(UI, 'AfterRefresh')
    g.setv('ChoiceSelected', g.arg('Selected'))
    g.do(W + 'SetVisibility', self=g.getv('KeyRow'), InVisibility='Collapsed')
    g.own('StyleChoices')
    g.finish()


def set_keys():
    g = lg(UI, 'SetKeys')
    arrows = g.arg('Arrows')
    up = ieq(g, arrows, 1)
    g.do(W + 'SetVisibility', self=g.getv('KeyRow'), InVisibility='HitTestInvisible')
    some = g.math('Greater_IntInt', A=arrows, B=0)
    for name in ('CapPrev', 'CapNext', 'Txt_KeyChoose'):
        vis(g, g.getv(name), some)
    g.do(W + 'SetRenderTransformAngle', self=g.getv('Img_KeyPrev'), Angle=g.math('SelectFloat', A=-90., B=180., bPickA=up))
    g.do(W + 'SetRenderTransformAngle', self=g.getv('Img_KeyNext'), Angle=g.math('SelectFloat', A=90., B=0., bPickA=up))
    g.do(TB + 'SetText', self=g.getv('Txt_KeyChoose'), InText=g.arg('Choose'))
    for slot in ('A', 'B'):
        key = g.f('/Script/Engine.KismetTextLibrary:Conv_TextToString', InText=g.arg('Key' + slot))
        has = g.math('Not_PreBool', A=g.f('/Script/Engine.KismetTextLibrary:TextIsEmpty', InText=g.arg('Key' + slot)))
        vis(g, g.getv('Cap' + slot), has)
        vis(g, g.getv('Txt_Key' + slot), has)
        vis(g, g.getv('CapPad' + slot), g.f('/Script/Engine.KismetStringLibrary:EqualEqual_StrStr', A=key, B='Enter'))
        g.do(TB + 'SetText', self=g.getv('Txt_Cap' + slot), InText=g.arg('Key' + slot))
        g.do(TB + 'SetText', self=g.getv('Txt_Key' + slot), InText=g.arg('Label' + slot))
    g.finish()


def paint_order():
    """One row per item in the order, packed top to bottom; a pip per unit, filled as he packs; the newest pulses."""
    g = lg(UI, 'PaintOrder')
    targets = [g.arg(n) for n in ('Rice', 'Tea', 'Oat')]
    packed = [g.arg(n) for n in ('PackedRice', 'PackedTea', 'PackedOat')]
    used = [g.math('SelectInt', A=1, B=0, bPickA=g.math('Greater_IntInt', A=t, B=0)) for t in targets]
    rows = [None, used[0], g.math('Add_IntInt', A=used[0], B=used[1])]
    for k in range(3):
        y = g.math('Multiply_DoubleDouble', A=g.math('Conv_IntToDouble', InInt=rows[k]), B=float(ROW)) if k else 0.
        vis(g, g.getv(f'Txt_Order{k}'), g.math('Greater_IntInt', A=targets[k], B=0))
        g.do(CS + 'SetPosition', self=g.f(LAYOUT, Widget=g.getv(f'Txt_Order{k}')), InPosition=g.math('MakeVector2D', X=0, Y=y))
        for j in range(2):
            vis(g, g.getv(f'Pip{k}{j}'), g.math('Greater_IntInt', A=targets[k], B=j))
            g.do(CS + 'SetPosition', self=g.f(LAYOUT, Widget=g.getv(f'Pip{k}{j}')), InPosition=g.math(
                'MakeVector2D', X=PIP_X + j * PIP_GAP, Y=g.math('Add_DoubleDouble', A=y, B=10.)))
            g.do(IMG + 'SetColorAndOpacity', self=g.getv(f'Pip{k}{j}'), InColorAndOpacity=g.math(
                'SelectColor', A='(R=1,G=1,B=1,A=0.95)', B='(R=1,G=1,B=1,A=0.2)',
                bPickA=g.math('Greater_IntInt', A=packed[k], B=j)))
        grew = g.branch(g.math('Greater_IntInt', A=packed[k], B=g.getv(f'LastPacked{k}')))
        g.side(grew)
        g.setv('PulseAt', now(g))
        g.setv('PulseRow', k)
        g.setv('PulsePip', g.math('Subtract_IntInt', A=packed[k], B=1))
        last = g.tail
        g.side(grew, False)
        g.setv(f'LastPacked{k}', packed[k])  # the pulse branch joins in here
        g.link(last, 'then', g.tail, 'execute')
    g.finish()


def paint_status():
    g = lg(UI, 'PaintShiftStatus')
    g.setv('TimeTarget', g.math('FClamp', Value=g.arg('Remaining'), Min=0., Max=1.))
    for i in range(2):
        g.do(IMG + 'SetColorAndOpacity', self=g.getv(f'Mark{i}'), InColorAndOpacity=g.math(
            'SelectColor', A='(R=1,G=1,B=1,A=0.95)', B='(R=1,G=1,B=1,A=0.2)',
            bPickA=g.math('Greater_IntInt', A=g.arg('Mistakes'), B=i)))
    g.finish()


def move_marker():
    """MoveShiftMarker(Progress, Entrance), 30 Hz from the journey's TickShiftBoard: the dispatch marker, the card's
    entrance, the draining time line, the sliding underline and the pip pulse."""
    g = lg(UI, 'MoveShiftMarker')
    dt = .033
    g.do(W + 'SetRenderTranslation', self=g.getv('ShiftMarker'), Translation=g.math(
        'MakeVector2D', X=g.math('Multiply_DoubleDouble', A=g.arg('Progress'), B=544.), Y=0))
    rise = g.math('Multiply_DoubleDouble', A=g.math('Subtract_DoubleDouble', A=1., B=g.arg('Entrance')), B=14.)
    for name in ('ShiftTitle', 'OrderCard', 'ShiftReadout', 'ShiftStatus'):
        g.do(W + 'SetRenderOpacity', self=g.getv(name), InOpacity=g.arg('Entrance'))
        g.do(W + 'SetRenderTranslation', self=g.getv(name), Translation=g.math('MakeVector2D', X=0, Y=rise))
    g.setv('TimeShown', g.math('FInterpTo', Current=g.getv('TimeShown'), Target=g.getv('TimeTarget'), DeltaTime=dt, InterpSpeed=3.))
    g.do(W + 'SetRenderScale', self=g.getv('TimeFill'), Scale=g.math('MakeVector2D', X=g.getv('TimeShown'), Y=1.))
    g.setv('ChoiceX', g.math('FInterpTo', Current=g.getv('ChoiceX'), Target=g.getv('ChoiceTarget'), DeltaTime=dt, InterpSpeed=16.))
    g.do(W + 'SetRenderTranslation', self=g.getv('ChoiceLine'), Translation=g.math('MakeVector2D', X=g.getv('ChoiceX'), Y=0))
    fade = g.math('FClamp', Value=g.math('Subtract_DoubleDouble', A=1., B=g.math('Divide_DoubleDouble', A=g.math(
        'Subtract_DoubleDouble', A=now(g), B=g.getv('PulseAt')), B=.32)), Min=0., Max=1.)
    for k in range(3):
        for j in range(2):
            on = g.math('BooleanAND', A=ieq(g, g.getv('PulseRow'), k), B=ieq(g, g.getv('PulsePip'), j))
            s = g.math('SelectFloat', A=g.math('Add_DoubleDouble', A=1., B=g.math('Multiply_DoubleDouble', A=fade, B=.9)), B=1., bPickA=on)
            g.do(W + 'SetRenderScale', self=g.getv(f'Pip{k}{j}'), Scale=g.math('MakeVector2D', X=s, Y=s))
    g.finish()


def add_members(path, functions, variables):
    """Idempotent: variables update in place; functions are added once (graph lookup, no Python in the editor)."""
    import build_drive as b
    for name, typ, value in variables:
        b.call('blueprint_add_variable', path=path, variable_name=name, variable_type=typ, default_value=value,
               update_existing=True)
    for name, inputs in functions.items():
        if not b.h.call('blueprint_inspect_graph', {'path': path, 'graph_name': name}).get('ok'):
            b.call('blueprint_add_function', path=path, function_name=name, inputs=[dict(name=n, type=t) for n, t in inputs])
    b.call('blueprint_compile', path=path, save=True)


def wdeclare():
    add_members(UI, WFUNCS, WVARS)


def refresh_hook():
    """Call AfterRefresh(Selected) at the very end of Refresh (after the ui lane's AnimateIn), once."""
    import build_drive as b
    from held_tool_graphs import Batch
    nodes, edges = b.inspect(UI, 'Refresh')
    if any(n['title'].replace(' ', '').startswith('AfterRefresh') for n in nodes):
        return print('Refresh already calls AfterRefresh')
    entry = next(n['node_id'] for n in nodes if n['title'].replace(' ', '') == 'Refresh')
    linked = {e['from_node'] for e in edges if any(p['name'] == e['from_pin'] and p['type'] == 'exec'
                                                   for n in nodes if n['node_id'] == e['from_node'] for p in n['pins'])}
    fed = {e['to_node'] for e in edges if e['to_pin'] == 'execute'}
    tails = [n['node_id'] for n in nodes if n['node_id'] in fed and n['node_id'] not in linked
             and any(p['type'] == 'exec' and p['direction'] == 'output' for p in n['pins'])]
    assert len(tails) == 1, ('one exec tail expected', [n['title'] for n in nodes if n['node_id'] in tails])
    bt = Batch(UI, 'Refresh')
    bt.fn('after', UIC + ':AfterRefresh', 0, 0)
    bt.link(entry, 'Selected', 'after', 'Selected')
    bt.link(tails[0], 'then', 'after', 'execute')
    bt.run()


def wgraphs():
    for fn in (set_keys, style_choices, after_refresh, paint_board, paint_order, paint_status, move_marker):
        fn()
    refresh_hook()


# ---- the crate at Queen Market (BP_L2Journey) ----------------------------------------------------------------------
JVARS = [('DropAt0', 'float', '-1'), ('DropAt1', 'float', '-1'), ('DropAt2', 'float', '-1'), ('SpillAt', 'float', '-1'),
         ('CaseDoneAt', 'float', '-1')]
JFUNCS = {'PlaceCrate': [], 'HideCrate': [], 'CrateTick': [], 'SettleCrate': [], 'CrumbleCrateItems': [],
          'DropCrateItem': [('Kind', 'int'), ('Slot', 'int')], 'SpillCrateItem': [('Kind', 'int')]}
SCN = '/Script/Engine.SceneComponent:'
SMC = '/Script/Engine.StaticMeshComponent:'
GSL = '/Script/Engine.GameplayStatics:'
KSL = '/Script/Engine.KismetSystemLibrary:'


def declare():
    import build_drive as b
    have = {c['name'] for c in b.call('blueprint_get_info', path=JOURNEY).get('components', [])}
    for name in CRATE_COMPS:
        if name not in have:
            b.call('blueprint_add_component', path=JOURNEY, component_name=name,
                   component_class_path='/Script/Engine.StaticMeshComponent')
    add_members(JOURNEY, JFUNCS, JVARS)


def templates():
    import unreal as u
    assert not u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world(), 'PIE running'
    from free_drive_setup import templates as read
    bp, sds, lib, gathered, handles, comps = read(JOURNEY)
    root = next(h for n, h in handles.items() if n in ('DefaultSceneRoot', 'Root'))
    for name in CRATE_COMPS:
        assert name in handles, ('declare first', name)
        sds.attach_subobject(root, handles[name])
        c = comps[name]
        if name == 'ShiftCrate':
            c.set_static_mesh(u.load_asset(CRATE))
        c.set_collision_enabled(u.CollisionEnabled.NO_COLLISION)
        for prop, value in (('cast_shadow', True), ('visible', False), ('generate_overlap_events', False),
                            ('can_character_step_up_on', u.CanBeCharacterBase.ECB_NO), ('absolute_location', True),
                            ('absolute_rotation', True), ('absolute_scale', True)):
            c.set_editor_property(prop, value)
    u.BlueprintEditorLibrary.compile_blueprint(bp)
    assert u.EditorAssetLibrary.save_loaded_asset(bp, False)
    print('crate templates', CRATE_COMPS)


def jg(name):
    return lg(JOURNEY, name)


def jnow(g):
    return g.f(GSL + 'GetTimeSeconds')


def crate_at(g):
    return g.f(SCN + 'K2_GetComponentLocation', self=g.getv('ShiftCrate'))


def slot_base(g, k):
    """Slot k's rest point: along the crate's length (its X runs across his view), on its floor."""
    side = g.math('Multiply_VectorFloat', A=g.f(SCN + 'GetForwardVector', self=g.getv('ShiftCrate')), B=(k - 1) * SLOT_GAP)
    return g.math('Add_VectorVector', A=g.math('Add_VectorVector', A=crate_at(g), B=side), B='0,0,3')


def by_kind(g, kind, kind_values, scalar):
    out = kind_values[0]
    for i, v in enumerate(kind_values[1:], 1):
        out = g.math('SelectFloat' if scalar else 'SelectObject', A=v, B=out,
                     **{'bPickA' if scalar else 'bSelectA': ieq(g, kind, i)})
    return out


def burst(g, at, scale):
    g.do(SANDFX, Location=at, Scale=scale)


def crate_graphs():
    import build_job_hunt as jobs
    SHIFT = jobs.SHIFT

    g = jg('PlaceCrate')
    g.joins = None
    gate = g.branch(ieq(g, g.getv('Stop'), 0))
    g.side(gate)
    pc = g.f(GSL + 'GetPlayerController', PlayerIndex=0)
    yaw = (g.math('BreakRotator', InRot=g.f('/Script/Engine.Controller:GetControlRotation', self=pc))[0], 'Yaw')
    ahead = g.math('Multiply_VectorFloat', A=g.math('GetForwardVector', InRot=g.math('MakeRotator', Roll=0, Pitch=0, Yaw=yaw)),
                   B=CRATE_AHEAD)
    at = g.math('Add_VectorVector', A=g.f('/Script/Engine.Actor:K2_GetActorLocation', self=g.getv('Player')), B=ahead)
    trace = g.do(KSL + 'LineTraceSingle', Start=g.math('Add_VectorVector', A=at, B='0,0,150'),
                 End=g.math('Subtract_VectorVector', A=at, B='0,0,400'), TraceChannel='TraceTypeQuery1',
                 bTraceComplex=False, bIgnoreSelf=True)
    hit = g.f(GSL + 'BreakHitResult', Hit=(trace[0], 'OutHit'))
    ground = g.math('SelectVector', A=(hit[0], 'Location'), B=g.math('Subtract_VectorVector', A=at, B='0,0,92'),
                    bPickA=(trace[0], 'ReturnValue'))
    g.do(SCN + 'K2_SetWorldLocationAndRotation', self=g.getv('ShiftCrate'), NewLocation=ground,
         NewRotation=g.math('MakeRotator', Roll=0, Pitch=0, Yaw=g.math('Add_DoubleDouble', A=yaw, B=90.)),
         bSweep=False, bTeleport=True)
    g.do(SCN + 'SetVisibility', self=g.getv('ShiftCrate'), bNewVisibility=True, bPropagateToChildren=False)
    for name in CRATE_COMPS[1:]:
        g.do(SCN + 'SetVisibility', self=g.getv(name), bNewVisibility=False, bPropagateToChildren=False)
    for name in ('DropAt0', 'DropAt1', 'DropAt2', 'SpillAt', 'CaseDoneAt'):
        g.setv(name, -1.)
    # he looks down into the crate (BeginJob gave him the car's heading at a -4 deg pitch)
    g.do('/Script/Engine.Controller:SetControlRotation', self=g.f(GSL + 'GetPlayerController', PlayerIndex=0),
         NewRotation=g.math('MakeRotator', Roll=0, Pitch=PITCH, Yaw=yaw))
    g.finish()

    g = jg('HideCrate')
    for name in CRATE_COMPS:
        g.do(SCN + 'SetVisibility', self=g.getv(name), bNewVisibility=False, bPropagateToChildren=False)
    for name in ('DropAt0', 'DropAt1', 'DropAt2', 'SpillAt', 'CaseDoneAt'):
        g.setv(name, -1.)
    g.finish()

    g = jg('CrumbleCrateItems')
    for k in range(3):
        item = f'ShiftItem{k}'
        shown = g.branch(g.f(SCN + 'IsVisible', self=g.getv(item)))
        g.side(shown)
        burst(g, g.math('Add_VectorVector', A=g.f(SCN + 'K2_GetComponentLocation', self=g.getv(item)), B='0,0,8'), .45)
        g.do(SCN + 'SetVisibility', self=g.getv(item), bNewVisibility=False, bPropagateToChildren=False)
        g.setv(f'DropAt{k}', -1.)
        g.joins = [(shown, 'else')]
    g.finish()

    g = jg('DropCrateItem')
    kind, slot = g.arg('Kind'), g.arg('Slot')
    mesh = g.cast(by_kind(g, kind, [m for m, _ in ITEM_MESH], False), '/Script/Engine.StaticMesh', 'Static Mesh')
    scale = by_kind(g, kind, [s for _, s in ITEM_MESH], True)
    for k in range(3):
        item = f'ShiftItem{k}'
        here = g.branch(ieq(g, slot, k))
        g.side(here)
        g.do(SMC + 'SetStaticMesh', self=g.getv(item), NewMesh=mesh)
        g.do(SCN + 'SetWorldScale3D', self=g.getv(item), NewScale=g.math('MakeVector', X=scale, Y=scale, Z=scale))
        crate_yaw = (g.math('BreakRotator', InRot=g.f(SCN + 'K2_GetComponentRotation', self=g.getv('ShiftCrate')))[0], 'Yaw')
        g.do(SCN + 'K2_SetWorldLocationAndRotation', self=g.getv(item),
             NewLocation=g.math('Add_VectorVector', A=slot_base(g, k), B=f'0,0,{DROP_FROM}'),
             NewRotation=g.math('MakeRotator', Roll=0, Pitch=0, Yaw=g.math('Add_DoubleDouble', A=crate_yaw, B=90. + (k - 1) * 14.)),
             bSweep=False, bTeleport=True)
        g.do(SCN + 'SetVisibility', self=g.getv(item), bNewVisibility=True, bPropagateToChildren=False)
        g.setv(f'DropAt{k}', jnow(g))
        g.joins = [(here, 'else')]
    g.finish()

    g = jg('SpillCrateItem')
    kind = g.arg('Kind')
    g.own('CrumbleCrateItems')  # the round is lost: what he packed goes to sand with it
    mesh = g.cast(by_kind(g, kind, [m for m, _ in ITEM_MESH], False), '/Script/Engine.StaticMesh', 'Static Mesh')
    scale = by_kind(g, kind, [s for _, s in ITEM_MESH], True)
    g.do(SMC + 'SetStaticMesh', self=g.getv('ShiftSpill'), NewMesh=mesh)
    g.do(SCN + 'SetWorldScale3D', self=g.getv('ShiftSpill'), NewScale=g.math('MakeVector', X=scale, Y=scale, Z=scale))
    g.do(SCN + 'K2_SetWorldLocation', self=g.getv('ShiftSpill'),
         NewLocation=g.math('Add_VectorVector', A=crate_at(g), B=f'0,0,{DROP_FROM + 25.}'), bSweep=False, bTeleport=True)
    g.do(SCN + 'SetVisibility', self=g.getv('ShiftSpill'), bNewVisibility=True, bPropagateToChildren=False)
    g.setv('SpillAt', jnow(g))
    g.finish()

    def spill_pose(g, t):
        """Over the rim and out toward him: from above the crate's middle to the ground in front of it, tipping over."""
        crate = crate_at(g)
        toward = g.math('Multiply_VectorFloat', A=g.f(SCN + 'GetRightVector', self=g.getv('ShiftCrate')), B=40.)
        start = g.math('Add_VectorVector', A=crate, B=f'0,0,{DROP_FROM + 25.}')
        end = g.math('Add_VectorVector', A=g.math('Add_VectorVector', A=crate, B=toward), B='0,0,2')
        arc = g.math('MakeVector', X=0, Y=0, Z=g.math('Multiply_DoubleDouble', A=g.math('Sin', A=g.math(
            'Multiply_DoubleDouble', A=t, B=3.14159)), B=18.))
        pos = g.math('Add_VectorVector', A=g.math('VLerp', A=start, B=end, Alpha=g.math('Multiply_DoubleDouble', A=t, B=t)), B=arc)
        crate_yaw = (g.math('BreakRotator', InRot=g.f(SCN + 'K2_GetComponentRotation', self=g.getv('ShiftCrate')))[0], 'Yaw')
        rot = g.math('MakeRotator', Roll=g.math('Multiply_DoubleDouble', A=t, B=100.), Pitch=0,
                     Yaw=g.math('Add_DoubleDouble', A=crate_yaw, B=90.))
        return pos, rot, end

    g = jg('CrateTick')
    gate = g.branch(ieq(g, g.getv('Stop'), 0))
    g.side(gate)
    for k in range(3):
        item, var = f'ShiftItem{k}', f'DropAt{k}'
        falling = g.branch(g.math('GreaterEqual_DoubleDouble', A=g.getv(var), B=0.))
        g.side(falling)
        t = g.math('FClamp', Value=g.math('Divide_DoubleDouble', A=g.math('Subtract_DoubleDouble', A=jnow(g), B=g.getv(var)),
                                          B=DROP_SECONDS), Min=0., Max=1.)
        height = g.math('Multiply_DoubleDouble', A=DROP_FROM, B=g.math('Subtract_DoubleDouble', A=1., B=g.math('Multiply_DoubleDouble', A=t, B=t)))
        g.do(SCN + 'K2_SetWorldLocation', self=g.getv(item), NewLocation=g.math(
            'Add_VectorVector', A=slot_base(g, k), B=g.math('MakeVector', X=0, Y=0, Z=height)), bSweep=False, bTeleport=True)
        landed = g.branch(g.math('GreaterEqual_DoubleDouble', A=t, B=1.))
        g.side(landed)
        g.setv(var, -1.)
        g.do(GSL + 'SpawnSoundAtLocation', Sound=THUD, Location=slot_base(g, k), VolumeMultiplier=.9, PitchMultiplier=.8)
        burst(g, g.math('Add_VectorVector', A=slot_base(g, k), B='0,0,10'), .35)
        g.joins = [(falling, 'else'), (landed, 'else')]
    spilling = g.branch(g.math('GreaterEqual_DoubleDouble', A=g.getv('SpillAt'), B=0.))
    g.side(spilling)
    t = g.math('FClamp', Value=g.math('Divide_DoubleDouble', A=g.math('Subtract_DoubleDouble', A=jnow(g), B=g.getv('SpillAt')),
                                      B=SPILL_SECONDS), Min=0., Max=1.)
    pos, rot, end = spill_pose(g, t)
    g.do(SCN + 'K2_SetWorldLocationAndRotation', self=g.getv('ShiftSpill'), NewLocation=pos, NewRotation=rot,
         bSweep=False, bTeleport=True)
    down = g.branch(g.math('GreaterEqual_DoubleDouble', A=t, B=1.))
    g.side(down)
    g.setv('SpillAt', -1.)
    burst(g, g.math('Add_VectorVector', A=end, B='0,0,8'), .9)
    g.do(SCN + 'SetVisibility', self=g.getv('ShiftSpill'), bNewVisibility=False, bPropagateToChildren=False)
    g.joins = [(spilling, 'else'), (down, 'else')]
    due = g.branch(g.math('BooleanAND', A=g.math('GreaterEqual_DoubleDouble', A=g.getv('CaseDoneAt'), B=0.),
                          B=g.math('GreaterEqual_DoubleDouble', A=jnow(g), B=g.getv('CaseDoneAt'))))
    g.side(due)
    g.setv('CaseDoneAt', -1.)
    burst(g, g.math('Add_VectorVector', A=crate_at(g), B='0,0,30'), 1.1)
    g.own('CrumbleCrateItems')
    still = g.branch(ieq(g, g.getv('DialogueMode'), SHIFT))
    g.side(still)
    g.setv('DialogueReady', True)
    g.own('RenderShift')
    g.finish()

    g = jg('SettleCrate')  # the shift ended mid-drop (FinishJob): put what was falling at rest, drop the spill
    gate = g.branch(ieq(g, g.getv('Stop'), 0))
    g.side(gate)
    for k in range(3):
        item, var = f'ShiftItem{k}', f'DropAt{k}'
        falling = g.branch(g.math('GreaterEqual_DoubleDouble', A=g.getv(var), B=0.))
        g.side(falling)
        g.do(SCN + 'K2_SetWorldLocation', self=g.getv(item), NewLocation=slot_base(g, k), bSweep=False, bTeleport=True)
        g.setv(var, -1.)
        g.joins = [(falling, 'else')]
    g.setv('CaseDoneAt', -1.)
    spilling = g.branch(g.math('GreaterEqual_DoubleDouble', A=g.getv('SpillAt'), B=0.))
    g.side(spilling)
    burst(g, g.math('Add_VectorVector', A=crate_at(g), B='0,0,20'), .9)
    g.do(SCN + 'SetVisibility', self=g.getv('ShiftSpill'), bNewVisibility=False, bPropagateToChildren=False)
    g.setv('SpillAt', -1.)
    g.finish()


# ---- callers, input, cleanup ---------------------------------------------------------------------------------------
def hooks():
    """Rebuild the graphs that draw the stops (their sources now call the new look)."""
    import build_job_hunt as jobs
    import shift_minigames as shift
    for fn in (shift.tick_board, shift.accept_round, shift.submit, shift.render_shift,
               lambda: jobs.render_pitch(jobs.JOBS), lambda: jobs.render(jobs.JOBS), lambda: jobs.begin_shift(jobs.JOBS),
               jobs.clear, jobs.finish):
        fn()


def keys_input():
    """Left and Right choose too (the shift's three choices sit in a row); D-pad Left stays 'read the C.V.'."""
    import build_drive as b
    nodes, edges = b.inspect(JOURNEY, 'EventGraph')
    titles = {n['title'].split('\n')[0]: n['node_id'] for n in nodes}
    from held_tool_graphs import Batch
    bt = Batch(JOURNEY, 'EventGraph')
    for i, (key, delta) in enumerate((('Left', -1), ('Right', 1))):
        if key in titles and any(e['from_node'] == titles[key] for e in edges):
            continue
        bt.ops.append(dict(op='add_node', ref='k' + key, node_type='input_key', key=key, x=i * 700, y=10400))
        bt.fn('m' + key, JOURNEY + '.BP_L2Journey_C:DialogueMove', 300 + i * 700, 10400, Delta=delta)
        bt.link('k' + key, 'Pressed', 'm' + key, 'execute')
    if bt.ops:
        bt.comment('Left and Right move the choice', [o['ref'] for o in bt.ops if o['op'] == 'add_node'])
        bt.run()


def keys_consume_off():
    """Editor Python: the new Left/Right key events must not swallow the car's arrow steering (IMC_L2Drive)."""
    import unreal as u
    bp = u.load_asset(JOURNEY)
    u.get_editor_subsystem(u.AssetEditorSubsystem).close_all_editors_for_asset(bp)
    ed = u.BlueprintGraphEditor.get_graph_editor_by_name(bp, 'EventGraph')
    changed = []
    for node in ed.list_all_nodes():
        title = str(u.BlueprintEditorLibrary.get_node_title(node)).split('\n')[0]
        if node.get_class().get_name() == 'K2Node_InputKey' and title in ('Left', 'Right'):
            node.set_editor_property('consume_input', False)
            changed.append(title)
    assert sorted(changed) == ['Left', 'Right'], changed
    u.BlueprintEditorLibrary.compile_blueprint(bp)
    assert u.EditorAssetLibrary.save_loaded_asset(bp, False)
    print('consume off', changed)


def cleanup():
    """The slab, the colour cells, the centred notice and PaintCrate: nothing references them any more."""
    import build_drive as b
    # PaintCrate went first (2026-11-18: emptied, then BlueprintEditorLibrary.remove_function_graph in editor Python)
    assert not b.h.call('blueprint_inspect_graph', {'path': UI, 'graph_name': 'PaintCrate'}).get('ok'), 'remove PaintCrate first'
    for name in ('ShiftPaper', 'ShiftCell0', 'ShiftCell1', 'ShiftCell2', 'ShiftNotice'):
        if b.call('ui_query', path=UI, name_pattern=name).get('matches'):
            print(name, b.call('ui_remove_element', widget_blueprint_path=UI, widget_name=name).get('ok'))
    print(b.call('blueprint_compile', path=UI, save=True).get('saved'))


SANDLINE = '/Game/FoA/UI/Widgets/Common/WBP_SandLine'
CARD = ROOT + '/WBP_L2ShiftTimeCard'


def sandline_halo():
    """WBP_SandLine option bHalo (instance editable, off by default): the HUD subtitle's soft halo (T_UI_SoftDot)
    behind the line, fading in as the letters form and out as they blow away. Outside the retainer, so the sand
    material never touches it. Only the stop lines (bright sand behind them) turn it on."""
    import build_drive as b
    from held_tool_graphs import Batch, inspect
    if 'Img_Halo' not in str(b.call('ui_query', path=SANDLINE)):
        b.call('ui_build_tree', widget_blueprint_path=SANDLINE, parent_widget_name='RootCanvas', tree=[{
            'class': 'Image', 'name': 'Img_Halo', 'properties': {
                'Brush': f'(ImageSize=(X=256,Y=256),DrawAs=Image,ResourceObject="{DOT}")', 'ColorAndOpacity': [0, 0, 0, .6],
                'Visibility': 'Collapsed', 'RenderOpacity': 0},
            'slot_props': dict(anchors_min=[0, 0], anchors_max=[1, 1], alignment=[0, 0], position=[-200, -70],
                               size=[-200, -70], z_order=-1)}])
        b.call('ui_move_element', widget_blueprint_path=SANDLINE, widget_name='Img_Halo', index=0)
        b.call('ui_set_variable', widget_blueprint_path=SANDLINE, widget_name='Img_Halo', is_variable=True)
    b.call('blueprint_add_variable', path=SANDLINE, variable_name='bHalo', variable_type='bool', default_value='false',
           category='Look', instance_editable=True, update_existing=True)
    b.call('blueprint_compile', path=SANDLINE, save=True)
    K = '/Script/Engine.KismetMathLibrary:'
    nodes, edges = inspect(SANDLINE, 'Play')
    if not any('Img_Halo' in str(n) for n in nodes):
        fed = {e['to_node'] for e in edges if e['to_pin'] == 'execute'}
        linked = {e['from_node'] for e in edges if e['from_pin'] in ('then', 'else')}
        tail = [n['node_id'] for n in nodes if n['node_id'] in fed and n['node_id'] not in linked]
        assert len(tail) == 1, tail
        bt = Batch(SANDLINE, 'Play')
        bt.get('on', 'bHalo', 0, 300)
        bt.node('br', 'branch', 300, 0)
        bt.link('on', 'bHalo', 'br', 'Condition')
        bt.link(tail[0], 'then', 'br', 'execute')
        for ref, vis in (('show', 'HitTestInvisible'), ('hide', 'Collapsed')):
            bt.get(ref + 'w', 'Img_Halo', 500, 400)
            bt.fn(ref, W + 'SetVisibility', 600, 0, InVisibility=vis)
            bt.link(ref + 'w', 'Img_Halo', ref, 'self')
        bt.link('br', 'then', 'show', 'execute')
        bt.link('br', 'else', 'hide', 'execute')
        bt.comment('Optional soft halo behind the line (bHalo)', ['on', 'br', 'show', 'hide', 'showw', 'hidew'])
        bt.run()
    nodes, edges = inspect(SANDLINE, 'Step')
    if not any('Img_Halo' in str(n) for n in nodes):
        state = next(n['node_id'] for n in nodes if n['title'].replace(' ', '').startswith('SetVectorParameterValue')
                     and any(p['name'] == 'ParameterName' and p.get('default_value') == 'State' for p in n['pins']))
        nxt = next(e for e in edges if e['from_node'] == state and e['from_pin'] == 'then')
        bt = Batch(SANDLINE, 'Step')
        bt.cut(state, 'then', nxt['to_node'], nxt['to_pin'])
        bt.get('t', 'T', 0, 600); bt.get('span', 'FormSpan', 0, 700); bt.get('out', 'OutT', 0, 800)
        bt.fn('in', K + 'Divide_DoubleDouble', 200, 600); bt.link('t', 'T', 'in', 'A'); bt.link('span', 'FormSpan', 'in', 'B')
        bt.fn('inc', K + 'FClamp', 400, 600, Min=0, Max=1); bt.link('in', 'ReturnValue', 'inc', 'Value')
        bt.fn('o', K + 'Divide_DoubleDouble', 200, 800, B=.42); bt.link('out', 'OutT', 'o', 'A')
        bt.fn('oc', K + 'FClamp', 400, 800, Min=0, Max=1); bt.link('o', 'ReturnValue', 'oc', 'Value')
        bt.fn('left', K + 'Subtract_DoubleDouble', 600, 800, A=1); bt.link('oc', 'ReturnValue', 'left', 'B')
        bt.fn('a', K + 'Multiply_DoubleDouble', 800, 700); bt.link('inc', 'ReturnValue', 'a', 'A'); bt.link('left', 'ReturnValue', 'a', 'B')
        bt.get('hw', 'Img_Halo', 800, 500)
        bt.fn('set', W + 'SetRenderOpacity', 1000, 0); bt.link('hw', 'Img_Halo', 'set', 'self'); bt.link('a', 'ReturnValue', 'set', 'InOpacity')
        bt.link(state, 'then', 'set', 'execute')
        bt.link('set', 'then', nxt['to_node'], nxt['to_pin'])
        bt.comment('Halo follows the line in and out', ['t', 'span', 'out', 'in', 'inc', 'o', 'oc', 'left', 'a', 'hw', 'set'])
        bt.run()
    # the stop lines sit over bright sand: halo on, there only
    r = b.call('ui_set_widget_properties', widget_blueprint_path=CARD, widget_name='Line_Stop', properties={'bHalo': True})
    assert not r.get('rejected_properties'), r
    b.call('blueprint_compile', path=CARD, save=True)


def run(step):
    if step == 'selftest':
        return selftest()
    if step == 'textures':
        return textures()
    import build_drive as b
    import editor_lock
    owner = 'level2'
    os.environ.update(FOA_AGENT=owner, HAYBA_AGENT_ID=owner)
    token = editor_lock.acquire(owner, wait_s=1500, ttl=300, areas=[UI, JOURNEY] + ([SANDLINE, CARD] if step == 'halo' else []))
    os.environ['FOA_LEASE'] = token or editor_lock.hayba_leases(owner)[0][0]
    try:
        assert not b.call('editor_get_state')['pie_running'], 'PIE is running'
        dict(widget=widget, wdeclare=wdeclare, declare=declare, wgraphs=wgraphs, graphs=crate_graphs, hooks=hooks,
             input=keys_input, cleanup=cleanup, halo=sandline_halo)[step]()
    finally:
        editor_lock.release(owner)


if __name__ == '__main__':
    step = os.environ.get('FOA_LOOK_STEP')
    if step:
        sys.path.insert(0, 'P:/FoA/Tools/Unreal/level2')
        dict(import_=import_textures, templates=templates, keys=keys_consume_off)[step + ('_' if step == 'import' else '')]()
    else:
        for name in sys.argv[1:]:
            print('== step', name, flush=True)
            run(name)
