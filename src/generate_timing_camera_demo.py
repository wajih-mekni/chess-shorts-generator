"""Generate browser comparisons for timing and layered camera motion.

Run from the project root, then serve it with ``python3 -m http.server 8000``.
The inspector belongs only to these demos; production composition is unchanged.
"""
from pathlib import Path

import chess

try:
    from .renderer.chess_state import compile_sequence
    from .renderer.composition import render_scene
    from .renderer.timing import REFERENCE_HERO_HOLD
except ImportError:
    from renderer.chess_state import compile_sequence
    from renderer.composition import render_scene
    from renderer.timing import REFERENCE_HERO_HOLD


LINE = f"e4@K e5 Nf3!!@L({REFERENCE_HERO_HOLD / 1000:g}s) Nc6@K Bc4@L Nf6@J"

INSPECTOR_STYLE = """
<style>
body {
    display: block;
    min-height: 100vh;
    background: #14181e;
    color: #e6edf3;
    font: 14px/1.5 system-ui, sans-serif;
}
.review-shell { max-width: 1440px; padding: 24px; margin: auto; }
.review-heading { margin: 0 0 20px; }
.review-heading h1 { margin: 0 0 6px; font-size: 25px; }
.review-heading p { color: #b3bfcc; margin: 6px 0; max-width: 950px; }
.review-heading a, .review-panel a { color: #8ad8e3; }
.review-layout {
    display: grid;
    grid-template-columns: minmax(270px, 378px) minmax(280px, 1fr) minmax(240px, 320px);
    align-items: start;
    gap: 20px;
}
.review-panel { min-width: 0; }
.review-panel h2 { font-size: 16px; margin: 0 0 12px; }
.preview-stage {
    position: relative;
    width: 100%;
    aspect-ratio: 9 / 16;
    overflow: hidden;
    border-radius: 12px;
    background: #d9bb92;
}
.preview-stage .short-canvas {
    position: absolute;
    top: 0;
    left: 0;
    transform: scale(var(--preview-scale, .35));
    transform-origin: top left;
}
.review-shell .controls { position: static; margin-top: 12px; }
.review-shell button, .review-shell select {
    padding: 8px 12px;
    border: 1px solid #41505f;
    border-radius: 7px;
    background: #27323e;
    color: #eef7ff;
    cursor: pointer;
    font: inherit;
}
.review-shell button:hover { background: #344554; }
.review-shell button:disabled { opacity: .5; cursor: default; }
.review-shell #playButton { background: #238076; border-color: #56b4a9; width: 100%; }
.review-note { color: #a9b6c3; font-size: 12px; margin: 9px 0 14px; }
.cue-status, .recipe-info {
    padding: 12px;
    border: 1px solid #35414e;
    border-radius: 9px;
    background: #1d252e;
    margin-bottom: 12px;
}
.cue-status strong { display: block; font-size: 22px; color: #8ee3d5; }
.move-strip { display: flex; flex-wrap: wrap; gap: 6px; margin: 12px 0; }
.move-token { padding: 3px 7px; border: 1px solid #3a4856; border-radius: 5px; }
.move-token.active { border-color: #6bd2bb; color: #9ff6db; background: #234039; }
.recipe-info dl { display: grid; grid-template-columns: 1fr auto; gap: 5px 12px; margin: 0; }
.recipe-info dt { color: #b2bfcc; }
.recipe-info dd { margin: 0; text-align: right; font-variant-numeric: tabular-nums; }
.cue-trace { border: 1px solid #35414e; border-radius: 9px; height: 230px; overflow: auto; }
.cue-trace table { width: 100%; border-collapse: collapse; font-size: 12px; }
.cue-trace th { position: sticky; top: 0; background: #28333e; text-align: left; }
.cue-trace td, .cue-trace th { padding: 5px 8px; border-bottom: 1px solid #303a45; }
.cue-trace td:first-child { font-variant-numeric: tabular-nums; }
.cue-trace tr[data-cue="contact"] { color: #ffe0a3; }
.cue-trace tr[data-cue="settled"] { color: #9ff6db; }
.reference-video { width: 100%; border-radius: 9px; background: #090b0e; display: block; }
.reference-actions { display: flex; flex-wrap: wrap; gap: 7px; margin: 10px 0; }
.reference-time { color: #aac1d5; font-variant-numeric: tabular-nums; }
@media (max-width: 1000px) {
    .review-layout { grid-template-columns: minmax(260px, 378px) minmax(260px, 1fr); }
    .reference-panel { grid-column: 2; }
    .preview-panel { grid-row: span 2; }
    .reference-video { max-height: 360px; }
}
@media (max-width: 650px) {
    .review-shell { padding: 16px; }
    .review-layout { display: flex; flex-direction: column; }
    .review-panel { width: 100%; }
    .preview-panel { max-width: 378px; margin: auto; }
}
</style>
"""

