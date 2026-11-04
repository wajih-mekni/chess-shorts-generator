"""Real child attachment, media clocks, captures, promotion, panel isolation and off mode."""
from pathlib import Path
import sys
import tempfile
import chess
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.renderer.chess_state import compile_sequence
from src.renderer.composition import render_scene
from src.generate_piece_meme_demo import REGISTRY, main as generate_demo


def main():
    generate_demo()
    with tempfile.TemporaryDirectory() as folder,sync_playwright() as pw:
        browser=pw.chromium.launch()
        try:
            page=browser.new_page(viewport={'width':1080,'height':1920});errors=[]
            page.on('pageerror',lambda e:errors.append(str(e)))
            def load(scene,**opts):
                html=render_scene(scene,directing_profile='AUTO',piece_memes=REGISTRY,**opts)
                path=Path(folder)/'scene.html';path.write_text(html.replace('../assets/',(ROOT/'assets').as_uri()+'/'))
                page.goto(path.as_uri())
                page.wait_for_function('[...document.images].every(i=>i.complete&&i.naturalWidth>0)')
                page.evaluate('async()=>{prepareMoveAudio=async()=>{};playMoveSound=()=>{};if(window.preparePieceMemes)await window.preparePieceMemes();}')
            for mode,layout in [('fixed','safe'),('off','safe'),('off','crop')]:
                scene=compile_sequence(chess.Board(),'e4(0s) e5(0s) Qh5!!^N~queen-spin(piece:HikaruFace,when=start,dur=2,shape=circle,y=-10)(0s) Nc6!!^A~jump(piece:HikaruLaugh,when=land,dur=1,loop=true)(0s)')
                load(scene,piece_meme_mode='on',meme_mode=mode,layout_mode=layout,
                     meme_path='../assets/memes/Cr7.mp4',meme_volume=0)
                page.evaluate(r'''async()=>{
                    const assert=(v,m)=>{if(!v)throw Error(m);};
                    window.triggers=[];
                    const attach=pieceMemeSystem.attach;
                    pieceMemeSystem.attach=function(actor,key,config){
                        attach.call(this,actor,key,config);
                        const entry=[...this.active].find(e=>e.actor===actor);
                        assert(entry.layer.parentElement===actor.reaction,'not an actor child');
                        assert(actor.reaction.contains(actor.sprite),'normal sprite removed');
                        assert(entry.layer.closest('.piece')===actor,'wrong actor');
                        if(config.type==='video')assert(entry.media.muted&&entry.media.playsInline&&!entry.media.controls,'video flags');
                        triggers.push({id:config.id,when:config.when,square:actor.dataset.square,transform:entry.layer.style.transform});
                    };
                    timelineScheduler.subscribe(e=>{
                        const key=e.move.piece_meme,c=pieceMemeConfig.entries[key];
                        if(!c)return;
                        if((c.when==='start'&&e.cue==='launch')||(c.when==='land'&&e.cue==='settled'))
                            assert([...pieceMemeSystem.active].some(a=>a.layer.dataset.memeId===c.id),'wrong trigger boundary');
                        if(c.when==='land'&&e.cue==='launch')assert(!document.querySelector('.piece-meme-media[src*="hikaruLaugh"]'),'landing video appeared early');
                    });
                    const panel=document.querySelector('.reaction-area'),rect=panel&&JSON.stringify(panel.getBoundingClientRect());
                    const videos=[...pieceMemeSystem.media.values()].filter(n=>n.tagName==='VIDEO');
                    const clean=()=>{
                        assert(!document.querySelector('.piece-meme')&&!pieceMemeSystem.active.size,'overlay leak');
                        assert(!document.querySelector('.piece-meme-host'),'host class leak');
                        assert(videos.every(v=>v.paused&&!v.isConnected&&v.currentTime<.02),'video leak');
                    };
                    await playSequence();clean();const first=JSON.stringify(triggers);triggers.length=0;
                    await playSequence();clean();assert(JSON.stringify(triggers)===first,'replay changed attachment');
                    assert(!panel||JSON.stringify(panel.getBoundingClientRect())===rect,'panel moved');
                    assert(!panel||document.getElementById('memeVideo').parentElement===panel,'top panel modified');
                    // Inspect a paused video clock: seeking affects only its local playback.
                    const [key,config]=Object.entries(pieceMemeConfig.entries).find(([k,c])=>c.type==='video');
                    const actor=pieceBySquare.c6;
                    pieceMemeSystem.attach(actor,key,config);
                    const entry=[...pieceMemeSystem.active][0];entry.clock.pause();entry.clock.currentTime=400;
                    await new Promise(r=>setTimeout(r,180));
                    assert(entry.media.paused&&Math.abs(entry.media.currentTime-.4)<.05,'video did not follow seek');
                    entry.clock.currentTime=100;await new Promise(r=>setTimeout(r,180));
                    assert(Math.abs(entry.media.currentTime-.1)<.05,'video backward seek');
                    const done=entry.finished;resetPieces();await done;clean();
                }''')
                print('PASS:',mode,layout,'start/land, hierarchy, media seek, panel, replay and reset',flush=True)
            # Square selection resolves at the cue, then follows actor identity.
            scene=compile_sequence(chess.Board('4k2r/8/8/8/8/8/7Q/K7 w - - 0 1'),
                'Qh5+(pm:e8:HikaruLaugh,dur=20,shape=circle)'
                '(pm:h8:HikaruFace,dur=20,scale=.65,y=-5)'
                '(pm:h5:HikaruFace,when=land,dur=.15)'
                '(pm:a4:HikaruFace)(0.3s) Kd7(0s) Qxh8(0s)')
            load(scene,piece_meme_mode='on',meme_mode='off')
            page.evaluate('''async()=>{
                const assert=(v,m)=>{if(!v)throw Error(m);};
                for(let replay=0;replay<2;replay++){
                    resetPieces();
                    const king=pieceBySquare.e8,rook=pieceBySquare.h8,queen=pieceBySquare.h2;
                    const attached=[];const original=pieceMemeSystem.attach;
                    pieceMemeSystem.attach=function(actor,key,c){
                        original.call(this,actor,key,c);attached.push(actor);
                    };
                    await animateMove(scene.moves[0],{shot:'J',focus:null});
                    pieceMemeSystem.attach=original;
                    assert(attached.length===3&&attached.includes(king)&&attached.includes(rook)&&attached.includes(queen),'target lookup, destination or empty square');
                    assert(pieceMemeSystem.active.size===2,'individual duration did not expire');
                    const k=[...pieceMemeSystem.active].find(e=>e.actor===king);
                    const r=[...pieceMemeSystem.active].find(e=>e.actor===rook);
                    assert(k.layer.style.transform.includes('scale(0.48)')&&k.layer.style.transform.includes('-8px'),'king anchor');
                    assert(r.layer.style.transform.includes('scale(0.65)')&&r.layer.style.transform.includes('-5px'),'inline override');
                    assert(king.sprite.isConnected&&rook.sprite.isConnected,'sprite replaced');
                    await animateMove(scene.moves[1],{shot:'J',focus:null});
                    assert(pieceBySquare.d7===king&&k.layer.closest('.piece')===king,'lost king identity');
                    await animateMove(scene.moves[2],{shot:'J',focus:null});
                    assert(!r.layer.isConnected&&r.closed,'captured target overlay survived');
                    assert(k.layer.isConnected,'unrelated overlay removed');
                    resetPieces();assert(!pieceMemeSystem.active.size&&!document.querySelector('.piece-meme'),'reset leak');
                }
            }''')
            # Start selects the original occupant; land selects the incoming piece.
            scene=compile_sequence(chess.Board('4k3/8/8/8/8/8/7Q/K7 w - - 0 1'),
                'Qh5+(pm:h2:HikaruFace,when=start,dur=2)(pm:h5:HikaruLaugh,when=land,dur=.2)(0s)')
            load(scene,piece_meme_mode='on',meme_mode='off')
            page.evaluate('''async()=>{
                const actor=pieceBySquare.h2;let count=0;
                const attach=pieceMemeSystem.attach;
                pieceMemeSystem.attach=function(a,key,c){if(a!==actor)throw Error('cue selected wrong actor');count++;attach.call(this,a,key,c);};
                await playSequence();if(count!==2||pieceMemeSystem.active.size)throw Error('start/land replacement');
            }''')
            print('PASS: simultaneous square targets, independent expiry, anchors, overrides, movement, capture, empty squares, replay and cue occupancy',flush=True)
            # Long-lived overlay must not serialize moves, and dies with its victim.
            scene=compile_sequence(chess.Board('7k/8/3p4/8/4P3/8/8/K7 w - - 0 1'),
                                   'e5^N(piece:HikaruFace,when=start,dur=20)(0s) dxe5^N(0s)')
            load(scene,piece_meme_mode='on',meme_mode='off')
            page.evaluate('''async()=>{
                const assert=(v,m)=>{if(!v)throw Error(m);};let removed=false;
                const remove=pieceMemeSystem.removeActor;
                pieceMemeSystem.removeActor=function(actor){
                    if(this.active.size&&[...this.active].some(e=>e.actor===actor))removed=true;
                    return remove.call(this,actor);
                };
                const start=performance.now();await playSequence();
                assert(performance.now()-start<10000,'overlay stalled the next move');
                assert(removed&&!pieceMemeSystem.active.size,'captured overlay orphan');
            }''')
            print('PASS: later capture retires overlay without waiting for its lifetime',flush=True)
            scene=compile_sequence(chess.Board('7k/1P6/8/8/8/8/8/K7 w - - 0 1'),
                                   'b8=Q!!^VA(piece:HikaruFace,when=start,dur=4)(0s)')
            load(scene,piece_meme_mode='on',meme_mode='off')
            page.evaluate('''async()=>{
                let promotion=false;
                timelineScheduler.subscribe(e=>{if(e.cue==='holdStart') {
                    const actor=pieceBySquare.b8;
                    promotion=actor.sprite.src.endsWith('wQ.svg')&&actor.reaction.querySelector('.piece-meme')!==null;
                }});
                await playSequence();if(!promotion||pieceMemeSystem.active.size)throw Error('promotion/VA attachment failed');
                // Reset during actual movement cancels the session and its media.
                const run=playSequence().catch(e=>e.name);
                while(!pieceMemeSystem.active.size)await new Promise(requestAnimationFrame);
                resetPieces();await run;
                if(pieceMemeSystem.active.size||document.querySelector('.piece-meme'))throw Error('cancel leak');
            }''')
            print('PASS: promotion, VA camera and cancellation retain/clean correct actor',flush=True)
            # Off mode ignores unknown IDs and never loads piece media, while panel plays.
            scene=compile_sequence(chess.Board(),'Nf3(piece:Missing)')
            load(scene,piece_meme_mode='off',meme_path='../assets/memes/Cr7.mp4',meme_volume=0)
            page.evaluate('''async()=>{
                if(window.preparePieceMemes||pieceMemeSystem.media.size)throw Error('off preloaded media');
                await playSequence();
                if(document.querySelector('.piece-meme')||pieceMemeSystem.active.size)throw Error('off overlay');
                if(!document.getElementById('memeVideo')||!memeStarted)throw Error('off affected panel');
            }''')
            assert not errors,errors
            print('PASS: off mode has no piece media or overlays and panel remains independent',flush=True)
        finally:browser.close()

if __name__=='__main__':main()
