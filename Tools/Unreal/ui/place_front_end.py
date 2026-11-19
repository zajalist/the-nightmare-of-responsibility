"""Places (or updates) the one BP_FoAFrontEnd in the open level, wired to BP_MenuCamera + LS_MainMenu_Camera.
Run via ue_remote.py: spawns and labels only, then prints the Hayba object_set_property call for the references
(Python never writes Blueprint instance properties, editor-rules 20:42). Replay it, then Hayba level_save."""
import json

import unreal


def main():
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    actors = {a.get_actor_label(): a for a in eas.get_all_level_actors()}
    cls = unreal.load_class(None, '/Game/FoA/UI/Framework/BP_FoAFrontEnd.BP_FoAFrontEnd_C')
    fe = actors.get('BP_FoAFrontEnd') or eas.spawn_actor_from_class(cls, unreal.Vector(0, 0, 250))
    fe.set_actor_label('BP_FoAFrontEnd')
    fe.set_folder_path('UI')
    props = {'MenuCamera': actors['BP_MenuCamera'].get_path_name(),
             'MenuSequence': actors['LS_MainMenu_Camera'].get_path_name(), 'bSkipFrontEnd': False}
    print('HAYBA object_set_property', json.dumps({'path': fe.get_path_name(), 'properties': props}))


main()
