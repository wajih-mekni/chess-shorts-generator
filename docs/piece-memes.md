# Piece-attached reaction faces

The feature is independent of the existing reaction panel. In
`src/generate_sequence_animation.py`, `PIECE_MEME_MODE` controls the feature.
Use `"off"` for unchanged chess rendering.
Switch it to `"on"` to enable piece directives. With `"off"`, directives are
stripped before rendering: unknown IDs and option values inside a well-formed
`(piece:...)` or `(pm:...)` do not cause asset validation or media loading. You can leave your
sequence unchanged. Unclosed parentheses still produce a syntax error.

## Register and use an asset

Edit `PIECE_MEMES` in the production file:

```python
PIECE_MEME_MODE = "on"
PIECE_MEMES = {
    "HikaruLaugh": {
        "src": "assets/memes/hikaruLaughExecuseme.mp4",
        "type": "video",
    },
    "MyFace": {
        "src": "assets/memes/my_face.png",
        "type": "image",
        "shape": "circle",  # Optional per-asset defaults.
        "scale": 0.5,
    },
}
```

Paths are project-relative local files inside `assets/`. External URLs and paths
outside that directory are rejected when enabled. Only referenced assets load.
Image formats are browser-supported images, including transparent PNG/WebP and
SVG; video formats/codecs must be supported by the export browser. MP4/H.264 works
with the current browser. An unknown enabled ID or missing file produces a clear
Python error; decode failures produce a browser/preload error.

Move syntax (no spaces inside the directive):

```text
Qxh7!!(piece:HikaruLaugh)
Nf3~jump(piece:HikaruLaugh,when=start,dur=1.2,scale=0.5,x=0,y=-10,shape=rounded,loop=true)
Qh5!!^VA@L(piece:MyFace,when=land)
```

Target any piece by square with `(pm:e8:HikaruLaugh)`. Repeat parenthesized
directives for multiple faces on the same move, with independent options:

```text
Qh5(pm:e8:HikaruLaugh,dur=1.5)(pm:h8:MyFace,scale=0.65,y=-5)(piece:MyFace)
```

Do not put spaces inside a directive. Both forms can appear among existing
annotations, camera/choreography directives, `(meme)` and `(Xs)` suffixes.
`piece:` selects the moving actor; `pm:` selects the square's occupant at the
chosen cue. `when=start` uses occupancy at launch; `when=land` uses occupancy at
the moving piece's landing (including its destination, excluding captured pieces).
An empty target square is skipped. The existing castling landing cue precedes the
rook's travel, so select its original square at that cue. The square is only a
selector: the overlay thereafter belongs to the same actor, including when it
moves. Multiple directives on the same actor replace one another in written order;
different actors can display independent faces simultaneously.

Defaults live in `src/renderer/piece_memes.py`, `PIECE_MEME_DEFAULTS`:

| Option | Default | Meaning |
| --- | --- | --- |
| when | land | `start` = launch cue; `land` = settled landing cue |
| dur | 0.8 | Lifetime in seconds from the trigger |
| scale | piece-specific, 0.40–0.48 | Size relative to the piece's square |
| x, y | piece-specific | Local logical board-pixel offsets; positive y moves down |
| shape | none | `none`, `circle`, `rounded` |
| follow | full | Inherits all piece and camera transforms |
| loop | false | Video looping |
| audio | false | Play the video’s original audio when true |

Piece-specific defaults live in `src/renderer/piece_memes.py`,
`PIECE_MEME_ANCHORS`:

| Piece | scale | x | y |
| --- | --- | --- | --- |
| pawn | .40 | 0 | -3 |
| knight | .45 | -3 | -5 |
| bishop | .42 | 0 | -6 |
| rook | .45 | 0 | 0 |
| queen | .48 | 0 | -8 |
| king | .48 | 0 | -8 |

These keep the original SVG, crowns, bases and outlines visible. Anchors use the
actor's current sprite type at attachment. Existing active faces retain their
placement during promotion; a later attachment uses the promoted type.
Overrides resolve as defaults → piece anchors → registry settings → inline options.
Setting only `scale` or `y` leaves the other anchor values intact. Scale is
centered on the piece. Unmasked media uses `object-fit: contain`; shaped masks use
`cover`. A non-looping video shorter than `dur` holds its final frame until the
overlay ends. Videos have no controls; audio is muted unless explicitly requested.

## Optional video audio

```text
Qh5(pm:e8:HikaruLaugh,when=start,dur=1.5,audio=true)
Qh5(pm:e8:HikaruLaugh,when=land,hold=true,audio=true)
```

