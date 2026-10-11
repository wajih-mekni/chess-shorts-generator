from pathlib import Path

import chess
import chess.svg


OUTPUT_DIR = Path("output/frames")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Starting position
fen = chess.STARTING_FEN

# Moves in UCI format
moves = [
    "e2e4",
    "e7e5",
    "g1f3",
    "b8c6",
    "f1b5",
]

board = chess.Board(fen)


def save_board(board, index, last_move=None):
    svg = chess.svg.board(
        board=board,
        size=1080,
        lastmove=last_move,
    )

    path = OUTPUT_DIR / f"frame_{index:02d}.svg"

    with open(path, "w") as f:
        f.write(svg)

    print(f"Created {path}")


# Initial position
save_board(board, 0)

# Apply moves one by one
for i, move_text in enumerate(moves, start=1):
    move = chess.Move.from_uci(move_text)

    if move not in board.legal_moves:
        raise ValueError(f"Illegal move: {move_text}")

    board.push(move)

    save_board(board, i, last_move=move)

print("Sequence finished.")