# Reference board motion: findings and implementation plan

Analysis of `assets/references/Reference.mp4`, **28 October 2026**. The original analysis changed no renderer behavior. Stages 1–2 were subsequently implemented on **29 October 2026**; see [implementation and tuning](timing-camera.md). Stage 3 is implemented; see [piece choreography](piece-choreography.md). Stage 4 is implemented; see [reactions and impact cues](reactions.md). Stage 5 is implemented; see [lighting and particles](lighting-particles.md). Stage 6 remains unimplemented. The goal is a reusable directing system, not a reconstruction of the reference game.

## Evidence and limits

The source is **1440×1800, 60 fps, 2,572 video frames, 42.867 s**; its container/audio runs to 42.921 s. It is 4:5, so its full-screen board framing should not be copied literally into our 1080×1920 board-plus-meme layout. The board takes over around **3 s**. The introductory portraits were excluded from the design analysis.

Inspection used:

- FFmpeg 15 fps contact sheets across the board section: one sample every 66.7 ms.
- Native 60 fps sheets around the early rook spin (10.70–11.50 s), king reaction (13.25–13.75 s), and five later spin/reaction sequences.
- Every decoded frame for luminance, frame-difference and color-coverage signals; these locate changes, **not camera pose**.
- Checkerboard grid-spacing measurements on clear frames to estimate relative zoom. Occluded/overexposed and warped frames were excluded from rigid camera estimates.
- Read-only inspection of the current renderer and baseline tests.

[Local inspection viewer](../output/reference_analysis/index.html) provides timestamp bookmarks, slow playback and frame stepping. [Signal plot](../output/reference_analysis/frame_signals.png), [60 fps CSV](../output/reference_analysis/frame_signals_60fps.csv), [early overview](../output/reference_analysis/overview_01.jpg), [late overview](../output/reference_analysis/overview_02.jpg), and [late detailed observations](../output/reference_analysis/late/observations.md) preserve the evidence.

A flattened video does not reveal authored keyframes, easing functions, original layer transforms, random seeds or the editor used. Timing below is approximate unless a specific native frame is cited. Full-turn counts hidden by a flash are inferred, not measured. Exact camera shake amplitude and ordinary-move overshoot cannot be isolated confidently from board deformation, zoom and sprite movement.

## What the reference actually does

The main grammar is **tactical travel → local reaction/accent → readable hold**, with occasional **hero entrance → impact bloom → animated hero hold**. Effects have different intensities and rhythms; it is not one maximal preset applied to every move.

| Time | Observation | Reusable implication |
|---|---|---|
| 3.4–8.9 s | Rapid slides/lifts and captures, colored squares, badges, small local bursts; camera reframes while pieces are already moving. Typical visible travel occupies roughly 0.3–0.5 s in these examples. | Ordinary move, knight lift, capture accent, overlapping destination reframe. |
| 7.8–8.4 s | Grid pitch falls from approximately 345 to 267 source pixels per square. Rook travel starts during the pull-out. | About 23% apparent scale reduction; camera and movement need parallel tracks. |
| 9.25–10.73 s | Warm orange/red treatment, darkening, spotlight/vignette, visibly bending grid lines. | A lighting treatment plus **non-rigid board distortion**, not just rotation/shake. |
| 10.75–11.48 s | Bright flash; rook turns sideways, hangs inverted around 10.97–11.10, accelerates out of the hang, then lands amid cyan wash. | Spin with an apex hold, independently timed camera travel and arrival effects. |
| 11.0–11.4 s | Clear grid pitch changes from about 535 to 324 pixels/square. | Strong pull-out, about 39% scale reduction over 0.4 s; not an automatic reset after every move. |
| 13.35–13.70 s | King enlarges and tips as the queen approaches; recovers as red check emphasis appears. The board mostly remains upright. | King recoil is a sprite reaction; it can anticipate arrival. Not evidence of a permanent falling king. |
| 18.8–19.6 s | Rook flip beside a still-visible victim; close shot then cyan arrival and pull-out. Grid pitch grows about 324→531 px/square from 18.8→19.2. | Roughly 1.64× relative push over 0.4 s; keep victim visuals alive during approach. |
| 27.35–30.85 s | Bishop spin, flash, then a long cyan hero treatment. | About 0.5 s entrance followed by roughly 2.5–3 s animated hold. |
| 31.50–35.05 s | Rook repeats the same motif: sideways→inverted→opposite sideways→flash; rings, glow and particles persist. | A reusable spin recipe, not game-specific choreography. Final quarter-turn is partly hidden by bloom. |
| 35.2–35.4; 39.2–39.4 s | Victims shrink/tumble and emit local fragments while attackers approach. | Stylized reaction timing, separate from logical removal and from attacker animation. |
| 39.75–42.2 s | Queen uses a spinning transit, briefly wider framing, then a green hero shot. | Destination emphasis is strong, but the reference also uses optional travel coverage; do not enforce one camera rule everywhere. |

