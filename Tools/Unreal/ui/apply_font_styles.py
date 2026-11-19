"""Darker Grotesque on every UI text block, over Hayba TCP (ui_set_widget_properties with a nested Font struct; the
MCP-only ui_set_text_style is not on TCP). Then compile + save each widget. Hold the UI lease as FOA_AGENT=ui.
  python Tools/Unreal/ui/apply_font_styles.py [--only WBP_Logotype,...]
Composite fonts and faces come first (import_fonts.py, then font_swap_calls.py's object_set_property lines)."""
import json
import sys

sys.path.insert(0, 'P:/FoA/Tools/Unreal')
sys.path.insert(0, 'P:/FoA/Tools/Unreal/ui')
from hayba_replay import send_retry  # noqa: E402
from font_swap_calls import STYLE  # noqa: E402  (importing prints nothing: its printing is at module end, guarded below)

only = sys.argv[sys.argv.index('--only') + 1].split(',') if '--only' in sys.argv else None
state = {}
bad = 0
for wbp, rows in STYLE.items():
    if only and wbp.rsplit('/', 1)[1] not in only:
        continue
    for name, font, face, size, track, col in rows:
        props = {'Font': {'FontObject': f"{font}.{font.rsplit('/', 1)[1]}", 'TypefaceFontName': face, 'Size': size,
                          'LetterSpacing': track},
                 'ColorAndOpacity': {'SpecifiedColor': list(col)}}
        r = send_retry(state, 'ui_set_widget_properties', {'widget_blueprint_path': wbp, 'widget_name': name,
                                                             'properties': props})
        ok = r.get('ok') and not (r.get('data') or {}).get('failed')
        bad += 0 if ok else 1
        print('ok  ' if ok else 'FAIL', wbp.rsplit('/', 1)[1], name, '' if ok else json.dumps(r)[:300])
    for cmd in ('ui_compile_widget', 'ui_save_widget'):
        r = send_retry(state, cmd, {'widget_blueprint_path': wbp})
        print('ok  ' if r.get('ok') else 'FAIL', cmd, wbp.rsplit('/', 1)[1])
sys.exit(1 if bad else 0)
