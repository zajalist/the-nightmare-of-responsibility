"""Patch the approved story text (story_text.py) into DT_Interactions, DT_Items and GI_FoA NotebookLines, by row name.
Runs inside the editor; only Line/Prompt cells, the ROW_FIELDS cells, the DT_Items DisplayName/LookLine cells and
NotebookLines values change, every other cell is checked
unchanged. Save afterwards with Hayba asset_save (the runner below does both):
  python Tools/Unreal/flow/apply_story_text.py          (outside the editor: lease, run, save, release)"""
import json
import os
import sys

DT_I, DT_T, GI = '/Game/FoA/Gameplay/DT_Interactions', '/Game/FoA/Gameplay/DT_Items', '/Game/FoA/Gameplay/GI_FoA'


def patch():
    import unreal
    sys.path.insert(0, 'P:/FoA/Tools/Unreal/flow')
    import story_text as T
    assert unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world() is None, 'PIE running'
    report = {}
    lib = unreal.DataTableFunctionLibrary
    for path, edits in ((DT_I, {**{(k, 'Line'): v for k, v in T.LINES.items()}, **{(k, 'Prompt'): v for k, v in T.PROMPTS.items()},
                               **{(k, f): v for k, cells in T.ROW_FIELDS.items() for f, v in cells.items()}}),
                        (DT_T, {**{(k, 'LookLine'): v for k, v in T.ITEM_LOOKS.items()}, **{(k, 'DisplayName'): v for k, v in T.ITEM_NAMES.items()}})):
        table = unreal.load_asset(path)
        rows = json.loads(lib.export_data_table_to_json_string(table))
        names = {r['Name'] for r in rows}
        missing = sorted({k for k, _ in edits} - names)
        assert not missing, (path, missing)
        nocol = sorted({f for _, f in edits} - set(rows[0]))
        assert not nocol, (path, 'no such column', nocol)
        changed = []
        for r in rows:
            for (name, field), text in edits.items():
                if r['Name'] == name and T.plain(r[field]) != text and not (text == 'None' and r[field] in ('', 'None')):
                    r[field] = text
                    changed.append(name + '.' + field)
        if changed:
            assert lib.fill_data_table_from_json_string(table, json.dumps(rows))
        after = json.loads(lib.export_data_table_to_json_string(table))
        assert len(after) == len(rows)
        for want, got in zip(rows, after):
            for key, value in want.items():
                same = T.plain(got[key]) == T.plain(value) if key in ('Line', 'Prompt', 'LookLine', 'DisplayName') else got[key] == value
                assert same, (path, want['Name'], key, value, got[key])
        report[path] = changed
    gi = unreal.load_asset(GI)
    cdo = unreal.get_default_object(gi.generated_class())
    notes = dict(cdo.get_editor_property('NotebookLines'))
    keys = {str(k): k for k in notes}
    assert set(T.NOTES) <= set(keys), sorted(set(T.NOTES) - set(keys))
    changed = [f for f, t in T.NOTES.items() if str(notes[keys[f]]) != t]
    for f in changed:
        notes[keys[f]] = unreal.Text(T.NOTES[f])
    if changed:
        cdo.set_editor_property('NotebookLines', notes)
        gi.modify()
    after = {str(k): str(v) for k, v in dict(cdo.get_editor_property('NotebookLines')).items()}
    assert all(after[f] == t for f, t in T.NOTES.items()), after
    report[GI] = changed
    with open('P:/FoA/Saved/StoryShots/story_text_applied.json', 'w') as fh:
        json.dump(report, fh, indent=1)
    print('story text patched', {k: len(v) for k, v in report.items()})


def run():
    sys.path.insert(0, 'P:/FoA/Tools/Unreal')
    import subprocess
    import hayba_call as h
    env = dict(os.environ, FOA_AGENT='story', HAYBA_AGENT_ID='story', FOA_AREAS=','.join((DT_I, DT_T, GI)))
    out = subprocess.run([sys.executable, 'P:/FoA/Tools/Unreal/ue_remote.py', os.path.abspath(__file__)], env=env,
                         capture_output=True, text=True, timeout=300)
    print(out.stdout[-2000:], out.stderr[-2000:])
    assert 'story text patched' in out.stdout, 'patch did not run'
    r = h.call('asset_save', {'asset_paths': [DT_I, DT_T, GI]})
    assert r.get('ok') and not r.get('data', {}).get('failed'), r
    print('saved', r.get('data'))


if __name__ == '__main__':
    try:
        import unreal  # noqa: F401  (inside the editor)
    except ImportError:
        run()
    else:
        patch()
