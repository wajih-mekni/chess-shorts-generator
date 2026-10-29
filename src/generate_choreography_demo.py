"""Generate the Stage 3 gallery: legal positions, both colors, reusable recipes."""
from pathlib import Path
import json
import chess
try:
    from .renderer.chess_state import compile_sequence
    from .renderer.composition import render_scene
    from .renderer.choreography import choreography_config
except ImportError:
    from renderer.chess_state import compile_sequence
    from renderer.composition import render_scene
    from renderer.choreography import choreography_config

CASES = [
    ("Rook flip · right", chess.ROOK, "d4f4", False, "ROOK_FLIP"),
    ("Rook flip · left / black", chess.ROOK, "f4d4", True, "ROOK_FLIP"),
    ("Bishop sweep · ascending", chess.BISHOP, "b2d4", False, "BISHOP_SWEEP"),
    ("Bishop sweep · black", chess.BISHOP, "d4b2", True, "BISHOP_SWEEP"),
    ("Bishop spin · ascending", chess.BISHOP, "b2d4", False, "BISHOP_SPIN"),
    ("Bishop spin · black", chess.BISHOP, "d4b2", True, "BISHOP_SPIN"),
    ("Queen spin · right", chess.QUEEN, "c4e4", False, "QUEEN_SPIN"),
    ("Queen spin · left / black", chess.QUEEN, "e4c4", True, "QUEEN_SPIN"),
    ("Knight jump · ascending", chess.KNIGHT, "b1c3", False, "KNIGHT_JUMP"),
    ("Knight jump · black", chess.KNIGHT, "g1f3", True, "KNIGHT_JUMP"),
    ("Lift · white pawn", chess.PAWN, "e2e4", False, "LIFT_MOVE"),
    ("Generic spin · bishop", chess.BISHOP, "b2d4", False, "SPIN_WITH_HANG"),
    ("Legacy aggressive · same rook path", chess.ROOK, "d4f4", False, "LEGACY"),
    ("Legacy aggressive · pawn", chess.PAWN, "e2e4", False, "LEGACY"),
]


def demo_scene(kind, uci, black, preset):
    board = chess.Board(None)
    board.set_piece_at(chess.A1, chess.Piece(chess.KING, chess.WHITE))
    board.set_piece_at(chess.H6, chess.Piece(chess.KING, chess.BLACK))
    move = chess.Move.from_uci(uci)
    board.set_piece_at(move.from_square, chess.Piece(kind, chess.WHITE))
    if black:
        board = board.mirror()
        move = chess.Move(chess.square_mirror(move.from_square), chess.square_mirror(move.to_square))
    assert board.is_valid() and move in board.legal_moves, (board.fen(), move)
    scene = compile_sequence(board, board.san(move) + "!@K", .7)
    scene["moves"][0]["choreography_preset"] = preset
    return scene


