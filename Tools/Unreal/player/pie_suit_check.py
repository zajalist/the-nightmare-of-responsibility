"""Inject into the coordinator's running free-roam PIE; 18-second suit/body/animation proof, no PIE stop."""
import json
from pathlib import Path
import time
import unreal

OUT = Path("P:/FoA/Saved/CharacterShots/suit_runtime")
OUT.mkdir(parents=True, exist_ok=True)
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
player = unreal.GameplayStatics.get_player_character(world, 0)
pc = unreal.GameplayStatics.get_player_controller(world, 0)
assert player and pc, "Inject after free roam starts"
parts = {c.get_name(): c for c in player.get_components_by_class(unreal.SkeletalMeshComponent)}
body = parts["Body"]
starter = parts["StartOutfit"]
suit = parts["Suit"]
original_mesh = body.get_skeletal_mesh_asset()
original_class = body.get_anim_instance().get_class()
original_rotation = pc.get_control_rotation()
initial_location = player.get_actor_location()
state = {"t0": time.time(), "handle": None, "stage": 0, "shots": [], "passed": False}


def shot(label):
    unreal.SystemLibrary.execute_console_command(world, f"Shot showui filename={OUT.as_posix()}/{label}.png nosuffix")
    state["shots"].append({"label": label, "wall": time.time()})


def finish(error=None):
    player.call_method("UnequipAll")
    player.call_method("SetBattle", (False,))
    pc.set_control_rotation(original_rotation)
    if state["handle"] is not None:
        unreal.unregister_slate_post_tick_callback(state["handle"])
        state["handle"] = None
    state["error"] = str(error) if error else None
    OUT.parent.joinpath("suit_runtime.json").write_text(json.dumps({k: v for k, v in state.items() if k != "handle"}, indent=2))
    unreal.log("[suit-proof] " + ("PASS" if state["passed"] else "FAIL " + str(error)))


def tick(dt):
    elapsed = time.time() - state["t0"]
    try:
        if state["stage"] == 0:
            player.call_method("UnequipAll")
            player.call_method("Equip", ("Suit",))
            assert suit.is_visible() and not starter.is_visible()
            assert body.get_skeletal_mesh_asset().get_name() == "SK_FoA_Body_Suited"
            assert body.get_anim_instance().get_class() == original_class, "Body retarget AnimBP changed"
            pc.set_control_rotation(unreal.Rotator(roll=0, pitch=-7, yaw=player.get_actor_rotation().yaw + 145))
            state["stage"] = 1
        elif elapsed > 2.0 and state["stage"] == 1:
            shot("suited_still")
            state["stage"] = 2
        elif 3.0 < elapsed < 5.0:
            player.add_movement_input(player.get_actor_forward_vector(), 0.4)
            if elapsed > 4.0 and state["stage"] == 2:
                shot("suited_walk")
                state["stage"] = 3
        elif elapsed > 6.0 and state["stage"] == 3:
            state["walk_cm"] = (player.get_actor_location() - initial_location).length()
            player.call_method("SetBattle", (True,))
            state["stage"] = 4
        elif elapsed > 8.0 and state["stage"] == 4:
            shot("suited_battle_idle")
            state["stage"] = 5
        elif elapsed > 10.0 and state["stage"] == 5:
            player.call_method("SetBattle", (False,))
            player.call_method("UnequipAll")
            assert body.get_skeletal_mesh_asset() == original_mesh
            assert body.get_anim_instance().get_class() == original_class
            assert not suit.is_visible() and starter.is_visible()
            state["stage"] = 6
        elif elapsed > 12.0 and state["stage"] == 6:
            shot("starter_restored")
            state["passed"] = True
            finish()
        elif elapsed > 18.0:
            raise AssertionError("Suit proof did not finish its stages")
    except Exception as error:
        finish(error)


state["handle"] = unreal.register_slate_post_tick_callback(tick)
unreal.log("[suit-proof] registered; no asset changes and no PIE stop")
