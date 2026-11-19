"""Bounded real battle UI proof. Coordinator owns PIE, native clicks and Slate snapshots."""
import json
import os
from pathlib import Path
import time
import unreal

OUT = Path('P:/FoA/Saved/EncounterCaptures/battle_feedback_runtime.json')
CAPTURE = Path(os.environ['FOA_BATTLE_UI_OUT'])
CAPTURE.mkdir(parents=True, exist_ok=True)
ACK = CAPTURE / 'ack.txt'
S = dict(start=time.monotonic(), phase=0, ready=0, done=False, log=[], handle=None)
COMMANDS = ('Btn_Act0','Btn_Act1','Btn_Act2','Btn_Breathe','Btn_Mirror','Btn_Items','Btn_Flee','Btn_NextTarget')


def request(label, action='snapshot', **extra):
    OUT.write_text(json.dumps(dict(status='running', label=label, action=action, ack=str(ACK), **extra)))


def ack(label):
    return ACK.exists() and ACK.read_text().strip() == label


def label(widget, name):
    return str(widget.get_editor_property(name).get_editor_property('Txt_Label').get_text())


def focused(world, widget):
    pc = unreal.GameplayStatics.get_player_controller(world, 0)
    return [n for n in COMMANDS if widget.get_editor_property(n).has_keyboard_focus()
            or widget.get_editor_property(n).has_user_focused_descendants(pc)]


def capture(world, widget, name, extra_text=()):
    commands = [label(widget, n) for n in COMMANDS if widget.get_editor_property(n).is_visible()
                and widget.get_editor_property(n).get_parent().is_visible()] \
        if widget.get_editor_property('CommandPanel').is_visible() else []
    footer = str(widget.get_editor_property('Txt_BattleHelp').get_text())
    details = []
    if widget.get_editor_property('CommandPanel').is_visible():
        for i in range(3):
            detail = widget.get_editor_property('Txt_Act'+str(i)+'Detail')
            if detail.get_parent().is_visible():
                value = str(detail.get_text())
                assert value, 'Visible action card has no effect description'
                details.append(value)
        details += [str(widget.get_editor_property('Txt_'+name+'Detail').get_text()) for name in ('Breathe','Mirror')]
        details.append('Switch freely. No turn spent.')
    progress = [str(widget.get_editor_property('Txt_Progress'+str(i)).get_text()) for i in range(5)]
    pc = unreal.GameplayStatics.get_player_controller(world, 0)
    filename = str(CAPTURE / (name + '.png'))
    unreal.SystemLibrary.execute_console_command(world, f'Shot showui filename={filename} -nosuffix', pc)
    S['log'].append(dict(label=name, footer=footer, commands=commands, filename=filename))
    request(name, commands=commands, expected_text=[footer, *details, *progress, *extra_text])


def finish(result, error=None):
    if S['done']:
        return
    S['done'] = True
    unreal.unregister_slate_post_tick_callback(S['handle'])
    OUT.write_text(json.dumps(dict(result=result, error=error, log=S['log']), indent=2))
    print('Battle feedback', result, error or '', str(OUT))


