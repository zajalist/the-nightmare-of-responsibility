"""Level 2 screen-space motion. The persistent threshold owns the post-process component."""

import os
import sys
from pathlib import Path

MATERIAL='/Game/FoA/Level2/Materials/M_PP_L2DreamMotion'
THRESHOLD='/Game/FoA/Level2/Transition/BP_DreamThreshold'
COMPONENT='L2DreamMotion'

CODE=r"""
float motion = 1 - saturate(ReduceMotion);
if (motion < 0.01 || abs(Stencil.r - 200.0) < 0.5) return Scene.rgb;
float2 p = UV - 0.5;
float edge = smoothstep(0.06, 0.61, length(p));
float t = View.GameTime;
float age = t - Impact.z;
float pulse = saturate(Impact.w) * smoothstep(0, 0.10, age) * (1 - smoothstep(0.21, 1.25, age));
float drift = (0.74 + 0.26 * sin(t * 1.48)) * edge;
float2 sway = float2(sin(UV.y * 18.0 + t * 1.56), sin(UV.x * 14.0 - t * 1.28));
float2 at = UV + motion * (sway * (0.0036 * drift + 0.0051 * pulse) + p * pulse * 0.007);
float scan = smoothstep(0.93, 0.993, sin(t * 1.21 + 1.4));
float band = 1 - smoothstep(0.002, 0.018, abs(UV.y - (0.3 + 0.28 * sin(t * 0.81))));
at.x += motion * edge * scan * band * 0.0045;
float2 trail = View.ViewSizeAndInvSize.zw * float2(1.8, 2.4) * (edge * 0.55 + pulse * 1.1) * motion;
#define FOA_SAMPLE(pos) SceneTextureLookup(Parameters, ClampSceneTextureUV(ViewportUVToSceneTextureUV(pos, PPI_PostProcessInput0), PPI_PostProcessInput0), PPI_PostProcessInput0, true).rgb
float3 image = FOA_SAMPLE(at);
float3 echoA = FOA_SAMPLE(at - trail);
float3 echoB = FOA_SAMPLE(at + trail * 0.78);
float blur = saturate(edge * 0.31 + pulse * 0.44) * motion;
return lerp(image, (echoA + echoB) * 0.5, blur);
#undef FOA_SAMPLE
"""


def build_material():
    from build_drive import call,h
    root,name=MATERIAL.rsplit('/',1)
    if not h.call('material_get_info',{'path':MATERIAL}).get('ok'):
        call('material_create',package_path=root,name=name)
        call('material_set_property',material_path=MATERIAL,properties={'domain':'MD_PostProcess'})
        call('object_set_property',path=MATERIAL,properties={'BlendableLocation':'BL_SceneColorAfterTonemapping','BlendablePriority':8})
    expressions=call('material_get_info',path=MATERIAL)['expressions']
    if expressions:
        assert len(expressions)==6,expressions
        custom=next(row for row in expressions if row['class']=='MaterialExpressionCustom')
        call('material_set_node',material_path=MATERIAL,node_id=custom['id'],properties={'Code':CODE})
    else:
        inputs=(('UV','ScreenPosition',{},'ViewportUV'),('Scene','SceneTexture',{'SceneTextureId':'PPI_PostProcessInput0'},0),
                ('Stencil','SceneTexture',{'SceneTextureId':'PPI_CustomStencil'},0),
                ('ReduceMotion','CollectionParameter',{'Collection':'/Game/FoA/PostProcess/MPC_Dream.MPC_Dream','ParameterName':'ReduceMotion'},0),
                ('Impact','CollectionParameter',{'Collection':'/Game/FoA/Level2/Materials/MPC_L2.MPC_L2','ParameterName':'Impact0'},0))
        nodes=[]
        for index,(pin,kind,props,output) in enumerate(inputs):
            node=call('material_add_node',material_path=MATERIAL,expression_class='MaterialExpression'+kind,
                      node_pos=[-580,index*155],properties=props)['node_id']
            nodes.append((pin,node,output))
        custom=call('material_add_node',material_path=MATERIAL,expression_class='MaterialExpressionCustom',node_pos=[-195,80],
                    properties={'Inputs':[{'InputName':row[0]} for row in inputs],'Code':CODE,'OutputType':'CMOT_Float3',
                                'Description':'Dream motion and impact echo'})['node_id']
        for pin,node,output in nodes:
            args={'from_output':output} if isinstance(output,str) else {'from_output_index':output}
            call('material_connect_nodes',material_path=MATERIAL,from_node=node,to_node=custom,to_input=pin,**args)
        call('material_connect_nodes',material_path=MATERIAL,from_node=custom,to_property='EmissiveColor')
        call('material_add_comment',material_path=MATERIAL,text='Dream motion',node_pos=[-640,-75],size=[890,830],color=[.26,.14,.18])
    validation=call('material_validate',material_path=MATERIAL);assert not validation.get('has_errors'),validation
    result=call('material_compile',material_path=MATERIAL);assert not result.get('has_errors'),result
    call('asset_save',asset_paths=[MATERIAL])


def template():
    import unreal as u
    bp=u.load_asset(THRESHOLD)
    u.get_editor_subsystem(u.AssetEditorSubsystem).close_all_editors_for_asset(bp)
    sub=u.get_engine_subsystem(u.SubobjectDataSubsystem)
    lib=u.SubobjectDataBlueprintFunctionLibrary
    data=next(lib.get_data(h) for h in sub.k2_gather_subobject_data_for_blueprint(bp)
              if str(lib.get_variable_name(lib.get_data(h)))==COMPONENT)
    pp=lib.get_object_for_blueprint(data,bp)
    pp.set_editor_property('unbound',True);pp.set_editor_property('blend_weight',0.)
    blend=u.WeightedBlendable();blend.set_editor_property('weight',1.);blend.set_editor_property('object',u.load_asset(MATERIAL))
    blends=u.WeightedBlendables();blends.set_editor_property('array',[blend])
    settings=pp.get_editor_property('settings');settings.set_editor_property('weighted_blendables',blends)
    pp.set_editor_property('settings',settings)
    assert u.EditorAssetLibrary.save_loaded_asset(bp,False)


def install():
    import build_drive as b
    build_material()
    info=b.call('blueprint_get_info',path=THRESHOLD)
    if COMPONENT not in {item['name'] for item in info.get('components',[])}:
        b.call('blueprint_add_component',path=THRESHOLD,component_name=COMPONENT,component_class_path='/Script/Engine.PostProcessComponent')
    b.call('python_exec_file',path=Path(__file__).resolve().as_posix(),env={'FOA_JOB_LOOK':'template'},resources=['asset:'+THRESHOLD])


if __name__=='__main__':
    assert os.environ.get('FOA_JOB_LOOK')=='template'
    template()
