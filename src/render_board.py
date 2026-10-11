import chess
import chess.svg

fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"

board = chess.Board(fen)

svg = chess.svg.board(
    board=board,
    size=1080
)

with open("board.svg", "w") as f:
    f.write(svg)

print("Created board.svg")