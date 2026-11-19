"""Apply the final UI-owned text (docs/design/story/script.md sections 3 and 7) to the live widgets, in place (Hayba).
HUD hint rows, the phone inbox labels, both versions of each message, and the notebook empty state.
  python Tools/Unreal/ui/aaa_text_final.py"""
import json
import sys

sys.path.insert(0, 'P:/FoA/Tools/Unreal')
import hayba_call as hc  # noqa: E402

HUD = '/Game/FoA/UI/Game/WBP_HUD'
PHONE = '/Game/FoA/UI/Game/WBP_Phone'
INBOX = ["Mom\nYour shirt's in the wardrobe", 'Career Center\nReminder: today', 'Draft\nim up']
EARLY = ["Mom\n\nMorning! Your shirt's in the wardrobe, I ironed it.\n\nEat something before you go. Love you",
         'Career Center\n\nReminder: your drop-in appointment is today at 10:30. Reply C to cancel.',
         'Draft\n\nim up']
LATER = ["Mom\n\nProud of you. Call me when you're out. Love you",
         'Career Center\n\nWe missed you on Tuesday. Drop in any weekday, 9 to 4. No appointment needed.',
         "Draft\n\nsorry about yesterday. and the day before. today's different i promise"]
OLD_HEAD = ('Mum\n', 'Careers office\n', 'Unsent\n')


def c(cmd, **p):
    r = hc.call(cmd, p)
    d = r.get('data') or {}
    print(cmd, r.get('ok'), d.get('succeeded', d.get('applied')), d.get('error') or r.get('error') or '')
    assert r.get('ok'), r
    return d


def pages(bp, graph):
    off, nodes = 0, []
    while off is not None:
        d = hc.call('blueprint_inspect_graph', {'path': bp, 'graph_name': graph, 'offset': off})['data']
        nodes += d['nodes']
        off = ((d.get('page') or {}).get('nodes') or {}).get('next_offset')
    return nodes


def pin(n, name):
    return next((p.get('default_value') or '') for p in n['pins'] if p['name'] == name)


# HUD hint rows
c('ui_set_widget_properties', widget_blueprint_path=HUD, widget_name='Txt_PhoneHint', properties={'Text': 'P Phone    Ctrl Crouch'})
tool = [n for n in pages(HUD, 'SetToolFeedback') if n['title'].replace(' ', '') == 'SelectString']
tool = [n for n in tool if 'Release' in pin(n, 'B')]
assert len(tool) == 1, len(tool)
c('blueprint_graph_batch', path=HUD, graph_name='SetToolFeedback',
  ops=[{'op': 'set_pin', 'node_id': tool[0]['node_id'], 'pin_name': 'B', 'value': 'D A Turn    Q Release'}])
c('ui_compile_widget', widget_blueprint_path=HUD)
c('ui_save_widget', widget_blueprint_path=HUD)

# Phone inbox, messages, notebook empty state
for i, line in enumerate(INBOX):
    c('ui_set_widget_properties', widget_blueprint_path=PHONE, widget_name=f'Txt_Sender{i}', properties={'Text': line})
sel = [n for n in pages(PHONE, 'OpenMessage') if n['title'].replace(' ', '') == 'SelectString']
ops = []
for i in range(3):
    hit = [n for n in sel if pin(n, 'B').startswith(OLD_HEAD[i]) or pin(n, 'B') == EARLY[i]]
    assert len(hit) == 1, (i, len(hit), [pin(n, 'B')[:20] for n in sel])
    ops += [{'op': 'set_pin', 'node_id': hit[0]['node_id'], 'pin_name': 'B', 'value': EARLY[i]},
            {'op': 'set_pin', 'node_id': hit[0]['node_id'], 'pin_name': 'A', 'value': LATER[i]}]
c('blueprint_graph_batch', path=PHONE, graph_name='OpenMessage', ops=ops)
empty = [n for n in pages(PHONE, 'AppendNotebookLine') if n['title'].replace(' ', '') == 'SelectString']
print('notebook selectors', [(pin(n, 'A'), pin(n, 'B')) for n in empty])
for n in empty:
    for side in ('A', 'B'):
        v = pin(n, side)
        if v.startswith('Nothing written'):
            c('blueprint_graph_batch', path=PHONE, graph_name='AppendNotebookLine',
              ops=[{'op': 'set_pin', 'node_id': n['node_id'], 'pin_name': side, 'value': 'No notes yet.'}])
c('ui_compile_widget', widget_blueprint_path=PHONE)
c('ui_save_widget', widget_blueprint_path=PHONE)
print(json.dumps({'ok': True}))
