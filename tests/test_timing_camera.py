"""Browser regression checks for overlapping timing and independent camera tracks.

Run: .venv/bin/python tests/test_timing_camera.py
Creates temporary HTML fixtures; no demo regeneration or video export is needed.
"""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import sys
import tempfile
import threading

import chess
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.renderer.chess_state import compile_sequence
from src.renderer.composition import render_scene


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *_):
        pass


def fixture(path, line, *, profile="REFERENCE", camera_enabled=True, meme=False, board=None):
    scene = compile_sequence(board if board is not None else chess.Board(), line, 0.1)
    html = render_scene(
        scene, timing_profile=profile, camera_enabled=camera_enabled,
        meme_path="../assets/memes/MonkeyCry.mp4" if meme else None,
    )
    path.write_text(html.replace("../assets/", "../../assets/"), encoding="utf-8")


def open_page(browser, url):
    page = browser.new_page(viewport={"width": 1080, "height": 1920})
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto(url)
    page.wait_for_function("[...moveAudio.values()].every(audio => audio.readyState >= 3)")
    page.evaluate("""() => {
        window.cueTrace = [];
        window.mediaTrace = [];
        window.frameTrace = [];
        window.holdingMove = null;
        window.stopSampling = false;
        const reaction = document.querySelector('.reaction-area');
        window.initialReaction = reaction.getBoundingClientRect().toJSON();
        const clone = value => JSON.parse(JSON.stringify(value));
        window.unsubscribeCues = timelineScheduler.subscribe(event => {
            cueTrace.push({cue: event.cue, to: event.move.to, time: event.time,
                           plan: clone(event.plan), pose: clone(camera.pose)});
            if (event.cue === 'holdStart') holdingMove = event.move.to;
            if (event.cue === 'holdEnd') holdingMove = null;
        });
        const sound = playMoveSound;
        playMoveSound = function(move) {
            mediaTrace.push({kind: 'sound', to: move.to, time: performance.now()});
            return sound(move);
        };
        const meme = startMemeVideo;
        startMemeVideo = function() {
            const wasStarted = memeStarted;
            const result = meme();
            if (!wasStarted && memeStarted) mediaTrace.push({kind: 'meme', time: performance.now()});
            return result;
        };
        const sample = () => {
            if (stopSampling) return;
            if (playing) frameTrace.push({
                hold: holdingMove,
                hero: getComputedStyle(document.getElementById('cameraHero')).transform,
                reactionFixed: JSON.stringify(reaction.getBoundingClientRect().toJSON()) ===
                    JSON.stringify(initialReaction)
            });
            requestAnimationFrame(sample);
        };
        requestAnimationFrame(sample);
    }""")
    return page, errors


def one_cue(trace, name, square):
    matches = [event for event in trace if event["cue"] == name and event["to"] == square]
    assert len(matches) == 1, (name, square, matches)
    return matches[0]


def assert_idle(page):
    page.evaluate("""async () => {
        await camera.finished;
        await cameraMotion.finished;
        const assert = (ok, message) => { if (!ok) throw Error(message); };
        assert(timelineScheduler.active.size === 0, 'move schedule leaked');
        assert(cameraMotion.tracks.size === 0, 'transient camera track leaked');
        for (const id of ['cameraReframe', 'cameraImpact', 'cameraHero']) {
            const element = document.getElementById(id);
            const matrix = new DOMMatrix(getComputedStyle(element).transform);
            assert(matrix.isIdentity, id + ' did not return to identity');
        }
        assert(document.querySelector('.board-area').getAnimations({subtree: true}).length === 0,
               'a board animation survived completion');
        assert(!playing && !playButton.disabled, 'playback did not finish');
    }""")