INSPECTOR_HTML = """
<main class="review-shell">
    <header class="review-heading">
        <h1>Timing + camera composition · __PROFILE__</h1>
        <p>Inspect overlapping camera and piece motion, a persistent destination shot,
        a temporary camera accent, and a return to wide. The piece movement presets are unchanged.</p>
        <p><a href="__COMPARE_PATH__">Open __COMPARE_PROFILE__ comparison</a> ·
        <a href="reference_analysis/index.html">Reference analysis viewer</a></p>
    </header>
    <div class="review-layout">
        <section class="review-panel preview-panel">
            <h2>Generated composition</h2>
            <div class="preview-stage" id="previewStage"></div>
            <div id="playControls"></div>
            <p class="review-note">The full 1080 × 1920 composition is scaled for this inspector.
            The reaction panel stays fixed while the chess scene moves.</p>
        </section>
        <section class="review-panel">
            <h2>Move cues</h2>
            <div class="move-strip" id="moveStrip"></div>
            <div class="cue-status" aria-live="polite">
                <span id="activeMove">Ready to play</span>
                <strong id="activeCue">Waiting</strong>
                <span id="activeTime">0.000 s</span>
            </div>
            <div class="recipe-info"><dl>
                <dt>Profile</dt><dd>__PROFILE__</dd>
                <dt>Piece launch delay</dt><dd id="pieceDelay">—</dd>
                <dt>Camera transition</dt><dd id="cameraDuration">—</dd>
                <dt>Piece movement</dt><dd id="moveDuration">—</dd>
                <dt>Arrival cue after launch</dt><dd id="contactDelay">—</dd>
                <dt>Reading hold</dt><dd id="holdDuration">—</dd>
                <dt>Hero / impulse</dt><dd id="recipeFlags">—</dd>
                <dt>Persistent target</dt><dd id="poseTarget">Wide</dd>
            </dl></div>
            <div class="cue-trace" id="cueTrace">
                <table><thead><tr><th>Time</th><th>Move</th><th>Cue</th></tr></thead>
                <tbody id="cueRows"></tbody></table>
            </div>
            <p class="review-note">Contact marks the existing arrival/overshoot keyframe, not a
            simulated collision. Existing chess
            sounds, checks and meme triggers retain their settled landing boundary.</p>
            <p class="review-note">Watch e5 retain the e4 shot, Nf3!! hold with an independent
            camera accent during its authored reading pause, and Nf6@J return wide.
            No capture effects or new piece choreography.</p>
        </section>
        <section class="review-panel reference-panel">
            <h2>Reference · independent playback</h2>
            <video id="referenceVideo" class="reference-video" controls muted playsinline preload="metadata"
                src="../assets/references/Reference.mp4"></video>
            <div class="reference-actions">
                <button type="button" data-reference-time="11.1">11.1 s · pull-out</button>
                <button type="button" data-reference-time="18.8">18.8 s · push</button>
                <button type="button" data-reference-time="27.3">27.3 s · hero hold</button>
            </div>
            <div class="reference-actions">
                <button type="button" id="previousFrame">−1 frame</button>
                <button type="button" id="nextFrame">+1 frame</button>
                <label>Speed <select id="referenceRate">
                    <option value="0.25">0.25×</option>
                    <option value="0.5" selected>0.5×</option>
                    <option value="1">1×</option>
                </select></label>
            </div>
            <div class="reference-time" id="referenceTime">0.000 s</div>
            <p class="review-note">Bookmarks pause on the selected source time. Use the native
            play control to watch. Frame stepping uses the source's 60 fps cadence.
            Later spin, reaction, lighting and particle stages are outside this demo.</p>
        </section>
    </div>
</main>
<script>
(() => {
    const stage = document.getElementById('previewStage');
    stage.appendChild(document.querySelector('.short-canvas'));
    document.getElementById('playControls').appendChild(document.querySelector('.controls'));
    const resize = () => stage.style.setProperty('--preview-scale', stage.clientWidth / 1080);
    new ResizeObserver(resize).observe(stage);
    resize();

    const tokens = __TOKENS__;
    // JSON serializes scene.moves and timeline moves separately; use the actual
    // dispatched objects so repeated source/destination pairs still identify correctly.
    const dispatchedMoves = timeline.filter(event => event.type === 'move').map(event => event.move);
    const strip = document.getElementById('moveStrip');
    tokens.forEach(token => {
        const span = document.createElement('span');
        span.className = 'move-token';
        span.textContent = token;
        strip.appendChild(span);
    });
    let origin = null;
    const rows = document.getElementById('cueRows');
    playButton.addEventListener('click', () => {
        if (playing) return;
        origin = null;
        rows.replaceChildren();
        document.getElementById('activeCue').textContent = 'Preparing';
        document.getElementById('activeTime').textContent = '0.000 s';
        [...strip.children].forEach(node => node.classList.remove('active'));
    }, true);

    timelineScheduler.subscribe(event => {
        if (origin === null) origin = event.time;
        const elapsed = ((event.time - origin) / 1000).toFixed(3) + ' s';
        const index = dispatchedMoves.indexOf(event.move);
        const label = tokens[index] || event.move?.from + ' → ' + event.move?.to;
        document.getElementById('activeMove').textContent = label;
        document.getElementById('activeCue').textContent = event.cue;
        document.getElementById('activeTime').textContent = elapsed;
        [...strip.children].forEach((node, i) => node.classList.toggle('active', i === index));
        for (const key of ['pieceDelay', 'cameraDuration', 'moveDuration', 'contactDelay', 'holdDuration']) {
            const value = event.plan?.[key];
            document.getElementById(key).textContent = Number.isFinite(value) ? Math.round(value) + ' ms' : '—';
        }
        document.getElementById('recipeFlags').textContent =
            (event.plan?.hero ? 'Yes' : 'No') + ' / ' + (event.plan?.impulse ? 'Yes' : 'No');
        if (camera.pose) {
            document.getElementById('poseTarget').textContent =
                camera.pose.zoom.toFixed(2) + '× / ' + camera.pose.rotation.toFixed(1) + '°';
        }
        const row = document.createElement('tr');
        row.dataset.cue = event.cue;
        for (const value of [elapsed, label, event.cue]) {
            const cell = document.createElement('td');
            cell.textContent = value;
            row.appendChild(cell);
        }
        rows.appendChild(row);
        while (rows.children.length > 80) rows.firstChild.remove();
        const trace = document.getElementById('cueTrace');
        trace.scrollTop = trace.scrollHeight;
    });

    const reference = document.getElementById('referenceVideo');
    reference.playbackRate = 0.5;
    const openBoardSection = () => { reference.currentTime = 18.8; };
    if (reference.readyState >= 1) openBoardSection();
    else reference.addEventListener('loadedmetadata', openBoardSection, {once: true});
    const showReferenceTime = () => {
        document.getElementById('referenceTime').textContent = reference.currentTime.toFixed(3) + ' s';
    };
    for (const event of ['timeupdate', 'seeked', 'loadedmetadata']) {
        reference.addEventListener(event, showReferenceTime);
    }
    document.querySelectorAll('[data-reference-time]').forEach(button => {
        button.addEventListener('click', () => {
            reference.pause();
            reference.currentTime = Number(button.dataset.referenceTime);
        });
    });
    const step = direction => {
        reference.pause();
        reference.currentTime = Math.max(0, Math.min(
            Number.isFinite(reference.duration) ? reference.duration : Infinity,
            reference.currentTime + direction / 60));
    };
    document.getElementById('previousFrame').addEventListener('click', () => step(-1));
    document.getElementById('nextFrame').addEventListener('click', () => step(1));
    document.getElementById('referenceRate').addEventListener('change', event => {
        reference.playbackRate = Number(event.target.value);
    });
})();
</script>
"""


