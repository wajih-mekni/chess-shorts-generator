"""Stage 6 end-to-end: legal sequences, override integration and animation cleanup."""
from functools import partial
from http.server import ThreadingHTTPServer
from pathlib import Path
import sys,tempfile,threading
import chess
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from playwright.sync_api import sync_playwright
from test_directing import DEMO_SEQUENCE
from src.generate_reaction_demo import position
from src.renderer.chess_state import compile_sequence
from src.renderer.composition import render_scene
from test_reactions_browser import QuietHandler,expected_position,assert_final,instrument


def setup(page):
    instrument(page)
    page.evaluate('''()=>{
      window.plans=[];window.effectLog=[];
      timelineScheduler.subscribe(e=>{if(e.cue==='launch')plans.push({tier:e.plan.tier,choreography:e.plan.choreography,
        camera:e.move.camera_directive,palette:e.plan.lighting?.palette,hold:e.plan.holdDuration,
        overlap:Boolean(camera.animation),hero:e.plan.hero,impact:e.plan.impactStrength});});
      const animate=LightingSession.prototype.animate;
      LightingSession.prototype.animate=function(node,frames,duration,delay,iterations){
        effectLog.push({type:node.dataset.primitive,frames,duration,delay,iterations,style:node.getAttribute('style')});
        return animate.call(this,node,frames,duration,delay,iterations);
      };
    }''')


def playback(page,scene):
    page.evaluate('''async()=>{
      records.length=0;plans.length=0;effectLog.length=0;
      const before=JSON.stringify(scene),fixed=JSON.stringify(document.querySelector('.reaction-area').getBoundingClientRect().toJSON());
      await playSequence();
      const assert=(v,m)=>{if(!v)throw Error(m);};
      const landings=records.filter(e=>e.cue==='settled'),sounds=records.filter(e=>e.cue==='sound');
      assert(landings.length===moves.length&&sounds.length===moves.length,'one landing/sound per move');
      for(let i=0;i<sounds.length;i++)assert(Math.abs(sounds[i].time-landings[i].time)<35,'landing sound shifted');
      const trigger=moves.findIndex(m=>m.start_meme);
      if(trigger>=0)assert(Math.abs(records.find(e=>e.cue==='meme').time-landings[trigger].time)<35,'meme shifted');
      assert(JSON.stringify(scene)===before,'logical input mutated');
      assert(JSON.stringify(document.querySelector('.reaction-area').getBoundingClientRect().toJSON())===fixed,'meme moved');
      await lightingSystem.finished;
      assert(!lightingSystem.sessions.size&&!lightingSystem.tracks.size&&!document.querySelector('.light-primitive'),'effect leak');
    }''')
    assert_final(page,expected_position(scene))


def main():
    main_scene=compile_sequence(chess.Board(),DEMO_SEQUENCE)
    cases=[('main',main_scene)]
    alternate=compile_sequence(chess.Board('r4rk1/1b1R3p/p1p1p3/Pp2Bp1q/nb2nQ2/7P/1P3PP1/6K1 w - - 0 1'),'Qg3!!~queen-spin(meme)')
    cases.append(('alternate',alternate))
    cases.append(('castle',compile_sequence(position({'e1':'K','h1':'R','f8':'k'},castle=True),'O-O+@J(meme)')))
    cases.append(('ep',compile_sequence(position({'a1':'K','h8':'k','e5':'P','d5':'p'},ep='d6'),'exd6(meme)')))
    cases.append(('promotion',compile_sequence(position({'c1':'K','h7':'k','b7':'P','a8':'r'}),'bxa8=Q(meme)')))
    capture=compile_sequence(position({'a1':'K','f5':'k','c4':'R','f4':'b'}),'Rxf4+!!@L(meme)')
    cases.append(('capture',capture))
    override=compile_sequence(chess.Board(),'Nf3!!~lift@J(0s)(meme)')
    override['moves'][0].update(effect_preset='NONE',king_reaction='NONE',capture_reaction='NONE')
    cases.append(('override',override))
    black=compile_sequence(position({'a8':'k','h2':'K','f5':'r','d5':'B'},turn=chess.BLACK),'Rxd5!~flip(meme)')
    cases.append(('black',black))
    server=ThreadingHTTPServer(('127.0.0.1',0),partial(QuietHandler,directory=str(ROOT)))
    threading.Thread(target=server.serve_forever,daemon=True).start()
    try:
      with tempfile.TemporaryDirectory(prefix='directing-',dir=ROOT/'output') as folder,sync_playwright() as pw:
        work=Path(folder)
        for name,scene in cases:
            html=render_scene(scene,directing_profile='AUTO',meme_path='../assets/memes/MonkeyCry.mp4',meme_volume=0)
            (work/f'{name}.html').write_text(html.replace('../assets/','../../assets/'))
        browser=pw.chromium.launch(headless=True)
        try:
          page=browser.new_page(viewport={'width':1080,'height':1920});errors=[]
          page.on('pageerror',lambda e:errors.append(str(e)))
          base=f'http://127.0.0.1:{server.server_port}/output/{work.name}'
          for name,scene in cases:
            page.goto(base+'/'+name+'.html');setup(page);playback(page,scene)
            plans=page.evaluate('plans')
            if name=='main':
                assert {p['tier'] for p in plans}=={'NORMAL','TACTICAL','HERO'}
                assert plans[2]['choreography']=='KNIGHT_JUMP' and plans[4]['choreography']=='BISHOP_SWEEP'
                assert plans[10]['camera']=='L' and plans[10]['hero'] and plans[10]['hold']==2980
                assert plans[10]['overlap'] and plans[12]['impact']==.25
                assert plans[-1]['camera']=='J'
                first=page.evaluate('JSON.stringify(effectLog)');firstplans=page.evaluate('JSON.stringify(plans.map(({overlap,...rest})=>rest))')
                playback(page,scene)
                assert page.evaluate('JSON.stringify(effectLog)')==first,'particle replay changed'
                assert page.evaluate('JSON.stringify(plans.map(({overlap,...rest})=>rest))')==firstplans,'directing context accumulated'
            if name=='override':
                assert plans[0]['choreography']=='LIFT_MOVE' and plans[0]['camera']=='J' and plans[0]['hold']==180
                assert page.evaluate('effectLog.length')==0
            if name=='castle':
                assert page.evaluate("records.find(e=>e.cue==='kingAnticipation').time>records.find(e=>e.cue==='settled').time")
            print('PASS: AUTO '+name+' placement, reactions, media and cleanup.',flush=True)
          page.goto(base+'/capture.html');setup(page)
          page.evaluate('''async()=>{
            let error;const run=playSequence().catch(e=>error=e.name);
            while(!reactionSystem.ghosts.size||!document.querySelector('[data-primitive="CAPTURE_FRAGMENTS"]'))await new Promise(requestAnimationFrame);
            resetPieces();await run;await lightingSystem.finished;await reactionSystem.finished;
            if(error!=='AbortError'||reactionSystem.ghosts.size||document.querySelector('.light-primitive'))throw Error('AUTO reset leaked actors/effects');
          }''')
          playback(page,capture)
          assert not errors,errors
          print('PASS: automatic directing cancellation/reset and replay; no browser errors.',flush=True)
        finally:browser.close()
    finally:server.shutdown();server.server_close()

if __name__=='__main__':main()
