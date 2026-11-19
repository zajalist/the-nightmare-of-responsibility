"""Exact graph ownership shared by layout and capture finalizers."""
TARGETS=dict(
    threshold='/Game/FoA/Level2/Transition/BP_DreamThreshold',
    merge='/Game/FoA/Level2/Journey/BP_L2Merge',
    stopset='/Game/FoA/Level2/Journey/BP_L2StopSet',
    journey='/Game/FoA/Level2/Journey/BP_L2Journey',
    phone_widget='/Game/FoA/UI/Game/WBP_Phone',
    phone_actor='/Game/FoA/UI/Game/BP_Phone',
    frontend_phone='/Game/FoA/UI/Framework/BP_FoAFrontEnd',
    drive_hud='/Game/FoA/Level2/Drive/WBP_L2Drive',
    battle_hud='/Game/FoA/Gameplay/Encounter/WBP_Encounter',
    journey_hud='/Game/FoA/Level2/Journey/WBP_L2Journey',
    player_camera='/Game/FoA/Characters/Player/BP_FoAPlayer',
    interactor='/Game/FoA/Gameplay/BPC_Interactor',
    aim_hud='/Game/FoA/UI/Game/WBP_HUD',
    drive_car='/Game/FoA/Level2/Drive/BP_L2Car',
    meteor='/Game/FoA/Level2/Drive/BP_Meteor',
    city_sector='/Game/FoA/Level2/City/Expanded/BP_City2Sector',
    interview_hud='/Game/FoA/Level2/Journey/WBP_L2Interview',
)
GRAPH_NAMES={
    TARGETS['phone_widget']:('ResolveL2Phone','CacheL1Phone','RestoreL1Phone','RefreshL2Phone',
                            'CloseL2Phone','OpenL2Message','RefreshL2Progress'),
    TARGETS['phone_actor']:('NotifyL2PhoneClosed',),
    TARGETS['frontend_phone']:('RestoreL2PhoneHUD','SayCharacter','PickCharacterVoice','StopCharacterVoice',
                              'ShowCinematicSubtitle','HideCinematicSubtitle','ReturnToTitle','RestartDay','EventGraph'),
    TARGETS['drive_hud']:('RefreshL2Progress',),
    TARGETS['battle_hud']:('RefreshL2Progress','RefreshL2ProgressContext','TornConfigure','RefreshBattleActionIcon'),
    TARGETS['journey_hud']:('RefreshL2Progress','Refresh'),
    TARGETS['player_camera']:('UpdateFirstPersonVisibility',),
    TARGETS['interactor']:('FindBest','Scan'),
    TARGETS['aim_hud']:('RefreshAimDot','HandleNarration','EventGraph'),
    TARGETS['drive_car']:('PlaceAtCheckpoint','CheckDestination','Move','Schedule','StartLeg','Continue','Deactivate','QueueTurn','UpdateCamera','UpdateShockwave','ResetShockwave','Restart','EventGraph'),
    TARGETS['meteor']:('Impact','UpdateImpact','ResetImpact'),
    TARGETS['city_sector']:('UpdateSector','ReleaseSector','EventGraph'),
}


def capture_names(path, available):
    """Validate the complete capture selection before writing any graph image."""
    assert path in TARGETS.values(),path
    requested=GRAPH_NAMES.get(path)
    if requested is None:return list(available)
    missing=set(requested)-set(available)
    assert not missing,('Requested graphs missing',path,sorted(missing))
    return list(requested)
