// Effects system. Included inline by composition.py.
const checkTargetLayer = document.getElementById("checkTargetLayer");
// One reusable overlay per square; checking moves never create new nodes.
const checkOverlays = Array.from({ length: 64 }, () => {
    const overlay = document.createElement("div");
    overlay.className = "check-target";
    checkTargetLayer.appendChild(overlay);
    return overlay;
});

const fromHighlight = document.getElementById("fromHighlight");
const toHighlight = document.getElementById("toHighlight");
const arrowLayer = document.getElementById("arrowLayer");
const brilliantArrow = document.getElementById("brilliantArrow");
const annotationBadge = document.getElementById("annotationBadge");
const annotationPill = document.getElementById("annotationPill");
const effectElements = [fromHighlight, toHighlight, arrowLayer, annotationBadge, annotationPill];

function clearCheckEffects() {
    checkOverlays.forEach(overlay => {
        overlay.getAnimations().forEach(animation => animation.cancel());
        overlay.style.display = "none";
    });
}

function showCheckEffects(move) {
    clearCheckEffects();
    if (!move.check) return;
    const targets = new Set(move.check_targets || []);
    const squares = new Set([...(move.check_paths || []), ...targets]);
    squares.forEach(square => {
        const coords = squareToCoords(square);
        const overlay = checkOverlays[coords.y * 8 + coords.x];
        const opacity = square === move.checked_king ? 0.7
            : targets.has(square) ? 0.55 : 0.32;
        placePiece(overlay, square);
        overlay.style.opacity = opacity;
        overlay.style.display = "block";
        overlay.animate([{ opacity: 0 }, { opacity }],
            { duration: 180, easing: "ease-out" });
    });
}

function clearMoveEffects(clearCheck = true) {

    if (clearCheck) clearCheckEffects();

    effectElements.forEach(element => {
        element.getAnimations().forEach(animation => animation.cancel());
        element.style.display = "none";
    });
    annotationBadge.textContent = "";
    annotationPill.textContent = "";

}

function showMoveEffects(move) {

    clearMoveEffects(false);
    if (!move.annotation || !move.annotation_style) return;

    const from = squareToCoords(move.from);
    const to = squareToCoords(move.to);

    [fromHighlight, toHighlight].forEach((element, index) => {
        element.className = "move-highlight "
            + (index === 0 ? "from-highlight " : "to-highlight ")
            + move.annotation_style;
        placePiece(element, index === 0 ? move.from : move.to);
        element.style.display = "block";
        element.animate([
            { opacity: 0 },
            { opacity: index === 0 ? 0.25 : 0.46 }
        ], { duration: 140, easing: "ease-out" });
    });

    if (move.annotation === "!!") {
        // Center-to-center in board coordinates; SVG rotates the head automatically.
        // The arrow is above highlights but below pieces to keep them readable.
        brilliantArrow.setAttribute("x1", (from.x + 0.5) * squareSize);
        brilliantArrow.setAttribute("y1", (from.y + 0.5) * squareSize);
        brilliantArrow.setAttribute("x2", (to.x + 0.5) * squareSize);
        brilliantArrow.setAttribute("y2", (to.y + 0.5) * squareSize);
        arrowLayer.style.display = "block";
        arrowLayer.animate([{ opacity: 0 }, { opacity: 0.85 }],
            { duration: 160, easing: "ease-out" });
    }

    annotationBadge.textContent = move.annotation;
    annotationBadge.className = "annotation-badge " + move.annotation_style;
    annotationBadge.style.display = "flex";

    annotationPill.className = "annotation-pill " + move.annotation_style;
    annotationPill.textContent = move.annotation_label || "";
    const hasLabel = Boolean(move.annotation_label);
    annotationPill.style.display = hasLabel ? "flex" : "none";

    // Measure the connected component before positioning it. Keep it outside
    // near the top edge, with only a small part extending into the square.
    const badgeWidth = annotationBadge.offsetWidth;
    const badgeHeight = annotationBadge.offsetHeight;
    const pillWidth = hasLabel ? annotationPill.offsetWidth : 0;
    const pillHeight = hasLabel ? annotationPill.offsetHeight : 0;
    const gap = hasLabel ? 2 : 0;
    const edgeInset = 6; // Also leaves room for the badge's 1.1x pop.
    const pieceGap = 4;
    const componentWidth = pillWidth + gap + badgeWidth;
    const componentHeight = Math.max(badgeHeight, pillHeight);
    const boardSize = squareSize * 8;
    const preferredRight = (to.x + 1) * squareSize - edgeInset;
    const left = Math.max(edgeInset, Math.min(
        preferredRight - componentWidth, layout.labelRight - edgeInset - componentWidth));
    const squareTop = to.y * squareSize;
    // Let about one-third of the badge cross the square edge. The shorter
    // pill extends less deeply, leaving the piece's crown clear.
    const overlap = badgeHeight * 0.30;
    const above = squareTop - componentHeight + overlap;
    const top = above >= edgeInset ? above : Math.min(
        squareTop + squareSize + pieceGap, boardSize - edgeInset - componentHeight);

    annotationBadge.style.left = (left + pillWidth + gap) + "px";
    annotationBadge.style.top = (top + (componentHeight - badgeHeight) / 2) + "px";
    if (hasLabel) {
        annotationPill.style.left = left + "px";
        annotationPill.style.top = (top + (componentHeight - pillHeight) / 2) + "px";
        annotationPill.style.transform = "none";
        annotationPill.style.transformOrigin = "right center";
        annotationPill.animate([
            { transform: "scale(0.94)", opacity: 0 },
            { transform: "scale(1)", opacity: 1 }
        ], { duration: 200, easing: "ease-out" });
    }

    annotationBadge.animate([
        { transform: "scale(0.7)", opacity: 0 },
        { transform: "scale(1.1)", opacity: 1, offset: 0.65 },
        { transform: "scale(1)", opacity: 1 }
    ], { duration: 220, easing: "cubic-bezier(.22,.61,.36,1)" });

}
