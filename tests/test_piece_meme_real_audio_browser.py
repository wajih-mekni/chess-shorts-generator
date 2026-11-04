"""Capture REAL Hikaru browser output after a click (no export/autoplay bypass)."""
from pathlib import Path
import os,sys,subprocess,tempfile,uuid,array,math,json
import chess
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from src.renderer.chess_state import compile_sequence
from src.renderer.composition import render_scene

def main():
    sink='piece_audio_test_'+uuid.uuid4().hex
    module=subprocess.check_output(['pactl','load-module','module-null-sink',f'sink_name={sink}'],text=True).strip()
    try:
        with tempfile.TemporaryDirectory() as folder,sync_playwright() as pw:
            browser=pw.chromium.launch(ignore_default_args=['--mute-audio'],
                args=['--autoplay-policy=document-user-activation-required'],env={**os.environ,'PULSE_SINK':sink})
            page=browser.new_page();warnings=[]
            page.on('console',lambda m:warnings.append(m.text) if m.type=='warning' else None)
            for audible in (True,False):
                scene=compile_sequence(chess.Board('4k2r/8/8/8/8/8/7Q/K7 w - - 0 1'),
                    'Qh5+^N@J(0s) Kd7^N@J(0s) Qh4^N@J(pm:d7:HikaruLaugh,hold=true,shape=circle,audio='+str(audible).lower()+')(4s)')
                html=render_scene(scene,piece_meme_mode='on',meme_mode='off',directing_profile='AUTO',
                    piece_memes={'HikaruLaugh':dict(src='assets/memes/hikaruLaughExecuseme.mp4',type='video')})
                path=Path(folder)/'scene.html';path.write_text(html.replace('../assets/',(ROOT/'assets').as_uri()+'/'))
                page.goto(path.as_uri());page.evaluate('''async()=>{
                    await preparePieceMemes();playMoveSound=()=>{};prepareMoveAudio=async()=>{};
                    window.realNode=[...pieceMemeSystem.media.values()][0];window.plays=[];
                    const play=realNode.play.bind(realNode);
                    realNode.play=()=>play().then(()=>plays.push('resolved'),e=>{plays.push(e.name);throw e;});
                }''')
                for replay in range(2 if audible else 1):
                    page.click('#playButton')
                    page.wait_for_function('pieceMemeSystem.active.size===1 && realNode.isConnected && realNode.currentTime>.1')
                    state=page.evaluate('''()=>({muted:realNode.muted,attribute:realNode.hasAttribute('muted'),
                        volume:realNode.volume,paused:realNode.paused,time:realNode.currentTime,
                        sameNode:[...pieceMemeSystem.active][0].media===realNode,plays})''')
                    assert state['muted']==(not audible) and state['attribute']==(not audible),state
                    assert state['volume']==1 and not state['paused'] and state['sameNode'],state
                    assert all(v=='resolved' for v in state['plays']),state
                    # Record actual device output while the browser event loop continues.
                    recorder=subprocess.Popen(['ffmpeg','-v','error','-f','pulse','-i',sink+'.monitor',
                        '-t','1.5','-ac','1','-ar','8000','-f','f32le','-'],stdout=subprocess.PIPE)
                    raw,_=recorder.communicate(timeout=10)
                    samples=array.array('f',raw);rms=math.sqrt(sum(v*v for v in samples)/len(samples))
                    assert rms>.003 if audible else rms<.00001,(audible,rms,state)
                    page.wait_for_function('hasPlayed&&!playing')
                    assert page.evaluate('realNode.paused&&realNode.muted&&realNode.currentTime===0')
                    print(json.dumps(dict(audio=audible,replay=replay,rms=rms,state=state)),flush=True)
            assert not warnings,warnings
            browser.close()
    finally:subprocess.run(['pactl','unload-module',module],check=True)
    print('PASS: real Hikaru audible in clicked preview and replay; audio=false silent; no export or autoplay bypass')
if __name__=='__main__':main()