`audio=false` (the default) preserves muted playback. `audio=true` uses the
video element's original audio track, so audio and picture share the same start,
seek position, loop and playback clock. It works with `piece:` too, and with
`"audio": True` in initial configuration or per-asset registry defaults. Images
have no audio track; the option has no effect on them. Multiple opted-in videos
can play simultaneously and the browser mixes them normally.

Click **Play Sequence** to enable sound. Only opted-in videos are silently primed
inside the click gesture; initial preview faces remain muted before playback.
The exporter uses the same Play button and records the browser's mixed audio,
including opted-in piece videos. Browser/site mute settings still apply.

Removal, replacement, capture, reset and sequence cleanup immediately mute,
pause and rewind that video, cancel its synchronization callback and remove its
overlay. Replay reuses the same video node, rewinds it, and starts again at its
cue. Reset-created initial faces stay muted until the next playback. The reaction
panel and chess sounds retain their existing independent behavior.

## Persistence, removal and initial faces

Use `hold=true` on either existing attachment syntax:

```text
Qh5(pm:e8:HikaruLaugh,hold=true)
Qh5(piece:HikaruFace,hold=true)
```

A held face remains on the same actor across moves until replacement, explicit
removal, capture, reset or sequence-end cleanup. It never extends playback/export
by itself. Timed overlays still finish their tails; held faces stay visible during
those tails. A held video preserves the existing video behavior: `loop=true`
repeats it; otherwise it plays once and holds its final frame.

Remove the face from a square's current occupant with:

```text
Rf3(pm-remove:d7)
Rf3(pm-remove:d7,when=start)
```

Removal defaults to `when=land`, supports only the `when` option, and is harmless
on an empty square or an actor without a face. The square selects the actor at the
cue, using exactly the same occupancy rules as `pm:`. Repeated directives execute
in written order at each cue. Removal creates no image/video node.

`hold=false` is the default. Explicit `dur` combined with `hold=true` is rejected,
including conflicts between registry defaults and inline options. The implicit
0.8-second default does not conflict with hold; held clocks have no finite end.

In `src/generate_sequence_animation.py`, configure optional initial faces:

```python
INITIAL_PIECE_MEMES = [
    {"square": "e8", "meme": "HikaruLaugh", "scale": 0.5,
     "shape": "circle", "hold": True},
    {"square": "h8", "meme": "CR7", "hold": True},
]
```

The production default is `[]`. Entries accept the attachment options except
`when`: they appear as soon as initial assets are ready, before the first move.
Empty squares are skipped. Preview clocks restart at playback start, before
`INITIAL_DELAY`, so time spent looking at the preview does not consume the clip
or a timed initial meme. Reset reconstructs initial faces on new starting actors;
replay restarts their clocks. Sequence completion removes remaining faces.
`PIECE_MEME_MODE="off"` ignores initial faces and all attachment/removal directives.

## Lifecycle and layering

An overlay is an absolute child of the actor's existing reaction element, beside
and above its SVG. It naturally inherits travel, jumps, flips, spins, reactions,
and camera transforms. The actor remains below annotation layers and inside the
board's clipping system. Promotion changes only the SVG, retaining the overlay.
Captures remove the overlay with its actor, including reaction ghosts.

Timed overlay lifetimes use finite Web Animations clocks; held clocks are unbounded. They do **not** add pauses
between moves, so multiple actors can carry overlays simultaneously. Playback and
export wait for any remaining final overlay tail. A new directive on the same
actor replaces its previous overlay.

Used media nodes preload once per directive and are reused on replay. Active video
playback follows its overlay clock, including paused/backward clock seeks. A
single RAF loop per active video checks synchronization; it never positions the
piece or creates nodes each frame. Expiry, reset, cancellation and capture cancel
that RAF, pause/rewind the video, and remove the layer/classes. Detached media
nodes remain cached for replay. The exporter awaits preloading before recording.

## V1 limitations

- Only `follow=full` is implemented. `follow=position` is rejected rather than
  pretending to remain upright during flips and camera spins.
- No replacement of the SVG.
- Seeking an **active** overlay clock synchronizes its video. Like existing
  renderer effects, an expired/deleted overlay is not resurrected by arbitrary
  global scrubbing; restart/replay the timeline to reconstruct earlier states.
- Media can extend final export duration beyond the last move's pause.
- Use compact media assets: each directive preloads its own reusable node.

## Demo

Run from the project root:

```bash
.venv/bin/python src/generate_piece_meme_demo.py
xdg-open output/piece_meme_demo.html
```

Click **Play Sequence**, then **Replay Sequence**. The script extracts one 192 px
PNG from the existing Hikaru video if needed; it does not copy any large videos.
The top panel plays the existing CR7 clip independently.

