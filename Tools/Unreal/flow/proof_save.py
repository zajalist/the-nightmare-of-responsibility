"""Story lane: keep every proof run off the player's save (main's rule, 2026-11-10; the pattern of
Tools/Unreal/gameplay/pie_play.py). A Restart Day proof had advanced the user's FoA.sav from Day 18 to 20.
  isolate(world): remembers the player's slot, knowledge, notebook and day, then GI_FoA.SetProofProgressContext(
                  'FoA_QA_Play', {}, []) and ResetProgress (which now deletes only that slot): day 18, nothing known,
                  the first morning a new player sees. Call it before any game flow (splash, title, wake).
  restore(world, ctx): back to the player's slot, reloaded from disk (or the remembered values when he has no file),
                  his day as it was, and the QA slot deleted.
The context is also written to Saved/StoryShots/proof_ctx.json for runs whose steps are separate scripts
(record_story.sh)."""
import json
from pathlib import Path

import unreal

QA_SLOT = 'FoA_QA_Play'
CTX_FILE = Path('P:/FoA/Saved/StoryShots/proof_ctx.json')


def _gi(world):
    return unreal.GameplayStatics.get_game_instance(world)


def isolate(world):
    g = _gi(world)
    slot = str(g.get_editor_property('SaveSlot'))
    if slot == QA_SLOT:  # already isolated in this PIE session (a multi-step run): keep the player's context from disk
        return json.loads(CTX_FILE.read_text())
    ctx = dict(slot=slot, knowledge=[str(k) for k in g.get_editor_property('Knowledge')],
               notebook=[str(t) for t in (g.get_editor_property('Notebook') or [])], day=g.get_editor_property('DayCount'))
    CTX_FILE.write_text(json.dumps(ctx, indent=1))
    g.call_method('SetProofProgressContext', (QA_SLOT, set(), []))
    g.call_method('ResetProgress')  # SaveSlot is the QA slot now: only that slot is deleted
    assert str(g.get_editor_property('SaveSlot')) == QA_SLOT, 'proof context did not take'
    unreal.log('[proof_save] isolated: player slot %s day %s -> %s' % (slot, ctx['day'], QA_SLOT))
    return ctx


def restore(world, ctx=None):
    if world is None:
        return False
    ctx = ctx or json.loads(CTX_FILE.read_text())
    g = _gi(world)
    g.call_method('SetProofProgressContext', (ctx['slot'], set(unreal.Name(k) for k in ctx['knowledge']),
                                              [unreal.Text(t) for t in ctx['notebook']]))
    # LoadProgress brings his day back from his file. DayCount can't be set on an instance (it raised and skipped the
    # QA-slot delete below), and without a file this PIE game instance is thrown away at PIE end anyway.
    g.call_method('LoadProgress')
    unreal.GameplayStatics.delete_game_in_slot(QA_SLOT, 0)
    unreal.log('[proof_save] restored: %s day %s' % (ctx['slot'], ctx['day']))
    return True
