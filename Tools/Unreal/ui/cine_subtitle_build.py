"""Cinematic subtitles (story's ask for LS_BattleIntro, main approved 2026-11-10): a line that stays up while the
story HUD is hidden (SetStoryHUDHidden) and across camera cuts, because it is its own viewport widget.

  BP_FoAFrontEnd.ShowCinematicSubtitle(Line: Text, Seconds: float, Speaker: Name)   Seconds <= 0 holds until Hide
  BP_FoAFrontEnd.HideCinematicSubtitle()

Look: a copy of the HUD subtitle (Brd_Narration halo, Txt_Narration type, same safe-zone spot), the same 0.26 s rise,
the player's Subtitles on/off and size; Speaker 'Nightmare' at 0.7 text opacity. ZOrder 12: over the HUD and screens,
under the pause menu (15).
Steps (each idempotent; quiet slot, PIE off):  python Tools/Unreal/ui/cine_subtitle_build.py widget | graphs | fe
"""
import sys

sys.path.insert(0, 'P:/FoA/Tools/Unreal')
sys.path.insert(0, 'P:/FoA/Tools/Unreal/ui')
import editor_lock  # noqa: E402
import hayba_call as hc  # noqa: E402
from hayba_batch import B, compile_bp, entry_of, is_empty, ok, save  # noqa: E402

UI = '/Game/FoA/UI/Game'
WBP = f'{UI}/WBP_CineSubtitle'
WBPC = f'{WBP}.WBP_CineSubtitle_C'
HUD_TREE = '/Game/FoA/UI/Game/WBP_HUD.WBP_HUD:WidgetTree.'
FE = '/Game/FoA/UI/Framework/BP_FoAFrontEnd'
SG = '/Game/FoA/UI/Framework/SG_FoASettings.SG_FoASettings_C'
SETTINGS_LIB = '/Game/FoA/UI/Framework/BPFL_FoASettings.BPFL_FoASettings_C'
KML, KSL, GS = '/Script/Engine.KismetMathLibrary', '/Script/Engine.KismetSystemLibrary', '/Script/Engine.GameplayStatics'
TB, W = '/Script/UMG.TextBlock', '/Script/UMG.Widget'
STEP = sys.argv[1] if len(sys.argv) > 1 else ''


def props(path):
    return (hc.call('object_get_property', {'path': path}).get('data') or {}).get('properties', {})


def widget():
    if not hc.call('blueprint_get_info', {'path': WBP}).get('ok'):
        ok(hc.call('ui_create_widget', {'path': UI, 'name': 'WBP_CineSubtitle'}), 'create')  # comes with RootCanvas
    if 'Txt_Line' not in str(hc.call('ui_query', {'path': WBP}).get('data')):
        ok(hc.call('ui_build_tree', {'widget_blueprint_path': WBP, 'tree': {
            'class': 'SafeZone', 'name': 'Safe_Frame', 'slot_props': {'anchors_min': [0, 0], 'anchors_max': [1, 1], 'position': [0, 0], 'size': [0, 0]},
            'children': [{'class': 'Overlay', 'name': 'Ovl_Frame', 'children': [
                {'class': 'Border', 'name': 'Brd_Line', 'slot_props': {'padding': '(Left=48,Top=0,Right=48,Bottom=48)',
                                                                       'horizontal_alignment': 'HAlign_Center', 'vertical_alignment': 'VAlign_Bottom'},
                 'children': [{'class': 'TextBlock', 'name': 'Txt_Line', 'properties': {'Text': ''}}]}]}]}}), 'tree')
        for w in ('Brd_Line', 'Txt_Line'):
            ok(hc.call('ui_set_variable', {'widget_blueprint_path': WBP, 'widget_name': w, 'is_variable': True}), w)
    # the HUD subtitle's exact look, copied rather than restated
    tree = f'{WBP}.WBP_CineSubtitle:WidgetTree.'
    # the halo brush does not survive a text copy: set it as aaa_hud.tree2 does
    ok(hc.call('ui_set_widget_properties', {'widget_blueprint_path': WBP, 'widget_name': 'Brd_Line', 'properties': {
        'Background': {'ResourceObject': '/Game/FoA/UI/Textures/T_UI_SoftDot.T_UI_SoftDot', 'DrawAs': 'Image',
                       'TintColor': {'SpecifiedColor': [0, 0, 0, 1]}}}}), 'halo')
    for src, dst, keys in (('Brd_Narration', 'Brd_Line', ('BrushColor', 'Padding', 'HorizontalAlignment', 'VerticalAlignment')),
                           ('Txt_Narration', 'Txt_Line', ('Font', 'ColorAndOpacity', 'WrapTextAt', 'Justification', 'ShadowOffset',
                                                          'ShadowColorAndOpacity', 'LineHeightPercentage'))):
        have = props(HUD_TREE + src)
        r = hc.call('object_set_property', {'path': tree + dst, 'properties': {k: have[k] for k in keys}})
        print(dst, (r.get('data') or {}).get('applied'), r.get('error') or '')
    ok(hc.call('object_set_property', {'path': tree + 'Brd_Line', 'properties': {'Visibility': 'Collapsed'}}), 'collapsed')
    have = {v['name'] for v in hc.call('blueprint_get_info', {'path': WBP})['data'].get('variables', [])}
    if 'SubT' not in have:
        ok(hc.call('blueprint_add_variable', {'path': WBP, 'variable_name': 'SubT', 'variable_type': 'real', 'default_value': '0.0',
                                               'category': 'Subtitle'}), 'SubT')
    funcs = hc.call('blueprint_get_info', {'path': WBP})['data']['functions']
    for name, spec in (('ShowLine', dict(inputs=[{'name': 'Line', 'type': 'text'}, {'name': 'Seconds', 'type': 'real'}, {'name': 'Speaker', 'type': 'name'}])),
                       ('HideLine', {}), ('SubStep', {})):
        if name not in funcs:
            ok(hc.call('blueprint_add_function', {'path': WBP, 'function_name': name, **spec}), name)
    compile_bp(WBP, widget=True)
    print('widget', save(WBP))


