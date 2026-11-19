"""Narrow existing Battle sequence-player edit; run only after coordinator clearance.
FOA_BATTLE_IDLE=inspect (default) | apply. Compile/save ABP natively after apply.
No transitions, shared rig, skeleton, clip keys or sleep assets are edited.
"""
import hashlib,json,os
from pathlib import Path
import unreal
assert not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
P='/Game/FoA/Characters/Player';bp=unreal.load_asset(P+'/ABP_FoAPlayer')
mode=os.environ.get('FOA_BATTLE_IDLE','inspect');assert mode in ('inspect','apply')
clip=unreal.load_asset(P+'/Anims/UAL/UAL_Idle_Loop');assert clip
assert bp.get_editor_property('target_skeleton')==clip.get_editor_property('skeleton')
B=unreal.BlueprintEditorLibrary
graph=next(g for g in B.list_graphs(bp) if g.get_class().get_name()=='AnimationStateGraph' and g.get_name()=='Battle')
ed=unreal.BlueprintGraphEditor.get_graph_editor(graph)
players=[n for n in ed.list_all_nodes() if n.get_class().get_name()=='AnimGraphNode_SequencePlayer'];assert len(players)==1
player=players[0];node=player.get_editor_property('node')
assets=['Content/FoA/Cinematics/LS_WakeUp_ManualPose.uasset','Content/FoA/Cinematics/WakeUp/AS_FoA_Wake_Lying.uasset','Content/FoA/Cinematics/WakeUp/AS_FoA_Wake_EdgeReach.uasset']
hashes=lambda:{p:hashlib.sha256(Path('P:/FoA',p).read_bytes()).hexdigest() for p in assets}
before=hashes();report=dict(mode=mode,battle_node=player.get_path_name(),before=node.export_text(),new_sequence=clip.get_path_name(),protected=before)
if mode=='apply':
    unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(bp)
    node.set_editor_property('sequence',clip);node.set_editor_property('play_rate',1.0);node.set_editor_property('loop_animation',True)
    player.set_editor_property('node',node)
    assert player.get_editor_property('node').get_editor_property('sequence')==clip
    assert hashes()==before
    report.update(after=player.get_editor_property('node').export_text(),requires_native_compile_save=True)
out=Path('P:/FoA/Saved/Integration/cinematic_audit');out.mkdir(exist_ok=True)
(out/('battle_idle_'+mode+'.json')).write_text(json.dumps(report,indent=2));print('BATTLE_IDLE',mode)
