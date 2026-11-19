"""Focused PIE-only phone setup/readback. Invoked only in the coordinator's short proof window."""
import json
import os
from pathlib import Path
import unreal


def main():
    world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world();assert world
    find=lambda p:unreal.GameplayStatics.get_actor_of_class(world,unreal.load_class(None,p))
    fe=find('/Game/FoA/UI/Framework/BP_FoAFrontEnd.BP_FoAFrontEnd_C')
    phone=find('/Game/FoA/UI/Game/BP_Phone.BP_Phone_C')
    director=find('/Game/FoA/Gameplay/BP_BeatDirector.BP_BeatDirector_C')
    pawn=unreal.GameplayStatics.get_player_pawn(world,0);pc=unreal.GameplayStatics.get_player_controller(world,0)
    phase=os.environ.get('PHONE_PHASE','read')
    if phase=='setup':
        gi=unreal.GameplayStatics.get_game_instance(world)
        assert not hasattr(unreal,'_foa_phone_progress_restore')
        unreal._foa_phone_progress_restore=(gi,(str(gi.get_editor_property('SaveSlot')),set(gi.get_editor_property('Knowledge')),list(gi.get_editor_property('Notebook'))))
        gi.call_method('SetProofProgressContext',('FoA_QA_PhoneLayout',set(),[]))
        fe.call_method('OnSplashFinished')
    if phase=='cleanup':
        long_saved=getattr(unreal,'_foa_phone_long_restore',None)
        if long_saved:
            long_saved[0].set_text(long_saved[1]);del unreal._foa_phone_long_restore
        saved=getattr(unreal,'_foa_phone_progress_restore',None)
        if saved:
            saved[0].call_method('SetProofProgressContext',saved[1])
            unreal.GameplayStatics.delete_game_in_slot('FoA_QA_PhoneLayout',0)
            del unreal._foa_phone_progress_restore
        return
    if phase=='title':fe.call_method('OnTitleConfirmed')
    if phase=='start':fe.call_method('WakeUp')
    if phase=='story':
        story=fe.get_editor_property('Story')
        if story and story.is_in_viewport():story.call_method('Finish')
    if phase=='wake':director.call_method('SkipWakeUp')
    if phase=='ready':
        assert director.get_editor_property('BeatIndex')==1,'Still outside free gameplay'
        assert pc.get_view_target()==pawn,'Still viewing cinematic camera'
        assert director.get_editor_property('bWakeDone'),'Wake callbacks are still active'
        assert not pawn.get_editor_property('bCinematic') and not pawn.get_editor_property('bInteractionLocked'),'Player presentation is still locked'
        unreal.SystemLibrary.pause_timer(director,'PollStoryMoment')
        unreal.SystemLibrary.clear_timer(director,'TryStoryMoment')
    if phase=='duplicate':
        phone.call_method('OpenPhone');phone.call_method('OpenPhone')
    screen=phone.get_editor_property('Screen').get_user_widget_object()
    if phase=='long_message':
        text=screen.get_editor_property('Txt_Message');original=text.get_text()
        unreal._foa_phone_long_restore=(text,original)
        text.set_text('\n\n'.join([str(original)]*3))
    if phase=='restore_message':
        saved=unreal._foa_phone_long_restore;saved[0].set_text(saved[1]);del unreal._foa_phone_long_restore
        screen.get_editor_property('MessagesScroll').scroll_to_start()
    body=pawn.get_editor_property('Body');mesh=pawn.get_editor_property('Mesh')
    if phase in ('open','message'):
        def xf(t):return dict(position=list(t.translation.to_tuple()),rotation=list(t.rotation.to_tuple()),scale=list(t.scale3d.to_tuple()))
        bones=[dict(name=str(body.get_bone_name(i)),**xf(body.get_socket_transform(body.get_bone_name(i),unreal.RelativeTransformSpace.RTS_COMPONENT))) for i in range(body.get_num_bones())]
        Path('P:/FoA/Saved/UIShots/phone_grip_body_pose.json').write_text(json.dumps(dict(mesh=body.get_skeletal_mesh_asset().get_path_name(),space='component',world=xf(body.get_world_transform()),bones=bones),indent=1))
        parts={}
        for component in phone.get_components_by_class(unreal.SceneComponent):
            parts[component.get_name()]=dict(world=xf(component.get_world_transform()),relative=xf(component.get_relative_transform()))
            if isinstance(component,unreal.StaticMeshComponent) and component.get_editor_property('static_mesh'):
                box=component.get_editor_property('static_mesh').get_bounding_box()
                parts[component.get_name()]['bounds']=[list(box.min.to_tuple()),list(box.max.to_tuple())]
        Path('P:/FoA/Saved/UIShots/phone_grip_frames.json').write_text(json.dumps(dict(phone=xf(phone.get_actor_transform()),hand=xf(body.get_socket_transform('hand_r')),parts=parts),indent=1))
    if phase=='contact':
        camera=phone.get_editor_property('PhoneCam');t=camera.get_relative_transform()
        Path('P:/FoA/Saved/UIShots/phone_camera_restore.json').write_text(json.dumps(dict(position=list(t.translation.to_tuple()),rotation=list(t.rotation.to_tuple()),scale=list(t.scale3d.to_tuple()))))
        frame=phone.get_actor_transform();target=unreal.MathLibrary.transform_location(frame,unreal.Vector(-7,3,0))
        location=unreal.MathLibrary.transform_location(frame,unreal.Vector(-7,23,-27.5))
        camera.set_world_location_and_rotation(location,unreal.MathLibrary.find_look_at_rotation(location,target),False,False)
    if phase=='restore_contact':
        saved=json.loads(Path('P:/FoA/Saved/UIShots/phone_camera_restore.json').read_text());camera=phone.get_editor_property('PhoneCam')
        camera.set_relative_location_and_rotation(unreal.Vector(*saved['position']),unreal.Quat(*saved['rotation']).rotator(),False,False)
    pos=lambda v:[v.x,v.y,v.z]
    story=fe.get_editor_property('Story')
    data=dict(phase=phase,open=phone.get_editor_property('bOpen'),page=screen.get_editor_property('CurrentPage'),
              story_visible=bool(story and story.is_in_viewport()),sequence_started=bool(director.get_editor_property('SeqPlayer')),
              wake_done=director.get_editor_property('bWakeDone'),
              message_index=screen.get_editor_property('MessageIndex'),reading=screen.get_editor_property('bReadingMessage'),
              ignored_move=pc.is_move_input_ignored(),ignored_look=pc.is_look_input_ignored(),
              cinematic=pawn.get_editor_property('bCinematic'),phone_position=pos(phone.get_actor_location()),
              pawn_position=pos(pawn.get_actor_location()),hand_position=pos(body.get_socket_location('hand_r')),
              montage=str(mesh.get_anim_instance().get_current_active_montage()),
              message=str(screen.get_editor_property('Txt_Message').get_text()),
              notebook=str(screen.get_editor_property('Txt_Notebook').get_text()),
              label_size=screen.get_editor_property('Btn_Action').get_editor_property('LabelSize'),
              action_label=str(screen.get_editor_property('Btn_Action').get_editor_property('Label')),
              beat=director.get_editor_property('BeatIndex'),view=pc.get_view_target().get_class().get_name(),
              gameplay=fe.get_editor_property('bInGameplay'),interaction_locked=pawn.get_editor_property('bInteractionLocked'))
    if phase in ('open','inbox','message','message_scrolled','notes','closed'):
        def rect(widget):
            geometry=widget.get_paint_space_geometry();size=unreal.SlateLibrary.get_local_size(geometry)
            origin=unreal.SlateLibrary.local_to_absolute(geometry,unreal.Vector2D())
            end=unreal.SlateLibrary.local_to_absolute(geometry,size)
            return [origin.x,origin.y,end.x,end.y]
        names=('Pages','MessagesScroll','Btn_Action','Txt_Controls','Btn_Message0','Btn_Message1','Btn_Message2','Txt_Message')
        trees=[tree for tree in unreal.ObjectIterator(unreal.load_class(None,'/Script/UMG.WidgetTree')) if tree.get_outer()==screen]
        def child(name):
            found=[obj for tree in trees for obj in [unreal.find_object(tree,name)] if obj]
            assert len(found)==1,(name,len(found))
            return found[0]
        data['rectangles']={name:rect(child(name)) for name in names}
        data['message_scroll']=screen.get_editor_property('MessagesScroll').get_scroll_offset()
        if phase=='message_scrolled':assert data['message_scroll']>50,'Long message did not scroll'
        data['geometry_available']=all(data['rectangles'][name][2]>data['rectangles'][name][0] for name in ('Pages','Btn_Action','Txt_Controls'))
        if not data['geometry_available']:
            data['layout_check']='World-space widget exposes zero paint rectangles; use the captured runtime image, not geometric assertions.'
        if phase!='closed' and data['geometry_available']:
            bounds=data['rectangles'];assert bounds['Pages'][3]<=bounds['Btn_Action'][1]+1, 'Page overlaps phone action'
            assert bounds['Btn_Action'][3]<=bounds['Txt_Controls'][1]+1, 'Phone action overlaps controls'
            assert bounds['Txt_Controls'][3]<=1201, 'Phone footer leaves screen'
        if phase=='inbox':
            data['selection_alpha']=[screen.get_editor_property('Txt_Sender'+str(i)).get_render_opacity() for i in range(3)]
            data['selection_color']=[list(screen.get_editor_property('Btn_Message'+str(i)).get_editor_property('background_color').to_tuple()) for i in range(3)]
            assert [i for i,a in enumerate(data['selection_alpha']) if a>.9]==[data['message_index']],data['selection_alpha']
            assert [i for i,c in enumerate(data['selection_color']) if c[0]>2]==[data['message_index']],data['selection_color']
            rt=phone.get_editor_property('Screen').get_render_target()
            if rt:unreal.RenderingLibrary.export_render_target(world,rt,'P:/FoA/Saved/UIShots','phone_flat_inbox.exr')
            assert screen.get_editor_property('Txt_Message').get_parent()==screen.get_editor_property('ReadMessage')
            assert screen.get_editor_property('ReadMessage').get_visibility()==unreal.SlateVisibility.COLLAPSED
            if data['geometry_available']:
                selected=data['rectangles']['Btn_Message'+str(data['message_index'])];clip=data['rectangles']['MessagesScroll']
                assert selected[1]>=clip[1]-1 and selected[3]<=clip[3]+1,'Selected message hidden by clipping'
    Path('P:/FoA/Saved/UIShots/phone_pie_'+phase+'.json').write_text(json.dumps(data,indent=2))
    print('Phone readback',phase,'open',data['open'],'page',data['page'],'reading',data['reading'])


main()
