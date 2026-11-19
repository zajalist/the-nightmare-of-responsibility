"""BP_BeatDirector text pass (Hayba only, idempotent): the approved story moments and clothing lines replace the old
string pins (story_text.DIRECTOR), and the level end says "Day one." on the black before the front end's EndOfLevel.
  python Tools/Unreal/flow/apply_story_director.py
EndLevel was: fade to black 1 s, Delay 1.2, front end EndOfLevel. Now: fade, Delay 1.2, WBP_EndCard (ENDING, built by
Tools/LookDev/build_end_card.py) for 3 s, then the same EndOfLevel branch."""
import json
import os
import sys
from pathlib import Path

sys.path[:0] = ['P:/FoA/Tools/Unreal', 'P:/FoA/Tools/Unreal/player', 'P:/FoA/Tools/Unreal/flow']
import hayba_call as h  # noqa: E402
from held_tool_graphs import Batch, inspect  # noqa: E402
from story_text import DIRECTOR, ENDING  # noqa: E402

P = '/Game/FoA/Gameplay/BP_BeatDirector'
INTER = '/Game/FoA/Gameplay/BPC_Interactor.BPC_Interactor_C'
CARD = '/Game/FoA/UI/Intro/WBP_EndCard.WBP_EndCard_C'
FE = '/Game/FoA/UI/Framework/BP_FoAFrontEnd.BP_FoAFrontEnd_C'
GS = '/Script/Engine.GameplayStatics:'
OWNER = 'story'


def pins_to_fix(graph):
    nodes, _ = inspect(P, graph)
    return [(n['node_id'], p['name'], DIRECTOR[p['default_value']]) for n in nodes for p in n.get('pins', [])
            if p.get('default_value') in DIRECTOR]


def ending():
    """EndLevel: fade, Delay 1.2, WBP_EndCard (the line centred on the black, independent of the HUD and the phone),
    Delay 3.0, RemoveFromParent, then the front end's EndOfLevel. Replaces the first version, which narrated the line
    through the HUD subtitle and was invisible whenever the phone (T10) still had the HUD hidden."""
    nodes, edges = inspect(P, 'EventGraph')
    if any(n['title']=='Continue into the dream' for n in nodes):
        return 'Dream threshold owns the chapter card'
    by = {n['node_id']: n for n in nodes}
    if any(CARD in str(p.get('default_object') or p.get('default_value') or '') for n in nodes for p in n.get('pins', [])):
        return 'end card already present'
    end = next(n['node_id'] for n in nodes if n['title'] == 'EndLevel' and not any(p['name'] == 'self' for p in n['pins']))
    chain, cur = [], end                                     # EndLevel -> fade -> Delay(1.2) -> ... -> GetActorOfClass
    for _ in range(12):
        nxt = next((e for e in edges if e['from_node'] == cur and e['from_pin'] == 'then'), None)
        assert nxt, ('EndLevel chain broken at', by[cur]['title'])
        cur = nxt['to_node']
        chain.append((cur, nxt['to_pin']))
        if by[cur]['title'] == 'GetActorOfClass':
            break
    titles = [by[n]['title'] for n, _ in chain]
    first = titles.index('Delay')
    delay, (target, target_pin) = chain[first][0], chain[-1]
    old = [n for n, _ in chain[first + 1:-1]]                # the first version's Narrate + Delay(3.0)
    pure = [e['from_node'] for e in edges if e['to_node'] in old and by[e['from_node']]['title'] in
            ('GetPlayerCharacter', 'GetComponentByClass', 'To Text (String)')]
    pure += [e['from_node'] for e in edges if e['to_node'] in pure and by[e['from_node']]['title'] == 'GetPlayerCharacter']
    boxes = [n['node_id'] for n in nodes if n['title'] == 'Day one']
    b = Batch(P, 'EventGraph')
    if old:
        b.ops.append(dict(op='remove', node_ids=sorted(set(old + pure + boxes))))
    else:
        b.cut(delay, 'then', target, target_pin)
    b.node('card', 'create_widget', 1100, 2300)
    b.pin('card', 'Class', CARD)
    b.fn('show', '/Script/UMG.UserWidget:AddToViewport', 1450, 2300, ZOrder=200)
    b.link('card', 'ReturnValue', 'show', 'self')
    b.fn('hold', '/Script/Engine.KismetSystemLibrary:Delay', 1750, 2300, Duration=3.0)
    b.fn('gone', '/Script/UMG.Widget:RemoveFromParent', 2050, 2300)
    b.link('card', 'ReturnValue', 'gone', 'self')
    b.link(delay, 'then', 'card', 'execute')
    b.chain('card', 'show', 'hold', 'gone')
    b.link('gone', 'then', target, target_pin)
    b.comment('Day one', ['card', 'show', 'hold', 'gone'])
    b.run()
    return 'end card after ' + by[delay]['title'] + (', replaced the narrated version' if old else '')


