"""Wire existing hands and preserve their editor transforms; verify the actual Blueprint step."""
import json
from pathlib import Path
import unreal
assert not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
e=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
actors={a.get_actor_label():a for a in e.get_all_level_actors()}
bp=unreal.load_asset('/Game/FoA/Gameplay/BP_ClockTick'); assert bp
hands={'Hours':actors['WallClock_wall_clock_hours_hand'],
       'Minutes':actors['WallClock_wall_clock_minute_hand'],
       'Seconds':actors['WallClock_wall_clock_second_hand']}
original={n:a.get_actor_transform() for n,a in hands.items()}
clock=actors.get('ClockTick') or e.spawn_actor_from_class(bp.generated_class(),unreal.Vector())
clock.set_actor_label('ClockTick');clock.set_folder_path('Room/Furniture')
for name,a in hands.items():
    clock.set_editor_property(name,a)
    a.static_mesh_component.set_mobility(unreal.ComponentMobility.MOVABLE)
report={}
try:
    clock.call_method('ClockTick')
    for name,expected in [('Hours',-1/120),('Minutes',-.1),('Seconds',-6.)]:
        a=hands[name];start=original[name];end=a.get_actor_transform()
        q=start.rotation
        delta=unreal.Quat(-q.x,-q.y,-q.z,q.w)*end.rotation
        angle=delta.rotator()
        assert abs(angle.pitch-expected)<.0001,(name,angle)
        assert (start.translation-end.translation).length()<.00001
        report[name]={'step_degrees':angle.pitch,'position_unchanged':True}
finally:
    for name,a in hands.items():a.set_actor_transform(original[name],False,True)
amb=actors['Amb_ClockTick'].audio_component
report['existing_tick_audio']=str(amb.sound)
assert amb.sound
unreal.FoAGraphToolsLibrary.capture_graph_png(bp,'EventGraph','P:/FoA/Saved/GraphShots/clock_tick.png',True)
Path('P:/FoA/Saved/Integration/clock_step_check.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report))
