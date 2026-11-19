"""Apply the approved battle text (encounter_data.py MOVES and OPPONENTS, story_text.MOVE_DETAIL) to the live data assets
and BP_Encounter's MoveDetail pins, through Hayba only. Only the text fields are written, then read back.
  python Tools/Unreal/encounter/apply_battle_text.py --apply"""
import json
import os
import sys
from pathlib import Path

sys.path[:0] = ['P:/FoA/Tools/Unreal', 'P:/FoA/Tools/Unreal/flow', 'P:/FoA/Tools/Unreal/player']
import hayba_call as h  # noqa: E402
from encounter_data import MOVES, OPPONENTS  # noqa: E402
from held_tool_graphs import inspect  # noqa: E402
from story_text import MOVE_DETAIL, plain as text_of  # noqa: E402

DATA = '/Game/FoA/Gameplay/Encounter/Data/'
BP = '/Game/FoA/Gameplay/Encounter/BP_Encounter'
OWNER = 'story'


def main():
    assert sys.argv[1:] == ['--apply']
    os.environ['HAYBA_AGENT_ID'] = OWNER
    targets = {DATA + 'DA_Move_' + k: {f: v[f] for f in ('Narration', 'TelegraphLine') if v.get(f)} for k, v in MOVES.items()}
    targets.update({DATA + 'DA_Opponent_' + k: {f: v[f] for f in ('DisplayName', 'IntroLine', 'WinLine', 'LoseLine',
                                                                  'VictoryLine') if v.get(f)} for k, v in OPPONENTS.items()})
    token = h.lease_acquire(OWNER, ['asset:' + p for p in list(targets) + [BP]], ttl_s=90, wait_s=30)

    def call(command, **params):
        r = h.call(command, params, owner=OWNER, lease=token)
        assert r.get('ok'), (command, r)
        d = r.get('data', {})
        assert d.get('ok', True) and not d.get('failed'), (command, d)
        return d

    rows, changed = [], []
    try:
        assert not call('editor_get_state')['pie_running'], 'PIE running'
        for path, want in targets.items():
            props = call('object_get_property', path=path, names=list(want))['properties']
            diff = {k: v for k, v in want.items() if text_of(props.get(k)) != v}
            if diff:
                call('object_set_property', path=path, properties=diff)
                after = call('object_get_property', path=path, names=list(want))['properties']
                assert all(text_of(after[k]) == v for k, v in want.items()), (path, after)
                changed.append(path)
            rows.append({'path': path, 'set': list(diff)})
        if changed:
            call('asset_save', asset_paths=changed)
        # BP_Encounter MoveDetail: the player reads "pants"
        nodes, _ = inspect(BP, 'MoveDetail')
        ops = [dict(op='set_pin', node_id=n['node_id'], pin_name=p['name'], value=MOVE_DETAIL[p.get('default_value')])
               for n in nodes for p in n.get('pins', []) if p.get('default_value') in MOVE_DETAIL]
        if ops:
            r = call('blueprint_graph_batch', path=BP, graph_name='MoveDetail', ops=ops, compile=True, save=True)
            assert r.get('applied') == len(ops) and not r.get('compile_error'), r
        rows.append({'path': BP, 'move_detail_pins': len(ops)})
        Path('P:/FoA/Saved/StoryShots/battle_text_applied.json').write_text(json.dumps(rows, indent=1))
        print('battle text: %d assets changed, %d MoveDetail pins' % (len(changed), len(ops)))
    finally:
        h.release(OWNER, token)


if __name__ == '__main__':
    main()
