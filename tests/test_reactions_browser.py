"""Real-browser reaction lifetime, transform ownership and media regressions.
Run: .venv/bin/python tests/test_reactions_browser.py
"""
from functools import partial
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
import sys,tempfile,threading
import chess
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.generate_reaction_demo import examples,position
from src.renderer.chess_state import compile_sequence
from src.renderer.composition import render_scene

class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self,*_):pass
    def copyfile(self,source,outputfile):
        try:super().copyfile(source,outputfile)
        except (BrokenPipeError,ConnectionResetError):pass


def expected_position(scene):
    board=chess.Board(None)
    for item in scene['pieces']:
        asset=item['asset'];symbol=asset[1] if asset[0]=='w' else asset[1].lower()
        board.set_piece_at(chess.parse_square(item['square']),chess.Piece.from_symbol(symbol))
    if scene['moves']:
        board.turn=scene['moves'][0]['piece_color']=='white'
    for move in scene['moves']:
        if move['en_passant']:board.ep_square=chess.parse_square(move['to'])
        promotion=chess.PIECE_SYMBOLS.index(move['promotion'][1].lower()) if move['promotion'] else None
        board.push(chess.Move(chess.parse_square(move['from']),chess.parse_square(move['to']),promotion))
    return {chess.square_name(sq):('w' if p.color else 'b')+p.symbol().upper()+'.svg' for sq,p in board.piece_map().items()}


def instrument(page):
    page.evaluate('''()=>{
      window.records=[];
      timelineScheduler.subscribe(e=>records.push({cue:e.cue,time:performance.now(),to:e.move.to,
        cameraActive:Boolean(camera.animation||cameraMotion.tracks.size)}));
      const sound=playMoveSound;playMoveSound=function(m){records.push({cue:'sound',time:performance.now()});return sound(m);};
      const meme=startMemeVideo;startMemeVideo=function(){const started=memeStarted;const r=meme();if(!started&&memeStarted)records.push({cue:'meme',time:performance.now()});return r;};
    }''')


def assert_final(page,expected):
    page.evaluate('''async expected=>{
      const assert=(ok,msg)=>{if(!ok)throw Error(msg);};
      await reactionSystem.finished;
      assert(reactionSystem.ghosts.size===0 && reactionSystem.sessions.size===0 && reactionSystem.tracks.size===0,'reaction ownership leaked');
      assert(timelineScheduler.active.size===0,'schedule leaked');
      const actors=[...board.querySelectorAll('.piece')];
      assert(actors.length===Object.keys(expected).length,'ghost or missing actor');
      assert(Object.keys(pieceBySquare).length===actors.length,'occupancy differs from visual actors');
      for(const [square,asset] of Object.entries(expected)){
        const actor=pieceBySquare[square];const coords=squareToCoords(square);
        assert(actor && actor.sprite.src.endsWith(asset),'incorrect chess state on '+square);
        assert(actor.style.left===coords.x*squareSize+'px' && actor.style.top===coords.y*squareSize+'px','incorrect coordinates');
        assert(getComputedStyle(actor.reaction).transform==='none','king/reaction did not return to neutral');
        assert(getComputedStyle(actor.reaction).opacity==='1','reaction opacity leaked');
        assert(getComputedStyle(actor.choreography).transform==='none','choreography changed');
      }
      assert(document.querySelector('.board-area').getAnimations({subtree:true}).length===0,'animation outlived playback');
    }''',expected)


def playback(page,expected,legacy=False):
    page.evaluate('''async legacy=>{
      records.length=0;
      const fixed=JSON.stringify(document.querySelector('.reaction-area').getBoundingClientRect().toJSON());
      const move=timeline[0].move;
      await playSequence();
      const cue=name=>records.find(e=>e.cue===name)?.time;
      const assert=(ok,msg)=>{if(!ok)throw Error(msg);};
      assert(Math.abs(cue('sound')-cue('settled'))<35,'sound moved off settled landing');
      if(move.start_meme)assert(Math.abs(cue('meme')-cue('settled'))<35,'meme moved off settled landing');
      if(legacy){assert(!cue('captureReaction')&&!cue('kingAnticipation'),'legacy gained reactions');}
      else {
        if(move.capture){assert(cue('captureReaction')<cue('settled'),'victim reaction did not overlap approach');}
        if(move.check){
          assert(cue('kingAnticipation')<cue('kingRecovery'),'king recovery order');
          if(move.rook_to)assert(cue('settled')<cue('kingAnticipation'),'checking castle reacted before rook approach');
          else assert(cue('kingAnticipation')<cue('settled'),'king anticipation happened after landing');
          assert(cue('kingRecovery')>=cue('settled'),'king recovered before attacker settlement');
        }
      }
      assert(JSON.stringify(document.querySelector('.reaction-area').getBoundingClientRect().toJSON())===fixed,'meme moved');
    }''',legacy)
    assert_final(page,expected)