Starting FEN: `4k2r/8/8/8/8/8/7Q/K7 w - - 0 1`.

Initial config (the demo also uses `initial_delay=1`):

```python
INITIAL_PIECE_MEMES = [
    {"square": "e8", "meme": "HikaruFace", "scale": 0.48,
     "shape": "circle", "hold": True},
]
```

Exact sequence:

```text
Qh5+^N@J(0.6s) Kd7^N@J(0.6s) Qh4^N@J(pm:d7:HikaruLaugh,hold=true,shape=circle)(pm:h8:HikaruFace,hold=true,shape=circle)(0.6s) Kc6^N@J(0.6s) Qxh8^N@J(pm-remove:c6)(0.6s)
```

The initial king face follows it to d7. Qh4 replaces that face with a held video
and gives the rook a held image. The king moves to c6, where the final directive
removes its face. Qxh8 captures the rook and cleans up its face automatically.
Replay restores the initial king face and repeats the sequence.

The demo explicitly enables piece memes; it leaves your production switch unchanged.

Optional export:

```bash
.venv/bin/python src/export_video.py --html output/piece_meme_demo.html --output output/piece_meme_demo.mp4 --fps 60
```

## Files added or changed for this feature

- `src/renderer/piece_memes.py` — new parser, defaults, registry validation and off-mode stripping.
- `src/renderer/piece_memes.js` — new preload, attachment, lifetime and media cleanup subsystem.
- `src/generate_sequence_animation.py` — independent switch and asset registry.
- `src/renderer/chess_state.py` — strip/parse the new directive before existing suffixes.
- `src/renderer/composition.py` — serialize resolved media and load its runtime.
- `src/renderer/timeline.js` — launch/landing bindings, preload and final lifetime wait.
- `src/renderer/pieces.js` — reset and immediate capture cleanup.
- `src/renderer/reactions.js` — captured reaction actor cleanup.
- `src/renderer/scene.css` — child overlay styling and masks.
- `src/export_video.py` — await detached piece-media preloading before capture.
- `src/generate_piece_meme_demo.py` — dedicated demo generator.
- `assets/memes/piece_meme_demo.png` — small extracted demo image.
- `output/piece_meme_demo.html` — generated demo (ignored output artifact).
- `tests/test_piece_memes.py` — new parser/config/switch tests.
- `tests/test_piece_memes_browser.py` — new timing/media/capture/promotion/replay/browser tests.
- `tests/test_piece_memes_export.py` — new real 60 fps export pixel check.
- `tests/recipe_fixtures.py` — fixed camera fixtures, independent of editable production tuning.
- `tests/test_aggressive.py`, `tests/test_very_aggressive.py` — use explicit regression tuning.
- `tests/test_initial_delay.py` — disabled piece-system stub in its isolated timeline test.
- `docs/piece-memes.md` — this guide.

No directing, camera, choreography, lighting or reaction recipes were retuned.

## Verification commands

```bash
.venv/bin/python -m unittest discover -s tests -p 'test_*.py'
.venv/bin/python tests/test_piece_memes_browser.py
.venv/bin/python tests/test_piece_meme_persistence_browser.py
.venv/bin/python tests/test_piece_meme_audio_browser.py
.venv/bin/python tests/test_piece_meme_real_audio_browser.py
.venv/bin/python tests/test_piece_memes_export.py
.venv/bin/python tests/test_directing_browser.py
```

The real-asset browser audio test requires PulseAudio/PipeWire and FFmpeg. It
records `hikaruLaughExecuseme.mp4` from an isolated temporary output sink after
a real Play button click, with Chromium autoplay restrictions enabled. It checks
audible playback/replay, silent opt-out, live/default mute state and node identity.
It does not invoke the exporter or alter the desktop audio output.

### Firefox audio synchronization diagnostics

Audible clips use their native media clock during uninterrupted playback. Small
animation-clock drift must not trigger repeated seeks: those seeks continually
restart decoding in Firefox and can starve audio. Explicit timeline seeks and
paused scrubbing still update the video position. Muted clips keep their existing
visual synchronization behavior, and overlay start/end cues are unchanged.

To inspect a production preview, append `?pieceMemeDebug=1` to its server URL,
open Firefox's console (enable Debug messages), then click Play. `[piece-meme]`
records include the registry ID, stable element key, source, requested audio,
mute property/attribute, volume, paused state, current time, ready state, visible
node identity, play promise results, and sync-seek targets. Records are also
available as `window.pieceMemeDiagnostics`. Remove the query parameter to disable
logging, or set `window.PIECE_MEME_DEBUG = true` temporarily in the console.
