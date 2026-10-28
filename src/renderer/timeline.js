// Timeline system. Included inline by composition.py.
const playButton = document.getElementById("playButton");
let playing = false;
let hasPlayed = false;

function sleep(ms) {

    return new Promise(
        resolve => setTimeout(resolve, ms)
    );

}

// Timeline owns ordering; renderers own DOM updates and visual primitives.
async function animateMove(move) {
    clearMoveEffects();
    // Establish destination framing first; the piece may enter from offscreen.
    if (move.camera_directive) await camera.directMove(move);
    const brilliant = move.annotation === "!!";
    if (brilliant) await sleep(cameraConfig.brilliantPreHold);
    const landed = await animatePieceMove(move, () => {
        // Keep landing sound/check/meme ahead of promotion and the castling rook.
        playMoveSound(move);
        showCheckEffects(move);
        if (move.start_meme) startMemeVideo();
    });
    if (!landed) return;
    showMoveEffects(move);
    await sleep(move.pause * 1000 + (brilliant ? cameraConfig.brilliantPostHold : 0));
}

const timelineHandlers = {
    move: event => animateMove(event.move),
    meme: () => startMemeVideo(),
    camera: event => camera.apply(event.preset, event.from, event.to)
};

async function runTimeline(events) {
    for (const event of events) {
        const handler = timelineHandlers[event.type];
        if (!handler) throw new Error("Unknown timeline event: " + event.type);
        await handler(event);
    }
}

async function playSequence() {

    if (playing) return;

    playing = true;

    playButton.disabled = true;

    // Start with audio in the click gesture, before any asynchronous chess work.
    // The media element runs independently of every per-move pause.
    memeStarted = false;
    const memeReady = hasMemeTriggers ? prepareDelayedMeme() : null;
    if (!hasMemeTriggers) startMemeVideo();
    startBackgroundMusic();
    await Promise.all([prepareMoveAudio(), memeReady]);

    if (hasPlayed) {
        clearMoveEffects();
        resetPieces();
        camera.reset();
    }

    await runTimeline(timeline);
    await camera.finished;

    hasPlayed = true;
    playing = false;
    playButton.disabled = false;
    playButton.textContent = "Replay Sequence";

}
