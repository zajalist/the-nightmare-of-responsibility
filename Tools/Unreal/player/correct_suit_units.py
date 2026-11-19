"""Compatibility entry: use the checked centimetre-native bundle; never compensate skeleton units with import scale."""
from pathlib import Path
exec(compile(Path("P:/FoA/Tools/Unreal/player/reimport_player_units_cm.py").read_text(), "reimport_player_units_cm.py", "exec"))
