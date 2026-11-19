"""WBP_EndCard (story lane): the level's last words on the black, centred in the intro's type (story_text.ENDING,
"Day one."). BP_BeatDirector's EndLevel creates it after the fade and removes it before the front end's EndOfLevel.
Hayba only; idempotent.  python Tools/LookDev/build_end_card.py"""
import os
import sys
from pathlib import Path

sys.path[:0] = ['P:/FoA/Tools/Unreal', 'P:/FoA/Tools/Unreal/flow']
import hayba_call as h  # noqa: E402
from story_text import ENDING  # noqa: E402

W = '/Game/FoA/UI/Intro/WBP_EndCard'


def c(cmd, **p):
    r = h.call(cmd, p, timeout=90)
    assert r.get('ok'), (cmd, r)
    d = r.get('data', {})
    assert d.get('ok', True) and not d.get('failed'), (cmd, d)
    return d


os.environ['HAYBA_AGENT_ID'] = 'story'
assert not c('editor_get_state')['pie_running'], 'PIE running'
token = h.lease_acquire('story', ['asset:' + W], ttl_s=90, wait_s=60)
try:
    if not Path('P:/FoA/Content/FoA/UI/Intro/WBP_EndCard.uasset').exists():
        c('ui_create_widget', path='/Game/FoA/UI/Intro', name='WBP_EndCard')
    q = c('ui_query', path=W)
    names = lambda n: [n['name']] + [x for ch in n.get('children', []) for x in names(ch)]  # noqa: E731
    if 'Txt_Line' not in names(q['root']):
        c('ui_add_element', widget_blueprint_path=W, name='Txt_Line', child_class='TextBlock', parent_widget_name=q['root']['name'])
    c('ui_set_widget_properties', widget_blueprint_path=W, widget_name='Txt_Line',
      properties={'Text': ENDING, 'Font': {'FontObject': '/Game/FoA/UI/Fonts/F_FoA_UI', 'TypefaceFontName': 'Medium', 'Size': 46},
                  'ColorAndOpacity': {'SpecifiedColor': {'R': 0.87, 'G': 0.88, 'B': 0.89, 'A': 1}},
                  'Justification': 'Center', 'Visibility': 'HitTestInvisible'},
      slot_props={'anchors_min': [0.5, 0.5], 'anchors_max': [0.5, 0.5], 'alignment': [0.5, 0.5], 'position': [0, 0],
                  'size': [800, 90]})
    r = c('ui_compile_widget', widget_blueprint_path=W)
    c('ui_save_widget', widget_blueprint_path=W)
    print('WBP_EndCard built', r.get('compiled_clean', r))
finally:
    h.release('story', token)