def inspect_lifetime(page,expected):
    page.evaluate('''async()=>{
      const assert=(ok,msg)=>{if(!ok)throw Error(msg);};
      const delay=ms=>new Promise(r=>setTimeout(r,ms));
      const frames=()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)));
      const move=timeline[0].move, victim=pieceBySquare[move.capture], king=pieceBySquare[move.checked_king];
      const kingPosition=[king.style.left,king.style.top];
      const original=animatePieceMove;let info;
      animatePieceMove=function(m,onLand,onMotion,...rest){return original(m,onLand,value=>{
        info=value;value.animations.forEach(a=>{a.pause();a.currentTime=0;});onMotion(value);
      },...rest);};
      const run=playSequence();
      while(!info)await frames();
      assert(!pieceBySquare[move.capture],'victim retained logical occupancy');
      assert(reactionSystem.ghosts.has(victim)&&victim.isConnected,'victim removed at launch');
      assert(victim.dataset.visualOnly==='true','victim not marked visual-only');
      assert(Number(victim.style.zIndex)>Number(info.animation.effect.target.style.zIndex),'victim exit hidden behind attacker');
      await delay(220);
      assert(!records.some(e=>e.cue==='captureReaction'||e.cue==='kingAnticipation'),'wall clock triggered paused reactions');
      // Advance the actual attacker clock just beyond both reaction thresholds.
      const ms=info.duration*info.contactOffset-100;
      info.animations.forEach(a=>a.currentTime=ms);
      await frames();
      assert(records.some(e=>e.cue==='captureReaction')&&records.some(e=>e.cue==='kingAnticipation'),'missing anticipation cues');
      assert(victim.reaction.getAnimations().length===1,'victim missing reaction track');
      const exit=victim.reaction.getAnimations()[0];exit.pause();exit.currentTime=100;
      const pose=new DOMMatrix(getComputedStyle(victim.reaction).transform);
      assert(Math.hypot(pose.a,pose.b)<1,'victim not shrinking');
      assert(getComputedStyle(victim).transform==='none'&&getComputedStyle(victim.choreography).transform==='none','victim reaction owns wrong transform');
      const windup=king.reaction.getAnimations()[0];if(windup)windup.finish();
      await delay(20);
      const kingPose=new DOMMatrix(getComputedStyle(king.reaction).transform);
      assert(Math.hypot(kingPose.a,kingPose.b)>1,'king not enlarged');
      assert(Math.abs(kingPose.b)>0,'king not tilted');
      assert(king.style.left===kingPosition[0]&&king.style.top===kingPosition[1],'king logical position moved');
      exit.play();info.animations.forEach(a=>a.finish());await run;
      animatePieceMove=original;
    }''')
    assert_final(page,expected)


def cancelled_replay(page,expected):
    page.evaluate('''async()=>{
      const assert=(ok,msg)=>{if(!ok)throw Error(msg);};
      const frame=()=>new Promise(requestAnimationFrame);
      let aborted;const run=playSequence().catch(e=>aborted=e.name);
      while(![...reactionSystem.sessions].some(s=>s.captureStarted&&s.kingStarted))await frame();
      const actor=[...renderedPieces].find(p=>p.choreography.getAnimations().length);
      assert(actor,'missing moving actor');actor.choreography.getAnimations()[0].cancel();
      await run;await reactionSystem.finished;
      assert(aborted==='AbortError','cancel did not stop playback');
      assert(!reactionSystem.ghosts.size&&!reactionSystem.sessions.size,'cancel retained ghosts/session');
      const king=pieceBySquare[timeline[0].move.checked_king];
      assert(getComputedStyle(king.reaction).transform==='none','cancel left king tilted');
      await playSequence();
    }''')
    assert_final(page,expected)


