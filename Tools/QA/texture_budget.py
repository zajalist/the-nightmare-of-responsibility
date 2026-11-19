# Runs inside the editor via ue_remote: dumps the loaded-texture list and streaming pool settings to the log,
# between markers, so Tools/QA/texture_budget_report.py can rank what eats the streaming pool. Read-only.
import unreal

world = unreal.EditorLevelLibrary.get_editor_world()
unreal.log("FOA_TEXBUDGET_BEGIN")
for cv in ("r.Streaming.PoolSize", "r.Streaming.LimitPoolSizeToVRAM", "r.Streaming.UseFixedPoolSize",
           "r.Streaming.MaxTempMemoryAllowed"):
    unreal.SystemLibrary.execute_console_command(world, cv)
unreal.SystemLibrary.execute_console_command(world, "ListTextures")
unreal.log("FOA_TEXBUDGET_END")
