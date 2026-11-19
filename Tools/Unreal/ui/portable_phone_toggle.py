"""The player's guarded P-open route. The enabled phone actor owns P-close."""
from portable_phone_graphs import Graph, run, PLAYER, GS, M


def main():
    path=PLAYER.rsplit('.',1)[0]
    g=Graph(path,'TogglePhone');e=g.entry
    cine=g.get('bCinematic');bc=g.add('cinematic','branch',250,0);g.link(cine,bc,'bCinematic','Condition');g.chain(e,bc)
    locked=g.get('bInteractionLocked',500,250);bl=g.add('interaction','branch',750,0)
    g.link(locked,bl,'bInteractionLocked','Condition');g.link(bc,bl,'False')
    pc=g.fn('pc',GS+'GetPlayerController',1000,250,PlayerIndex=0)
    ignored=g.fn('ignored','/Script/Engine.Controller:IsMoveInputIgnored',1250,250);g.link(pc,ignored,'ReturnValue','self')
    bi=g.add('movement','branch',1500,0);g.link(ignored,bi,'ReturnValue','Condition');g.link(bl,bi,'False')
    target=g.fn('target','/Script/Engine.PlayerController:GetViewTarget',1750,250);g.link(pc,target,'ReturnValue','self')
    own=g.add('self','self',1750,450);eq=g.fn('sameview',M+'EqualEqual_ObjectObject',2000,250)
    g.link(target,eq,'ReturnValue','A');g.link(own,eq,'self','B')
    bv=g.add('view','branch',2250,0);g.link(eq,bv,'ReturnValue','Condition');g.link(bi,bv,'False')
    fe='/Game/FoA/UI/Framework/BP_FoAFrontEnd.BP_FoAFrontEnd_C'
    find=g.fn('find',GS+'GetActorOfClass',2550,0,ActorClass=fe)
    cast=g.add('front','cast',2900,0,class_path=fe);g.link(find,cast,'ReturnValue','Object');g.link(bv,find,'True');g.chain(find,cast)
    gameplay=g.get('bInGameplay',3200,250,class_path=fe);g.link(cast,gameplay,'AsBP Fo AFront End','self')
    bg=g.add('gameplay','branch',3450,0);g.link(gameplay,bg,'bInGameplay','Condition');g.chain(cast,bg)
    opened=g.fn('open',fe+':OpenPhone',3750,0);g.link(cast,opened,'AsBP Fo AFront End','self');g.link(bg,opened,'True')
    g.save('Phone in free play')


if __name__=='__main__':main()
