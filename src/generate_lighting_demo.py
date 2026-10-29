"""Stage 5 gallery: explicit treatment selection, production renderer throughout."""
from pathlib import Path
import json
import chess
try:
    from .generate_reaction_demo import position
    from .renderer.chess_state import compile_sequence
    from .renderer.composition import render_scene
except ImportError:
    from generate_reaction_demo import position
    from renderer.chess_state import compile_sequence
    from renderer.composition import render_scene


def examples():
    cases=[
        ('Ordinary · small local accent',chess.Board(),'e4@K(meme)','LIFT_MOVE','LOCAL_ACCENT','CYAN',.7),
        ('Cyan hero · checking capture',position({'a1':'K','f5':'k','c4':'R','f4':'b'}),'Rxf4+!!@L(meme)','ROOK_FLIP','HERO','CYAN',2.8),
        ('Green hero · queen spin',position({'a1':'K','h7':'k','b3':'Q'}),'Qe3!!@L(meme)','QUEEN_SPIN','HERO','GREEN',2.8),
        ('Red · checking capture',position({'a1':'K','f5':'k','c4':'R','f4':'b'}),'Rxf4+!@K(meme)','ROOK_FLIP','HERO','RED',1.2),
        ('Orange · tension treatment',position({'a1':'K','h7':'k','b2':'B'}),'Be5!?@K(meme)','BISHOP_SWEEP','HERO','ORANGE',2.8),
        ('Fragments · diagonal capture',position({'a1':'K','h7':'k','b2':'B','e5':'r'}),'Bxe5!@K(meme)','BISHOP_SPIN','TACTICAL_ACCENT','ORANGE',1),
        ('Arrival sparks · knight jump',chess.Board(),'Nf3!@K(meme)','KNIGHT_JUMP','TACTICAL_ACCENT','GREEN',1),
        ('Long hero hold · repeated pulses',position({'a1':'K','h7':'k','b3':'Q'}),'Qe3!!@L(meme)','QUEEN_SPIN','HERO','CYAN',5),
        ('Reference effects disabled · legacy palette',position({'a1':'K','f5':'k','c4':'R','f4':'b'}),'Rxf4+!!@L(meme)','ROOK_FLIP','HERO','CYAN',1),
    ]
    result=[]
    for label,board,token,choreo,preset,palette,pause in cases:
        scene=compile_sequence(board,token,pause)
        scene['moves'][0].update(choreography_preset=choreo,effect_preset=preset,effect_palette=palette)
        result.append((label,scene,'LEGACY' if label.startswith('Reference effects disabled') else 'REFERENCE'))
    return result


BRIDGE=r'''<style>body{display:block;margin:0;padding:0;min-height:0}.controls{display:none}</style><script>
window.lightingDemo={
 subscribe:fn=>timelineScheduler.subscribe(fn),
 count:()=>document.querySelectorAll('.light-primitive').length,
 settings:()=>{const m=timeline[0].move;return {preset:m.effect_preset,palette:m.effect_palette,pause:m.pause,profile:lightingConfig.profile};},
 play:(preset,palette,pause)=>{if(playing)return Promise.resolve();Object.assign(timeline[0].move,{effect_preset:preset,effect_palette:palette,pause});return playSequence();}
};</script>'''

