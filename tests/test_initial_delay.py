"""Opening hold configuration and once-per-playback/replay ordering."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import chess
from src.renderer.chess_state import compile_sequence
from src.renderer.composition import render_scene
from src import generate_sequence_animation as production

ROOT = Path(__file__).resolve().parents[1]


class InitialDelayTests(unittest.TestCase):
    def test_configuration_and_production_wiring(self):
        scene=compile_sequence(chess.Board(),'e4(0.5s) e5(0s)')
        def config(html):
            return json.loads(html.split('const playbackConfig = ')[1].split(';\n')[0])
        self.assertEqual(config(render_scene(scene))['initialDelayMs'],0)
        self.assertEqual(config(render_scene(scene,initial_delay=2.5))['initialDelayMs'],2500)
        self.assertEqual(scene['moves'][0]['pause'],.5)
        for value in [-1,float('nan'),float('inf'),True,'2',3_000_000]:
            with self.assertRaises(ValueError):render_scene(scene,initial_delay=value)
        with tempfile.TemporaryDirectory() as folder, patch.object(production,'INITIAL_DELAY',1.75):
            output=Path(folder)/'preview.html'
            production.generate(output,start_fen=chess.STARTING_FEN,sequence='e4')
            self.assertEqual(config(output.read_text())['initialDelayMs'],1750)
            production.generate(output,start_fen=chess.STARTING_FEN,sequence='e4',initial_delay=0)
            self.assertEqual(config(output.read_text())['initialDelayMs'],0)

    def test_once_per_playback_after_reset(self):
        script=r'''
const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const log=[],timers=[];
const ctx=vm.createContext({
  document:{getElementById:()=>({})},hasMemeTriggers:false,
  pieceMemeConfig:{enabled:false},pieceMemeSystem:{reset(){}},
  playbackConfig:{initialDelayMs:1250},timeline:[{type:'move',move:{id:1}},{type:'move',move:{id:2}}],
  setTimeout:(fn,ms)=>{timers.push({fn,ms});log.push('delay');},
  startMemeVideo:()=>log.push('meme'),startBackgroundMusic:()=>log.push('music'),
  prepareMoveAudio:async()=>{log.push('prepare');},
  clearMoveEffects:()=>log.push('clear'),resetPieces:()=>log.push('reset'),
  camera:{reset:()=>log.push('camera-reset'),finished:Promise.resolve()},
  cameraMotion:{reset:()=>log.push('motion-reset'),finished:Promise.resolve()},
  reactionSystem:{finished:Promise.resolve()},lightingSystem:{finished:Promise.resolve()},
  finishMoveEffects:()=>Promise.resolve(),log
});
vm.runInContext(fs.readFileSync('src/renderer/timeline.js','utf8'),ctx);
vm.runInContext('animateMove=async move=>log.push("move"+move.id)',ctx);
const flush=()=>new Promise(setImmediate);
(async()=>{
  for(let run=0;run<2;run++) {
    log.length=0;let finished=false;
    const playback=vm.runInContext('playSequence()',ctx).then(()=>finished=true);
    await flush();assert(!finished,'opening hold missing from playback/export completion');
    assert.equal(timers.length,1);assert.equal(timers[0].ms,1250);
    assert(!log.includes('move1'),'move started before opening hold');
    assert(log.indexOf('music')<log.indexOf('delay'),'music start changed');
    if(run)assert(log.indexOf('reset')>=0&&log.indexOf('reset')<log.indexOf('delay'),'replay held final position');
    await vm.runInContext('playSequence()',ctx);assert.equal(timers.length,1,'double play created another timer');
    timers.shift().fn();await playback;
    assert.deepEqual(log.filter(x=>x.startsWith('move')),['move1','move2']);
    assert.equal(timers.length,0,'delay repeated between moves');
  }
  ctx.playbackConfig.initialDelayMs=0;
  await vm.runInContext('playSequence()',ctx);assert.equal(timers.length,0,'zero delay allocated a timer');
})().catch(e=>{console.error(e);process.exitCode=1;});
'''
        subprocess.run(['node','-e',script],cwd=ROOT,check=True)


if __name__=='__main__':unittest.main()
