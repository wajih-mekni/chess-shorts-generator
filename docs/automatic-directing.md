# Stage 6 — Automatic directing and production workflow

The production generator now defaults to `AUTO`: legal chess metadata and optional
notation select the existing Stage 1–5 systems. No animation library is duplicated,
no chess-engine evaluation is inferred, and no board warp is implemented.

## Edit and generate

Edit **`src/generate_sequence_animation.py`**:

```python
START_FEN = chess.STARTING_FEN  # Or any valid FEN, including Black to move.
SEQUENCE = ('e4@J e5 Nf3@K Nc6 Bc4 Nf6 Ng5! d5 exd5 '
            'Nxd5?! Nxf7!!@L(meme) Kxf7 Qf3+!@K Ke6 Nc3@J')
```

From the repository root, generate your configured sequence:

```bash
.venv/bin/python src/generate_sequence_animation.py
python3 -m http.server 8000
```

Open <http://localhost:8000/output/sequence_demo.html>. The HTML is the same renderer
used by MP4 export; it is not a special effect gallery. Optional one-command video:

```bash
.venv/bin/python src/generate_sequence_animation.py --video output/cinematic_short.mp4 --fps 30
```

Use `--fps 60` for 60 fps capture. `--output` changes the HTML path. Asset references
are made relative to that output. `MEME_PATH`, `MEME_VOLUME`, `MEME_COMMENT`,
`MUSIC_PATH` and `MUSIC_VOLUME` remain in the same production file.
`MEME_MODE = "fixed"` (the default, beside `MEME_PATH`) preserves the existing
fixed video/comment layer. Set `MEME_MODE = "off"` to omit the entire meme
container, video and comment. `LAYOUT_MODE` then selects `"safe"` (the default,
centered full-board portrait layout) or `"crop"` (the cinematic cropped layout).
Canvas size, directing, timing, audio and generation commands remain unchanged.
`"piece"` is reserved for future support and is not implemented;
unsupported modes raise an error. Setting `MEME_PATH=None` removes only the video.
Existing `(meme)` triggering still occurs at settled landing and safely does
nothing when the layer is off.

### Meme-free layout controls

Set these two values together in `src/generate_sequence_animation.py`:

| Production variant | `MEME_MODE` | `LAYOUT_MODE` |
|---|---|---|
| Original fixed meme | `"fixed"` | `"safe"` |
| Safe, all 64 squares | `"off"` | `"safe"` |
| Cinematic crop, no meme | `"off"` | `"crop"` |

Fixed memes always use the original composition; a valid `LAYOUT_MODE` is ignored
while `MEME_MODE="fixed"`. Unknown layout names fail clearly. Library calls to
`render_scene()` also accept `layout_mode="safe"` or `"crop"`; omitting it preserves
previous behavior. No CLI or export command changes are required.

Both modes render at 1080×1920. `fixed` retains the original 960 px board at
(60, 180), its 1020×1020 viewport and the fixed reaction area. `off` uses a
1032×1640 viewport at (24, 140), with an 808 px board centered at (540, 960).
All 64 squares remain visible in wide shots; existing K/L shots still deliberately
focus on a local neighborhood. The smaller wide board is intentional: full-board
visibility and motion clearance take priority over enlargement within 1080 px.

Tune output-pixel dimensions in **`src/renderer/layout.py`**:

- `FULL_BOARD_MAX_SIZE`: upper limit on the meme-free board size (960).
- `FULL_BOARD_SAFE_MARGIN`: minimum board-to-viewport clearance (112 per side).
  Actual board size is the minimum of the cap and the available viewport width
  and height minus twice this margin. Reducing it enlarges the board but reduces
  clearance for motion and effects.
- `FULL_VIEWPORT_SIDE_MARGIN`: viewport-to-canvas clearance (24 per side).
- `FULL_VIEWPORT_TOP_MARGIN` / `FULL_VIEWPORT_BOTTOM_MARGIN`: vertical viewport
  insets (140 each); unequal values shift the composition's vertical center.
- `FULL_CAMERA_EFFECT_MARGIN`: additional inset for focused camera framing (32),
  applied before the existing transient-motion safety calculation.

