"""Offline input-driver check: a delayed boot cannot turn menu tests into Wake up."""
import json
from pathlib import Path
import tempfile
import time
from unittest.mock import patch

import sweep_intro as sweep


with tempfile.TemporaryDirectory() as out:
    screen, overlay, focus = 'WBP_BootSplash_C', None, 0
    visited, waking = [], False

    def publish():
        ui = [[screen, 'VISIBLE', 1.0]]
        if overlay:
            ui.append([overlay, 'VISIBLE', 1.0])
        Path(out, 'live_state.json').write_text(json.dumps(dict(
            Screen=screen, ui=ui, epoch=time.time(), t=1, bWaking=waking)))

    publish()
    with patch.object(sweep.time, 'sleep', return_value=None):
        for _, key in sweep.regression_steps(out):
            if key is None:
                break
            if screen == 'WBP_BootSplash_C':
                screen = 'WBP_Title_C'
            elif screen == 'WBP_Title_C':
                assert key == 'SpaceBar'
                screen, focus = 'WBP_MainMenu_C', 0
            elif overlay:
                if key in ('Escape', 'Gamepad_FaceButton_Right'):
                    overlay, focus = None, 0
            elif key == 'Down':
                focus += 1
            elif key == 'Escape':
                screen = 'WBP_Title_C'
            elif key == 'Enter':
                if focus in (1, 3):
                    overlay = {1: 'WBP_Settings_C', 3: 'WBP_ConfirmDialog_C'}[focus]
                    visited.append(overlay)
                else:
                    assert visited == ['WBP_Settings_C', 'WBP_ConfirmDialog_C'], visited
                    waking = True
            publish()
    assert waking
    # Missing/stale state ends the run instead of continuing blind or waiting forever.
    with patch.object(sweep.time, 'monotonic', side_effect=[0, 43]):
        try:
            next(sweep.regression_steps(out))
            raise AssertionError('missing timeout')
        except AssertionError as exc:
            assert 'Timed out waiting' in str(exc), exc
print('regression driver: phase gates and deadline passed')
