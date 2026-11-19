"""Read live hit-test prerequisites after a real mouse attempt; no delegates."""
import json
from pathlib import Path
import unreal
import ctypes
from ctypes import wintypes
w=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world();assert w
path='/Game/FoA/Level2/Journey/BP_L2Journey.BP_L2Journey_C'
j=unreal.GameplayStatics.get_actor_of_class(w,unreal.load_class(None,path));assert j
hud=j.get_editor_property('InterviewHUD');assert hud
pc=unreal.GameplayStatics.get_player_controller(w,0)
result=dict(journey_valid=unreal.SystemLibrary.is_valid(hud.get_editor_property('Journey')),
    journey_matches=hud.get_editor_property('Journey')==j,
    ready=j.get_editor_property('DialogueReady'),held=j.get_editor_property('DialogueHeld'),
    mode=j.get_editor_property('DialogueMode'),response=j.get_editor_property('DialogueState'),
    selected=j.get_editor_property('DialogueSelected'),show_cursor=pc.get_editor_property('show_mouse_cursor'),
    mouse=str(pc.get_mouse_position()),widgets=[],buttons=[])
point=wintypes.POINT();clip=wintypes.RECT()
ctypes.windll.user32.GetCursorPos(ctypes.byref(point));ctypes.windll.user32.GetClipCursor(ctypes.byref(clip))
result.update(desktop_cursor=[point.x,point.y],cursor_clip=[clip.left,clip.top,clip.right,clip.bottom])
for widget in unreal.ObjectIterator(unreal.UserWidget):
    if widget.get_world()==w and widget.is_in_viewport():result['widgets'].append(dict(name=widget.get_name(),type=widget.get_class().get_name(),
        visibility=str(widget.get_visibility()),enabled=widget.get_is_enabled(),opacity=widget.get_render_opacity()))
for i in range(3):
    button=hud.get_editor_property('Btn_Answer'+str(i))
    result['buttons'].append(dict(index=i,visibility=str(button.get_visibility()),enabled=button.get_is_enabled(),
        hovered=button.is_hovered(),pressed=button.is_pressed(),click_method=str(button.get_editor_property('click_method'))))
Path('P:/FoA/Saved/Integration/city_ui/mouse_live.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result))
