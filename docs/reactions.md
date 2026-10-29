# Stage 4 — Reactions and impact cues

Stage 4 adds independent victim exits and recoverable king reactions. It keeps
the Stage 1 scheduler, Stage 2 camera and Stage 3 choreography. Lighting,
particles and Stage 6 tactical recipe selection remain unimplemented.

## Run the browser demo

From the repository root:

```bash
.venv/bin/python src/generate_reaction_demo.py
python3 -m http.server 8000
```

Open <http://localhost:8000/output/reaction_demo.html>.

The 12 legal scenarios show captures from four directions and both colors,
shrink/tumble/knockback, queen check, checking capture, en passant, capture
promotion, checking castling and a legacy comparison. Choreography and camera
run simultaneously. Select optional overrides, replay, or reset during playback;
the cue inspector and visual-victim count expose the lifetime. The reference
viewer has reaction bookmarks and slow playback. Child scenes use the production
renderer, not demo-only animation code.

## Presets and metadata bindings

| Preset | Behavior |
|---|---|
| `CAPTURE_SHRINK` | Shrink and fade in place |
| `CAPTURE_TUMBLE` | Shrink/fade with 110° directional rotation and 0.35-square displacement |
| `CAPTURE_KNOCKBACK` | Stronger 0.65-square displacement, 28° rotation and shrink/fade |
| `KING_RECOIL` | Anticipatory 14° tilt, 1.12× scale and slight displacement; recover to identity |

Compatibility remains the default (`REACTION_PROFILE="LEGACY"`). Enable basic
metadata bindings once for an entire sequence:

```python
scene = compile_sequence(board, "e4 d5 exd5 Qxd5@K", 0.6)
html = render_scene(scene, choreography_profile="REFERENCE",
                    reaction_profile="REFERENCE")
```

REFERENCE binds captures to `CAPTURE_TUMBLE` and checks to `KING_RECOIL`; it does
not require individual assignments. Optional move overrides take precedence:

```python
scene["moves"][2]["capture_reaction"] = "CAPTURE_KNOCKBACK"
scene["moves"][3]["king_reaction"] = "NONE"
```

Overrides also work with the legacy profile; `NONE` disables a channel. Invalid
preset/channel combinations fail before rendering. Pure `resolveReactions(move)`
returns selections inside `buildMovePlan()`. Stage 6 can replace those basic
bindings without changing actor lifetime, transform ownership or playback.
No chess-game, move-number or specific-square behavior is hardcoded.

The compiler adds captured kind/color, en-passant and checkmate metadata. Existing
moving-piece/checker metadata, SAN/directive parsing and legality stay intact.
Mate uses the same recoverable king reaction; it does not remove or topple a king.

## Lifetime and timing

Python's chess compiler remains authoritative for the sequence. At capture launch
the browser removes the victim from its square-occupancy map, as before. A reaction
session retains that DOM actor in `renderedPieces` and a visual-only `ghosts` set.
It remains fully visible during early approach, then exits; it is never restored
as an occupant and cannot be mistaken for the attacker at the destination.
Its visual layer stays above the arriving attacker and below labels, so overlap
does not hide the tumble/shrink.
Legacy captures and `NONE` retain immediate visual removal.

Victim exits begin 120 ms before the choreography arrival marker, last 240 ms,
then remove the visual actor. The scheduler observes the attacker's actual WAAPI
animation clock, so pausing travel before the threshold does not trigger a reaction
on a wall-clock timeout. Instant travel has a settlement fallback. The scheduler
joins exits/recovery even with zero reading pause, so the exporter cannot truncate
them. Cancellation/replay removes ghosts and cancels reaction tracks.

King anticipation starts 150 ms before arrival and reaches its pose in 100 ms.
It holds until actual attacker settlement, then recovers over 180 ms. Existing
audio/check effects/meme triggers remain at settled landing, not the new reaction
cues. Added cues are `captureReaction`, `kingAnticipation`, and `kingRecovery`.

For direct checks, the king recoils away from the checking piece's destination.
Discovered checks use the actual revealed checker. Checking castling watches the
rook's animation and recovers after the rook settles; the original king-landing
audio/meme contract remains unchanged. En passant retains the victim on its own
square while the attacker travels to the different destination. Promotion updates
the attacker's sprite after landing as before.

## Direction and transform ownership

Victim knockback follows the normalized source-to-destination vector. Rotation
handedness follows horizontal travel, with vertical travel providing the fallback;
opposite approaches therefore tumble in opposite directions. King displacement
uses checker-to-king geometry. Neither behavior depends on piece color.

```text
transient camera owners
  persistent board camera
    .piece                  travel / exact board coordinates
      .piece-choreography   lift, sweep, spin and scale
        .piece-reaction     reaction transform and opacity
          .piece-sprite     SVG asset / promotion
```

Reactions only animate `.piece-reaction`. They never change square coordinates,
travel/choreography keyframes, camera state, or the fixed meme layer. Recovery
cancels its fill and clears the inline held pose. The legacy combined movement
still owns `.piece` unchanged; its inner reaction layer can be used independently.

## Tuning and reference evidence

All recipe values are in `src/renderer/reactions.py`. Start with:

- `CAPTURE_LEAD_DURATION`, `CAPTURE_DURATION`: overlap and exit pace.
- `CAPTURE_*_DISTANCE`, `CAPTURE_*_ROTATION`, `CAPTURE_MID_SCALE`: exit intensity.
- `KING_LEAD_DURATION`, `KING_ANTICIPATION_DURATION`, `KING_RECOVERY_DURATION`:
  anticipation, held pose and recovery rhythm.
- `KING_TILT`, `KING_SCALE`, `KING_DISPLACEMENT`: reaction amplitude.
- `CAPTURE_EASING`, `KING_EASING`: acceleration and settling.

The reference shows victim exits around 35.20–35.40 s and 39.20–39.40 s, with
king anticipation/recovery at 13.35–13.70 s and 26.15–26.40 s. Our approximately
200 ms exit/recovery durations adapt those observations to the existing arrival
markers. Exact lead offsets, angles, scale and distances are tunable choices,
not recovered authoring settings. No fragments, lighting or new camera shake
were added in this stage.

## Files and validation

- `renderer/reactions.py`, `reactions.js`: configuration, pure selection,
  keyframes, visual lifetime and recoverable reactions.
- `renderer/chess_state.py`: capture and end-state metadata.
- `renderer/composition.py`, `director.js`: profile/override validation and plans.
- `renderer/pieces.js`, `timeline.js`: actor retention, actual-motion observers,
  settled/completed boundaries and cleanup.
- `generate_reaction_demo.py`: production-renderer browser gallery.
- `tests/test_reactions.py`, `test_reactions_browser.py`: regression coverage.
  `test_timing_config.py` loads the new pure resolver dependency.

```bash
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python tests/test_reactions_browser.py
```

Browser checks cover all presets/directions, moving cameras, actual-clock
anticipation, separate transform owners, exact final occupancy/assets/coordinates,
king recovery, discovered checks, checking captures, checkmate, en passant,
promotion, castling, cancellation, active reset, replay, NONE overrides, instant
travel and zero-pause reaction tails. Existing choreography, timing/camera,
piece-motion, camera, meme and audio suites also pass.
