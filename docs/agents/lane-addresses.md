# Lane addresses (2026-11-09 wave)
Use these ids with SendMessage. The coordinator is "main". Territories: Saved/QA/lanes.json.

| Lane | Agent id | Owns |
|---|---|---|
| cleanup | a1022d0917c225aa2 | Content audit, then deletes and moves only in maintenance windows |
| horror | a6e4d6e821db500b3 | Jumpscare (BP_Jumpscare), monster, SFX acquisition, Content/FoA/Audio |
| face | a9048a1d2dbcf763c | Always-on face blur (PostProcess/FaceBlur), avatar materials (Teen/Materials, Hair, Cloth) |
| story | a45d2913a0b59c2fb | Script, intro parallax (UI/Intro), monologues (BP_BeatDirector), battle text |
| ui | a835e7cb42a19dae1 | The AAA material UI pass on every screen, input responsiveness, boot length |
| anim | ac437700517de2d1c | All animations, a tighter wake-up, post-wake camera framing, BP_FoAPlayer and the ABPs |
| world | aa7c6c54518f70380 | Scene, lighting, props, the sand events, the clock crumble, performance (Mass) |
| qa | a17726f0eb8e8c315 | The playthrough harness (pie_play plans A-D), repeated playtests, bug reports routed through main |
| hayba | a2a4cc39dbeb0d391 | Hayba restart 8 (r7 plus input_key nodes, UI slot parsers); restart 7 is installed; never touches the FoA editor |
| rig | a399f03aee1039342 | Teen skeleton, skinning, SK meshes, the retargeter (fingers first); owns Teen root files, Teen/Mesh, Teen/Anim, Player/Retarget, Tools/MPFB |
