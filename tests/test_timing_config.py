"""Pure timing plans: authored pauses, preset durations and profile compatibility."""
import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.renderer.camera import camera_config
from src.renderer.composition import render_scene
from src.renderer.motion import movement_presets
from src.renderer.timing import timing_config
from src.renderer.choreography import choreography_config
from src.renderer.reactions import reaction_config
from src.renderer.lighting import lighting_config


class TimingPlanTests(unittest.TestCase):
    def test_profile_validation(self):
        with self.assertRaisesRegex(ValueError, "profile"):
            render_scene({"pieces": [], "moves": [], "timeline": []}, timing_profile="typo")

    def test_plans_preserve_user_timing_and_movement(self):
        script = """
const fs = require('node:fs'), vm = require('node:vm'), assert = require('node:assert/strict');
const input = JSON.parse(fs.readFileSync(0, 'utf8'));
const context = vm.createContext(input);
vm.runInContext(fs.readFileSync('src/renderer/motion.js', 'utf8') +
                fs.readFileSync('src/renderer/choreography.js', 'utf8') +
                fs.readFileSync('src/renderer/reactions.js', 'utf8') +
                fs.readFileSync('src/renderer/lighting_plan.js', 'utf8') +
                fs.readFileSync('src/renderer/director.js', 'utf8'), context);
const plan = move => {
    context.move = move;
    const before = JSON.stringify(move);
    const result = vm.runInContext('buildMovePlan(move)', context);
    assert.equal(JSON.stringify(move), before, 'director must not mutate compiled state');
    assert(Object.isFrozen(result));
    return result;
};
const ordinary = plan({camera_directive:'K',pause:.2});
assert.equal(ordinary.moveDuration, 700);
assert.equal(ordinary.holdDuration, 200);
assert.equal(ordinary.pieceDelay, 0);
const hero = plan({camera_directive:'L',annotation:'!!',pause:2.8});
assert.equal(hero.holdDuration, 2980, 'authored pause plus original brilliant posthold');
assert.equal(hero.pieceDelay, 120);
assert.equal(plan({animation_preset:'FAST_MOVE'}).moveDuration, 455);
assert.equal(plan({animation_preset:'DRAMATIC_MOVE'}).moveDuration, 1050);
assert.equal(plan({camera_directive:'J'}).cameraDuration, input.cameraConfig.wideDuration);
assert.equal(plan({pause:0}).holdDuration, 0, 'zero pauses must remain zero');
assert.equal(plan({}).cameraDuration, 0, 'unmarked move must retain its shot');
assert.equal(plan({annotation:'!!'}).holdDuration, 180);
assert.throws(() => plan({animation_preset:'typo'}), /Unknown movement preset/);
if (input.timingConfig.profile === 'REFERENCE') {
    assert.equal(hero.cameraDuration, 400);
    assert.equal(hero.hero, true);
    assert.equal(hero.impulse, true);
    assert.equal(hero.serialCamera, false);
    assert(hero.pieceDelay < hero.cameraDuration);
} else {
    assert.equal(hero.cameraDuration, 240);
    assert.equal(hero.hero, false);
    assert.equal(hero.impulse, false);
    assert.equal(hero.serialCamera, true);
}
"""
        for profile in ("REFERENCE", "LEGACY"):
            with self.subTest(profile=profile):
                data = dict(squareSize=135, motion=dict(presets=movement_presets(),
                            defaultPreset="NORMAL_MOVE"), cameraConfig=camera_config(profile=profile),
                            timingConfig=timing_config(profile), choreographyConfig=choreography_config(),
                            reactionConfig=reaction_config(), lightingConfig=lighting_config())
                subprocess.run(["node", "-e", script], input=json.dumps(data), text=True,
                               cwd=ROOT, check=True)


if __name__ == "__main__":
    unittest.main()
