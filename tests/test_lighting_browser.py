"""Production Chromium: Stage 5 determinism, ownership, lifetime and compatibility."""
from functools import partial
from http.server import ThreadingHTTPServer
from pathlib import Path
import sys,threading
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from playwright.sync_api import sync_playwright
from src.generate_lighting_demo import generate,examples
from test_reactions_browser import QuietHandler,expected_position,assert_final,instrument


def instrument_lighting(page):
    instrument(page)
    page.evaluate('''()=>{
      window.effectLog=[];
      const original=LightingSession.prototype.animate;
      LightingSession.prototype.animate=function(node,frames,duration,delay=0,iterations=1){
        effectLog.push({class:node.className,primitive:node.dataset.primitive,style:node.getAttribute('style'),frames,duration,delay,iterations});
        return original.call(this,node,frames,duration,delay,iterations);
      };
    }''')


def finished(page,scene):
    assert_final(page,expected_position(scene))
    page.evaluate('''async()=>{
      await lightingSystem.finished;
      if(lightingSystem.sessions.size||lightingSystem.tracks.size||document.querySelector('.light-primitive'))throw Error('lighting leak');
      if(timelineScheduler.active.size)throw Error('schedule leak');
      if(timelineScheduler.listeners.size!==1)throw Error('debug listener leaked');
    }''')


def playback(page,scene,disabled=False):
    page.evaluate('''async disabled=>{
      const assert=(v,m)=>{if(!v)throw Error(m);};
      effectLog.length=0;records.length=0;
      const meme=document.querySelector('.reaction-area');const box=JSON.stringify(meme.getBoundingClientRect().toJSON());
      await playSequence();
      const at=c=>records.find(e=>e.cue===c)?.time;
      assert(Math.abs(at('sound')-at('settled'))<35,'sound timing changed');
      assert(Math.abs(at('meme')-at('settled'))<35,'meme timing changed');
      assert(JSON.stringify(meme.getBoundingClientRect().toJSON())===box,'meme moved');
      assert(!meme.querySelector('.light-primitive')&&!meme.closest('.lighting-layer'),'meme tinted');
      if(disabled){assert(!effectLog.length,'disabled profile animated effects');assert(!lightingSystem.layers.over,'disabled profile created effect layers');}
      else assert(effectLog.length,'enabled profile missing effects');
    }''',disabled)
    finished(page,scene)


def probe_hero(page,scene):
    page.evaluate('''async()=>{
      const assert=(v,m)=>{if(!v)throw Error(m);};
      let hold,overlap=false;const entered=new Promise(r=>hold=r);
      const unsub=timelineScheduler.subscribe(e=>{
        if(e.cue==='captureReaction')overlap=Boolean(camera.animation||cameraMotion.tracks.size)&&
          [...renderedPieces].some(p=>p.choreography.getAnimations().length)&&
          Boolean(document.querySelector('[data-primitive="CAPTURE_FRAGMENTS"]'));
        if(e.cue==='holdStart')hold();
      });
      const run=playSequence();await entered;
      assert(overlap,'capture fragments/camera/choreography did not overlap');
      assert(lightingSystem.layers.under.parentNode===board&&lightingSystem.layers.over.parentNode===board,'local effects lost camera');
      assert(lightingSystem.layers.viewport.parentNode===document.querySelector('.board-area'),'viewport wash follows camera');
      assert(getComputedStyle(document.querySelector('.board-area')).overflow==='hidden','effects not clipped');
      const bloom=document.querySelector('[data-primitive="HERO_BLOOM"]');
      const ring=document.querySelector('[data-primitive="BADGE_RING"]');
      const wash=document.querySelector('[data-primitive="BOARD_WASH"]');
      assert(bloom&&ring&&wash,'missing hero primitives');
      const animations=[...lightingSystem.sessions].flatMap(s=>[...s.animations]);
      assert(animations.every(a=>a.effect.target.classList.contains('light-primitive')),'effect wrote another transform owner');
      animations.forEach(a=>a.pause());
      const sample=t=>{animations.forEach(a=>a.currentTime=t);return {
        bloom:getComputedStyle(bloom).opacity,wash:getComputedStyle(wash).opacity,
        ring:getComputedStyle(ring).transform};};
      const a=sample(500),b=sample(750),c=sample(1000);
      assert(a.bloom!==b.bloom&&a.wash!==b.wash,'hero hold frozen');
      assert(Math.abs(Number(a.bloom)-Number(c.bloom))<.00001,'pulse is not reproducible at 500 ms period');
      assert(a.ring!==b.ring,'ring does not pulse');
      // Sample both export cadences on the same finite timeline. Transforms are
      // functions of time, not frame number; the shared samples must agree.
      for(const fps of [30,60])for(let i=0;i<=fps;i++)sample(i*1000/fps);
      assert(JSON.stringify(sample(750))===JSON.stringify(b),'cadence changed the effect state');
      const late=[...document.querySelectorAll('[data-primitive="AMBIENT_DUST"]')].some(n=>n.getAnimations()[0].effect.getComputedTiming().endTime>=2900);
      assert(late,'particles stop before the long hold');
      animations.forEach(a=>a.play());await run;unsub();
    }''')
    finished(page,scene)


