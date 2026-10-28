"""Capture the existing Short in an isolated X11 display and a Pulse-compatible capture sink."""
import argparse
from contextlib import ExitStack
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import secrets
import select
import shutil
import subprocess
import tempfile
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
try:
    from .renderer.layout import CANVAS_WIDTH as WIDTH, CANVAS_HEIGHT as HEIGHT
except ImportError:
    from renderer.layout import CANVAS_WIDTH as WIDTH, CANVAS_HEIGHT as HEIGHT


def run(command, **kwargs):
    return subprocess.run(command, check=True, capture_output=True, text=True, **kwargs)


def stop(process):
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


def wait_for(predicate, timeout, description):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.05)
    raise RuntimeError(f"Timed out waiting for {description}")


class QuietHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/favicon.ico":
            self.send_response(204)
            self.end_headers()
        else:
            super().do_GET()

    def log_message(self, *_):
        pass


def probe(path):
    return json.loads(run(["ffprobe", "-v", "error", "-show_streams", "-show_format",
                           "-of", "json", str(path)]).stdout)


def export(args):
    for name in ("ffmpeg", "ffprobe", "Xvfb", "xauth", "pactl"):
        if not shutil.which(name):
            raise RuntimeError(f"Missing {name}. See README.md export setup.")
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError("Install requirements-export.txt and run playwright install chromium.") from exc
    html = args.html.resolve()
    if not html.is_file() or not html.is_relative_to(ROOT):
        raise RuntimeError("HTML must exist inside the project. Run the generator first.")
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    # Retain diagnostics on failure. Raw recording and browser profile are temporary.
    log_dir = output.parent / (output.stem + "_export_logs")
    log_dir.mkdir(exist_ok=True)
    errors = []
    with ExitStack() as stack:
        work = Path(stack.enter_context(tempfile.TemporaryDirectory(prefix="chess-export-")))
        env = os.environ.copy()
        authority = work / "Xauthority"
        authority.touch(mode=0o600)
        cookie = secrets.token_hex(16)
        run(["xauth", "-f", str(authority), "add", ":0", ".", cookie])
        read_fd, write_fd = os.pipe()
        xlog = stack.enter_context((log_dir / "xvfb.log").open("w"))
        try:
            xvfb = subprocess.Popen([
                "Xvfb", "-displayfd", str(write_fd), "-screen", "0", f"{WIDTH}x{HEIGHT}x24",
                "-nolisten", "tcp", "-auth", str(authority), "-noreset"],
                pass_fds=(write_fd,), stdout=xlog, stderr=xlog)
            stack.callback(stop, xvfb)
            os.close(write_fd)
            write_fd = None
            if not select.select([read_fd], [], [], 10)[0]:
                raise RuntimeError("Xvfb did not start; see xvfb.log")
            number = os.read(read_fd, 32).decode().strip()
            if not number.isdigit():
                raise RuntimeError("Xvfb failed; see xvfb.log")
        finally:
            os.close(read_fd)
            if write_fd is not None:
                os.close(write_fd)
        display = f":{number}"
        run(["xauth", "-f", str(authority), "add", display, ".", cookie])
        env.update(DISPLAY=display, XAUTHORITY=str(authority))

        # Use the existing user's server, including PipeWire's Pulse protocol.
        # Do not replace session/runtime settings or change any default device.
        pulse_env = {**env, "LC_ALL": "C"}
        try:
            info = run(["pactl", "info"], env=pulse_env).stdout
        except subprocess.CalledProcessError as exc:
            raise RuntimeError("Cannot connect to the running Pulse-compatible audio server. "
                               "Run LC_ALL=C pactl info in the same user session. "
                               + exc.stderr.strip()) from exc
        (log_dir / "pulse.log").write_text(info)
        sink = "chess_export_" + secrets.token_hex(8)
        module = run(["pactl", "load-module", "module-null-sink",
                      f"sink_name={sink}", "rate=48000", "channels=2"],
                     env=pulse_env).stdout.strip()

        def unload_sink():
            result = subprocess.run(["pactl", "unload-module", module], env=pulse_env,
                                    capture_output=True, text=True)
            with (log_dir / "pulse.log").open("a") as log:
                log.write(f"\nUnload temporary module {module}: {result.returncode}\n")
                log.write(result.stderr)
            if result.returncode:
                print(f"Warning: could not unload capture module {module}: "
                      f"{result.stderr.strip()}", flush=True)

        # Register immediately: also cleans up if media loading/capture fails.
        stack.callback(unload_sink)
        with (log_dir / "pulse.log").open("a") as log:
            log.write(f"\nTemporary sink: {sink}\nModule: {module}\n")
        monitor = sink + ".monitor"
        wait_for(lambda: any(source["name"] == monitor for source in json.loads(
            run(["pactl", "--format=json", "list", "sources"], env=pulse_env).stdout)),
            10, "temporary sink monitor")
        run(["pactl", "set-sink-volume", sink, "100%"], env=pulse_env)
        run(["pactl", "set-sink-mute", sink, "0"], env=pulse_env)
        run(["pactl", "set-source-volume", monitor, "100%"], env=pulse_env)
        run(["pactl", "set-source-mute", monitor, "0"], env=pulse_env)
        # Only this Chromium process routes to the temporary sink. FFmpeg reads
        # its monitor explicitly; desktop output and microphone stay untouched.
        env["PULSE_SINK"] = sink

        server = ThreadingHTTPServer(("127.0.0.1", 0), partial(QuietHandler, directory=str(ROOT)))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        stack.callback(server.server_close)
        stack.callback(server.shutdown)
        url = f"http://127.0.0.1:{server.server_port}/{html.relative_to(ROOT).as_posix()}"
        playwright = stack.enter_context(sync_playwright())
        context = playwright.chromium.launch_persistent_context(
            str(work / "browser"), headless=False, viewport={"width": WIDTH, "height": HEIGHT},
            device_scale_factor=1, env=env, ignore_default_args=["--mute-audio"],
            executable_path=args.chromium,
            args=["--kiosk", "--window-position=0,0", f"--window-size={WIDTH},{HEIGHT}",
                  "--autoplay-policy=no-user-gesture-required", "--disable-dev-shm-usage",
                  "--disable-background-timer-throttling", "--disable-renderer-backgrounding",
                  "--disable-backgrounding-occluded-windows", "--force-device-scale-factor=1"])
        stack.callback(context.close)
        page = context.pages[0]
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.on("console", lambda msg: errors.append(msg.text) if msg.type in ("warning", "error") else None)
        page.add_init_script("""(() => {
            window.exportMediaPlays = [];
            const original = HTMLMediaElement.prototype.play;
            HTMLMediaElement.prototype.play = function(...args) {
                const element = this;
                return original.apply(this, args).then(result => {
                    window.exportMediaPlays.push({src: element.currentSrc, muted: element.muted,
                        volume: element.volume, time: Date.now() / 1000});
                    return result;
                });
            };
        })();""")
        print("Loading page and preloading media…", flush=True)
        page.goto(url, wait_until="load", timeout=60000)
        # Export-only CSS: the generated HTML and all animation code stay intact.
        page.add_style_tag(content="""
            html, body { margin:0!important; width:__WIDTH__px!important; height:__HEIGHT__px!important;
                overflow:hidden!important; }
            body { display:block!important; }
            .short-canvas { position:absolute!important; left:0!important; top:0!important; }
            .controls { display:none!important; }
            * { cursor:none!important; }
        """.replace("__WIDTH__", str(WIDTH)).replace("__HEIGHT__", str(HEIGHT)))
        cdp = context.new_cdp_session(page)
        window_id = cdp.send("Browser.getWindowForTarget")["windowId"]
        cdp.send("Browser.setWindowBounds", {"windowId": window_id,
                                           "bounds": {"windowState": "fullscreen"}})
        page.wait_for_function(f"innerWidth === {WIDTH} && innerHeight === {HEIGHT}", timeout=10000)
        page.wait_for_function("""() => [...document.images].every(i => i.complete && i.naturalWidth)
            && [...document.querySelectorAll('video,audio')].every(m => m.readyState >= 3)
            && [...moveAudio.values()].every(m => m.readyState >= 3)""", timeout=60000)
        page.evaluate("document.fonts.ready")
        if not page.evaluate("async () => (await Promise.all(audioReady)).every(Boolean)"):
            raise RuntimeError("A chess sound failed to preload")
        if errors:
            raise RuntimeError("Browser errors before capture: " + "; ".join(errors))
        bounds = page.locator(".short-canvas").bounding_box()
        if bounds != {"x": 0, "y": 0, "width": WIDTH, "height": HEIGHT}:
            raise RuntimeError(f"Unexpected canvas bounds: {bounds}")
        page.screenshot(path=str(log_dir / "canvas-before.png"))

        raw = work / "capture.mkv"
        progress = work / "capture.progress"
        flog = stack.enter_context((log_dir / "capture.log").open("w"))
        anchor = time.time()
        # Both inputs use the same wall clock. Preserve their relative timestamps;
        # subtract a common anchor so the intermediate has small timestamps.
        recorder = subprocess.Popen([
            "ffmpeg", "-hide_banner", "-y", "-nostats", "-copyts",
            "-thread_queue_size", "512", "-use_wallclock_as_timestamps", "1",
            "-f", "x11grab", "-draw_mouse", "0", "-framerate", str(args.fps),
            "-video_size", f"{WIDTH}x{HEIGHT}", "-i", display + ".0+0,0",
            "-thread_queue_size", "512", "-use_wallclock_as_timestamps", "1",
            "-f", "pulse", "-sample_rate", "48000", "-channels", "2",
            "-i", monitor, "-map", "0:v:0", "-map", "1:a:0",
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "15", "-threads", "4",
            "-pix_fmt", "yuv420p", "-fps_mode", "passthrough", "-c:a", "pcm_s16le",
            "-output_ts_offset", str(-anchor), "-progress", str(progress), str(raw)],
            stdin=subprocess.PIPE, stdout=flog, stderr=flog, env=env)
        stack.callback(stop, recorder)
        wait_for(lambda: (progress.exists() and "frame=" in progress.read_text())
                 or recorder.poll() is not None, 20, "FFmpeg recording")
        if recorder.poll() is not None:
            raise RuntimeError("FFmpeg capture failed; see capture.log")
        print(f"Recording {WIDTH}x{HEIGHT} at {args.fps} fps with browser audio…", flush=True)
        # Call the existing button handler, measuring the exact lifetime of its
        # promise (including the final move's pause). No estimated sequence length.
        page.evaluate("""() => {
            const original = playSequence;
            window.exportState = {start: null, end: null, done: false, error: null};
            playSequence = async function() {
                exportState.start = Date.now() / 1000;
                try { await original(); }
                catch (e) { exportState.error = String(e); }
                finally {
                    exportState.end = Date.now() / 1000;
                    exportState.done = true;
                }
            };
            document.getElementById('playButton').click();
        }""")
        page.wait_for_function("exportState.done", timeout=args.timeout * 1000)
        state = page.evaluate("exportState")
        media = page.evaluate("exportMediaPlays")
        page.screenshot(path=str(log_dir / "canvas-after.png"))
        # Small drain for audio device/encoder latency; trimmed from final output.
        page.wait_for_timeout(300)
        recorder.communicate(input=b"q\n", timeout=30)
        if recorder.returncode != 0:
            raise RuntimeError("FFmpeg capture failed; see capture.log")
        if state["error"] or errors:
            raise RuntimeError(f"Playback error: {state['error'] or errors}")
        audible = [entry for entry in media if not entry["muted"] and entry["volume"] > 0]
        expected = page.evaluate("""() => [...new Set([
            ...moves.map(m => moveAudio.get(moveSoundKind(m)).src),
            ...[memeVideo, backgroundMusic].filter(m => m && m.volume > 0).map(m => m.src)
        ])]""")
        missing = set(expected) - {entry["src"] for entry in audible}
        if missing:
            raise RuntimeError(f"Media did not play audibly: {missing}")
        duration = state["end"] - state["start"]
        report = {"fps": args.fps, "duration": duration, "playback": state,
                  "capture_anchor": anchor, "media_plays": media, "expected_audio": expected}
        (log_dir / "playback.json").write_text(json.dumps(report, indent=2))
        print(f"Encoding {duration:.2f}s to H.264 / AAC…", flush=True)
        encoded = work / "final.mp4"
        command = [
            "ffmpeg", "-hide_banner", "-y", "-seek_timestamp", "1",
            "-ss", str(state["start"] - anchor), "-i", str(raw), "-t", str(duration),
            "-map", "0:v:0", "-map", "0:a:0", "-vf", f"fps={args.fps}",
            "-af", "aresample=async=1:first_pts=0", "-c:v", "libx264",
            "-preset", "medium", "-crf", str(args.crf), "-threads", "4",
            "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
            "-ar", "48000", "-movflags", "+faststart", str(encoded)]
        with (log_dir / "encode.log").open("w") as log:
            subprocess.run(command, check=True, stdout=log, stderr=log)
        info = probe(encoded)
        video = next(s for s in info["streams"] if s["codec_type"] == "video")
        audio = next(s for s in info["streams"] if s["codec_type"] == "audio")
        if (video["width"], video["height"], video["codec_name"], video["pix_fmt"],
                audio["codec_name"]) != (WIDTH, HEIGHT, "h264", "yuv420p", "aac"):
            raise RuntimeError("Unexpected output format")
        if abs(float(info["format"]["duration"]) - duration) > 0.15:
            raise RuntimeError("Output duration does not match playback")
        volume = run(["ffmpeg", "-hide_banner", "-i", str(encoded), "-vn", "-af",
                      "volumedetect", "-f", "null", "-"]).stderr
        (log_dir / "audio-levels.log").write_text(volume)
        if audible and "max_volume: -inf" in volume:
            raise RuntimeError("Recorded audio is silent; refusing to publish a silent export")
        (log_dir / "ffprobe.json").write_text(json.dumps(info, indent=2))
        # Copy to a sibling first, then atomically replace the previous successful export.
        staging = output.with_suffix(".partial.mp4")
        try:
            shutil.copyfile(encoded, staging)
            staging.replace(output)
        finally:
            staging.unlink(missing_ok=True)
        print(f"Created {output}\nDiagnostics: {log_dir}", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--html", type=Path, default=ROOT / "output/sequence_demo.html")
    parser.add_argument("--output", type=Path, default=ROOT / "output/final_short.mp4")
    parser.add_argument("--fps", type=int, choices=(30, 60), default=30)
    parser.add_argument("--crf", type=int, choices=range(0, 52), default=18, metavar="0..51")
    parser.add_argument("--timeout", type=int, default=600, help="Maximum playback seconds")
    parser.add_argument("--chromium", help="Optional non-Snap Chromium executable")
    args = parser.parse_args()
    try:
        export(args)
    except (RuntimeError, subprocess.SubprocessError) as exc:
        parser.exit(1, f"Export failed: {exc}\n")


if __name__ == "__main__":
    main()
