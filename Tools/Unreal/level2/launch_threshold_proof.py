"""Arm the runtime proof before PIE and wait for the owning runner's start receipt."""
import os
from pathlib import Path
import time
import traceback
import unreal

ROOT = Path('P:/FoA/Saved/Codex/dream_transition')
SCRIPT = Path('P:/FoA/Tools/Unreal/level2/threshold_proof.py')


def arm():
    env = {key: os.environ[key] for key in ('FOA_JOURNEY_CASE', 'FOA_PROOF_REALTIME', 'FOA_CV_FAILURE_RUNS', 'FOA_CV_MOUSE','FOA_PROOF_HEADLESS')}
    nonce = os.environ['FOA_PROOF_NONCE']
    assert len(nonce) == 32 and all(ch in '0123456789abcdef' for ch in nonce)
    receipt = ROOT / f'launch_{nonce}.txt'
    deadline = time.monotonic() + 70
    editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    assert editor.get_game_world() is None

    def tick(_delta):
        if time.monotonic() >= deadline:
            unreal.unregister_slate_post_tick_callback(handle)
            return
        if not receipt.exists() or receipt.read_text() != nonce:
            return
        world = editor.get_game_world()
        if not unreal.SystemLibrary.is_valid(world):
            return
        unreal.unregister_slate_post_tick_callback(handle)
        saved = {key: os.environ.get(key) for key in env}
        try:
            assert 'UEDPIE_' in world.get_path_name() and 'L_Tutorial_Bedroom' in world.get_path_name()
            os.environ.update(env)
            namespace = {'__name__': '__main__', '__file__': str(SCRIPT)}
            exec(compile(SCRIPT.read_text(encoding='utf-8'), str(SCRIPT), 'exec'), namespace)
        except Exception:
            receipt.with_suffix('.error').write_text(traceback.format_exc(), encoding='utf-8')
        finally:
            for key, value in saved.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value

    handle = unreal.register_slate_post_tick_callback(tick)


arm()
