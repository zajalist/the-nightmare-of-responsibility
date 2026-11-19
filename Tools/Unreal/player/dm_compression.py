"""Own Uniform Indexable curve codec required by native distance matching.

Keep this outside imported GASP staging so cleanup cannot replace it with the
default compressed rich-curve codec, which cannot be indexed by distance.
"""
import unreal

PATH='/Game/FoA/Characters/Player/Anims/CC_FoA_DistanceMatching'
CODEC='AnimCurveCompressionCodec_UniformIndexable'


def settings():
    asset=unreal.load_asset(PATH)
    if not asset:
        directory,name=PATH.rsplit('/',1)
        asset=unreal.AssetToolsHelpers.get_asset_tools().create_asset(
            name,directory,unreal.AnimCurveCompressionSettings,unreal.AnimCurveCompressionSettingsFactory())
        assert asset,PATH
    codec=asset.get_editor_property('codec')
    if not codec or codec.get_class().get_name()!=CODEC:
        codec=unreal.new_object(unreal.load_class(None,'/Script/Engine.'+CODEC),outer=asset)
        asset.set_editor_property('codec',codec)
        assert unreal.EditorAssetLibrary.save_loaded_asset(asset,False)
    return asset


def assign(sequence):
    sequence.set_editor_property('curve_compression_settings',settings())


if __name__=='__main__':
    for name in ('Run_Start','Walk_Start','Run_Stop','Walk_Stop'):
        path='/Game/FoA/Characters/Player/Anims/GASP/AS_GASP_M_Relaxed_'+name+'_F_Lfoot'
        sequence=unreal.load_asset(path)
        assert sequence,path
        assign(sequence)
        assert unreal.EditorAssetLibrary.save_loaded_asset(sequence,False)
        assert sequence.get_editor_property('curve_compression_settings').get_editor_property('codec').get_class().get_name()==CODEC
        print('Distance matching compression:',sequence.get_name())

