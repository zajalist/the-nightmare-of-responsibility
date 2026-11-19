"""Shared bits for the MPFB (MakeHuman for Blender) character scripts. Run them with the portable Blender:
  P:/FoA-Assets/_tools/blender-5.2.3-windows-x64/blender.exe -b --python Tools/MPFB/<script>.py -- <args>
That Blender has its own config ("portable" folder), so MPFB and its asset packs never touch the user's Blender."""
import importlib
import os
import sys

BLENDER = "P:/FoA-Assets/_tools/blender-5.2.3-windows-x64/blender.exe"
ASSETS = "P:/FoA-Assets/character/mpfb"
SHOTS = "P:/FoA/Saved/CharacterShots/mpfb"


def mpfb(module, name):
    """MPFB is an extension, so its package name is bl_ext.<repo>.mpfb; find it by suffix (MPFB's own sample idiom)."""
    for mod in list(sys.modules):
        if mod.endswith("mpfb." + module):
            return getattr(importlib.import_module(mod), name)
    raise ImportError("MPFB module not loaded: " + module + " (is the extension enabled in the portable Blender?)")


def args():
    """Arguments after Blender's '--'."""
    return sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def ensure_dir(path):
    os.makedirs(path, exist_ok=True)
    return path