def tick(_dt):
    try:
        t = time.monotonic() - S['start']
        if t > 28:
            return finish('FAIL', '28 second battle UI cap')
        world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
        assert world, 'PIE ended'
        enc = unreal.GameplayStatics.get_actor_of_class(world, unreal.load_class(None,
            '/Game/FoA/Gameplay/Encounter/BP_Encounter.BP_Encounter_C'))
        assert enc and enc.get_editor_property('bActive')
        widget = enc.get_editor_property('Widget')
        state = str(enc.get_editor_property('BattleState'))
        if state != S.get('last_state'):
            S['last_state'] = state
            S['log'].append(dict(state=state, t=round(t, 2)))
        if not widget:
            return
        if S['phase'] == 0:
            S['enc'], S['widget'] = enc, widget
            S['phase'] = 2
        elif S['phase'] == 1 and ack('intro'):
            S['phase'] = 2
        elif S['phase'] == 2 and enc.get_editor_property('bPlayerTurn'):
            assert str(widget.get_editor_property('Txt_BattleHelp').get_text()) == 'Your move'
            capture(world, widget, 'commands')
            S['phase'] = 3
        elif S['phase'] == 3 and ack('commands'):
            assert not widget.get_editor_property('Btn_Items').is_visible()
            assert not widget.get_editor_property('Btn_Flee').is_visible()
            assert all(widget.get_editor_property('Txt_Progress'+str(i)).get_parent().is_visible() for i in range(5))
            S['focus_before'] = focused(world, widget)
            request('keyboard_right', 'key', key='Right')
            S['phase'] = 4
        elif S['phase'] == 4 and ack('keyboard_right'):
            S['ready'], S['phase'] = t + 0.25, 5
        elif S['phase'] == 5 and t > S['ready']:
            focus = focused(world, widget)
            assert focus and focus != S['focus_before'], ('Keyboard focus did not move', S['focus_before'], focus)
            assert 'Btn_Items' not in focus and 'Btn_Flee' not in focus
            S['log'].append(dict(result='Keyboard focus moved between visible commands', before=S['focus_before'], after=focus))
            capture(world, widget, 'keyboard_focus')
            S['phase'] = 6
        elif S['phase'] == 6 and ack('keyboard_focus'):
            S['original_resolve'], S['original_free'] = enc.get_editor_property('Resolve'), enc.get_editor_property('bFreePreview')
            S['cost'] = int(enc.call_method('MoveCost', (enc.get_editor_property('MirrorMove'),)))
            assert S['cost'] == (0 if S['original_free'] else 5)
            assert ('Resolve' not in label(widget, 'Btn_Mirror')) if S['cost'] == 0 else ('5 Resolve' in label(widget, 'Btn_Mirror'))
            assert widget.get_editor_property('Btn_Mirror').get_is_enabled()
            S['log'].append(dict(result='Observed real Mirror cost before click', free_preview=S['original_free'], cost=S['cost']))
            S['nav'] = 1
            request('mirror_tab_1', 'key', key='Tab')
            S['phase'] = 20
        elif S['phase'] == 20 and ack('mirror_tab_'+str(S['nav'])):
            current = focused(world, widget)
            if current == ['Btn_Mirror']:
                S['log'].append(dict(result='Keyboard reached Mirror before activation', focus=current))
                request('enter_mirror', 'key', key='Enter')
                S['phase'] = 11
            else:
                S['nav'] += 1
                assert S['nav'] <= 3, ('Tab navigation did not reach Mirror', current)
                request('mirror_tab_'+str(S['nav']), 'key', key='Tab')
        elif S['phase'] == 11 and ack('enter_mirror') and state == 'EnemyPhase':
            assert not enc.get_editor_property('bFreePreview'), 'Free preview was not consumed by the real move'
            assert not widget.get_editor_property('CommandPanel').is_visible()
            assert "Clothes' turn" in str(widget.get_editor_property('Txt_BattleHelp').get_text())
            capture(world, widget, 'enemy_turn')
            S['phase'] = 12
        elif S['phase'] == 12 and ack('enemy_turn'):
            S['phase'] = 13
        elif S['phase'] == 13 and enc.get_editor_property('bPlayerTurn'):
            assert not enc.get_editor_property('bFreePreview')
            assert '5 Resolve' in label(widget, 'Btn_Mirror')
            assert enc.get_editor_property('Resolve') == S['original_resolve'] - S['cost'], 'Mirror spent the wrong Resolve cost'
            assert str(widget.get_editor_property('Txt_BattleHelp').get_text()) == 'Your move'
            S['log'].append(dict(result='Real Mirror used its displayed cost and returned to paid command', initial_free_preview=S['original_free'], spent=S['cost']))
            capture(world, widget, 'after_mirror')
            S['phase'] = 14
        elif S['phase'] == 14 and ack('after_mirror'):
            finish('PASS')
    except Exception as exc:
        finish('FAIL', repr(exc))


S['handle'] = unreal.register_slate_post_tick_callback(tick)
print('Battle UI proof registered; actual clicks supplied by coordinator, 28 second cap')
