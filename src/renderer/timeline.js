// Timeline system. Included inline by composition.py.
const playButton = document.getElementById("playButton");
let playing = false;
let hasPlayed = false;

// Timeline owns ordering; renderers own DOM updates and visual primitives.
async function animateMove(source, context) {
    const plan = buildMovePlan(source, context);
    const move = plan.move;
    const schedule = timelineScheduler.begin(move, plan);
    const reactions = reactionSystem.begin(move, schedule, plan.reactions);
    const lighting = lightingSystem.begin(move, schedule, plan.lighting);
    const unbindPieceMeme = pieceMemeSystem.bind(move, schedule, pieceBySquare[move.from]);
    try {
        clearMoveEffects();
        if (move.camera_directive && cameraConfig.enabled) {
            const transition = camera.directMove(move, plan.aggressive ? cameraConfig.aggressiveMargin : 0);
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
            if (!schedule.cue("contact")) return;
            if (plan.impulse) schedule.track(cameraMotion.impact(move, plan.impactStrength,
                plan.aggressive?.impactStrength ?? 1));
            if (plan.aggressive && !plan.aggressive.spinTurns)
                schedule.track(cameraMotion.aggressiveHit(move, plan.aggressive));
        };
        schedule.cue("launch");
        const landed = await animatePieceMove(move, () => {
            contact(); // Instant moves / missed RAF sample: cue once before settling.
            schedule.cue("settled");
            if (plan.aggressive?.spinTurns)
                schedule.track(cameraMotion.aggressiveHit(move, plan.aggressive));
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
        if(context)Object.assign(context,plan.nextContext);
    } catch (error) {
        pieceMemeSystem.reset();
        cameraMotion.reset();
        camera.reset();
        throw error;
    } finally {
        unbindPieceMeme();
        lighting.close();
        reactions.close();
        schedule.close();
    }
}

const timelineHandlers = {
    move: (event, context) => animateMove(event.move, context),
    meme: () => startMemeVideo(),
    camera: event => camera.apply(event.preset, event.from, event.to)
};

async function runTimeline(events) {
    const context = {shot:'J',focus:null};
    for (const event of events) {
        const handler = timelineHandlers[event.type];
        if (!handler) throw new Error("Unknown timeline event: " + event.type);
        await handler(event, context);
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
        const pieceAudioReady = pieceMemeConfig.enabled ? pieceMemeSystem.unlockAudio() : null;
        await Promise.all([prepareMoveAudio(), memeReady, pieceAudioReady]);

        if (pieceMemeConfig.enabled) await pieceMemeSystem.prepare();

        if (hasPlayed) {
            clearMoveEffects();
            resetPieces(false);
            camera.reset();
            cameraMotion.reset();
        }

        if (pieceMemeConfig.enabled) pieceMemeSystem.audioActive = true;
        if (pieceMemeConfig.initial) pieceMemeSystem.initialize();

        // Hold the starting position once per playback, after replay reset and
        // media preparation. The exporter awaits this promise as part of playback.
        if (playbackConfig.initialDelayMs > 0) {
            await new Promise(resolve => setTimeout(resolve, playbackConfig.initialDelayMs));
        }
        await runTimeline(timeline);
        // The exporter awaits playSequence(): include all transient tails.
        await Promise.all([camera.finished, cameraMotion.finished, reactionSystem.finished,
                           lightingSystem.finished, finishMoveEffects()]);
        if (pieceMemeConfig.enabled) await pieceMemeSystem.finishAll();
    } finally {
        pieceMemeSystem.reset();
        hasPlayed = true;
        playing = false;
        playButton.disabled = false;
        playButton.textContent = "Replay Sequence";
    }

}
