# AAA UI direction for The Nightmare of Responsibility

This is the brief a UI artist turns into WebGL prototypes first, then into UMG widgets driven by animated UI materials. Part 1 studies ten games. Part 2 sets the rules for the whole set. Part 3 specifies each FoA screen. Part 4 lists the material kit.

UMG plumbing (Retainer Box PhaseCount, invalidation, CommonUI stacks, no Tick) is covered in `docs/ui/ui-motion-research.md`, so it isn't repeated here.

**Build from the prototype.** The live prototypes are at https://claude.ai/artifact/VwkNfHmcAspBtdGQEDzVph (source: the ui lane scratchpad `ui_v4/index.html`). Where this doc's Suggested numbers differ from the prototype, the prototype wins once the user approves it. Its tokens are Tick 90 ms linear, Move 140 ms (0.22, 1, 0.36, 1), Exit 220 ms (0.55, 0, 0.85, 0.35), Enter 320 ms (0.22, 1, 0.36, 1), Form 1100 ms (0.22, 1, 0.36, 1), Scatter 800 ms (0.55, 0, 0.85, 0.35) and Carry 520 ms (0.65, 0, 0.35, 1). The research below is the reasoning behind them.

How claims are marked:

- A sentence followed by a link is sourced.
- **Inference** is my own reading of a game, with no developer source.
- **Suggested** is a number I am proposing, not one I found.

## The one idea

The interface is made of the same black sand as the house, and it remembers.

Every element **forms** out of grains when it's needed, **holds** almost perfectly still, and **disperses** when it's done.

- **Time-shift echo** means the present has a past. An item you just left keeps a ghost for a moment, and knowledge from a failed day trails into the next one.
- **Datamosh** means time is breaking. It is rare, short, and only happens at time events.
- **Grain sheen and sparkles** only appear where light falls. In a game with no colour, light is the highlight.

## Part 1. Ten games

### Death Stranding (Kojima Productions, 2019)

**Idea.** A calm logistics instrument panel. Fonts in Use credits the look to "minimal use of animations, a soft blue color scheme and long lines of information". A long strand shape marks the selected button.

**Motion.** Mostly still. **Inference:** the loudest UI motion is in the world: the Odradek scan, a pulse that tags terrain. A Decima frame breakdown notes the scan footprints are drawn as decals at the end of the frame.

**Type.** SST for UI. Sackers Gothic for the logo and chapter cards. Custom faces for numbers.

**Diegesis.** The studio's UI designer says cutscene UI is "meant to be seen not just by the game players but also by the characters in the game". No audio source found.

**Steal.** Calm, long, readable rows. UI the character can see, which is FoA's phone.

**Avoid.** The strand as a selection marker. It is a drawn line, and FoA's sand vortex already does that job. Also avoid blue and data density.

