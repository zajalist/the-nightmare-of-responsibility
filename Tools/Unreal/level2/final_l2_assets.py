"""Short in-editor final graph capture or exact sedan-import cleanup step.

Only finalize_l2_graphs.py invokes this, inside its declared scoped/global lease.
Scan closes loaded target editors without loading an asset; delete is a separate run.
"""
import json
import os
import sys
from pathlib import Path
import unreal
sys.path.insert(0,'P:/FoA/Tools/Unreal/level2')
from final_l2_graph_targets import TARGETS, capture_names

OUT=Path('P:/FoA/Saved/Integration/l2_final_graphs')
OUT.mkdir(parents=True,exist_ok=True)
MATERIALS=tuple('/Game/FoA/Level2/Drive/SM_L2Sedan/SM_L2Sedan/Materials/'+n for n in ('MI_L2Dark','M_L2Flat'))


def capture():
    path=os.environ['FOA_FINAL_BP'];assert path in TARGETS.values(),path
    bp=unreal.load_asset(path);assert bp
    assert bp.get_editor_property('status')==unreal.BlueprintStatus.BS_UP_TO_DATE
    folder=OUT/path.rsplit('/',1)[-1];folder.mkdir(parents=True,exist_ok=True)
    rows=[]
    graphs={graph.get_name():graph for graph in unreal.BlueprintEditorLibrary.list_graphs(bp)}
    for name in capture_names(path,graphs):
        graph=graphs[name]
        editor=unreal.BlueprintGraphEditor.get_graph_editor(graph)
        png=folder/(graph.get_name()+'.png')
        rows.append(dict(graph=graph.get_name(),nodes=len(editor.list_all_nodes()) if editor else 0,png=str(png)))
    (folder/'capture.json').write_text(json.dumps(dict(asset=path,graphs=rows),indent=2))
    print('CAPTURE_MANIFEST',path,len(rows),'graphs; outer runner captures one at a time')


def materials(mode):
    assert mode in ('scan_materials','delete_materials')
    registry=unreal.AssetRegistryHelpers.get_asset_registry()
    registry.scan_paths_synchronous(['/Game/FoA/Level2/Drive/SM_L2Sedan/SM_L2Sedan/Materials'],True)
    options=unreal.AssetRegistryDependencyOptions(include_soft_package_references=True,
        include_hard_package_references=True,include_searchable_names=True,
        include_soft_management_references=True,include_hard_management_references=True)
    previous={}
    if mode=='delete_materials':
        previous={r['path']:r for r in json.loads((OUT/'scan_materials.json').read_text())}
    rows=[]
    for path in MATERIALS:
        row=dict(path=path,exists=unreal.EditorAssetLibrary.does_asset_exist(path))
        rows.append(row)
        if not row['exists']:row['action']='missing';continue
        asset_data=unreal.EditorAssetLibrary.find_asset_data(path)
        row['kind']=str(asset_data.asset_class_path.asset_name)
        row['referencers']=sorted(map(str,registry.get_referencers(path,options) or []))
        row['eligible']=row['kind']=='MaterialInstanceConstant' and not row['referencers']
        if not row['eligible']:row['action']='kept';continue
        if mode=='scan_materials':
            if asset_data.is_asset_loaded():
                unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(asset_data.get_asset())
            row['action']='ready'
        else:
            assert previous.get(path,{}).get('eligible'),('No clean preflight',path)
            # No target asset is loaded by this run before the normal delete API.
            row['deleted']=unreal.EditorAssetLibrary.delete_asset(path)
            disk=Path('P:/FoA/Content'+path[5:]+'.uasset')
            row['action']='deleted' if row['deleted'] and not disk.exists() else 'delete_failed'
            assert row['action']=='deleted',row
    (OUT/(mode+'.json')).write_text(json.dumps(rows,indent=2))
    print(json.dumps(rows))


assert unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world() is None,'No PIE allowed'
mode=os.environ['FOA_FINAL_STEP']
if mode=='capture':capture()
elif mode=='close_capture':
    path=os.environ['FOA_FINAL_BP'];assert path in TARGETS.values(),path
    manifest=json.loads((OUT/path.rsplit('/',1)[-1]/'capture.json').read_text())
    assert manifest['asset']==path and all(Path(row['png']).is_file() for row in manifest['graphs'])
    # The coordinator verified no target editors were open before this pass.
    # Close only this pass's captured asset, preserving every unrelated editor.
    unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(unreal.load_asset(path))
    print('CLOSED_CAPTURE',path)
else:materials(mode)
