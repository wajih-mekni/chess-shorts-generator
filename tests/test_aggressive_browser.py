"""Real-browser aggressive rotation, overscan, integration and replay checks."""
from pathlib import Path
import sys
import tempfile
import chess
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.renderer.chess_state import compile_sequence
from src.renderer.composition import render_scene


def main():
    with tempfile.TemporaryDirectory() as folder, sync_playwright() as pw:
        browser = pw.chromium.launch()
        try:
            page = browser.new_page(viewport={'width':1080,'height':1920})
            errors = []
            page.on('pageerror', lambda e: errors.append(str(e)))
            for mode, layout in [('fixed','safe'), ('off','safe'), ('off','crop')]:
                for amplitude in (12,20):
                    # Capture + check exercises retained victims and king reactions too.
                    scene = compile_sequence(chess.Board('8/8/8/5k2/2R2b2/8/8/K7 w - - 0 1'),
                                             'Rxf4+!!^A@L(0s)')
                    html = render_scene(scene, directing_profile='AUTO', meme_mode=mode, layout_mode=layout,
                                        aggressive_config={'rotation':amplitude})
                    path = Path(folder)/'scene.html'
                    path.write_text(html.replace('../assets/', (ROOT/'assets').as_uri()+'/'))
                    page.goto(path.as_uri())
                    page.wait_for_function('[...document.images].every(i=>i.complete && i.naturalWidth>0)')
                    page.evaluate('''() => {
                        // Keep real piece/timeline/lighting code; media decoding is unrelated.
                        prepareMoveAudio=async()=>{};playMoveSound=()=>{};
                        window.frameLog=[];
                        const play=cameraMotion.play;
                        cameraMotion.play=function(name,frames,duration) {
                            if(name==='aggressive')frameLog.push(JSON.stringify(frames));
                            return play.call(this,name,frames,duration);
                        };
                    }''')
                    result = page.evaluate('''async () => {
                        const assert=(v,m)=>{if(!v)throw Error(m);};
                        const move=scene.moves[0],config=directingConfig.aggressive;
                        const frames=cameraMotion.aggressiveFrames(move,config);
                        const rotations=frames.map(f=>Number(f.transform.match(/rotate\\(([-+.0-9eE]+)deg/)[1]));
                        assert(Math.max(...rotations)>config.rotation*.97,'positive large rotation');
                        assert(Math.min(...rotations)<-config.rotation*.7,'negative large rotation');
                        assert(frames[0].transform===cameraMotion.identity && frames.at(-1).transform===cameraMotion.identity,'identity endpoints');
                        const base=JSON.stringify(camera.pose);
                        // Every shot, board corner and sampled rock pose must retain backing.
                        for(const shot of ['J','K','L']) for(const square of ['a1','a8','h1','h8']) {
                            const m={...move,to:square,camera_directive:shot};
                            await camera.directMove(m,cameraConfig.aggressiveMargin);
                            for(const name of ['reframe','impact','hero']) {
                                const t=cameraConfig.transient[name], strength=name==='impact'?config.impactStrength:1;
                                cameraMotion.owners[name].style.transform=cameraMotion.frame(0,t.translation*strength,t.translation*strength,1+t.zoom*strength,t.rotation*strength).transform;
                            }
                            let region;
                            if(shot!=='J') {
                                const r=destination_region(square,shot);region=document.createElement('div');
                                Object.assign(region.style,{position:'absolute',left:(r.left+540)+'px',top:(r.top+540)+'px',width:(r.right-r.left)+'px',height:(r.bottom-r.top)+'px'});
                                board.appendChild(region);
                            }
                            const done=cameraMotion.aggressiveHit(m,config);
                            const track=cameraMotion.tracks.get('aggressive');
                            track.animation.pause();
                            const owner=cameraMotion.owners.aggressive;
                            const backing=getComputedStyle(owner,'::before');
                            assert(backing.content!=='none','overscan missing');
                            const inset=parseFloat(backing.left),size=owner.offsetWidth;
                            const markers=[[inset,inset],[size-inset,inset],[size-inset,size-inset],[inset,size-inset]].map(([x,y])=>{
                                const e=document.createElement('i');Object.assign(e.style,{position:'absolute',left:x+'px',top:y+'px',width:'0',height:'0'});owner.appendChild(e);return e;
                            });
                            const viewport=document.querySelector('.board-area').getBoundingClientRect();
                            for(let i=0;i<frames.length;i++) {
                                track.animation.currentTime=i/(frames.length-1)*config.duration;
                                if(region) {
                                    const r=region.getBoundingClientRect();
                                    assert(r.left>=viewport.left-.1 && r.right<=viewport.right+.1 && r.top>=viewport.top-.1 && r.bottom<=viewport.bottom+.1,'focused region clipped: '+shot+square);
                                }
                                const poly=markers.map(e=>e.getBoundingClientRect());
                                for(const [x,y] of [[viewport.left,viewport.top],[viewport.right,viewport.top],[viewport.right,viewport.bottom],[viewport.left,viewport.bottom]]) {
                                    const cross=poly.map((a,j)=>{const b=poly[(j+1)%4];return (b.x-a.x)*(y-a.y)-(b.y-a.y)*(x-a.x);});
                                    assert(cross.every(v=>v>=-.1)||cross.every(v=>v<=.1),'exposed viewport corner');
                                }
                            }
                            region?.remove();markers.forEach(e=>e.remove());cameraMotion.reset();await done;
                        }
                        camera.reset();cameraMotion.reset();
                        assert(JSON.stringify(camera.pose)===base,'persistent camera changed');
                        const residue=()=>{
                            assert(!cameraMotion.tracks.size,'camera track leak');
                            for(const owner of Object.values(cameraMotion.owners)) {
                                assert(new DOMMatrix(getComputedStyle(owner).transform).isIdentity,'transform residue');
                                assert(!owner.getAnimations().length,'animation residue');
                            }
                            assert(!document.querySelector('.aggressive-active'),'backing residue');
                            assert(!lightingSystem.sessions.size && !lightingSystem.tracks.size && !document.querySelector('.light-primitive'),'light leak');
                            assert(!reactionSystem.ghosts.size && !reactionSystem.sessions.size,'reaction leak');
                            assert(!timelineScheduler.active.size,'schedule leak');
                        };
                        frameLog.length=0;
                        const meme=document.querySelector('.reaction-area');
                        const memeRect=meme && JSON.stringify(meme.getBoundingClientRect());
                        await playSequence();residue();
                        const first=frameLog[0];assert(frameLog.length===1,'one contact hit');
                        assert(pieceBySquare.f4?.dataset.square==='f4' || pieceBySquare.f4,'final actor missing');
                        await playSequence();residue();assert(frameLog.length===2 && frameLog[1]===first,'replay differs');
                        assert(!meme || JSON.stringify(meme.getBoundingClientRect())===memeRect,'meme moved');
                        // Cancellation and replacement must not clear a newer track.
                        const old=cameraMotion.aggressiveHit(move,config);
                        const next=cameraMotion.aggressiveHit(move,config);
                        await old;assert(cameraMotion.tracks.has('aggressive'),'predecessor erased replacement');
                        camera.reset();await next;residue();
                        const pending=cameraMotion.aggressiveHit(move,config);
                        resetPieces();await pending;residue();
                        return {amplitude:config.rotation, frames:frames.length};
                    }''')
                    print('PASS:', mode, layout, result, 'overscan, playback, replay and reset', flush=True)
            assert not errors, errors
        finally:
            browser.close()


if __name__ == '__main__':
    main()