def hide_hud_at_end():
    """The card owns the black: the HUD (objective, key hints) collapses first. EnterGameplay makes a fresh HUD each
    morning, so nothing has to restore it."""
    nodes, edges = inspect(P, 'EventGraph')
    if any(n['title']=='Continue into the dream' for n in nodes):
        return 'Dream threshold owns HUD visibility'
    by = {n['node_id']: n for n in nodes}
    card = next(n['node_id'] for n in nodes if any(CARD in str(p.get('default_object') or p.get('default_value') or '')
                                                   for p in n['pins']))
    feed = next(e for e in edges if e['to_node'] == card and e['to_pin'] == 'execute')
    if by[feed['from_node']]['title'] in ('SetVisibility', 'Branch'):
        return 'HUD already hidden at the end'
    b = Batch(P, 'EventGraph')
    b.fn('fe', GS + 'GetActorOfClass', 900, 2650, ActorClass=FE)
    b.get('hud', 'HUD', 1150, 2850, FE)
    b.link('fe', 'ReturnValue', 'hud', 'self')
    b.fn('ok', '/Script/Engine.KismetSystemLibrary:IsValid', 1400, 2850)
    b.link('hud', 'HUD', 'ok', 'Object')
    b.node('has', 'branch', 1400, 2650)
    b.link('ok', 'ReturnValue', 'has', 'Condition')
    b.fn('hide', '/Script/UMG.Widget:SetVisibility', 1650, 2650, InVisibility='Collapsed')
    b.link('hud', 'HUD', 'hide', 'self')
    b.cut(feed['from_node'], feed['from_pin'], card, 'execute')
    b.link(feed['from_node'], feed['from_pin'], 'fe', 'execute')
    b.chain('fe', 'has')
    b.link('has', 'then', 'hide', 'execute')
    b.link('hide', 'then', card, 'execute')
    b.link('has', 'else', card, 'execute')
    b.comment('Only the card on the black', ['fe', 'hud', 'ok', 'has', 'hide'])
    b.run()
    return 'HUD collapses before the end card'


def main():
    os.environ['HAYBA_AGENT_ID'] = OWNER
    assert not h.call('editor_get_state', {})['data']['pie_running'], 'PIE running'
    token = h.lease_acquire(OWNER, ['asset:' + P], ttl_s=180, wait_s=60)
    os.environ['FOA_LEASE'] = token
    report = {}
    try:
        graphs = json.loads(Path('P:/FoA/Saved/StoryShots/graph_names.json').read_text())[P]
        for g in graphs:
            fixes = pins_to_fix(g)
            if fixes:
                b = Batch(P, g)
                for node, pin, value in fixes:
                    b.pin(node, pin, value)
                b.run()
                report[g] = [v for _, _, v in fixes]
        report['EndLevel'] = ending()
        report['EndHUD'] = hide_hud_at_end()
        left = [(g, v) for g in graphs for _, _, v in pins_to_fix(g)]
        assert not left, left
        Path('P:/FoA/Saved/StoryShots/director_text_applied.json').write_text(json.dumps(report, indent=1))
        print(json.dumps(report, indent=1))
    finally:
        h.release(OWNER, token)
        os.environ.pop('FOA_LEASE', None)


if __name__ == '__main__':
    main()