HTML=r'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Lighting and particles · Stage 5</title><style>
*{box-sizing:border-box}body{margin:0;background:#121a22;color:#e5edf5;font:14px/1.5 system-ui}main{max-width:1450px;margin:auto;padding:24px}h1{font-size:26px;margin:0}h2{font-size:17px}p{color:#adbdca}.grid{display:grid;grid-template-columns:378px 1fr 320px;gap:24px;align-items:start}.preview{width:100%;aspect-ratio:9/16;position:relative;overflow:hidden;border-radius:12px}iframe{position:absolute;width:1080px;height:1920px;border:0;transform-origin:top left}button,select,input{background:#263744;color:#ebf7ff;border:1px solid #496070;border-radius:6px;font:inherit;padding:9px;margin:5px 0}select{width:100%}input{width:100px}button{cursor:pointer}button:disabled{opacity:.5}#play{background:#167c80}.box{background:#1b2934;padding:16px;border-radius:8px;margin-top:16px}#trace{white-space:pre-wrap;font:12px/1.6 monospace;max-height:210px;overflow:auto}#phase{font-size:24px;color:#79e9ed}video{width:100%;border-radius:10px}.small{font-size:12px}@media(max-width:1100px){.grid{grid-template-columns:340px 1fr}.reference{grid-column:2}}@media(max-width:650px){.grid{display:block}.preview,.reference{max-width:378px}}
</style><main><h1>Lighting and particles · Stage 5</h1><p>Neutral board, saturated accents, finite effects. Compare local treatments with animated hero holds.</p>
<div class="grid"><section><div class="preview"><iframe id="scene" title="Lighting scene"></iframe></div><button id="play">Play / Replay</button> <button id="reset">Reset scene</button><p class="small">Reset works during playback. The meme stays outside the chess effects.</p></section>
<section><h2>Scenario</h2><select id="cases" aria-label="Scenario"></select><h2>Treatment</h2><select id="preset" aria-label="Treatment"><option>LOCAL_ACCENT</option><option>TACTICAL_ACCENT</option><option>HERO</option><option>NONE</option></select><h2>Palette</h2><select id="palette" aria-label="Palette"><option>CYAN</option><option>GREEN</option><option>ORANGE</option><option>RED</option></select><label>Authored hold (seconds) <input id="hold" type="number" min="0" max="30" step=".1"></label><div class="box"><div id="phase">Ready</div><div id="count">Effects: 0</div><div id="profile"></div></div><div class="box" id="trace"></div><p class="small">Treatments and colors are explicitly selected here. A check or !! does not automatically select Stage 5 effects. Hero pulses recur about every 500 ms; the hold is authored, never silently extended.</p></section>
<section class="reference"><h2>Reference · independent playback</h2><video id="reference" controls muted playsinline preload="metadata"></video><p class="small" id="referenceStatus">Loading reference…</p><button data-time="28.2">Cyan hero</button><button data-time="40.5">Green hero</button><button data-time="9.6">Orange tension</button><button data-time="35.2">Capture</button><select id="rate" aria-label="Reference speed"><option value=".25">0.25× reference</option><option value=".5" selected>0.5× reference</option><option value="1">1× reference</option></select><p class="small">The existing analysis guides pulse/hold timing; strengths remain tunable. This stage adds no automatic tactical directing.</p></section></div></main><script>
const cases=__CASES__,frame=document.getElementById('scene'),chooser=document.getElementById('cases'),play=document.getElementById('play'),preset=document.getElementById('preset'),palette=document.getElementById('palette'),hold=document.getElementById('hold'),trace=document.getElementById('trace');let api=null,generation=0;
cases.forEach((c,i)=>chooser.add(new Option(c.label,i)));
new ResizeObserver(()=>frame.style.transform='scale('+frame.parentElement.clientWidth/1080+')').observe(frame.parentElement);
function load(){generation++;api=null;play.disabled=true;[chooser,preset,palette,hold].forEach(e=>e.disabled=false);trace.textContent='';document.getElementById('phase').textContent='Ready';frame.src=cases[Number(chooser.value)].file;}
frame.onload=()=>{api=frame.contentWindow.lightingDemo;if(!api)return;play.disabled=false;const s=api.settings();preset.value=s.preset;palette.value=s.palette;hold.value=s.pause;document.getElementById('profile').textContent=s.profile+' lighting profile';api.subscribe(e=>{document.getElementById('phase').textContent=e.cue;trace.textContent+=Math.round(e.elapsed)+' ms · '+e.cue+'\n';trace.scrollTop=trace.scrollHeight;});};
chooser.onchange=load;document.getElementById('reset').onclick=load;
play.onclick=async()=>{if(!api)return;const run=generation;play.disabled=true;[chooser,preset,palette,hold].forEach(e=>e.disabled=true);trace.textContent='';try{await api.play(preset.value,palette.value,Math.max(0,Math.min(30,Number(hold.value)||0)));}catch(e){if(run===generation)trace.textContent+='Error: '+e.message;}finally{if(run===generation){play.disabled=false;[chooser,preset,palette,hold].forEach(e=>e.disabled=false);}}};
function sample(){document.getElementById('count').textContent='Effects: '+(api?api.count():0);requestAnimationFrame(sample);}sample();
const reference=document.getElementById('reference');reference.playbackRate=.5;let url;
reference.onloadedmetadata=()=>reference.currentTime=28.2;reference.onseeked=()=>document.getElementById('referenceStatus').textContent=reference.currentTime.toFixed(3)+' s';
fetch('../assets/references/Reference.mp4').then(r=>{if(!r.ok)throw Error('Reference not found');return r.blob();}).then(blob=>{url=URL.createObjectURL(blob);reference.src=url;}).catch(e=>document.getElementById('referenceStatus').textContent=e.message);
window.addEventListener('unload',()=>{if(url)URL.revokeObjectURL(url);});document.querySelectorAll('[data-time]').forEach(b=>b.onclick=()=>{reference.pause();reference.currentTime=Number(b.dataset.time);});document.getElementById('rate').onchange=e=>reference.playbackRate=Number(e.target.value);load();
</script></html>'''


def generate():
    output=Path('output');output.mkdir(exist_ok=True);entries=[]
    for i,(label,scene,profile) in enumerate(examples()):
        name=f'lighting_case_{i:02d}.html'
        html=render_scene(scene,choreography_profile='REFERENCE',reaction_profile='REFERENCE',
                          lighting_profile=profile,meme_path='../assets/memes/MonkeyCry.mp4',
                          meme_volume=0,meme_comment_text='Fixed meme · starts at settled landing')
        (output/name).write_text(html.replace('</body>',BRIDGE+'</body>'),encoding='utf-8')
        entries.append(dict(label=label,file=name))
    (output/'lighting_demo.html').write_text(HTML.replace('__CASES__',json.dumps(entries)),encoding='utf-8')
    print('Created output/lighting_demo.html')
    print('Serve: python3 -m http.server 8000')
    print('Open http://localhost:8000/output/lighting_demo.html')

if __name__=='__main__':generate()
