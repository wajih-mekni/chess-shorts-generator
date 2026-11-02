"""Automatic selection, override precedence and compact choreography notation."""
import json,subprocess,sys,unittest
from pathlib import Path
import chess
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.renderer.chess_state import compile_sequence,parse_choreography_directive
from src.renderer.directing import CHOREOGRAPHY_ALIASES,directing_config
from src.renderer.composition import render_scene
from src.renderer.camera import camera_config
from src.renderer.timing import timing_config
from src.renderer.motion import movement_presets
from src.renderer.choreography import choreography_config
from src.renderer.reactions import reaction_config
from src.renderer.lighting import lighting_config
from src.generate_sequence_animation import DEMO_SEQUENCE

class DirectingTests(unittest.TestCase):
    def test_inline_aliases_and_order(self):
        for alias,preset in CHOREOGRAPHY_ALIASES.items():
            for token in [f'Nf3~{alias}!!@L(meme)(0s)',f'Nf3!!@L~{alias}(meme)(0s)',f'Nf3!!(meme)(0s)~{alias}@L']:
                with self.subTest(token=token):
                    m=compile_sequence(chess.Board(),token)['moves'][0]
                    self.assertEqual(m['choreography_preset'],preset)
                    self.assertEqual((m['annotation'],m['camera_directive'],m['pause'],m['start_meme']),('!!','L',0,True))
                    self.assertTrue(m['pause_explicit'])
        for token in ['e4~bad','e4~jump~spin','e4~','e4~Lift','e4~~spin']:
            with self.assertRaises(ValueError):compile_sequence(chess.Board(),token)
        m=compile_sequence(chess.Board(),'e4 e5')['moves'][0]
        self.assertFalse(m['pause_explicit']);self.assertNotIn('choreography_preset',m)
        self.assertEqual(parse_choreography_directive('Qh5~spin+!!@L')[0],'Qh5+!!@L')

    def test_auto_composition_and_validation(self):
        scene=compile_sequence(chess.Board(),DEMO_SEQUENCE)
        auto=render_scene(scene,directing_profile='AUTO')
        for name in ['choreographyConfig','reactionConfig','lightingConfig']:
            config=json.loads(auto.split('const '+name+' = ')[1].split(';\n')[0])
            self.assertEqual(config['profile'],'REFERENCE')
        legacy=render_scene(scene,directing_profile='LEGACY')
        self.assertIn('src="../assets/board.svg"',legacy)
        with self.assertRaisesRegex(ValueError,'directing profile'):render_scene(scene,directing_profile='bad')
        scene['moves'][0]['director_tier']='bad'
        with self.assertRaisesRegex(ValueError,'director tier'):render_scene(scene,directing_profile='AUTO')

    def test_pure_plans(self):
        data=dict(directingConfig=directing_config('AUTO'),cameraConfig=camera_config(),timingConfig=timing_config(),
                  choreographyConfig=choreography_config('REFERENCE'),reactionConfig=reaction_config('REFERENCE'),
                  lightingConfig=lighting_config('REFERENCE'),squareSize=135,
                  motion=dict(presets=movement_presets(),defaultPreset='NORMAL_MOVE'),
                  moves=compile_sequence(chess.Board(),DEMO_SEQUENCE)['moves'])
        script=r'''
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const data=JSON.parse(fs.readFileSync(0,'utf8')),ctx=vm.createContext(data);
for(const name of ['motion','choreography','reactions','lighting_plan','director'])vm.runInContext(fs.readFileSync('src/renderer/'+name+'.js','utf8'),ctx);
const run=s=>vm.runInContext(s,ctx);
const before=JSON.stringify(data.moves);
const plans=run("(()=>{let c={shot:'J',focus:null};return moves.map(m=>{const p=buildMovePlan(m,c);c=p.nextContext;return p;});})()");
assert.equal(JSON.stringify(data.moves),before,'director mutated logical sequence');
assert.equal(plans[0].tier,'NORMAL');assert.equal(plans[0].choreography,'LIFT_MOVE');assert.equal(plans[0].holdDuration,280);
assert.equal(plans[2].choreography,'KNIGHT_JUMP');assert.equal(plans[4].choreography,'BISHOP_SWEEP');
assert.equal(plans[6].tier,'TACTICAL');assert.equal(plans[6].lighting.palette,'GREEN');assert(plans[6].impulse);assert.equal(plans[6].impactStrength,.55);
assert.equal(plans[9].lighting.palette,'ORANGE');assert.equal(plans[10].tier,'HERO');assert.equal(plans[10].holdDuration,2980);
assert.equal(plans[10].lighting.name,'HERO');assert.equal(plans[10].lighting.palette,'CYAN');assert(plans[10].hero);
assert.equal(plans[10].reactions.capture.name,'CAPTURE_KNOCKBACK');assert.equal(plans[12].lighting.palette,'RED');assert.equal(plans[12].reactions.king.name,'KING_RECOIL');
assert.equal(plans.at(-1).move.camera_directive,'J');
ctx.input={from:'d1',to:'d5',piece_kind:'queen',capture:'d5',check:true,checked_king:'h5',pause_explicit:false};
const plan=()=>run('buildMovePlan(input)');
assert.equal(plan().choreography,'QUEEN_SPIN');assert.equal(plan().tier,'TACTICAL');
for(const directive of ['J','K','L']) {ctx.input.camera_directive=directive;assert.equal(plan().move.camera_directive,directive);}
Object.assign(ctx.input,{annotation:'!!',choreography_preset:'LIFT_MOVE',effect_preset:'NONE',capture_reaction:'NONE',king_reaction:'NONE',pause:0,pause_explicit:true});
assert.equal(plan().choreography,'LIFT_MOVE');assert.equal(plan().lighting,null);assert.equal(plan().reactions.capture,null);assert.equal(plan().reactions.king,null);assert.equal(plan().holdDuration,180);
ctx.input={from:'a1',to:'h8',piece_kind:'bishop',annotation:'!!',pause_explicit:false};
assert.equal(plan().move.camera_directive,'K','long hero must have wider default framing');assert.equal(plan().choreography,'BISHOP_SPIN');
ctx.input={from:'a1',to:'a2',piece_kind:'rook',pause_explicit:false};
assert.equal(run("buildMovePlan(input,{shot:'L',focus:'h8'}).move.camera_directive"),'J');
assert.equal(run("buildMovePlan(input,{shot:'K',focus:'a3'}).move.camera_directive"),undefined);
ctx.input={from:'e1',to:'g1',piece_kind:'king',rook_from:'h1',rook_to:'f1',pause_explicit:false};
assert.equal(plan().choreography,'LIFT_MOVE');assert.equal(plan().move.camera_directive,'J');assert.equal(plan().move.rook_choreography_preset,'LIFT_MOVE');
ctx.input={from:'b7',to:'a8',piece_kind:'pawn',promotion:'wQ.svg',pause_explicit:false};assert.equal(plan().tier,'HERO');assert.equal(plan().choreography,'LIFT_MOVE');
ctx.input={from:'e5',to:'d6',piece_kind:'pawn',capture:'d5',en_passant:true,pause_explicit:false};assert.equal(plan().reactions.capture.name,'CAPTURE_SHRINK');
ctx.input={from:'d4',to:'d5',piece_kind:'rook',animation_preset:'FAST_MOVE'};assert.equal(plan().choreography,'FAST_MOVE');
ctx.input.director_tier='HERO';ctx.input.effect_palette='ORANGE';assert.equal(plan().lighting.palette,'ORANGE');
ctx.directingConfig.enabled=false;assert.equal(plan().tier,null);assert.equal(plan().choreography,'FAST_MOVE');
'''
        subprocess.run(['node','-e',script],input=json.dumps(data),text=True,cwd=ROOT,check=True)

if __name__=='__main__':unittest.main()
