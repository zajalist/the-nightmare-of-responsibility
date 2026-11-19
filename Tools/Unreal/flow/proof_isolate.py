"""Story lane: proof_save as a step for multi-script runs (record_story.sh). FOA_PROOF=isolate (default) right after
PIE begins, FOA_PROOF=restore right before it ends. No-op without a PIE world."""
import importlib
import os
import sys

import unreal

sys.path.insert(0, 'P:/FoA/Tools/Unreal/flow')
import proof_save  # noqa: E402
importlib.reload(proof_save)

w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
mode = os.environ.get('FOA_PROOF', 'isolate')
if w is None:
    print('proof_isolate: no PIE world, nothing to do')
elif mode == 'restore':
    print('proof_isolate: restored', proof_save.restore(w))
else:
    print('proof_isolate: isolated', proof_save.isolate(w)['slot'], '->', proof_save.QA_SLOT)
