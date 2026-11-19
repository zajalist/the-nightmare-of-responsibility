"""One width constraint and backplate for the existing prompt; graph toggles them only during tool sessions."""
import json
P='/Game/FoA/UI/Game/WBP_HUD'
calls=[dict(cmd='ui_build_tree',params=dict(widget_blueprint_path=P,parent_widget_name='Ovl_Frame',tree={
    'class':'SizeBox','name':'Size_ContextPrompt','properties':{'WidthOverride':720.,'bOverride_WidthOverride':False},
    'children':[{'class':'Border','name':'Brd_ToolPrompt','properties':{'Padding':'(Left=0,Top=0,Right=0,Bottom=0)','BrushColor':[0,0,0,0]}}]}))]
calls += [dict(cmd='ui_set_variable',params=dict(widget_blueprint_path=P,widget_name=n,is_variable=True))
          for n in ('Size_ContextPrompt','Brd_ToolPrompt')]
for call in calls:print(json.dumps(call))
