# Chess Shorts generator

Generate the existing HTML preview, then optionally export a 1080×1920 MP4.
Run commands from the project root. Configure the position, annotated sequence,
pauses, meme and music in `src/generate_sequence_animation.py` as before.

## HTML preview

```bash
source .venv/bin/activate
python src/generate_sequence_animation.py
```

Open `output/sequence_demo.html` and click Play Sequence. The export step does
not replace or edit this file.

## Trigger the reaction video from moves

Add `(meme)` to the annotated sequence to choose when the reaction video starts:

```text
(meme) e4(1s) e5(1s) Nf3
e4(1s) e5(1s) (meme) Nf3
e4(1s) e5!!(meme)(3s) Nf3
```

A standalone `(meme)` runs between moves, **after the previous move's pause**.
An attached `(meme)` runs **when that move lands**, before its pause. Keep the
pause suffix last, as in `e5!!(meme)(3s)`. Neither form adds a delay.

When a trigger is present, the video waits on its first frame with no audible
meme audio. Once triggered, it plays and loops independently of chess timing.
Repeated triggers are ignored until Replay Sequence resets playback. With no
`(meme)` in the sequence, the video starts immediately as before. Music and
chess sounds keep their existing behavior. If no meme file is configured,
triggers do nothing. The HTML preview and MP4 exporter use the same timeline.

## Video export setup (Ubuntu)

FFmpeg needs the `x11grab` and `pulse` input devices and the `libx264` encoder
(the Ubuntu FFmpeg package supplies these). Install the export dependencies:

```bash
sudo apt-get install ffmpeg xvfb xauth pulseaudio-utils
source .venv/bin/activate
python -m pip install -r requirements-export.txt
python -m playwright install chromium
```

On a minimal Ubuntu installation, install Chromium's system libraries too:

```bash
python -m playwright install-deps chromium
```

Verify audio connectivity in the same user session before exporting:

```bash
LC_ALL=C pactl info
```

`Server Name: PulseAudio (on PipeWire 1.0.5)` is supported. A running native
PulseAudio server is also accepted, but the **legacy `pulseaudio` executable is
not required, installed, or launched** by the exporter. `pulseaudio-utils`
provides the `pactl` client; keep your existing PipeWire audio backend. Run as
your normal desktop user, not with sudo, so the session audio socket is accessible.

Use Playwright's downloaded Chromium, not the Snap launcher: Snap confinement
can prevent access to the private display or session audio sockets. `--chromium /path/to/chromium`
can select another compatible non-Snap binary with H.264/AAC playback support.

## Export

```bash
source .venv/bin/activate
python src/generate_sequence_animation.py
python src/export_video.py
```

Result: **`output/final_short.mp4`**, 1080×1920, 30 fps, H.264/yuv420p,
AAC stereo at 48 kHz / 192 kbps, CRF 18, with MP4 fast-start metadata.

For 60 fps:

```bash
python src/export_video.py --fps 60
```

Options:

```bash
python src/export_video.py --fps 30 --crf 18 --timeout 600
python src/export_video.py --output output/another_short.mp4
python src/export_video.py --html output/sequence_demo.html
```

`--timeout` is the maximum time allowed for playback, not a requested video
length. The exporter awaits the existing `playSequence()` promise, including
the last move's pause. It resets the page in a fresh browser profile each run.
A successful export replaces the selected MP4; a failed run preserves the last
successful MP4. Do not run two exporters targeting the same output concurrently.

### What gets recorded

- A private Xvfb screen containing only the 1080×1920 canvas, with no browser
  toolbar, development controls, desktop, or mouse pointer.
- A temporary null sink's monitor on your existing Pulse-compatible server containing Chromium's **actual mixed
  output**: chess SFX, meme audio, and music at their configured volumes.
- Meme and music continue during chess pauses exactly as in the preview. They
  are trimmed at sequence completion; export adds no music or sound changes.

Playwright controls Chromium; its built-in silent video recorder is **not**
used. FFmpeg records X11 video and PulseAudio audio against a common wall clock,
then trims startup/shutdown padding and encodes the final MP4. The exporter does not launch a PulseAudio daemon. It uses `pactl` to create a
uniquely named null sink on your running server and removes that sink and its
monitor on completion or failure. It does not change your desktop's default
audio devices or record the microphone.
The generator and all playback functions remain unchanged on disk. Only the
export browser receives CSS to hide controls and align the canvas at (0, 0), plus
instrumentation to observe completion and media playback.

This is automated **real-time capture**, not offline frame-by-frame rendering.
The workflow and start/stop conditions are repeatable, but OS scheduling, video
decoding, and CPU load can produce frame jitter or duplicated frames. It is not
byte-for-byte deterministic. Export on an otherwise idle machine; 30 fps is the
safer default, particularly with a large reaction video. Bit-identical rendering
would require changing the animation/media clock and is outside this pipeline.

