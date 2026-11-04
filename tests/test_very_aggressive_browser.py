"""Real accumulated rotations, spin coverage, seek/replay/reset and landing integration."""
from pathlib import Path
import sys
import tempfile
import chess
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.renderer.chess_state import compile_sequence
from src.renderer.composition import render_scene


def main():
    with tempfile.TemporaryDirectory() as folder, sync_playwright() as pw:
        browser=pw.chromium.launch()
        try:
            page=browser.new_page(viewport={'width':1080,'height':1920})
            errors=[]
            page.on('pageerror',lambda e:errors.append(str(e)))
            for mode,layout in [('fixed','safe'),('off','safe'),('off','crop')]:
                scene=compile_sequence(chess.Board('8/8/8/5k2/2R2b2/8/8/K7 w - - 0 1'),'Rxf4+!!^VA@L(0s)')
                html=render_scene(scene,directing_profile='AUTO',meme_mode=mode,layout_mode=layout)
                path=Path(folder)/'scene.html'
                path.write_text(html.replace('../assets/',(ROOT/'assets').as_uri()+'/'))
                page.goto(path.as_uri())
                page.wait_for_function('[...document.images].every(i=>i.complete && i.naturalWidth>0)')
                page.evaluate(r'''async () => {
                    const assert=(v,m)=>{if(!v)throw Error(m);};
                    prepareMoveAudio=async()=>{};playMoveSound=()=>{};
                    const config=directingConfig.veryAggressive, move=scene.moves[0];
                    const total=config.spinDuration-config.spinOverlap+config.duration;
                    const frames=cameraMotion.veryAggressiveFrames(move,config);
                    const owner=cameraMotion.owners.aggressive;
                    const matrix=()=>getComputedStyle(owner).transform;
                    const pose=JSON.stringify(camera.pose);
                    for(const shot of ['J','K','L']) for(const square of ['a1','a8','h1','h8']) {
                        await camera.directMove({...move,to:square,camera_directive:shot},cameraConfig.aggressiveMargin);
                        for(const name of ['reframe','impact','hero']) {
                            const c=cameraConfig.transient[name],s=name==='impact'?config.impactStrength:1;
                            cameraMotion.owners[name].style.transform=cameraMotion.frame(0,c.translation*s,c.translation*s,1+c.zoom*s,c.rotation*s).transform;
                        }
                        const done=cameraMotion.aggressiveHit(move,config);
                        const track=cameraMotion.tracks.get('aggressive');track.animation.pause();
                        const inset=parseFloat(getComputedStyle(owner,'::before').left),size=owner.offsetWidth;
                        const markers=[[inset,inset],[size-inset,inset],[size-inset,size-inset],[inset,size-inset]].map(([x,y])=>{
                            const e=document.createElement('i');Object.assign(e.style,{position:'absolute',left:x+'px',top:y+'px',width:'0',height:'0'});owner.appendChild(e);return e;
                        });
                        const viewport=document.querySelector('.board-area').getBoundingClientRect();
                        let previous=0,unwrapped=0,maxScale=0;
                        // Include interpolation between authored frames, all 45° crossings,
                        // and all angles of both turns, rather than only spin endpoints.
                        for(let time=0;time<=total;time+=2) {
                            track.animation.currentTime=time;
                            const m=new DOMMatrix(matrix()),angle=Math.atan2(m.b,m.a)*180/Math.PI;
                            let delta=angle-previous;while(delta>180)delta-=360;while(delta< -180)delta+=360;
                            unwrapped+=delta;previous=angle;maxScale=Math.max(maxScale,Math.hypot(m.a,m.b));
                            const poly=markers.map(e=>e.getBoundingClientRect());
                            for(const [x,y] of [[viewport.left,viewport.top],[viewport.right,viewport.top],[viewport.right,viewport.bottom],[viewport.left,viewport.bottom]]) {
                                const signs=poly.map((a,j)=>{const b=poly[(j+1)%4];return (b.x-a.x)*(y-a.y)-(b.y-a.y)*(x-a.x);});
                                assert(signs.every(v=>v>=-.1)||signs.every(v=>v<=.1),'spin exposed a corner: '+shot+square);
                            }
                        }
                        assert(Math.abs(unwrapped-720)<.1,'browser did not perform two full turns: '+unwrapped);
                        assert(maxScale>2,'zoom punch missing');
                        track.animation.currentTime=245;const first=matrix();
                        track.animation.currentTime=850;track.animation.currentTime=245;
                        assert(matrix()===first,'backward seek changed pose');
                        // Final explicit 720° is visually identity, then cleanup writes exact 0°.
                        track.animation.currentTime=total;
                        const last=new DOMMatrix(matrix());
                        assert(Math.abs(last.a-1)<1e-8&&Math.abs(last.b)<1e-8&&last.e===0&&last.f===0,'final pose not identity');
                        markers.forEach(e=>e.remove());cameraMotion.reset();await done;
                    }
                    camera.reset();assert(JSON.stringify(camera.pose)===pose,'persistent pose polluted');
                    const clean=()=>{
                        assert(!cameraMotion.tracks.size,'camera track leak');
                        for(const e of Object.values(cameraMotion.owners)) {
                            assert(new DOMMatrix(getComputedStyle(e).transform).isIdentity,'transform residue');
                            assert(!e.getAnimations().length,'animation residue');
                        }
                        assert(!document.querySelector('.aggressive-active'),'backing remained active');
                        assert(!lightingSystem.sessions.size&&!lightingSystem.tracks.size&&!document.querySelector('.light-primitive'),'lighting leak');
                        assert(!reactionSystem.sessions.size&&!reactionSystem.ghosts.size,'reaction leak');
                        assert(!timelineScheduler.active.size,'scheduler leak');
                    };
                    let landed=false;const log=[];const effects=[];
                    const play=cameraMotion.play;
                    cameraMotion.play=function(name,frames,duration) {
                        if(name==='aggressive') {assert(landed,'spin before landing');log.push(JSON.stringify({frames,duration}));}
                        return play.call(this,name,frames,duration);
                    };
                    const animate=LightingSession.prototype.animate;
                    LightingSession.prototype.animate=function(node,frames,duration,delay,iterations) {
                        effects.push(JSON.stringify({primitive:node.dataset.primitive,frames,duration,delay,iterations}));
                        return animate.call(this,node,frames,duration,delay,iterations);
                    };
                    timelineScheduler.subscribe(e=>{if(e.cue==='settled')landed=true;});
                    const meme=document.querySelector('.reaction-area');
                    const memeRect=meme&&JSON.stringify(meme.getBoundingClientRect());
                    await playSequence();clean();assert(log.length===1,'more than one spin at landing');
                    assert(pieceBySquare.f4&&!pieceBySquare.c4,'capture placement wrong');
                    const firstEffects=JSON.stringify(effects);effects.length=0;landed=false;
                    await playSequence();clean();assert(log.length===2&&log[0]===log[1],'replay spin differs');
                    assert(JSON.stringify(effects)===firstEffects,'lighting replay differs');
                    assert(!meme||JSON.stringify(meme.getBoundingClientRect())===memeRect,'meme moved');
                    // Reset while actively spinning and while rocking; stale completions
                    // cannot erase a replacement track or leave a residual whole turn.
                    for(const time of [200,800]) {
                        const old=cameraMotion.aggressiveHit(move,config);
                        cameraMotion.tracks.get('aggressive').animation.currentTime=time;
                        const replacement=cameraMotion.aggressiveHit(move,config);
                        await old;assert(cameraMotion.tracks.has('aggressive'),'old completion erased replacement');
                        camera.reset();await replacement;clean();
                        const next=cameraMotion.aggressiveHit(move,config);
                        cameraMotion.tracks.get('aggressive').animation.currentTime=time;
                        resetPieces();await next;clean();
                    }
                }''')
                print('PASS:',mode,layout,'720° browser rotation, zoom, interpolated coverage, seeking, landing, replay and reset',flush=True)
            assert not errors,errors
        finally:
            browser.close()


if __name__=='__main__':
    main()
