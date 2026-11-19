"""Edit the existing physical phone screen in place through native Hayba UI calls."""
import sys

sys.path.insert(0, 'P:/FoA/Tools/Unreal')
from hayba_call import call

P = '/Game/FoA/UI/Game/WBP_Phone'


def run(cmd, **params):
    result = call(cmd, params)
    assert result.get('ok'), result
    data = result.get('data', {})
    assert not data.get('failed_properties'), data
    return data


def prop(name, properties=None, slot=None):
    return run('ui_set_widget_properties', widget_blueprint_path=P, widget_name=name,
               properties=properties or {}, slot_props=slot or {})


def main():
    existing = run('ui_query', path=P, flatten=True)['matches']
    names = {w['name'] for w in existing}

    def add(name, cls, parent):
        if name not in names:
            run('ui_add_element', widget_blueprint_path=P, name=name, child_class=cls, parent_widget_name=parent)
            names.add(name)

    def move(name, parent):
        run('ui_mutate_tree', operation='reparent', widget_blueprint_path=P, widget_name=name, new_parent_name=parent)

    def text(name, value, size=26, alpha=1):
        prop(name, {'Text': value, 'Font': {'FontObject': '/Game/FoA/UI/Fonts/F_FoA_UI.F_FoA_UI',
                                          'TypefaceFontName': 'SemiBold', 'Size': size},
                    'ColorAndOpacity': {'SpecifiedColor': {'R': .9, 'G': .9, 'B': .9, 'A': alpha}, 'ColorUseRule': 'UseColor_Specified'},
                    'AutoWrapText': True})

    def button(name):
        style={}
        for state,shade in [('Normal',.025),('Hovered',.08),('Pressed',.13),('Disabled',.015)]:
            style[state]={'DrawAs':'RoundedBox','TintColor':{'SpecifiedColor':{'R':shade,'G':shade,'B':shade,'A':1},
                                                          'ColorUseRule':'UseColor_Specified'},
                          'OutlineSettings':{'Width':0,'CornerRadii':{'X':8,'Y':8,'Z':8,'W':8}}}
        prop(name,{'WidgetStyle':style,'BackgroundColor':'(R=1,G=1,B=1,A=1)','IsFocusable':False})

    prop('Brd_Screen', {'Padding': '(Left=42,Top=62,Right=42,Bottom=82)',
                        'BrushColor': '(R=1,G=1,B=1,A=1)',
                        'Background': {'DrawAs': 'Box', 'TintColor': {'SpecifiedColor': {'R':.008,'G':.008,'B':.008,'A':1},
                                                                   'ColorUseRule':'UseColor_Specified'}}})
    prop('Txt_Clock', {'Font': {'FontObject': '/Game/FoA/UI/Fonts/F_FoA_Display.F_FoA_Display',
                              'TypefaceFontName': 'ExtraBold', 'Size': 76}})
    prop('Btn_Action', {'bPlainLabel': True, 'LabelSize': 26.0, 'TextAlphaRest': 1.0}, {'padding': [0, 22, 0, 10]})
    add('HB_Pages', 'HorizontalBox', 'VB_Phone')
    add('Pages', 'WidgetSwitcher', 'VB_Phone')
    add('Page_Tasks', 'VerticalBox', 'Pages')
    add('Page_Messages', 'VerticalBox', 'Pages')
    add('Page_Notes', 'VerticalBox', 'Pages')
    move('VB_Tasks', 'Page_Tasks')
    move('Txt_Notebook', 'Page_Notes')
    for title, page, heading in [('Tasks', 'Page_Tasks', 'Today'), ('Messages', 'Page_Messages', 'Morning reminder'),
                                 ('Notes', 'Page_Notes', 'What I know')]:
        add('Btn_' + title, 'Button', 'HB_Pages')
        add('Tab_' + title, 'TextBlock', 'Btn_' + title)
        text('Tab_' + title, title, 22)
        prop('Btn_' + title, {'IsFocusable': False, 'BackgroundColor': '(R=.1,G=.1,B=.1,A=1)'},
             {'fill': 1, 'padding': [0, 0, 8, 0]})
        button('Btn_'+title)
        prop('Tab_' + title, slot={'Padding': '(Left=8,Top=12,Right=8,Bottom=12)'})
        add('Heading_' + title, 'TextBlock', page)
        text('Heading_' + title, heading, 34)
        run('ui_mutate_tree', operation='move', widget_blueprint_path=P, widget_name='Heading_' + title, index=0)
    add('Inbox', 'VerticalBox', 'Page_Messages')
    add('ReadMessage', 'VerticalBox', 'Page_Messages')
    add('MessagesScroll', 'ScrollBox', 'Page_Messages')
    add('MessageContent', 'VerticalBox', 'MessagesScroll')
    move('Inbox', 'MessageContent')
    move('ReadMessage', 'MessageContent')
    prop('MessagesScroll', {'Clipping':'ClipToBounds','AllowOverscroll':False}, {'fill':1,'padding':[0,16,0,0]})
    for i, line in enumerate(("Mom\nYour shirt's in the wardrobe", 'Career Center\nReminder: today', 'Draft\nim up')):
        add('Btn_Message' + str(i), 'Button', 'Inbox')
        add('Txt_Sender' + str(i), 'TextBlock', 'Btn_Message' + str(i))
        text('Txt_Sender' + str(i), line, 24)
        prop('Btn_Message' + str(i), {'IsFocusable': False}, {'padding': [0, 0, 0, 12]})
        button('Btn_Message'+str(i))
        prop('Txt_Sender' + str(i), slot={'Padding': '(Left=14,Top=14,Right=14,Bottom=14)'})
    add('Txt_Message', 'TextBlock', 'ReadMessage')
    move('Txt_Message', 'ReadMessage')
    text('Txt_Message', '', 25)
    prop('ReadMessage', {'Visibility': 'Collapsed'})
    prop('Txt_Message', slot={'padding': [0, 0, 12, 12]})
    add('NotesScroll', 'ScrollBox', 'Page_Notes')
    move('Txt_Notebook', 'NotesScroll')
    prop('NotesScroll', slot={'fill': 1})
    prop('Txt_Notebook', {'Font': {'FontObject': '/Game/FoA/UI/Fonts/F_FoA_UI.F_FoA_UI',
                                 'TypefaceFontName': 'Medium', 'Size': 25}}, {'padding': [0, 24, 0, 0]})
    prop('VB_Tasks', slot={'padding': [0, 24, 0, 0]})
    for i in range(4):
        prop('Txt_Task' + str(i), {'Font': {'FontObject': '/Game/FoA/UI/Fonts/F_FoA_UI.F_FoA_UI',
                                         'TypefaceFontName': 'SemiBold', 'Size': 28}},
             {'padding': [0, 0 if i == 0 else 22, 0, 0]})
    prop('HB_Pages', slot={'padding': [0, 24, 0, 20]})
    prop('Pages', {'Clipping':'ClipToBounds'}, slot={'fill': 1})
    prop('Spc_Push', {'Visibility': 'Collapsed'})
    add('Txt_Controls', 'TextBlock', 'VB_Phone')
    text('Txt_Controls', 'Left and Right  Pages      Up and Down  Browse\nEnter or A  Read      Backspace or B  Back\nP  Put away', 18, .85)
    for i, name in enumerate(('Txt_Clock', 'HB_Day', 'HB_Crossed', 'HB_Pages', 'Pages', 'Spc_Push', 'Btn_Action', 'Txt_Controls')):
        run('ui_mutate_tree', operation='move', widget_blueprint_path=P, widget_name=name, index=i)
    for name in ('Pages', 'Btn_Tasks', 'Btn_Messages', 'Btn_Notes', 'Tab_Tasks', 'Tab_Messages', 'Tab_Notes', 'Txt_Message',
                 'Inbox', 'ReadMessage', 'MessagesScroll', 'NotesScroll', 'Btn_Message0', 'Btn_Message1', 'Btn_Message2',
                 'Txt_Sender0', 'Txt_Sender1', 'Txt_Sender2'):
        run('ui_set_variable', widget_blueprint_path=P, widget_name=name, is_variable=True)
    run('ui_compile_widget', widget_blueprint_path=P)
    run('ui_save_widget', widget_blueprint_path=P)
    print('Phone screen updated in place')


if __name__ == '__main__':
    main()
