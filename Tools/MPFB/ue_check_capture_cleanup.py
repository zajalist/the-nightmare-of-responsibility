"""Verify no teen capture actors remain; read-only, safe after asynchronous capture cleanup."""
import unreal
names = [a.get_actor_label() for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
         if a.get_actor_label().startswith('TMP_rlchar_')]
assert not names, names
print('TEEN_CAPTURE_CLEANUP no TMP_rlchar_ actors')