Sources: [Fonts in Use](https://www.fontsinuse.com/uses/67648/death-stranding-video-game), [Kojima Productions staff interview](https://kojimaproductions.jp/en/Staff-interview-01), [Behind the Pretty Frames](https://mamoniem.com/behind-the-pretty-frames-death-stranding/), [Interface In Game](https://interfaceingame.com/games/death-stranding/)

### Control (Remedy, 2019)

**Idea.** Bureaucratic restraint against the paranormal. Kotaku argues the clean UI lets the type carry the Bureau's authority.

**Type.** Interstate and Basic Commercial for UI and documents. ITC Avant Garde Gothic Bold for area titles, which stay on screen during action, and for the wordmark. Remedy says the visual target set the "red pulsating glow" and a logo with "striking clean typography". The UI was built in Coherent's HTML middleware with live iteration.

**Motion.** **Inference:** area names cut in huge over live play. The HUD is small and static. Hiss corruption reads as doubled, flickering type, and it only works because the baseline is so clean. No audio source found.

**Steal.** Huge single-weight type over live play with no plate, for FoA's room names and rollover clock. A clean baseline so that distortion reads.

**Avoid.** The red accent and constant flicker.

Sources: [Fonts in Use](https://fontsinuse.com/uses/48689/control-video-game), [Kotaku](https://kotaku.com/the-fonts-in-control-make-its-world-feel-way-creepier-1837714580), [GamesRadar](https://www.gamesradar.com/we-created-something-exceptional-remedy-reflects-on-control-our-2019-game-of-the-year), [Coherent Labs](https://coherent-labs.com/?p=1228), [Interface In Game](https://interfaceingame.com/games/control/)

### Alan Wake 2 (Remedy, 2023)

**Idea.** The menu is a place. Entering the Mind Place "doesn't pause the game", so the player can't hide there.

**Motion.** Case-board items move on Spring Motion. Hand animations sync to a camera driven by panning volumes. Clues start in a card hand that lead UI/UX designer Riho Kroll says was "somewhat inspired by Hearthstone". Everything in the real world had to be interruptible. Localised text renders to textures through Coherent Gameface. The article covers neither typefaces nor audio.

**Inference.** Chapter titles are large type over live footage. Scene rewrites use light wipes, not panels.

**Steal.** The phone doesn't pause the day either. Spring-damped placement for knowledge notes.

**Avoid.** A walkable menu room. FoA can't afford one.

Sources: [Game Developer](https://www.gamedeveloper.com/design/true-detective-meets-hearthstone-unlocking-the-metaphysical-mind-place-of-alan-wake-ii), [Interface In Game](https://interfaceingame.com/games/alan-wake-ii/)

### The Last of Us Part II (Naughty Dog, 2020)

**Idea.** Get out of the way, and give every visual signal a non-visual twin. Naughty Dog routes visual-only information through sound and vibration.

**Options to copy.** HUD Scale. HUD Background, which sets backdrop darkness. HUD Flashing on or off. High Contrast Display. Text-to-Speech. Screen Magnifier. Camera Shake and Motion Blur sliders from 1 to 10. Combat Audio Cues. Three one-step presets.

**Inference.** Crafting happens on Ellie's backpack in the world, and the camera stays live.

**Steal.** The options list. HUD Background maps to FoA's scrim opacity. HUD Flashing maps to a switch for glints and datamosh.

**Avoid.** Nothing in principle.

Sources: [Naughty Dog accessibility](https://naughtydog.com/blog/THE_LAST_OF_US_PART_II_ACCESSIBILITY_FEATURES_DETAILED), [Interface In Game](https://interfaceingame.com/games/the-last-of-us-part-ii/)

### Persona 5 (Atlus, 2016)

**Idea.** Style as attitude. Each menu is its own bespoke program, according to Hashino. CEDEC 2017 described a red-only palette with no secondary colours except HP/MP, central lines that guide the eye, and key information "on the same side as the mainly white color".

**Motion.** A 3D model spins and lands in a pose, captured to 2D with a custom tool. A fan frame study of the calendar day change measures 6 s on the old date, 2 s for the change, and 4 s on the new date. **Inference:** hard cuts, skew, overshoot, and an audible hit on every confirm.

**Readability.** Hashino says early menus were hard to read and needed repeated passes.

**Steal.** The day change as a ritual with an unmistakable before and after. One-colour discipline, taken to zero colours. A bespoke entrance per screen inside one grammar.

**Avoid.** 12 s is far too long for a loop the player fails repeatedly. Also avoid skewed chaos.

Sources: [Siliconera, CEDEC 2017](https://www.siliconera.com/?p=668266), [PC Gamer](https://www.pcgamer.com/games/rpg/persona-series-director-says-atluss-flashy-menus-are-actually-really-annoying-to-design), [GamesRadar](https://www.gamesradar.com/games/jrpg/persona-director-and-jrpg-veteran-says-the-amazing-menus-in-metaphor-refantazio-were-really-annoying-to-make-just-as-persona-5s-were-impossible-to-read-at-first), [itch.io frame study](https://itch.io/blog/533534/making-ui-come-to-life-study-of-persona-5), [Inverse](https://inverse.com/gaming/persona-5-tactica-user-interface)

### Hades (Supergiant, 2020)

**Idea.** Painted, fast, and never in the way of the next run. Josh Barnett is credited with "FX art, UI design and animations", and the game has 194 boon icons. For Hades II, Supergiant hired an animator to cut illustrated art into transitions and menu loops in After Effects, then "render animation to PNG sequence".

**Inference.** Boon choices arrive as three staggered panels. The trip from death back to the next run is short and skippable. No audio source found.

**Steal.** Short repeat loops. A staggered three-way choice reveal for FoA's garment-battle actions.

**Avoid.** PNG sequences, which would blow FoA's 1 GB budget; materials do that job here. Colour-coded identity.

Sources: [MCV](https://mcvuk.com/business-news/behind-the-art-of-hades-we-value-artistic-integrity-and-excellence-in-artistic-craft-at-supergiant-however-were-first-and-foremost-a-game-design-lead-team/), [80.lv](https://80.lv/articles/hades-ii-developer-is-looking-for-a-part-time-ui-animator/), [Interface In Game](https://interfaceingame.com/games/hades/)

### Returnal (Housemarque, 2021)

The closest relative: a time loop with a monochrome UI.

**Idea.** Industrial and functional. UI/UX director Johannes Koski describes one "haunting shade of teal" taken from monochrome CRTs and night vision. There is no title screen; the game starts straight in play.

**Motion.** "Little to no directional movement". Elements flicker on and off. Pop-up layers were avoided. Near death brings cracked visor glass, glitch animations, vignettes, and flashing warnings.

**Audio and haptics.** A rising charge-up sound ends in a distinct cue and a haptic pulse.

**Accessibility.** The controller map comes first in options. Changes preview live: the stick highlights during deadzone tuning, and subtitles preview as you change them.

**Steal.** Proof that strict monochrome reads as AAA. Glitch reserved for danger. Live preview in settings. Charge-up audio on holds.

**Avoid.** CRT scanlines. FoA is sand, not glass.

Sources: [PlayStation Blog](https://blog.playstation.com/?p=348960), [Interface In Game](https://interfaceingame.com/games/returnal/)

### Hi-Fi Rush (Tango Gameworks, 2023)

**Idea.** Everything lands on the beat.

- Mikami suggested building without UI, and Johanas says "We did a long time without any UI."
- Attacks are adjusted to land on the beat, and the UI pulses to the music.
- A beat visualiser can be toggled.
- Krafton ships a latency check because audio/video delay varies by hardware.

**Inference.** Idle loops and hit flashes are quantised to the tempo, so the whole screen breathes as one.

**Steal.** One shared clock: FoA's idle loops lock to the house clock's 1000 ms tick. An audio/video offset slider for the battle.

**Avoid.** The comic palette and constant bounce.

Sources: [Vice](https://vice.com/en/article/88qyw5/how-a-designer-known-for-horror-made-the-musical-gaming-triumph-hi-fi-rush), [Unreal Engine](https://www.unrealengine.com/developer-interviews/hi-fi-rush-was-inspired-by-shaun-of-the-dead-and-futurama), [Krafton](https://support.krafton.com/hc/en-us/articles/52370830105625-Hi-Fi-RUSH-Frame-Rate-and-Music-Sync-Information), [Interface In Game](https://interfaceingame.com/games/hi-fi-rush/)

### Senua's Saga: Hellblade II (Ninja Theory, 2024)

**Idea.** No interface.

- Reviewers report no HUD and no prompts beyond the pause menu. The controller diagram shows once, before play.
- The game is framed in 2.39:1, with bars on non-ultrawide screens.
- The first game aimed to give all feedback without a HUD. Its failure state was rot that spread up Senua's arm with each death.

**Inference.** Binaural voices carry warnings. This is widely reported but not verified here.

**Steal.** The rot. It is the best model for FoA's kept knowledge: memory shows on the character and in the room, not only in a menu. Also the letterbox as the signal that a time event is happening and the player is not in control.

**Avoid.** Zero HUD. FoA has objectives and a battle.

Sources: [Laptop Mag](https://www.laptopmag.com/gaming/senuas-saga-hellblade-ii), [Windows Central](https://www.windowscentral.com/gaming/xbox/hellblade-2-will-be-delivered-in-2391-aspect-ratio-creating-cinematic-film-bars-on-non-ultrawide-displays), [Unreal Engine, Hellblade](https://www.unrealengine.com/en-US/developer-interviews/exploring-the-mindset-behind-hellblade-senuas-sacrifice), [Interface In Game](https://interfaceingame.com/games/hellblade-senuas-sacrifice/)

### Silent Hill 2 (Bloober Team, 2024)

**Idea.** UI is optional. The whole interface can be switched off. Guidance then comes from visuals, sound, and James, who glances at points of interest. A 90s filter adds grain, colour correction, and screen adjustments.

**Inference.** Fog and grain carry the uncertainty a HUD would otherwise resolve.

**Steal.** The teen's head-look as the quietest prompt. A UI-off option. Grain as a setting.

**Avoid.** Map-centred navigation. FoA is one house.

Sources: [GamesRadar](https://gamesradar.com/games/silent-hill/silent-hill-2-remake-lets-you-disable-all-ui-elements-for-the-most-immersive-experience-and-youll-be-told-where-to-go-by-visual-sound-and-character-cues), [PC Gamer](https://pcgamer.com/games/horror/the-silent-hill-2-devs-explain-why-you-wont-need-to-use-ui-in-the-remake-instead-james-will-just-glare-at-things-devilishly), [Siliconera](https://siliconera.com/you-can-turn-off-the-ui-turn-on-90s-filter-in-silent-hill-2-remake)

### What the ten add up to

Each strong UI in this set does five things:

1. **One material idea, and nothing else.** CRT teal, bureau type, the manifest, red slabs.
2. **Small motion at rest, loud motion only at events.**
3. **Memory and failure shown in the world.** Rot, the live Mind Place, the loop.
4. **Short repeat loops.**
5. **A sound, haptic, or setting twin for every visual signal.**

Sand-that-remembers fits all five.

## Part 2. Principles

### Timing and easing tokens

Every curve has an exact closed form, so the WebGL prototype, CSS and the Unreal material match frame for frame. The bezier values are the easings.net equivalents. All durations are **Suggested**. The 15 Hz step and 6 Hz glint already exist in MF_UI_TimeSlice (`floor(T * 15)`) and MF_UI_SandGrain (`floor(T * 6)`).

| Token | Duration | cubic-bezier | Closed form, x in 0..1 | Use |
|---|---|---|---|---|
| snap | 80 ms | 0.33, 1, 0.68, 1 | 1 - (1-x)^3 | press-in, interrupt to end state |
| focus-in | 160 ms | 0.33, 1, 0.68, 1 | 1 - (1-x)^3 | focus gained |
| focus-out | 240 ms | 0.37, 0, 0.63, 1 | (1 - cos(pi x)) / 2 | focus lost; slower, so the echo trails |
| enter | 360 ms | 0.22, 1, 0.36, 1 | 1 - (1-x)^5 | panels, rows, prompts |
| form | 600 ms | 0.16, 1, 0.3, 1 | x >= 1 ? 1 : 1 - 2^(-10x) | sand letters forming |
| form-hero | 1400 ms | 0.16, 1, 0.3, 1 | same | logotype, rollover clock |
| exit | 240 ms | 0.32, 0, 0.67, 0 | x^3 | rows and panels leaving |
| disperse | 420 ms | 0.7, 0, 0.84, 0 | x <= 0 ? 0 : 2^(10x - 10) | sand blowing away |
| bury | 900 ms | 0.7, 0, 0.84, 0 | same | SandWipe coverage to 1 |
| unbury | 800 ms | 0.16, 1, 0.3, 1 | form curve | coverage to 0 |
| move | 500 ms | 0.65, 0, 0.35, 1 | in-out cubic | logotype from title to menu |
| sweep | 900 ms | 0.37, 0, 0.63, 1 | in-out sine | light sweep |
| step | 66.7 ms per step | steps | floor(T x 15) | datamosh and echo lag, 2 to 6 steps |
| breathe | 4000 ms period | sine | 0.5 + 0.5 sin(2 pi T / 4) | idle |
| glint | 166 ms life | hash at 6 Hz | step(0.994, hash) | rim sparkle, about 1 per 5 s per word |

**Mapping to UMG.** Each widget gets **one linear `Progress` scalar**, from 0 to 1. A UMG material track or a Set Scalar Parameter call drives it. The material applies the curve with MF_UI_Ease (Part 4) and derives per-layer timing as `saturate((Progress - Delay) / Span)`.

If those are plain math nodes on a parameter, UE's material compiler should fold them into a per-draw uniform. A Custom node would run per pixel instead. Confirm the result in Material Stats.

Per-letter stagger uses the same expression with `Delay` taken from UV.x, which costs one multiply-add per pixel.

### Transitions

1. **Exits are faster than enters.** Enters run 360 to 600 ms, exits 240 to 420 ms. The next screen starts forming at 50% of the previous exit, so screens overlap by about 120 ms.
2. **Input is never blocked for more than 200 ms.** The first item becomes live as soon as its own form ends.
3. **Interrupting an enter** snaps it to the end state in 80 ms, then handles the input.
4. **Interrupting an exit** queues the input. No exit is longer than 420 ms.
5. **Never play an enter backwards as an exit.** Reversed sand means time rewinding, and only the rollover's unbury uses it.
6. **No half-states.** A widget removed mid-animation snaps to rest in 80 ms. Nothing sits between Reveal 0.05 and 0.95 for longer than its token.
7. **Repeats get shorter.** A sequence plays in full the first time. After that it plays a compressed version that can be skipped after 600 ms (Hades, Returnal).

### Focus states

| State | Ink on #050505 | Contrast | Sand energy | Echo | Other |
|---|---|---|---|---|---|
| Rest | #8C8C8C | 6.1:1 | 0.28 | 0 | still |
| Focus | #F0F0F0 | 17.9:1 | 1.0 | 4 ghosts | vortex on, grain pours |
| Pressed | #FFFFFF | 20.4:1 | 1.0 | collapses in 80 ms | glint burst, 166 ms |
| Disabled | #5A5A5A | 3.0:1 (disabled is exempt) | 0 | 0 | one plain sentence says why |

Focus is never motion-only. Luminance changes too, from 6:1 to 18:1. With Reduce Motion on, one static ghost stays as a shape cue.

Focus never changes weight or size, because either one reflows text and invalidates layout.

If focus moves again within 160 ms, the item left behind skips its echo. This prevents smear storms during fast scrolling.

### Idle life

At rest the screen should look like a photograph that is very slightly alive. All values are **Suggested**:

- Type moves at most 1 px, with grain drift only inside the glyphs.
- Luminance breathes by at most 2% over a 4000 ms period.
- Glints average about 1 per 5 s per word, with at most 3 on screen at once, and only on focused or hero type.
- Loop periods divide 60 s exactly. Anything that ticks does so on the house clock's 1000 ms.

Set **Period = 60** on every UI Time node. Loops then wrap without a pop, and float precision holds over long sessions.

MF_UI_TimeEcho breathes with `sin(T * 1.3)`, a 4.83 s period. Change it to `sin(T * 1.2566)`, which is exactly 5 s.

Every UI material reads the same Time, so all loops stay in phase for free, without an MPC or Tick. If grain freezes on pause, enable Ignore Pause on the Time node. Verify on 5.8 which clock UI materials actually read.

### Parallax

Use three layers at most: the live 3D backdrop, the scrim, and type.

- **Type never moves.**
- The backdrop shifts up to ±1.5° of camera yaw (or 12 px UV offset for a flat backdrop). The scrim shifts 4 px.
- Input is the mouse or right stick, with an exponential follow at a 120 ms time constant, run on BP_MenuCamera's own tick.
- Reduce Motion sets parallax to 0.

### Light sweeps

The sweep is the game's only highlight: "grain sheen only in light", made literal.

- A band 18% of the element's width, tilted 20°, travelling left to right in 900 ms on an in-out sine.
- It multiplies **only SandGrain's Tone and Glint**, by up to 1.35, so the sand catches light while the letterform stays put.
- It fires on a focus that rests for 400 ms or more (once), on each new knowledge sentence, and at the end of hero forms.
- It never repeats on one element within 8 s.

### Dissolve and distortion grammar

Each effect has one meaning. Using it anywhere else is a bug.

| Effect | Means | Allowed on | Never on |
|---|---|---|---|
| Sand form | it appears, it is learned | words, logotype, own marks | partner logos, paragraphs over 2 lines (fade those) |
| Sand disperse | it is done | words, completed prompts | errors |
| Bury and unbury | a time boundary | full screen: New game, rollover, hard loads | navigation within a menu |
| Time echo | the present has a past | focus lag, kept knowledge, the phone's minute | resting items |
| Datamosh | time breaks | pause freeze, failure, rollover, New game; at most 400 ms and 3 per second | focus, idle, text being read |
| Glint | light touches sand | rims of focused or hero type | anything resting in shadow |
| Light sweep | new, or matters now | new knowledge, hero forms | lists, idle loops |

### Audio-motion sync

Play each sound from the same Blueprint event that sets the material parameter, never from a delayed notify.

ITU-R BT.1359 puts detectability at audio leading by 45 ms or lagging by 125 ms. Treat that as the outer limit and aim for one frame (16.7 ms).

| Event | Sound | Sync point | Length |
|---|---|---|---|
| Focus move | dry grain tick, 3 variants, ±1 semitone | first frame of focus-in | 40 to 60 ms |
| Focus blocked | muffled double tick | same frame | 80 ms |
| Confirm | low thump, then a sand pour | thump on the echo collapse; pour across the disperse | 400 to 600 ms |
| Back | soft downward sand exhale | first frame of exit | 200 ms |
| Screen enter | low air swell | peak at 70% of the form | 600 ms |
| Slider step | grain tick, pitch mapped over one octave | each step | 30 ms |
| Hold to interact | rising hiss, +12 semitones over the hold | follows Progress | completion clunk plus a 60 ms rumble |
| Pause | tape-stop, world low-passed to 800 Hz | freeze frame | 150 ms |
| Rollover | tape-stop, pour, silence, ticks, alarm | see the rollover spec | about 4 s |

### Readability and accessibility

1. **Contrast.** Informative text is at least 4.5:1. The floor on #050505 is #787878 (4.6:1). Over the live bedroom, the scrim must keep the area behind resting text at or below #262626 (luminance about 0.019), so #8C8C8C stays above 4.5:1. QA checks this with a luminance probe on captures. Echo and glints never carry information.
2. **Size.** XAG 101 sets a 26 px body height (descender to ascender) at 1080p as the minimum. Measure it in a capture. UE font sizes are points at 96 DPI, not pixel height. Text scales to 100, 125 or 150%.
3. **Reduce Motion** (MPC_UI.ReduceMotion already scales Time).
   - Form becomes a 150 ms fade, and disperse becomes 120 ms.
   - Echo becomes one static ghost on focus.
   - Datamosh becomes a 200 ms crossfade through black.
   - Grain, glints, parallax and sweeps stop.
4. **Flashing Effects off** is separate, like TLOU2's HUD Flashing. It removes glints, sweeps and datamosh.
5. **No full-screen white frames, ever.** Large luminance changes happen at most 3 times per second (WCAG 2.3.1). Bursts go dark to dark.
6. **No motion-only feedback.** Every state change also changes luminance, text or sound. Every important sound has a visual or haptic twin.
7. **Toggle alternatives.** Hold-to-interact has a toggle option, and the battle has an audio/video offset.

### Performance on low-end PCs

These budgets are **Suggested**; Epic publishes none for UI materials. Measure with Material Stats on the SM6 platform, plus `stat slate`, `stat gpu` and `ProfileGPU`.

| Material class | Pixel instructions | Samples | Notes |
|---|---|---|---|
| Always-on HUD | ≤ 80 | ≤ 2 | no retainer |
| Menu text on retainer | ≤ 220 | ≤ 14 | ≤ 8 retainers per screen, sized to the word |
| Full-screen transition | ≤ 150 | ≤ 3 | about 2 M pixels at 1080p |
| Full-screen translucent layers | ≤ 2 at once | | scrim plus one transition |

- **Fixed taps only**, like the existing 4-tap blur and 4 echo ghosts. No loops in Custom nodes and no per-pixel dynamic branches.
- **One noise texture.** T_UI_SandNoise uses only B, which holds fBm. Put new needs in its free channels: R for blue noise, G for the block hash, A for cells.
- **Retainers only where a material needs neighbouring glyph pixels:** menu words, the logotype, and rollover text. HUD, phone and settings rows use plain Text.
- **A Quality Switch** drops echo and blur taps at Low quality. Verify it in the UI domain on 5.8.
- **Target** at most 0.5 ms for the UI pass on a GTX 1060-class GPU at 1080p.

## Part 3. FoA screens

Copy here is placeholder, but it follows the rules: sentence case, no separators, no eyebrow labels, and never the codename. Timings are **Suggested** and measured from the triggering event.

### Boot cards (WBP_BootSplash)

**Layout.** One mark per card on #050505, 96 px tall, sitting 4% above centre. No captions. The sand escalates across the three cards: Unreal Engine is clean, Aholo is clean, and Hayba forms entirely from sand before handing over to the title.

| Beat | Unreal Engine, Aholo | Hayba |
|---|---|---|
| Enter | 600 ms of black, then a 500 ms fade (form curve) with a 4 px rise | M_UI_SplatLogo Transition 0 to 1 over 1300 ms (form) |
| Hold | 1200 ms | 1200 ms, glints only |
| Exit | 400 ms fade (exit) | Transition 1 to 0 over 600 ms (disperse) |
| Skip | From the second launch on, any input after 300 ms ends the card in 240 ms | same |

Partner marks stay unaltered, with opacity changes only. Check each brand's logo guidelines.

**Sound.** Room tone on the partner cards. On Hayba, a pour during the assemble, then a thump when Transition reaches 1.

### Title (WBP_Title, WBP_Logotype)

**Layout.**
- The logotype sits in the left third over the live bedroom camera (LS_MainMenu_Camera), with the left scrim behind it.
- "Nightmare" is ExtraBold and the largest word. "The" and "of Responsibility" are SemiBold at about 45% of its size, locked up as one mark.
- "Press any button" sits 48 px below, 26 px Medium in #8C8C8C.

| Beat | Timing and easing | Material |
|---|---|---|
| Enter | Scene fades up over 1200 ms (form). The logotype forms left to right over 1400 ms (form-hero), with "Nightmare" starting 200 ms after "The". The prompt enters 400 ms after that (360 ms, enter) | SandText Title MI, SandReveal Dir (1, 0) |
| Idle | The echo settles at Calm 0.55 and breathes on a 5 s cycle. The prompt breathes between 0.75 and 1.0 over 4000 ms | Time only |
| Confirm | The prompt's echo collapses (80 ms), then a 2-step datamosh hits the logotype (133 ms) | MF_UI_TimeSlice Amount |
| Exit | The logotype **persists**. It scales to 50% and moves top-left over 500 ms (move) while the menu forms | render transform, this one move only |

**Sound.** A swell peaking 980 ms into the form. Confirm gets a thump and a short pour.

### Main menu (WBP_MainMenu, WBP_SandButton)

**Layout.**
- The logotype sits top-left at 50%.
- Items are words in a column at x = 160 px: SemiBold, 40 px, on a 64 px pitch.
- Items: Continue, New game, Settings, Credits, Quit.
- No icons and no plates. The live bedroom sits behind the scrim.

| Beat | Timing and easing | Material |
|---|---|---|
| Enter | Each item forms over 600 ms, staggered 60 ms down the column. The first focus is live at 200 ms | SandText Menu MI Reveal |
| Idle | Resting words sit at energy 0.28. The focused word pours grain, with the vortex circling on its left | SandVortex render opacity |
| Focus | The new word lights up over 160 ms. The old word dims over 240 ms and its echo lingers for 4 steps (267 ms). The vortex fades out over 80 ms and back in over 160 ms. It never slides | State.R, Calm |
| Confirm | The echo collapses (80 ms) with a 166 ms glint. The other words disperse over 240 ms, staggered 30 ms outward. The chosen word holds 120 ms, then disperses over 420 ms. The next screen starts forming at 240 ms | State.G, State.A |
| New game | Bury over 900 ms, hold black for 300 ms, then the wake-up cinematic | SandWipe Coverage |

**Sound.** Tick on focus, thump on confirm. New game gets a 1200 ms pour plus a drone held through the black.

### Pause (WBP_Pause)

**Layout.**
- The world is frozen behind MI_UI_Scrim_Pause, held at #262626 or darker behind text.
- Top-left, the goal as one sentence: "Get dressed and leave the house." (30 px Medium).
- Below that: Resume, Settings, Start the day over, Quit to title.

| Beat | Timing and easing | Material |
|---|---|---|
| Enter | A 2-step datamosh freeze (133 ms, post process). The scrim comes in over 200 ms. Items form over 360 ms, staggered 40 ms. Input is live at 120 ms | PP via MPC, scrim MI, SandText |
| Idle | Grain keeps moving while the world is still. That contrast is the point | Time with Ignore Pause |
| Focus, confirm | Same as the main menu | shared WBP_SandButton |
| Exit | Items leave over 240 ms and the scrim over 200 ms. Pressing pause during the enter resumes instantly | |

**Sound.** A tape-stop, with the world low-passed to 800 Hz. On resume the filter opens over 200 ms.

### Settings (WBP_Settings, SettingRow widgets)

**Layout.**
- Categories on the left at 32 px: Display, Audio, Controls, Accessibility.
- Rows on a 56 px pitch: label on the left (Medium), value right-aligned (SemiBold), both 26 px.
- One sentence at the bottom describes the focused row (22 px, #B0B0B0).
- Reduce Motion, Flashing Effects and Text Size appear under both Display and Accessibility. Returnal spreads its options the same way.

| Beat | Timing and easing | Material |
|---|---|---|
| Enter | No sand on a utility screen. Rows fade in with an 8 px rise over 240 ms, staggered 20 ms, capped at 160 ms total | opacity, translation |
| Focus | The label brightens over 160 ms, and only the value gets sand energy | SandText on the value |
| Slider | The fill moves at once. The old value lingers as a trail that drains over 240 ms, which is the time echo on a slider | M_UI_Meter, MF_UI_TrailFill |
| Switcher | Both options are visible: #F0F0F0 for the chosen one, #8C8C8C for the other, separated by spacing only. The old option disperses over 160 ms while the new one forms over 200 ms | State.R per option |
| Apply | Changes apply instantly and preview live, so Reduce Motion stills this very screen. A resolution change triggers a 15 s revert ring | MF_UI_RadialTimer |

**Options.**
- Reduce Motion, Flashing Effects, Text Size.
- Background Opacity, Subtitle Size and Background.
- Hold or Toggle to interact.
- Camera Shake and Motion Blur (0 to 10).
- Screen Effects intensity.
- Audio/video offset.
- Prompts: Always, Minimal or Off.

**Sound.** Pitch-mapped slider ticks and clicks. No confirm thump.

### HUD and prompts (WBP_HUD, WBP_InputHint)

**Layout.**
- Almost nothing on screen (Hellblade II, Silent Hill 2).
- The goal sentence shows bottom-left for 4000 ms at the start of the day and whenever the Goal button is pressed.
- Prompts are anchored to the object. Each one is a key glyph inside a 40 px SDF ring, plus a verb such as "Put on" (26 px SemiBold).
- The first prompt is the teen turning their head toward the object.
- When Prompts is set to Minimal, the glyph waits until the player has been in range for 2000 ms.

| Beat | Timing and easing | Material |
|---|---|---|
| Enter | The ring draws over 240 ms and the verb fades in over 240 ms | M_UI_Ring: SDFRing, RadialTimer |
| Focus | Brightens from #8C8C8C to #F0F0F0 over 160 ms | VertexColor |
| Hold | A 500 ms hold fills the ring with a bright head. Releasing early drains it at twice the speed | RadialTimer Progress, Head |
| Complete | The ring collapses (80 ms) and the verb disperses (240 ms) | |
| Exit | A 160 ms fade, no sand | |
| Battle | "Your turn" forms over 360 ms. The damage trail holds 400 ms, then drains over 600 ms; tune by feel, since no source gives timings | MI_UI_Meter_Garment, MI_UI_Ring_Parry |

**Sound.** Prompts appear silently. Holds rise in pitch. Completion gets a clunk and a rumble.

### The phone (BP_Phone, WBP_Phone)

**Layout.**
- A widget component in the teen's hand, rendering to a 512 by 1024 target.
- The time is huge, in ExtraBold at a quarter of the screen height, with messages below.
- A notes screen titled "What I know" (34 px SemiBold) lists the kept knowledge, one sentence each.
- **The phone is where knowledge lives.** As in Alan Wake 2, opening it doesn't pause the day.

| Beat | Timing and easing | Material |
|---|---|---|
| Raise | 450 ms (move). Depth of field pulls focus to the phone and the room blurs | camera, not UI |
| Screen on | 120 ms. The clock forms over 360 ms. Rows rise 8 px and fade in over 240 ms, staggered 40 ms | SandText on the clock only |
| Idle | Each new minute, the old digits disperse over 240 ms and the new ones form over 360 ms, leaving a 4-step echo | TimeEcho |
| Lower | 350 ms. The screen collapses to black in 80 ms | |
| New knowledge | A buzz and a 120 ms rumble, then the line "You will remember this." with the fact, held 3000 ms | text, haptic and sound together |

Redraw the widget component only on change: the minute, input or a notification. Inside the world GetUserInterfaceUV doesn't apply, but the existing functions measure pixels with ddx/ddy, so they still work.

### Day rollover (WBP_DayRollover)

This is the hero screen. Prototype it first.

**Layout.**
- Black sand.
- "7:00" in ExtraBold at 220 px, left of centre.
- Below it, "Third morning." in SemiBold at 40 px.
- Below that, up to three knowledge sentences in Medium at 30 px, newest first.

**The idea.** The sand that buries the failed day becomes the sand that writes what you learned.

- Knowledge learned today forms from grains and gets the light sweep.
- Knowledge from earlier days is simply there, at rest ink.

That separates new from kept without colour or labels.

| Phase | First time | Repeat | What happens | Material |
|---|---|---|---|---|
| A. Freeze | 0 to 400 ms | 0 to 300 ms | Time dilation drops to 0.05 over 150 ms. Four ghosts trail the frozen frame, block smear runs in 15 Hz steps, and the letterbox grows to 2.39:1 over 300 ms | post process: the existing PP time-echo material and function (internal asset names) plus BlockSmear, set through MPC |
| B. Bury | 400 to 1300 ms | 300 to 900 ms | Sand falls from the top | SandWipe Coverage 0 to 1, FallBias 0.55 |
| Silence | 1300 to 1600 ms | none | Black | |
| C. Remember | 1600 to 2800 ms | 900 to 1500 ms | "7:00" forms over 600 ms, rising from the burial (Dir 0, -1). The day line follows 200 ms later. New sentences form over 600 ms each, staggered 150 ms, each with one sweep. Kept sentences cut in | SandText, LightSweep |
| D. Hold | 2800 to 4300 ms or until input. A prompt appears at 1500 ms | 1500 to 2100 ms, skippable after 600 ms | Still. Glints on new lines only | |
| E. Wake | 4300 to 5100 ms | 2100 to 2700 ms | The text disperses upward over 420 ms and the sand unburies over 800 ms into the wake-up camera. The only reverse in the game, because time rewinds | SandWipe 1 to 0 |

A skip after 600 ms jumps to phase E. Any sentence not yet shown cuts in first, so no knowledge goes unseen.

UI materials can't sample the 3D scene. So phase A is post process, and the widget only sets MPC scalars on events.

**Reduce Motion.** Fade to black over 200 ms. Text fades in over 150 ms, with the newest sentence first and brightest. Hold for 1500 ms or until input, then fade into the morning over 300 ms.

**Sound.**
- A sting, then a 400 ms tape-stop locked to the time dilation.
- A pour across phase B, then 300 ms of silence.
- A clock tick as each sentence starts forming.
- The alarm's first beep starts phase E, and the unbury reveals on the second beep.
- Rumble: 200 ms at the freeze, 80 ms per new sentence.

### Loading

**Layout.**
- Black.
- A 40 px ring in the bottom-right corner, with a comet head circling once per 1200 ms.
- One kept sentence or hint at 30 px Medium.
- No "Loading" word.

| Beat | Timing | Material |
|---|---|---|
| Threshold | Show nothing for loads under 300 ms. Otherwise show for at least 800 ms | |
| Enter | The ring comes in over 240 ms and the sentence forms over 600 ms | M_UI_Ring, RadialTimer Head, SandText |
| Exit | The ring fades over 160 ms and the sentence disperses over 420 ms. The destination unburies over 800 ms | SandWipe |

A blocking OpenLevel stops Slate drawing, so prefer level streaming. If a hard load can't be avoided, end on a deliberate still (sand-black with a static sentence) so the freeze reads as calm.

**Sound.** Room tone, with a tick every 1000 ms in phase with the ring.

## Part 4. Material kit

### Reuse

| Function | Reuse on |
|---|---|
| MF_UI_SDFRoundRect | dialog focus field only. Never a visible box around words |
| MF_UI_SDFRing | prompt, loading and parry rings |
| MF_UI_RadialTimer | hold fill, loading comet, revert timer |
| MF_UI_TrailFill | slider value echo, garment damage trail |
| MF_UI_EdgeGlow | low halo on the focused prompt ring only |
| MF_UI_SandReveal | every directional form |
| MF_UI_TimeSlice | 2-step datamosh in UI (title confirm, pause) |
| MF_UI_TimeEcho | focus lag, phone minute, rollover text; change its breathe period to 5 s |
| MF_UI_SandGrain | grain and glints everywhere; the sweep multiplies its outputs |
| MF_UI_SandDissolve | threshold under SandReveal and SandWipe, unchanged |

MF_UI_SandShape and MF_UI_SandFlow stay inside the existing masters. Those masters are SandText, SandButton, SandVortex, SandWipe, SplatLogo, Ring, Meter, Panel and Scrim. New screens get **new instances, not new masters**.

### Missing

1. **MF_UI_Ease.**
   - Inputs: `P`, `Delay`, `Span`, and `Curve`, which picks one of the seven closed forms via a static switch.
   - Built from plain math nodes, so it folds to a per-draw uniform on a parameter.
   - With Delay taken from UV, it becomes per-letter stagger.
   - It replaces most UMG keyframing.
2. **MF_UI_LightSweep.**
   - Inputs: `UV`, `T`, `Width` (0.18), `Angle` (20°). It outputs the band mask.
   - About 10 instructions and no texture samples.
3. **MF_UI_BlockSmear.**
   - Inputs: `UV`, `T`, `Amount`, `BlockPx` (16), `Dir`.
   - It quantises UV into blocks, offsets each block from the noise texture's G channel at `floor(T * 15)`, and drags along `Dir`.
   - It returns a UV, not a colour, so the same function serves UI (sampling a retainer texture) and post process (sampling the scene). Datamosh then exists in exactly one place.
4. **MPC_UI.FxIntensity.** A scalar set by the Screen Effects slider, which multiplies echo and datamosh. Turning Flashing Effects off zeroes glint and sweep gain through the same MPC.

**No new textures or fonts.** New noise goes in T_UI_SandNoise's free R, G and A channels. Darker Grotesque in Medium, SemiBold and ExtraBold covers every screen. F_FoA_Mono exists but isn't used. The clock sits in a fixed-width, right-aligned box so the digits never jitter.

### Prototype order

1. The day rollover, phases B to E, in WebGL with the real noise and token curves, then in UMG with MF_UI_Ease.
2. Main menu focus: the 4-step echo trail and the vortex.
3. The title logotype's form-hero and its persistent move to the menu.
4. The hold prompt ring with rising-pitch audio.
5. The light sweep on new knowledge.

Each prototype ships with its Reduce Motion version beside it. A prototype without one isn't finished.

## Part 5. The AAA pass in Unreal (2026-11-09): which reference informed which screen

The v4 build in UMG. Each line names the reference behind the choice and what was taken from it. Motion is material-driven through M_UI_SandText (one master, instances per use) and short self-stopping 60 Hz timers, or widget Tick where the world is paused.

| Screen | Reference | What it gave the screen |
|---|---|---|
| Boot | Inside, P.T. | A fast, quiet start on true black. Three 2 s cards (0.2 s black, 0.5 s ease-out in, 0.9 s hold, 0.4 s out), any key, click or pad button skips the current card, and the title arrives about 5 s after the first logo (it was about 14 s). Partner marks only fade; the Hayba mark gathers from grains. |
| Title | Alan Wake 2, Silent Hill 2 (2024) | Large type over the live room, no plate. The logotype gathers from sand left to right over 1.5 s (Reveal on MI_UI_SandText_Title). The time echo runs only while the letters gather and is gone at rest. Input is live from the first frame. |
| Main menu | Resident Evil Village, Silent Hill 2 (2024) | Plain words with no boxes. Focus shows by brightness and the grain vortex. The words gather from sand down the column, 60 ms apart. No datamosh at rest: the dream preset's menu glitch timer is cleared by the front end. |
| Pause | Resident Evil 7, Dead Space (2023) | The frozen frame tears into rows for 0.3 s (Tear on M_UI_Scrim), then settles under the scrim. The goal line and the words form from sand, 50 ms apart. Driven by widget Tick, because world timers stop while paused. |
| HUD objective | Resident Evil Village, The Last of Us Part II | The objective gathers from sand over 0.8 s with each beat, then quiets to half brightness after 6 s, so it is there when you look and out of the way when you don't. |
| Subtitles | The Last of Us Part II (subtitle background option) | A soft dark halo under the line instead of a box, with a 0.26 s fade and a 6 px rise for each new line. |
| Hint rows | Silent Hill 2 (2024) | Key and verb pairs separated by space only, dimmed to rest grey (no "/" separators). |
| Phone | Dead Space (2023), Alan Wake 2 | Diegetic: the phone is an object in the room and opening it does not pause the day. The text is final, from docs/design/story/script.md section 3. |
| Rollover and loading | P.T., Inside | The loop resets in place, with no loading word; sand buries the failed day and the new morning gathers from it. |

All UI ink is neutral grey. UMG draws after the monochrome post-process, so any warm tint in a UI colour would show on screen.
