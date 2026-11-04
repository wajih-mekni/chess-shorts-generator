# Optional aggressive brilliant mode

In `src/generate_sequence_animation.py`, set `BRILLIANT_MODE = "aggressive"` to
boost brilliant (`!!`) moves. The default is `"standard"`, preserving the tuned
HERO choreography, timing, reactions and camera tracks. The CLI also accepts
`--brilliant-mode aggressive`.

- `Qh7!!`: standard HERO, or aggressive HERO when globally enabled.
- `Qh7!!^N`: NORMAL override, including when global aggressive mode is enabled.
- `Qh7!!^A`: aggressive HERO regardless of the global mode.
- `^A` may also promote an unannotated move to aggressive HERO. It is a directing
  override like `^N`; only one tier override is allowed per move.

These treatments use the AUTO director. LEGACY remains unchanged. Explicit camera,
choreography, effect `NONE`, reaction and pause overrides retain their precedence.
A programmatic `brilliant_mode='standard'` on an individual move opts it out of a
global aggressive setting without suppressing HERO.

## Tuning

`AGGRESSIVE_HERO` in `src/renderer/directing.py` owns the overlay recipe:

| Parameter | Default | Meaning |
| --- | --- | --- |
| rotation | 12 | Peak whole-board rotation in degrees; supported range 0–20 |
| duration | 700 | Rocking duration in milliseconds |
| oscillations | 4 | Alternating oscillation cycles |
| damping | 1.5 | Decay exponent; higher settles faster |
| zoom | 0.16 | Additional camera scale at the punch |
| shakeTranslation | 26 | Tremble amplitude in logical board pixels |
| shakeCycles | 12 | Deterministic tremble cycles during the hit |
| impactStrength | 2.5 | Multiplier on the existing contact impact |
| lightingMultiplier | 1.6 | Light opacity multiplier, clamped to 1 |
| lightSizeMultiplier | 1.35 | Bloom/ring size and ring thickness multiplier |
| particlesMultiplier | 2 | Particle counts and bounded per-session budget multiplier |

Change `rotation` to 15 or 20 without changing animation code. Python validates
parameters before serialization. For experiments, `render_scene` also accepts
`aggressive_config={'rotation': 20}` and `brilliant_mode='aggressive'`.

The hit begins at the existing contact marker, alongside the impact flash. It
uses a deterministic damped sinusoid with explicit identity endpoints, not random
noise. The HERO hold/choreography continues underneath. This is a contact-aligned
music-drop treatment; it does not detect beats in an audio file. Authored pauses
remain unchanged, but sequence completion waits for the finite 700 ms effect tail,
even with `(0s)`.

A dedicated outer camera wrapper composes with the existing reframe, impact, HERO,
and persistent camera transforms. Pieces, board, captures, annotations, bloom,
rings and particles inherit the same rocking transform. Full-viewport wash/flash
remain screen-space overlays as before; the meme stays outside the camera.
Aggressive focused shots reserve additional framing room. An oversized themed
backing sized from the viewport diagonal covers large rotations even in portrait
and crop layouts; this extends the existing backing rather than inventing extra
chess squares. Large wide-shot rotations can intentionally crop board edges.

The common Web Animations track lifecycle handles completion, cancellation and
replacement. `camera.reset()`, `cameraMotion.reset()` and `resetPieces()` cancel
the aggressive track. No new timers or RAF loops are introduced.

## Compare

Run `.venv/bin/python src/generate_brilliant_demo.py`, then open
`output/brilliant_comparison.html` and click **Play Sequence**. It plays
`Nf3!!(1.5s) Nf6!!^A(1.5s) Nc3!!^VA(1.5s)` with labels for all three levels. Production
FEN, sequence and output are untouched.

## Verification

- `.venv/bin/python -m unittest discover -s tests -p 'test_*.py'`
- `.venv/bin/python tests/test_aggressive_browser.py`

The browser checks 12° and 20°, wide/medium/close shots at every board corner,
all three production layouts, backing coverage throughout the oscillation,
capture/check playback, deterministic replay, replacement and reset cleanup.

## Very aggressive (`^VA`)

`Qh7!!^VA` selects a third treatment: landing → punch zoom → two fast full
rotations → recoil → overlapping aggressive rocking → clean settle. Standard
`!!`, aggressive `!!^A`, and NORMAL `!!^N` retain their existing behavior. The
global `BRILLIANT_MODE` option retains its existing standard/aggressive choices;
`^VA` is an explicit per-move override.

