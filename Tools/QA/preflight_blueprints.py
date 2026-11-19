"""qa lane pre-flight, run through run_read inside qa's EXCLUSIVE lease right before PIE: makes sure no Blueprint will
raise the editor's modal "Blueprint Asset Compilation Error" dialog at PIE start (it froze the editor on 2026-11-09).
Read-only: checks the key Blueprints (loading them) plus every FoA Blueprint already in memory (PIE checks those). An
error fails it, and so does a stale (dirty) one: PIE start would compile it and an error there is the modal. It never
compiles: other lanes may be mid-edit. Also reports (never gates) every DT_Interactions montage without AN_FoA_InteractionContact. Writes Saved/QA/preflight.json."""
import json
import os

import unreal

KEY = ('/Game/FoA/Gameplay/BP_BeatDirector', '/Game/FoA/Characters/Player/BP_FoAPlayer', '/Game/FoA/Gameplay/BP_Interactable',
       '/Game/FoA/Gameplay/Jumpscare/BP_Jumpscare', '/Game/FoA/UI/Game/BP_Phone', '/Game/FoA/UI/Framework/BP_FoAFrontEnd',
       '/Game/FoA/Gameplay/Encounter/BP_Encounter', '/Game/FoA/Gameplay/Encounter/WBP_Encounter')


def status(bp):
    v = bp.get_editor_property('status')
    return str(getattr(v, 'name', v)).upper()  # BS_UP_TO_DATE, BS_ERROR, BS_DIRTY, ...


def montage_contacts():
    """Every montage a DT_Interactions row plays must carry AN_FoA_InteractionContact, or the real E interaction
    animates and never commits (2026-11-10). Read-only: the table export and each montage's notify events."""
    rows = json.loads(unreal.DataTableFunctionLibrary.export_data_table_to_json_string(
        unreal.load_asset('/Game/FoA/Gameplay/DT_Interactions')))
    paths = sorted({str(r.get('Montage') or '') for r in rows} - {'', 'None'})
    out = []
    for path in paths:
        m = unreal.load_asset(path)
        if m is None:
            out.append(dict(montage=path, contact=False, why='missing asset'))
            continue
        names = [str(n) for n in unreal.AnimationLibrary.get_animation_notify_event_names(m)]
        classes = [ev.get_editor_property('notify').get_class().get_name()
                   for ev in unreal.AnimationLibrary.get_animation_notify_events(m) if ev.get_editor_property('notify')]
        out.append(dict(montage=path.rsplit('.', 1)[-1], contact=any('InteractionContact' in x for x in names + classes),
                        notifies=sorted(set(names + classes))[:12]))
    return out


def main():
    rows, paths = [], set(KEY)
    reg = unreal.AssetRegistryHelpers.get_asset_registry()
    for data in reg.get_assets_by_path('/Game/FoA', recursive=True):
        cls = str(data.asset_class_path.asset_name)
        if cls in ('Blueprint', 'WidgetBlueprint', 'AnimBlueprint') and 'RoomAudio' in str(data.asset_name):
            paths.add(str(data.package_name))  # BP_RoomAudio when it exists (main asked for it by name)
        if cls in ('Blueprint', 'WidgetBlueprint', 'AnimBlueprint') and data.is_asset_loaded():
            paths.add(str(data.package_name))
    for path in sorted(paths):
        name = path + '.' + path.rsplit('/', 1)[1]
        bp = unreal.find_object(None, name)
        if bp is None and (path in KEY or 'RoomAudio' in path):
            bp = unreal.load_asset(name)
        if not bp or not isinstance(bp, unreal.Blueprint):
            rows.append(dict(path=path, status='missing' if path in KEY else 'skipped'))
            continue
        rows.append(dict(path=path, status=status(bp)))
    bad = [r for r in rows if r['status'] not in ('skipped', 'BS_UP_TO_DATE', 'BS_UP_TO_DATE_WITH_WARNINGS')]
    montages = []
    if os.environ.get('FOA_PREFLIGHT_SKIP_CONTACTS') != '1':
        try:
            montages = montage_contacts()
        except Exception as ex:  # the montage report must never break the Blueprint gate above
            montages = [dict(montage='(check failed)', contact=False, why=repr(ex)[:200])]
    mbad = [m for m in montages if not m['contact']]
    out = dict(ok=not bad, failures=bad, checked=len(rows), rows=rows,
               montages_ok=not mbad, montage_failures=mbad, montages=montages)
    json.dump(out, open('P:/FoA/Saved/QA/preflight.json', 'w', encoding='utf-8'), indent=1)
    print('preflight', 'OK' if not bad else 'FAIL', len(rows), 'checked;', [r['path'] for r in bad],
          '| montages', 'OK' if not mbad else 'FAIL', [m['montage'] for m in mbad])


main()
