// Transient camera motion never writes #board or the persistent camera target.
// Each named wrapper owns one transform so independent tracks can overlap.
const cameraMotion = {
    identity: "translate(0px,0px) rotate(0deg) scale(1)",
    owners: {
        reframe: document.getElementById("cameraReframe"),
        impact: document.getElementById("cameraImpact"),
        hero: document.getElementById("cameraHero")
    },
    tracks: new Map(),

    get enabled() {
        return cameraConfig.enabled && cameraConfig.transient?.enabled;
    },

    // A caller can await this once at sequence end. Tracks added while it waits
    // are included; cancellation resolves normally and cannot leave a waiter stuck.
    get finished() {
        return this.finishAll();
    },

    async finishAll() {
        while (this.tracks.size) {
            await Promise.all(Array.from(this.tracks.values(), track => track.finished));
        }
    },

    cancel(name) {
        const track = this.tracks.get(name);
        if (track) {
            this.tracks.delete(name);
            track.animation.cancel();
        }
        if (this.owners[name]) this.owners[name].style.transform = this.identity;
    },

    reset() {
        for (const name of Object.keys(this.owners)) this.cancel(name);
    },

    // No random state: replay and exports receive the same directional accents.
    direction(move) {
        const from = move?.from ? squareToCoords(move.from) : {x: 3.5, y: 3.5};
        const to = move?.to ? squareToCoords(move.to) : from;
        const dx = to.x - from.x, dy = to.y - from.y;
        const length = Math.hypot(dx, dy);
        return {x: length ? dx / length : 0, y: length ? dy / length : 0,
                turn: Math.sign(dx || -dy || (to.x - 3.5) || 1)};
    },

    frame(offset, x = 0, y = 0, zoom = 1, rotation = 0, easing = "linear") {
        return {offset, transform: "translate(" + x + "px," + y + "px) rotate(" +
            rotation + "deg) scale(" + zoom + ")", easing};
    },

    play(name, frames, duration) {
        if (!this.enabled) return Promise.resolve();
        this.cancel(name);
        const owner = this.owners[name];
        if (!owner || !Number.isFinite(duration) || duration <= 0) return Promise.resolve();
        const animation = owner.animate(frames, {duration, easing: "linear", fill: "both"});
        const track = {animation, finished: null};
        track.finished = animation.finished.catch(error => {
            if (error.name !== "AbortError") throw error;
        }).finally(() => {
            // A canceled predecessor must not erase a replacement on this owner.
            if (this.tracks.get(name) === track) {
                this.tracks.delete(name);
                owner.style.transform = this.identity;
                animation.cancel();
            }
        });
        this.tracks.set(name, track);
        return track.finished;
    },

    reframe(move, duration) {
        if (!this.enabled || !move.camera_directive) return Promise.resolve();
        if (!Number.isFinite(duration) || duration <= 0) return Promise.resolve();
        const config = cameraConfig.transient.reframe;
        const direction = this.direction(move);
        const total = duration + config.settleDuration;
        const accent = (offset, amount, zoom) => this.frame(offset,
            direction.x * config.translation * amount,
            direction.y * config.translation * amount, 1 + config.zoom * zoom,
            direction.turn * config.rotation * amount, cameraConfig.transient.easing);
        return this.play("reframe", [
            accent(0, 0, 0),
            accent(duration * config.peak / total, 1, 1),
            accent(duration / total, -config.rebound, config.rebound),
            accent(1, 0, 0)
        ], total);
    },

    // Stage 2 exposes an explicit close-shot accent, not automatic capture logic.
    impact(move) {
        if (!this.enabled || move.camera_directive !== "L") return Promise.resolve();
        const config = cameraConfig.transient.impact;
        const direction = this.direction(move);
        const accent = (offset, amount) => this.frame(offset,
            direction.x * config.translation * amount,
            direction.y * config.translation * amount, 1 + config.zoom * Math.abs(amount),
            direction.turn * config.rotation * amount, cameraConfig.transient.easing);
        return this.play("impact", [
            accent(0, 0), accent(config.peakAt, 1), accent(config.reboundAt, -config.rebound),
            accent(config.settleAt, config.settle), accent(1, 0)
        ], config.duration);
    },

    heroHold(move, duration) {
        if (!this.enabled || !Number.isFinite(duration) || duration <= 0) return Promise.resolve();
        const config = cameraConfig.transient.hero;
        const direction = this.direction(move);
        const count = Math.max(2, Math.ceil(duration / config.sampleInterval));
        const frames = [];
        for (let index = 0; index <= count; index++) {
            const offset = index / count;
            // Explicit identity endpoints avoid floating-point residue. The
            // envelope bounds every drift/pulse and fades them back to identity.
            if (index === 0 || index === count) {
                frames.push(this.frame(offset));
                continue;
            }
            const elapsed = offset * duration;
            const envelope = Math.sin(Math.PI * offset);
            const drift = elapsed / config.driftPeriod * 2 * Math.PI;
            const pulse = (1 - Math.cos(elapsed / config.pulsePeriod * 2 * Math.PI)) / 2;
            frames.push(this.frame(offset,
                Math.sin(drift) * config.translation * envelope * direction.turn,
                (Math.cos(drift) - 1) / 2 * config.translation * envelope,
                1 + pulse * config.zoom * envelope,
                Math.sin(drift) * config.rotation * envelope * direction.turn));
        }
        return this.play("hero", frames, duration);
    }
};
