// Run after generation: node tests/test_sequence_audio.cjs
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const path = require('node:path');
const html = fs.readFileSync(path.join(__dirname, '../output/sequence_demo.html'), 'utf8');
const script = html.match(/<script>([\s\S]*?)<\/script>/)[1];
const started = [];
let failAudio = false;
const audioElements = [];
class Audio {
    constructor() {
        this.currentTime = 0;
        this.events = new Map();
        audioElements.push(this);
    }
    addEventListener(name, fn) { this.events.set(name, fn); }
    removeEventListener(name) { this.events.delete(name); }
    load() {
        assert.equal(this.preload, 'auto');
        const file = path.join(__dirname, '../output', this.src);
        assert(fs.statSync(file).size > 0, 'local sound must exist');
    }
    pause() {}
    async play() {
        if (failAudio) throw Error('audio disabled');
        if (!this.muted) {
            assert.equal(this.currentTime, 0, 'rewind before every playback');
            started.push(this.src);
            this.currentTime = 0.2;
        }
    }
}
class Element {
    constructor() { this.style = {}; this.dataset = {}; this.transitions = []; }
    appendChild() {}
    remove() { this.removed = true; }
    setAttribute() {}
    animate() {}
    getAnimations() { return this.transitions; }
}
const elements = {};
const sandbox = vm.createContext({
    assert, started, Element, console: { ...console, warn() {} },
    Audio, clearTimeout, setTimeout: (fn, ms) => ms === 500 ? fn() : setTimeout(fn, ms),
    document: {
        getElementById: id => elements[id] ||= new Element(),
        createElement: () => new Element()
    }
});
vm.runInContext(script, sandbox);
async function main() {
    await vm.runInContext(`(async () => {
        let ready = false;
        const preparation = prepareMoveAudio().then(() => ready = true);
        await Promise.resolve(); await Promise.resolve();
        assert.equal(ready, false, 'wait for every file to preload');
        const files = Array.from(moveAudio.values());
        files.slice(0,4).forEach(audio => audio.events.get('canplaythrough')());
        await Promise.resolve(); await Promise.resolve();
        assert.equal(ready, false, 'last file must also load');
        files[4].events.get('canplaythrough')();
        await preparation;
        await prepareMoveAudio();
        assert.equal(moveAudio.size, 5);
        assert.equal(started.length, 0, 'unlock must be silent');
        assert.equal(moves.map(moveSoundKind).join(','), 'castle,promotion,capture,check,move');
        const cases = [
            [{}, 'move'], [{capture:'d5'}, 'capture'], [{check:true}, 'check'],
            [{rook_from:'h1',rook_to:'f1'}, 'castle'], [{promotion:'wQ.svg'}, 'promotion'],
            [{capture:'h8',check:true}, 'check'],
            [{rook_from:'h1',rook_to:'f1',check:true}, 'check'],
            [{promotion:'wQ.svg',capture:'h8',check:true}, 'promotion']
        ];
        for (const [metadata, kind] of cases) {
            assert.equal(moveSoundKind(metadata), kind);
            const piece = new Element();
            let finishX, finishY;
            piece.transitions = [
                {transitionProperty:'left',finished:new Promise(r => finishX=r)},
                {transitionProperty:'top',finished:new Promise(r => finishY=r)}
            ];
            pieceBySquare = {e2:piece};
            const captured = new Element();
            if (metadata.capture) pieceBySquare[metadata.capture] = captured;
            let finishRook;
            if (metadata.rook_from) {
                const rook = new Element();
                rook.transitions = [{transitionProperty:'left',finished:new Promise(r => finishRook=r)}];
                pieceBySquare[metadata.rook_from] = rook;
            }
            const before = started.length;
            const task = animateMove({from:'e2',to:'e4',...metadata});
            assert.equal(started.length, before, 'must not sound before landing');
            finishX();
            await Promise.resolve(); await Promise.resolve();
            assert.equal(started.length, before, 'must wait for both axes');
            finishY();
            // Drain the landing continuation; rook completion stays pending.
            for (let i=0;i<8;i++) await Promise.resolve();
            assert.equal(started.length, before+1);
            assert.equal(started.at(-1), '../assets/sfx/' + kind + '.webm');
            if (finishRook) finishRook();
            await task;
            assert.equal(started.length, before+1, 'one sound, including castling');
            assert.equal(pieceBySquare.e4, piece);
            if (metadata.capture) assert(captured.removed);
            if (metadata.promotion) assert.equal(piece.src, '../assets/pieces/wQ.svg');
        }
        // No transition (e.g. disabled motion) must finish without hanging.
        await slidePieceToSquare(new Element(), 'a8');
        // Run the actual sample twice through the Play button flow.
        pieceBySquare = {};
        createPieces();
        const start = started.length;
        await playSequence();
        await playSequence();
        assert.equal(started.slice(start).map(src => src.split('/').at(-1)).join(','),
            'castle.webm,promotion.webm,capture.webm,check.webm,move.webm,'
            + 'castle.webm,promotion.webm,capture.webm,check.webm,move.webm');
        assert.equal(playing, false);
        assert.equal(playButton.disabled, false);
    })()`, sandbox);
    assert.equal(audioElements.length, 5, 'reuse audio elements');
    failAudio = true;
    await vm.runInContext('prepareMoveAudio()', sandbox); // Must not reject.
    await vm.runInContext('playMoveSound({})', sandbox);
    console.log('PASS: local files, preload gate, silent unlock, sound priority, landing timing, rewind, test position, replay, and audio rejection handling.');
}
main().catch(error => { console.error(error); process.exitCode = 1; });
