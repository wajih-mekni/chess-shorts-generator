# Timing foundation and camera composition

Stages 1–2, implemented 29 October 2026. The measurements in
[reference-motion-analysis.md](reference-motion-analysis.md) drive camera timing.
No new piece choreography, capture reactions, lighting, particles or automatic
tactical event detection are included.

## Playback and comparison

From the repository root:

```bash
.venv/bin/python src/generate_timing_camera_demo.py
python3 -m http.server 8000
```

Open <http://localhost:8000/output/timing_camera_demo.html>. The inspector shows
the generated composition, live cues and the local reference video. It includes
a link to the same sequence using the serial LEGACY profile. Reference bookmarks
are 11.1 s (pull-out), 18.8 s (push), and 27.3 s (hero hold), with slow playback and
60 fps stepping. No MP4 export is needed.

The demo uses `e4@K e5 Nf3!!@L(2.8s) Nc6@K Bc4@L Nf6@J`:

- `e4@K` starts the destination reframe alongside the piece.
- Unmarked `e5` retains the previous persistent pose.
- `Nf3!!@L` leads the piece slightly, pushes close, adds a temporary arrival accent,
  and keeps the authored hold moving with small drift and zoom pulses.
- `Nc6@K` / `Bc4@L` change tactical subjects; `Nf6@J` pulls wide during travel.

`render_scene(..., timing_profile="REFERENCE")` is the default. Use
`timing_profile="LEGACY"` for the previous camera → prehold → piece sequence.
The existing `generate_camera_demo.py` explicitly uses LEGACY as a regression
comparison. `camera_enabled=False` disables both persistent and transient camera
motion. The main generator automatically receives the new default when regenerated.

## Responsibilities

| File | Responsibility |
|---|---|
| `renderer/timing.py` | Profile selection, camera leads, recommended demo hero pause |
| `renderer/director.js` | Pure move plan: timings and enabled camera tracks, without DOM writes or new chess logic |
| `renderer/scheduler.js` | Named cues, animation-clock observation, parallel promise joining, observer cleanup |
| `renderer/timeline.js` | Connect plans/cues to existing pieces, annotations, audio, memes and camera primitives |
| `renderer/camera.py` | Persistent shots and transient amplitudes/timing, plus conservative framing margin |
| `renderer/camera.js` | Absolute persistent destination poses, interruption and reset |
| `renderer/camera_impulses.js` | Independent finite reframe, arrival-impact and hero-hold transforms |
| `renderer/composition.py`, `scene.html`, `scene.css` | Serialize configuration; nest camera owners inside the fixed board crop |

`motion.js` and `pieces.js` gain an optional observation callback reporting
the existing animation handle and arrival marker. Piece ownership is also retained
on cancellation so replay removes interrupted actors without ghost sprites.
Their keyframes, durations,
easing, scale, rotation, overshoot, promotion, capture and castling behavior remain
the same. `effects.js` gains a completion helper for the final existing fades.
Chess parsing/state, audio/media handling, layout and exporter code are unchanged.

## Scheduler and synchronization

Each move gets a pure `buildMovePlan(move)` and a disposable `MoveSchedule`.
The camera track begins immediately. REFERENCE waits only for the configured
camera lead before launching the piece, while LEGACY awaits the complete shot.
Tracks can overlap without becoming independent fire-and-forget tasks.

The cue order is `launch → contact → settled → holdStart → holdEnd → complete`.
`cameraStart` / `cameraEnd` occur independently. The historical name `contact`
means the **existing 0.80 arrival/overshoot keyframe**, not a simulated collision
or the exact first crossing of the destination. The scheduler reads this marker
from the piece keyframes and observes the actual Web Animation `currentTime`.
Pausing or cancelling the animation cannot leave a wall-clock arrival timer behind.
Instant motion emits contact once immediately before settled.

For a typical `!!@L` with the unchanged NORMAL preset, approximate times from
move start are:

| Track / cue | Time |
|---|---|
| Persistent camera transition | 0–400 ms |
| Piece launch | 120 ms |
| Reframe accent and settling | 0–520 ms |
| Arrival cue / impact start | 680 ms |
| Piece settled; sound/check/meme | 820 ms |
| Temporary impact ends | 870 ms |
| Hero drift/pulses | From settling through the authored reading hold |

