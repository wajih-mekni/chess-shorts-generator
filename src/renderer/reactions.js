// Pure metadata -> primitive bindings. Stage 6 can replace this decision without
// changing actor lifetime or rendering. Explicit NONE disables either channel.
function resolveReactions(move) {
    const select = (channel, eligible) => {
        const override = move[channel + "_reaction"];
        const name = override ?? (reactionConfig.profile === "REFERENCE"
            ? reactionConfig.defaults[channel] : "NONE");
        if (name === "NONE") return null;
        const preset = reactionConfig.presets[name];
        if (!preset || preset.kind !== channel) throw new Error("Invalid " + channel + " reaction: " + name);
        return eligible ? {name, preset} : null;
    };
    return {capture: select("capture", Boolean(move.capture)),
            king: select("king", Boolean(move.check && move.checked_king))};
}

function reactionDirection(fromSquare, toSquare) {
    const from = squareToCoords(fromSquare), to = squareToCoords(toSquare);
    const dx = to.x - from.x, dy = to.y - from.y, length = Math.hypot(dx, dy);
    return {x: length ? dx / length : 0, y: length ? dy / length : 0,
            turn: Math.sign(dx || -dy || 1)};
}

function reactionTransform(direction, distance, rotation, scale) {
    return "translate(" + direction.x * distance * squareSize + "px," +
        direction.y * distance * squareSize + "px) rotate(" +
        direction.turn * rotation + "deg) scale(" + scale + ")";
}

function captureReactionKeyframes(direction, preset) {
    return [
        {offset: 0, transform: reactionTransform(direction, 0, 0, 1), opacity: 1},
        {offset: preset.midpoint,
         transform: reactionTransform(direction, preset.distance * preset.midDistance,
                                      preset.rotation * preset.midRotation, preset.midScale), opacity: 1},
        {offset: 1, transform: reactionTransform(direction, preset.distance, preset.rotation,
                                               preset.endScale), opacity: 0}
    ];
}

const reactionSystem = {
    sessions: new Set(), tracks: new Set(), ghosts: new Set(),
    begin(move, schedule, plan = resolveReactions(move)) { return new ReactionSession(move, schedule, plan); },
    reset() { for (const session of [...this.sessions]) session.cancel(); },
    get finished() { return this.finishAll(); },
    async finishAll() {
        while (this.tracks.size) await Promise.all([...this.tracks]);
    }
};

class ReactionSession {
    constructor(move, schedule, plan) {
        this.move = move;
        this.schedule = schedule;
        this.plan = plan;
        this.animations = new Set();
        this.victim = null;
        this.king = plan.king ? pieceBySquare[move.checked_king] : null;
        this.captureStarted = false;
        this.kingStarted = false;
        this.kingUsesRook = Boolean(move.rook_to && move.checker_squares?.includes(move.rook_to));
        this.recoveryStarted = false;
        this.cancelled = false;
        this.windup = Promise.resolve();
        reactionSystem.sessions.add(this);
    }

    track(promise) {
        reactionSystem.tracks.add(promise);
        const remove = () => reactionSystem.tracks.delete(promise);
        promise.then(remove, remove);
        return this.schedule.track(promise);
    }

    retainVictim(actor) {
        this.victim = actor;
        actor.dataset.visualOnly = "true";
        // Keep the short exit readable when the arriving attacker overlaps it.
        // This actor is always retired; it never returns to normal occupancy.
        actor.style.zIndex = String(reactionConfig.captureVisualLayer);
        reactionSystem.ghosts.add(actor);
    }

    retireVictim() {
        if (!this.victim) return;
        reactionSystem.ghosts.delete(this.victim);
        renderedPieces.delete(this.victim);
        this.victim.remove();
        this.victim = null;
    }

    // Only the reserved reaction element receives transforms/opacity.
    animate(actor, frames, duration, easing, onFinish = () => {}) {
        if (this.cancelled) return Promise.resolve();
        const animation = actor.reaction.animate(frames, {duration, easing, fill: "both"});
        this.animations.add(animation);
        const task = animation.finished.then(() => {
            if (!this.cancelled) onFinish();
        }, error => {
            if (error.name !== "AbortError") throw error;
        }).finally(() => {
            this.animations.delete(animation);
            animation.cancel();
        });
        return this.track(task);
    }

    observeMotion(info, rook = false) {
        const observe = (selection, callback) => {
            if (!selection) return;
            const offset = Math.max(0, info.contactOffset - selection.preset.lead / info.duration);
            this.schedule.observeMotion({...info, contactOffset: offset}, callback);
        };
        if (!rook) observe(this.plan.capture, () => this.startCapture());
        if (rook === this.kingUsesRook) observe(this.plan.king, () => this.startKing());
    }

    startCapture() {
        if (this.cancelled || this.captureStarted || !this.victim || !this.plan.capture) return;
        this.captureStarted = true;
        this.schedule.cue("captureReaction");
        const preset = this.plan.capture.preset;
        // Incoming travel direction also works for en passant, whose victim
        // square differs from the attacker's destination.
        const direction = reactionDirection(this.move.from, this.move.to);
        const task = this.animate(this.victim, captureReactionKeyframes(direction, preset),
                                  preset.duration, preset.easing);
        // Cancelled visual exits also retire the ghost, never revive occupancy.
        this.track(task.finally(() => this.retireVictim()));
    }

    startKing() {
        if (this.cancelled || this.kingStarted || !this.king || !this.plan.king) return;
        this.kingStarted = true;
        this.schedule.cue("kingAnticipation");
        const preset = this.plan.king.preset;
        // A discovered check comes from the revealed checker, not the moving actor.
        const checkers = this.move.checker_squares || [];
        const source = checkers.includes(this.move.to) ? this.move.to : (checkers[0] || this.move.to);
        const direction = reactionDirection(source, this.move.checked_king);
        const peak = reactionTransform(direction, preset.distance, preset.rotation, preset.scale);
        this.windup = this.animate(this.king, [{transform: "none"}, {transform: peak}],
            preset.anticipation, preset.easing, () => {
                // Hold until actual attacker settlement, including a paused attacker.
                this.king.reaction.style.transform = peak;
            });
    }

    settled() {
        if (this.cancelled) return;
        this.startCapture(); // Fallback for instant travel / an unsampled cue.
        if (!this.kingUsesRook) this.recoverKing();
    }

    completed() {
        if (this.kingUsesRook) this.recoverKing();
    }

    recoverKing() {
        if (this.cancelled || this.recoveryStarted) return;
        this.startKing();
        if (!this.kingStarted) return;
        this.recoveryStarted = true;
        this.track(this.windup.then(() => {
            if (this.cancelled) return;
            this.schedule.cue("kingRecovery");
            const preset = this.plan.king.preset;
            const from = getComputedStyle(this.king.reaction).transform;
            return this.animate(this.king, [{transform: from}, {transform: "none"}],
                preset.recovery, preset.easing, () => this.clearKing());
        }));
    }

    clearKing() {
        if (this.king) this.king.reaction.style.transform = "";
    }

    cancel() {
        this.cancelled = true;
        for (const animation of this.animations) animation.cancel();
        this.retireVictim();
        this.clearKing();
        reactionSystem.sessions.delete(this);
    }

    close() {
        // The scheduler has joined all exits/recoveries before normal close.
        this.cancel();
    }
}
