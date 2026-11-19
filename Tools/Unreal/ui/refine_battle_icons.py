"""Battle icon assets and in-place card readability. prepare/selftest are offline; apply refuses PIE."""
import concurrent.futures
import hashlib
import html
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import urllib.request
sys.path.insert(0,str(Path(__file__).parents[1]/'level2'))
from cv_data import MOVE_ICONS as CV_MOVES

SOURCE = Path('P:/FoA-Assets/game-icons/battle-20261111')
STAGE = Path(os.environ['TEMP']) / 'hayba-asset-connectors/foa/battle_game_icons'
DEST = '/Game/FoA/Gameplay/Encounter/Icons'
ICONS = {
    'Shirt': 'delapouite/polo-shirt', 'Button': 'delapouite/shirt-button',
    'Socks': 'delapouite/socks', 'Foot': 'lorc/footprint', 'Knot': 'delapouite/knot',
    'Trousers': 'lorc/trousers', 'Grip': 'delapouite/hand-grip', 'Tie': 'delapouite/tie',
    'Breathe': 'delapouite/lungs', 'Mirror': 'lorc/mirror-mirror',
    'Composure': 'lorc/brain', 'Resolve': 'lorc/fist', 'Target': 'delapouite/eye-target',
}
MOVES = dict(FindArmhole='Shirt', ButtonUp='Button', MatchPair='Socks', PullOn='Foot',
             UntwistLeg='Knot', StepIn='Trousers', Loosen='Grip', TieKnot='Tie')
CREDIT = 'Battle icons by Lorc and Delapouite, game-icons.net.\nCC BY 3.0. Used in monochrome.\nhttps://creativecommons.org/licenses/by/3.0/'


def asset(name):
    return f'{DEST}/T_BattleGame_{name}.T_BattleGame_{name}'


def prepare():
    SOURCE.mkdir(parents=True, exist_ok=True); STAGE.mkdir(parents=True, exist_ok=True)
    def download(item):
        name, source = item
        url = f'https://game-icons.net/icons/ffffff/transparent/1x1/{source}.png'
        path = SOURCE / f'T_BattleGame_{name}.png'
        if not path.exists():
            request = urllib.request.Request(url, headers={'User-Agent': 'FoA asset preparation'})
            with urllib.request.urlopen(request, timeout=30) as response:
                path.write_bytes(response.read())
        data = path.read_bytes()
        assert data[:8] == b'\x89PNG\r\n\x1a\n', path
        width, height = struct.unpack('>II', data[16:24]); assert width == height and width >= 128
        # Hayba's importer accepts 8-bit RGBA, not the site's palette/1-bit PNG encoding.
        subprocess.run(['ffmpeg','-y','-v','error','-i',str(path),'-vf','format=rgba',
                        '-frames:v','1',str(STAGE / path.name)],check=True)
        assert (STAGE / path.name).read_bytes()[24:26] == bytes((8,6))
        return dict(name=name, source=url, author=source.split('/')[0],
                    page=f'https://game-icons.net/1x1/{source}.html',
                    license='https://creativecommons.org/licenses/by/3.0/',
                    sha256=hashlib.sha256(data).hexdigest(), dimensions=[width, height])
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        records = list(pool.map(download, ICONS.items()))
    (SOURCE / 'SOURCES.json').write_text(json.dumps(records, indent=2))
    (SOURCE / 'SOURCES.txt').write_text(CREDIT + '\n\n' + '\n'.join(
        f"{r['name']}: {r['page']}\nDownload: {r['source']}\nAuthor: {r['author']}\nLicense: {r['license']}"
        for r in records))
    print(f'{len(records)} credited, transparent icons staged at {STAGE}')


def selftest():
    sys.path.insert(0, 'P:/FoA/Tools/Unreal/encounter')
    from encounter_data import OPPONENTS
    required = {move for opponent in OPPONENTS.values() for move in opponent['ActMoves']}
    assert set(MOVES) == required, (required - set(MOVES), set(MOVES) - required)
    assert set(MOVES.values()) <= ICONS.keys()
    assert len(set(MOVES.values())) == len(MOVES), 'Actions must have distinct silhouettes'
    assert len(CV_MOVES)==len(set(CV_MOVES.values()))==6
    assert set(CV_MOVES.values())<=ICONS.keys()
    for width in (1728, 1920):
        assert 5 * (202 + 12) < width * .9, 'Three actions and two recovery cards must fit'
    assert 1080 - 88 - 252 - 24 > 1080 - 400, 'Lifted cards overlap the effect description'
    print('PASS: all eight garment moves have distinct icons; cards and description fit')


