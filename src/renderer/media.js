// Media system. Included inline by composition.py.
const memeVideo = document.getElementById("memeVideo");

let memeStarted = false;

const backgroundMusic = document.getElementById("backgroundMusic");

async function prepareDelayedMeme() {
    if (!memeVideo) return;
    // Prime playback in the Play gesture without emitting audio, then freeze
    // the first decoded frame. Later timeline triggers can play with audio.
    memeVideo.pause();
    memeVideo.currentTime = 0;
    memeVideo.muted = true;
    try {
        await memeVideo.play();
    } catch (error) {
        console.warn("Could not prepare meme video:", error);
    } finally {
        memeVideo.pause();
        memeVideo.currentTime = 0;
        memeVideo.volume = media.memeVolume;
        memeVideo.muted = false;
    }
    if (memeVideo.seeking) {
        await new Promise(resolve =>
            memeVideo.addEventListener("seeked", resolve, { once: true }));
    }
}

function startMemeVideo() {
    if (!memeVideo || memeStarted) return;
    memeStarted = true;
    memeVideo.volume = media.memeVolume;
    memeVideo.muted = false;
    memeVideo.currentTime = 0;
    memeVideo.play().catch(error => {
        console.warn("Could not play meme video:", error);
    });
}

function startBackgroundMusic() {
    if (!backgroundMusic) return;
    backgroundMusic.volume = media.musicVolume;
    backgroundMusic.currentTime = 0;
    backgroundMusic.play().catch(error => {
        console.warn("Could not play background music:", error);
    });
}
