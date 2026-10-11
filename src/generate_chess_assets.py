from pathlib import Path

import chess
import chess.svg


ASSETS_DIR = Path("assets")
PIECES_DIR = ASSETS_DIR / "pieces"

PIECES_DIR.mkdir(parents=True, exist_ok=True)


# --------------------------------------------------
# Generate empty chess board
# --------------------------------------------------

board_svg = chess.svg.board(
    board=None,
    size=800,
    coordinates=False,
)

(ASSETS_DIR / "board.svg").write_text(
    board_svg,
    encoding="utf-8"
)

print("Created assets/board.svg")


# --------------------------------------------------
# Generate the 12 chess pieces
# --------------------------------------------------

pieces = {
    "wP": chess.Piece(chess.PAWN, chess.WHITE),
    "wN": chess.Piece(chess.KNIGHT, chess.WHITE),
    "wB": chess.Piece(chess.BISHOP, chess.WHITE),
    "wR": chess.Piece(chess.ROOK, chess.WHITE),
    "wQ": chess.Piece(chess.QUEEN, chess.WHITE),
    "wK": chess.Piece(chess.KING, chess.WHITE),

    "bP": chess.Piece(chess.PAWN, chess.BLACK),
    "bN": chess.Piece(chess.KNIGHT, chess.BLACK),
    "bB": chess.Piece(chess.BISHOP, chess.BLACK),
    "bR": chess.Piece(chess.ROOK, chess.BLACK),
    "bQ": chess.Piece(chess.QUEEN, chess.BLACK),
    "bK": chess.Piece(chess.KING, chess.BLACK),
}

for name, piece in pieces.items():

    svg = chess.svg.piece(
        piece,
        size=100
    )

    path = PIECES_DIR / f"{name}.svg"

    path.write_text(
        svg,
        encoding="utf-8"
    )

    print(f"Created {path}")