def preview():
    """Offline composition only; the in-engine proof remains a separate required check."""
    folder = Path('P:/FoA/Saved/UIShots/battle_refinement'); folder.mkdir(parents=True, exist_ok=True)
    font = Path('P:/FoA-Assets/fonts/DarkerGrotesque/DarkerGrotesque-SemiBold.ttf').as_uri()
    scene = Path('P:/FoA/Saved/PresentationReview/battle_PlayerCommand.png').as_uri()
    def icon(name): return (SOURCE / f'T_BattleGame_{name}.png').as_uri()
    cards = ''.join(f'<button class="card {"selected" if i == 0 else ""}"><img src="{icon(img)}" alt=""><span>{label}</span></button>'
                    for i, (img, label) in enumerate((('Shirt','Find Armhole'), ('Button','Button Up<br>(10 Resolve)'),
                                                      ('Breathe','Deep Breath'), ('Mirror','Check Mirror<br>(5 Resolve)'))))
    content = f'''<!doctype html><html><meta charset="utf-8"><title>Battle UI preview</title><style>
    @font-face{{font-family:Game;src:url('{font}')}}*{{box-sizing:border-box}}html,body{{margin:0;width:100vw;height:100vh;overflow:hidden;background:#080808;color:#f1f1ef;font-family:Game}}
    .scene{{position:absolute;inset:0;background:url('{scene}') center/cover;filter:grayscale(1)}}
    .shade{{position:absolute;inset:0;background:linear-gradient(#080808 0%,#080808 22%,transparent 36%,rgba(8,8,8,.1) 49%,#080808 60%)}}
    .stats{{position:absolute;left:48px;top:40px;width:330px}}.stat{{display:grid;grid-template-columns:28px 1fr auto;align-items:center;gap:12px;font-size:28px;margin-bottom:8px}}.stat img{{width:28px;height:28px}}.bar{{height:7px;background:#292929;margin:0 0 20px}}.bar div{{height:100%;background:#e6e6e2}}
    .turn{{position:absolute;top:48px;left:50%;transform:translateX(-50%);font-size:36px}}.target{{position:absolute;right:56px;top:40px;text-align:right;font-size:32px}}.target p{{font-size:24px;margin:8px 0;color:#bdbdb9}}.target .change{{font-size:22px;display:flex;align-items:center;justify-content:end;gap:12px;margin-top:20px}}.target img{{width:28px;height:28px}}
    .detail{{position:absolute;left:50%;transform:translateX(-50%);bottom:400px;width:1040px;text-align:center;font-size:28px;line-height:1.2;color:#e2e2de}}
    .deck{{position:absolute;bottom:88px;left:50%;transform:translateX(-50%);display:flex;gap:12px;align-items:end}}
    .card{{position:relative;width:202px;height:252px;padding:0;border:0;background:#1b1b1a;color:#e7e7e3;font:28px/1 Game;cursor:pointer;box-shadow:0 12px 24px #0008;transition:transform .16s,background .16s}}
    .card img{{position:absolute;left:49px;top:38px;width:104px;height:104px;object-fit:contain}}
    .card span{{position:absolute;left:12px;right:12px;bottom:20px;min-height:56px;display:flex;flex-direction:column;justify-content:center}}
    .card.selected,.card:hover,.card:focus-visible{{transform:translateY(-24px);background:#30302d;color:#fff;outline:2px solid #d9d9d1;outline-offset:3px}}
    .help{{position:absolute;bottom:28px;left:48px;font-size:24px;color:#bdbdb9}}.preview{{position:absolute;bottom:28px;right:48px;font-size:22px;color:#9e9e9a}}
    </style><div class="scene"></div><div class="shade"></div>
    <div class="stats"><div class="stat"><img src="{icon('Composure')}" alt=""><span>Composure</span><strong>80</strong></div><div class="bar"><div style="width:80%"></div></div><div class="stat"><img src="{icon('Resolve')}" alt=""><span>Resolve</span><strong>30</strong></div><div class="bar"><div style="width:75%"></div></div></div>
    <div class="turn">Your move</div><div class="target">The Shirt (inside out)<p>Buttons 2 of 6</p><div class="change"><img src="{icon('Target')}" alt="">Change target</div></div>
    <div class="detail">Clear tangled sleeves.<br>Your next Button Up timing window is 1.75× wider.</div><div class="deck">{cards}</div>
    <div class="help">Arrows choose. Enter confirms. Every round costs 4 Composure.</div><div class="preview">Offline design preview</div></html>'''
    (folder / 'battle-preview.html').write_text(content, encoding='utf-8')
    rows = ''.join(f'<figure><img src="{icon(name)}"><figcaption>{html.escape(name)}</figcaption></figure>' for name in ICONS)
    (folder / 'icons.html').write_text(f'<html><style>body{{background:#151515;color:#eee;font:20px Arial;display:flex;flex-wrap:wrap;gap:24px}}figure{{margin:16px;width:150px;text-align:center}}img{{width:96px;height:96px;object-fit:contain}}figcaption{{margin-top:20px}}</style>{rows}</html>')
    print(folder / 'battle-preview.html')


