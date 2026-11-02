"""Production layouts at 1080x1920; run directly with the project Python."""
from pathlib import Path
import sys
import chess
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tests'))
from src.renderer.chess_state import compile_sequence
from src.renderer.composition import render_scene
from src.renderer.layout import layout_config
from test_reactions_browser import assert_final, expected_position, instrument


def main():
    artifacts = ROOT / 'output/layout_verification'
    artifacts.mkdir(exist_ok=True)
    scene = compile_sequence(chess.Board(), 'e4@J(0s) d5(0s) exd5!@K(0s) Qxd5!!@L(meme)(0.3s) Nc3@J(0s)')
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        try:
            for mode in ('fixed', 'off', 'crop'):
                meme_mode = 'fixed' if mode == 'fixed' else 'off'
                layout_mode = 'crop' if mode == 'crop' else 'safe'
                html = render_scene(scene, meme_mode=meme_mode, layout_mode=layout_mode, directing_profile='AUTO',
                                    meme_path='../assets/memes/MonkeyCry.mp4', meme_comment_text='Reaction')
                path = artifacts / f'{mode}.html'
                path.write_text(html.replace('../assets/', (ROOT / 'assets').as_uri() + '/'))
                page = browser.new_page(viewport={'width': 1080, 'height': 1920})
                errors = []
                page.on('pageerror', lambda error: errors.append(str(error)))
                page.goto(path.as_uri())
                page.wait_for_function('[...document.images].every(i => i.complete && i.naturalWidth > 0)')
                geometry = page.evaluate('''() => {
                    const rect = selector => document.querySelector(selector).getBoundingClientRect().toJSON();
                    return {canvas:rect('.short-canvas'), viewport:rect('.board-area'),
                            board:rect('.board-background'), meme:!!document.querySelector('.reaction-area'),
                            cameraSize:cameraConfig.viewportSize};
                }''')
                config = layout_config(meme_mode, layout_mode)
                assert geometry['canvas']['width'] == 1080 and geometry['canvas']['height'] == 1920
                assert geometry['meme'] == (mode == 'fixed')
                for field, key in [('x', 'BOARD_X'), ('y', 'BOARD_Y'), ('width', 'BOARD_SIZE')]:
                    assert abs(geometry['board'][field] - config[key]) < .01, geometry
                assert geometry['viewport']['height'] == config['VIEWPORT_HEIGHT']
                page.add_style_tag(content='.controls { visibility: hidden; }')
                page.locator('.short-canvas').screenshot(path=str(artifacts / f'{mode}-wide.png'))
                if mode == 'off':
                    # Conservative simultaneous positive maxima of all transient tracks.
                    # Verify complete wide board containment, including rotation and kicks.
                    page.evaluate('''() => {
                        for (const [id, name] of [['cameraReframe','reframe'],['cameraImpact','impact'],['cameraHero','hero']]) {
                            const t=cameraConfig.transient[name];
                            document.getElementById(id).style.transform=`translate(${t.translation}px,${t.translation}px) rotate(${t.rotation}deg) scale(${1+t.zoom})`;
                        }
                        const a=document.querySelector('.board-area').getBoundingClientRect();
                        const b=document.querySelector('.board-background').getBoundingClientRect();
                        if(b.left<a.left || b.right>a.right || b.top<a.top || b.bottom>a.bottom) throw Error('Wide board clips at maximum camera envelope');
                        cameraMotion.reset();
                    }''')
                # Check every destination at both focused shot levels using actual geometry.
                page.evaluate('''async mode => {
                    const a=document.querySelector('.board-area').getBoundingClientRect();
                    if(mode!=='fixed') for (const [id,name] of [['cameraReframe','reframe'],['cameraImpact','impact'],['cameraHero','hero']]) {
                        const t=cameraConfig.transient[name];
                        document.getElementById(id).style.transform=`translate(${t.translation}px,${t.translation}px) rotate(${t.rotation}deg) scale(${1+t.zoom})`;
                    }
                    for(const shot of ['K','L']) for(const file of 'abcdefgh') for(let rank=1;rank<=8;rank++) {
                        const square=file+rank;
                        await camera.to(camera_focus_destination(square,shot),0);
                        const r=destination_region(square,shot), p=document.createElement('div');
                        Object.assign(p.style,{position:'absolute',left:(r.left+540)+'px',top:(r.top+540)+'px',width:(r.right-r.left)+'px',height:(r.bottom-r.top)+'px'});
                        board.appendChild(p);const b=p.getBoundingClientRect();p.remove();
                        if(b.left<a.left-.1 || b.right>a.right+.1 || b.top<a.top-.1 || b.bottom>a.bottom+.1) throw Error('Focused neighborhood clips: '+square+shot);
                    }
                    if(mode==='crop') for(const file of 'abcdefgh') for(let rank=1;rank<=8;rank++) {
                        const square=file+rank;
                        await camera.directMove({camera_directive:'J',to:square});
                        if(camera.pose.zoom!==cameraConfig.wideZoom) throw Error('Wide crop changed zoom');
                        const q=squareToCoords(square),p=document.createElement('div');
                        Object.assign(p.style,{position:'absolute',left:q.x*squareSize+'px',top:q.y*squareSize+'px',width:squareSize+'px',height:squareSize+'px'});
                        board.appendChild(p);const b=p.getBoundingClientRect();p.remove();
                        if(b.left<a.left-.1 || b.right>a.right+.1 || b.top<a.top-.1 || b.bottom>a.bottom+.1) throw Error('Wide crop destination clips: '+square);
                    }
                    camera.reset();
                    cameraMotion.reset();
                }''', mode)
                instrument(page)
                page.evaluate('''() => {
                    timelineScheduler.subscribe(e => {
                        if(!window.heroReady && e.cue==='holdStart' && e.move.annotation==='!!') {
                            window.heroReady=true;
                            for(const animation of document.getAnimations()) animation.pause();
                        }
                    });
                    window.playbackDone=playSequence();
                }''')
                page.wait_for_function('window.heroReady === true')
                page.locator('.short-canvas').screenshot(path=str(artifacts / f'{mode}-hero.png'), animations='allow')
                page.evaluate('() => { for(const animation of document.getAnimations()) animation.play(); }')
                page.evaluate('async () => await window.playbackDone')
                assert_final(page, expected_position(scene))
                page.evaluate('''() => {
                    const land=records.filter(r=>r.cue==='settled'), sound=records.filter(r=>r.cue==='sound');
                    if(land.length!==moves.length || sound.length!==moves.length || sound.some((s,i)=>Math.abs(s.time-land[i].time)>35)) throw Error('Settled audio timing changed');
                }''')
                page.evaluate('async () => { await lightingSystem.finished; if(lightingSystem.sessions.size || document.querySelector(".light-primitive")) throw Error("Lighting leak"); }')
                page.evaluate('async () => await playSequence()')
                assert_final(page, expected_position(scene))
                assert not errors, errors
                page.close()
                print(f'PASS: {mode}: geometry, all 128 focused shots, playback, replay, final chess state and cleanup', flush=True)
        finally:
            browser.close()


if __name__ == '__main__':
    main()
