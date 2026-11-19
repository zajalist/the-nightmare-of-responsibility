"""Credits from the project's recorded asset sources. Existing Darker Grotesque and sand Back button.

Offline --selftest; --apply uses Hayba for the new tree. Run through ue_remote with FOA_CREDITS_PHASE=wire,
then ui_compile_widget and blueprint_set_defaults bIsFocusable=true through Hayba.
"""
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'encounter'))
from gen_encounter_tree import canvas, text, vbox, pad, SAND_BUTTON  # noqa: E402

CREDITS = '/Game/FoA/UI/Widgets/Menus/WBP_Credits'


def block(name, title, body, top=0):
    return pad(vbox(name, [text(name + '_Title', 'H2', title, size=32),
                            pad(text(name + '_Body', 'Body', body, size=24, wrap=720), top=8)]), top=top)


def tree():
    left = vbox('CreditsLeft', [
        block('Engine', 'Engine and characters', 'Unreal Engine and MetaHuman by Epic Games.'),
        block('Typeface', 'Typography', 'Darker Grotesque by Gabriel Lam and Viet Anh Nguyen.\nSIL Open Font License 1.1.', 28),
        block('Assets', 'Animation and environment', 'Animation by Quaternius. CC0 1.0.\nEnvironment assets by Poly Haven. CC0.', 28),
        block('Audio', 'Sound', 'Sonniss Game Audio GDC bundles and Kenney.', 28),
    ])
    right = vbox('CreditsRight', [
        block('Tools', 'Built with', 'Lux3D by Manycore and Hayba.'),
        block('Suit', 'Suit', 'Man Black Business Suit by Style3D CG.\nAdapted for this game. CC BY 4.0.', 28),
        pad(text('SuitSource', 'Body',
                 'Source: https://sketchfab.com/3d-models/man-black-business-suit-7a669a06fb954d459985ccaa98672177\n'
                 'Author: https://sketchfab.com/Style3DMeta\n'
                 'License: https://creativecommons.org/licenses/by/4.0/', size=20, wrap=720), top=18),
        block('BattleIcons', 'Battle icons', 'Battle icons by Lorc and Delapouite, game-icons.net.\n'
              'CC BY 3.0. Used in monochrome.\nhttps://creativecommons.org/licenses/by/3.0/', 28),
        pad(text('Hackathon', 'Body', 'Created for the Aholo hackathon.', size=24), top=36),
    ])
    return [
        canvas({'class': 'Image', 'name': 'CreditsShade', 'properties': {
            'Brush': '(DrawAs=Box,TintColor=(SpecifiedColor=(R=0.003,G=0.003,B=0.003,A=0.96)))',
            'Visibility': 'HitTestInvisible'}}, [0, 0], [0, 0], [0, 0], [1920, 1080]),
        canvas(text('CreditsTitle', 'H1', 'Credits', size=72), [0, 0], [0, 0], [120, 90]),
        canvas(text('CreditsGame', 'H2', 'The Nightmare of Responsibility', size=38), [0, 0], [0, 0], [120, 210]),
        canvas(left, [0, 0], [0, 0], [120, 320], [720, 560]),
        canvas(right, [0, 0], [0, 0], [1040, 320], [760, 560]),
        canvas({'class': SAND_BUTTON, 'name': 'Btn_Back', 'properties': {
            'Label': 'Back', 'bIsVariable': True, 'TextAlphaRest': 0.95,
            'SandMaterial': '/Game/FoA/UI/Materials/MI_UI_SandText_Menu.MI_UI_SandText_Menu'}},
            [0, 1], [0, 1], [108, -60]),
    ]


def selftest():
    names, visible = [], []
    def walk(n):
        names.append(n['name'])
        visible.append(str(n.get('properties', {}).get('Text', '')))
        for child in n.get('children', []):
            walk(child)
    for n in tree():
        walk(n)
    assert len(names) == len(set(names))
    assert 'Btn_Back' in names and any('Style3D CG' in s for s in visible)
    assert not any('dream' in s.lower() or '·' in s or '•' in s for s in visible)
    print('Credits selfcheck: unique widgets, factual attribution, Back button, text rules')


def apply():
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from hayba_call import call
    def c(cmd, **params):
        r = call(cmd, params)
        assert r.get('ok'), r
        return r.get('data', {})
    assert not c('editor_get_state').get('pie_running'), 'PIE must finish first'
    if not Path('P:/FoA/Content/FoA/UI/Widgets/Menus/WBP_Credits.uasset').exists():
        c('ui_create_widget', path='/Game/FoA/UI/Widgets/Menus', name='WBP_Credits')
    if not c('ui_query', path=CREDITS, name_pattern='CreditsShade').get('matches'):
        c('ui_build_tree', widget_blueprint_path=CREDITS, parent_widget_name='RootCanvas', tree=tree())
    c('ui_compile_widget', widget_blueprint_path=CREDITS, save_on_success=True)
    print('Credits tree created with Hayba')


def wire():
    previous = os.environ.get('FOA_WIDGETS')
    try:
        os.environ['FOA_WIDGETS'] = 'Credits'
        exec(compile(open('P:/FoA/Tools/Unreal/ui/wire_overlays.py', encoding='utf-8').read(),
                     'P:/FoA/Tools/Unreal/ui/wire_overlays.py', 'exec'), globals())
    finally:
        if previous is None:
            os.environ.pop('FOA_WIDGETS', None)
        else:
            os.environ['FOA_WIDGETS'] = previous
    g = Graph(CREDITS)
    focus = next(n for n in g.ed.list_all_nodes() if BEL.get_node_title(n).splitlines()[0].replace(' ', '') == 'FocusButton')
    label = g.call('/Game/FoA/UI/Widgets/Common/WBP_SandButton.WBP_SandButton_C:SetLabel', 1792, 0, NewLabel='Back')
    button = g.get('Btn_Back', 1728, 192)
    g.link(button, 'Btn_Back', label, 'self')
    g.link(focus, 'then', label, 'execute')
    g.comment('Back label', '', [label, button], C_VISUAL)
    compile_save(CREDITS, defaults={'bIsFocusable': True})


if os.environ.get('FOA_CREDITS_PHASE') == 'cleanup':
    if os.environ.get('FOA_WIDGETS') == 'Credits':
        os.environ.pop('FOA_WIDGETS', None)
    print('Credits-only wiring environment cleared')
elif os.environ.get('FOA_CREDITS_PHASE') == 'wire':
    wire()
else:
    selftest()
    if '--apply' in sys.argv:
        apply()