def inspected_scene(scene, profile):
    import json

    comparison = "LEGACY" if profile == "REFERENCE" else "REFERENCE"
    comparison_path = "timing_camera_legacy.html" if comparison == "LEGACY" else "timing_camera_demo.html"
    html = render_scene(
        scene,
        timing_profile=profile,
        meme_path="../assets/memes/MonkeyCry.mp4",
        meme_volume=0.25,
        meme_comment_text="Fixed reaction layer · camera only moves the chess scene",
    )
    inspector = (INSPECTOR_HTML.replace("__PROFILE__", profile)
                 .replace("__COMPARE_PROFILE__", comparison)
                 .replace("__COMPARE_PATH__", comparison_path)
                 .replace("__TOKENS__", json.dumps(LINE.split())))
    return (html.replace("</head>", INSPECTOR_STYLE + "</head>")
            .replace("</body>", inspector + "</body>"))


def generate():
    scene = compile_sequence(chess.Board(), LINE, default_pause=0.7)
    output = Path("output")
    output.mkdir(exist_ok=True)
    for profile, filename in [("REFERENCE", "timing_camera_demo.html"),
                              ("LEGACY", "timing_camera_legacy.html")]:
        path = output / filename
        path.write_text(inspected_scene(scene, profile), encoding="utf-8")
        print(f"Created {path}")
    print("Preview: http://localhost:8000/output/timing_camera_demo.html")
    print("Serve the project root with: python3 -m http.server 8000")


if __name__ == "__main__":
    generate()
