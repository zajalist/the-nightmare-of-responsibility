"""PIE checks for the T2-T6 chain, run between editor ticks while PIE plays (start PIE with Hayba first):
  python Tools/Unreal/ue_remote.py Tools/Unreal/gameplay/pie_test.py FOA_STEP=<step> [FOA_ROUTE=A|B]
Steps (comma-separated, run in order within one call): aim:<Label> walks the player in front of an actor and aims the camera at it, so the real 0.1 s scan picks it;
       use:<Label> focuses that actor and presses Interact, like the E key; state prints every actor's state and the
       inventory. Each call returns at once; let PIE tick (~0.3 s) between calls."""
import os

import unreal

world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
assert world, "PIE is not running"
pawn = unreal.GameplayStatics.get_player_pawn(world, 0)
I = pawn.get_component_by_class(unreal.load_asset("/Game/FoA/Gameplay/BPC_Interactor").generated_class())
INV = pawn.get_component_by_class(unreal.load_asset("/Game/FoA/Gameplay/BPC_Inventory").generated_class())
assert I and INV, f"{pawn.get_name()} lacks the interactor or inventory"
BASE = unreal.load_asset("/Game/FoA/Gameplay/BP_Interactable").generated_class()


def find(label):
    for a in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor):
        if a.get_actor_label() == label:
            return a
    raise KeyError(label)


def report():
    print("FOCUS", I.get_editor_property("Target").get_actor_label() if I.get_editor_property("Target") else None,
          "VERB", I.get_editor_property("Verb"), "PROMPT", I.get_editor_property("Prompt"))
    print("INVENTORY", list(INV.get_editor_property("Items")), "SELECTED", INV.get_editor_property("Selected"))
    for a in unreal.GameplayStatics.get_all_actors_of_class(world, BASE):
        print("STATE", a.get_actor_label(), a.get_editor_property("State"))


for step in os.environ.get("FOA_STEP", "state").split(","):
    verb, _, label = step.partition(":")
    if verb == "aim":
        target = find(label)
        origin, extent = target.get_actor_bounds(False)
        stand = origin + (unreal.Vector(0.0, 0.0, 0.0) - unreal.Vector(origin.x, origin.y, 0.0)).normal() * 110.0
        stand.z = 96.0
        pawn.set_actor_location(stand, False, True)
        look = unreal.MathLibrary.find_look_at_rotation(stand + unreal.Vector(0.0, 0.0, 60.0), origin)
        pawn.get_controller().set_control_rotation(look)
        pawn.set_actor_rotation(unreal.Rotator(0.0, 0.0, look.yaw), True)
        print("aimed at", label, "from", stand)
    elif verb == "use":
        I.call_method("SetFocus", (find(label),))
        I.call_method("Interact")
        print("used", label, "->", find(label).get_editor_property("State"),
              "| inventory", list(INV.get_editor_property("Items")))
report()
