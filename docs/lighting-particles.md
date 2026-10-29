# Stage 5 — Lighting and particles

Stage 5 adds a reference-like neutral theme and independent, finite lighting and
particle primitives. Stages 1–4 remain intact. Stage 6 automatic tactical
selection/pacing is not implemented.

## Browser demo

From the repository root:

```bash
.venv/bin/python src/generate_lighting_demo.py
python3 -m http.server 8000
```

Open <http://localhost:8000/output/lighting_demo.html>.

Nine scenarios cover ordinary local accents, cyan/green heroes, red checking
capture, orange tension, diagonal capture fragments, knight arrival sparks, a
five-second hero hold, and disabled lighting. Change treatment, palette or hold;
replay or reset while animations are active. The reference viewer has bookmarks
and slow playback. All child scenes use the production renderer, including
camera, choreography, reactions, annotations and settled audio/meme cues.

## Opt-in configuration and explicit selection

`LIGHTING_PROFILE="LEGACY"` is the compatibility default: original warm board,
no new effect nodes/tracks, unchanged motion and timing. Enable once:

```python
scene = compile_sequence(board, "e4 e5 Nf3!!@L(2.8s)", 0.7)
scene["moves"][2].update(effect_preset="HERO", effect_palette="CYAN")
html = render_scene(scene, choreography_profile="REFERENCE",
                    reaction_profile="REFERENCE", lighting_profile="REFERENCE")
```

REFERENCE uses the neutral board and `LOCAL_ACCENT` for an unspecified treatment.
`effect_preset` overrides that choice; `NONE` suppresses new effects while retaining
the neutral theme. `effect_palette` is independent of chess correctness. Disabling
the lighting profile disables even explicit effects. Invalid names fail before
rendering. These selectors are an API for Stage 6 to use later, not its automatic
director: neither `!!`, captures nor checks silently select a stronger treatment.

| Treatment | At contact | On capture (if present) | During authored hold |
|---|---|---|---|
| `LOCAL_ACCENT` | Small square glow | None | None |
| `TACTICAL_ACCENT` | Local glow, brief flash, arrival sparks | Local fragments | None |
| `HERO` | Local glow, brief flash, arrival sparks | Local fragments | Square glow, bloom, wash/vignette, rings, sparse dust |

A hero hold uses the existing timing plan. Choose a 2.8-second pause for the
reference's roughly 2.5–3-second hold language, or another authored duration.
Stage 5 does not extend authored pauses. Existing brilliant posthold timing stays
unchanged. Finite arrival tails are joined even when the reading pause is zero.

## Primitives and spaces

| Primitive | Owner | Behavior |
|---|---|---|
| `SQUARE_GLOW` | Board, below pieces | Saturated square and soft edge glow |
| `LOCAL_GLOW` | Board, below pieces | Short radial glow around arrival square |
| `HERO_BLOOM` | Board, below pieces | Larger breathing radial bloom approximation |
| `BADGE_RING` | Board, above pieces, below labels | Expanding/fading ring at placed badge; piece center if no badge |
| `CAPTURE_FRAGMENTS` | Board, above pieces, below labels | Direction-biased geometric exit burst |
| `ARRIVAL_SPARKS` | Board, above pieces, below labels | Small radial arrival burst |
| `AMBIENT_DUST` | Board, above pieces, below labels | Sparse, staggered drifting points around hero |
| `IMPACT_FLASH` | Fixed chess viewport | Short palette-core flash |
| `BOARD_WASH` | Fixed chess viewport | Breathing saturated wash plus vignette |

The board-local layers are children of `#board` and inherit persistent and
transient camera transforms. The viewport layer is a sibling of the camera
container inside `.board-area`; its wash does not pan or rotate. The viewport's
existing overflow clip contains everything, including glow near board edges.
The meme is outside both spaces. No new effect writes to camera, piece travel,
choreography, reaction, badge or arrow transforms.

The neutral board is an inline SVG with the same 8×8 geometry as the legacy asset.
Palette selection does not recolor existing chess annotation semantics or remove
check highlights. Bloom is a layered radial-gradient approximation, not a full
scene postprocess; non-rigid board warp remains outside this stage.

## Cue scheduling, determinism and lifecycle

`resolveLighting()` supplies an explicit recipe to the existing move plan.
`LightingSession` registers a move-local cue handler:

- `captureReaction`: emit selected fragments on the actual victim square, including
  en passant; `contact` is the fallback if reactions are disabled.
- `contact`: glow/flash/sparks at the attacker's arrival marker on its actual
  animation clock. It does not move existing sound/check/meme events.
- `holdStart`: start the finite hero treatment after annotation placement.

