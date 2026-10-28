"""Generate camera_demo.html first, then run this real-browser regression test."""
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]


def main():
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True)
        page=browser.new_page(viewport={'width':1080,'height':1920})
        errors=[]
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto((ROOT/'output/camera_demo.html').as_uri())
        page.evaluate('''async () => {
            const assert=(ok,msg)=>{if(!ok) throw Error(msg);};
            for(const shot of ['K','L']) for(const square of ['d5','f3','a1','h8']) {
                const pose=camera_focus_destination(square,shot);
                const r=destination_region(square,shot);
                const angle=pose.rotation*Math.PI/180;
                for(const x of [r.left,r.right]) for(const y of [r.top,r.bottom]) {
                    const px=pose.x+pose.zoom*(x*Math.cos(angle)-y*Math.sin(angle));
                    const py=pose.y+pose.zoom*(x*Math.sin(angle)+y*Math.cos(angle));
                    assert(Math.max(Math.abs(px),Math.abs(py))<=cameraConfig.viewportSize/2+0.001,'cropped neighborhood');
                }
                assert(JSON.stringify(pose)===JSON.stringify(camera_frame_move('a1',square,shot)),'source affects shot');
                assert(JSON.stringify(pose)===JSON.stringify(camera_frame_move('h8',square,shot)),'distance affects shot');
            }
            assert(camera_focus_destination('d5','L').zoom>3,'close too weak');
            assert(camera_focus_destination('d5','K').zoom>2,'medium too weak');
            const close=camera_focus_destination('d5','L');
            const angle=close.rotation*Math.PI/180;
            const source={x:(3.5-4)*squareSize,y:(7.5-4)*squareSize};
            assert(Math.abs(close.y+close.zoom*(source.x*Math.sin(angle)+source.y*Math.cos(angle)))>
                cameraConfig.viewportSize/2,'long queen source should be offscreen');
            window.timing={};
            const direct=camera.directMove;
            camera.directMove=async function(move) {
                const task=direct.call(this,move);
                const expected=move.camera_directive==='J'?cameraConfig.wideDuration:cameraConfig.shots[move.camera_directive].duration;
                assert(this.animation.effect.getTiming().duration===expected,'wrong shot duration');
                await task; timing.ready=performance.now();
            };
            const pieceMove=animatePieceMove;
            animatePieceMove=async function(...args) {
                timing.start=performance.now();
                return pieceMove(...args);
            };
            const effects=showMoveEffects;
            showMoveEffects=function(move) {effects(move);timing.effects=performance.now();};
            window.observations=[];
            const original=animateMove;
            animateMove=async function(move) {
                const before=getComputedStyle(board).transform;
                const fixed=document.querySelector('.reaction-area').getBoundingClientRect().toJSON();
                timing.ready=performance.now();
                await original(move);
                const elapsed=performance.now()-timing.effects;
                if(move.annotation==='!!') {
                    assert(timing.start-timing.ready>=cameraConfig.brilliantPreHold-10,'missing pre-hold');
                    assert(elapsed>=move.pause*1000+cameraConfig.brilliantPostHold-10,'missing post-hold');
                } else {
                    assert(timing.start-timing.ready<cameraConfig.brilliantPreHold,'normal move delayed');
                }
                const after=getComputedStyle(board).transform;
                if(!move.camera_directive) assert(before===after,'unmarked move changed camera');
                if(move.camera_directive==='J') assert(new DOMMatrix(after).isIdentity,'J not wide');
                assert(JSON.stringify(fixed)===JSON.stringify(document.querySelector('.reaction-area').getBoundingClientRect().toJSON()),'meme moved');
                observations.push({directive:move.camera_directive,before,after});
            };
        }''')
        for _ in range(2):
            page.click('#playButton')
            page.wait_for_function('hasPlayed && !playing',timeout=60000)
        assert page.evaluate('observations.length')==16
        assert not errors,errors
        browser.close()
        print('PASS: directive persistence, destination bounds, source independence, transition speeds, brilliant holds, absolute targets, close shot, fixed meme, J reset and replay.')


if __name__=='__main__': main()
