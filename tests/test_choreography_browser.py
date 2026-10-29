"""Real-browser Stage 3 contracts; no generated demo prerequisites.
Run: .venv/bin/python tests/test_choreography_browser.py
"""
from functools import partial
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
import sys,tempfile,threading
import chess
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.generate_choreography_demo import CASES,demo_scene
from src.renderer.composition import render_scene
from src.renderer.chess_state import compile_sequence

class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self,*_): pass


def write_scene(path,scene):
    html=render_scene(scene,choreography_profile='REFERENCE',meme_path='../assets/memes/MonkeyCry.mp4')
    path.write_text(html.replace('../assets/','../../assets/'))


def check_recipe(page):
    page.evaluate('''async()=>{
      const assert=(ok,msg)=>{if(!ok)throw Error(msg);};
      const move=timeline[0].move, spec=resolvePieceMotion(move);
      if(spec.kind==='legacy')return;
      const piece=pieceBySquare[move.from], reaction=piece.reaction;
      const cameraTask=camera.directMove(move);
      const cameraAnimation=camera.animation;
      cameraAnimation.pause();cameraAnimation.currentTime=cameraConfig.shots.K.duration*.5;
      const cameraTransform=getComputedStyle(board).transform;
      let landed=0, info;
      const task=animatePieceMove(move,()=>landed++,value=>info=value);
      assert(info.animations.length===2,'missing separate travel/deformation tracks');
      const [travel,deformation]=info.animations;
      info.animations.forEach(a=>a.pause());
      assert(travel.effect.target===piece && deformation.effect.target===piece.choreography,'wrong transform owners');
      assert(!travel.effect.getKeyframes().some(f=>'transform' in f),'travel owns deformation transform');
      assert(!deformation.effect.getKeyframes().some(f=>'left' in f || 'top' in f),'deformation owns travel coordinates');
      const seek=t=>{info.animations.forEach(a=>a.currentTime=t);return {
        pose:getComputedStyle(piece.choreography).transform,
        x:getComputedStyle(piece).left,y:getComputedStyle(piece).top};};
      const p=spec.preset;
      if(p.kind==='spin'){
        const a=seek(p.launch+10),b=seek(p.launch+p.hang-10);
        assert(a.pose===b.pose && a.x===b.x && a.y===b.y,'inverted hang is not held');
        const inverted=new DOMMatrix(b.pose);
        assert(inverted.a < -1 && inverted.d < -1 && Math.abs(inverted.b)<.001,'sprite not inverted at hang');
        const finish=seek(p.launch+p.hang+p.finish*.7);
        assert(finish.pose!==b.pose,'spin did not accelerate out of hang');
      }else{
        seek(p.duration*p.peakAt);
        const m=new DOMMatrix(getComputedStyle(piece.choreography).transform);
        assert(Math.hypot(m.a,m.b)>1.05,'missing lift scale');
        assert(m.f!==0 || m.e!==0,'missing lift/sweep displacement');
      }
      assert(getComputedStyle(piece).transform==='none','new travel deforms outer piece');
      assert(getComputedStyle(reaction).transform==='none','reserved reaction owner was modified');
      assert(getComputedStyle(board).transform===cameraTransform,'piece motion changed camera owner');
      assert(!landed,'landed before tracks finished');
      travel.finish();await Promise.resolve();await Promise.resolve();
      assert(!landed,'travel completion ignored deformation settling');
      deformation.finish();await task;
      assert(landed===1,'landing count changed');
      const to=squareToCoords(move.to);
      assert(piece.style.left===to.x*squareSize+'px' && piece.style.top===to.y*squareSize+'px','wrong final square');
      assert(pieceBySquare[move.to]===piece,'logical actor not committed');
      for(const owner of [piece,piece.choreography,reaction]){
        assert(getComputedStyle(owner).transform==='none','residual rotation/scale');
        assert(owner.getAnimations().length===0,'piece track leaked');
      }
      cameraAnimation.finish();await cameraTask;
      // Cancel either track while inverted/mid-flight: both must be removed.
      for(const index of [0,1]){
        resetPieces();const actor=pieceBySquare[move.from];let current;
        const cancelled=animatePieceMove(move,()=>{throw Error('cancel landed');},value=>current=value)
          .then(()=>null,error=>error.name);
        current.animations.forEach(a=>{a.pause();a.currentTime=p.duration*.4;});
        current.animations[index].cancel();
        assert(await cancelled==='AbortError','cancel did not propagate');
        assert(actor.getAnimations({subtree:true}).length===0,'sibling track survived cancellation');
        assert(pieceBySquare[move.from]===actor,'cancel lost actor ownership');
        assert(getComputedStyle(actor.choreography).transform==='none','cancel left deformation');
      }
      resetPieces();camera.reset();cameraMotion.reset();
    }''')


