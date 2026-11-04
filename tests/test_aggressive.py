"""Optional brilliant recipe: parsing, immutable plans and safe serialization."""
import json
from itertools import permutations
from pathlib import Path
import subprocess
import unittest
import chess
from src.renderer.chess_state import compile_sequence
from src.renderer.composition import render_scene
from src.renderer.directing import AGGRESSIVE_HERO, directing_config

ROOT = Path(__file__).resolve().parents[1]


class AggressiveTests(unittest.TestCase):
    def test_parser(self):
        for suffixes in permutations(['!!', '^A', '~lift', '@K']):
            move = compile_sequence(chess.Board(), 'Nf3'+''.join(suffixes)+'(meme)(0s)')['moves'][0]
            self.assertEqual((move['director_tier'], move['brilliant_mode']), ('HERO', 'aggressive'))
            self.assertEqual((move['annotation'], move['camera_directive'], move['pause']), ('!!', 'K', 0))
            self.assertEqual(move['choreography_preset'], 'LIFT_MOVE')
        for token in ['Nf3^A^N', 'Nf3^A^A', 'Nf3^AA', 'Nf3^a']:
            with self.assertRaises(ValueError):
                compile_sequence(chess.Board(), token)

    def test_config(self):
        self.assertEqual(directing_config('AUTO')['aggressive'], AGGRESSIVE_HERO)
        for config in [{'rotation':21}, {'duration':0}, {'damping':float('nan')}, {'zoom':2}, {'unknown':1}]:
            with self.assertRaises(ValueError):
                directing_config('AUTO', aggressive=config)
        with self.assertRaises(ValueError):
            directing_config('AUTO', brilliant_mode='typo')
        scene = compile_sequence(chess.Board(), 'Nf3!!^A')
        html = render_scene(scene, directing_profile='AUTO', brilliant_mode='aggressive', aggressive_config={'rotation':20})
        self.assertNotIn('${', html)
        config = json.loads(html.split('const directingConfig = ')[1].split(';\n')[0])
        self.assertEqual(config['aggressive']['rotation'], 20)
        self.assertEqual(config['brilliantMode'], 'aggressive')

    def test_plans(self):
        html = render_scene(compile_sequence(chess.Board(), 'Nf3!!'), directing_profile='AUTO', aggressive_config={'rotation':12})
        names = ['scene','directingConfig','cameraConfig','timingConfig','choreographyConfig','reactionConfig','lightingConfig','motion']
        data = {n:json.loads(html.split('const '+n+' = ')[1].split(';\n')[0]) for n in names}
        data['squareSize'] = 135
        script = r'''
const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const ctx=vm.createContext(JSON.parse(fs.readFileSync(0,'utf8')));
for(const n of ['motion','choreography','reactions','lighting_plan','director'])vm.runInContext(fs.readFileSync('src/renderer/'+n+'.js','utf8'),ctx);
ctx.assert=assert;
vm.runInContext(`
const source=scene.moves[0], before=JSON.stringify(source);
const standard=buildMovePlan(source);
assert.equal(standard.tier,'HERO');assert.equal(standard.aggressive,null);
assert(standard.hero);assert.equal(standard.lighting.name,'HERO');
assert.equal(standard.holdDuration,1680);assert.equal(standard.impactStrength,1);
const forced=buildMovePlan({...source,director_tier:'HERO',brilliant_mode:'aggressive'});
assert.equal(forced.aggressive.rotation,12);assert.equal(forced.lighting.aggressive.particlesMultiplier,2);
assert.equal(forced.choreography,standard.choreography);
assert.equal(forced.holdDuration,standard.holdDuration);
directingConfig.brilliantMode='aggressive';
assert.equal(JSON.stringify(buildMovePlan(source).aggressive),JSON.stringify(forced.aggressive));
const normal=buildMovePlan({...source,director_tier:'NORMAL'});
assert.equal(normal.aggressive,null);assert(!normal.hero);assert(!normal.impulse);
assert.equal(normal.lighting.name,'LOCAL_ACCENT');assert.equal(normal.holdDuration,450);
assert.equal(buildMovePlan({...source,annotation:null}).aggressive,null);
assert.equal(buildMovePlan({...source,brilliant_mode:'standard'}).aggressive,null);
const explicit=buildMovePlan({...source,camera_directive:'J',pause:0,pause_explicit:true,effect_preset:'NONE'});
assert.equal(explicit.move.camera_directive,'J');assert.equal(explicit.holdDuration,180);assert.equal(explicit.lighting,null);
assert.equal(JSON.stringify(source),before);
directingConfig.enabled=false;assert.equal(buildMovePlan(source).aggressive,null);
`,ctx);
'''
        subprocess.run(['node','-e',script], input=json.dumps(data), text=True, cwd=ROOT, check=True)


if __name__ == '__main__':
    unittest.main()
