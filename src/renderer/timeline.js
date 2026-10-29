// Timeline system. Included inline by composition.py.
const playButton = document.getElementById("playButton");
let playing = false;
let hasPlayed = false;

// Timeline owns ordering; renderers own DOM updates and visual primitives.
async function animateMove(move) {
    const plan = buildMovePlan(move);
    const schedule = timelineScheduler.begin(move, plan);
    const reactions = reactionSystem.begin(move, schedule, plan.reactions);
    const lighting = lightingSystem.begin(move, schedule, plan.lighting);
    try {
        clearMoveEffects();
        if (move.camera_directive && cameraConfig.enabled) {
            const transition = camera.directMove(move);
            schedule.cue("cameraStart");
            const cameraTrack = schedule.track(Promise.resolve(transition).then(() => {
                schedule.cue("cameraEnd");
            }));
            if (plan.serialCamera) await cameraTrack;
            else schedule.track(cameraMotion.reframe(move, plan.cameraDuration));
        }
        // REFERENCE gives the camera a small optional lead, rather than waiting
        // for the shot to finish. LEGACY preserves camera -> prehold -> piece.
        if (plan.pieceDelay > 0) await schedule.wait(plan.pieceDelay);
        const contact = () => {
            if (schedule.cue("contact") && plan.impulse) {
                schedule.track(cameraMotion.impact(move));
            }
        };
        schedule.cue("launch");
        const landed = await animatePieceMove(move, () => {
            contact(); // Instant moves / missed RAF sample: cue once before settling.
            schedule.cue("settled");
            reactions.settled();
            // Preserve the exact existing landing boundary, including castling:
            // audio/check/meme occur before promotion or the rook's movement.
            playMoveSound(move);
            showCheckEffects(move);
            if (move.start_meme) startMemeVideo();
        }, motionEvent => {
            schedule.observeMotion(motionEvent, contact);
            reactions.observeMotion(motionEvent);
        }, plan.reactions.capture ? actor => reactions.retainVictim(actor) : null,
           motionEvent => reactions.observeMotion(motionEvent, true));
        if (landed) {
            reactions.completed();
            showMoveEffects(move);
            schedule.cue("holdStart");
            if (plan.hero) schedule.track(cameraMotion.heroHold(move, plan.holdDuration));
            await schedule.wait(plan.holdDuration);
            schedule.cue("holdEnd");
        }
        await schedule.finish();
        schedule.cue("complete");
    } catch (error) {
        cameraMotion.reset();
        camera.reset();
        throw error;
    } finally {
        lighting.close();
        reactions.close();
        schedule.close();
    }
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

    try {
        // Start with audio in the click gesture, before asynchronous chess work.
        // Media continues independently of per-move pauses and camera tracks.
        memeStarted = false;
        const memeReady = hasMemeTriggers ? prepareDelayedMeme() : null;
        if (!hasMemeTriggers) startMemeVideo();
        startBackgroundMusic();
        await Promise.all([prepareMoveAudio(), memeReady]);

        if (hasPlayed) {
            clearMoveEffects();
            resetPieces();
            camera.reset();
            cameraMotion.reset();
        }

        await runTimeline(timeline);
        // The exporter awaits playSequence(): include all transient tails.
        await Promise.all([camera.finished, cameraMotion.finished, reactionSystem.finished,
                           lightingSystem.finished, finishMoveEffects()]);
    } finally {
        hasPlayed = true;
        playing = false;
        playButton.disabled = false;
        playButton.textContent = "Replay Sequence";
    }

}
