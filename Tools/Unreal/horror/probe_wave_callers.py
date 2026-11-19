"""Read-only: who references each SoundWave directly (raw-wave plays bypass the presets' class, attenuation and concurrency).
  $env:FOA_AREAS='Audio'; python Tools/Unreal/ue_remote.py Tools/Unreal/horror/probe_wave_callers.py
Writes Saved/HorrorShots/wave_callers.txt: one line per wave with its non-preset referencers."""
import unreal


def main():
    reg = unreal.AssetRegistryHelpers.get_asset_registry()
    opts = unreal.AssetRegistryDependencyOptions()
    rows = []
    for p in unreal.EditorAssetLibrary.list_assets('/Game/FoA/Audio/SFX', recursive=True, include_folder=False):
        pkg = p.split('.')[0]
        refs = [str(r) for r in (reg.get_referencers(pkg, opts) or []) if str(r) != pkg]
        direct = [r for r in refs if '/Audio/MetaSounds/' not in r and '/Audio/SFX/' not in r]
        if direct:
            rows.append(pkg.split('/')[-1] + ' <- ' + ', '.join(direct))
    with open('P:/FoA/Saved/HorrorShots/wave_callers.txt', 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(rows))
    print('waves with direct callers', len(rows))


main()
