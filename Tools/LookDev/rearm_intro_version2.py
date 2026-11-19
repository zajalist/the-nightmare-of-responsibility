"""Coordinator-only final rearm of the current intro version; every other saved preference remains intact."""
import json,unreal
from pathlib import Path
assert not unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).is_in_play_in_editor()
s=unreal.GameplayStatics.load_game_from_slot('Settings',0);assert s
names=['MasterVolume','EffectsVolume','AmbienceVolume','InterfaceVolume','MouseSensitivity','bInvertY','bSubtitles','SubtitleSize','bReduceMotion','bShowPhotoWarning','bSeenIntro']
before={n:s.get_editor_property(n) for n in names};old=s.get_editor_property('IntroVersionSeen')
s.set_editor_property('IntroVersionSeen',1)
assert unreal.GameplayStatics.save_game_to_slot(s,'Settings',0)
check=unreal.GameplayStatics.load_game_from_slot('Settings',0)
assert check.get_editor_property('IntroVersionSeen')==1
assert all(check.get_editor_property(n)==v for n,v in before.items())
Path('P:/FoA/Saved/LookDev/intro_restored/rearm_version2.json').write_text(json.dumps({'old_version':old,'new_version':1,'other_preferences_unchanged':before},indent=1))
print('Only intro version rearmed; all other saved preferences verified unchanged')