The denser [grid-pitch curves](../output/reference_analysis/metrics/grid_pitch_curves.png) refine those sample windows: 8.00→8.50 s falls 344→260 px (24%); 11.10→11.50 s falls 540→284 px (47%); 18.90→19.30 s grows 324→538 px (1.66×). At 19.30→19.60 s, scale stays about 538–540 px while a matched grid boundary moves approximately 244 px left and 44 px up. This separates a held zoom from continuing translation. Sharp-grid pitch uncertainty is approximately ±2–4 source pixels; blurred frames were rejected. [Method and CSV](../output/reference_analysis/metrics/measurement_notes.md).

Grid measurements describe image-space scale, not authored zoom values. In many normal shots, the grid stays close to axis-aligned. Large sprite rotation should not be mistaken for large persistent camera rotation. Some hero frames visibly tilt, pulse and drift; periodic pulses are roughly half a second apart. Exact oscillation frequency varies and should be tunable rather than tied to a presumed soundtrack beat.

## Reusable visual vocabulary

**Camera.** Wide establishment, persistent medium tactical shot, destination hero close-up, quick reframe, overlapping push/pull, transient overshoot/settle, low-amplitude hero drift, repeated zoom pulse. A separate impact-shake primitive is useful, but the flattened reference does not justify adding strong random shake to every capture. Keep `@J/@K/@L` as absolute persistent shot instructions; transient motion must decay without changing their targets.

**Pieces.** A common lift/scale/eased-travel language, with deliberate spin-and-hang exceptions. Rook inversion is unmistakable; bishop and queen reuse the spin motif. A knight lift/jump and bishop sweep are useful type-aware defaults, but there is no proof that each piece always uses a unique motion. Current aggressive presets should remain selectable unchanged. King tilt/recover and captured-piece shrink/tumble/fragment are independent reaction recipes. Normal checks must not permanently topple a king or change chess state.

**Timing.** Ordinary travel is relatively quick, while hero entrances and holds expand time. Camera, attacker, victim, badge, flash and particles overlap rather than waiting in one serial chain. The near-inverted pause is especially important: a uniform 360° rotation would miss the reference's timing. Hero holds remain animated through drift, rings and light pulses.

**Color and light.** The underlying board is neutral gray/white with monochrome pieces, which makes saturated accents dominant. Blue/cyan, lime green, orange and red are used at several levels: source/destination squares, nearby tactical paths, checked kings, badge glows, local blooms and whole-board washes. Cyan `!!` hero treatments repeat; green heroes also occur. Do not infer chess correctness from color alone. A theme registry should offer a reference-like neutral palette while retaining our warm board theme.

**Particles.** Separate sparse ambient dust, localized capture fragments, arrival sparks, and badge rings. They have different lifetimes and attachment spaces. Particles should not obscure a piece throughout its readable hold.

**Warp.** Curved checker lines and uneven neighboring square widths cannot come from one translate/rotate/scale matrix. This detail needs an optional scene postprocess or mesh deformation later. It should not be imitated by excessive camera shake, or used as a reason to replace the renderer now.

## Fit with the existing renderer

The current modules are useful; keep the HTML compositor, compiler, media, audio, exporter, and logical square system.

- `chess_state.py` already compiles legal moves, camera directives, captures, promotions, castling and check geometry. Add **moving/captured piece kind and color**, and mate/end-state metadata where needed. Do not change SAN/directive parsing.
- `timeline.js` currently serializes camera → pre-hold → piece → effects → pause. Introduce a small **move plan and cue scheduler**, not a large monolithic animation function.
- `camera.js` already owns absolute persistent shots and interruption handling. Add a separate transform owner for transient pulses/shake/drift. Preserve destination-only K/L semantics and explicit-directive priority.
- `motion.js`/`pieces.js` own exact placement and the current 700 ms, 1.20× scale, 12° rotation, 0.12-square overshoot preset. Keep it intact as the legacy profile. Add choreography presets and a distinct sprite-reaction transform instead of competing animations on one CSS property.
- `pieces.js` currently deletes capture victims before travel. Separate visual lifetime from logical occupancy: the victim can remain as an effect actor until its exit finishes.
- Existing `onLand` means **settling completed**, and triggers sound/check/meme. Preserve that contract. Add separate cues such as `launch`, `contact`, `settled` and `holdEnd`; new visuals can use contact or anticipation without silently moving existing audio/meme triggers.
- Keep `effects.js` responsible for square highlights/arrows/labels. Add independently resettable lighting and particle modules. Board-attached effects share the chess camera; viewport washes stay inside the chess viewport; the meme remains outside both.