def graphs():
    brd, txt = ('Brd_Line',), ('Txt_Line',)
    if is_empty(WBP, 'HideLine'):
        e, _, _ = entry_of(WBP, 'HideLine')
        b = B(WBP, 'HideLine')
        b.chain(e, b.fn(f'{KSL}:K2_ClearTimer', FunctionName='HideLine'), b.fn(f'{KSL}:K2_ClearTimer', FunctionName='SubStep'),
                b.fn(f'{W}:SetVisibility', self=b.get(*brd), InVisibility='Collapsed'))
        b.run()
    if is_empty(WBP, 'SubStep'):  # the HUD's subtitle rise: opacity easeOut3 over 0.26 s, up from 6 px
        e, _, _ = entry_of(WBP, 'SubStep')
        b = B(WBP, 'SubStep')
        st = b.set('SubT', b.fn(f'{KML}:Add_DoubleDouble', A=b.get('SubT'), B=0.0167))
        a = b.fn(f'{KML}:Ease', A=0.0, B=1.0, EasingFunc='EaseOut', BlendExp=3.0,
                 Alpha=b.fn(f'{KML}:FClamp', Value=b.fn(f'{KML}:Divide_DoubleDouble', A=b.get('SubT'), B=0.26), Min=0.0, Max=1.0))
        op = b.fn(f'{W}:SetRenderOpacity', self=b.get(*brd), InOpacity=a)
        tr = b.fn(f'{W}:SetRenderTranslation', self=b.get(*brd),
                  Translation=b.fn(f'{KML}:MakeVector2D', X=0.0, Y=b.fn(f'{KML}:Lerp', A=6.0, B=0.0, Alpha=a)))
        br = b.node('branch', {'Condition': b.fn(f'{KML}:GreaterEqual_DoubleDouble', A=b.get('SubT'), B=0.26)})
        b.chain(e, st, op, tr, br, b.fn(f'{KSL}:K2_ClearTimer', FunctionName='SubStep'))
        b.run()
    if is_empty(WBP, 'ShowLine'):
        e, _, _ = entry_of(WBP, 'ShowLine')
        b = B(WBP, 'ShowLine')
        load = b.fn(f'{SETTINGS_LIB}:LoadSettings')
        on = b.node('branch', {'Condition': b.get('bSubtitles', cls=SG, target=(load, 'Settings'))})
        size = b.fn(f'{TB}:SetFontSize', self=b.get(*txt), DisplayFontSize=b.fn(f'{KML}:Conv_IntToDouble', InInt=b.fn(f'{KML}:Add_IntInt', B=22, A=b.fn(
            f'{KML}:Multiply_IntInt', B=6, A=b.fn(f'{KML}:Clamp', Min=0, Max=2, Value=b.get('SubtitleSize', cls=SG, target=(load, 'Settings')))))))
        text = b.fn(f'{TB}:SetText', self=b.get(*txt), InText=(e, 'Line'))
        voice = b.fn(f'{W}:SetRenderOpacity', self=b.get(*txt), InOpacity=b.fn(
            f'{KML}:SelectFloat', A=0.7, B=1.0, bPickA=b.fn(f'{KML}:EqualEqual_NameName', A=(e, 'Speaker'), B='Nightmare')))
        show = b.fn(f'{W}:SetVisibility', self=b.get(*brd), InVisibility='HitTestInvisible')
        zero = b.set('SubT', 0.0)
        first = b.fn(f'{WBPC}:SubStep')
        rise = b.fn(f'{KSL}:K2_SetTimer', FunctionName='SubStep', Time=0.0167, bLooping=True)
        clear = b.fn(f'{KSL}:K2_ClearTimer', FunctionName='HideLine')
        timed = b.node('branch', {'Condition': b.fn(f'{KML}:Greater_DoubleDouble', A=(e, 'Seconds'), B=0.0)})
        hold = b.fn(f'{KSL}:K2_SetTimer', FunctionName='HideLine', Time=(e, 'Seconds'), bLooping=False)
        off = b.fn(f'{WBPC}:HideLine')
        b.chain(e, load, on, size, text, voice, show, zero, first, rise, clear, timed, hold)
        b.chain((on, 'else'), off)
        b.run()
    compile_bp(WBP, widget=True)
    print('graphs', save(WBP))


