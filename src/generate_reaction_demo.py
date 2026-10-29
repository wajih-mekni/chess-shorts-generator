"""Stage 4 browser gallery: legal captures/checks, metadata defaults and overrides."""
from pathlib import Path
import json
import chess
try:
    from .renderer.chess_state import compile_sequence
    from .renderer.composition import render_scene
    from .renderer.reactions import reaction_config
except ImportError:
    from renderer.chess_state import compile_sequence
    from renderer.composition import render_scene
    from renderer.reactions import reaction_config


def position(pieces, turn=chess.WHITE, *, ep=None, castle=False):
    board=chess.Board(None)
    for square,symbol in pieces.items():
        board.set_piece_at(chess.parse_square(square),chess.Piece.from_symbol(symbol))
    board.turn=turn
    if ep:board.ep_square=chess.parse_square(ep)
    if castle:board.castling_rights=chess.BB_H1
    return board


def examples():
    basic={'a1':'K','h7':'k','d4':'R','f4':'b'}
    cases=[
        ('Ordinary capture · right / tumble',position(basic),'d4f4','ROOK_FLIP',{}),
        ('Capture · left / black',position({'a1':'K','h7':'k','f4':'R','d4':'b'}).mirror(),'f5d5','ROOK_FLIP',{}),
        ('Capture · upward',position({'a1':'K','h7':'k','d2':'R','d4':'n'}),'d2d4','LIFT_MOVE',{}),
        ('Capture · downward',position({'a1':'K','h7':'k','d6':'R','d4':'n'}),'d6d4','LIFT_MOVE',{}),
        ('Shrink override',position(basic),'d4f4','ROOK_FLIP',{'capture_reaction':'CAPTURE_SHRINK'}),
        ('Bishop sweep / knockback override',position({'a1':'K','h7':'k','b2':'B','d4':'r'}),'b2d4','BISHOP_SWEEP',{'capture_reaction':'CAPTURE_KNOCKBACK'}),
        ('Queen check · king anticipation',position({'a1':'K','g5':'k','c4':'Q'}),'c4g4','QUEEN_SPIN',{}),
        ('Checking capture · both reactions',position({'a1':'K','f5':'k','c4':'R','f4':'b'}),'c4f4','ROOK_FLIP',{}),
        ('En passant · victim off destination',position({'a1':'K','h8':'k','e5':'P','d5':'p'},ep='d6'),'e5d6','LIFT_MOVE',{}),
        ('Capture promotion',position({'c1':'K','h7':'k','b7':'P','a8':'r'}),'b7a8q','LIFT_MOVE',{}),
        ('Checking castle · react to rook',position({'e1':'K','h1':'R','f8':'k'},castle=True),'e1g1','LIFT_MOVE',{'rook_choreography_preset':'ROOK_FLIP'}),
        ('Legacy capture · immediate removal',position(basic),'d4f4','LEGACY',{}),
    ]
    result=[]
    for label,board,uci,choreography,overrides in cases:
        move=chess.Move.from_uci(uci)
        assert board.is_valid() and move in board.legal_moves,(label,board.fen(),uci)
        camera='J' if board.is_castling(move) else 'K'
        scene=compile_sequence(board,board.san(move)+'!@'+camera+'(meme)',.6)
        scene['moves'][0].update(choreography_preset=choreography,**overrides)
        result.append((label,scene,'LEGACY' if label.startswith('Legacy') else 'REFERENCE'))
    return result


