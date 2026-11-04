"""Third-level selection, compatibility and accumulated spin choreography."""
import json
from itertools import permutations
from pathlib import Path
import subprocess
import unittest
import chess
from src.renderer.chess_state import compile_sequence
from src.renderer.composition import render_scene
from src.renderer.directing import directing_config, VERY_AGGRESSIVE_HERO
from recipe_fixtures import AGGRESSIVE, THREE_SECOND

ROOT = Path(__file__).resolve().parents[1]


class VeryAggressiveTests(unittest.TestCase):
    def test_parser(self):
        for suffixes in permutations(['!!', '^VA', '~lift', '@K']):
            move = compile_sequence(chess.Board(), 'Nf3'+''.join(suffixes)+'(meme)(0s)')['moves'][0]
            self.assertEqual((move['director_tier'], move['brilliant_mode']), ('HERO','very_aggressive'))
            self.assertEqual((move['annotation'],move['camera_directive'],move['pause']), ('!!','K',0))
            self.assertEqual(move['choreography_preset'], 'LIFT_MOVE')
            self.assertTrue(move['start_meme'])
        for token in ['Nf3^VA^A','Nf3^N^VA','Nf3^V','Nf3^VAA','Nf3^va']:
            with self.assertRaises(ValueError):
                compile_sequence(chess.Board(),token)

    def test_config(self):
        config = directing_config('AUTO')
        for key,value in VERY_AGGRESSIVE_HERO.items():
            self.assertEqual(config['veryAggressive'][key],value)
        for key,value in config['aggressive'].items():
            self.assertEqual(config['veryAggressive'][key],value)
        # Existing valid aggressive minimum duration remains accepted.
        directing_config('AUTO',aggressive={'duration':100})
        for bad in [{'spinTurns':1.5},{'spinDirection':0},{'spinDuration':0},
                    {'spinOverlap':300},{'spinZoomRecoil':.9},{'spinZoomIn':float('nan')},
                    {'typo':1},{'spinReturnWide':1},{'spinReturnWideAt':1}]:
            with self.assertRaises(ValueError):
                directing_config('AUTO', very_aggressive=bad)
        html=render_scene(compile_sequence(chess.Board(),'Nf3!!^VA'),directing_profile='AUTO',
                          very_aggressive_config={'spinDuration':500,'spinDirection':-1})
        data=json.loads(html.split('const directingConfig = ')[1].split(';\n')[0])
        self.assertEqual(data['veryAggressive']['spinDuration'],500)
        self.assertEqual(data['veryAggressive']['spinDirection'],-1)
        self.assertEqual(data['aggressive'],config['aggressive'])

    def test_three_second_timing(self):
        config=directing_config('AUTO', aggressive=AGGRESSIVE, very_aggressive=THREE_SECOND)['veryAggressive']
        self.assertEqual(config['spinZoomDuration'],3000)
        self.assertAlmostEqual(config['spinPunchAt']*config['spinZoomDuration'],1400)
        self.assertAlmostEqual(config['spinRecoilAt']*config['spinZoomDuration'],1600)
        self.assertAlmostEqual(config['spinReturnWideAt']*config['spinZoomDuration'],1600)
        self.assertEqual(config['spinDuration']-config['spinOverlap']+config['duration'],3000)
        self.assertEqual(config['spinZoomIn'],config['spinZoomHold'])

    def test_plans_and_frames(self):
        html=render_scene(compile_sequence(chess.Board(),'Nf3!!^VA'),directing_profile='AUTO',
                          aggressive_config=AGGRESSIVE,
                          very_aggressive_config={**THREE_SECOND, 'spinDuration':450, 'spinZoomDuration':450, 'spinPunchAt':.16, 'spinRecoilAt':.70, 'spinReturnWideAt':.50})
        names=['scene','directingConfig','cameraConfig','timingConfig','choreographyConfig','reactionConfig','lightingConfig','motion']
        data={n:json.loads(html.split('const '+n+' = ')[1].split(';\n')[0]) for n in names}
        data['squareSize']=135
        script=r'''
const fs=require('fs'),vm=require('vm'),assert=require('assert/strict'),crypto=require('crypto');
const ctx=vm.createContext({...JSON.parse(fs.readFileSync(0,'utf8')),document:{getElementById:()=>null},assert,crypto});
vm.runInContext("function squareToCoords(s){return {x:s.charCodeAt(0)-97,y:8-Number(s[1])};}",ctx);
for(const n of ['motion','choreography','reactions','lighting_plan','director','camera_impulses'])vm.runInContext(fs.readFileSync('src/renderer/'+n+'.js','utf8'),ctx);
vm.runInContext(`
const before=JSON.stringify(directingConfig), source=scene.moves[0];
const va=buildMovePlan(source);
assert.equal(va.nextContext.shot,'J');assert.equal(va.nextContext.focus,null);
const returnFlag=directingConfig.veryAggressive.spinReturnWide;
directingConfig.veryAggressive.spinReturnWide=false;assert.equal(buildMovePlan(source).nextContext.shot,'L');
directingConfig.veryAggressive.spinReturnWide=returnFlag;
assert.equal(va.tier,'HERO');assert.equal(va.aggressive.spinTurns,2);assert.equal(va.aggressive.spinDuration,450);
assert.equal(va.lighting.aggressive.particlesMultiplier,directingConfig.aggressive.particlesMultiplier);
const a=buildMovePlan({...source,brilliant_mode:'aggressive'});
assert.equal(a.aggressive,directingConfig.aggressive);assert.equal(a.aggressive.spinTurns,undefined);
const standard=buildMovePlan({...source,brilliant_mode:'standard'});
assert.equal(standard.aggressive,null);assert.equal(standard.holdDuration,a.holdDuration);
assert.equal(standard.choreography,a.choreography);assert.equal(va.choreography,a.choreography);
const normal=buildMovePlan({...source,director_tier:'NORMAL'});
assert.equal(normal.aggressive,null);assert(!normal.hero && !normal.impulse);
assert.equal(JSON.stringify(directingConfig),before);
const move={from:'c4',to:'f4'},config=directingConfig.veryAggressive;
const oldFrames=cameraMotion.aggressiveFrames(move,directingConfig.aggressive);
assert.equal(crypto.createHash('sha256').update(JSON.stringify(oldFrames)).digest('hex'),
    '6c6c04759311cb11f117a6c1639ec81ae46a51279d8679c04ce192501afc79fd','existing ^A keyframes changed');
const frames=cameraMotion.veryAggressiveFrames(move,config);
const values=f=>f.transform.match(/[-+]?(?:\\d*\\.)?\\d+(?:e[-+]?\\d+)?/gi).map(Number);
const end=values(frames.at(-1));assert.deepEqual(Array.from(end),[0,0,720,1]);
assert.equal(frames[0].transform,cameraMotion.identity);
const total=config.spinDuration-config.spinOverlap+config.duration;
const firstPhase=frames.filter(f=>f.offset*total<config.spinDuration-config.spinOverlap);
for(let i=1;i<firstPhase.length;i++)assert(values(firstPhase[i])[2]>values(firstPhase[i-1])[2]);
assert(Math.max(...firstPhase.map(f=>values(f)[2]))>600,'two-turn spin collapsed');
assert(Math.max(...frames.map(f=>values(f)[3]))>2,'missing cinematic/safety zoom');
const join=frames.findIndex(f=>Math.abs(f.offset*total-config.spinDuration)<.00001);
assert(join>0);assert(values(frames[join])[2]>720,'rocking must already overlap spin end');
assert.notEqual(frames[join].transform,frames[join+1].transform,'handoff stopped');
assert.notEqual(frames[join].transform,frames[join-1].transform,'handoff stopped');
// The tail reuses original rocking frames, merely carrying the full-turn angle.
for(const f of oldFrames.filter(f=>f.offset*config.duration>2*config.spinOverlap)) {
    const time=config.spinDuration-config.spinOverlap+f.offset*config.duration;
    const merged=frames.find(v=>Math.abs(v.offset*total-time)<.00001);
    const expected=values(f);expected[2]+=720;
    const actual=values(merged);actual.forEach((v,i)=>assert(Math.abs(v-expected[i])<1e-9));
}
const reversed=cameraMotion.veryAggressiveFrames(move,{...config,spinDirection:-1});
assert.equal(values(reversed.at(-1))[2],-720);
const short=cameraMotion.veryAggressiveFrames(move,{...config,duration:100});
assert.deepEqual(Array.from(values(short.at(-1))),[0,0,720,1]);
assert.equal(JSON.stringify(frames),JSON.stringify(cameraMotion.veryAggressiveFrames(move,config)));
`,ctx);
'''
        subprocess.run(['node','-e',script],input=json.dumps(data),text=True,cwd=ROOT,check=True)


if __name__=='__main__':
    unittest.main()
