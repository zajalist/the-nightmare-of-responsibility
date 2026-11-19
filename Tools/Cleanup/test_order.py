"""Offline check of delete_assets.ordered_batches: python Tools/Cleanup/test_order.py"""
from delete_assets import ordered_batches

# A references B, B references C; D <-> E is a cycle referenced by A.
deps = {"A": ["B", "D"], "B": ["C"], "C": [], "D": ["E"], "E": ["D"]}
flat = [p for b in ordered_batches(list(deps), deps, 2) for p in b]
assert flat.index("A") < flat.index("B") < flat.index("C"), flat
assert flat.index("A") < flat.index("D") and flat.index("A") < flat.index("E"), flat
assert any({"D", "E"} <= set(b) for b in ordered_batches(list(deps), deps, 2)), "cycle split across batches"
print("ordered_batches ok:", ordered_batches(list(deps), deps, 2))

from delete_assets import declared
assert declared(["/Game/Fab/MetaHuman/X", "/Game/FoA/Characters/Player/P", "/Game/Fab/MetaHumanX"],
                ["/Game/Fab/MetaHuman"]) == ["/Game/Fab/MetaHuman", "/Game/Fab/MetaHumanX", "/Game/FoA/Characters/Player/P"]
print("declared ok")
