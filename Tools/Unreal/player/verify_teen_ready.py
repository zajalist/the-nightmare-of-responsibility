"""Check runtime defaults and remove the obsolete MH facial track from the wake sequence."""
import unreal
P='/Game/FoA/Characters/Player'
bp=unreal.load_asset(P+'/BP_FoAPlayer')
sds=unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem);lib=unreal.SubobjectDataBlueprintFunctionLibrary
parts={}
for h in sds.k2_gather_subobject_data_for_blueprint(bp):
    d=lib.get_data(h);parts.setdefault(str(lib.get_variable_name(d)),lib.get_object_for_blueprint(d,bp))
for n in ('Body','Face','StartOutfit','StartPants','StartSocks','Shirt','Trousers','Socks','Suit','BootsWornMesh'):
    c=parts[n];m=c.get_skeletal_mesh_asset();assert m and '/Teen/' in m.get_path_name(),(n,m)
    print(n,m.get_name(),str(c.get_editor_property('relative_scale3d')),c.get_editor_property('anim_class'))
assert parts['Face'].get_editor_property('custom_depth_stencil_value')==4
print('Source',parts['Mesh'].get_editor_property('animation_mode'),parts['Mesh'].get_editor_property('anim_class'))
seq=unreal.load_asset('/Game/FoA/Cinematics/LS_WakeUp')
for b in seq.get_bindings():
    if str(b.get_display_name())=='Face':
        for t in list(b.get_tracks()):
            print('Face track',t.get_class().get_name())
            if isinstance(t,unreal.MovieSceneSkeletalAnimationTrack):
                b.remove_track(t)
                print('Removed MetaHuman-only face animation; CopyPose and ARKit are owned by player')
assert unreal.EditorAssetLibrary.save_loaded_asset(seq,False)
print('Teen runtime defaults verified')
