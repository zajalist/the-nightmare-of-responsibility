"""Bounded settings proof in the coordinator's free-roam PIE. Restores preferences on every exit.
Exercises the real row delegates, checks the persisted slot, captures each page, then returns through Pause.
"""
import json
import os
import time

import unreal

OUT = 'P:/FoA/Saved/UIShots/settings_runtime.json'
LAYOUT_ONLY = os.environ.get('FOA_LAYOUT_ONLY') == '1'
NATIVE_LAYOUT = os.environ.get('FOA_UI_NATIVE_LAYOUT') == '1'
CAPTURE_DIR = os.environ.get('FOA_UI_OUT', 'P:/FoA/Saved/UIShots/settings_pages')
ACK = CAPTURE_DIR + '/slate_page_ack.txt'
FE = '/Game/FoA/UI/Framework/BP_FoAFrontEnd.BP_FoAFrontEnd_C'
SG_FIELDS = ('MasterVolume', 'EffectsVolume', 'AmbienceVolume', 'InterfaceVolume', 'MouseSensitivity',
             'bInvertY', 'bSubtitles', 'SubtitleSize', 'bReduceMotion', 'bShowPhotoWarning')
SAVED_ROWS = (('Row_Master', 'MasterVolume', 0.65), ('Row_Effects', 'EffectsVolume', 0.7),
              ('Row_Ambience', 'AmbienceVolume', 0.75), ('Row_Interface', 'InterfaceVolume', 0.8),
              ('Row_Sensitivity', 'MouseSensitivity', 1.45), ('Row_InvertY', 'bInvertY', None),
              ('Row_Subtitles', 'bSubtitles', None), ('Row_SubtitleSize', 'SubtitleSize', None),
              ('Row_ReduceMotion', 'bReduceMotion', None))
S = dict(start=time.monotonic(), phase=0, log=[], handle=None, settings=None, original=None,
         screen=None, host=None, done=False, cleaned=False, mutated=[], layout_issues=[])


def same(a, b):
    return abs(float(a) - float(b)) < 0.0001 if isinstance(a, (float, int)) else a == b


def rect(widget):
    geometry = widget.get_paint_space_geometry()
    origin = unreal.SlateLibrary.local_to_absolute(geometry, unreal.Vector2D())
    size = unreal.SlateLibrary.get_absolute_size(geometry)
    return dict(x=origin.x, y=origin.y, w=size.x, h=size.y)


def painted_child(widget, name):
    child = widget.get_editor_property(name)
    if child and rect(child)['w'] > 0 and rect(child)['h'] > 0:
        return child
    # Nested widgets can retain a stale BindWidget member after an editor recompile.
    trees = [tree for tree in unreal.ObjectIterator(unreal.load_class(None, '/Script/UMG.WidgetTree'))
             if tree.get_outer() == widget]
    candidates = [found for tree in trees for found in [unreal.find_object(tree, name)] if found]
    painted = [found for found in candidates if rect(found)['w'] > 0 and rect(found)['h'] > 0]
    return painted[0] if len(painted) == 1 else child


def drive_row(name,field,value):
    row=S['screen'].get_editor_property(name)
    if field.startswith('b') or field=='SubtitleSize':
        target=int(value)
        row.call_method('Step',(target-row.get_editor_property('Index'),))
    else:row.call_method('HandleSliderChanged',(float(value),))


def next_page(elapsed):
    if S['page'] < 4:
        S['phase'], S['ready'] = 3, elapsed + 0.2
    else:
        S['phase'], S['ready'] = 6, elapsed + 1.0


def restore():
    if S['original'] is None:return
    for name,field in S['mutated']:drive_row(name,field,S['original'][field])
    persisted=unreal.GameplayStatics.load_game_from_slot('Settings',0)
    for field,value in S['original'].items():
        assert same(S['settings'].get_editor_property(field),value),('Restore live',field,value)
        assert persisted and same(persisted.get_editor_property(field),value),('Restore persisted',field,value)


def finish(result, error=None):
    if S['done']:
        return
    S['done'] = True
    unreal.unregister_slate_post_tick_callback(S['handle'])
    restore_error = None
    try:
        restore()
        if S.get('ui_fixture_active'):
            hud = S['host'].get_editor_property('HUD')
            if hud.get_editor_property('bToolStatus'):
                hud.call_method('HideToolStatus')
            hud.call_method('ClearNarration')
        if S['host'] and not S['cleaned']:
            S['host'].call_method('CloseOverlay')
            S['host'].call_method('Resume')
    except Exception as exc:
        restore_error = repr(exc)
        result = 'FAIL'
    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump(dict(result=result, error=error, restore_error=restore_error, log=S['log']), f, indent=2)
    print('SETTINGS RUNTIME', result, error or '', restore_error or '', OUT)