def check_playback(page):
    page.evaluate('''async()=>{
      const assert=(ok,msg)=>{if(!ok)throw Error(msg);};
      const records=[];const unsubscribe=timelineScheduler.subscribe(e=>records.push({cue:e.cue,time:e.time}));
      const sound=playMoveSound, meme=startMemeVideo;
      playMoveSound=function(m){records.push({cue:'sound',time:performance.now()});return sound(m);};
      startMemeVideo=function(){const before=memeStarted;const result=meme();if(!before&&memeStarted)records.push({cue:'meme',time:performance.now()});return result;};
      const fixed=JSON.stringify(document.querySelector('.reaction-area').getBoundingClientRect().toJSON());
      for(let replay=0;replay<2;replay++){
        records.length=0;await playSequence();
        const cue=name=>records.find(e=>e.cue===name)?.time;
        assert(cue('launch')<cue('cameraEnd') && cue('cameraEnd')<cue('settled'),'camera/piece no longer overlap');
        assert(cue('contact')<cue('settled'),'recipe arrival marker lost');
        assert(Math.abs(cue('sound')-cue('settled'))<30,'sound moved from settled boundary');
        assert(Math.abs(cue('meme')-cue('settled'))<30,'meme moved from settled boundary');
        assert(records.filter(e=>e.cue==='settled').length===1,'duplicate landing');
        assert(board.querySelectorAll('.piece').length===initialPieces.length,'replay ghost actor');
        assert(document.querySelector('.board-area').getAnimations({subtree:true}).length===0,'playback left active tracks');
        assert(JSON.stringify(document.querySelector('.reaction-area').getBoundingClientRect().toJSON())===fixed,'meme moved');
      }
      unsubscribe();
      // Cancel through full playback, then replay. No ghosts or late landings.
      let aborted;
      const pending=playSequence().catch(e=>aborted=e.name);
      let actor;
      do {await new Promise(requestAnimationFrame);actor=[...renderedPieces].find(p=>p.choreography.getAnimations().length);}while(!actor);
      actor.choreography.getAnimations()[0].cancel();await pending;
      assert(aborted==='AbortError','choreography cancellation not propagated to sequence');
      await playSequence();
      assert(board.querySelectorAll('.piece').length===initialPieces.length,'cancel/replay retained actor');
      assert(timelineScheduler.active.size===0 && cameraMotion.tracks.size===0,'cancel/replay leaked tracks');
    }''')


def check_special(page,expected):
    page.evaluate('''async expected=>{
      const assert=(ok,msg)=>{if(!ok)throw Error(msg);};
      await playSequence();
      for(const [square,asset] of Object.entries(expected)){
        assert(pieceBySquare[square]?.sprite.src.endsWith(asset),'special move final asset/square: '+square);
      }
      for(const actor of Object.values(pieceBySquare)){
        assert(getComputedStyle(actor.choreography).transform==='none','special move deformation remains');
        assert(actor.getAnimations({subtree:true}).length===0,'special move track remains');
      }
    }''',expected)


def main():
    server=ThreadingHTTPServer(('127.0.0.1',0),partial(QuietHandler,directory=str(ROOT)))
    threading.Thread(target=server.serve_forever,daemon=True).start()
    try:
      with tempfile.TemporaryDirectory(prefix='choreography-',dir=ROOT/'output') as folder,sync_playwright() as pw:
        work=Path(folder)
        for i,(_,kind,uci,black,preset) in enumerate(CASES):
            write_scene(work/f'case{i}.html',demo_scene(kind,uci,black,preset))
        scene=demo_scene(chess.ROOK,'d4f4',False,'ROOK_FLIP')
        scene['moves'][0]['start_meme']=True
        write_scene(work/'timing.html',scene)
        scene=compile_sequence(chess.Board('4k3/8/8/3p4/4P3/8/p7/3QK2R w K - 0 1'),'O-O a1=Q exd5 Qa7+ Kh1',0)
        for move in scene['moves']:move['choreography_preset']='LIFT_MOVE'
        write_scene(work/'special.html',scene)
        scene=compile_sequence(chess.Board(),'e4 a6 e5 d5 exd6',0)
        write_scene(work/'ep.html',scene)
        browser=pw.chromium.launch(headless=True)
        try:
          page=browser.new_page(viewport={'width':1080,'height':1920});errors=[]
          page.on('pageerror',lambda error:errors.append(str(error)))
          base=f'http://127.0.0.1:{server.server_port}/output/{work.name}'
          for i,case in enumerate(CASES):
            page.goto(base+f'/case{i}.html');check_recipe(page)
          print('PASS: all recipes/colors/directions, inversion hold, transform separation, exact coordinates and cancellation.',flush=True)
          page.goto(base+'/timing.html');check_playback(page)
          print('PASS: actual camera overlap, settled sound/meme, replay and sequence cancellation.',flush=True)
          page.goto(base+'/special.html');check_special(page,{'h1':'wK.svg','f1':'wR.svg','a7':'bQ.svg','d5':'wP.svg'})
          page.goto(base+'/ep.html');check_special(page,{'d6':'wP.svg'})
          assert not page.evaluate("Boolean(pieceBySquare.d5)"),'en passant victim survived'
          assert not errors,errors
          print('PASS: castling, promotion, capture and en passant with layered pieces.',flush=True)
        finally:browser.close()
    finally:server.shutdown();server.server_close()

if __name__=='__main__':main()