def play_and_check(page, *, reference, disabled=False, meme=False):
    page.evaluate("cueTrace.length = 0; mediaTrace.length = 0; frameTrace.length = 0")
    page.click("#playButton")
    page.wait_for_function("hasPlayed && !playing", timeout=20000)
    assert_idle(page)
    trace = page.evaluate("cueTrace")
    media = page.evaluate("mediaTrace")
    destinations = page.evaluate("moves.map(move => move.to)")
    for square in destinations:
        launch = one_cue(trace, "launch", square)
        contact = one_cue(trace, "contact", square)
        settled = one_cue(trace, "settled", square)
        hold_start = one_cue(trace, "holdStart", square)
        hold_end = one_cue(trace, "holdEnd", square)
        complete = one_cue(trace, "complete", square)
        assert launch["time"] <= contact["time"] <= settled["time"] <= hold_start["time"]
        assert hold_start["time"] <= hold_end["time"] <= complete["time"]
        # Authored timing remains a real post-settle pause, not a minimum recipe duration.
        held = hold_end["time"] - hold_start["time"]
        assert hold_start["plan"]["holdDuration"] - 20 <= held <= hold_start["plan"]["holdDuration"] + 250, held
        sounds = [event for event in media if event["kind"] == "sound" and event["to"] == square]
        assert len(sounds) == 1, sounds
        assert abs(sounds[0]["time"] - settled["time"]) < 35, (sounds, settled)
    if not disabled:
        for square in ["e4", "f3", "c4"]:
            camera_start = one_cue(trace, "cameraStart", square)
            camera_end = one_cue(trace, "cameraEnd", square)
            launch = one_cue(trace, "launch", square)
            assert camera_start["time"] <= camera_end["time"]
            if reference:
                assert camera_start["time"] <= launch["time"] < camera_end["time"], (square, trace)
            else:
                assert camera_end["time"] <= launch["time"], (square, trace)
        # Unmarked moves keep the absolute shot; impulses must not accumulate into it.
        assert one_cue(trace, "complete", "e4")["pose"] == one_cue(trace, "complete", "e5")["pose"]
        assert one_cue(trace, "complete", "f3")["pose"] == one_cue(trace, "complete", "c6")["pose"]
    frames = page.evaluate("frameTrace")
    assert frames and all(frame["reactionFixed"] for frame in frames), "reaction moved with camera"
    hero_frames = [frame for frame in frames if frame["hold"] == "f3"]
    assert hero_frames, "no frames sampled during authored hero hold"
    hero_transforms = {frame["hero"] for frame in hero_frames}
    if reference and not disabled:
        assert len(hero_transforms) > 2, "hero hold was static"
    else:
        assert len(hero_transforms) == 1, "disabled or LEGACY hero hold moved"
    if meme:
        starts = [event for event in media if event["kind"] == "meme"]
        assert len(starts) == 1
        assert abs(starts[0]["time"] - one_cue(trace, "settled", "f3")["time"]) < 35
    page.evaluate("""() => {
        if (!new DOMMatrix(getComputedStyle(board).transform).isIdentity)
            throw Error('wide/reset shot did not restore neutral framing');
        for (const square of ['e4','e5','f3','c6','c4']) {
            if (!pieceBySquare[square]) throw Error('incorrect final chess position: ' + square);
        }
    }""")
    return [one_cue(trace, "complete", square)["pose"] for square in destinations]


def check_motion_clock(page):
    """Pause/cancel are decisive cases against a wall-clock arrival timer."""
    page.evaluate("""async () => {
        const assert = (ok, message) => { if (!ok) throw Error(message); };
        const delay = ms => new Promise(resolve => setTimeout(resolve, ms));
        const frames = () => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
        for (const name of Object.keys(motion.presets)) {
            resetPieces();
            const piece = pieceBySquare.e2;
            const move = {from: 'e2', to: 'e4', pause: 0, animation_preset: name};
            const schedule = new MoveSchedule(move, buildMovePlan(move));
            let contact = 0;
            let metadata;
            const task = animatePieceToSquare(piece, 'e4', name, info => {
                metadata = info;
                schedule.observeMotion(info, () => contact++);
            });
            assert(metadata && metadata.animation, 'piece did not report its actual animation');
            const animation = metadata.animation;
            animation.pause();
            animation.currentTime = metadata.duration * (metadata.contactOffset - 0.15);
            await delay(180);
            assert(contact === 0, name + ': paused piece emitted contact');
            animation.currentTime = metadata.duration * (metadata.contactOffset + 0.01);
            await frames();
            assert(contact === 1, name + ': animation clock marker was not observed');
            animation.currentTime = metadata.duration * (metadata.contactOffset + 0.04);
            await frames();
            assert(contact === 1, name + ': contact fired twice');
            animation.finish();
            await task;
            schedule.close();
            assert(piece.style.top === 4 * squareSize + 'px', 'settled coordinates changed');
            assert(piece.getAnimations().length === 0, 'piece animation leaked');
        }
        resetPieces();
        const piece = pieceBySquare.e2;
        const move = {from: 'e2', to: 'e4', pause: 0};
        const schedule = new MoveSchedule(move, buildMovePlan(move));
        let contact = 0;
        let metadata;
        const task = animatePieceToSquare(piece, 'e4', motion.defaultPreset, info => {
            metadata = info;
            schedule.observeMotion(info, () => contact++);
        }).then(() => null, error => error.name);
        metadata.animation.pause();
        metadata.animation.currentTime = metadata.duration * 0.2;
        metadata.animation.cancel();
        assert(await task === 'AbortError', 'cancellation was swallowed');
        await frames();
        assert(contact === 0, 'cancelled motion emitted contact');
        assert(piece.style.top === 6 * squareSize + 'px', 'cancelled motion committed destination');
        schedule.close();
        assert(timelineScheduler.active.size === 0, 'contact observer leaked its schedule');
        resetPieces();

        // Instant movement still dispatches contact/settled once, and completion
        // must join the longer camera tail (also the exporter's completion boundary).
        const preset = motion.presets[motion.defaultPreset];
        const originalDuration = preset.duration;
        const events = [];
        const unsubscribe = timelineScheduler.subscribe(event => events.push(event));
        try {
            preset.duration = 0;
            await animateMove({from: 'e2', to: 'e4', pause: 0, camera_directive: 'L'});
            for (const cue of ['contact', 'settled', 'cameraEnd', 'complete'])
                assert(events.filter(event => event.cue === cue).length === 1, 'instant move duplicate/missing ' + cue);
            const at = cue => events.find(event => event.cue === cue).time;
            assert(at('contact') <= at('settled'), 'instant contact came after settling');
            assert(at('complete') >= at('cameraEnd'), 'completion truncated camera tail');
            assert(cameraMotion.tracks.size === 0, 'completion truncated transient tail');
            assert(timelineScheduler.active.size === 0, 'instant move leaked schedule');
        } finally {
            preset.duration = originalDuration;
            unsubscribe();
            camera.reset();
            cameraMotion.reset();
            resetPieces();
        }
    }""")


