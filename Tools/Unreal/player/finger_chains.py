"""Finger-chain rules shared by every FoA retargeter (imported by retarget_ual.py and hero_retarget.py).
FUZZY auto-mapping paired Manny's metacarpal chains with the source finger chains (LeftIndexMetacarpal <- LeftIndex),
so each finger's curl was applied twice, once at the metacarpal and again along the phalanges: over-clenched,
sideways-bent fingers. Rules:
  - a metacarpal chain may only be fed by a metacarpal chain (Manny -> Manny-hierarchy hero keeps them; UAL/Mixamo
    sources have none, so there the metacarpals stay unmapped and hold the rest pose);
  - phalanges 3-to-3 with One-to-One rotation, thumb included (thumb_01 is the CMC joint on every rig used here)."""
import unreal

FINGERS = ("Thumb", "Index", "Middle", "Ring", "Pinky")


def fix_fingers(c):
    """c: IKRetargeterController. Returns (unmapped metacarpals, one-to-one finger chains) for the log."""
    unmapped = []
    for side in ("Left", "Right"):
        for f in FINGERS[1:]:
            chain = f"{side}{f}Metacarpal"
            src = str(c.get_source_chain(chain))
            if src != "None" and "Metacarpal" not in src:
                c.set_source_chain("None", chain)
                unmapped.append(chain)
    fk = c.get_op_controller(c.get_index_of_op_by_name("FK Chains"))
    s = fk.get_settings()
    chains = list(s.get_editor_property("chains_to_retarget"))
    done = []
    for ch in chains:
        name = str(ch.get_editor_property("target_chain_name"))
        if any(f in name for f in FINGERS) and "Metacarpal" not in name:
            ch.set_editor_property("rotation_mode", unreal.FKChainRotationMode.ONE_TO_ONE)
            done.append(name)
    s.set_editor_property("chains_to_retarget", chains)
    fk.set_settings(s)
    return unmapped, done