def action_graph(b):
    name = 'RefreshBattleActionIcon'
    info = b.c('blueprint_get_info', path=b.WBP)
    if name not in info['functions']:
        b.c('blueprint_add_function', path=b.WBP, function_name=name,
            inputs=[dict(name='Index', type='int'), dict(name='Move', type='object:' + b.MOVE)])
    nodes, edges = b.graph(b.WBP, name)
    entry = next(n['node_id'] for n in nodes if n['title'].replace(' ', '') == name)
    old = [n['node_id'] for n in nodes if n['node_id'] != entry]
    batch = b.B(b.WBP, name)
    if old: batch.ops.append(dict(op='remove', node_ids=old))
    k = '/Script/Engine.KismetMathLibrary:'
    target = batch.get('TornGlyph_Act2')
    for i in (1, 0):
        matches = batch.fn(k + 'EqualEqual_IntInt', A=(entry, 'Index'), B=i)
        target = batch.fn(k + 'SelectObject', A=batch.get(f'TornGlyph_Act{i}'), B=target, bSelectA=matches)
    image = batch.node('cast', class_path='/Script/UMG.Image', pins={'Object': target})
    texture = asset('Grip')
    for folder,mapping in (('/Game/FoA/Gameplay/Encounter/Data',MOVES),('/Game/FoA/Level2/CV/Data',CV_MOVES)):
        for move, icon in mapping.items():
            matches = batch.fn(k + 'EqualEqual_ObjectObject', A=(entry, 'Move'),
                               B=f'{folder}/DA_Move_{move}.DA_Move_{move}')
            texture = batch.fn(k + 'SelectObject', A=asset(icon), B=texture, bSelectA=matches)
    cast = batch.node('cast', class_path='/Script/Engine.Texture2D', pins={'Object': texture})
    brush = batch.fn('/Script/UMG.Image:SetBrushFromTexture', self=(image, 'AsImage'),
                     Texture=(cast, 'AsTexture 2D'), bMatchSize=False)
    batch.chain(entry, image, cast, brush); batch.run()
    nodes, edges = b.graph(b.WBP, 'RefreshAct')
    if any(n['title'].replace(' ', '') == name for n in nodes): return
    entry = next(n['node_id'] for n in nodes if n['title'] == 'RefreshAct' and any(p['name'] == 'Index' for p in n['pins']))
    move = next(n['node_id'] for n in nodes if n['title'] == 'Get')
    source = next(n['node_id'] for n in nodes if n['title'] == 'SetIsEnabled')
    following = [e for e in edges if e['from_node'] == source and e['from_pin'] == 'then']
    assert len(following) == 1, following
    batch = b.B(b.WBP, 'RefreshAct')
    update = batch.fn(b.WBP + '.WBP_Encounter_C:' + name, Index=(entry, 'Index'), Move=(move, 'Item'))
    batch.ops.append(dict(op='disconnect', node_id=source, pin_name='then'))
    batch.chain(source, update); batch.link(update, 'then', following[0]['to_node'], following[0]['to_pin']); batch.run()


def restore_cost_labels(b):
    nodes, edges = b.graph(b.WBP, 'MoveLabel')
    fmt = next(n['node_id'] for n in nodes if n['title'] == 'Format Text')
    name = next(n['node_id'] for n in nodes if n['title'] == 'Get DisplayName')
    branch = next(n['node_id'] for n in nodes if n['title'] == 'Branch')
    paid = next(e['to_node'] for e in edges if e['from_node'] == branch and e['from_pin'] == 'then')
    free = next(e['to_node'] for e in edges if e['from_node'] == branch and e['from_pin'] == 'else')
    batch = b.B(b.WBP, 'MoveLabel')
    for node, source, pin in ((paid, fmt, 'Result'), (free, name, 'DisplayName')):
        batch.ops.append(dict(op='disconnect', node_id=node, pin_name='Label'))
        batch.link(source, pin, node, 'Label')
    batch.run()


