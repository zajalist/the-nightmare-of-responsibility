"""Integration lane, read-only: BP_BeatDirector's beat data on the placed instance and the CDO.
  python Tools/Unreal/integration/run_read.py Tools/Unreal/integration/probe_director.py"""
import unreal

C = '/Game/FoA/Gameplay/BP_BeatDirector.BP_BeatDirector_C'


def show(tag, obj):
    out = []
    for k in ('Beats', 'PhoneTasks', 'RolloverSeconds', 'TopDownHold', 'bAlarmClockFail', 'BeatIndex', 'RefillActor',
              'ShirtActor', 'NightMareMesh'):
        try:
            v = obj.get_editor_property(k)
            out.append(f'{k}={len(v) if hasattr(v, "__len__") and not isinstance(v, str) else v}')
        except Exception as err:  # noqa: BLE001
            out.append(f'{k}=n/a')
    print(tag, ' '.join(out))


cls = unreal.load_class(None, C)
show('CDO', unreal.get_default_object(cls))
for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
    if a.get_class() == cls:
        show('LEVEL ' + a.get_actor_label(), a)
