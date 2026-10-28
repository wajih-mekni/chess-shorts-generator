"""Real browser checks for cinematic keyframes, landing and static camera.
Run: python tests/test_piece_motion.py (after generating motion_demo.html).
"""
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]


def main():
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page(viewport={'width':1080, 'height':1920})
        errors = []
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.goto((ROOT/'output/motion_demo.html').as_uri())
        page.evaluate('''async () => {
            const assert = (ok, message) => {if (!ok) throw Error(message);};
            const cameraBefore = board.getBoundingClientRect().toJSON();
            for (const name of Object.keys(motion.presets)) {
                resetPieces();
                const piece = pieceBySquare.e2;
                let landed = false;
                const task = animatePieceMove({from:'e2',to:'e4',animation_preset:name},
                    () => landed = true);
                const animation = piece.getAnimations()[0];
                animation.pause();
                animation.currentTime = motion.presets[name].duration * 0.38;
                assert(!landed, 'premature landing');
                const style = getComputedStyle(piece);
                const matrix = new DOMMatrix(style.transform);
                assert(Math.hypot(matrix.a,matrix.b) > 1.04, 'missing scale lift');
                assert(Math.abs(matrix.b) > 0, 'missing rotation');
                assert(parseFloat(style.top) < 6*squareSize && parseFloat(style.top) > 4*squareSize,
                       'midpoint must lie between source and target');
                animation.finish();
                await task;
                assert(landed && pieceBySquare.e4 === piece, 'landing not committed');
                assert(piece.style.left === 4*squareSize+'px' && piece.style.top === 4*squareSize+'px',
                       'incorrect final coordinates');
                assert(getComputedStyle(piece).transform === 'none', 'transform leaked');
                assert(piece.getAnimations().length === 0, 'animation leaked');
            }
            const preset = motion.presets.NORMAL_MOVE;
            const frames = pieceMoveKeyframes({x:0,y:135}, {x:0,y:0}, preset);
            assert(parseFloat(frames[2].top) === 0, 'overshoot escaped top edge');
            const horizontal = pieceMoveKeyframes({x:0,y:0}, {x:270,y:0}, preset);
            assert(parseFloat(horizontal[2].left)>270, 'missing overshoot');
            resetPieces();
            const piece = pieceBySquare.e2;
            const task = slidePieceToSquare(piece,'e4');
            piece.getAnimations()[0].cancel();
            let cancelled = false;
            try {await task;} catch(e) {cancelled = e.name === 'AbortError';}
            assert(cancelled && piece.style.top === 6*squareSize+'px', 'cancel committed destination');
            assert(piece.getAnimations().length===0, 'cancel leaked animation');
            assert(JSON.stringify(board.getBoundingClientRect().toJSON()) === JSON.stringify(cameraBefore),
                   'camera moved');
            resetPieces();
        }''')
        page.click('#playButton')
        page.wait_for_function('hasPlayed && !playing')
        page.evaluate('''() => {
            for (const square of ['e4','e5','f3','c6','c4']) {
                if (!pieceBySquare[square]) throw Error('Missing final piece: '+square);
            }
        }''')
        page.click('#playButton')
        page.wait_for_function('hasPlayed && !playing')
        assert not errors, errors
        browser.close()
        print('PASS: all presets, midpoint scale/rotation, exact settling, overshoot bounds, cancellation, static camera and replay.')


if __name__ == '__main__':
    main()
