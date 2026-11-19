"""ABP_FoAPlayer locomotion state machine through Hayba's C++ anim tools (Hayba first), driven over TCP.
  python Tools/Unreal/player/hayba_abp_states.py      (plain Python, outside the editor; hold your lease first)
Adds Jog and TurnInPlace to the template's Locomotion machine, wires the transitions with their rules, compiles.
Re-runnable: existing states/transitions are reported by Hayba and skipped. Then run build_abp.py FOA_STEP=states."""
import json
import sys

sys.path.insert(0, "P:/FoA/Tools/Unreal")
from hayba_call import call  # noqa: E402

ABP = "/Game/FoA/Characters/Player/ABP_FoAPlayer"
SM = "Locomotion"
STATES = ["Jog", "TurnInPlace"]
RULES = [  # (from, to, condition) - variables live on ABP_FoAPlayer (pushed by the pawn / computed in its update)
    ("Walk / Run", "Jog", "IsJogging && GroundSpeed > 150"),
    ("Jog", "Walk / Run", "!IsJogging"),
    ("Jog", "Idle", "!ShouldMove"),
    ("Idle", "TurnInPlace", "YawRate > 60 || YawRate < -60"),
    ("TurnInPlace", "Idle", "YawRate < 15 && YawRate > -15"),
    ("TurnInPlace", "Walk / Run", "ShouldMove"),
]


def ok(resp):
    return isinstance(resp, dict) and resp.get("ok", True) and not resp.get("error")


def main():
    info = call("anim_blueprint_get_info", {"path": ABP})
    have = json.dumps(info)
    for st in STATES:
        if f'"{st}"' not in have:
            r = call("anim_blueprint_add_state", {"path": ABP, "state_machine_name": SM, "new_state_name": st})
            print("add_state", st, r)
    body = info.get("result", info)
    if isinstance(body, dict) and "content" in body:  # MCP-style envelope: the JSON sits in content[0].text
        body = json.loads(body["content"][0]["text"])
    pairs = {(t["from"], t["to"]) for sm in body.get("state_machines", []) if sm.get("name") == SM for t in sm.get("transitions", [])}
    for a, b, cond in RULES:
        if (a, b) not in pairs:  # add_transition is not idempotent
            r = call("anim_blueprint_add_transition", {"path": ABP, "from_state": a, "to_state": b, "state_machine_name": SM})
            print("transition", a, "->", b, r)
        r = call("anim_blueprint_set_condition", {"path": ABP, "from_state": a, "to_state": b, "condition_expression": cond})
        print("  condition", cond, r)
    r = call("anim_blueprint_compile", {"path": ABP})
    print("compile", r)
    sys.exit(0 if ok(r) else 1)


main()
