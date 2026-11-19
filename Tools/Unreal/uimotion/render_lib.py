"""Test renders of the UI Lib masters through a throwaway widget, all through Hayba (lease the Lib folder first).
  python Tools/Unreal/uimotion/render_lib.py build      # TMP_uimotion_LibSheet: meter, ring, panel retainer with a word
  python Tools/Unreal/uimotion/render_lib.py shot NAME  # render it to Saved/Screenshots/Hayba/NAME.png
  python Tools/Unreal/uimotion/render_lib.py state hit  # push the instances into their hit / mid-reveal state (or: rest)
The sheet is deleted afterwards with asset_delete (cleanup rule); the instances end at rest."""
import json
import sys

sys.path.insert(0, 'P:/FoA/Tools/Unreal/ui')
from build_sandtext_hayba import hb  # noqa: E402

LIB = '/Game/FoA/UI/Materials/Lib'
W = f'{LIB}/TMP_uimotion_LibSheet'
MAT = '/Game/FoA/UI/Materials'
STATES = {  # instance -> params, at rest and in the hit / mid-reveal state
    'rest': {'MI_UI_Meter_Garment': {'Value': 0.62, 'TrailFrom': 0.85, 'ChipT': 0.0, 'Hit': 0.0},
             'MI_UI_Ring_Parry': {'Progress': 0.7, 'Hit': 0.0},
             'MI_UI_Panel_Prompt': {'Reveal': 1.0, 'Slice': 0.0, 'Hit': 0.0}},
    'hit': {'MI_UI_Meter_Garment': {'Value': 0.48, 'TrailFrom': 0.85, 'ChipT': 0.35, 'Hit': 1.0},
            'MI_UI_Ring_Parry': {'Progress': 0.86, 'Hit': 0.6},
            'MI_UI_Panel_Prompt': {'Reveal': 0.55, 'Slice': 0.6, 'Hit': 0.35}},
}


def add(cls, parent, name, **slot):
    return hb('ui_add_element', widget_blueprint_path=W, child_class=cls, parent_widget_name=parent, name=name,
              slot_props=slot)


def build():
    r = hb('ui_create_widget', path=LIB, name='TMP_uimotion_LibSheet')
    root = (r.get('data') or r).get('root') or 'RootCanvas'
    print('root', root)
    add('VerticalBox', root, 'Vb', x=40, y=40, w=900, h=360)
    add('Image', 'Vb', 'Img_Meter', padding=[0, 0, 0, 24])
    hb('ui_set_brush', widget_blueprint_path=W, widget_name='Img_Meter', resource=f'{MAT}/MI_UI_Meter_Garment',
       draw_as='Image', image_size=[488, 40])
    add('HorizontalBox', 'Vb', 'Hb')
    add('Image', 'Hb', 'Img_Ring', padding=[0, 0, 40, 0])
    hb('ui_set_brush', widget_blueprint_path=W, widget_name='Img_Ring', resource=f'{MAT}/MI_UI_Ring_Parry',
       draw_as='Image', image_size=[180, 180])
    add('RetainerBox', 'Hb', 'Ret_Panel', vertical_alignment='Center')
    hb('ui_set_widget_properties', widget_blueprint_path=W, widget_name='Ret_Panel',
       properties={'EffectMaterial': f'{MAT}/MI_UI_Panel_Prompt.MI_UI_Panel_Prompt', 'TextureParameter': 'Texture'})
    add('TextBlock', 'Ret_Panel', 'Txt_Word', padding=[34, 26, 40, 30])
    hb('ui_set_widget_properties', widget_blueprint_path=W, widget_name='Txt_Word',
       properties={'Text': 'Open the wardrobe',
                   'Font': {'FontObject': '/Game/FoA/UI/Fonts/F_FoA_UI.F_FoA_UI', 'TypefaceFontName': 'SemiBold', 'Size': 34}})
    hb('ui_compile_widget', widget_blueprint_path=W)
    print('sheet ok')


def state(name):
    for mi, params in STATES[name].items():
        for k, v in params.items():
            hb('material_set_param', instance_path=f'{MAT}/{mi}', param_name=k, value=v)
    print('state', name)


def shot(name):
    r = hb('ui_render_widget_to_png', widget_blueprint_path=W, width=980, height=440, scale=1.5, out_path=f'{name}.png',
           inline_image=False)
    print(json.dumps(r.get('data') or r)[:400])


if __name__ == '__main__':
    {'build': build, 'shot': lambda: shot(sys.argv[2]), 'state': lambda: state(sys.argv[2])}[sys.argv[1]]()
