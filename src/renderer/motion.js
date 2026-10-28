// Visual motion is separate from chess coordinates and timeline ordering.
function pieceMoveKeyframes(from, to, preset) {
    const dx = to.x - from.x;
    const dy = to.y - from.y;
    const distance = Math.hypot(dx, dy);
    const overshoot = Math.min(squareSize * preset.overshoot, distance * 0.08);
    const rotation = Math.sign(dx || -dy) * preset.rotation;
    const edge = squareSize * 7;
    const clamp = value => Math.max(0, Math.min(edge, value));
    const frame = (offset, x, y, scale, angle, blur, easing) => ({
        offset, left: x + "px", top: y + "px",
        transform: "rotate(" + angle + "deg) scale(" + scale + ")",
        filter: "blur(" + blur + "px)", easing
    });
    return [
        frame(0, from.x, from.y, 1, 0, 0, "ease-in"),
        frame(0.38, from.x + dx * 0.40, from.y + dy * 0.40,
              preset.scalePeak, rotation, preset.blur, preset.easing),
        frame(0.80, clamp(to.x + (distance ? dx / distance * overshoot : 0)),
              clamp(to.y + (distance ? dy / distance * overshoot : 0)),
              1 + (preset.scalePeak - 1) * 0.25, -rotation * 0.15, 0, "ease-in-out"),
        frame(1, to.x, to.y, 1, 0, 0, "linear")
    ];
}

async function animatePieceToSquare(element, square, presetName = motion.defaultPreset) {
    const preset = motion.presets[presetName];
    if (!preset) throw new Error("Unknown movement preset: " + presetName);
    const target = squareToCoords(square);
    const from = {x: parseFloat(element.style.left) || 0,
                  y: parseFloat(element.style.top) || 0};
    const to = {x: target.x * squareSize, y: target.y * squareSize};
    if (preset.duration <= 0 || (from.x === to.x && from.y === to.y)) {
        placePiece(element, square);
        return;
    }
    const previousZ = element.style.zIndex;
    element.style.zIndex = "6";
    const animation = element.animate(pieceMoveKeyframes(from, to, preset), {
        duration: preset.duration, easing: "linear", fill: "both"
    });
    try {
        // Resolve only after the overshoot has settled: sounds/memes use this boundary.
        await animation.finished;
        placePiece(element, square);
    } finally {
        // Remove fill effects and restore stacking, including on cancellation.
        animation.cancel();
        element.style.zIndex = previousZ;
    }
}