### Validation and troubleshooting

The exporter preloads all configured media and checks for browser/media failures,
1080×1920 framing, H.264/AAC streams, expected duration, and an entirely silent
audio track. Missing media or a failed capture causes an error rather than
silently producing a video without its intended audio. Setting meme/music paths
to `None` in the generator remains supported.

Diagnostics are saved in `output/final_short_export_logs/` (or a directory named
for your selected output): browser canvas screenshots, FFmpeg/PulseAudio/Xvfb
logs, playback timestamps and successful media plays, audio levels, and ffprobe
metadata. Raw capture and browser-profile temporary files are removed on exit.

If capture fails, inspect `capture.log` and `pulse.log`. If loading fails, check
that all referenced local media exists and can decode in Chromium. The HTML is
served on a temporary loopback-only HTTP server during export, preserving its
relative asset URLs.

A quick independent file check:

```bash
ffprobe -v error -show_streams -show_format output/final_short.mp4
```

References: [FFmpeg X11/PulseAudio devices](https://ffmpeg.org/ffmpeg-devices.html)
and [Playwright Chromium launch options](https://playwright.dev/python/docs/api/class-browsertype#browser-type-launch).

### Integration test

With export dependencies installed:

```bash
python tests/test_video_export.py
```

This runs a separate four-second 60 fps export with generated test media. It
checks three distinct tones in the captured audio (meme, music, and a one-shot
SFX), continuous playback across pauses/loops, and video/audio timing using a
color change. Test media and output are temporary; your puzzle and assets are
untouched.

## Shorts composition

Layout settings live together in `src/renderer/layout.py`.
The 1080×1920 canvas uses a 960px board at (60, 180), inside a 1020px
warm frame starting at y=150. The 980×440 reaction panel begins at (50, 1200),
leaving 280px below it. `MEME_FIT = "contain"` preserves the whole source image
with warm padding when aspect ratios differ. Board pieces and all effects share
one scaled coordinate system. `RIGHT_UI_SAFE_AREA` moves annotation labels and
caption text inward; actual YouTube overlays vary by device and can still cover
part of the rightmost file on a centered board of this size.

Regenerate the HTML after changing these settings. `output/layout_preview.png`
is a single representative frame of the updated composition.


## Renderer architecture

Edit the demo position, annotated line, and media settings in
`src/generate_sequence_animation.py`. Importing it no longer writes an output file;
call `generate()` or run the script. The scene compiler and compositor can also
be used directly for other positions without editing source or creating files.

| Component | Responsibility |
| --- | --- |
| `src/renderer/chess_state.py` | Existing SAN/annotation/timing parsing and legal move metadata; `compile_sequence()` copies the board and returns pieces, moves, and ordered events. |
| `src/renderer/layout.py` | Canvas, board, frame, safe areas, and reaction geometry shared by composition and export. |
| `src/renderer/scene.html`, `scene.css` | Board/frame, camera boundary, overlay layers, reaction panel, and styling. |
| `src/renderer/board.js` | Shared board-local square coordinates and placement. |
| `src/renderer/pieces.js` | Sprite lifecycle, captures, promotion, castling, and `animatePieceMove(move, onLand)`. |
| `src/renderer/camera.js` | Shared eased camera transform around board, pieces, and overlays. |
| `src/renderer/effects.js` | Existing check highlights, arrows, annotation badges and labels. |
| `src/renderer/media.js`, `audio.js` | Meme/music playback and chess sound loading/playback. |
| `src/renderer/timeline.js` | Ordered event dispatch, landing callbacks, pauses, and replay. |
| `src/renderer/composition.py` | Serializes scene/configuration and embeds templates and runtime into one HTML file. |
| `src/export_video.py` | Captures the browser's final composition and audio into MP4. |

Flow: position + annotated SAN → compiled scene → composed HTML → timeline
handlers → piece movement → landing audio/check/meme → rook/promotion completion
→ annotation effects → move pause. Standalone meme events run between moves.
The board uses one logical coordinate system scaled by the composition. The
camera boundary is inside that scale and excludes the frame and reaction panel.

Add future visual behavior in the owning renderer and call it from the timeline;
new event types can be registered in `timelineHandlers`. Camera focus/zoom live in `camera.js`; cinematic capture effects are not implemented. Runtime
files are concatenated into a single script to retain file-based previews and the
existing playback/export hooks without a JS build tool.

Generate the representative test video:

```bash
.venv/bin/python src/generate_sequence_animation.py
.venv/bin/python src/export_video.py --output output/refactor_test.mp4
```

Run regression checks (browser/export checks require the normal export setup):

```bash
.venv/bin/python -m unittest discover -s tests -p 'test_*.py'
.venv/bin/python tests/test_meme_timeline.py
.venv/bin/python tests/test_video_export.py
```

The unit suite runs the existing Node audio assertions against a dedicated
five-move fixture. Parser and browser tests also use explicit positions/media,
so changing demo settings no longer changes their assumptions.

## Cinematic piece movement

`src/renderer/motion.py` defines `MOVE_DURATION` (milliseconds), `MOVE_EASING`,
`MOVE_SCALE_PEAK`, `MOVE_ROTATION` (degrees), `MOVE_OVERSHOOT` (fraction of a
square), and `MOVE_BLUR` (logical pixels; disabled by default). Regenerate HTML
after tuning them. `NORMAL_MOVE`, `FAST_MOVE`, and `DRAMATIC_MOVE` are reusable
presets derived from these defaults. Rotation and blur can be disabled with zero;
scale can be disabled with 1, and overshoot with zero.

`render_scene(..., movement_preset="DRAMATIC_MOVE")` selects a scene default.
Set `move["animation_preset"] = "FAST_MOVE"` on a compiled move to override it
(including its castling rook). The SAN parser is unchanged. The runtime entry
point is `animatePieceToSquare(element, square, presetName)` in `motion.js`.
It animates board-local position, scale, rotation and optional blur together,
then commits the exact destination and removes all transient animation styles.
Landing sound/check/meme triggers occur after settling, before the existing
promotion/castling completion and annotation/pause stages. Camera motion is independent; the piece-only demo disables it.

Generate the five-move comparison (`e4 e5 Nf3 Nc6 Bc4`):

```bash
.venv/bin/python src/generate_motion_demo.py
.venv/bin/python src/export_video.py --html output/motion_demo.html --output output/cinematic_moves_test.mp4
.venv/bin/python tests/test_piece_motion.py
```

The demo uses normal, fast, dramatic, normal, dramatic presets respectively,
with 0.8-second pauses, and leaves the main demo settings untouched.

## Destination-focused camera directing

- No suffix: retain the current shot; start the video at full-board framing.
- `@J`: ease back to wide (zoom 1, centered translation, zero rotation), 380 ms.
- `@K`: medium destination focus, desired zoom 2.05, 4×4-square context, 300 ms.
- `@L`: close destination focus, desired zoom 3.15, 2.5×2.5-square context, 240 ms.

`src/renderer/camera.py` centralizes zoom, local region size, per-shot duration,
rotation, easing, translation/zoom limits and overscan. Region size is in square
widths; timings are milliseconds. Regenerate HTML after changing configuration.

`camera_focus_destination(square, shot_type)` builds a local neighborhood around
the landing square. Near edges it shifts the neighborhood inward to retain real
board context. It rotates the region's corners and fits that region within the
viewport and translation limits. The resulting absolute pose is independent of
the source square and move distance. `camera_frame_move()` is retained as a
compatibility wrapper, with the same destination-only behavior. The destination
is centered for interior shots and slightly offset near board edges.

The camera interpolates from the current shot to the new pose and remains there.
It establishes the destination shot before piece movement; an approaching piece
can intentionally enter from offscreen. All chess layers share this transform,
while the frame clips the scene and warm overscan fills exposed margins. The
reaction panel stays fixed. Replay starts wide. Unmarked moves never reframe.

`BRILLIANT_PRE_HOLD = 120` pauses after camera framing and before piece motion
for `!!` moves only. `BRILLIANT_POST_HOLD = 180` adds to their existing post-move
pause after effects are shown. Both are configurable in `camera.py`, apply even
without a camera directive, and can be disabled with zero. Landing sounds/checks
and move-triggered memes still fire at actual landing; media keeps playing through
holds. Normal moves receive neither hold. No new effects or piece motion changes.

Camera parsing is unchanged: `parse_camera_directive()` removes one `@J`, `@K`,
or `@L` before existing evaluation/timing/meme/SAN parsing. Each compiled move
stores `camera_directive`, also referenced by its timeline event. Examples:
`Nf3!!@L(0.8s)(meme)` and `Nf3@L!!(0.8s)(meme)`.

Generate the browser demo:

```bash
.venv/bin/python src/generate_camera_demo.py
```

Open `output/camera_demo.html` and click **Play Sequence**. A sparse legal
position demonstrates `Nf3@L`, `Bc4@K`, the long queen entrance `Qd5@L`,
`Qe5!!@L` with extra holds, and `Kh7@J` returning wide. Intervening unmarked
moves preserve the shot. The current aggressive piece presets are unchanged.

```bash
.venv/bin/python -m unittest discover -s tests -p 'test_*.py'
.venv/bin/python tests/test_camera.py
.venv/bin/python tests/test_meme_timeline.py
```
