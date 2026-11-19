"""Read-only authored nested button geometry; no PIE or widget changes."""
import json
from pathlib import Path
import unreal
assert unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world() is None
paths=['/Game/FoA/UI/Widgets/Common/WBP_SandButton','/Game/FoA/Gameplay/Encounter/WBP_Encounter']
out=[]
for path in paths:
    bp=unreal.load_asset(path)
    tree=unreal.find_object(bp,'WidgetTree')
    names=('SizeBox_0','Btn_Hit','Ovl_Face','Ret_Sand','Ovl_Glyphs','Txt_Label') if path==paths[0] else ('Btn_Act0','Btn_Act1','Btn_Act2')
    for name in names:
        widget=unreal.find_object(tree,name);assert widget,(path,name)
        row=dict(asset=path,name=name,class_name=widget.get_class().get_name())
        for prop in ('LabelSize','bPlainLabel','wrap_text_at','auto_wrap_text','font','min_desired_width','width_override','height_override','content_padding'):
            try:row[prop]=str(widget.get_editor_property(prop))
            except Exception:pass
        slot=widget.get_editor_property('slot')
        if slot:
            row['slot']=dict(class_name=slot.get_class().get_name())
            for prop in ('padding','horizontal_alignment','vertical_alignment','size'):
                try:row['slot'][prop]=str(slot.get_editor_property(prop))
                except Exception:pass
        out.append(row)
target=Path('P:/FoA/Saved/Integration/cv_card_style/authored_geometry.json')
target.parent.mkdir(parents=True,exist_ok=True);target.write_text(json.dumps(out,indent=2))
print(json.dumps(out))
