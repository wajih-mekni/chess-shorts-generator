"""Real 60 fps export test: three simultaneous tones and a timed visual marker.

Requires the same dependencies as src/export_video.py. No real media is changed.
Run: python tests/test_video_export.py
"""
from array import array
import math
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def ffmpeg(*args):
    return subprocess.run(["ffmpeg", "-v", "error", "-y", *map(str, args)],
                          check=True, capture_output=True).stdout


def amplitude(samples, frequency, start, end, rate=8000):
    clip = samples[int(start * rate):int(end * rate)]
    real = sum(value * math.cos(2 * math.pi * frequency * i / rate)
               for i, value in enumerate(clip))
    imag = sum(value * math.sin(2 * math.pi * frequency * i / rate)
               for i, value in enumerate(clip))
    return 2 * math.hypot(real, imag) / len(clip)


def main():
    with tempfile.TemporaryDirectory(prefix="export-test-", dir=ROOT / "output") as folder:
        work = Path(folder)
        ffmpeg("-f", "lavfi", "-i", "color=c=blue:s=320x180:r=30",
               "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000",
               "-t", "1", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", work / "meme.mp4")
        for name, hz, duration in [("music", 660, 1), ("move", 880, 0.5)]:
            ffmpeg("-f", "lavfi", "-i", f"sine=frequency={hz}:sample_rate=48000",
                   "-t", str(duration), work / f"{name}.wav")
        html = work / "test.html"
        html.write_text('''<!doctype html><style>
        body{margin:0}.short-canvas{width:1080px;height:1920px;background:red}
        video{position:absolute;top:1080px;width:1080px;height:560px}
        .controls{position:fixed;top:10px}
        </style><div class="short-canvas"><video id="memeVideo" src="meme.mp4" preload="auto" loop></video></div>
        <audio id="backgroundMusic" src="music.wav" preload="auto" loop></audio>
        <div class="controls"><button id="playButton" onclick="playSequence()">Play</button></div>
        <script>
        const memeVideo=document.getElementById('memeVideo');
        const backgroundMusic=document.getElementById('backgroundMusic');
        const sound=new Audio('move.wav');sound.preload='auto';sound.load();
        const moveAudio=new Map([['move',sound]]);
        const audioReady=[Promise.resolve(true)];
        const moves=[{}];
        function moveSoundKind(){return 'move';}
        const sleep=ms=>new Promise(r=>setTimeout(r,ms));
        async function playSequence(){
            memeVideo.volume=0.8;backgroundMusic.volume=0.12;
            await Promise.all([memeVideo.play(),backgroundMusic.play()]);
            await sleep(1500);
            document.querySelector('.short-canvas').style.background='lime';
            sound.currentTime=0;await sound.play();
            await sleep(2500);
        }
        </script>''')
        video = work / "test.mp4"
        subprocess.run([sys.executable, str(ROOT / "src/export_video.py"),
                        "--html", str(html), "--output", str(video), "--fps", "60"], check=True)
        samples = array('f', ffmpeg("-i", video, "-vn", "-ac", "1", "-ar", "8000", "-f", "f32le", "-"))
        for frequency, threshold in [(440, 0.04), (660, 0.006), (880, 0.04)]:
            level = amplitude(samples, frequency, 1.65, 1.9)
            assert level > threshold, (frequency, level, "missing from browser mix")
        assert amplitude(samples, 880, 0.8, 1.1) < 0.002, "SFX played too early"
        # Both continuous sources must remain audible after the one-shot SFX,
        # across multiple media loops and while the sequence awaits a timer.
        for frequency, threshold in [(440, 0.04), (660, 0.006)]:
            assert amplitude(samples, frequency, 3.3, 3.6) > threshold
        for timestamp, expected in [(1.3, (255, 0, 0)), (1.7, (0, 255, 0))]:
            rgb = ffmpeg("-ss", timestamp, "-i", video, "-frames:v", "1", "-an",
                         "-vf", "crop=2:2:0:0,scale=1:1", "-pix_fmt", "rgb24", "-f", "rawvideo", "-")
            assert all(abs(value - target) < 10 for value, target in zip(rgb, expected)), (timestamp, rgb)
        print("PASS: 60 fps export, three captured audio sources, loops through pauses, timed SFX and canvas marker.")


if __name__ == '__main__':
    main()
