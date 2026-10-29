// Small per-move cue/track scheduler. Renderers own their animation handles;
// this module observes timing, joins parallel work and releases observers.
const timelineScheduler = {
    listeners: new Set(),
    active: new Set(),
    now: () => typeof performance === "undefined" ? Date.now() : performance.now(),
    subscribe(listener) {
        this.listeners.add(listener);
        return () => this.listeners.delete(listener);
    },
    begin(move, plan) { return new MoveSchedule(move, plan); },
    emit(event) {
        for (const listener of this.listeners) {
            // A preview inspector must never interrupt the video renderer.
            try { listener(event); } catch (error) { console.warn("Cue observer failed", error); }
        }
    }
};

class MoveSchedule {
    constructor(move, plan) {
        this.move = move;
        this.plan = plan;
        this.start = timelineScheduler.now();
        this.cues = new Set();
        this.tracks = [];
        this.cleanups = new Set();
        this.cueHandlers = new Set();
        this.closed = false;
        timelineScheduler.active.add(this);
    }

    cue(cue) {
        if (this.closed || this.cues.has(cue)) return false;
        this.cues.add(cue);
        const time = timelineScheduler.now();
        const event = {cue, time, elapsed: time - this.start, move: this.move, plan: this.plan};
        // Rendering subscribers belong to this schedule. Join failures even
        // when a cue came from RAF, so finish() reports them and cleanup runs.
        for (const handler of this.cueHandlers) {
            try { handler(event); } catch (error) { this.track(Promise.reject(error)); }
        }
        timelineScheduler.emit(event);
        return true;
    }

    onCue(handler) {
        this.cueHandlers.add(handler);
        return () => this.cueHandlers.delete(handler);
    }

    track(task) {
        const promise = Promise.resolve(task);
        // Attach a handler now so a parallel failure cannot become unhandled
        // while the caller is awaiting the piece. finish() still propagates it.
        promise.catch(() => {});
        this.tracks.push(promise);
        return promise;
    }

    wait(duration) {
        if (!(duration > 0) || this.closed) return Promise.resolve();
        return new Promise(resolve => {
            const done = () => {
                clearTimeout(timer);
                this.cleanups.delete(done);
                resolve();
            };
            const timer = setTimeout(done, duration);
            this.cleanups.add(done);
        });
    }

    observeMotion({animation, contactOffset, duration}, callback) {
        // Observe the animation clock, not a wall-clock timeout. Pausing a piece
        // or cancelling it must not cause an early/late arrival accent.
        if (typeof requestAnimationFrame === "undefined") return () => {};
        let frame;
        let stopped = false;
        const stop = () => {
            stopped = true;
            if (frame !== undefined) cancelAnimationFrame(frame);
            this.cleanups.delete(stop);
        };
        const sample = () => {
            if (stopped || this.closed || animation.playState === "idle") return stop();
            if (animation.currentTime !== null && animation.currentTime >= duration * contactOffset) {
                stop();
                callback();
            } else {
                frame = requestAnimationFrame(sample);
            }
        };
        this.cleanups.add(stop);
        frame = requestAnimationFrame(sample);
        // onLand supplies the once-only fallback if no RAF samples the marker.
        animation.finished.then(stop, stop);
        return stop;
    }

    async finish() {
        // Cues may add a track while another is finishing (e.g. an arrival accent).
        let joined = 0;
        while (joined < this.tracks.length) {
            const batch = this.tracks.slice(joined);
            joined = this.tracks.length;
            await Promise.all(batch);
        }
    }

    close() {
        this.closed = true;
        this.cueHandlers.clear();
        for (const cleanup of [...this.cleanups]) cleanup();
        timelineScheduler.active.delete(this);
    }
}
