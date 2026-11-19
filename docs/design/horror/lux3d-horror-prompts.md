# Lux3D prompts: horror lane (jumpscare monster)

Run with `python Tools/Lux3D/lux3d_batch.py --table docs/design/horror/lux3d-horror-prompts.md --out P:/FoA-Assets/lux3d/horror --only "<Item>"`.
Outputs land in `P:\FoA-Assets\lux3d\horror\<slug>\` with their own `_state.json`. Monochrome game: prompts describe shape and surface only; the black-sand look comes from the UE material.

| Item | Beat | Version | Prompt | After generation |
|---|---|---|---|---|
| Jumpscare Face A | T2-T3 | G1 40k 700mm | Horrifying emaciated humanoid creature bust, head neck and bony shoulders only, gaunt elongated skull face with stretched cracked skin, deep empty eye sockets, unhinged jaw hanging open far too wide in a scream, long uneven needle teeth, two long skeletal hands with hooked fingers raised beside the face, surface crumbling like wet sand, single object | SM_Jumpscare_Monster in /Game/FoA/Gameplay/Jumpscare, black-sand material, lunges at the camera |
| Jumpscare Face B | T2-T3 | G1 40k 700mm | Hunched shadow creature leaning forward toward the viewer, upper body only, long thin neck, pale featureless face split by an enormous gaping mouth full of thin teeth, ragged shroud of dripping sand over the shoulders, long arms with clawed fingers reaching forward, single object | Alternative to Face A; keep only the one that reads best in black and white |
