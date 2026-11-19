"""Review render of LS_WakeUp through Movie Render Queue (PIE executor), one frame range per run:
  $env:FOA_EXCLUSIVE='1'  (a PIE window: the first 3 minutes of every 10, 60 s or less)
  python Tools/Unreal/ue_remote.py Tools/Unreal/cine/render_ls.py FOA_RANGE=0-300 [FOA_RES=1920x1080] [FOA_OUT=dir]
PNG frames land in FOA_OUT (default Saved/Cinematics/wakeup_v3_frames) as LS_WakeUp.<frame>.png; ffmpeg joins them.
Game mode override: MoviePipelineGameMode, so no front end, HUD or menu exists in the render world.
The run only queues and starts the render; "[cine] render done <ok>" in the log marks the end."""
import os

import unreal

SEQ = "/Game/FoA/Cinematics/LS_WakeUp.LS_WakeUp"
MAP = "/Game/FoA/Maps/L_Tutorial_Bedroom.L_Tutorial_Bedroom"
OUT = os.environ.get("FOA_OUT", "P:/FoA/Saved/Cinematics/wakeup_v3_frames")
F0, F1 = [int(x) for x in os.environ.get("FOA_RANGE", "0-1092").split("-")]
W_, H_ = [int(x) for x in os.environ.get("FOA_RES", "1920x1080").split("x")]
SAMPLES = int(os.environ.get("FOA_SAMPLES", "4"))

sub = unreal.get_editor_subsystem(unreal.MoviePipelineQueueSubsystem)
if sub.is_rendering():
    raise RuntimeError("a render is already running")
queue = sub.get_queue()
queue.delete_all_jobs()
job = queue.allocate_new_job(unreal.MoviePipelineExecutorJob)
job.set_editor_property("job_name", "cine_wakeup_%d_%d" % (F0, F1))
job.set_editor_property("sequence", unreal.SoftObjectPath(SEQ))
job.set_editor_property("map", unreal.SoftObjectPath(MAP))
cfg = job.get_configuration()
out = cfg.find_or_add_setting_by_class(unreal.MoviePipelineOutputSetting)
out.set_editor_property("output_directory", unreal.DirectoryPath(OUT))
out.set_editor_property("output_resolution", unreal.IntPoint(W_, H_))
out.set_editor_property("file_name_format", "{sequence_name}.{frame_number}")
out.set_editor_property("zero_pad_frame_numbers", 4)
out.set_editor_property("use_custom_playback_range", True)
out.set_editor_property("custom_start_frame", F0)
out.set_editor_property("custom_end_frame", F1)
if os.environ.get("FOA_FPS"):  # draft: fewer frames per second of film (the editor renders at ~2 frames/s under PIE)
    out.set_editor_property("use_custom_frame_rate", True)
    out.set_editor_property("output_frame_rate", unreal.FrameRate(int(os.environ["FOA_FPS"]), 1))
cfg.find_or_add_setting_by_class(unreal.MoviePipelineDeferredPassBase)
cfg.find_or_add_setting_by_class(unreal.MoviePipelineImageSequenceOutput_PNG)
aa = cfg.find_or_add_setting_by_class(unreal.MoviePipelineAntiAliasingSetting)
aa.set_editor_property("spatial_sample_count", 1)
aa.set_editor_property("temporal_sample_count", SAMPLES)
# 32 warm-up frames cost ~40 s of a 60 s EXCLUSIVE hold (02:21 test); 8 let Lumen settle, exposure is manual
aa.set_editor_property("engine_warm_up_count", int(os.environ.get("FOA_WARMUP", "8")))
go = cfg.find_or_add_setting_by_class(unreal.MoviePipelineGameOverrideSetting)
go.set_editor_property("cinematic_quality_settings", False)  # render at the scalability players get (cheaper than Cinematic)


def done(executor, ok):
    unreal.log("[cine] render done %s %s" % (ok, OUT))


executor = sub.render_queue_with_executor(unreal.MoviePipelinePIEExecutor)
executor.on_executor_finished_delegate.add_callable(done)
print("render queued", F0, F1, W_, H_, OUT)
