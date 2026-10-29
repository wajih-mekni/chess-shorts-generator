"""Pure Stage 5 selection, deterministic particle geometry and finite envelopes."""
from pathlib import Path
import json,subprocess,sys,unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.renderer.lighting import lighting_config
from src.renderer.composition import render_scene
from src.generate_lighting_demo import examples

class LightingTests(unittest.TestCase):
    def test_validation_and_legacy(self):
        self.assertFalse(lighting_config()['enabled'])
        with self.assertRaisesRegex(ValueError,'lighting profile'):lighting_config('bad')
        scene=examples()[0][1]
        html=render_scene(scene)
        self.assertIn('src="../assets/board.svg"',html)
        self.assertNotIn('class="short-canvas lighting-reference"',html)
        reference=render_scene(scene,lighting_profile='REFERENCE')
        self.assertIn('data:image/svg+xml',reference)
        self.assertNotIn('${',reference)
        for key,value,pattern in [('effect_preset','bad','effect preset'),('effect_palette','bad','effect palette')]:
            original=scene['moves'][0].get(key)
            scene['moves'][0][key]=value
            with self.assertRaisesRegex(ValueError,pattern):render_scene(scene)
            scene['moves'][0][key]=original

    def test_pure_effect_plans(self):
        script=r"""
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const lightingConfig=JSON.parse(fs.readFileSync(0,'utf8'));
const ctx=vm.createContext({lightingConfig,squareSize:135});
vm.runInContext(fs.readFileSync('src/renderer/lighting_plan.js','utf8')+fs.readFileSync('src/renderer/particles.js','utf8'),ctx);
const run=s=>vm.runInContext(s,ctx);
assert.equal(run("resolveLighting({annotation:'!!',check:true}).name"),'LOCAL_ACCENT','Stage 6 selection leaked in');
assert.equal(run("resolveLighting({effect_palette:'RED'}).palette"),'RED');
assert.equal(run("resolveLighting({effect_preset:'NONE'})"),null);
const source="particleDescriptors('CAPTURE_FRAGMENTS','seed',420,{x:1,y:0})";
assert.equal(JSON.stringify(run(source)),JSON.stringify(run(source)));
assert.notEqual(JSON.stringify(run(source)),JSON.stringify(run(source.replace("'seed'","'other'"))));
for(const name of Object.keys(lightingConfig.particles)) {
  ctx.name=name;
  const particles=run("particleDescriptors(name,'seed',5000,{x:1,y:0})");
  assert(particles.length>0&&particles.length<=lightingConfig.maxParticles);
  for(const p of particles){assert(p.duration>0);assert(p.delay>=0);assert(p.frames.at(-1).opacity===0);assert(!JSON.stringify(p).includes('NaN'));}
}
assert.equal(run("particleDescriptors('AMBIENT_DUST','seed',0,{x:0,y:0}).length"),0);
assert(run("particleDescriptors('AMBIENT_DUST','seed',1e9,{x:0,y:0}).length")<=lightingConfig.maxParticles);
const frames=run('lightPulseFrames(3000,.85,.3,true)');
assert.equal(frames[0].opacity,0);assert.equal(frames.at(-1).opacity,0);
assert(Math.abs(frames[10].opacity-frames[20].opacity)<1e-8,'500ms rhythm changed');
assert(frames[10].opacity>frames[15].opacity,'hold does not breathe');
lightingConfig.enabled=false;
assert.equal(run("resolveLighting({effect_preset:'HERO'})"),null);
"""
        subprocess.run(['node','-e',script],input=json.dumps(lighting_config('REFERENCE')),text=True,cwd=ROOT,check=True)

if __name__=='__main__':unittest.main()