The board retains its 1080-unit logical space. Only its layout scale and centered
offset change. Camera bounds use the new viewport's inscribed safe square in
logical units; the extra portrait height remains available to choreography,
glows and particles. Effects still intentionally fade/crop at the viewport edge;
the margin does not promise visibility of every particle at every zoom.
Fixed-mode controls (`BOARD_SIZE`, `FRAME_PADDING`, `TOP_SAFE_AREA`) are unchanged.

### Cinematic crop controls

The crop layout uses a **1440×1440 board** centered inside a **1080×1800 viewport**
at (0, 60), retaining the 1080×1920 canvas. The centered wide shot crops 180 px
from each horizontal board edge. It does not stretch squares or change logical
piece coordinates. Medium/hero shots still use the existing destination-region
solver, including transient safety, with bounds derived from the crop viewport.

Crop-only output-pixel parameters in `src/renderer/layout.py`:

- `CROP_BOARD_SIZE = 1440`: physical board size before camera zoom.
- `CROP_VIEWPORT_SIDE_MARGIN = 0`: horizontal canvas inset.
- `CROP_VIEWPORT_TOP_MARGIN = 60` and `CROP_VIEWPORT_BOTTOM_MARGIN = 60`:
  vertical canvas insets and balance.
- `CROP_CAMERA_EFFECT_MARGIN = 24`: additional framing inset for motion/effects.

Increasing board size increases cropping and leaves less room for multi-square
tactical neighborhoods; the tested 1440 default balances wide scale and close
shot headroom. In this mode only, directed wide (`@J`, including AUTO choices)
shots pan the minimum distance needed to keep the destination square inside the
transient-safe area. Wide zoom stays unchanged. K/L shots retain their local
context, and playback/reset starts from the centered wide pose. A distant source
square or travel path may be cropped; this is destination-focused coverage.
Camera-disabled rendering still respects the caller's choice to disable motion.

Run `.venv/bin/python tests/test_meme_layout_browser.py` to verify all three layouts,
all K/L destination regions, maximum transient wide-board containment, playback
and replay, settled audio timing and crop-wide destinations on all 64 squares.
Preview HTML and 1080×1920 screenshots go to `output/layout_verification/`.

The built-in Stage 6 demo always uses the legal starting-position line above,
independently of later edits to your `START_FEN` and `SEQUENCE`:

```bash
.venv/bin/python src/generate_sequence_animation.py --demo
python3 -m http.server 8000
```

Open <http://localhost:8000/output/cinematic_demo.html>. To export that demo:

```bash
.venv/bin/python src/generate_sequence_animation.py --demo --video output/cinematic_demo.mp4 --fps 30
```

The 15-ply Short contains ordinary development, knight jumps, bishop travel,
captures, checking moves, king/victim reactions, `!`, `?!`, `!!`, all three camera
directives and a cyan animated hero hold. The annotations are artistic inputs,
not a claim of engine-verified move quality.

A non-starting position is also covered by the browser tests:

```python
START_FEN = 'r4rk1/1b1R3p/p1p1p3/Pp2Bp1q/nb2nQ2/7P/1P3PP1/6K1 w - - 0 1'
SEQUENCE = 'Qg3!!~queen-spin(meme)'
```

## Classification and pacing

Priority is explicit `director_tier`, then HERO, then TACTICAL, then NORMAL.

| Tier | Automatic trigger | Reading pause | Treatment |
|---|---|---|---|
| NORMAL | Quiet unannotated move, including ordinary castling | 280 ms | Type-based travel, small square accent, no particles/wash |
| TACTICAL | Capture, check, or an annotation other than `!!` | 650 ms | Medium destination shot, 55% impact, local glow/flash/sparks, capture fragments |
| HERO | `!!`, promotion or checkmate | 2800 ms | Strong choreography where appropriate, full impact, animated camera hold, wash/bloom/rings/dust |

The presence of promotion/mate is a chess fact; HERO is an editing choice, not a
correctness score. Captures/checks do not automatically become heroes. A checking
capture is TACTICAL unless another HERO trigger exists, but selects stronger
choreography than an ordinary short capture.

