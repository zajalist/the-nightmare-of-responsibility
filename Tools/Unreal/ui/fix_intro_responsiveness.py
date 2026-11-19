"""Apply the narrow v3 intro fixes through Hayba; safe to rerun after the UI builders."""
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import editor_lock
import hayba_call as hc

FE = '/Game/FoA/UI/Framework/BP_FoAFrontEnd'
TITLE = '/Game/FoA/UI/Widgets/Menus/WBP_Title'
KML = '/Script/Engine.KismetMathLibrary:'
GS = '/Script/Engine.GameplayStatics:'
FC = FE + '.BP_FoAFrontEnd_C:'
OUT = Path('P:/FoA/Saved/UIShots/fix_r8')


def call(command, **params):
    r = hc.call(command, params)
    assert r.get('ok'), r
    d = r.get('data', {})
    assert d.get('ok', True), d
    return d


def graph(path, name):
    return call('blueprint_inspect_graph', path=path, graph_name=name)


def node(g, title):
    found = [n['node_id'] for n in g['nodes'] if n['title'] == title]
    assert len(found) == 1, (title, found)
    return found[0]


def patch(path, name, ops):
    if ops:
        r = call('blueprint_graph_batch', path=path, graph_name=name, ops=ops,
                 compile=True, save=True)
        assert r.get('applied') == len(ops), r
        print(name, 'applied', len(ops), 'operations', r.get('compile'), flush=True)


def add(ref, kind='call_function', **kw):
    return dict(op='add_node', ref=ref, node_type=kind, **kw)


def link(a, b, ap='then', bp='execute'):
    return dict(op='connect', from_node=a, from_pin=ap, to_node=b, to_pin=bp)


def pin_value(path, name, title, pin, value):
    g = graph(path, name)
    n = next(n for n in g['nodes'] if n['title'] == title)
    current = next(p.get('default_value') for p in n['pins'] if p['name'] == pin)
    if float(current) != float(value):
        patch(path, name, [dict(op='set_pin', node_id=n['node_id'], pin_name=pin, value=str(value))])


def run():
    os.environ['HAYBA_AGENT_ID'] = os.environ['FOA_AGENT'] = 'ui'
    assert not call('editor_get_state').get('pie_running'), 'User PIE is protected'
    editor_lock.acquire('ui', wait_s=60, ttl=90, areas=['UI'])
    try:
        pin_value(FE, 'WakeUp', 'Set Timer by Function Name', 'Time', .15)
        pin_value(FE, 'CutToBlack', 'StartCameraFade', 'Duration', .01)

        g = graph(TITLE, 'TryConfirm')
        if any(n['title'] == 'Branch' for n in g['nodes']):
            patch(TITLE, 'TryConfirm', [
                dict(op='remove', node_ids=[node(g, 'Branch'), node(g, 'Get bReady')]),
                link(node(g, 'TryConfirm'), node(g, 'OnTitleConfirmed'))])

        g = graph(FE, 'HandleBack')
        if not any(n['title'] == 'ShowScreen' for n in g['nodes']):
            paused = node(g, 'IsGamePaused')
            paused_branch = next(e['to_node'] for e in g['edges'] if e['from_node'] == paused)
            ops = [
                add('screen', 'variable_get', variable_name='Screen', x=1000, y=440),
                add('class', function_name=GS+'GetObjectClass', x=1220, y=440),
                add('menu', 'variable_get', variable_name='MainMenuClass', x=1220, y=580),
                add('same', function_name=KML+'EqualEqual_ClassClass', x=1450, y=440),
                add('waking', 'variable_get', variable_name='bWaking', x=1220, y=710),
                add('notwaking', function_name=KML+'Not_PreBool', x=1450, y=710),
                add('both', function_name=KML+'BooleanAND', x=1690, y=440),
                add('guard', 'branch', x=1920, y=240),
                add('title', 'variable_get', variable_name='TitleClass', x=2100, y=440),
                add('show', function_name=FC+'ShowScreen', x=2200, y=240),
                link('screen', 'class', 'Screen', 'Object'),
                link('class', 'same', 'ReturnValue', 'A'),
                link('menu', 'same', 'MainMenuClass', 'B'),
                link('waking', 'notwaking', 'bWaking', 'A'),
                link('same', 'both', 'ReturnValue', 'A'),
                link('notwaking', 'both', 'ReturnValue', 'B'),
                link('both', 'guard', 'ReturnValue', 'Condition'),
                link(paused_branch, 'guard', 'else'), link('guard', 'show'),
                link('title', 'show', 'TitleClass', 'ScreenClass'),
                dict(op='comment', title='Back to title',
                     node_ids=['screen', 'class', 'menu', 'same', 'waking', 'notwaking', 'both', 'guard', 'title', 'show']),
                dict(op='fit_comments')]
            patch(FE, 'HandleBack', ops)

        g = graph(FE, 'CloseOverlay')
        if not any(n['title'] == 'Set Overlay' for n in g['nodes']):
            entry, remove, branch = node(g, 'CloseOverlay'), node(g, 'RemoveFromParent'), node(g, 'Branch')
            patch(FE, 'CloseOverlay', [
                add('valid', function_name='/Script/Engine.KismetSystemLibrary:IsValid', x=224, y=256),
                add('guard', 'branch', x=160, y=-96),
                add('clear', 'variable_set', variable_name='Overlay', x=480, y=0),
                dict(op='disconnect', node_id=entry, pin_name='then'),
                dict(op='disconnect', node_id=remove, pin_name='then'),
                link(node(g, 'Get Overlay'), 'valid', 'Overlay', 'Object'),
                link('valid', 'guard', 'ReturnValue', 'Condition'),
                link(entry, 'guard'), link('guard', remove), link('guard', branch, 'else'),
                link(remove, 'clear'), link('clear', branch), dict(op='fit_comments')])

        textures = []
        for name in ('Unreal', 'Aholo', 'Hayba'):
            path = '/Game/FoA/UI/Textures/T_UI_Logo_' + name
            before = call('texture_get_info', path=path)
            if max(before['width'], before['height']) > 512:
                call('texture_set_settings', path=path, properties={'max_texture_size': 512})
            after = call('texture_get_info', path=path)
            assert max(after['width'], after['height']) <= 512, after
            textures.append(dict(path=path, before=before, after=after))
        call('asset_save', asset_paths=[t['path'] for t in textures])
        OUT.mkdir(exist_ok=True)
        if not (OUT/'texture_sizes.json').exists():
            (OUT/'texture_sizes.json').write_text(json.dumps(textures, indent=2))
        result = {n: graph(p, n) for p,n in [(FE,'WakeUp'), (FE,'HandleBack'), (FE,'CloseOverlay'), (TITLE,'TryConfirm')]}
        assert not any(n['title']=='Branch' for n in result['TryConfirm']['nodes'])
        assert any(n['title']=='ShowScreen' for n in result['HandleBack']['nodes'])
        assert any(n['title']=='Set Overlay' for n in result['CloseOverlay']['nodes'])
        timer = next(n for n in result['WakeUp']['nodes'] if n['title']=='Set Timer by Function Name')
        assert float(next(p['default_value'] for p in timer['pins'] if p['name']=='Time')) == .15
        (OUT/'after_graphs.json').write_text(json.dumps(result, indent=2))
        print('Graph assertions passed; PIE proof remains required.')
    finally:
        editor_lock.release('ui')


if __name__ == '__main__':
    run()
