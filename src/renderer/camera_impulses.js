// Transient camera motion never writes #board or the persistent camera target.
// Each named wrapper owns one transform so independent tracks can overlap.
const cameraMotion = {
    identity: "translate(0px,0px) rotate(0deg) scale(1)",
    owners: {
        aggressive: document.getElementById("cameraAggressive"),
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
            track.cancelReturn?.();
        }
        if (this.owners[name]) {
            this.owners[name].style.transform = this.identity;
            if (name === 'aggressive') this.owners[name].classList.remove('aggressive-active');
        }
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
        if (name === 'aggressive') owner.classList.add('aggressive-active');
        const animation = owner.animate(frames, {duration, easing: "linear", fill: "both"});
        const track = {animation, finished: null};
        track.finished = animation.finished.catch(error => {
            if (error.name !== "AbortError") throw error;
        }).finally(() => {
            // A canceled predecessor must not erase a replacement on this owner.
            if (this.tracks.get(name) === track) {
                this.tracks.delete(name);
                owner.style.transform = this.identity;
                if (name === 'aggressive') owner.classList.remove('aggressive-active');
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

    // Existing close-shot accent; the director can select a bounded intensity.
    impact(move, strength = null, multiplier = 1) {
        if (!this.enabled || (strength === null && move.camera_directive !== "L")) return Promise.resolve();
        const intensity = Math.max(0, Math.min(1, strength ?? 1)) * multiplier;
        const config = cameraConfig.transient.impact;
        const direction = this.direction(move);
        const accent = (offset, amount) => this.frame(offset,
            direction.x * config.translation * amount * intensity,
            direction.y * config.translation * amount * intensity, 1 + config.zoom * Math.abs(amount) * intensity,
            direction.turn * config.rotation * amount * intensity, cameraConfig.transient.easing);
        return this.play("impact", [
            accent(0, 0), accent(config.peakAt, 1), accent(config.reboundAt, -config.rebound),
            accent(config.settleAt, config.settle), accent(1, 0)
        ], config.duration);
    },

    // Deterministic bass-drop oscillation. No timers or RAF; the common track
    // owner handles completion, cancellation, replacement and exact identity.
    aggressiveFrames(move, config) {
        const direction = this.direction(move).turn;
        const count = Math.ceil(Math.max(config.oscillations * 16, config.shakeCycles * 8));
        const firstPeak = 1 / (4 * config.oscillations);
        return Array.from({length: count + 1}, (_, index) => {
            const t = index / count;
            if (index === 0 || index === count) return this.frame(t);
            const decay = Math.min(1, Math.pow((1-t)/(1-firstPeak), config.damping));
            const attack = Math.min(1, t/firstPeak);
            const envelope = attack * decay;
            const rock = Math.sin(2*Math.PI*config.oscillations*t) * decay;
            const shake = Math.sin(2*Math.PI*config.shakeCycles*t) * envelope;
            return this.frame(t, shake*config.shakeTranslation*direction,
                Math.cos(2*Math.PI*config.shakeCycles*t)*config.shakeTranslation*envelope,
                1+config.zoom*envelope, direction*config.rotation*rock);
        });
    },

    // One animation owns both phases. Keep explicit rotate(deg) functions and
    // carry whole turns through every rocking frame; never decompose a matrix.
    veryAggressiveDuration(config) {
        return Math.max(config.spinZoomDuration ?? config.spinDuration,
            config.spinDuration-config.spinOverlap+config.duration);
    },

    veryAggressiveFrames(move, config) {
        const rockStart = config.spinDuration - config.spinOverlap;
        const total = this.veryAggressiveDuration(config);
        const zoomDuration = config.spinZoomDuration ?? config.spinDuration;
        const turns = 360 * config.spinTurns * config.spinDirection;
        const rocks = this.aggressiveFrames(move, config).map(frame => {
            const values = frame.transform.match(/[-+]?(?:\d*\.)?\d+(?:e[-+]?\d+)?/gi).map(Number);
            return {time: rockStart + frame.offset * config.duration, values};
        });
        const times = new Set([0, config.spinDuration, rockStart, total,
            zoomDuration, zoomDuration * config.spinPunchAt, zoomDuration * config.spinRecoilAt]);
        // Include both original rocking keyframes and spin samples. The rocking
        // waveform remains the existing one, with a short overlapping handoff.
        rocks.forEach(frame => times.add(frame.time));
        const samples = Math.ceil(config.spinDuration / config.spinSampleInterval);
        for (let i=0; i<=samples; i++) times.add(i/samples*config.spinDuration);
        const lerp = (a,b,t) => a+(b-a)*t;
        const smooth = t => t*t*(3-2*t);
        const rockAt = time => {
            if (time <= rockStart) return [0,0,0,1];
            const right = rocks.findIndex(frame => frame.time >= time);
            if (right <= 0) return rocks.at(-1).values;
            const a=rocks[right-1], b=rocks[right];
            return a.values.map((value,i)=>lerp(value,b.values[i],(time-a.time)/(b.time-a.time)));
        };
        return [...times].sort((a,b)=>a-b).map(time => {
            const t = Math.min(1, time/config.spinDuration);
            const rotation = t===1 ? turns : turns*smooth(t);
            const z = Math.min(1, time/zoomDuration);
            let zoom;
            if(z<config.spinPunchAt) zoom=lerp(1,config.spinZoomIn,smooth(z/config.spinPunchAt));
            else if(z<config.spinRecoilAt) zoom=lerp(config.spinZoomIn,config.spinZoomHold,
                smooth((z-config.spinPunchAt)/(config.spinRecoilAt-config.spinPunchAt)));
            else zoom=lerp(config.spinZoomHold,config.spinZoomRecoil,
                smooth((z-config.spinRecoilAt)/(1-config.spinRecoilAt)));
            // Blend residual recoil into the rocking instead of stopping at identity.
            if(time>zoomDuration) zoom=lerp(config.spinZoomRecoil,1,
                smooth(Math.min(1,(time-zoomDuration)/Math.max(1,Math.min(config.spinOverlap,total-zoomDuration)))));
            if(time===total) zoom=1;
            const radians=rotation*Math.PI/180;
            // A rotated square requires |cos|+|sin| coverage (sqrt(2) at 45°).
            // The existing circumradius backing also covers tall/crop viewports.
            const safety = t===1 ? 1 : Math.abs(Math.cos(radians))+Math.abs(Math.sin(radians));
            const [x,y,rock,scale] = rockAt(time);
            return this.frame(time/total,x,y,zoom*safety*scale,rotation+rock);
        });
    },

    aggressiveHit(move, config) {
        if (config.spinTurns) {
            const done = this.play('aggressive', this.veryAggressiveFrames(move, config),
                this.veryAggressiveDuration(config));
            const track = this.tracks.get('aggressive');
            if (track && config.spinReturnWide)
                return Promise.all([done, camera.returnWideDuringSpin(track, config)]);
            return done;
        }
        return this.play('aggressive', this.aggressiveFrames(move, config), config.duration);
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