`(Xs)` takes precedence over automatic pauses, including `(0s)`. The original
extra 180 ms brilliant posthold remains for `!!`; a default brilliant hold is
therefore 2.98 seconds. The director does not change travel durations or the
launch → contact → settled → hold cue architecture. Camera and travel overlap;
arrival/exit tails remain included in playback/export completion.

## Choreography

Normal choices are pawn/rook/queen/king `LIFT_MOVE`, knight `KNIGHT_JUMP`, and
bishop `BISHOP_SWEEP`. Strong choices substitute `ROOK_FLIP`, `QUEEN_SPIN` and
`BISHOP_SPIN`; pawn/king movement stays restrained and knights retain their jump.

Strong choices apply to HERO moves, or to TACTICAL moves with `!`, a checking
capture, or a capture spanning at least four square widths (Euclidean distance).
Direction, lift, spin handedness, inverted hang and exact settling remain owned
by Stage 3. Promotion animates the pawn first and updates its sprite at landing.
Castling preserves sequential king/rook travel and restrained rook motion by
default.

## Camera

Explicit `@J` / `@K` / `@L` always wins: wide / medium / close. Camera instructions
do not themselves classify a move as brilliant or force hero lighting.

Without an instruction:

- NORMAL keeps a wide shot, or an existing medium shot if its destination is
  within 1.5 square widths of the current focus. It returns wide after a close
  hero shot or when the next quiet move falls outside the medium neighborhood.
- TACTICAL selects medium destination framing.
- HERO selects close framing, or medium when the move spans at least five square
  widths, providing more context for long travel.
- Castling selects wide, unless a camera directive overrides it.

These remain destination-based shots with the existing framing/safety clamps.
Shot context records the last directed shot/focus and resets for every replay.
Persistent camera state and transient impulses remain separate. TACTICAL impacts
scale the existing impact primitive to 55%; HERO uses 100%. An explicit `@L`
retains the original full impact. HERO camera holds use the tuned oscillation and
500 ms zoom pulse, even for a promotion/mate without `!!`.

## Reactions, lighting and palettes

The existing reaction resolver still checks eligibility. Automatic capture
selection is shrink for en passant (or an explicitly NORMAL capture), tumble for
TACTICAL, and knockback for HERO. Checks select recoverable `KING_RECOIL`.
Checking castling observes the rook, discovered checks use the real checker, and
victim lifetime stays separate from logical occupancy.

Lighting uses `LOCAL_ACCENT`, `TACTICAL_ACCENT`, or `HERO` according to tier.
Only HERO receives a whole-board wash and continuing dust/rings/bloom. Palette
priority is:

1. `!!` → cyan, including a brilliant checking capture.
2. Check/mate, `?` or `??` → red.
3. `!?` or `?!` → orange.
4. `!`, capture or promotion → green.
5. Otherwise cyan for the small local accent.

Palette names express visual language. There is no inferred evaluation, search,
engine score or hidden knowledge of a specific game. Existing annotation labels
and check overlays retain their semantics. Seeded particles and the fixed meme
layer work exactly as before.

## Inline choreography overrides

### Calm annotation override: `^N`

In AUTO directing, `Qh7!!^N` compiles to `director_tier='NORMAL'` while retaining
the `!!` annotation and Brilliant label. It uses normal piece choreography,
restrained automatic camera selection, LOCAL_ACCENT lighting and the NORMAL
reading pause (currently 280 ms). It adds no brilliant pre/posthold, hero wash,
bloom, rings, hero particles, impact tremble or hero zoom pulse. Chess check and
capture facts and their normal reactions remain intact.

`^N` can appear alongside existing suffixes, for example
`Nf3!!^N@K(meme)(2s)` or `Nf3~lift^N!!`. Explicit camera shots, choreography
aliases and `(Xs)` pauses retain their existing priority; even an explicit `@L`
does not add impact tremble to forced NORMAL. Avoid an explicit spin alias if a
calm piece move is desired. `^N` is an AUTO tier override; `--legacy` continues
to bypass automatic directing. Unknown or repeated tier directives are rejected.

One `~alias` may appear in a move token alongside the existing suffixes. The alias
registry is in `src/renderer/directing.py`; adding an alias for a future registered
preset does not require another parser branch. Unknown or repeated aliases fail
clearly before rendering. Aliases are lowercase, and select a preset regardless
of piece type. Examples assume a position in which the SAN move is legal.

