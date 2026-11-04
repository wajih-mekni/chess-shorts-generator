"""Close destination shot -> wide view while the same VA spin continues."""
from pathlib import Path
import tempfile
import sys
import chess
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.renderer.chess_state import compile_sequence
from src.renderer.composition import render_scene


def main():
    with tempfile.TemporaryDirectory() as folder,sync_playwright() as pw:
        browser=pw.chromium.launch()
        try:
            page=browser.new_page(viewport={'width':1080,'height':1920})
            errors=[]
            page.on('pageerror',lambda e:errors.append(str(e)))
            for mode,layout in [('fixed','safe'),('off','safe'),('off','crop')]:
                scene=compile_sequence(chess.Board(),'Nf3!!^VA@L(0s) Nf6^N(0s)')
                html=render_scene(scene,directing_profile='AUTO',meme_mode=mode,layout_mode=layout)
                path=Path(folder)/'scene.html'
                path.write_text(html.replace('../assets/',(ROOT/'assets').as_uri()+'/'))
                page.goto(path.as_uri())
                page.wait_for_function('[...document.images].every(i=>i.complete && i.naturalWidth>0)')
                page.evaluate('''async () => {
                    const assert=(v,m)=>{if(!v)throw Error(m);};
                    prepareMoveAudio=async()=>{};playMoveSound=()=>{};
                    const config=directingConfig.veryAggressive,move=buildMovePlan(scene.moves[0]).move;
                    const matrix=()=>new DOMMatrix(getComputedStyle(board).transform);
                    const same=(a,b)=>['a','b','c','d','e','f'].every(k=>Math.abs(a[k]-b[k])<1e-5);
                    const wide=new DOMMatrix(camera.transform(camera.identity));
                    for(const at of [.25,.5,.75]) {
                        await camera.directMove(move,cameraConfig.aggressiveMargin);
                        const close=matrix();assert(!same(close,wide),'initial shot was wide');
                        assert(Math.hypot(close.e,close.f)>10,'initial zoom did not target the piece');
                        const done=cameraMotion.aggressiveHit(move,{...config,spinReturnWideAt:at});
                        const spin=cameraMotion.tracks.get('aggressive').animation,pan=camera.animation;
                        assert(spin.startTime===pan.startTime,'different animation clocks');
                        spin.pause();pan.pause();
                        const seek=t=>{spin.currentTime=t;pan.currentTime=t;};
                        seek(config.spinZoomDuration*at);assert(same(matrix(),close),'left piece before configured return');
                        seek(config.spinZoomDuration*(at+1)/2);
                        assert(!same(matrix(),close)&&!same(matrix(),wide),'return did not interpolate');
                        const middle=matrix();seek(0);seek(config.spinZoomDuration*(at+1)/2);
                        assert(same(matrix(),middle),'backward seek changed return');
                        seek(config.spinZoomDuration);assert(same(matrix(),wide),'not wide by spin end');
                        assert(spin.playState!=='finished','spin/rocking stopped during return');
                        cameraMotion.reset();await done;
                        assert(!camera.animation&&!cameraMotion.tracks.size,'reset leaked return');
                        assert(same(matrix(),wide),'return left a camera transform');
                    }
                    await camera.directMove(move,cameraConfig.aggressiveMargin);
                    const close=matrix();
                    const disabled=cameraMotion.aggressiveHit(move,{...config,spinReturnWide:false});
                    assert(!camera.animation,'disabled option created return');
                    cameraMotion.reset();await disabled;assert(same(matrix(),close),'disabled option changed shot');
                    camera.reset();
                    const logs=[];
                    timelineScheduler.subscribe(e=>{
                        if(e.cue==='complete'&&e.move.brilliant_mode==='very_aggressive')
                            logs.push(JSON.stringify({pose:camera.pose,next:e.plan.nextContext}));
                    });
                    await playSequence();await playSequence();
                    assert(logs.length===2&&logs[0]===logs[1],'replay differs');
                    const log=JSON.parse(logs[0]);
                    assert(JSON.stringify(log.pose)===JSON.stringify(camera.identity),'did not finish wide');
                    assert(log.next.shot==='J'&&log.next.focus===null,'director context stayed close');
                    assert(!camera.animation&&!cameraMotion.tracks.size&&!board.getAnimations().length,'animation leak');
                    assert(!document.querySelector('.light-primitive')&&!timelineScheduler.active.size,'session leak');
                }''')
                print('PASS:',mode,layout,'piece focus, timed wide return, seeking, disabled option, reset and replay',flush=True)
            assert not errors,errors
        finally:browser.close()

if __name__=='__main__':main()