def fixed_card_width(b):
    nodes, edges = b.graph(b.WBP, 'TornConfigure')
    if any(n['title'].replace(' ', '') == 'SetWidthOverride' for n in nodes): return
    old = next(n['node_id'] for n in nodes if n['title'].replace(' ', '') == 'SetMinDesiredWidth')
    size = next(e for e in edges if e['to_node'] == old and e['to_pin'] == 'self')
    tail = next(e for e in edges if e['from_node'] == old and e['from_pin'] == 'then')
    batch = b.B(b.WBP, 'TornConfigure')
    width = batch.fn('/Script/UMG.SizeBox:SetWidthOverride', self=(size['from_node'], size['from_pin']), InWidthOverride=202.)
    batch.ops.append(dict(op='disconnect', node_id=old, pin_name='then'))
    batch.chain(old, width); batch.link(width, 'then', tail['to_node'], tail['to_pin'])
    batch.run()


def stable_card_labels(b):
    nodes, edges = b.graph(b.WBP, 'TornConfigure')
    shifts = [n for n in nodes if n['title'].replace(' ', '') == 'SetRenderTranslation']
    if not shifts:return
    shift = shifts[0]['node_id']
    slot = next(n['node_id'] for n in nodes if n['title'].replace(' ', '') == 'SlotAsOverlaySlot')
    tail = next(e for e in edges if e['from_node'] == shift and e['from_pin'] == 'then')
    batch = b.B(b.WBP, 'TornConfigure')
    batch.ops.append(dict(op='set_pin',node_id=shift,pin_name='Translation',value='(X=0,Y=0)'))
    if any(n['title'].replace(' ', '') == 'SetPadding' for n in nodes):return
    pad = batch.fn('/Script/UMG.OverlaySlot:SetPadding',self=(slot,'ReturnValue'),InPadding='(Left=0,Top=140,Right=0,Bottom=0)')
    batch.ops.append(dict(op='disconnect',node_id=shift,pin_name='then'))
    batch.chain(shift,pad);batch.link(pad,'then',tail['to_node'],tail['to_pin']);batch.run()


