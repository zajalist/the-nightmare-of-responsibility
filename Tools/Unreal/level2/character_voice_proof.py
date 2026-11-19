"""Short proof inside coordinator-owned QA PIE; no save or settings writes."""
import json
from pathlib import Path
import unreal as u

OUT=Path('P:/FoA/Saved/CharacterVoice');OUT.mkdir(parents=True,exist_ok=True)
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
assert world and u.SystemLibrary.is_valid(world),'Owned QA PIE required'
gi=u.GameplayStatics.get_game_instance(world)
gi.call_method('SetProofProgressContext',('FoA_QA_Play',set(),[]))
assert str(gi.get_editor_property('SaveSlot'))=='FoA_QA_Play','Isolate progress before this proof'
front=u.GameplayStatics.get_actor_of_class(world,u.load_class(None,'/Game/FoA/UI/Framework/BP_FoAFrontEnd.BP_FoAFrontEnd_C'))
assert u.SystemLibrary.is_valid(front)
get=lambda name:front.get_editor_property(name)
say=lambda text,speaker=0,emotion=1:front.call_method('SayCharacter',(u.Text(text),speaker,emotion))
paused=u.GameplayStatics.is_game_paused(world)
assert not paused,'Start the proof unpaused'
report={}
try:
    front.call_method('StopCharacterVoice',())
    say('A line only for the voice proof.')
    first=get('VoiceAudio');assert u.SystemLibrary.is_valid(first)
    phrase=get('VoicePhrase');variant=get('VoiceVariant')
    assert not first.get_editor_property('is_ui_sound'),'Dialogue must pause with gameplay'
    assert first.is_playing()
    for _ in range(12):say('A line only for the voice proof.')
    assert get('VoiceAudio')==first and get('VoiceVariant')==variant
    report['duplicate_refreshes']=12
    say('A different reply.',1)
    second=get('VoiceAudio');assert second!=first and u.SystemLibrary.is_valid(second)
    assert not u.SystemLibrary.is_valid(first) or not first.is_playing()
    say('Another player line.')
    assert get('VoicePhrase')!=phrase,'Player alternates despite NPC interruption'
    front.call_method('StopCharacterVoice',())
    assert str(get('VoiceLine'))==''
    stopped=get('VoiceAudio')
    assert not u.SystemLibrary.is_valid(stopped) or not stopped.is_playing()
    u.GameplayStatics.set_game_paused(world,True)
    say('Must not start while paused.')
    assert str(get('VoiceLine'))==''
    u.GameplayStatics.set_game_paused(world,False)
    say('Must not start while paused.')
    assert u.SystemLibrary.is_valid(get('VoiceAudio')) and get('VoiceAudio').is_playing()
    report.update(dedup=True,interruption=True,per_speaker_variation=True,stop=True,paused_gate=True)
    bank=list(get('VoiceBank'));assert len(bank)==30
    dialogue=u.load_asset('/Game/FoA/Audio/Mix/SC_Dialogue')
    assert dialogue.get_editor_property('parent_class')==u.load_asset('/Game/FoA/Audio/Mix/SC_Master')
    assert all(w.get_editor_property('sound_class_object')==dialogue and not w.get_editor_property('looping') for w in bank)
    report.update(sound_class='SC_Dialogue',parent_class='SC_Master',bank_count=30)
finally:
    u.GameplayStatics.set_game_paused(world,paused)
    if u.SystemLibrary.is_valid(front):front.call_method('StopCharacterVoice',())
report['passed']=True
(OUT/'runtime_proof.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print('PASS character voice runtime',json.dumps(report))
