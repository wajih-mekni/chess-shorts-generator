// Recipe choice is explicit or ordinary piece-type selection, never tactical
// event detection. The legacy branch retains the original keyframes verbatim.
function resolvePieceMotion(move) {
    let name = move.choreography_preset;
    if (!name && !move.animation_preset && choreographyConfig.profile === "REFERENCE") {
        name = choreographyConfig.ordinary[move.piece_kind] || "LIFT_MOVE";
    }
    if (name && name !== "LEGACY") {
        const preset = choreographyConfig.presets[name];
        if (!preset) throw new Error("Unknown choreography preset: " + name);
        const contactOffset = preset.kind === "spin"
            ? (preset.launch + preset.hang + preset.finish) / preset.duration : preset.arrivalAt;
        return {kind: "choreography", name, preset, duration: preset.duration, contactOffset};
    }
    name = move.animation_preset || motion.defaultPreset;
    const preset = motion.presets[name];
    if (!preset) throw new Error("Unknown movement preset: " + name);
    const frames = pieceMoveKeyframes({x: 0, y: 0}, {x: squareSize, y: 0}, preset);
    return {kind: "legacy", name, preset, duration: preset.duration,
            contactOffset: frames[frames.length - 2].offset};
}

// Independent outputs: travel writes only left/top; deformation writes only
// the inner choreography transform. Neither touches camera or reaction owners.
function choreographyKeyframes(from, to, preset) {
    const dx = to.x - from.x, dy = to.y - from.y;
    const distance = Math.hypot(dx, dy);
    const direction = Math.sign(dx || -dy || 1) * preset.direction;
    const overshoot = Math.min(squareSize * preset.overshoot, distance * preset.distanceLimit);
    const clamp = value => Math.max(0, Math.min(7 * squareSize, value));
    const arrival = {x: clamp(to.x + (distance ? dx / distance * overshoot : 0)),
                     y: clamp(to.y + (distance ? dy / distance * overshoot : 0))};
    const sweepX = distance ? -dy / distance * preset.sweep * squareSize : 0;
    const sweepY = distance ? dx / distance * preset.sweep * squareSize : 0;
    const at = progress => ({x: from.x + dx * progress, y: from.y + dy * progress});
    const travel = (offset, point, easing) => ({offset, left: point.x + "px", top: point.y + "px", easing});
    const shape = (offset, lift, scale, rotation, easing) => ({offset,
        transform: "translate(" + sweepX * lift + "px," +
            (sweepY - preset.lift * squareSize) * lift + "px) rotate(" +
            direction * rotation + "deg) scale(" + scale + ")", easing});
    if (preset.kind === "spin") {
        const inverse = preset.launch / preset.duration;
        const release = (preset.launch + preset.hang) / preset.duration;
        const contact = (preset.launch + preset.hang + preset.finish) / preset.duration;
        return {duration: preset.duration, contactOffset: contact,
            travel: [travel(0, from, preset.launchEasing),
                     travel(inverse, at(preset.hangProgress), "linear"),
                     travel(release, at(preset.hangProgress), preset.finishEasing),
                     travel(contact, arrival, preset.settleEasing), travel(1, to, "linear")],
            deformation: [shape(0, 0, 1, 0, preset.launchEasing),
                          shape(inverse, 1, preset.scale, 180, "linear"),
                          shape(release, 1, preset.scale, 180, preset.finishEasing),
                          shape(contact, 0, 1 + (preset.scale - 1) * preset.arrivalScale,
                                360 + preset.rotation, preset.settleEasing),
                          // 360 is identity. Do not animate backwards from 360 to 0!
                          shape(1, 0, 1, 360, "linear")]};
    }
    return {duration: preset.duration, contactOffset: preset.arrivalAt,
        travel: [travel(0, from, preset.launchEasing),
                 travel(preset.peakAt, at(preset.peakProgress), preset.easing),
                 travel(preset.arrivalAt, arrival, preset.settleEasing), travel(1, to, "linear")],
        deformation: [shape(0, 0, 1, 0, preset.launchEasing),
                      shape(preset.peakAt, 1, preset.scale, preset.rotation, preset.easing),
                      shape(preset.arrivalAt, 0, 1 + (preset.scale - 1) * preset.arrivalScale,
                            -preset.rotation * preset.rotationRebound, preset.settleEasing),
                      shape(1, 0, 1, 0, "linear")]};
}

async function animateChoreographedPieceToSquare(element, square, name, onMotion = () => {}) {
    const preset = choreographyConfig.presets[name];
    if (!preset) throw new Error("Unknown choreography preset: " + name);
    if (!element.choreography) throw new Error("Choreography requires a layered piece actor");
    const target = squareToCoords(square);
    const from = {x: parseFloat(element.style.left) || 0, y: parseFloat(element.style.top) || 0};
    const to = {x: target.x * squareSize, y: target.y * squareSize};
    if (preset.duration <= 0 || (from.x === to.x && from.y === to.y)) {
        placePiece(element, square);
        return;
    }
    const frames = choreographyKeyframes(from, to, preset);
    const animations = [];
    const previousZ = element.style.zIndex;
    element.style.zIndex = "6";
    try {
        const options = {duration: frames.duration, easing: "linear", fill: "both"};
        const travel = element.animate(frames.travel, options);
        animations.push(travel);
        const deformation = element.choreography.animate(frames.deformation, options);
        animations.push(deformation);
        // Both tracks use the same document timeline start, including on a busy frame.
        const start = document.timeline.currentTime;
        if (start !== null) animations.forEach(animation => animation.startTime = start);
        const finished = Promise.all(animations.map(animation => animation.finished));
        finished.catch(() => {});
        onMotion({animation: travel, animations, duration: frames.duration,
                  contactOffset: frames.contactOffset});
        await finished; // Land only after BOTH travel and deformation have settled.
        placePiece(element, square);
    } finally {
        animations.forEach(animation => animation.cancel());
        element.style.zIndex = previousZ;
    }
}