HTML=r'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Reactions · Stage 4</title><style>
*{box-sizing:border-box}body{margin:0;background:#14181e;color:#e6edf3;font:14px/1.5 system-ui}
main{max-width:1440px;margin:auto;padding:24px}h1{font-size:26px;margin:0 0 8px}h2{font-size:17px}p{color:#b3bfcc}
.grid{display:grid;grid-template-columns:minmax(270px,378px) 1fr 320px;gap:24px;align-items:start}
.preview{position:relative;width:100%;aspect-ratio:9/16;overflow:hidden;border-radius:12px;background:#222}
iframe{position:absolute;left:0;top:0;width:1080px;height:1920px;border:0;transform-origin:top left}
button,select{font:inherit;background:#27323e;color:#eef7ff;border:1px solid #546575;border-radius:6px;padding:9px;margin:4px 0;max-width:100%}
button{cursor:pointer}button:disabled{opacity:.5}select{width:100%}#play{background:#238076}
.box{background:#1d252e;border:1px solid #35414e;border-radius:8px;padding:14px;margin:14px 0}#status{font-size:22px;color:#8ee3d5}
#trace{max-height:230px;overflow:auto;font:12px/1.6 monospace;white-space:pre-wrap}video{width:100%;border-radius:10px;background:#000}.small{font-size:12px}
@media(max-width:1000px){.grid{grid-template-columns:minmax(270px,378px) 1fr}.reference{grid-column:2}}
@media(max-width:650px){.grid{display:block}.preview,.reference{max-width:378px}}
</style><main><h1>Reactions and impact cues · Stage 4</h1><p>Victims stay visible during approach. Kings anticipate and recover. Choreography and camera continue independently.</p>
<div class="grid"><section><div class="preview" id="preview"><iframe id="scene" title="Reaction scene"></iframe></div>
<button id="play">Play / Replay</button> <button id="reset">Reset scene</button>
<p class="small">Reset is available during playback. The reaction video starts at the attacker's settled landing.</p></section>
<section><h2>Choose a legal scenario</h2><select id="cases" aria-label="Scenario"></select>
<h2>Optional capture override</h2><select id="capture" aria-label="Capture override"><option value="DEFAULT">Scenario / metadata default</option><option>CAPTURE_SHRINK</option><option>CAPTURE_TUMBLE</option><option>CAPTURE_KNOCKBACK</option><option>NONE</option></select>
<h2>Optional king override</h2><select id="king" aria-label="King override"><option value="DEFAULT">Scenario / metadata default</option><option>KING_RECOIL</option><option>NONE</option></select>
<div class="box"><div id="status">Ready</div><div id="actors">Visual victims: 0</div><div id="metadata"></div></div>
<div class="box" id="trace"></div><p class="small">The reference profile binds capture/check metadata to basic presets. Overrides are optional. No Stage 6 tactical directing, lights or particles.</p></section>
<section class="reference"><h2>Reference · independent playback</h2><video id="reference" controls muted playsinline preload="metadata"></video>
<p id="referenceStatus" class="small">Loading reference…</p><button data-time="35.2">Shrink · 35.20 s</button><button data-time="39.2">Tumble · 39.20 s</button><button data-time="26.15">King · 26.15 s</button>
<select id="rate" aria-label="Reference speed"><option value=".25">0.25× reference</option><option value=".5" selected>0.5× reference</option><option value="1">1× reference</option></select>
<p class="small">Reference victims retire in roughly 200 ms. Their reactions overlap attacker approach; the king enlarges/tilts and returns upright.</p></section></div></main>
<script>
const cases=__CASES__,frame=document.getElementById('scene'),chooser=document.getElementById('cases'),play=document.getElementById('play'),trace=document.getElementById('trace');
const capture=document.getElementById('capture'),king=document.getElementById('king');let api=null,generation=0;
cases.forEach((item,i)=>chooser.add(new Option(item.label,i)));
const resize=()=>frame.style.transform='scale('+document.getElementById('preview').clientWidth/1080+')';new ResizeObserver(resize).observe(document.getElementById('preview'));resize();
function load(){generation++;api=null;play.disabled=true;chooser.disabled=false;capture.disabled=false;king.disabled=false;trace.textContent='';document.getElementById('status').textContent='Ready';frame.src=cases[Number(chooser.value)].file;}
chooser.onchange=()=>{capture.value='DEFAULT';king.value='DEFAULT';load();};document.getElementById('reset').onclick=load;
frame.onload=()=>{api=frame.contentWindow.reactionDemo;play.disabled=!api;if(!api)return;
 document.getElementById('metadata').textContent=api.describe();
 api.subscribe(e=>{document.getElementById('status').textContent=e.cue;trace.textContent+=Math.round(e.elapsed)+' ms · '+e.cue+'\n';trace.scrollTop=trace.scrollHeight;});};
play.onclick=async()=>{if(!api)return;const run=generation;play.disabled=true;chooser.disabled=true;capture.disabled=true;king.disabled=true;trace.textContent='';
 try{await api.play(capture.value,king.value);}catch(error){if(run===generation)trace.textContent+='Error: '+error.message;}
 finally{if(run===generation){play.disabled=false;chooser.disabled=false;capture.disabled=false;king.disabled=false;}}};
function sample(){if(api)document.getElementById('actors').textContent='Visual victims: '+api.ghosts();requestAnimationFrame(sample);}sample();
const reference=document.getElementById('reference');reference.playbackRate=.5;let url;
reference.onloadedmetadata=()=>reference.currentTime=39.2;
reference.onseeked=()=>document.getElementById('referenceStatus').textContent=reference.currentTime.toFixed(3)+' s';
fetch('../assets/references/Reference.mp4').then(r=>{if(!r.ok)throw Error('Reference not found');return r.blob();}).then(blob=>{url=URL.createObjectURL(blob);reference.src=url;}).catch(e=>document.getElementById('referenceStatus').textContent=e.message);
window.addEventListener('unload',()=>{if(url)URL.revokeObjectURL(url);});
document.querySelectorAll('[data-time]').forEach(b=>b.onclick=()=>{reference.pause();reference.currentTime=Number(b.dataset.time);});
document.getElementById('rate').onchange=e=>reference.playbackRate=Number(e.target.value);load();
</script></html>'''

BRIDGE=r'''<style>body{display:block;padding:0;margin:0;min-height:0}.controls{display:none}</style><script>
const originalReactionSettings={capture:timeline[0].move.capture_reaction,king:timeline[0].move.king_reaction};
window.reactionDemo={
 subscribe:listener=>timelineScheduler.subscribe(listener),ghosts:()=>reactionSystem.ghosts.size,
 playing:()=>playing,
 describe:()=>{const m=timeline[0].move;return reactionConfig.profile+' · '+m.piece_kind+' / '+m.piece_color+(m.capture?' · captures '+m.captured_kind+' on '+m.capture:'')+(m.check?' · check on '+m.checked_king:'');},
 play:(capture,king)=>{if(playing)return Promise.resolve();for(const [channel,value] of [['capture',capture],['king',king]]){
   const v=value==='DEFAULT'?originalReactionSettings[channel]:value;
   if(v===undefined)delete timeline[0].move[channel+'_reaction'];else timeline[0].move[channel+'_reaction']=v;
 }return playSequence();}
};
</script>'''


def generate():
    output=Path('output');output.mkdir(exist_ok=True);entries=[]
    for index,(label,scene,profile) in enumerate(examples()):
        filename=f'reaction_case_{index:02d}.html'
        html=render_scene(scene,choreography_profile='REFERENCE',reaction_profile=profile,
                          meme_path='../assets/memes/MonkeyCry.mp4',meme_volume=0,
                          meme_comment_text='Fixed reaction layer · starts at settled landing')
        (output/filename).write_text(html.replace('</body>',BRIDGE+'</body>'),encoding='utf-8')
        entries.append(dict(label=label,file=filename))
    (output/'reaction_demo.html').write_text(HTML.replace('__CASES__',json.dumps(entries)),encoding='utf-8')
    print('Created output/reaction_demo.html')
    print('Serve: python3 -m http.server 8000')
    print('Open http://localhost:8000/output/reaction_demo.html')


if __name__=='__main__':generate()