`VERY_AGGRESSIVE_HERO` in `src/renderer/directing.py` controls only the new phase:

| Parameter | Default | Meaning |
| --- | --- | --- |
| spinTurns | 2 | Complete turns; integer 1–4 |
| spinDuration | 450 | Spin phase duration in milliseconds |
| spinDirection | 1 | +1 clockwise, -1 counterclockwise |
| spinZoomIn | 1.65 | Absolute punch scale before temporary safety scaling |
| spinZoomHold | 1.4 | Scale through the main spin |
| spinZoomRecoil | 1.04 | Recoil scale at spin completion, blending to 1 |
| spinPunchAt | 0.16 | Fraction of spin duration at the punch peak |
| spinRecoilAt | 0.70 | Fraction at which the final recoil begins |
| spinOverlap | 60 | Milliseconds of rocking overlapping the end of the spin |
| spinSampleInterval | 8 | Maximum spin keyframe interval in milliseconds |

`render_scene(..., very_aggressive_config={'spinDuration': 500})` can override
these values for experiments. The new recipe inherits the existing aggressive
rocking, impact, lighting and particle settings. It does not change that recipe.

One Web Animations track combines the spin with the original rocking keyframes.
Explicit `rotate(...)` angles carry 720° into the rocking tail; the final frame
remains at 720°, and cleanup writes exact identity without animating backwards.
The spin starts at the existing settled/landing boundary; the standard/aggressive
contact timing is unchanged. The 60 ms overlap avoids an identity pause between
phases. Timing is deterministic and aligned to the move, not automatic music beat
detection.

Temporary safety scale uses `abs(cos(angle)) + abs(sin(angle))`, reaching √2 at
45° crossings. The existing rotation-invariant backing also covers tall and crop
viewports throughout both turns. The strong zoom intentionally crops more board
context during the spin; it does not resize the permanent layout or move the meme.

Regenerate `output/brilliant_comparison.html` with
`.venv/bin/python src/generate_brilliant_demo.py` to see all three labeled moves:
`Nf3!!(1.5s) Nf6!!^A(1.5s) Nc3!!^VA(1.5s)`.

Run `.venv/bin/python tests/test_very_aggressive_browser.py` for actual browser
rotation (unwrapped through 720°), zoom, coverage sampled every 2 ms, backward
seeking, landing timing, capture/check integration, deterministic effects,
replacement and reset checks across fixed-meme, full-board and crop layouts.

### Return to the board during the final turn

`VERY_AGGRESSIVE_HERO` now includes:

```python
spinReturnWide=True
spinReturnWideAt=.50
```

With `Qh7!!^VA` (automatic focus) or `Qh7!!^VA@L` (explicit close focus),
the camera first frames the destination piece. Halfway through the spin, the
persistent camera starts returning to its centered wide pose, reaching that pose
at spin completion. The outer spin and rocking continue without interruption.
`@J` still explicitly requests a wide starting shot; omit it for the piece-focused
entrance.

`spinReturnWideAt` is a fraction of total spin time: `.25` starts earlier, `.75`
later. With a 1500 ms spin, `.50` begins the return at 750 ms. Set
`spinReturnWide=False` to retain the previous close-shot ending. This option only
changes VA. The normal/aggressive recipes and tuned spin parameters are untouched.

The return and spin share a Web Animations clock; reset cancels both. The director
records the final wide view for the next move. In crop layout, “wide” means the
layout's normal centered crop view, not resizing the oversized board to fit.

### Current three-second zoom timing

The VA zoom cycle now uses `spinZoomDuration=3000` independently of rotation:

- 0–1400 ms: smooth zoom inward (`spinPunchAt=1400/3000`).
- 1400–1600 ms: short peak transition (`spinZoomHold=spinZoomIn`).
- 1600–3000 ms: smooth zoom outward and return to the wide board
  (`spinRecoilAt=spinReturnWideAt=1600/3000`).

`spinDuration=2360`, `spinOverlap=60` and the inherited 700 ms rocking duration
make the spin/rocking finish at 3000 ms too. Rocking therefore overlaps the return
instead of adding a tail after the zoom cycle. The persistent camera return uses
ease-in-out. These times measure the VA effect from landing; piece travel and any
longer explicitly authored `(Xs)` pause are separate. Standard and aggressive
HERO timing is unchanged.
