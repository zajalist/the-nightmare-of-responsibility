"""qa lane, read-only: the director's top-down camera timings (answers which camera a QA frame shows)."""
import unreal

w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
d = unreal.GameplayStatics.get_actor_of_class(w, unreal.load_class(None, '/Game/FoA/Gameplay/BP_BeatDirector.BP_BeatDirector_C'))
print({k: d.get_editor_property(k) for k in ('TopDownBlend', 'TopDownHold', 'TopDownHoldKnown')})
