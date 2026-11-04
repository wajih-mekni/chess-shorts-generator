"""Real held clocks, t=0/replay, removal, replacement and finite completion."""
from pathlib import Path
import sys
import tempfile
import chess
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.generate_piece_meme_demo import START_FEN, DEMO_SEQUENCE, INITIAL_PIECE_MEMES, REGISTRY
from src.renderer.chess_state import compile_sequence
from src.renderer.composition import render_scene

def main():
    with tempfile.TemporaryDirectory() as folder,sync_playwright() as pw:
        browser=pw.chromium.launch()
        page=browser.new_page(); errors=[]
        page.on('pageerror',lambda e:errors.append(str(e)))
        def load(line, initial=INITIAL_PIECE_MEMES, mode='on'):
            scene=compile_sequence(chess.Board(START_FEN),line)
            html=render_scene(scene,piece_meme_mode=mode,piece_memes=REGISTRY,initial_piece_memes=initial,
                              directing_profile='AUTO',meme_mode='off')
            path=Path(folder)/'scene.html';path.write_text(html.replace('../assets/',(ROOT/'assets').as_uri()+'/'))
            page.goto(path.as_uri());page.evaluate('async()=>{if(window.preparePieceMemes)await window.preparePieceMemes();prepareMoveAudio=async()=>{};playMoveSound=()=>{};}')
        load(DEMO_SEQUENCE)
        page.evaluate('''async()=>{
            const assert=(v,m)=>{if(!v)throw Error(m);};
            assert(pieceMemeSystem.active.size===1,'t=0 absent');
            for(let replay=0;replay<2;replay++){
                const king=pieceBySquare.e8;
                const original=[...pieceMemeSystem.active][0];
                assert(original.actor===king&&original.hold,'initial actor');
                original.clock.currentTime=60000;
                assert(original.clock.playState!=='finished','hold expired');
                await animateMove(scene.moves[0],{shot:'J',focus:null});
                await animateMove(scene.moves[1],{shot:'J',focus:null});
                assert(pieceBySquare.d7===king&&original.layer.isConnected,'hold did not follow king');
                await animateMove(scene.moves[2],{shot:'J',focus:null});
                assert(original.closed&&pieceMemeSystem.active.size===2,'replacement duplicated face');
                const replacement=[...pieceMemeSystem.active].find(e=>e.actor===king);
                assert(replacement.media.tagName==='VIDEO'&&replacement.hold,'held video absent');
                const rook=pieceBySquare.h8,rookEntry=[...pieceMemeSystem.active].find(e=>e.actor===rook);
                await animateMove(scene.moves[3],{shot:'J',focus:null});
                assert(pieceBySquare.c6===king&&replacement.layer.isConnected,'replacement lost actor');
                await animateMove(scene.moves[4],{shot:'J',focus:null});
                assert(replacement.closed&&rookEntry.closed&&!pieceMemeSystem.active.size,'remove/capture leak');
                resetPieces();assert(pieceMemeSystem.active.size===1,'reset did not restore initial');
            }
            resetPieces();await playSequence();assert(!pieceMemeSystem.active.size,'sequence cleanup');
            await playSequence();assert(!pieceMemeSystem.active.size,'replay cleanup');
        }''')
        # An unremoved held video must never hold completion open; timed tails still finish.
        load('Qh5+^N@J(piece:HikaruFace,dur=.3)(0s)',
             [dict(square='e8',meme='HikaruLaugh',hold=True,loop=True)])
        page.evaluate('''async()=>{
            const start=performance.now();await Promise.race([playSequence(),new Promise((_,reject)=>setTimeout(()=>reject(Error('held meme blocked completion')),7000))]);
            if(pieceMemeSystem.active.size||performance.now()-start>6500)throw Error('held cleanup failed');
            const videos=[...pieceMemeSystem.media.values()].filter(n=>n.tagName==='VIDEO');
            if(videos.some(v=>!v.paused||v.isConnected||v.currentTime>.01))throw Error('held video leak');
        }''')
        # Removal targets the incoming actor at landing, and no-ops on empty squares.
        load('Qh5+^N@J(pm-remove:h5)(pm-remove:a4)(0s)',[dict(square='h2',meme='HikaruFace',hold=True)])
        page.evaluate('async()=>{await playSequence();if(pieceMemeSystem.active.size)throw Error("removal failed");}')
        load('Qh5+^N@J(pm-remove:e8)(0s)',mode='off')
        page.evaluate('async()=>{await playSequence();if(pieceMemeSystem.media.size||pieceMemeSystem.active.size)throw Error("off created media");}')
        assert not errors,errors
        browser.close()
        print('PASS: initial t=0, held identity, replacement, removal, capture, reset/replay, video cleanup, finite completion and off mode')
if __name__=='__main__':main()
