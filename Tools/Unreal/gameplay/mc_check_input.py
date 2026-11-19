"""mech_core: print what IMC_Default maps for IA_Interact and IA_CycleVerb (UE 5.8 moved mappings into DefaultKeyMappings)."""
import unreal

imc = unreal.load_asset("/Game/Input/IMC_Default")
for prop in ("default_key_mappings", "mappings"):
    try:
        v = imc.get_editor_property(prop)
    except Exception as e:  # report which layout this engine uses
        print(prop, "n/a", e)
        continue
    rows = v.get_editor_property("mappings") if hasattr(v, "get_editor_property") and not isinstance(v, unreal.Array) else v
    for m in rows:
        a = m.get_editor_property("action")
        if a and a.get_name() in ("IA_Interact", "IA_CycleVerb", "IA_Jump"):
            print(prop, a.get_name(), m.get_editor_property("key").get_editor_property("key_name"))
