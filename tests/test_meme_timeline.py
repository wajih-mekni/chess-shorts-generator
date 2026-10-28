"""Parser and real-Chromium timing checks for meme timeline events.

Run: python tests/test_meme_timeline.py
Requires Playwright + Chromium (same Python dependencies as the exporter).
"""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import tempfile
import threading
import sys
import chess

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.renderer.chess_state import compile_sequence
from src.renderer.composition import render_scene
from src.renderer.camera import BRILLIANT_POST_HOLD
CASES = [
    '(meme) e4(1s) e5(1s) Nf3',
    'e4(1s) e5(1s) (meme) Nf3',
    'e4(1s) e5!!(meme)(3s) Nf3',
    'e4(1s) e5(1s) Nf3',
    '(meme) e4(meme)(0.25s) (meme) e5(0.25s)',
]


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *_):
        pass


def generate(line, output, meme=True):
    scene = compile_sequence(chess.Board(), line, 2)
    output.write_text(render_scene(scene,
        meme_path="../assets/memes/MonkeyCry.mp4" if meme else None,
        meme_volume=0.8, music_path="../assets/music/background.mp3", music_volume=0.8))
    return scene


def instrument(page):
    page.evaluate('''() => {
        window.trace = [];
        const record = (kind, extra={}) => trace.push({kind, time:performance.now(), ...extra});
        const move = animateMove;
        animateMove = async function(m) {
            record('move-start',{to:m.to});
            await move(m);
            record('move-end',{to:m.to});
        };
        const slide = slidePieceToSquare;
        slidePieceToSquare = async function(piece,square) {
            await slide(piece,square);
            record('land',{to:square});
        };
        const sfx = playMoveSound;
        playMoveSound = function(m) { record('sound',{to:m.to}); return sfx(m); };
        const meme = startMemeVideo;
        startMemeVideo = function() {
            const alreadyStarted = memeStarted;
            meme();
            if (!alreadyStarted && memeStarted) record('meme');
        };
        const effects = showMoveEffects;
        showMoveEffects = function(m) { effects(m);record('effects',{to:m.to}); };
    }''')


def event(trace, kind, to=None):
    return next(e['time'] for e in trace if e['kind'] == kind and (to is None or e.get('to') == to))


def main():
    server = ThreadingHTTPServer(('127.0.0.1', 0), partial(QuietHandler, directory=str(ROOT)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        with tempfile.TemporaryDirectory(prefix='meme-timeline-', dir=ROOT/'output') as folder, sync_playwright() as pw:
            work = Path(folder)
            # Fixtures are one level deeper than the normal HTML: preserve asset URLs.
            for i,line in enumerate(CASES):
                path = work/f'case{i}.html'
                scope = generate(line,path)
                path.write_text(path.read_text().replace('../assets/', '../../assets/'))
                assert len(scope['moves']) == (2 if i == 4 else 3)
                assert scope['moves'][0]['from'] == 'e2'
                if i == 2:
                    assert scope['moves'][1]['start_meme'] is True
                    assert scope['moves'][1]['annotation'] == '!!'
                    assert scope['moves'][1]['pause'] == 3
                if i in (0,1):
                    assert scope['timeline'][0 if i == 0 else 2] == {'type':'meme'}
            missing = work/'no-meme.html'
            generate('e4(meme)(0s) (meme) e5(0s)',missing,meme=False)
            missing.write_text(missing.read_text().replace('../assets/', '../../assets/'))
            browser = pw.chromium.launch(headless=True, ignore_default_args=['--mute-audio'])
            try:
                for i in range(len(CASES)):
                    page = browser.new_page(viewport={'width':1080,'height':1920})
                    errors=[]
                    page.on('pageerror',lambda error:errors.append(str(error)))
                    page.goto(f'http://127.0.0.1:{server.server_port}/output/{work.name}/case{i}.html')
                    page.wait_for_function('memeVideo.readyState >= 3 && [...moveAudio.values()].every(m=>m.readyState>=3)')
                    instrument(page)
                    first_frame = page.locator('#memeVideo').screenshot()
                    assert page.evaluate('memeVideo.paused && memeVideo.currentTime === 0')
                    await_count = 2 if i == 1 else 1
                    for replay in range(await_count):
                        page.evaluate('trace.length = 0')
                        page.click('#playButton')
                        page.wait_for_function("trace.some(e=>e.kind==='land' && e.to==='e4')")
                        if i in (1,2):
                            assert page.evaluate('memeVideo.paused && memeVideo.currentTime === 0')
                            assert page.locator('#memeVideo').screenshot() == first_frame, 'first frame must stay frozen'
                            assert page.evaluate('backgroundMusic.currentTime > 0 && !backgroundMusic.paused')
                        page.wait_for_function("trace.some(e=>e.kind==='meme')")
                        page.wait_for_function('!memeVideo.paused && memeVideo.currentTime > 0.1')
                        assert page.evaluate('!memeVideo.muted && memeVideo.volume === 0.8')
                        if i == 2:
                            before=page.evaluate('memeVideo.currentTime')
                            page.wait_for_timeout(800)
                            assert page.evaluate('memeVideo.currentTime') > before + 0.5
                            assert not page.evaluate("trace.some(e=>e.kind==='move-start' && e.to==='f3')")
                        page.wait_for_function('hasPlayed && !playing')
                        trace=page.evaluate('trace')
                        starts=[e for e in trace if e['kind']=='meme']
                        assert len(starts)==1, 'repeated triggers must not restart video'
                        meme_time=starts[0]['time']
                        if i in (0,3,4):
                            assert meme_time <= event(trace,'move-start','e4')
                        elif i==1:
                            assert event(trace,'move-end','e5') <= meme_time <= event(trace,'move-start','f3')
                            assert 950 <= meme_time-event(trace,'effects','e5') <= 1250
                        else:
                            assert abs(meme_time-event(trace,'land','e5')) < 30
                            assert abs(meme_time-event(trace,'sound','e5')) < 30
                            assert 2950 + BRILLIANT_POST_HOLD <= event(trace,'move-start','f3')-event(trace,'effects','e5') <= 3250 + BRILLIANT_POST_HOLD
                        print(f'PASS Chromium case {i+1}, replay {replay}: {CASES[i]}',flush=True)
                    assert not errors,errors
                    page.close()
                page=browser.new_page()
                page.goto(f'http://127.0.0.1:{server.server_port}/output/{work.name}/no-meme.html')
                page.click('#playButton');page.wait_for_function('hasPlayed && !playing')
                assert page.locator('#memeVideo').count()==0
                print('PASS: missing meme is a no-op; all parsing, first-frame, trigger, audio-state and replay checks passed.')
            finally:
                browser.close()
    finally:
        server.shutdown();server.server_close()


if __name__ == '__main__':
    main()
