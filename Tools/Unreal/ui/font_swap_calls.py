"""Writes the Hayba call list for the Darker Grotesque swap and the Aholo boot card (replay with hayba_replay.py --calls).
  python Tools/Unreal/ui/font_swap_calls.py > Saved/UIShots/font_swap.jsonl
Sizes follow the approved direction page v3.1 at 1920 px (UMG pt = CSS px x 0.75)."""
import json

F = '/Game/FoA/UI/Fonts'
DISPLAY, UI = f'{F}/F_FoA_Display', f'{F}/F_FoA_UI'
W = '/Game/FoA/UI/Widgets'
TEX = '/Game/FoA/UI/Textures'
STAGE = 'C:/Users/Admin/AppData/Local/Temp/hayba-asset-connectors/ui/logos'
INK, MUTED = [0.86, 0.86, 0.86, 1.0], [0.86, 0.86, 0.86, 0.62]
calls = []


def c(cmd, **p):
    calls.append({'cmd': cmd, 'params': p})


def composite(styles):
    return '(DefaultTypeface=(Fonts=(' + ','.join(
        f'(Name="{s}",Font=(FontFaceAsset="/Script/Engine.FontFace\'{F}/Faces/FF_DarkerGrotesque_{s}.'
        f'FF_DarkerGrotesque_{s}\'",LoadingPolicy=LazyLoad,Hinting=Default))' for s in styles) + ')))'


# composite fonts: the first typeface is the fallback for any widget naming one the font lacks
c('object_set_property', path=f'{DISPLAY}.F_FoA_Display',
  properties={'CompositeFont': composite(['ExtraBold']), 'LegacyFontName': 'ExtraBold'})
c('object_set_property', path=f'{UI}.F_FoA_UI',
  properties={'CompositeFont': composite(['SemiBold', 'Medium']), 'LegacyFontName': 'SemiBold'})
c('asset_save', asset_paths=[DISPLAY, UI])

STYLE = {  # widget -> [(text block, font, typeface, pt, letter spacing, colour)]
    f'{W}/Common/WBP_Logotype': [('Txt_Line1', DISPLAY, 'ExtraBold', 110, 0, INK), ('Txt_Line2', UI, 'SemiBold', 51, 0, INK)],
    f'{W}/Common/WBP_SandButton': [('Txt_Label', UI, 'SemiBold', 38, 0, INK)],
    f'{W}/Common/WBP_InputHint': [('Txt_Key', DISPLAY, 'ExtraBold', 12, 0, INK), ('Txt_Action', UI, 'Medium', 16, 0, MUTED)],
    f'{W}/Common/WBP_ConfirmDialog': [('Txt_Title', DISPLAY, 'ExtraBold', 52, 0, INK), ('Txt_Body', UI, 'Medium', 20, 0, MUTED)],
    f'{W}/Menus/WBP_BootSplash': [('Txt_MadeWith', UI, 'Medium', 15, 0, MUTED), ('Txt_Lux3D', DISPLAY, 'ExtraBold', 43, 10, INK),
                                  ('Txt_Hayba', UI, 'Medium', 16, 0, MUTED)],
    f'{W}/Menus/WBP_MainMenu': [('Txt_Build', UI, 'Medium', 16, 0, MUTED)],
    f'{W}/Menus/WBP_Pause': [('Txt_Header', DISPLAY, 'ExtraBold', 59, 0, INK), ('Txt_Objective', UI, 'Medium', 16, 0, MUTED)],
    f'{W}/Menus/WBP_Title': [('Txt_Press', UI, 'SemiBold', 19, 0, INK)],
    '/Game/FoA/UI/Game/WBP_HUD': [('Txt_Objective', DISPLAY, 'ExtraBold', 36, 0, INK)],
    '/Game/FoA/UI/Game/WBP_SkipHint': [('Txt_Hint', UI, 'Medium', 16, 0, MUTED)],
}
for wbp, rows in STYLE.items():
    for name, font, face, size, track, col in rows:
        c('ui_set_text_style', widget_blueprint_path=wbp, widget_name=name, font_asset=font, typeface=face, size=size,
          letter_spacing=track, color=col)

# logotype line 2: the page's 228 px indent and 0.58 em baseline gap (the tall Darker Grotesque ascender needs -30 px)
c('ui_set_slot_layout', widget_blueprint_path=f'{W}/Common/WBP_Logotype', widget_name='Txt_Line2', padding=[228, -30, 0, 0])

# textures: Aholo logo (unaltered brand colours), the prompt halo and the darker bottom edge
for name in ('T_UI_Logo_Aholo', 'T_UI_SoftDot', 'T_UI_FadeV'):
    c('asset_import', source_file=f'{STAGE}/{name}.png', destination_path=TEX, asset_type='texture')
    c('texture_set_settings', path=f'{TEX}/{name}',
      properties={'compression_settings': 'EditorIcon', 'lod_group': 'UI', 'mip_gen_settings': 'SimpleAverage',
                  'filter': 'Trilinear', 'never_stream': True, 'srgb': True,
                  **({'max_texture_size': 512} if name.startswith('T_UI_Logo_') else {})})
c('asset_save', asset_paths=[f'{TEX}/{n}' for n in ('T_UI_Logo_Aholo', 'T_UI_SoftDot', 'T_UI_FadeV')])

# boot card 2: "Made with" small above; Aholo's logo (60 px high) and "Lux3D" (800) side by side, 21 px apart
SPL = f'{W}/Menus/WBP_BootSplash'
c('ui_add_element', widget_blueprint_path=SPL, child_class='HorizontalBox', parent_widget_name='VB_Lux3D', name='Row_Aholo')
c('ui_add_element', widget_blueprint_path=SPL, child_class='Image', parent_widget_name='Row_Aholo', name='Img_Aholo')
c('ui_set_brush', widget_blueprint_path=SPL, widget_name='Img_Aholo', resource=f'{TEX}/T_UI_Logo_Aholo',
  image_size=[267, 60], tint=[1, 1, 1, 1], draw_as='Image')
c('ui_reparent_element', widget_blueprint_path=SPL, widget_name='Txt_Lux3D', new_parent_name='Row_Aholo')
c('ui_set_text_style', widget_blueprint_path=SPL, widget_name='Txt_Lux3D', text='Lux3D')
c('ui_set_slot_layout', widget_blueprint_path=SPL, widget_name='Img_Aholo', vertical_alignment='Center', fill=0)
c('ui_set_slot_layout', widget_blueprint_path=SPL, widget_name='Txt_Lux3D', vertical_alignment='Center', fill=0,
  padding=[21, 0, 0, 0])
c('ui_set_slot_layout', widget_blueprint_path=SPL, widget_name='Row_Aholo', horizontal_alignment='Center', padding=[0, 8, 0, 0])
c('ui_set_slot_layout', widget_blueprint_path=SPL, widget_name='Txt_MadeWith', horizontal_alignment='Center')

for wbp in STYLE:
    c('ui_compile_widget', widget_blueprint_path=wbp)
    c('ui_save_widget', widget_blueprint_path=wbp)

if __name__ == '__main__':
    for d in calls:
        print(json.dumps(d))
