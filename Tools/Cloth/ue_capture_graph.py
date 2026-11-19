"""Read-only material graph capture for the devlog."""
import unreal
import time
mat = unreal.load_asset('/Game/FoA/Characters/Teen/Cloth/M_FoA_TeenCloth')
unreal.FoAGraphToolsLibrary.capture_graph_png(mat, '', 'P:/FoA/Saved/ClothShots/teen_cloth_graph.png', True)
state = {'until': time.time() + 3, 'handle': None}
def close_preview(_dt):
    if time.time() < state['until']:
        return
    unreal.unregister_slate_post_tick_callback(state['handle'])
    unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(mat)
state['handle'] = unreal.register_slate_post_tick_callback(close_preview)
