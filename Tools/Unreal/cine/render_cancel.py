"""Cancels the running Movie Render Queue job (render_chunks.py calls it when a chunk would overrun its hold)."""
import unreal

sub = unreal.get_editor_subsystem(unreal.MoviePipelineQueueSubsystem)
ex = sub.get_active_executor()
if ex:
    ex.cancel_all_jobs()
print("render cancel", bool(ex))
