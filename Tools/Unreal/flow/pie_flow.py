"""Drives BP_BeatDirector inside a running PIE session (mech_flow tests; keep PIE runs under 45 s).
    python Tools/Unreal/ue_remote.py Tools/Unreal/flow/pie_flow.py FOA_PIE=start
    python Tools/Unreal/ue_remote.py Tools/Unreal/flow/pie_flow.py "FOA_PIE=reset;begin;ev:PhoneWakeUp;state"
Commands (';'-separated, run in order within one editor tick): start, stop, reset (GI.ResetProgress), begin
(BeginMorning; GI_FoA's QA slot, never the player's save), wake (front end FinishWake), ev:<Event> (ReportEvent), fail (FailDay), restart (RestartDay), title (ResetToTitle), state."""
import os

import unreal
import importlib
import sys
sys.path.insert(0, 'P:/FoA/Tools/Unreal/flow')
import proof_save  # noqa: E402  the player's save stays untouched (main's rule 2026-11-10)
importlib.reload(proof_save)

CMDS = [c for c in os.environ.get('FOA_PIE', 'state').split(';') if c]


def world():
    return unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()


def state(d, gi):
    beat = d.get_editor_property('Beat')
    frame = d.get_editor_property('DoorFrame')
    pc = unreal.GameplayStatics.get_player_controller(world(), 0)
    vt = pc.get_view_target() if pc else None
    print('STATE beat=%s idx=%d day=%d known=%s ticked=%s topdown=%s rolling=%s view=%s frame=%s notebook=%s' % (
        beat.get_editor_property('Id') if beat else None, d.get_editor_property('BeatIndex'),
        gi.get_editor_property('DayCount'), sorted(str(k) for k in gi.get_editor_property('Knowledge')),
        list(d.get_editor_property('TasksTicked')), d.get_editor_property('bTopDown'),
        d.get_editor_property('bRollingOver'), vt.get_name() if vt else None,
        frame.get_actor_location() if frame else None, [str(t) for t in (gi.get_editor_property('Notebook') or [])]))


def main():
    les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    if CMDS == ['start']:
        les.editor_request_begin_play()
        print('PIE requested')
        return
    if CMDS == ['stop']:
        if world() and str(unreal.GameplayStatics.get_game_instance(world()).get_editor_property('SaveSlot')) == proof_save.QA_SLOT:
            proof_save.restore(world())
        les.editor_request_end_play()
        print('PIE stop requested')
        return
    w = world()
    assert w, 'no PIE world'
    d = unreal.GameplayStatics.get_actor_of_class(w, unreal.load_class(None, '/Game/FoA/Gameplay/BP_BeatDirector.BP_BeatDirector_C'))
    gi = unreal.GameplayStatics.get_game_instance(w)
    proof_save.isolate(w)  # every command, 'reset' included, works on the QA slot, never the player's save
    print('director', d, 'gi', gi.get_class().get_name())
    for c in CMDS:
        if c == 'reset':
            gi.call_method('ResetProgress')
        elif c == 'begin':
            d.call_method('BeginMorning')
        elif c == 'beats':  # T0 straight away, skipping the 16 s wake-up cinematic (persistence burst)
            d.call_method('StartMorningBeats')
        elif c == 'wake':  # the UI lane's real hand-off (menu camera off, gameplay, then BeginMorning); fallback BeginMorning
            fe = unreal.GameplayStatics.get_actor_of_class(w, unreal.load_class(None, '/Game/FoA/UI/Framework/BP_FoAFrontEnd.BP_FoAFrontEnd_C'))
            fe.call_method('FinishWake') if fe else d.call_method('BeginMorning')
            print('wake via', 'BP_FoAFrontEnd.FinishWake' if fe else 'BeginMorning')
        elif c.startswith('ev:'):
            d.call_method('ReportEvent', (c[3:],))
        elif c == 'fail':
            d.call_method('FailDay')
        elif c == 'restart':
            d.call_method('RestartDay')
        elif c == 'title':
            d.call_method('ResetToTitle')
        elif c == 'state':
            state(d, gi)
        print('did', c)


main()