def reset_and_overrides(page,expected):
    page.evaluate('''async()=>{
      const assert=(ok,msg)=>{if(!ok)throw Error(msg);};
      let aborted;const run=playSequence().catch(e=>aborted=e.name);
      while(![...reactionSystem.sessions].some(s=>s.captureStarted&&s.kingStarted))await new Promise(requestAnimationFrame);
      resetPieces();await run;await reactionSystem.finished;
      assert(aborted==='AbortError','reset failed to cancel moving actor');
      assert(!reactionSystem.ghosts.size&&!reactionSystem.sessions.size,'reset retained reaction owners');
      assert(renderedPieces.size===initialPieces.length,'reset left old actors');
      for(const p of initialPieces){
        const actor=pieceBySquare[p.square];
        assert(actor&&actor.sprite.src.endsWith(p.asset),'reset lost initial occupant');
        assert(!actor.getAnimations({subtree:true}).length,'reset retained animation');
      }
      const move=timeline[0].move;
      move.capture_reaction='NONE';move.king_reaction='NONE';records.length=0;
      await playSequence();
      assert(!records.some(e=>e.cue==='captureReaction'||e.cue==='kingAnticipation'),'NONE override ignored');
      delete move.capture_reaction;delete move.king_reaction;
      // Instant legacy travel misses the RAF anticipation window. Settlement
      // must still launch and join exits/recovery, even with no reading pause.
      move.choreography_preset='LEGACY';move.pause=0;
      motion.presets[motion.defaultPreset].duration=0;
      records.length=0;await playSequence();
      assert(records.some(e=>e.cue==='captureReaction')&&records.some(e=>e.cue==='kingRecovery'),'instant move lost reaction fallback');
    }''')
    assert_final(page,expected)


def main():
    server=ThreadingHTTPServer(('127.0.0.1',0),partial(QuietHandler,directory=str(ROOT)))
    threading.Thread(target=server.serve_forever,daemon=True).start()
    try:
      with tempfile.TemporaryDirectory(prefix='reactions-',dir=ROOT/'output') as folder,sync_playwright() as pw:
        work=Path(folder);cases=examples()
        discovered=compile_sequence(position({'a1':'K','e8':'k','e1':'R','e2':'B'}),'Bf3+@J(meme)',0)
        discovered['moves'][0]['choreography_preset']='BISHOP_SWEEP'
        cases.append(('Discovered check',discovered,'REFERENCE'))
        mate=compile_sequence(chess.Board(),'f3 e5 g4 Qh4#',0)
        cases.append(('Mate still recovers king',mate,'REFERENCE'))
        for i,(_,scene,profile) in enumerate(cases):
            html=render_scene(scene,reaction_profile=profile,choreography_profile='REFERENCE',meme_path='../assets/memes/MonkeyCry.mp4')
            (work/f'case{i}.html').write_text(html.replace('../assets/','../../assets/'))
        browser=pw.chromium.launch(headless=True)
        try:
          page=browser.new_page(viewport={'width':1080,'height':1920});errors=[]
          page.on('pageerror',lambda e:errors.append(str(e)))
          base=f'http://127.0.0.1:{server.server_port}/output/{work.name}'
          for i,(label,scene,profile) in enumerate(cases[:-1]):
            page.goto(base+f'/case{i}.html');instrument(page)
            playback(page,expected_position(scene),profile=='LEGACY')
            if i==2:
                assert page.evaluate("records.find(e=>e.cue==='captureReaction').cameraActive"),'camera and victim reaction did not overlap'
          print('PASS: capture directions/presets, checks/checking captures, en passant, promotion, checking castle, discovered check, legacy and exact final states.',flush=True)
          page.goto(base+'/case7.html');instrument(page)
          inspect_lifetime(page,expected_position(cases[7][1]))
          cancelled_replay(page,expected_position(cases[7][1]))
          reset_and_overrides(page,expected_position(cases[7][1]))
          print('PASS: visual-only victim lifetime, actual animation-clock anticipation, independent transforms, king recovery, cancellation and replay.',flush=True)
          page.goto(base+f'/case{len(cases)-1}.html')
          page.evaluate('playSequence()');assert_final(page,expected_position(mate))
          assert not errors,errors
          print('PASS: checkmate preserves/recover king; no browser errors.',flush=True)
        finally:browser.close()
    finally:server.shutdown();server.server_close()

if __name__=='__main__':main()