def check_combined_camera_bounds(page):
    """Exercise simultaneous track phases against actual browser geometry."""
    page.evaluate("""async () => {
        const assert = (ok, message) => { if (!ok) throw Error(message); };
        for (const id of ['fromHighlight','toHighlight','arrowLayer','annotationBadge','checkTargetLayer']) {
            assert(document.getElementById('cameraHero').contains(document.getElementById(id)),
                   id + ' is outside the camera scene');
        }
        const viewport = document.querySelector('.board-area');
        const reaction = JSON.stringify(document.querySelector('.reaction-area').getBoundingClientRect().toJSON());
        for (const square of ['a1', 'h8']) {
            const move = {from: 'd4', to: square, camera_directive: 'L', annotation: '!!'};
            await camera.directMove(move);
            const pose = JSON.stringify(camera.pose);
            const region = destination_region(square, 'L');
            const probes = [];
            for (const x of [region.left, region.right]) for (const y of [region.top, region.bottom]) {
                const probe = document.createElement('i');
                Object.assign(probe.style, {position: 'absolute', left: x + 4 * squareSize + 'px',
                    top: y + 4 * squareSize + 'px', width: '0px', height: '0px'});
                board.appendChild(probe);
                probes.push(probe);
            }
            const tasks = [cameraMotion.reframe(move, 400), cameraMotion.impact(move),
                           cameraMotion.heroHold(move, 700)];
            const tracks = Array.from(cameraMotion.tracks.values());
            assert(tracks.length === 3, 'parallel camera tracks replaced each other');
            for (const track of tracks) track.animation.pause();
            for (const a of [0.2, 0.55, 0.8]) for (const b of [0.18, 0.44, 0.72])
                for (const c of [0.2, 0.5, 0.8]) {
                    [a,b,c].forEach((progress, index) => {
                        const animation = tracks[index].animation;
                        animation.currentTime = animation.effect.getTiming().duration * progress;
                    });
                    const bounds = viewport.getBoundingClientRect();
                    for (const probe of probes) {
                        const p = probe.getBoundingClientRect();
                        assert(p.x >= bounds.left - 0.5 && p.x <= bounds.right + 0.5 &&
                               p.y >= bounds.top - 0.5 && p.y <= bounds.bottom + 0.5,
                               square + ': simultaneous camera accents cropped the destination region');
                    }
                    assert(JSON.stringify(camera.pose) === pose, 'transient modified persistent pose');
                }
            for (const track of tracks) track.animation.finish();
            await Promise.all(tasks);
            await cameraMotion.finished;
            probes.forEach(probe => probe.remove());
            assert(JSON.stringify(camera.pose) === pose, 'transient completion changed persistent pose');
            await camera.directMove(move);
            assert(JSON.stringify(camera.pose) === pose, 'repeated directive accumulated camera pose');
        }
        assert(JSON.stringify(document.querySelector('.reaction-area').getBoundingClientRect().toJSON()) === reaction,
               'transient camera moved reaction');
        camera.reset();
        cameraMotion.reset();
    }""")


