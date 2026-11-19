"""Read-only: graph names of the story-relevant Blueprints -> Saved/StoryShots/graph_names.json (text audit input)."""
import json
import unreal
out = {}
for p in ('/Game/FoA/Gameplay/BP_BeatDirector', '/Game/FoA/Gameplay/Encounter/BP_Encounter',
          '/Game/FoA/Gameplay/Encounter/WBP_Encounter', '/Game/FoA/Gameplay/Encounter/BP_Garment',
          '/Game/FoA/UI/Game/WBP_HUD', '/Game/FoA/UI/Game/WBP_Phone', '/Game/FoA/UI/Game/WBP_DayRollover'):
    bp = unreal.load_asset(p)
    out[p] = [str(n) for n in unreal.BlueprintEditorLibrary.list_graph_names(bp)] if bp else None
open('P:/FoA/Saved/StoryShots/graph_names.json', 'w').write(json.dumps(out, indent=1))
print({k: len(v or []) for k, v in out.items()})