Proposed transform ownership:

```text
fixed chess viewport (crop, lighting wash; meme is a sibling)
  layout scale
    transient camera impulse (screen-relative within viewport)
      persistent camera pose
        board / square highlights / arrows / labels / local particles
        piece position
          choreography deformation
            reaction deformation / sprite
```

Contact/settled/finished must be explicit promises or cues. `playSequence()` must include trailing effects in its completion promise so the exporter does not truncate them. Replay cancels all tracks, clears ghost victims/particles, restores transforms, and reseeds variation.

## Recommended implementation stages

Each stage should produce a browser HTML demo and pass the existing regression suites before moving on.

| Stage | Change | Demonstration / acceptance |
|---|---|---|
| 1. Timing foundation | Pure director builds a move plan from metadata and existing directives; named cues and parallel tracks; centralized timing/profile configuration. New tracks initially disabled. | Legacy demo unchanged; existing parser/audio/meme/replay tests pass. A debug timeline shows cue ordering. |
| 2. Camera composition | Separate persistent shots from transient impulse, overshoot, pulse and drift. Configurable camera lead/overlap with piece travel. | K/L subject changes, J wide, ordinary moves with no new shot, impulse returns to identity while persistent pose survives; meme stays fixed. |
| 3. Piece choreography | Registry for slide/lift, knight jump, bishop sweep, spin-with-hang; preserve current presets. Reactions use their own channel. | Same recipes on different FENs, paths and piece colors; exact final square/scale/rotation; cancellation leaves no residual transform. |
| 4. Reactions and impact cues | Capture shrink/tumble/knockback; recoverable king tilt; visual victim lifecycle. Keep default sound/meme settlement timing. | Ordinary/en-passant capture, checking capture, promotion and castling; no duplicate pieces, false king removal or premature logical updates. |
| 5. Lighting and particles | Theme palette, square/local glow, board-only color flash, vignette/bloom approximation, seeded bounded bursts/rings/dust. | Color treatment changes without affecting geometry; fixed meme; deterministic replay and no leaked particles; check 30/60 fps browser/export cost. |
| 6. Automatic recipes and pacing | Map piece type + existing capture/check/annotation + explicit camera directives to reusable recipes. Sparse accents, hero holds reserved for important moves; per-move overrides possible. | Compact ordinary sequence, tactical capture/check sequence, explicit `!!@L` hero sequence, all on more than one position. No game-name or move-number matching. |
| Optional polish | Scene warp/postprocess only after the above produces the right rhythm. Prototype it separately; add a renderer adapter only if needed. | Compare curved-grid/glow reference detail, with text/piece readability and export performance verified. |

Suggested **starting values for new profiles**, not recovered source settings: ordinary travel 300–450 ms; spin entrance 500–700 ms with a short inverted hold; reframe lead/overlap 0–120 ms; impact visual 100–250 ms; ordinary reading hold 200–500 ms; hero hold initially 1–2 s, with a 2.5–3 s reference-style option. Keep our current motion values available and avoid automatically stacking all effects.

## Tests and first implementation choice

Baseline: eight Python unit tests plus Node audio assertions pass. The real-browser suites are separate scripts, not included in unittest discovery. Existing tests protect destination framing, persistent unmarked shots, exact settling, fixed meme, parser behavior and landing synchronization.

Add tests for independent transform composition; overlap timestamps; capture actor lifetime; reaction recovery; seeded particle replay; camera limits under impulses; final completion including effect tails; and visual comparisons in a disabled/legacy profile.

**Original recommendation: start with stages 1 and 2.** The largest difference from the reference is coordination and layered motion ownership, not the absence of more particle types. Then add choreography and reactions before lighting polish. The analysis above describes the original evidence and plan; [the implementation notes](timing-camera.md) document the completed timing and camera work separately.
