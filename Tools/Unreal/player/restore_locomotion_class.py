"""Restore the hidden animation driver when Sequencer releases or skips the wake-up."""
import sys
sys.path.insert(0,'P:/FoA/Tools/Unreal/player')
from held_tool_graphs import Batch, inspect, find
P='/Game/FoA/Characters/Player/BP_FoAPlayer'
nodes,edges=inspect(P,'SetCinematic')
if not any(n['title']=='Set Anim Instance Class' for n in nodes):
    branch=find(nodes,'Branch');resume=find(nodes,'Unpause Timer by Function Name')
    b=Batch(P,'SetCinematic')
    b.get('source','Mesh',550,650)
    b.fn('restore','/Script/Engine.SkeletalMeshComponent:SetAnimInstanceClass',800,400,
         NewClass='/Game/FoA/Characters/Player/ABP_FoAPlayer.ABP_FoAPlayer_C')
    b.link('source','Mesh','restore','self')
    b.cut(branch,'else',resume,'execute')
    b.link(branch,'else','restore','execute');b.chain('restore',resume)
    b.comment('Resume locomotion driver',['source','restore']);b.run()
