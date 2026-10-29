// Pure move planning. No DOM writes, chess state mutation or automatic tactics.
function buildMovePlan(move) {
    const recipe = resolvePieceMotion(move);
    const brilliant = move.annotation === "!!";
    const directive = cameraConfig.enabled ? move.camera_directive : null;
    const reference = timingConfig.profile === "REFERENCE";
    const cameraDuration = !directive ? 0 : directive === "J"
        ? cameraConfig.wideDuration : cameraConfig.shots[directive].duration;
    const pieceDelay = timingConfig.serialCamera || !directive
        ? (brilliant ? cameraConfig.brilliantPreHold : 0)
        : brilliant ? timingConfig.cameraLeadHero
        : directive === "L" ? timingConfig.cameraLeadClose : timingConfig.cameraLeadNormal;
    // Each recipe supplies its own arrival marker; legacy keyframes are unchanged.
    return Object.freeze({
        profile: timingConfig.profile, serialCamera: timingConfig.serialCamera,
        cameraDuration, pieceDelay, moveDuration: Math.max(0, recipe.duration),
        choreography: recipe.name,
        reactions: resolveReactions(move),
        lighting: resolveLighting(move),
        contactDelay: Math.max(0, recipe.duration) * recipe.contactOffset,
        holdDuration: Math.max(0, Number(move.pause) || 0) * 1000 +
            (brilliant ? cameraConfig.brilliantPostHold : 0),
        hero: Boolean(reference && cameraConfig.enabled && brilliant),
        impulse: Boolean(reference && cameraConfig.enabled && directive === "L")
    });
}
