"""Commit the gameplay fills that passed the PIE variant stills (15:30, light_var3 'mid'): door gap 8 lm, bay moon fill
3 lm, view fill 2 lm (calibrated to the locked EV100 -1: the room's own lamp is 12 lm). Both rect lights Movable
(no lightmap build in this project). ViewFill visible in game again."""
import unreal

EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
A = {a.get_actor_label(): a for a in EAS.get_all_level_actors()}
for label, lm in (('Light_DoorGap', 8.0), ('Light_MoonFill_Bay', 3.0)):
    a = A[label]
    a.root_component.set_mobility(unreal.ComponentMobility.MOVABLE)
    c = a.get_component_by_class(unreal.LightComponent)
    c.set_editor_property('intensity', lm)
    print(label, c.get_editor_property('intensity'), c.get_editor_property('intensity_units'), c.get_editor_property('mobility'))
v = A['ViewFill']
v.set_actor_hidden_in_game(False)
v.set_editor_property('FillLumens', 2.0)
print('ViewFill', v.get_editor_property('FillLumens'), 'hidden', v.is_hidden_ed())
