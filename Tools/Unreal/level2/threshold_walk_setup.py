"""Grounded route components only; never edits Dream A or room actors.
dreamroom lane: glowing white marks and EXIT doorway, the black-sand fears (hidden until they rise), the dread and
clock audio. Attach, mesh, material, transform and render settings on the Blueprint's component templates only."""
import importlib
import sys
import unreal
sys.path.insert(0,'P:/FoA/Tools/Unreal/level2')
import threshold_data as D
importlib.reload(D)

MARK='/Game/FoA/Level2/Dream/MI_DreamMark'  # M_L2Flat child, HDR white: the marks and the door frame glow under bloom
# Marks sit at z 12: the Dream A carpet splats swell above a few cm and swallowed them.
EXIT_TEXT='/Game/FoA/Level2/Dream/M_DreamExitText'  # unlit font material: the TextRender default is lit and read grey
SOUNDS={'DreadAudio':'/Game/FoA/Audio/MetaSounds/Dream/S_Dream_Heartbeat_Loop_01',
        'TickAudio':'/Game/FoA/Audio/MetaSounds/Clock/S_Clock_TickFast_Loop_01'}


def main():
    assert unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world() is None
    bp=unreal.load_asset(D.BP)
    unreal.get_editor_subsystem(unreal.EditorActorSubsystem).select_nothing()
    unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(bp)
    sub=unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem);lib=unreal.SubobjectDataBlueprintFunctionLibrary
    handles={str(lib.get_variable_name(lib.get_data(h))):h for h in sub.k2_gather_subobject_data_for_blueprint(bp)}
    if 'FearBills' in handles and 'FearCrow' not in handles:  # the bills read as a blob: that slot becomes the crow
        assert sub.rename_subobject(handles['FearBills'],unreal.Text('FearCrow'))
        handles={str(lib.get_variable_name(lib.get_data(h))):h for h in sub.k2_gather_subobject_data_for_blueprint(bp)}
    def obj(name,parent='RouteGuide'):
        assert sub.attach_subobject(handles[parent],handles[name])
        return lib.get_object_for_blueprint(lib.get_data(handles[name]),bp)
    def quiet(c,visible=False):
        c.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION);c.set_editor_property('generate_overlap_events',False)
        c.set_editor_property('cast_shadow',False);c.set_visibility(visible)
    guide=obj('RouteGuide','Root');guide.set_visibility(False,True)
    guide.set_editor_property('relative_location',unreal.Vector())
    cube=unreal.load_asset('/Engine/BasicShapes/Cube')
    for name,at,scale,material in [('GuideBed',(0,45,2),(.32,6.3,.018),'/Game/FoA/Level2/Drive/MI_L2Dark')]+[
        ('Guide'+str(i),(0,y,12),(.3,.6,.03),MARK) for i,y in enumerate(D.GUIDE_Y)]+[(n,at,sc,MARK) for n,at,sc in D.EXIT_FRAME]:
        c=obj(name);c.set_static_mesh(cube);c.set_material(0,unreal.load_asset(material))
        c.set_editor_property('relative_location',unreal.Vector(*at));c.set_editor_property('relative_scale3d',unreal.Vector(*scale))
        quiet(c)
    sign=obj('GuideExit');sign.set_text(unreal.Text('EXIT'));sign.set_world_size(D.EXIT_TEXT[1])
    sign.set_editor_property('relative_location',unreal.Vector(*D.EXIT_TEXT[0]))
    sign.set_editor_property('relative_rotation',unreal.Rotator(pitch=0,yaw=-90,roll=0))
    sign.set_horizontal_alignment(unreal.HorizTextAligment.EHTA_CENTER)
    sign.set_vertical_alignment(unreal.VerticalTextAligment.EVRTA_TEXT_CENTER)
    sign.set_text_material(unreal.load_asset(EXIT_TEXT))
    sign.set_text_render_color(unreal.Color(255,255,255,255));sign.set_visibility(False)
    sign.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
    # Fears: two segment roots so a breath can hide its whole segment in one call.
    for root in ('FearsA','FearsB'):
        r=obj(root,'Root');r.set_editor_property('relative_location',unreal.Vector())
    for i,(name,mesh,material,at,yaw,scale,detail) in enumerate(D.FEARS):
        c=obj(name,'FearsA' if i<len(D.SEGMENTS[0]) else 'FearsB')
        c.set_static_mesh(unreal.load_asset(mesh));c.set_material(0,unreal.load_asset(material))
        c.set_editor_property('relative_location',unreal.Vector(*at))
        c.set_editor_property('relative_rotation',unreal.Rotator(pitch=0,yaw=yaw,roll=0))
        c.set_editor_property('relative_scale3d',unreal.Vector(scale,scale,scale))
        c.set_editor_property('detail_mode',getattr(unreal.DetailMode,'DM_'+detail))  # fewer hands on low tiers
        c.set_editor_property('render_custom_depth',True);c.set_editor_property('custom_depth_stencil_value',5)  # sand pass
        quiet(c)
    for name,path in SOUNDS.items():
        a=obj(name,'FearClock' if name=='TickAudio' else 'Root')
        a.set_editor_property('sound',unreal.load_asset(path));a.set_editor_property('auto_activate',False)
        a.set_editor_property('allow_spatialization',name=='TickAudio')  # the heartbeat is in his head
        a.set_editor_property('volume_multiplier',.12 if name=='DreadAudio' else .8)  # a culled silent start never resumes
        a.set_editor_property('relative_location',unreal.Vector(0,0,8 if name=='TickAudio' else 0))  # parent-scaled: 8 x 6 = 48 cm
    unreal.EditorAssetLibrary.save_loaded_asset(bp,False)
    print('Dream route, fears and audio configured; native compile/save required')


main()
