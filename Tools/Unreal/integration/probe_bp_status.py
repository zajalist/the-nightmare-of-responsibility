"""Integration lane, read-only: the compile status of every Blueprint under /Game/FoA, without compiling anything.
  python Tools/Unreal/integration/run_read.py Tools/Unreal/integration/probe_bp_status.py
Writes P:/FoA/Saved/Integration/bp_status.json: {path: status} for Blueprints and Widget Blueprints; BS_ERROR and
BS_UPTODATE_WITH_WARNINGS are the ones to chase (their messages are in the log from the owning lane's last compile)."""
import json

import unreal

OUT = 'P:/FoA/Saved/Integration/bp_status.json'
SKIP = ('/Game/FoA/Characters/Player/_', '/Game/FoA/Characters/Player/Anims')


def main():
    ar = unreal.AssetRegistryHelpers.get_asset_registry()
    flt = unreal.ARFilter(package_paths=['/Game/FoA'], recursive_paths=True,
                          class_paths=[unreal.TopLevelAssetPath('/Script/Engine', 'Blueprint'),
                                       unreal.TopLevelAssetPath('/Script/UMGEditor', 'WidgetBlueprint')])
    out = {}
    for ad in ar.get_assets(flt):
        path = str(ad.package_name)
        if path.startswith(SKIP):
            continue
        bp = unreal.load_asset(path)
        try:
            out[path] = str(bp.get_editor_property('status')).split('.')[-1].split(':')[0].strip()
        except Exception as err:  # noqa: BLE001  (read-only: report and go on)
            out[path] = f'n/a ({err})'
        del bp
    with open(OUT, 'w', encoding='utf-8') as fh:
        json.dump(out, fh, indent=1, sort_keys=True)
    bad = {k: v for k, v in out.items() if 'UPTODATE' not in v.upper() or 'WARN' in v.upper()}
    print('bp status', len(out), 'checked;', len(bad), 'not clean:', bad)


main()
