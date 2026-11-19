# Lux3D prompts: Level 2 drive cars and hiring signs (drive lane, 2026-11-18)

Six paid G1 generations, authorized by the user through the coordinator for the drive's cars and signs.
Run: `python Tools/Lux3D/lux3d_batch.py --table docs/lux3d-drive-prompts.md --out P:/FoA-Assets/lux3d/drive_cars_signs`
Job ids, output URLs and files land in `P:/FoA-Assets/lux3d/drive_cars_signs/_state.json`.
Version cell: G1, face target in thousands, height in mm. Materials are made monochrome in Unreal.

| Item | Beat | Version | Prompt | After generation |
|---|---|---|---|---|
| Player sedan | L2 drive | G1 30k 1400mm | A 1970s four-door sedan car, long boxy body, chrome bumpers, round headlights, whitewall tyres, clean intact bodywork, plain single paint colour, no people, no text, isolated vehicle on a plain background | BP_L2Car visual mesh (Body and Roof hidden), 3 LODs |
| Traffic hatchback | L2 drive | G1 25k 1450mm | A compact 1980s hatchback car, small rounded body, plain single paint colour, intact, no people, no text, isolated vehicle on a plain background | traffic variant, 3 LODs |
| Traffic van | L2 drive | G1 25k 2000mm | A small boxy panel delivery van, plain flat side panels, plain single paint colour, intact, no logos, no people, no text, isolated vehicle on a plain background | traffic variant, 3 LODs |
| Sign billboard | L2 drive | G1 12k 5000mm | A freestanding roadside billboard: a wide rectangular sign panel with a thick metal frame and a small walkway with railing, raised on two steel posts with concrete footings, blank flat panel face, no text, no logos | hiring sign structure, text on the panel, 3 LODs |
| Sign pylon | L2 drive | G1 12k 4500mm | A tall roadside pylon sign: a rectangular light box with a metal frame mounted on a single thick steel pole with a concrete base, blank flat panel face, no text, no logos | hiring sign structure, text on the panel, 3 LODs |
| Sign marquee | L2 drive | G1 10k 2600mm | A vintage theatre-style marquee sign: a horizontal metal box sign with a frame of small light bulbs around a blank flat panel, standing on two short square legs, no text, no logos | interview sign structure, text on the panel, 3 LODs |