def cancellation(page,scene):
    page.evaluate('''async()=>{
      let aborted;const run=playSequence().catch(e=>aborted=e.name);
      while(!document.querySelector('[data-primitive="CAPTURE_FRAGMENTS"]'))await new Promise(requestAnimationFrame);
      resetPieces();await run;await lightingSystem.finished;await reactionSystem.finished;
      if(aborted!=='AbortError')throw Error('active reset failed to cancel travel');
      if(document.querySelector('.light-primitive')||reactionSystem.ghosts.size)throw Error('reset leaked effects/ghosts');
      if(renderedPieces.size!==initialPieces.length)throw Error('reset lost pieces');
      await playSequence();
    }''')
    finished(page,scene)


def hold_reset_and_failure(page,scene):
    page.evaluate('''async()=>{
      const assert=(v,m)=>{if(!v)throw Error(m);};
      const run=playSequence();
      while(!document.querySelector('[data-primitive="HERO_BLOOM"]'))await new Promise(requestAnimationFrame);
      resetPieces();await run;await lightingSystem.finished;
      assert(!document.querySelector('.light-primitive'),'hold reset leaked effects');
      assert(!lightingSystem.sessions.size&&!lightingSystem.tracks.size,'hold reset leaked ownership');
      const original=LightingSession.prototype.emit;
      LightingSession.prototype.emit=function(name,...args){
        if(name==='CAPTURE_FRAGMENTS')throw Error('test effect failure');
        return original.call(this,name,...args);
      };
      let error;try{await playSequence();}catch(e){error=e.message;}
      await lightingSystem.finished;
      assert(error==='test effect failure','RAF cue failure did not propagate through schedule');
      assert(!document.querySelector('.light-primitive')&&!lightingSystem.sessions.size,'failure leaked effects');
      LightingSession.prototype.emit=original;
      await playSequence();
    }''')
    finished(page,scene)


def main():
    generate();cases=examples()
    server=ThreadingHTTPServer(('127.0.0.1',0),partial(QuietHandler,directory=str(ROOT)))
    threading.Thread(target=server.serve_forever,daemon=True).start()
    try:
      with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True)
        try:
          page=browser.new_page(viewport={'width':1080,'height':1920});errors=[]
          page.on('pageerror',lambda e:errors.append(str(e)))
          page.on('console',lambda e:errors.append(e.text) if e.type=='warning' and 'Cue observer failed' in e.text else None)
          base=f'http://127.0.0.1:{server.server_port}/output'
          for i,(_,scene,profile) in enumerate(cases):
            page.goto(base+f'/lighting_case_{i:02d}.html');instrument_lighting(page)
            playback(page,scene,profile=='LEGACY')
          print('PASS: all palettes/presets, exact final states, legacy disabled, media timing and cleanup.',flush=True)
          scene=cases[1][1];page.goto(base+'/lighting_case_01.html');instrument_lighting(page)
          probe_hero(page,scene)
          page.evaluate('effectLog.length=0; playSequence()');first=page.evaluate('JSON.stringify(effectLog)')
          page.evaluate('effectLog.length=0; playSequence()');second=page.evaluate('JSON.stringify(effectLog)')
          assert first==second,'replay changed seeded geometry/timing'
          finished(page,scene);cancellation(page,scene)
          hold_reset_and_failure(page,scene)
          page.evaluate("timeline[0].move.pause=0; playSequence()")
          finished(page,scene)
          assert not errors,errors
          print('PASS: deterministic replay, 30/60 Hz time sampling, animated hero holds, camera/choreography/reaction overlap, clipping, cancellation/reset and zero-pause tails.',flush=True)
        finally:browser.close()
    finally:server.shutdown();server.server_close()

if __name__=='__main__':main()
