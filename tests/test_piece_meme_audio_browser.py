"""Per-video audio permission, cue sync, overlap and cleanup in real Chromium."""
from pathlib import Path
import sys,tempfile
import chess
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from src.renderer.chess_state import compile_sequence
from src.renderer.composition import render_scene
from src.generate_piece_meme_demo import REGISTRY,START_FEN

def main():
    line=('Qh5+^N@J(pm:e8:HikaruLaugh,audio=true,hold=true,when=start)'
          '(pm:h8:HikaruLaugh,audio=true,hold=true)(piece:HikaruLaugh,dur=.2)(.3s) '
          'Kd7^N@J(pm:d7:HikaruLaugh,audio=true,hold=true)(0s) '
          'Qxh8^N@J(pm-remove:d7)(0s)')
    line=line.replace('(.3s)','(0.3s)')
    scene=compile_sequence(chess.Board(START_FEN),line)
    html=render_scene(scene,piece_meme_mode='on',piece_memes=REGISTRY,directing_profile='AUTO',meme_mode='off',
        initial_piece_memes=[dict(square='e8',meme='HikaruLaugh',audio=True,hold=True)])
    with tempfile.TemporaryDirectory() as folder,sync_playwright() as pw:
        browser=pw.chromium.launch(args=['--autoplay-policy=document-user-activation-required'])
        page=browser.new_page();errors=[];warnings=[]
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.on('console',lambda m:warnings.append(m.text) if m.type=='warning' else None)
        path=Path(folder)/'scene.html';path.write_text(html.replace('../assets/',(ROOT/'assets').as_uri()+'/'))
        page.goto(path.as_uri());page.evaluate('async()=>{await window.preparePieceMemes();}')
        page.evaluate('''()=>{
            const assert=(v,m)=>{if(!v)throw Error(m);};
            assert([...pieceMemeSystem.active].every(e=>e.media.muted),'preview sounded');
            window.audioEvents=[];window.overlap=false;
            const attach=pieceMemeSystem.attach;
            pieceMemeSystem.attach=function(actor,key,c){
                attach.call(this,actor,key,c);
                const e=[...this.active].find(e=>e.actor===actor);
                assert(e.media.muted===!(c.audio&&this.audioActive),'wrong opt-in mute');
                assert(e.media.currentTime<.1,'did not restart audio');
                audioEvents.push(key);
                if([...this.active].filter(e=>!e.media.muted).length>=2)overlap=true;
            };
            const close=pieceMemeSystem.close;
            pieceMemeSystem.close=function(e){close.call(this,e);assert(e.media.muted&&e.media.paused&&e.media.currentTime<.01,'audio cleanup');};
        }''')
        for replay in range(2):
            page.click('#playButton');page.wait_for_function('hasPlayed && !playing',timeout=20000)
            assert page.evaluate('overlap && !pieceMemeSystem.active.size')
            assert page.evaluate('[...pieceMemeSystem.media.values()].every(v=>v.paused&&v.muted&&v.currentTime<.01)')
            events=page.evaluate('audioEvents.splice(0)')
            if replay: assert events==previous,(events,previous)
            previous=events
        # Simulate decoder lag: audible playback must not be repeatedly seeked.
        page.evaluate('''async()=>{
            window.PIECE_MEME_DEBUG=true;
            pieceMemeSystem.audioActive=true;
            const [key,c]=Object.entries(pieceMemeConfig.entries).find(([k,c])=>c.audio&&c.type==='video');
            const actor=pieceBySquare.a1;pieceMemeSystem.attach(actor,key,c);
            const entry=[...pieceMemeSystem.active][0];entry.media.playbackRate=.5;
            await new Promise(r=>setTimeout(r,250));
            window.pieceMemeDiagnostics=[];
            await new Promise(r=>setTimeout(r,750));
            if(pieceMemeDiagnostics.some(e=>e.event==='sync-seek'))throw Error('audio decoder chased wall clock');
            entry.clock.pause();entry.clock.currentTime=700;
            await new Promise(r=>setTimeout(r,250));
            if(Math.abs(entry.media.currentTime-.7)>.05)throw Error('paused audio seek failed');
            entry.clock.currentTime=200;await new Promise(r=>setTimeout(r,250));
            if(Math.abs(entry.media.currentTime-.2)>.05)throw Error('backward audio seek failed');
            entry.clock.play();await new Promise(r=>setTimeout(r,150));
            entry.clock.currentTime=2000;await new Promise(r=>setTimeout(r,250));
            if(entry.media.currentTime<1.9)throw Error('running audio seek failed');
            entry.media.playbackRate=1;pieceMemeSystem.reset();window.PIECE_MEME_DEBUG=false;
        }''')
        # Reset cancels the existing movement promise with its normal AbortError.
        page.evaluate('''()=>{const play=playSequence;playSequence=async()=>{try{await play();}catch(e){if(e.name!=="AbortError")throw e;}};}''')
        page.click('#playButton');page.wait_for_function('[...pieceMemeSystem.active].some(e=>!e.media.muted)')
        page.evaluate('resetPieces()')
        assert page.evaluate('[...pieceMemeSystem.media.values()].every(v=>v.muted)')
        assert not errors,errors
        assert not [w for w in warnings if 'piece meme' in w.lower()],warnings
        browser.close()
        print('PASS: silent preview, start/land audio, simultaneous held audio, timed default mute, replacement/removal/capture, replay and reset')
if __name__=='__main__':main()
