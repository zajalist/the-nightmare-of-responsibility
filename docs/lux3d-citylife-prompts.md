# Lux3D prompts: Level 2 city life

Batch for Lux3D text-to-3D (G1, GLB with PBR), 2026-11-18, city life lane. Things that move around the job-hunt city
during the drive. The game is monochrome, so prompts describe shape, material and wear, not colour. Characters are
asked for in a relaxed A-pose with empty hands so Lux3D's auto-rig accepts them.
Run: `python Tools/Lux3D/lux3d_batch.py --table docs/lux3d-citylife-prompts.md --out P:/FoA-Assets/lux3d/citylife_20261118`

| Item | Beat | Version | Prompt | After generation |
|---|---|---|---|---|
| Commuter in suit | L2 drive | G1 20k 1800mm | Full-body adult man office commuter in a dark charcoal business suit, white shirt, narrow black tie and polished leather shoes, short neat hair, standing upright in a relaxed A-pose with both arms angled down and away from the body, empty open hands, realistic, single character | Auto-rig, Walk_Formal_Loop in place |
| Commuter in trench coat | L2 drive | G1 20k 1700mm | Full-body adult woman commuter in a long belted trench coat over office clothes, low-heeled shoes, hair tied in a low bun, standing upright in a relaxed A-pose with both arms angled down and away from the body, empty open hands, realistic, single character | Auto-rig, Walk_Loop in place |
| Faceless applicant | L2 drive | G1 20k 1850mm | Full-body faceless man in an oversized dark business suit, his head a smooth blank featureless oval with no face, a paper name tag on the lapel, standing upright in a relaxed A-pose with both arms angled down and away from the body, empty open hands, surreal, realistic materials, single character | Auto-rig, Zombie_Walk_Fwd_Loop in place |
| Night courier | L2 drive | G1 20k 1750mm | Full-body young delivery courier in a hooded rain jacket, track pants and sneakers, a large square insulated delivery backpack strapped on his back, standing upright in a relaxed A-pose with both arms angled down and away from the body, empty open hands, realistic, single character | Auto-rig, Jog_Fwd_Loop in place |
| Briefcase | L2 drive | G1 10k 420mm | Worn black leather office briefcase, closed, brass clasps, stitched carry handle on top, scuffed corners, single object | Flies in flocks over the road |
| Office chair | L2 drive | G1 10k 1100mm | Black mesh-back swivel office chair with padded armrests on a five-star base with caster wheels, slightly worn, single object | Rolls and spins along the kerb |
| Resume page | L2 drive | G1 10k 300mm | Single sheet of white printer paper with a printed resume, gently curled and bent as if caught by the wind, thin, single object | Swirls of pages over the road |
| Umbrella | L2 drive | G1 10k 1000mm | Open black umbrella with a curved wooden crook handle, canopy fully open, ribs visible, single object | Drifts and bobs above the pavement |
| Desk telephone | L2 drive | G1 10k 250mm | Vintage office desk telephone with a rotary dial and the handset resting on its cradle, coiled cord, worn plastic, single object | Giant, floats and rings over the road |
| Commuter in suit T | L2 drive | G1 20k 1800mm | Full-body adult man office commuter in a dark charcoal business suit, white shirt, narrow black tie and polished leather shoes, short neat hair, standing in a strict T-pose with both arms stretched straight out horizontally to the sides at shoulder height, palms down, legs slightly apart, realistic, single character | Retry of the suit after MODEL_NOT_RIGGABLE (arms hanging): auto-rig, Walk_Formal_Loop in place |
| Faceless applicant T | L2 drive | G1 20k 1850mm | Full-body faceless man in an oversized dark business suit, his head a smooth blank featureless oval with no face, a paper name tag on the lapel, standing in a strict T-pose with both arms stretched straight out horizontally to the sides at shoulder height, palms down, legs slightly apart, surreal, realistic materials, single character | Retry after MODEL_NOT_RIGGABLE: auto-rig, Zombie_Walk_Fwd_Loop in place |
| Crow in flight | L2 drive | G1 10k | Black crow in flight with both wings fully spread wide, gliding, tail feathers fanned, single bird | Flocks circling above the street |
