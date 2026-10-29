// Pieces system. Included inline by composition.py.
let pieceBySquare = {};
const renderedPieces = new Set();
let pieceGeneration = 0;

async function slidePieceToSquare(element, square, presetName, onMotion) {
    await animatePieceToSquare(element, square, presetName, onMotion);
}

function createPieces() {
    initialPieces.forEach(piece => {
        const actor = document.createElement("div");
        actor.className = "piece";
        actor.choreography = document.createElement("div");
        actor.choreography.className = "piece-choreography";
        actor.reaction = document.createElement("div");
        actor.reaction.className = "piece-reaction";
        const img = document.createElement("img");
        img.className = "piece-sprite";
        img.src = "../assets/pieces/" + piece.asset;
        img.draggable = false;
        actor.sprite = img;
        actor.reaction.appendChild(img);
        actor.choreography.appendChild(actor.reaction);
        actor.appendChild(actor.choreography);
        actor.dataset.square = piece.square;
        placePiece(actor, piece.square);
        board.appendChild(actor);
        renderedPieces.add(actor);
        pieceBySquare[piece.square] = actor;
    });
}

function resetPieces() {
    lightingSystem.reset();
    reactionSystem.reset();
    pieceGeneration++;
    new Set([...renderedPieces, ...Object.values(pieceBySquare)]).forEach(piece => {
        piece.getAnimations({subtree: true}).forEach(animation => animation.cancel?.());
        piece.remove();
    });
    renderedPieces.clear();
    pieceBySquare = {};
    createPieces();
}

// The callback is the exact landing boundary used by the timeline for audio/effects.
async function animatePieceMove(move, onLand = () => {}, onMotion = () => {}, retainCapture = null,
                                onRookMotion = () => {}) {
    const recipe = resolvePieceMotion(move); // Validate before changing logical occupancy.
    const generation = pieceGeneration;
    const piece = pieceBySquare[move.from];
    if (!piece) {
        console.error("No piece found on", move.from);
        return false;
    }
    if (move.capture && pieceBySquare[move.capture]) {
        const victim = pieceBySquare[move.capture];
        delete pieceBySquare[move.capture];
        if (retainCapture) retainCapture(victim);
        else {
            renderedPieces.delete(victim);
            victim.remove();
        }
    }
    delete pieceBySquare[move.from];
    try {
        if (recipe.kind === "legacy") {
            await slidePieceToSquare(piece, move.to, recipe.name, onMotion);
        } else {
            await animateChoreographedPieceToSquare(piece, move.to, recipe.name, onMotion);
        }
        onLand();
    } catch (error) {
        // Keep ownership on cancellation/error so replay can remove this actor.
        // Otherwise it is absent from both square keys and becomes a ghost sprite.
        if (generation === pieceGeneration) pieceBySquare[move.from] = piece;
        throw error;
    }
    piece.dataset.square = move.to;
    pieceBySquare[move.to] = piece;
    if (move.promotion) (piece.sprite || piece).src = "../assets/pieces/" + move.promotion;
    if (move.rook_from && move.rook_to) {
        const rook = pieceBySquare[move.rook_from];
        if (rook) {
            delete pieceBySquare[move.rook_from];
            try {
                // A castling rook keeps the existing sequential landing contract.
                // It uses ordinary travel unless its own choreography is requested.
                const rookRecipe = resolvePieceMotion({...move, piece_kind: "rook",
                    choreography_preset: move.rook_choreography_preset ||
                        (recipe.kind === "legacy" ? "LEGACY" : undefined)});
                if (rookRecipe.kind === "legacy") await slidePieceToSquare(rook, move.rook_to, rookRecipe.name, onRookMotion);
                else await animateChoreographedPieceToSquare(rook, move.rook_to, rookRecipe.name, onRookMotion);
            } catch (error) {
                if (generation === pieceGeneration) pieceBySquare[move.rook_from] = rook;
                throw error;
            }
            rook.dataset.square = move.rook_to;
            pieceBySquare[move.rook_to] = rook;
        }
    }
    return true;
}
