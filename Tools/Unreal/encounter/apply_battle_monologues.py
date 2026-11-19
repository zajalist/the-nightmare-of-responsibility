"""Apply only the authored narration fields, retaining every battle rule and reference."""
import json, os, sys
from pathlib import Path
sys.path.insert(0, 'P:/FoA/Tools/Unreal')
import hayba_call as h
from encounter_data import MOVES


def main():
    assert sys.argv[1:] == ['--apply']
    assert not h.call('editor_get_state')['data']['pie_running']
    owner = 'main:presentation'
    os.environ['HAYBA_AGENT_ID'] = owner
    paths = {key: '/Game/FoA/Gameplay/Encounter/Data/DA_Move_' + key for key in MOVES}
    token = h.lease_acquire(owner, ['asset:' + p for p in paths.values()], ttl_s=40, wait_s=3)
    def call(command, **params):
        result = h.call(command, params, owner=owner, lease=token)
        assert result.get('ok'), result
        data = result.get('data', {})
        assert data.get('ok', True) and not data.get('failed'), data
        return data
    rows = []
    try:
        assert not call('editor_get_state')['pie_running']
        for key, path in paths.items():
            fields = [k if k != 'Owner' else 'bOpponentMove' for k in MOVES[key]]
            before = call('object_get_property', path=path, names=fields)
            assert set(before['properties']) == set(fields), before
            call('object_set_property', path=path, properties={'Narration': MOVES[key]['Narration']})
            after = call('object_get_property', path=path, names=fields)
            old, new = before['properties'], after['properties']
            assert new['Narration'] in (MOVES[key]['Narration'], 'INVTEXT(' + json.dumps(MOVES[key]['Narration']) + ')'), new
            assert {k:v for k,v in old.items() if k != 'Narration'} == {k:v for k,v in new.items() if k != 'Narration'}, key
            rows.append({'path': path, 'before': old['Narration'], 'after': new['Narration'], 'rules_unchanged': True})
        call('asset_save', asset_paths=list(paths.values()))
        Path('Saved/PresentationReview/battle_monologues.json').write_text(json.dumps(rows, indent=1))
        print('Saved and read back', len(rows), 'thoughts; every other property unchanged')
    finally:
        h.release(owner, token)


if __name__ == '__main__':
    main()
