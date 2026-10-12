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
