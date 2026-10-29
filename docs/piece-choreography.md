# Stage 3 — Piece choreography

Stage 3 adds reusable piece movement recipes to the existing scheduler and
camera renderer. Captured-piece reactions, king reactions, lighting, particles,
and automatic tactical recipe selection remain outside this stage.

## Run the browser gallery

From the repository root:

```bash
.venv/bin/python src/generate_choreography_demo.py
python3 -m http.server 8000
```

Open <http://localhost:8000/output/choreography_demo.html>.

The gallery has 14 legal examples: white/black rooks, bishops, queens, knights,
pawn lift and legacy comparisons. Change the recipe to apply the same motion to
any displayed position. Toggle overlapping camera motion for a board-space
comparison. A live phase display identifies the inverted hang; the source video
has rook/bishop/queen bookmarks and slow playback. The generated child scenes use
the production renderer, not a separate demo animation implementation.

## Presets and selection

| Preset | Behavior | Duration |
|---|---|---|
| `LEGACY` | Existing `NORMAL_MOVE`, `FAST_MOVE`, or `DRAMATIC_MOVE` | Unchanged: 700 / 455 / 1050 ms |
| `LIFT_MOVE` | Eased travel with a small lift, scale peak and tilt | 420 ms |
| `KNIGHT_JUMP` | Higher lifted arc, larger scale peak and tilt | 500 ms |
| `BISHOP_SWEEP` | Perpendicular sweep and rotation along diagonal travel | 480 ms |
| `SPIN_WITH_HANG` | Generic staged full-turn motion | 570 ms |
| `ROOK_FLIP` | Stronger lift/scale and angular overshoot | 570 ms |
| `QUEEN_SPIN` | Sweep plus opposite spin handedness | 570 ms |
| `BISHOP_SPIN` | Lighter spin with a wider lateral sweep | 570 ms |

The existing behavior remains the default (`CHOREOGRAPHY_PROFILE="LEGACY"`).
Opt into ordinary piece-type recipes:

```python
scene = compile_sequence(board, "e4 e5 Nf3@K Nc6 Bc4@K", 0.7)
html = render_scene(scene, choreography_profile="REFERENCE")
```

REFERENCE selects knight jump for knights, sweep for bishops, and lift for other
pieces. It does **not** automatically spin every `!!`, capture or close shot.
Assign any recipe explicitly before rendering:

```python
scene["moves"][2]["choreography_preset"] = "SPIN_WITH_HANG"
scene["moves"][4]["choreography_preset"] = "BISHOP_SPIN"
```

Compiled moves and timeline events share their move objects before serialization,
so these changes apply to playback. Explicit `choreography_preset` takes priority;
`"LEGACY"` forces the original motion. Otherwise, an explicit `animation_preset`
also keeps that legacy preset, even with the REFERENCE profile. Castling retains
the sequential king/rook contract; the rook uses ordinary movement unless
`rook_choreography_preset` is explicitly provided.

The compiler adds moving `piece_kind` and `piece_color` metadata. It does not
change SAN/directive parsing or introduce tactical event logic. All recipes use
source/destination geometry, so no game, square, move number or color is hardcoded
into their animation behavior. Spin direction follows travel direction; the queen
variant reverses that sign.

## Inverted-hang timing

The reference rook becomes inverted around 31.70 s and stays near inversion through
31.83 s. The earlier rook example also holds around 10.97–11.10 s. These support
a distinct approximately 130 ms hang. The final quarter-turn is partly obscured
by bloom, so a clear full-turn finish and controlled settling are interpretations,
not recovered source keyframes.

| Time after piece launch | Motion |
|---|---|
| 0–200 ms | Ease toward 180° inversion; travel to 42% of the path and lift |
| 200–330 ms | Hold travel position, scale, lift and inversion |
| 330–480 ms | Accelerate rotation and travel toward the destination; slight overshoot |
| 480–570 ms | Settle onto exact square, scale 1, rotation equivalent to identity |

The end angle is 360°, not a backwards interpolation from 360° to 0°. Once both
tracks finish, the renderer writes exact square coordinates and cancels their
fill effects. The sprite then has no residual transform. Ordinary presets expose
their own arrival marker at 82%; spin presets expose the 480 ms arrival marker.
The scheduler observes actual travel-animation progress, not a wall-clock timer.
Sound, check and meme triggers still wait for **both** travel and deformation to
finish. The castling king triggers its existing landing events before rook travel.

## Transform ownership

```text
camera transient owners
  persistent board camera
    .piece                  left/top travel and logical square identity
      .piece-choreography   lift / sweep / spin / scale
        .piece-reaction     reserved, neutral; no Stage 4 behavior
          .piece-sprite     SVG image
```

New travel keyframes never write a transform. Deformation keyframes never write
left/top and never touch the camera or reaction element. Both animations share a
document-timeline start and their completion promises are joined. Cancelling
either cancels the other; placement is committed only after both finish.

The legacy compatibility path runs its original combined keyframes on `.piece`,
with neutral inner owners. Legacy and new choreography are alternative paths,
never competing writers. `motion.py` and its existing keyframes are unchanged.

Replay cancels subtree animations and removes all owned actors, including actors
temporarily absent from the square map during travel. A generation guard prevents
an interrupted old actor from being restored into the new position. Promotion
updates the innermost SVG; capture/en-passant removal remains immediate as before.

## Files and tuning

- `renderer/choreography.py`: centralized registry and all recipe parameters.
- `renderer/choreography.js`: pure keyframe builder, selection and paired playback.
- `renderer/pieces.js`, `scene.css`: layered actors, cancellation/replay ownership,
  promotion and dispatch to legacy/new animation.
- `renderer/chess_state.py`: moving piece kind/color metadata.
- `renderer/director.js`: recipe duration/arrival marker in existing timing plans.
- `renderer/composition.py`: profile configuration and explicit-preset validation.
- `generate_choreography_demo.py`: legal gallery scenarios and reference viewer.
- `tests/test_choreography.py`, `test_choreography_browser.py`: regression coverage.
  The existing timing-plan test loads the new resolver dependency.

Tune `SPIN_LAUNCH_DURATION`, `SPIN_HANG_DURATION`, `SPIN_FINISH_DURATION` and
`SPIN_SETTLE_DURATION` first. Then tune `SPIN_HANG_PROGRESS`, `*_LIFT`, `*_SCALE`,
`*_OVERSHOOT_ANGLE`, `*_SWEEP`, and launch/finish/settle easing. Ordinary travel has
separate durations, peak/arrival fractions, jump height and sweep width. Overshoot
is bounded in board coordinates. Ordinary 420–500 ms durations follow the observed
300–500 ms travel range; amplitudes are chosen tunable values, not measured ones.

## Tests

```bash
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python tests/test_choreography_browser.py
.venv/bin/python src/generate_motion_demo.py
.venv/bin/python tests/test_piece_motion.py
.venv/bin/python src/generate_camera_demo.py
.venv/bin/python tests/test_camera.py
.venv/bin/python tests/test_timing_camera.py
.venv/bin/python tests/test_meme_timeline.py
```

Browser checks cover inversion/hold, opposite directions and colors, independent
transform owners, camera overlap, exact final coordinates, no residual deformation,
cancel either track, full-sequence cancellation/replay, settled audio/meme timing,
castling, promotion, captures and en passant. The existing legacy suites also pass.