def fe():
    tok = editor_lock.acquire('ui', wait_s=120, ttl=120, areas=[FE])
    try:
        have = {v['name'] for v in hc.call('blueprint_get_info', {'path': FE})['data'].get('variables', [])}
        if 'CineSub' not in have:
            ok(hc.call('blueprint_add_variable', {'path': FE, 'variable_name': 'CineSub', 'variable_type': f'object:{WBPC}',
                                                   'category': 'Story'}), 'CineSub')
        funcs = hc.call('blueprint_get_info', {'path': FE})['data']['functions']
        for name, spec in (('ShowCinematicSubtitle', dict(inputs=[{'name': 'Line', 'type': 'text'}, {'name': 'Seconds', 'type': 'real'},
                                                                  {'name': 'Speaker', 'type': 'name'}])), ('HideCinematicSubtitle', {})):
            if name not in funcs:
                ok(hc.call('blueprint_add_function', {'path': FE, 'function_name': name, **spec}), name)
        if is_empty(FE, 'ShowCinematicSubtitle'):
            e, _, _ = entry_of(FE, 'ShowCinematicSubtitle')
            b = B(FE, 'ShowCinematicSubtitle')
            made = b.node('branch', {'Condition': b.fn(f'{KSL}:IsValid', Object=b.get('CineSub'))})
            cw = b.node('create_widget', {'Class': WBPC, 'OwningPlayer': b.fn(f'{GS}:GetPlayerController', PlayerIndex=0)})
            keep = b.set('CineSub', (cw, 'ReturnValue'))
            add = b.fn('/Script/UMG.UserWidget:AddToViewport', self=b.get('CineSub'), ZOrder=12)
            line = b.fn(f'{WBPC}:ShowLine', self=b.get('CineSub'), Line=(e, 'Line'), Seconds=(e, 'Seconds'), Speaker=(e, 'Speaker'))
            b.chain(e, made, line)
            b.chain((made, 'else'), cw, keep, add, line)
            b.run()
        if is_empty(FE, 'HideCinematicSubtitle'):
            e, _, _ = entry_of(FE, 'HideCinematicSubtitle')
            b = B(FE, 'HideCinematicSubtitle')
            made = b.node('branch', {'Condition': b.fn(f'{KSL}:IsValid', Object=b.get('CineSub'))})
            b.chain(e, made, b.fn(f'{WBPC}:HideLine', self=b.get('CineSub')))
            b.run()
        compile_bp(FE)
        print('FE', save(FE))
    finally:
        if tok:
            hc.release('ui', tok)
            editor_lock.forget('ui', tok)


assert not hc.call('editor_get_state', {})['data']['pie_running'], 'PIE running'
token = editor_lock.acquire('ui', wait_s=120, ttl=120, areas=[WBP])
try:
    {'widget': widget, 'graphs': graphs, 'fe': fe}[STEP]()
finally:
    if token:
        hc.release('ui', token)
        editor_lock.forget('ui', token)
