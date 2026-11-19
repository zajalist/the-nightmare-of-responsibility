"""Integration lane: read-only live probe of the contract wiring. Writes P:/FoA/Saved/Integration/probe.json.
  python Tools/Unreal/integration/run_read.py Tools/Unreal/integration/probe_wiring.py
Reads only: asset existence, function and dispatcher names, dirty packages, level actors, director instance refs."""
import json

import unreal

OUT = 'P:/FoA/Saved/Integration/probe.json'
BEL, EAL = unreal.BlueprintEditorLibrary, unreal.EditorAssetLibrary
BPS = ['/Game/FoA/Gameplay/BP_BeatDirector', '/Game/FoA/Gameplay/GI_FoA', '/Game/FoA/Gameplay/BPC_Interactor',
       '/Game/FoA/Gameplay/BPC_Inventory', '/Game/FoA/Gameplay/BP_Interactable', '/Game/FoA/Gameplay/Encounter/BP_Encounter',
       '/Game/FoA/Gameplay/Encounter/WBP_Encounter', '/Game/FoA/UI/Framework/BP_FoAFrontEnd', '/Game/FoA/UI/Game/WBP_HUD',
       '/Game/FoA/UI/Game/WBP_Phone', '/Game/FoA/UI/Game/WBP_DayRollover', '/Game/FoA/Cinematics/BP_WakeUpCinematic',
       '/Game/FoA/Characters/Player/BP_FoAPlayer', '/Game/FoA/Characters/Player/BP_Nightmare',
       '/Game/FoA/PostProcess/BP_DreamDirector', '/Game/FoA/VFX/Sand/BP_SandMaterialize', '/Game/FoA/VFX/Sand/BPL_SandFX']
OTHER = ['/Game/FoA/Characters/Player/MPC_FoAPlayer', '/Game/FoA/VFX/Sand/M_SandOverlay',
         '/Game/FoA/Audio/SFX/UI_FrontEnd/SFX_FE_WakeUpPress', '/Game/FoA/UI/Intro/WBP_IntroStory',
         '/Game/FoA/UI/Widgets/Menus/WBP_Settings', '/Game/FoA/UI/Widgets/Menus/WBP_Credits']


def names(seq):
    return sorted(str(x) for x in (seq or []))


def probe_bp(path):
    if not EAL.does_asset_exist(path):
        return None
    bp = unreal.load_asset(path)
    info = {}
    for key, fn in (('functions', 'list_functions'), ('dispatchers', 'list_event_dispatchers')):
        f = getattr(BEL, fn, None)
        try:
            info[key] = names(f(bp)) if f else 'n/a'
        except Exception as err:  # noqa: BLE001  (read-only probe: report, never stop)
            info[key] = f'err {err}'
    return info


def main():
    out = {'bps': {p: probe_bp(p) for p in BPS}, 'other': {p: EAL.does_asset_exist(p) for p in OTHER}}
    dirty = unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages() + \
        unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()
    out['dirty'] = sorted(p.get_name() for p in dirty if '/Game/FoA' in p.get_name())
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
    out['actors'] = sorted(f'{a.get_actor_label()}|{a.get_class().get_name()}' for a in actors
                           if not a.get_class().get_name().startswith(('StaticMeshActor', 'DecalActor')))
    out['tagged_WakeUpClock'] = [a.get_actor_label() for a in actors if 'WakeUpClock' in [str(t) for t in a.tags]]
    for a in actors:
        cn = a.get_class().get_name()
        if cn == 'BP_BeatDirector_C':
            refs = {}
            for k in ('Door', 'DoorFrame', 'RefillActor', 'Ceiling', 'WakeUpStart', 'ShirtActor'):
                try:
                    v = a.get_editor_property(k)
                    refs[k] = v.get_actor_label() if v else None
                except Exception:  # noqa: BLE001
                    refs[k] = 'n/a'
            out['director_refs'] = refs
        if cn == 'BP_FoAFrontEnd_C':
            refs = {}
            for k in ('StoryClass', 'PhoneClass', 'HUDClass', 'SettingsClass', 'CreditsClass'):
                try:
                    v = a.get_editor_property(k)
                    refs[k] = v.get_name() if v else None
                except Exception:  # noqa: BLE001
                    refs[k] = 'n/a'
            out['frontend_refs'] = refs
    with open(OUT, 'w', encoding='utf-8') as fh:
        json.dump(out, fh, indent=1)
    print('probe ok', len(out['actors']), 'actors,', len(out['dirty']), 'dirty')


main()
