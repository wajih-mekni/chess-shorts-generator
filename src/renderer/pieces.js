// Pieces system. Included inline by composition.py.
let pieceBySquare = {};

async function slidePieceToSquare(element, square, presetName) {
    await animatePieceToSquare(element, square, presetName);
}

function createPieces() {
    initialPieces.forEach(piece => {
        const img = document.createElement("img");
        img.className = "piece";
        img.src = "../assets/pieces/" + piece.asset;
        img.dataset.square = piece.square;
        placePiece(img, piece.square);
        board.appendChild(img);
        pieceBySquare[piece.square] = img;
    });
}

function resetPieces() {
    Object.values(pieceBySquare).forEach(piece => piece.remove());
    pieceBySquare = {};
    createPieces();
}

// The callback is the exact landing boundary used by the timeline for audio/effects.
async function animatePieceMove(move, onLand = () => {}) {
    const piece = pieceBySquare[move.from];
    if (!piece) {
        console.error("No piece found on", move.from);
        return false;
    }
    if (move.capture && pieceBySquare[move.capture]) {
        pieceBySquare[move.capture].remove();
        delete pieceBySquare[move.capture];
    }
    delete pieceBySquare[move.from];
    await slidePieceToSquare(piece, move.to, move.animation_preset);
    onLand();
    piece.dataset.square = move.to;
    pieceBySquare[move.to] = piece;
    if (move.promotion) piece.src = "../assets/pieces/" + move.promotion;
    if (move.rook_from && move.rook_to) {
        const rook = pieceBySquare[move.rook_from];
        if (rook) {
            delete pieceBySquare[move.rook_from];
            await slidePieceToSquare(rook, move.rook_to, move.animation_preset);
            rook.dataset.square = move.rook_to;
            pieceBySquare[move.rook_to] = rook;
        }
    }
    return true;
}