The existing `onLand` boundary still triggers sound, checks and `(meme)` **after
the attacker settles**, before promotion or the castling rook animation completes.
Annotations and the reading pause still follow full move completion. Authored
`(Xs)` pauses remain exact; `!!` retains its existing additional 180 ms posthold.
The demo authors 2.8 s explicitly, producing a 2.98 s brilliant hold. No recipe
silently replaces user timing with a minimum duration.

Each move joins all its camera tracks before completing. `playSequence()` also
waits for camera tails and the final existing annotation/check fades, so the
exporter's existing completion promise remains valid. Replay restores pieces and
both camera systems. The debug subscriber API is
`timelineScheduler.subscribe(event => ...)`, returning an unsubscribe function;
events contain cue, move, plan, time and elapsed milliseconds.

## Transform ownership and drift prevention

```text
fixed chess viewport
  fixed layout scale
    reframe transient
      impact transient
        hero drift/pulse transient
          persistent #board pose
            board, pieces, highlights, arrows, labels
fixed meme/reaction sibling
```

Persistent `camera.pose` is an **absolute commanded target**, not the current
interpolated pose. Unmarked moves keep it; K/L set destination shots independently
of source distance, and J returns wide. Interrupting a shot starts from the actual
displayed transform. It never adds deltas to the preceding target.

Each transient wrapper owns its own Web Animation with identity endpoints.
Reframe overshoot, directional impact and hero drift/pulse can overlap without
writing to `camera.pose` or the persistent element. They settle back to identity,
preserving the selected shot. `cameraMotion.finished` joins active tracks;
`cameraMotion.reset()` cancels and clears them. Motion is deterministic across
replays, with direction derived from the move. The impact primitive is currently
used only by explicit `@L`, not automatically by captures/checks.

The destination solver reserves room for the combined transient envelope. The
existing overscan background and fixed viewport prevent transparent gaps. The
meme stays outside every chess camera transform.

## Important tuning parameters

All durations below are milliseconds; rotation is degrees; transient translation
is logical viewport pixels before the fixed layout scale, independent of shot zoom.

| Location | Parameters / defaults | Basis |
|---|---|---|
| `timing.py` | `CAMERA_LEAD_NORMAL=0`, `CAMERA_LEAD_CLOSE=60`, `CAMERA_LEAD_HERO=120` | Chosen overlap controls; not recovered editor keyframes |
| `camera.py` | `REFERENCE_CAMERA_MEDIUM_DURATION=300` | Chosen quick tactical reframe |
| `camera.py` | `REFERENCE_CAMERA_CLOSE_DURATION=400`, `REFERENCE_CAMERA_WIDE_DURATION=450` | Measured ~400 ms push and 400–500 ms pull windows |
| `camera.py` | `CAMERA_MEDIUM_ZOOM=2.05`, `CAMERA_CLOSE_ZOOM=3.15`, local regions 4 / 2.5 squares | Existing destination shot strengths; solver constrains the visible region |
| `camera.py` | Reference persistent rotations 0.35° / 0.6° | Restrained chosen amplitudes; ordinary source grids largely upright |
| `camera.py` | `CAMERA_REFRAME_*`, `CAMERA_IMPACT_*` | Chosen overshoot/settle and 190 ms arrival accent; no inferred exact shake amplitude |
| `camera.py` | `CAMERA_HERO_PULSE_PERIOD=500`, `CAMERA_HERO_DRIFT_PERIOD=640`, `CAMERA_HERO_TRANSLATION/ZOOM/ROTATION` | Approximate observed pulse period; stronger amplitudes from the [Stage 5 visual tuning pass](lighting-particles.md#visual-tuning-pass-before-stage-6) |
| `timing.py` | `REFERENCE_HERO_HOLD=2800` | Demo's authored pause, from measured 2.5–3 s hero holds |

Tune camera durations/leads first, then shot zoom/region, then transient amplitudes.
Keep `motion.py` presets independent: all three existing presets are preserved.

## Validation

```bash
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python src/generate_camera_demo.py
.venv/bin/python tests/test_camera.py
.venv/bin/python src/generate_motion_demo.py
.venv/bin/python tests/test_piece_motion.py
.venv/bin/python tests/test_meme_timeline.py
.venv/bin/python tests/test_timing_camera.py
```

Coverage includes parsing, audio priority and settled timing, presets and exact
piece placement, LEGACY ordering, REFERENCE overlap, authored pauses, meme timing,
animated holds, replay, paused/cancelled arrival observation, simultaneous
transient corner framing, camera-disabled behavior, completion tails and replay
after cancelling an ordinary piece, castling king or castling rook.
