"""Show/hide fireplace parts:  ue_remote.py Tools/Fireplace/fp_visible.py FOA_SHOW=Surround,Hearth   (others hidden)"""
import os

import unreal

show = {s for s in os.environ.get("FOA_SHOW", "").split(",") if s}
for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
    lab = a.get_actor_label()
    if lab.startswith("Fireplace_"):
        on = lab[len("Fireplace_"):] in show or "all" in show
        a.static_mesh_component.set_visibility(on)
        print(lab, "visible" if on else "hidden")
