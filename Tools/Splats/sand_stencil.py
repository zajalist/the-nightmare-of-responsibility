"""Stencil 5 (sand) on every sand actor in the open level, for the pp lane's sand-only post pass (stencil table:
1 keep colour, 2 Nightmare tear, 3 focus rim, 4 face blur, 5 sand). Render flags only: never moves anything.
  python Tools/Unreal/ue_remote.py Tools/Splats/sand_stencil.py
"""
import unreal


def run():
    done = []
    for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
        label = a.get_actor_label()
        if not label.startswith(("SandStream_", "SandSplats_", "SandClock_", "SandSpill_", "SandMound_")):
            continue
        for c in a.get_components_by_class(unreal.PrimitiveComponent):
            c.set_render_custom_depth(True)
            c.set_custom_depth_stencil_value(5)
        done.append(label)
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    print("stencil 5 on", done)


run()