def tick(_dt):
    try:
        world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
        assert world, 'PIE ended before settings proof completed'
        elapsed = time.monotonic() - S['start']
        if elapsed > 15:
            return finish('FAIL', '15 second cap')
        if S['phase'] == 0:
            host = unreal.GameplayStatics.get_actor_of_class(world, unreal.load_class(None, FE))
            pawn = unreal.GameplayStatics.get_player_character(world, 0)
            assert host and pawn and not pawn.get_editor_property('bCinematic'), 'Run from free roam'
            assert not unreal.GameplayStatics.is_game_paused(world), 'Run from free roam, not Pause'
            S['host'] = host
            host.call_method('TogglePause')
            host.call_method('OpenSettings')
            S['log'].append(dict(label='open_requested',settings_class=str(host.get_editor_property('SettingsClass')),
                paused=unreal.GameplayStatics.is_game_paused(world),overlay=str(host.get_editor_property('Overlay'))))
            S['phase'] = 1
            S['ready'] = elapsed + 0.3
        elif S['phase'] == 1 and elapsed > S['ready']:
            screen = S['host'].get_editor_property('Overlay')
            assert screen and screen.get_class().get_name() == 'WBP_Settings_C',('Settings overlay did not open',
                str(S['host'].get_editor_property('SettingsClass')),str(screen),unreal.GameplayStatics.is_game_paused(world))
            S['screen'] = screen
            S['settings'] = screen.get_editor_property('Settings')
            S['original'] = {field: S['settings'].get_editor_property(field) for field in SG_FIELDS}
            for name,label in (('Btn_TabGraphics','Graphics'),('Btn_TabAudio','Audio'),
                               ('Btn_TabControls','Controls'),('Btn_TabAccess','Accessibility'),('Btn_Back','Back')):
                button=screen.get_editor_property(name)
                assert str(button.get_editor_property('Txt_Label').get_text())==label,(name,'Runtime button label',str(button.get_editor_property('Txt_Label').get_text()))
            if LAYOUT_ONLY:
                # Layout verification must not reapply graphics settings or override the editor's FPS cap.
                S['original'] = None
                S['phase'], S['page'], S['ready'] = 3, 0, elapsed
                return
            # Delta zero exercises the actual delegate without selecting a different display mode. A custom
            # engine preset outside the offered list stays untouched and is recorded as untested.
            gus = screen.get_editor_property('GUS')
            resolution = gus.get_screen_resolution()
            modes = ((1280, 720), (1600, 900), (1920, 1080), (2560, 1440),
                     (3840, 2160), (2560, 1080), (3440, 1440))
            caps = (30.0, 60.0, 120.0, 0.0)
            cap = gus.get_frame_rate_limit()
            current = dict(Row_Quality=gus.get_overall_scalability_level(),
                           Row_WindowMode=int(gus.get_fullscreen_mode().value),
                           Row_VSync=int(gus.is_v_sync_enabled()),
                           Row_FrameCap=caps.index(cap) if cap in caps else None,
                           Row_Resolution=modes.index((resolution.x, resolution.y))
                           if (resolution.x, resolution.y) in modes else None)
            for name in ('Row_Quality', 'Row_WindowMode', 'Row_VSync', 'Row_FrameCap', 'Row_Resolution'):
                row = screen.get_editor_property(name)
                if current[name] is None or current[name] < 0:
                    S['log'].append(dict(row=name, result='custom current value preserved; setter untested'))
                    continue
                assert row.get_editor_property('Index') == current[name], (name, current[name])
                row.call_method('Step', (0,))
                S['log'].append(dict(row=name, result='delegate applied current selection'))
            row = screen.get_editor_property('Row_ResScale')
            raw_scale=gus.get_resolution_scale_information_ex()[1]
            if raw_scale>0 and same(row.get_editor_property('Value'),raw_scale):
                row.call_method('HandleSliderChanged',(raw_scale,))
                S['log'].append(dict(row='Row_ResScale',result='delegate applied exact current percent'))
            else:S['log'].append(dict(row='Row_ResScale',result='custom/default raw scale preserved; setter untested',raw=raw_scale))
            # Verify the exact same restoration callbacks before changing a single saved preference.
            for name,field,_ in SAVED_ROWS:
                value=S['original'][field]
                if field=='SubtitleSize' and int(value) not in (0,1,2):continue
                drive_row(name,field,value)
                current=S['settings'].get_editor_property(field)
                persisted=unreal.GameplayStatics.load_game_from_slot('Settings',0).get_editor_property(field)
                assert same(current,value) and same(persisted,value),('Restore preflight',field,current,persisted,value)
            S['log'].append(dict(result='same-original row callbacks and persistence verified before mutation'))
            S['phase'] = 2
        elif S['phase'] == 2:
            for name, field, value in SAVED_ROWS:
                if field=='SubtitleSize' and int(S['original'][field]) not in (0,1,2):
                    S['log'].append(dict(row=name,result='custom saved index preserved; setter untested'));continue
                row = S['screen'].get_editor_property(name)
                S['mutated'].append((name,field))
                if value is None:
                    row.call_method('Step', (1,))
                    index = row.get_editor_property('Index')
                    value = index == 1 if field.startswith('b') else index
                else:
                    row.call_method('HandleSliderChanged', (value,))
                current = S['settings'].get_editor_property(field)
                persisted = unreal.GameplayStatics.load_game_from_slot('Settings', 0).get_editor_property(field)
                assert same(current, value) and same(persisted, value), (name, current, persisted, value)
                S['log'].append(dict(row=name, field=field, value=value, persisted=persisted))
            player = unreal.GameplayStatics.get_player_character(world, 0)
            look = player.get_editor_property('LookScale')
            assert abs(abs(look.x) - 1.45) < 0.0001 and abs(abs(look.y) - 1.45) < 0.0001
            assert (look.y < 0) == S['settings'].get_editor_property('bInvertY')
            hud = S['host'].get_editor_property('HUD')
            assert hud.get_editor_property('bSubtitlesEnabled') == S['settings'].get_editor_property('bSubtitles')
            S['phase'] = 3
            S['page'] = 0
            S['ready'] = elapsed
        elif S['phase'] == 3 and elapsed > S['ready']:
            if NATIVE_LAYOUT:
                os.makedirs(CAPTURE_DIR, exist_ok=True)
                with open(OUT, 'w', encoding='utf-8') as f:
                    json.dump(dict(status='running', action='click_page', page=S['page'],
                        match=('Graphics', 'Audio', 'Controls', 'Accessibility')[S['page']], ack=ACK), f)
                S['phase'] = 13
            else:
                S['screen'].call_method('ShowPage', (S['page'],))
                S['page'] += 1
                S['phase'], S['ready'] = 4, elapsed + 0.2
        elif S['phase'] == 13 and os.path.isfile(ACK):
            with open(ACK, encoding='utf-8') as f:
                if f.read().strip() == 'clicked:' + str(S['page']):
                    actual_page = S['screen'].get_editor_property('Switch_Pages').get_active_widget_index()
                    assert actual_page == S['page'], ('Native click did not select requested page', S['page'], actual_page)
                    S['page'] += 1
                    S['phase'], S['ready'] = 4, elapsed + 0.2
        elif S['phase'] == 4 and elapsed > S['ready']:
            folder=CAPTURE_DIR;os.makedirs(folder,exist_ok=True)
            if NATIVE_LAYOUT:
                tab_alphas = {}
                for index, name in enumerate(('Btn_TabGraphics', 'Btn_TabAudio', 'Btn_TabControls', 'Btn_TabAccess')):
                    button = S['screen'].get_editor_property(name)
                    assert button.get_editor_property('bPlainLabel'), (name, 'Expected readable navigation text')
                    expected_alpha = 1.0 if index == S['page'] - 1 else 0.62
                    assert same(button.get_editor_property('TextAlphaRest'), expected_alpha), (name, 'Persistent selected tab')
                    button.call_method('SetHovered', (False,))
                    assert same(button.get_editor_property('Txt_Label').get_render_opacity(), expected_alpha), (name, 'Hover exit lost current-page cue')
                    tab_alphas[name] = expected_alpha
                S['log'].append(dict(page=S['page']-1, result='Native click and persistent selection verified', tab_opacity=tab_alphas))
            pages = (('Row_Quality', 'Row_WindowMode', 'Row_VSync', 'Row_FrameCap', 'Row_ResScale', 'Row_Resolution'),
                     ('Row_Master', 'Row_Effects', 'Row_Ambience', 'Row_Interface'),
                     ('Row_Sensitivity', 'Row_InvertY'),
                     ('Row_Subtitles', 'Row_SubtitleSize', 'Row_ReduceMotion'))
            bounds, expected = {}, []
            for name in pages[S['page'] - 1]:
                row = S['screen'].get_editor_property(name) if NATIVE_LAYOUT else painted_child(S['screen'], name)
                expected.append(dict(row=name,
                    label=str(row.get_editor_property('Txt_Label').get_text()),
                    value=str(row.get_editor_property('Txt_Value').get_text())))
                if NATIVE_LAYOUT:
                    continue
                label, value = (rect(painted_child(row, n)) for n in ('Txt_Label', 'Txt_Value'))
                if not (label['w'] > 0 and value['w'] > 0 and label['h'] > 0 and value['h'] > 0):
                    S['layout_issues'].append(('Unpainted row geometry', name, label, value))
                elif label['x'] + label['w'] > value['x'] - 8:
                    S['layout_issues'].append(('Setting label overlaps value', name, label, value))
                bounds[name] = dict(label=label, value=value)
            pc=unreal.GameplayStatics.get_player_controller(world,0)
            actual=tuple(pc.get_viewport_size())
            filename=f'{folder}/page_{S["page"]-1}_{actual[0]}x{actual[1]}.png'
            unreal.SystemLibrary.execute_console_command(world,f'Shot showui filename={filename} -nosuffix',pc)
            S['log'].append(dict(page=S['page'] - 1, result='capture requested',actual=actual,filename=filename,bounds=bounds))
            if NATIVE_LAYOUT:
                with open(OUT, 'w', encoding='utf-8') as f:
                    json.dump(dict(status='running', action='snapshot', page=S['page']-1, expected=expected, actual=actual,
                                   ack=ACK, log=S['log']), f)
                S['phase'] = 12
            else:
                next_page(elapsed)
        elif S['phase'] == 12:
            if os.path.isfile(ACK):
                with open(ACK, encoding='utf-8') as f:
                    if f.read().strip() == 'captured:' + str(S['page'] - 1):
                        next_page(elapsed)
        elif S['phase']==6 and elapsed>S['ready']:
            restore()
            S['original'] = None
            S['host'].call_method('CloseOverlay')
            assert unreal.GameplayStatics.is_game_paused(world), 'Settings Back bypassed Pause'
            S['host'].call_method('Resume')
            S['cleaned'] = True
            S['phase'] = 7 if LAYOUT_ONLY and not NATIVE_LAYOUT else 5
            S['ready'] = elapsed + 0.2
        elif S['phase'] == 7 and elapsed > S['ready']:
            hud = S['host'].get_editor_property('HUD')
            S['ui_fixture_active'] = True
            hud.call_method('HandleNarration', ('The shoes settle into place. Take a breath, then collect the key.',))
            S['phase'], S['ready'] = 8, elapsed + 0.5
        elif S['phase'] == 8 and elapsed > S['ready']:
            hud = S['host'].get_editor_property('HUD')
            plate = hud.get_editor_property('Brd_Narration')
            assert plate.is_visible() == hud.get_editor_property('bSubtitlesEnabled')
            pc = unreal.GameplayStatics.get_player_controller(world, 0)
            unreal.SystemLibrary.execute_console_command(world,
                f'Shot showui filename={CAPTURE_DIR}/hud_narration.png -nosuffix', pc)
            S['phase'], S['ready'] = 9, elapsed + 0.3
        elif S['phase'] == 9 and elapsed > S['ready']:
            hud = S['host'].get_editor_property('HUD')
            hud.call_method('ShowToolStatus', ('Turn the key.\nD Turn clockwise   A Reverse   Q Cancel',))
            hud.call_method('HandleNarration', ('This must not cover the key instructions.',))
            assert not hud.get_editor_property('Brd_Narration').is_visible()
            assert not str(hud.get_editor_property('Txt_Narration').get_text())
            S['phase'], S['ready'] = 10, elapsed + 0.5
        elif S['phase'] == 10 and elapsed > S['ready']:
            pc = unreal.GameplayStatics.get_player_controller(world, 0)
            unreal.SystemLibrary.execute_console_command(world,
                f'Shot showui filename={CAPTURE_DIR}/hud_tool_instructions.png -nosuffix', pc)
            S['phase'], S['ready'] = 11, elapsed + 0.3
        elif S['phase'] == 11 and elapsed > S['ready']:
            hud = S['host'].get_editor_property('HUD')
            hud.call_method('HideToolStatus')
            hud.call_method('ClearNarration')
            S['ui_fixture_active'] = False
            S['log'].append(dict(result='Narration backplate and exclusive tool instructions verified'))
            S['phase'], S['ready'] = 5, elapsed + 0.2
        elif S['phase'] == 5 and elapsed > S['ready']:
            pc = unreal.GameplayStatics.get_player_controller(world, 0)
            assert not unreal.GameplayStatics.is_game_paused(world) and not pc.is_move_input_ignored()
            assert not pc.show_mouse_cursor
            assert not S['layout_issues'], S['layout_issues']
            finish('PASS')
    except Exception as exc:
        finish('FAIL', repr(exc))


S['handle'] = unreal.register_slate_post_tick_callback(tick)
print('SETTINGS runtime proof scheduled; 15 second cap, coordinator owns PIE lifecycle')