`MoveSchedule.onCue()` is separate from debug subscribers: rendering failures
join the schedule's promises and propagate through normal cleanup. Every effect
animation belongs to a session and the move scheduler. Completion includes tails;
reset or cancellation removes nodes, cancels WAAPI animations and releases cue
handlers. Replay rebuilds effects from the same inputs.

Particle descriptors use a string hash and seeded PRNG. The seed combines
`EFFECT_SEED` (or optional `move["effect_seed"]`) with source, destination, piece
kind/color and primitive name. There is no `Math.random()`, wall-clock seed or
replay counter. Identical inputs produce identical sizes, paths, rotation,
birth delays and lifetimes. Geometry is time-based rather than frame-count-based.
Each emitted batch shares the document animation timeline.

Particles use a bounded pool: ten capture fragments, ten arrival sparks and six
staggered ambient points in the default combined hero. The configurable maximum
is 64 allocated particles per move. Ambient points repeat with finite iterations
through the entire authored hold, so long holds do not allocate more nodes or
run out of activity. Rings also use a single finite repeating actor. All particles
fade out; no recurring wall-clock emitter or infinite animation survives cleanup.

## Rhythm and tuning

All palettes, theme colors, recipe composition, sizes, opacity, displacement,
particle count/lifetime, seed, budget and timing are in
`src/renderer/lighting.py`. Start with:

- `REFERENCE_THEME`: neutral light/dark squares, camera backing and canvas.
- `ACCENT_PALETTES`: cyan/brilliant, green/positive, orange/tension, red/danger;
  names are visual vocabulary, not automatic chess evaluation.
- `PULSE_PERIOD = 500`: recurring hero glow/color/ring rhythm.
- `EFFECT_FADE_DURATION = 180`: entry/exit envelope for held light.
- `LIGHT_PRIMITIVES`: glow size/opacity, wash strength, flash duration (150 ms),
  ring size/stroke/expansion.
- `PARTICLE_PRIMITIVES`: density, lifetime, sizes, travel range and directional bias.
- `EFFECT_PRESETS`: which primitives run on each cue, independently of palette.
- `EFFECT_SEED`, `MAX_PARTICLES`: reproducibility and cost limits.

The existing reference analysis measured hero pulses near 28.4, 28.93, 29.47,
29.93 and 30.47 seconds, with similar roughly half-second pulses in the rook hero.
These guide the 500 ms cadence. Glow, color breathing and repeated rings remain
active after landing, while sparse dust keeps moving. Fade envelopes bound the
start/end. Exact colors, glow strengths and particle counts are tunable design
choices; they cannot be recovered precisely from the graded flattened reference.

## Files and checks

- `renderer/lighting.py`: centralized theme, primitives and treatment recipes.
- `renderer/lighting_plan.js`: pure selection, seeded RNG and pulse envelopes.
- `renderer/particles.js`: pure deterministic finite particle descriptions.
- `renderer/lighting.js`, `lighting.css`: independent layers and owned playback.
- `renderer/composition.py`, `scene.html`, `scene.css`: theme and runtime assembly.
- `renderer/director.js`, `scheduler.js`, `timeline.js`, `pieces.js`: plan/cue
  integration, completion and reset.
- `generate_lighting_demo.py`: browser gallery and reference comparison.
- `tests/test_lighting.py`, `test_lighting_browser.py`: new regression coverage.
  The existing pure timing test loads the lighting selector dependency.

```bash
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python tests/test_lighting_browser.py
.venv/bin/python tests/test_reactions_browser.py
.venv/bin/python tests/test_choreography_browser.py
.venv/bin/python tests/test_timing_camera.py
```

Tests cover palette/profile validation, absence of Stage 6 selection, finite
particle budgets, deterministic replay, 30/60 Hz sampling, animated long holds,
space/transform ownership, simultaneous camera/choreography/reactions, exact final
placement, audio/meme settlement, disabled legacy behavior, reset/cancellation and
zero-pause tails. Additional checks reset during an active hero hold and inject a
rendering failure from an animation-clock cue, then verify cleanup and replay.
The gallery is also inspected visually in Chromium.

Optional production exports of the combined cyan hero:

```bash
.venv/bin/python src/export_video.py --html output/lighting_case_01.html --output output/lighting_stage5_30.mp4 --fps 30
.venv/bin/python src/export_video.py --html output/lighting_case_01.html --output output/lighting_stage5_60.mp4 --fps 60
```

Both exports were generated and verified at 1080×1920 with H.264/AAC, 3.8 seconds,
and no recorded playback errors: 114 frames at 30 fps and 228 frames at 60 fps.
These are output/capture checks, not a guarantee of rendering performance on every
machine. Effect-node budgets remain bounded independently of hold length.
