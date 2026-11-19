"""Read-only: retarget chains of the Manny and MetaHuman IK rigs (do the fingers transfer?).
  FOA_AREAS=Characters python Tools/Unreal/ue_remote.py Tools/Unreal/player/probe_rtg_chains.py"""
import unreal
for path in ('/Game/FoA/Characters/Player/Retarget/IK_FoA_Mannequin', '/Game/FoA/Characters/Player/Retarget/IK_FoA_MetaHuman'):
    c = unreal.IKRigController.get_controller(unreal.load_asset(path))
    chains = c.get_retarget_chains()
    print(path.split('/')[-1], [(str(ch.get_editor_property('chain_name')), str(ch.get_editor_property('start_bone').get_editor_property('bone_name')),
                                 str(ch.get_editor_property('end_bone').get_editor_property('bone_name'))) for ch in chains])
r = unreal.IKRetargeterController.get_controller(unreal.load_asset('/Game/FoA/Characters/Player/Retarget/RTG_Mannequin_to_MetaHuman'))
print('RTG', [m for m in dir(r) if 'chain' in m.lower()][:20])
