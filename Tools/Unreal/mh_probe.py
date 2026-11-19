"""Probe what MetaHuman Creator can do without the optional Core Data (one short run inside the editor lock).

  python Tools/Unreal/ue_remote.py Tools/Unreal/mh_probe.py

Leaves nothing behind (the user's clean-up rule): the test character is created in the transient package as
TMP_character_MHC_Probe and is never saved, so there is no asset to delete afterwards.
Reports: the MetaHuman Python classes, the editor subsystem's functions, whether a character can be opened for
editing, its parametric body constraints and whether it can build.
"""
import unreal


def run():
    print("MH_PROBE classes:", [n for n in ("MetaHumanCharacter", "MetaHumanCharacterFactoryNew",
                                             "MetaHumanCharacterEditorSubsystem") if hasattr(unreal, n)])
    char = unreal.new_object(unreal.MetaHumanCharacter, outer=unreal.get_transient_package(),
                             name="TMP_character_MHC_Probe")
    print("MH_PROBE transient character:", char.get_path_name() if char else None)
    sub = unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)
    print("MH_PROBE subsystem functions:", sorted(m for m in dir(sub) if not m.startswith("_") and "_" in m)[:80])
    try:  # Python signatures are undocumented: report instead of aborting
        added = sub.try_add_object_to_edit(char)
    except Exception as e:
        added = False
        print("MH_PROBE add error:", e)
    print("MH_PROBE added for editing:", added)
    if added:
        try:
            cons = sub.get_body_constraints(char)
            print("MH_PROBE body constraints:", len(cons),
                  [(str(c.get_editor_property("name")), round(c.get_editor_property("target_measurement"), 1),
                    round(c.get_editor_property("min_measurement"), 1), round(c.get_editor_property("max_measurement"), 1))
                   for c in cons][:40])
        except Exception as e:
            print("MH_PROBE constraints error:", e)
        try:
            print("MH_PROBE can build:", sub.can_build_meta_human(char))
        except Exception as e:
            print("MH_PROBE can_build error:", e)
        sub.remove_object_to_edit(char)
    print("MH_PROBE done, nothing saved")


run()