def check_effect_tail(page):
    # Await the same promise as the exporter, then inspect immediately rather
    # than allowing a browser polling delay to hide a prematurely resolved tail.
    page.evaluate("""async () => {
        const assert = (ok, message) => { if (!ok) throw Error(message); };
        const show = showMoveEffects;
        let animatedBadge = false;
        showMoveEffects = function(move) {
            show(move);
            animatedBadge = document.getElementById('annotationBadge').getAnimations().length > 0;
        };
        await playSequence();
        assert(animatedBadge, 'fixture did not exercise the existing badge animation');
        assert(document.querySelector('.board-area').getAnimations({subtree: true}).length === 0,
               'playSequence resolved before the final annotation animation');
        const start = cueTrace.find(event => event.cue === 'holdStart');
        const end = cueTrace.find(event => event.cue === 'holdEnd');
        assert(start.plan.holdDuration === 0 && end.time - start.time < 100,
               'effect completion changed the authored zero-length pause');
    }""")
    assert_idle(page)


def check_cancel_replay(page, square):
    """A failed travel must retain ownership so Replay cannot leave ghost sprites."""
    page.evaluate("""async square => {
        const assert = (ok, message) => { if (!ok) throw Error(message); };
        const task = playSequence().then(() => 'completed', error => error.name);
        let animation;
        const deadline = performance.now() + 3000;
        while (!animation && performance.now() < deadline) {
            const actor = board.querySelector('.piece[data-square="' + square + '"]');
            animation = actor?.getAnimations()[0];
            if (!animation) await new Promise(requestAnimationFrame);
        }
        assert(animation, 'did not observe the moving actor to cancel');
        animation.cancel();
        assert(await task === 'AbortError', 'cancel did not reject sequence playback');
        assert(timelineScheduler.active.size === 0 && cameraMotion.tracks.size === 0,
               'cancel left a running camera/schedule');
        await playSequence();
        const actors = [...board.querySelectorAll('.piece')];
        assert(actors.length === initialPieces.length, 'replay retained an orphaned moving sprite');
        assert(new Set(actors.map(actor => actor.dataset.square)).size === actors.length,
               'duplicate piece on a square after replay');
        assert(actors.every(actor => pieceBySquare[actor.dataset.square] === actor),
               'rendered actor is missing from chess coordinates');
    }""", square)
    assert_idle(page)


def main():
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(QuietHandler, directory=str(ROOT)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        with tempfile.TemporaryDirectory(prefix="timing-camera-", dir=ROOT / "output") as folder, sync_playwright() as pw:
            work = Path(folder)
            line = "e4@K(0.10s) e5(0.10s) Nf3!!@L(meme)(0.65s) Nc6(0.10s) Bc4@J(0.10s)"
            fixture(work / "reference.html", line, meme=True)
            fixture(work / "legacy.html", line, profile="LEGACY")
            fixture(work / "disabled.html", line, camera_enabled=False)
            fixture(work / "effect-tail.html", "e4!(0s)")
            fixture(work / "cancel.html", "e4@L(0s)")
            fixture(work / "cancel-castle.html", "O-O@K(0s)",
                    board=chess.Board("4k3/8/8/8/8/8/8/4K2R w K - 0 1"))
            browser = pw.chromium.launch(headless=True)
            try:
                base = f"http://127.0.0.1:{server.server_port}/output/{work.name}"
                page, errors = open_page(browser, base + "/reference.html")
                first_poses = play_and_check(page, reference=True, meme=True)
                replay_poses = play_and_check(page, reference=True, meme=True)
                assert first_poses == replay_poses, "replay accumulated camera state"
                check_motion_clock(page)
                check_combined_camera_bounds(page)
                assert not errors, errors
                page.close()
                print("PASS: REFERENCE overlap, authored holds, media settling, animated hero hold, replay, actual-motion contact, and combined camera bounds.", flush=True)
                for profile, reference, disabled in [("legacy", False, False), ("disabled", True, True)]:
                    page, errors = open_page(browser, base + f"/{profile}.html")
                    play_and_check(page, reference=reference, disabled=disabled)
                    assert not errors, errors
                    page.close()
                    print(f"PASS: {profile} ordering, fixed meme, independent camera state and cleanup.", flush=True)
                page, errors = open_page(browser, base + "/effect-tail.html")
                check_effect_tail(page)
                assert not errors, errors
                page.close()
                print("PASS: zero-pause export completion includes the existing annotation effect tail.", flush=True)
                for filename, squares in [("cancel", ["e2"]), ("cancel-castle", ["e1", "h1"])]:
                    page, errors = open_page(browser, base + f"/{filename}.html")
                    for square in squares:
                        check_cancel_replay(page, square)
                    assert not errors, errors
                    page.close()
                print("PASS: cancelled piece/king/rook movement replays without orphan sprites or tracks.", flush=True)
            finally:
                browser.close()
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    main()
