"""Hayba TCP calls for the title screen per the approved page v3.1 at 1920x1080 (replay: hayba_replay.py --calls).
  python Tools/Unreal/ui/title_calls.py > Saved/UIShots/title.jsonl
Logotype at the page's spot (x 146, top of "The Nightmare" at 243), "Press any key" bottom centre 119 px up with a soft
dark halo, and a darker bottom edge (30% of the frame, 55%) so the prompt reads over the bright floor."""
import json

P = '/Game/FoA/UI/Widgets/Menus/WBP_Title'
TEX = '/Game/FoA/UI/Textures'
calls = []


def c(cmd, **p):
    calls.append({'cmd': cmd, 'params': p})


def slot(name, **sp):
    c('ui_set_widget_properties', widget_blueprint_path=P, widget_name=name, slot_props=sp)


def brush(name, tex, tint, size):
    c('ui_set_widget_properties', widget_blueprint_path=P, widget_name=name,
      properties={'Brush': {'ResourceObject': f'{TEX}/{tex}.{tex}', 'TintColor': {'SpecifiedColor': tint},
                            'DrawAs': 'Image', 'ImageSize': {'X': size[0], 'Y': size[1]}}})


slot('Logo', horizontal_alignment='Left', vertical_alignment='Top', padding=[146, 243, 0, 0])
# halo first so it draws under the prompt; both bottom-centred in the safe frame
c('ui_add_element', widget_blueprint_path=P, child_class='Image', parent_widget_name='Ovl_Frame', name='Img_PromptHalo')
c('ui_move_element', widget_blueprint_path=P, widget_name='Img_PromptHalo', index=0)
brush('Img_PromptHalo', 'T_UI_SoftDot', [0, 0, 0, 0.85], [560, 150])
slot('Img_PromptHalo', horizontal_alignment='Center', vertical_alignment='Bottom', padding=[0, 0, 0, 61])
slot('Txt_Press', horizontal_alignment='Center', vertical_alignment='Bottom', padding=[0, 0, 0, 119])
# the darker bottom edge spans the whole screen, under the safe frame
c('ui_add_element', widget_blueprint_path=P, child_class='Image', parent_widget_name='RootCanvas', name='Img_BottomEdge')
brush('Img_BottomEdge', 'T_UI_FadeV', [0, 0, 0, 0.55], [4, 256])
slot('Img_BottomEdge', anchors_min=[0, 0.7], anchors_max=[1, 1], position=[0, 0], size=[0, 0], z_order=0)
slot('Safe_Frame', z_order=2)
c('ui_compile_widget', widget_blueprint_path=P)
c('ui_save_widget', widget_blueprint_path=P)
c('ui_render_widget_to_png', widget_blueprint_path=P, width=1920, height=1080, out_path='step2_WBP_Title_after.png',
  inline_image=False)
if __name__ == '__main__':
    for d in calls:
        print(json.dumps(d))
