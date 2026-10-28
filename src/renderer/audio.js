// Audio system. Included inline by composition.py.
// Reuse five local audio elements. Begin loading as soon as the page opens.
const moveAudio = new Map();
const audioReady = [];
for (const kind of ["move", "capture", "check", "castle", "promotion"]) {
    const audio = new Audio();
    audio.preload = "auto";
    audio.src = "../assets/sfx/" + kind + ".webm";
    moveAudio.set(kind, audio);
    audioReady.push(new Promise(resolve => {
        const finish = (ready) => {
            clearTimeout(timeout);
            audio.removeEventListener("canplaythrough", loaded);
            audio.removeEventListener("error", failed);
            if (!ready) console.warn("Could not preload chess sound:", audio.src);
            resolve(ready);
        };
        const loaded = () => finish(true);
        const failed = () => finish(false);
        const timeout = setTimeout(failed, 15000);
        audio.addEventListener("canplaythrough", loaded, { once: true });
        audio.addEventListener("error", failed, { once: true });
        audio.load();
    }));
}

async function prepareMoveAudio() {
    // Start muted playback on every element synchronously in the Play click
    // gesture, then pause/reset. This unlocks later landing-triggered playback.
    const unlock = Array.from(moveAudio.values(), async audio => {
        audio.muted = true;
        try {
            await audio.play();
        } catch (error) {
            console.warn("Could not unlock chess audio:", audio.src, error);
        } finally {
            audio.pause();
            audio.currentTime = 0;
            audio.muted = false;
        }
    });
    await Promise.all([...audioReady, ...unlock]);
}

function moveSoundKind(move) {
    // One sound per landing, even for captures/promotions that also give check.
    if (move.promotion) return "promotion";
    if (move.check) return "check";
    if (move.rook_from && move.rook_to) return "castle";
    if (move.capture) return "capture";
    return "move";
}

function playMoveSound(move) {
    const audio = moveAudio.get(moveSoundKind(move));
    if (!audio) return;
    // Always rewind, including consecutive uses of the same sound and replay.
    audio.pause();
    audio.currentTime = 0;
    audio.play().catch(error => {
        console.warn("Could not play chess sound:", audio.src, error);
    });
}
