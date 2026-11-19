# Lux3D prompts: tutorial bedroom

Batch list for Lux3D text-to-3D. **G1** = mesh with PBR (interactive props). **G1-Turbo PLY** = Gaussian splat for sand FX (it feeds the Niagara "Sand Morph" path).
The game is monochrome, so prompts describe shape, material and wear, not color. Style anchor for every prop: *slightly worn, lived-in, mid-century domestic, believable proportions, single object, neutral studio background*.

| Item | Beat | Version | Prompt | After generation |
|---|---|---|---|---|
| Bedroom door | T2–T6 | G1 | Plain interior wooden door, flat panel, round brass doorknob and a keyhole plate below it, slightly scuffed paint, single object | Articulation (hinge), retopo ~8k |
| Door key | T3–T4 | G1 | Old brass door key, long shaft, simple bit, worn | Retopo ~2k; cut into two halves in UE for the snap |
| Shoe | T3 | G1 | Worn black leather oxford shoe, creased toe, laces loose | Retopo ~6k |
| Bedding | T1 | G1 | Thin single mattress dressed with rumpled white linen sheets, one soft pillow and a grey wool blanket folded at the foot, no bed frame, single object | Goes on the Poly Haven iron bed frame, retopo ~10k |
| Single bed | T1 | G1 | Single wooden bed frame with a plain headboard, thin mattress, rumpled white linen sheets, one pillow, wool blanket folded at the foot | Part split (frame / mattress / bedding), retopo ~20k |
| Wardrobe | T6 | G1 | Tall two-door wooden wardrobe, flat doors, small round knobs, worn varnish | Part split (body / doors), articulation, retopo ~10k |
| Chest of drawers | T2, T7 | G1 | Four-drawer wooden chest of drawers, round wooden knobs, worn edges | Part split (drawers), articulation, retopo ~10k |
| Writing desk | T5 | G1 | Small wooden writing desk, thin straight legs, one drawer on the right | Part split (drawer), retopo ~8k |
| Desk lamp | T5 | G1 | Vintage metal desk lamp, cone shade, round heavy base, cloth cord | Retopo ~4k |
| Chair | — | G1 | Simple wooden bentwood chair | Retopo ~6k |
| Screwdriver | T5 | G1 | Flathead screwdriver with a worn wooden handle | Retopo ~2k |
| Wire hanger | T5 | G1 | Thin metal wire clothes hanger | Retopo ~1k |
| The Shirt (enemy) | T8 | G1 | Plain button-up dress shirt, inside out, crumpled, seams showing | Retopo ~10k, cloth sim in UE |
| Suit (payoff) | T9 | G1 | Sharp single-breasted suit jacket and trousers on a mannequin, crisp lapels, tie | Auto-rig with the Nightmare |
| The Nightmare | all | G1 | Faceless matte mannequin figure, smooth featureless head, visible joint seams, slender, standing in A-pose | Auto-rig + retarget; also a G1-Turbo PLY twin |
| Sand hand | T0 | G1-Turbo PLY | Human hand reaching forward, index finger extended, sculpted from fine dark sand | PLY → Niagara |
| The night mare | menu / rollover | G1-Turbo PLY | Horse rearing, sculpted from flowing dark sand, mane dissolving into grains | PLY → Niagara |
| Sand piles | trails | G1-Turbo PLY | Small spilled pile of fine dark sand on a floor | PLY → Niagara or static splat |
| Window frame | bay | G1 | Old wooden casement window frame with four small glass panes, chipped white paint, single object | Into the bay openings |
| Curtains | bay | G1 | Pair of long heavy linen curtains hanging from a turned wooden rod, slightly gathered, single object | Hang in the bay |
| Rug | room | G1 | Worn rectangular Persian rug lying flat, frayed edges, faded pattern | Floor dressing |
| Ceiling light | room | G1 | Vintage ceiling light fixture with a frosted glass dome shade on a short brass stem | Ceiling center |
| Radiator | bay | G1 | Old cast iron column radiator with chipped paint, single object | Under a bay window |
| Picture frame | wall | G1 | Small ornate wooden picture frame holding an old faded family photograph | Wall dressing |
| Fear of adulthood (clock) | commode mound | G1-Turbo PLY | Old wind-up alarm clock with twin bells, sculpted from dark sand | Splat that keeps materializing on the sand mound |
| Fear of adulthood (briefcase) | commode mound | G1-Turbo PLY | Worn leather office briefcase, sculpted from dark sand | Alternative splat for the mound |
| Heavy Hood | player | G1 | A heavy dark wool hood with a short shoulder cape, empty garment with no person inside, single object, worn and weighty folds | Skin to Manny in UE, retopo ~8k |
| Strap Harness | player | G1 | A worn leather chest harness of crossing straps and buckles, empty garment with no person inside, single object | Skin to Manny in UE, retopo ~6k |
| Faceless Mask | player | G1 | A smooth featureless angular mask with no eye holes and no mouth, matte, single object | Socket on Manny's head, retopo ~3k |
| Hooded Figure A | player | G1 300k 1800mm | Full-body 3D game character, a sturdy broad-shouldered adult man about 180 cm tall with a thick chest, strong arms and realistic male proportions. He wears a heavy dark wool coat that falls to the knees, a short shoulder cape, and a deep rounded hood pulled up over the head. Two leather straps cross in an X over the chest and back, joined by a round iron ring at the sternum. His face is a smooth featureless angular matte mask. Thick leather gloves with five separate fingers, sturdy leather boots. Standing in an A-pose, arms straight and 45 degrees out from the body, legs slightly apart, symmetric, single figure, neutral background | Knee coat, deep cowl hood, X harness. If picked: Lux3D retopo + auto-rig |
| Hooded Figure B | player | G1 300k 1800mm | Full-body 3D game character, a sturdy broad-shouldered adult man about 180 cm tall with a thick chest, strong arms and realistic male proportions. He wears a heavy dark wool coat cut at mid-thigh, a short shoulder cape, and a pointed peaked hood pulled up over the head. Two leather bandolier straps run from each shoulder to the opposite hip and cross on the chest, over a wide leather belt with a square buckle. His face is a smooth featureless angular matte mask. Thick leather gloves with five separate fingers, sturdy leather boots. Standing in an A-pose, arms straight and 45 degrees out from the body, legs slightly apart, symmetric, single figure, neutral background | Mid-thigh coat, peaked hood, crossed bandoliers + belt. If picked: Lux3D retopo + auto-rig |
| Hooded Figure C | player | G1 300k 1800mm | Full-body 3D game character, a sturdy broad-shouldered adult man about 180 cm tall with a thick chest, strong arms and realistic male proportions. He wears a long heavy dark wool coat reaching mid-calf, split at the front for walking, a short shoulder cape, and a large loose draped hood pulled up over the head. A leather harness of two shoulder straps joined by a horizontal chest strap, the straps crossing in an X between the shoulder blades. His face is a smooth featureless angular matte mask. Thick leather gloves with five separate fingers, sturdy leather boots. Standing in an A-pose, arms straight and 45 degrees out from the body, legs slightly apart, symmetric, single figure, neutral background | Mid-calf coat, draped hood, H harness crossing on the back. If picked: Lux3D retopo + auto-rig |
| Hooded Figure D | player | G1 300k 1800mm | Full-body 3D game character, a sturdy broad-shouldered adult man about 180 cm tall with a thick chest, strong arms and realistic male proportions. He wears a heavy dark wool hooded coat that ends at the hips, a short layered shoulder cape, and a close-fitting hood that frames the face. Leather straps cross over the shoulder cape, buckle at the center of the chest and run down to a wide belt with small pouches. His face is a smooth featureless angular matte mask. Thick leather gloves with five separate fingers, trousers tucked into tall sturdy leather boots. Standing in an A-pose, arms straight and 45 degrees out from the body, legs slightly apart, symmetric, single figure, neutral background | Hip-length coat, snug hood, straps crossing over the cape to a belt. If picked: Lux3D retopo + auto-rig |
| The Trousers | T8 boss | G1 30k 1050mm | Plain dark wool trousers standing upright on their own as if worn by an invisible person, one trouser leg twisted around the other, empty garment with no person inside, heavy soft fabric folds, waistband and belt loops, single object, neutral background | Lux3D retopo ~13k tris + 1k bake; rig 2x4 leg chains |
| The Socks | T8 boss | G1 30k 500mm | A single long knitted wool sock standing upright and slightly bent at the ankle, empty, ribbed cuff, worn heel and toe, single object, neutral background | Lux3D retopo ~13k tris + 1k bake; rig 1x4 chain; mismatched pair in UE |
| The Tie | T8 boss | G1 30k 1200mm | A long office necktie rising upright and coiled like a snake, silk fabric with a subtle diagonal stripe, tight knot at the top, single object, neutral background | Mesh twin of the Necktie Serpent splat; Lux3D retopo ~13k tris + 1k bake; rig 1x6 chain |
| Worn Shirt | player T8 | G1 30k | A plain long-sleeve button-up dress shirt shaped as if worn by an invisible sturdy man standing in an A-pose with arms 45 degrees out from the body, sleeves following the arms, collar closed, hem tucked in, empty garment with no person inside, single object, neutral background | Fit to SK_Sleeper, weights from the body, ~10k tris |
| Worn Trousers | player T8 | G1 30k | Plain dark wool trousers shaped as if worn by an invisible sturdy man standing straight with legs slightly apart, empty garment with no person inside, waistband with belt loops, single object, neutral background | Fit to SK_Sleeper, weights from the body, ~10k tris |
| Worn Sock | player T8 | G1 30k | A single knitted wool sock shaped as if worn on an invisible foot, upright, ribbed cuff at mid-calf, empty, single object, neutral background | Fit to SK_Sleeper (mirrored for the pair), ~3k tris |
| Worn Tie | player T8 | G1 30k | A long office necktie hanging straight down as if worn, knotted with its collar loop, silk with a subtle diagonal stripe, empty, single object, neutral background | Fit to SK_Sleeper neck/chest, ~2k tris |
| Worn Suit | player T9 | G1 30k | A sharp white single-breasted suit, jacket and matching white trousers, shaped as if worn by an invisible sturdy man standing in an A-pose with arms 45 degrees out from the body, crisp lapels, buttoned jacket, empty garment with no person inside, single object, neutral background | Payoff layer (white suit reference): fit to the MetaHuman body, weights from the body, ~10k tris |
| Worn T-Shirt | player start | G1 30k | A plain worn crew-neck t-shirt shaped as if worn by an invisible sturdy man standing in an A-pose with arms 45 degrees out from the body, short sleeves, soft faded cotton, slightly stretched, empty garment with no person inside, single object, neutral background | Start outfit: fit to the MetaHuman body, ~8k tris |
| Worn Sleep Pants | player start | G1 30k | Soft loose cotton sleep pants with a drawstring waist, shaped as if worn by an invisible sturdy man standing straight with legs slightly apart, empty garment with no person inside, single object, neutral background | Start outfit: fit to the MetaHuman body, ~8k tris |
| Hooded Figure B2 | player | G1 300k 1800mm | Full-body 3D game character, a sturdy broad-shouldered adult man about 180 cm tall with a thick chest, strong arms and realistic male proportions. He wears a heavy dark wool coat cut at mid-thigh, a short shoulder cape, and a pointed peaked hood pulled up over the head. Two leather bandolier straps run from each shoulder to the opposite hip and cross on the chest, over a wide leather belt with a square buckle. His face is a smooth flat angular matte mask with no nose and no eyes. Black leather gloves, sturdy leather boots. Standing in an A-pose, arms straight and 45 degrees out from the body with clear space between the arms and the coat, hands open with the five gloved fingers straight and slightly spread apart, legs slightly apart, symmetric, single figure, neutral background | B with open, spread gloved fingers and a flat mask (B's hands were a fused mitten) |
| Hooded Figure D2 | player | G1 300k 1800mm | Full-body 3D game character, a sturdy broad-shouldered adult man about 180 cm tall with a thick chest, strong arms and realistic male proportions. He wears a heavy dark wool hooded coat that ends at the hips, a short layered shoulder cape, and a close-fitting hood that frames the face. Leather straps cross over the shoulder cape, buckle at the center of the chest and run down to a wide belt with small pouches. His face is a smooth flat angular matte mask with no nose and no eyes. Both hands covered by black leather gloves, trousers tucked into tall sturdy leather boots. Standing in an A-pose, arms straight and 45 degrees out from the body, hands open with the five gloved fingers straight and slightly spread apart, legs slightly apart, symmetric, single figure, neutral background | D regenerated: D came back with bare hands |
| Sand Hourglass | dream | G1-Turbo PLY | An antique hourglass whose sand flows upward, sculpted from dark sand | PLY → splat mesh (Tools/Splats) |
| Melting Calendar | dream | G1-Turbo PLY | A wall calendar whose pages melt and drip into sand, sculpted from dark sand | PLY → splat mesh (Tools/Splats) |
| Unpaid Bills | dream | G1-Turbo PLY | A tall teetering stack of unpaid bills and envelopes, sculpted from dark sand | PLY → splat mesh (Tools/Splats) |
| Necktie Serpent | dream | G1-Turbo PLY | A long office necktie coiled like a snake, sculpted from dark sand | PLY → splat mesh (Tools/Splats) |
| Sand Crow | dream | G1-Turbo PLY | A crow perched and watching, its feathers dissolving into dark sand | PLY → splat mesh (Tools/Splats) |
| Alarm Clock Splat | dream | G1-Turbo PLY | An old twin-bell alarm clock, sculpted from dark sand, small cracks | PLY → splat mesh (Tools/Splats) |
| Sand Door | dream | G1 | A door frame and door made entirely of packed dark sand, crumbling at the edges, single object | Retopo ~8k |
| Bedside Book Stack | room | G1 | A small stack of old hardcover books, worn spines | Retopo ~3k |
| Glass Of Water | room | G1 | A half-full glass of water on a small coaster | Retopo ~2k |
| Coat Hook Rail | wall | G1 | An old wooden coat hook rail with three iron hooks, single object | Retopo ~2k |
| Smartphone | room | G1 10k 150mm | A slim modern black smartphone lying flat, matte black plastic back and thin metal edges, slightly worn corners, a cracked corner on the glass screen protector, screen off, single object | Retopo ~2.5k tris (1250 quads), 1k bake; screen slot added offline for WBP_Phone |

Tips from the docs: one object per prompt, and G1-Turbo returns a splat in about 20 s, so iterate prompts on Turbo first, then run the keeper on G1 for the mesh.

## Generating

This table is the input. Edit a prompt here, then run:

```
python Tools/Lux3D/lux3d_batch.py --dry-run                    # check what will be sent
python Tools/Lux3D/lux3d_batch.py --only "Single bed,Shoe"     # generate some rows
```

The key comes from the `LUX3D_API_KEY` env var or `~/.foa/lux3d_api_key`; never commit it. Results land in `P:/FoA-Assets/lux3d/<item>/`.
Re-running polls tasks it already created instead of paying for them again. To regenerate a row, delete its entry from `_state.json`.