HTML = r"""<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Piece choreography · Stage 3</title>
<style>
* {box-sizing:border-box} body {margin:0;background:#14181e;color:#e6edf3;font:14px/1.5 system-ui}
main {max-width:1440px;margin:auto;padding:24px} h1 {font-size:26px;margin:0 0 8px} h2 {font-size:17px}
p {color:#b3bfcc} a {color:#8ad8e3} .grid {display:grid;grid-template-columns:minmax(270px,378px) 1fr 320px;gap:24px;align-items:start}
.preview {position:relative;width:100%;aspect-ratio:9/16;overflow:hidden;border-radius:12px;background:#222}
iframe {position:absolute;left:0;top:0;width:1080px;height:1920px;border:0;transform-origin:top left}
button,select {font:inherit;background:#27323e;color:#eef7ff;border:1px solid #546575;border-radius:6px;padding:9px;margin:4px 0;max-width:100%}
button {cursor:pointer} button:disabled {opacity:.5} #play {background:#238076;width:100%}
select {width:100%} .box {background:#1d252e;border:1px solid #35414e;border-radius:8px;padding:14px;margin:14px 0}
#phase {font-size:26px;color:#8ee3d5} #trace {max-height:180px;overflow:auto;font:12px/1.6 monospace;white-space:pre-wrap}
video {width:100%;border-radius:10px;background:#000} .small {font-size:12px} #details {white-space:pre-line}
@media(max-width:1000px){.grid{grid-template-columns:minmax(270px,378px) 1fr}.reference{grid-column:2}}
@media(max-width:650px){.grid{display:block}.preview{max-width:378px}.reference{max-width:378px}}
</style><main><h1>Piece choreography · Stage 3</h1>
<p>Same recipes across colors and directions. Travel, sprite deformation and camera each own their motion.</p>
<div class="grid"><section><div class="preview" id="preview"><iframe id="scene" title="Generated chess scene"></iframe></div>
<button id="play">Play / Replay move</button><p class="small">The reaction layer stays fixed. No captured-piece reactions, lighting or particles.</p></section>
<section><h2>Choose a position</h2><select id="cases" aria-label="Position"></select>
<h2>Apply any recipe to this position</h2><select id="recipe" aria-label="Choreography preset"></select>
<label><input id="cameraEnabled" type="checkbox" checked> Overlapping camera movement</label>
<div class="box"><div id="phase">Ready</div><div id="details"></div></div>
<div class="box" id="trace"></div>
<p>Spin phases: launch toward inversion → inverted hang → accelerated finish → settle. The turn remains continuous through 360°; cleanup removes the final identity transform.</p>
<p class="small">Camera target remains destination-focused. Switch it off to inspect board-space travel. Recipes are explicit here; no automatic tactical choreography is added.</p>
<a href="timing_camera_demo.html">Timing + camera comparison</a></section>
<section class="reference"><h2>Reference · independent playback</h2>
<video id="reference" controls muted playsinline preload="metadata" data-src="../assets/references/Reference.mp4"></video>
<p class="small" id="referenceStatus">Loading reference…</p>
<button data-time="31.5">Rook · 31.50 s</button><button data-time="27.35">Bishop · 27.35 s</button><button data-time="39.75">Queen · 39.75 s</button>
<select id="rate" aria-label="Reference playback speed"><option value=".25">0.25× reference</option><option value=".5" selected>0.5× reference</option><option value="1">1× reference</option></select>
<p class="small">Inverted rook around 31.70–31.83 s. Final quarter-turn is partly obscured in the source; our clear finish and settling are a tunable interpretation.</p></section></div></main>
<script>
const cases=__CASES__, presets=__PRESETS__;
const frame=document.getElementById('scene'), chooser=document.getElementById('cases'), recipe=document.getElementById('recipe');
const play=document.getElementById('play'), trace=document.getElementById('trace');
let api=null, generation=0;
cases.forEach((item,i)=>chooser.add(new Option(item.label,i)));
['LEGACY',...Object.keys(presets)].forEach(name=>recipe.add(new Option(name,name)));
const resize=()=>frame.style.transform='scale('+document.getElementById('preview').clientWidth/1080+')';
new ResizeObserver(resize).observe(document.getElementById('preview')); resize();
function describe() {
 const name=recipe.value, p=presets[name];
 document.getElementById('details').textContent=p ? p.duration+' ms total · independent travel + deformation'+
   (p.kind==='spin'?'\n'+p.launch+' ms launch / '+p.hang+' ms hang / '+p.finish+' ms finish / '+p.settle+' ms settle':'\nLift '+p.lift+' squares · peak scale '+p.scale+'×') :
   'Original NORMAL_MOVE: 700 ms · scale 1.20× · rotation 12° · overshoot 0.12 square';
}
function load() {
 generation++; api=null; play.disabled=true; trace.textContent='';
 recipe.value=cases[Number(chooser.value)].preset; describe();
 document.getElementById('phase').textContent='Ready';
 frame.src=cases[Number(chooser.value)].file;
}
frame.onload=()=>{api=frame.contentWindow.choreographyDemo;play.disabled=!api;
 if(!api){trace.textContent='Serve the project with python3 -m http.server 8000';return;}
 api.subscribe(e=>{trace.textContent+=Math.round(e.elapsed)+' ms · '+e.cue+'\n';trace.scrollTop=trace.scrollHeight;});};
chooser.onchange=load; recipe.onchange=describe;
play.onclick=async()=>{if(!api)return;const current=generation;
 play.disabled=true;chooser.disabled=true;recipe.disabled=true;trace.textContent='';
 try {await api.play(recipe.value,document.getElementById('cameraEnabled').checked);}
 catch(error){trace.textContent+='Error: '+error.message;}
 finally{if(current===generation){play.disabled=false;chooser.disabled=false;recipe.disabled=false;document.getElementById('phase').textContent='Settled';}}};
function sample(){if(api&&api.playing())document.getElementById('phase').textContent=api.phase();requestAnimationFrame(sample);}sample();
const reference=document.getElementById('reference');reference.playbackRate=.5;
reference.onloadedmetadata=()=>reference.currentTime=31.5;
// python -m http.server lacks byte-range support. A local blob makes source
// seeking reliable without requiring a special preview server or video export.
let referenceBlob;
fetch(reference.dataset.src).then(response=>{
 if(!response.ok)throw Error('Reference video not found');
 return response.blob();
}).then(blob=>{referenceBlob=URL.createObjectURL(blob);reference.src=referenceBlob;})
 .catch(error=>document.getElementById('referenceStatus').textContent=error.message);
reference.onseeked=()=>document.getElementById('referenceStatus').textContent=reference.currentTime.toFixed(3)+' s';
window.addEventListener('unload',()=>{if(referenceBlob)URL.revokeObjectURL(referenceBlob);});
document.querySelectorAll('[data-time]').forEach(button=>button.onclick=()=>{reference.pause();reference.currentTime=Number(button.dataset.time);});
document.getElementById('rate').onchange=e=>reference.playbackRate=Number(e.target.value);
load();
</script></html>"""

