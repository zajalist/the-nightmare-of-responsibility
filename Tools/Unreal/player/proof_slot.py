"""Proof drivers never touch the player's save (editor-rules, 2026-11-10): before any game flow, point GI_FoA at the QA
slot ('FoA_QA_Play', reset to the first morning a new player sees); at the end, restore the player's slot and context
from disk and delete the QA slot. The anim PIE drivers call enter_once(S) at the top of every tick and leave(S) in finish.
Mirrors Tools/Unreal/gameplay/pie_play.py."""
import unreal

SLOT = 'FoA_QA_Play'


def _gi():
    w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
    return unreal.GameplayStatics.get_game_instance(w) if w else None


def enter_once(S):
    """Idempotent; True once the QA slot is active (the driver must not run game flow before that)."""
    if S.get('proof_ctx') is not None:
        return True
    g = _gi()
    if g is None:
        return False
    S['proof_ctx'] = (str(g.get_editor_property('SaveSlot')), set(g.get_editor_property('Knowledge')),
                      list(g.get_editor_property('Notebook')))
    g.call_method('SetProofProgressContext', (SLOT, set(), []))
    g.call_method('ResetProgress')  # deletes only the QA slot (SaveSlot now): day 18, nothing known
    assert str(g.get_editor_property('SaveSlot')) == SLOT, 'the proof slot did not take'
    unreal.log('[anim] proof slot %s (player slot %s untouched)' % (SLOT, S['proof_ctx'][0]))
    return True


def leave(S):
    ctx = S.get('proof_ctx')
    g = _gi()
    if ctx is None or g is None:
        return
    try:  # back to the player's slot, reloaded from disk, so any later save rewrites his own values unchanged
        g.call_method('SetProofProgressContext', ctx)
        g.call_method('LoadProgress')
        unreal.GameplayStatics.delete_game_in_slot(SLOT, 0)
    except Exception as e:  # noqa: BLE001
        unreal.log_warning('[anim] proof slot restore: %r' % e)
