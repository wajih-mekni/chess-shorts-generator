import json
from pathlib import Path

import chess


OUTPUT_PATH = Path("output/slide_demo.html")
OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

board = chess.Board()

move = chess.Move.from_uci("e2e4")

from_square = chess.square_name(move.from_square)
to_square = chess.square_name(move.to_square)


def square_to_coords(square_name: str):
    file_index = ord(square_name[0]) - ord("a")
    rank_index = 8 - int(square_name[1])

    return file_index, rank_index


def piece_asset(piece: chess.Piece):
    color = "w" if piece.color == chess.WHITE else "b"

    names = {
        chess.PAWN: "P",
        chess.KNIGHT: "N",
        chess.BISHOP: "B",
        chess.ROOK: "R",
        chess.QUEEN: "Q",
        chess.KING: "K",
    }

    return f"{color}{names[piece.piece_type]}.svg"


pieces = []

for square, piece in board.piece_map().items():

    square_name = chess.square_name(square)

    x, y = square_to_coords(square_name)

    pieces.append({
        "square": square_name,
        "x": x,
        "y": y,
        "asset": piece_asset(piece),
    })


html = f"""
<!DOCTYPE html>
<html lang="en">

<head>

<meta charset="UTF-8">

<title>Chess Animation</title>

<style>

body {{
    margin: 0;

    background: #111;

    height: 100vh;

    display: flex;

    justify-content: center;

    align-items: center;
}}


.board-container {{

    position: relative;

    width: 800px;

    height: 800px;

}}


.board-background {{

    position: absolute;

    width: 800px;

    height: 800px;

    left: 0;

    top: 0;

    z-index: 1;

}}


.piece {{

    position: absolute;

    width: 100px;

    height: 100px;

    z-index: 5;

    transition:

        left 0.55s cubic-bezier(.22,.61,.36,1),

        top 0.55s cubic-bezier(.22,.61,.36,1);

}}


.controls {{

    position: fixed;

    bottom: 30px;

    left: 50%;

    transform: translateX(-50%);

}}


button {{

    padding: 12px 24px;

    font-size: 18px;

    border: none;

    border-radius: 8px;

    cursor: pointer;

}}

</style>

</head>


<body>


<div class="board-container" id="board">

    <img
        class="board-background"
        src="../assets/board.svg"
    >

</div>


<div class="controls">

<button onclick="playMove()">

Play Move

</button>

</div>


<script>

const pieces = {json.dumps(pieces)};

const fromSquare = "{from_square}";

const toSquare = "{to_square}";

const board = document.getElementById("board");

const squareSize = 100;



function squareToCoords(square) {{

    const file =
        square.charCodeAt(0)
        -
        "a".charCodeAt(0);

    const rank =
        8
        -
        parseInt(square[1]);

    return {{
        x: file,
        y: rank
    }};
}}



let movingPiece = null;



pieces.forEach(piece => {{

    const img =
        document.createElement("img");

    img.className = "piece";

    img.src =
        "../assets/pieces/"
        +
        piece.asset;

    img.style.left =
        (piece.x * squareSize)
        +
        "px";

    img.style.top =
        (piece.y * squareSize)
        +
        "px";

    img.dataset.square =
        piece.square;


    if (
        piece.square
        ===
        fromSquare
    ) {{

        movingPiece = img;

    }}


    board.appendChild(img);

}});



function playMove() {{

    if (!movingPiece) return;


    const target =
        squareToCoords(
            toSquare
        );


    movingPiece.style.left =
        (
            target.x
            *
            squareSize
        )
        +
        "px";


    movingPiece.style.top =
        (
            target.y
            *
            squareSize
        )
        +
        "px";

}}

</script>


</body>

</html>
"""


OUTPUT_PATH.write_text(
    html,
    encoding="utf-8"
)

print(
    f"Created {OUTPUT_PATH}"
)