def apply():
    import battle_torn_cards as b
    import hayba_call as h
    assert not b.c('editor_get_state')['pie_running'], 'Stop Play mode before applying battle UI'
    selftest()
    assert all((STAGE / f'T_BattleGame_{n}.png').is_file() for n in ICONS), 'Run prepare first'
    owner = 'battle-ui'; os.environ['HAYBA_AGENT_ID'] = owner
    credits = '/Game/FoA/UI/Widgets/Menus/WBP_Credits'
    token = h.lease_acquire(owner, ['asset:' + b.WBP, 'asset:' + DEST, 'asset:' + credits], ttl_s=300, wait_s=3)
    os.environ['FOA_LEASE'] = token
    try:
        backup = Path('P:/FoA/Saved/Backups/battle-icons-20261111'); backup.mkdir(parents=True, exist_ok=True)
        for path in (b.WBP, credits):
            source = Path('P:/FoA/Content') / (path.removeprefix('/Game/') + '.uasset')
            if source.exists() and not (backup / source.name).exists(): shutil.copy2(source, backup / source.name)
        existing = b.c('ui_query', path=b.WBP, name_pattern='TornGlyph_Act0').get('matches')
        assert existing, 'Expected current torn-card layout; inspect live widget before changing it'
        # Claude saved only layout. Complete the existing builder's dependency order before styling it.
        b.lookup(); b.stubs(); b.stats()
        for graph, build in [('TornConfigure', b.configure), ('TornConfigureAll', b.configureall),
                             ('TornCost', b.costs), ('TornRememberCard', b.commit),
                             ('TornStep', b.stepcard), ('TornTrackIntent', b.intent), ('TornTick', b.tick)]:
            nodes, _ = b.graph(b.WBP, graph)
            body = [n for n in nodes if n['title'].replace(' ', '') != graph and not n['title'].startswith('Return')]
            if not body: build()
        b.hook()
        for name in ICONS:
            if not Path(f'P:/FoA/Content/FoA/Gameplay/Encounter/Icons/T_BattleGame_{name}.uasset').exists():
                b.c('asset_import', source_file=str(STAGE / f'T_BattleGame_{name}.png'), destination_path=DEST, asset_type='texture')
        for name, icon in dict(Act0='Shirt', Act1='Button', Act2='Grip', Breathe='Breathe', Mirror='Mirror').items():
            b.props('TornGlyph_' + name, {'Brush': f'(ResourceObject="{asset(icon)}",DrawAs=Image)',
                                        'ColorAndOpacity': '(R=.95,G=.95,B=.95,A=1)'}, b.slot(49,38,104,104))
            b.props('TornSize_' + name, {'WidthOverride':202., 'HeightOverride':252.})
            b.props('TornGrain_' + name, s=b.slot(-6,-6,214,264))
            b.props('TornCard_' + name, s={'fill':0, 'padding':[6,0,6,0]})
            b.props('TornPips_' + name, {'Visibility':'Collapsed'})
            b.props('Btn_' + name, {'LabelSize':24., 'TextAlphaRest':1., 'TextAlphaDisabled':.5})
        for name in ('Items','Flee'): b.props('TornCard_' + name, {'Visibility':'Collapsed'})
        b.props('TornDeck', s={'position':[0,-88]})
        b.props('Txt_TornDetail', b.text('x', size=24)['properties'], b.slot(0,-400,1040,60,(.5,1),(.5,1)))
        b.props('TornIntentGlyph', {'Brush': f'(ResourceObject="{asset("Target")}",DrawAs=Image)'})
        b.props('Txt_TornIntent', {'Visibility':'Collapsed'})
        # Resource names, exact values and horizontal fills stay together in the familiar HUD position.
        b.props('TornStats', {'Visibility':'Collapsed'})
        b.props('SelfBox', s=b.slot(48,40,330,156))
        for name in ('Composure','Resolve'):
            b.props('Box_' + name, {'Visibility':'SelfHitTestInvisible'})
            b.move('Txt_' + name + 'Label', 'Row_' + name, fill=1, padding=[12,0,12,0])
            b.move('Txt_' + name, 'Row_' + name, padding=[0,0,0,0])
            b.move('Size_Bar_' + name, 'Box_' + name, padding=[0,8,0,12])
            b.props('Icon_' + name, {'Brush':f'(ResourceObject="{asset(name)}",ImageSize=(X=28,Y=28),DrawAs=Image)'})
            b.props('Txt_' + name + 'Label', b.text('x', name, 24)['properties'] | {'Justification':'Left'})
            b.props('Size_Bar_' + name, {'WidthOverride':330., 'HeightOverride':7.})
            b.props('Bar_' + name, {'BarFillType':'LeftToRight', 'WidgetStyle':
                '(BackgroundImage=(DrawAs=Box,TintColor=(SpecifiedColor=(R=.15,G=.15,B=.15,A=1))),'
                'FillImage=(DrawAs=Box,TintColor=(SpecifiedColor=(R=1,G=1,B=1,A=1))))'})
        # Existing runtime configuration otherwise restores the old card hitbox dimensions.
        for graph in ('TornConfigure','TornTick','TornStep'):
            nodes, edges = b.graph(b.WBP, graph); batch = b.B(b.WBP, graph)
            focus_gets = {n['node_id'] for n in nodes if n['title'] == 'Get Img_CommandFocus'}
            focus_setters = {e['to_node'] for e in edges if e['from_node'] in focus_gets and e['to_pin'] == 'self'}
            for node in nodes:
                title = node['title'].replace(' ', '')
                pins = {p['name']: p.get('default') for p in node.get('pins', [])}
                changes = {}
                if graph == 'TornConfigure' and title == 'SetHeightOverride': changes['InHeightOverride'] = '252'
                if graph == 'TornConfigure' and title == 'SetMinDesiredWidth': changes['InMinDesiredWidth'] = '202'
                if graph == 'TornConfigure' and node['node_id'] in focus_setters and title == 'SetVisibility': changes['InVisibility'] = 'HitTestInvisible'
                if graph == 'TornTick' and title == 'TornStep': changes['Tilt'] = '0'
                if graph == 'TornStep' and title.startswith('Multiply') and str(pins.get('B')) in ('52','52.0','52.000000'): changes['B'] = '24'
                for pin, value in changes.items(): batch.ops.append(dict(op='set_pin', node_id=node['node_id'], pin_name=pin, value=value))
            if batch.ops: batch.run()
        fixed_card_width(b); stable_card_labels(b); action_graph(b); restore_cost_labels(b)
        import build_credits
        node = build_credits.block('BattleIcons', 'Battle icons', CREDIT, 28)
        if not b.c('ui_query', path=credits, name_pattern='BattleIcons').get('matches'):
            b.c('ui_build_tree', widget_blueprint_path=credits, parent_widget_name='CreditsRight', tree=node)
        result = b.c('blueprint_compile', path=b.WBP, save=True); assert result['error_count'] == 0
        b.c('ui_compile_widget', widget_blueprint_path=credits, save_on_success=True)
        print('Battle UI saved. Runtime visual and input proof still required.')
    finally:
        h.release(owner, token); os.environ.pop('FOA_LEASE', None)


if __name__ == '__main__':
    {'prepare': prepare, 'selftest': selftest, 'preview': preview, 'apply': apply}[sys.argv[1]]()