BRIDGE = r"""<style>body{display:block;padding:0;margin:0;min-height:0}.controls{display:none}</style>
<script>
window.choreographyDemo={
 subscribe:listener=>timelineScheduler.subscribe(listener), playing:()=>playing,
 play:(name,enabled)=>{
   if(playing)return Promise.resolve();
   for(const event of timeline)if(event.move)event.move.choreography_preset=name;
   cameraConfig.enabled=enabled;
   return playSequence();
 },
 phase:()=>{
   const element=Object.values(pieceBySquare).find(piece=>piece.getAnimations().length);
   // The moving actor is temporarily absent from the logical square map.
   const actor=element||[...renderedPieces].find(piece=>piece.getAnimations().length);
   const animation=actor?.getAnimations()[0];
   if(!animation)return 'Reading hold';
   const p=resolvePieceMotion(timeline[0].move).preset, t=animation.currentTime||0;
   if(p.kind!=='spin')return 'Eased travel / lift';
   return t<p.launch?'Launch → inversion':t<p.launch+p.hang?'Inverted hang':
       t<p.launch+p.hang+p.finish?'Accelerated finish':'Landing / settle';
 }
};
</script>"""


def generate():
    output=Path("output")
    output.mkdir(exist_ok=True)
    entries=[]
    for index,(label,kind,uci,black,preset) in enumerate(CASES):
        scene=demo_scene(kind,uci,black,preset)
        filename=f"choreography_case_{index:02d}.html"
        html=render_scene(scene, meme_path="../assets/memes/MonkeyCry.mp4", meme_volume=0,
                          meme_comment_text="Fixed reaction layer", choreography_profile="REFERENCE")
        (output/filename).write_text(html.replace("</body>",BRIDGE+"</body>"),encoding="utf-8")
        entries.append(dict(label=label,preset=preset,file=filename))
    html=HTML.replace("__CASES__",json.dumps(entries)).replace("__PRESETS__",json.dumps(choreography_config()["presets"]))
    (output/"choreography_demo.html").write_text(html,encoding="utf-8")
    print("Created output/choreography_demo.html")
    print("Serve the project root: python3 -m http.server 8000")
    print("Open http://localhost:8000/output/choreography_demo.html")


if __name__=="__main__":
    generate()
