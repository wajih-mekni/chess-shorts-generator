"""Inline NORMAL override preserves notation without brilliant visual timing."""
import json
import subprocess
import unittest
from itertools import permutations
from pathlib import Path
import chess
from src.renderer.chess_state import compile_sequence
from src.renderer.composition import render_scene


class NormalOverrideTests(unittest.TestCase):
    def test_suffix_order_and_validation(self):
        for suffixes in permutations(['!!', '^N', '~lift', '@K']):
            move = compile_sequence(chess.Board(), 'Nf3'+''.join(suffixes)+'(meme)(0s)')['moves'][0]
            self.assertEqual(move['director_tier'], 'NORMAL')
            self.assertEqual(move['annotation'], '!!')
            self.assertEqual(move['camera_directive'], 'K')
            self.assertEqual(move['choreography_preset'], 'LIFT_MOVE')
            self.assertTrue(move['start_meme'])
            self.assertEqual(move['pause'], 0)
        for token in ['Nf3!!(meme)(2s)^N', 'Nf3^N!!(meme)(2s)']:
            move = compile_sequence(chess.Board(), token)['moves'][0]
            self.assertEqual((move['director_tier'], move['pause']), ('NORMAL', 2))
        for token in ['Nf3^', 'Nf3^H', 'Nf3^n', 'Nf3^NN', 'Nf3^N^N']:
            with self.assertRaisesRegex(ValueError, 'director tier'):
                compile_sequence(chess.Board(), token)
        self.assertNotIn('director_tier', compile_sequence(chess.Board(), 'Nf3!!')['moves'][0])

    def test_calm_plan_and_unchanged_hero(self):
        scene = compile_sequence(chess.Board('7k/8/8/8/8/3Q4/8/K7 w - - 0 1'), 'Qh7!!^N')
        html = render_scene(scene, directing_profile='AUTO')
        names = ['scene', 'directingConfig', 'cameraConfig', 'timingConfig', 'choreographyConfig', 'reactionConfig', 'lightingConfig', 'motion']
        data = {n: json.loads(html.split('const '+n+' = ')[1].split(';\n')[0]) for n in names}
        data['squareSize'] = 135
        script = r'''
const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const ctx=vm.createContext(JSON.parse(fs.readFileSync(0,'utf8')));
for(const n of ['motion','choreography','reactions','lighting_plan','director'])vm.runInContext(fs.readFileSync('src/renderer/'+n+'.js','utf8'),ctx);
vm.runInContext(`
const original=JSON.stringify(scene);
const p=buildMovePlan(scene.moves[0],{shot:'L',focus:'d1'});
if(p.tier!=='NORMAL'||p.move.annotation!=='!!'||p.choreography!=='LIFT_MOVE'||p.move.camera_directive!=='J')throw Error('Normal selection failed');
if(p.hero||p.impulse||p.impactStrength!==0||p.lighting.name!=='LOCAL_ACCENT')throw Error('Hero visuals leaked');
if(p.holdDuration!==directingConfig.tiers.NORMAL.pause*1000||p.pieceDelay!==timingConfig.cameraLeadNormal)throw Error('Brilliant timing leaked');
const explicit=buildMovePlan({...scene.moves[0],camera_directive:'L',pause:2,pause_explicit:true});
if(explicit.hero||explicit.impulse||explicit.holdDuration!==2000)throw Error('Explicit pause/camera handling');
const hero={...scene.moves[0]};delete hero.director_tier;
const h=buildMovePlan(hero);
if(h.tier!=='HERO'||!h.hero||!h.impulse||h.lighting.name!=='HERO'||h.holdDuration!==directingConfig.tiers.HERO.pause*1000+cameraConfig.brilliantPostHold)throw Error('Existing hero changed');
if(JSON.stringify(scene)!==original)throw Error('Input mutated');
`,ctx);
'''
        subprocess.run(['node', '-e', script], input=json.dumps(data), text=True, check=True,
                       cwd=Path(__file__).resolve().parents[1])