| Exact keyword | Existing Stage 3 preset | Examples |
|---|---|---|
| `~lift` | `LIFT_MOVE` | `e4~lift`, `Qh5!~lift` |
| `~jump` | `KNIGHT_JUMP` | `Nf3~jump`, `Nc6~jump@K` |
| `~sweep` | `BISHOP_SWEEP` | `Bc4~sweep`, `Bb5!~sweep` |
| `~spin` | `SPIN_WITH_HANG` | `Qh5~spin`, `Bxf7+!!~spin@L` |
| `~flip` | `ROOK_FLIP` | `Rd7~flip`, `Rxe7+!!~flip` |
| `~rook-spin` | `ROOK_FLIP` | `Rxd5~rook-spin`, `Re7+~rook-spin` |
| `~queen-spin` | `QUEEN_SPIN` | `Qg3!!~queen-spin`, `Qh5+~queen-spin` |
| `~bishop-spin` | `BISHOP_SPIN` | `Bxc6~bishop-spin`, `Bxf7+!~bishop-spin` |
| `~legacy` | `LEGACY` (existing movement preset, normally `NORMAL_MOVE`) | `e4~legacy`, `Nf3~legacy` |

For example, all of these preserve annotation, camera, meme and pause parsing:

```text
Nf3~jump!!@L(meme)(2s)
Nf3!!@L~jump(meme)(2s)
Nf3!!(meme)(2s)~jump@L
```

An explicit choreography preset wins over the director's selected choreography.
It does not remove the annotation's lighting/hold treatment. Existing sequences
such as `Nxf7!!@L` require no syntax changes.

Other optional controls remain available to API callers: `director_tier`,
`choreography_preset`, `rook_choreography_preset`, legacy `animation_preset`,
`capture_reaction`, `king_reaction`, `effect_preset`, `effect_palette`, and
`effect_seed`. `NONE` disables an effect/reaction channel. A manually assigned
`pause` should set `pause_explicit=True`; notation `(Xs)` does that automatically.
These fields are not needed for normal production use.

## Integration and compatibility

`directMove()` in `renderer/director.js` copies a compiled move, chooses optional
presets and framing, and returns the next shot context. `buildMovePlan()` resolves
that copy through the existing Stage 1–5 systems. All renderers receive the same
copy. Neither the original sequence nor the logical chess board is rewritten.
The timeline commits shot context after successful completion, and initializes it
again for replay. Cancellation cleanup still belongs to the existing systems.

`renderer/directing.py` centralizes tier pauses/effects/impact strength, ordinary
and strong choreography maps, geometry thresholds and alias names. Detailed visual
amplitudes stay in `camera.py`, `choreography.py`, `reactions.py` and `lighting.py`.

The production entry point defaults to `DIRECTING_PROFILE='AUTO'`. For old output:

```bash
.venv/bin/python src/generate_sequence_animation.py --legacy --output output/legacy_sequence.html
```

This selects legacy timing, choreography, reactions and lighting. For library
callers, `render_scene(scene, directing_profile='AUTO')` activates the REFERENCE
stack by default. Explicit subsystem profile arguments are still respected.
The lower-level `render_scene()` default remains `LEGACY` directing to preserve
existing Stage 1–5 galleries and integrations; it does not silently direct their
hand-authored scenes.

## Validation

```bash
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python tests/test_directing_browser.py
```

Pure tests cover all aliases/suffix orders, invalid directives, tier selection,
palette precedence, explicit overrides, geometry, pacing and immutable inputs.
Browser tests cover the full starting-position Short, deterministic replay and
shot-context reset, the alternate FEN, Black to move, checking castling, en
passant, capture promotion, checking captures, inline overrides, exact final
coordinates, settled audio/meme timing, cancellation/reset and no ghost/effect
leaks. Existing gallery/legacy suites remain part of compatibility validation.

The real production demo was exported and visually inspected: 16.9 seconds,
1080×1920, H.264 at 30 fps (507 frames), AAC audio, and no playback errors.
The generated artifacts are `output/cinematic_demo.html` and
`output/cinematic_demo.mp4`; the export diagnostics remain alongside them.
