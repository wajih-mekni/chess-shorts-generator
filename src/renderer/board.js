// Board-local geometry shared by sprites, highlights, and arrows.
const board = document.getElementById("board");
const squareSize = layout.squareSize;

function squareToCoords(square) {
    return {x: square.charCodeAt(0) - "a".charCodeAt(0),
            y: 8 - parseInt(square[1])};
}

function placePiece(element, square) {
    const coords = squareToCoords(square);
    element.style.left = (coords.x * squareSize) + "px";
    element.style.top = (coords.y * squareSize) + "px";
}
