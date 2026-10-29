"""Pure chess compilation: no DOM, media, or output side effects."""
import re
import chess

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

ANNOTATIONS = {
    "!!": {"style": "brilliant", "label": "Brilliant"},
    "!": {"style": "great", "label": "Great"},
    "!?": {"style": "excellent", "label": "Excellent"},
    "?!": {"style": "inaccuracy", "label": "Inaccuracy"},
    "?": {"style": "mistake", "label": "Mistake"},
    "??": {"style": "blunder", "label": "Blunder"},
}


def split_annotated_san(token: str):
    """
    Examples:
    Bb5!!   -> ("Bb5", "!!")
    Nf3?!   -> ("Nf3", "?!")
    Qh5+!   -> ("Qh5+", "!")
    e4      -> ("e4", None)
    """
    match = re.match(r"^(.*?)(\?\?|\?\!|!\?|!!|!|\?)?$", token)

    if not match:
        raise ValueError(f"Could not parse move token: {token}")

    san = match.group(1)
    annotation = match.group(2)

    return san, annotation


def parse_camera_directive(token: str):
    """Remove one directing suffix independently of SAN/evaluation/timing parsing."""
    if "@" not in token:
        return token, None
    match = re.fullmatch(r"([^@]+)@([JKL])((?:[!?]+|\((?:meme|\d+(?:\.\d+)?s)\))*)", token)
    if not match:
        raise ValueError(f"Invalid camera directive in {token!r}; use one @J, @K or @L")
    return match[1] + match[3], match[2]


def parse_move_token(token: str, default_pause: float):
    """Separate SAN from annotations and trailing timing/meme metadata."""
    pause = None
    start_meme = False
    while True:
        metadata = re.search(r"\((meme|\d+(?:\.\d+)?s)\)$", token)
        if metadata is None:
            break
        value = metadata.group(1)
        if value == "meme":
            start_meme = True
        elif pause is None:
            pause = float(value[:-1])
        token = token[:metadata.start()]

    san, annotation = split_annotated_san(token)
    return san, annotation, default_pause if pause is None else pause, start_meme



def compile_sequence(board, annotated_line, default_pause=2):
    """Return initial sprites, moves and ordered events without mutating board."""
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


    # --------------------------------------------------
    # Prepare move information
    # --------------------------------------------------

    moves = []

    temp_board = board.copy()

    timeline = []

    for token in annotated_line.split():

        if token == "(meme)":
            timeline.append({"type": "meme"})
            continue

        token, camera_directive = parse_camera_directive(token)
        san, annotation, pause, start_meme = parse_move_token(token, default_pause)

        move = temp_board.parse_san(san)

        from_square = chess.square_name(move.from_square)
        to_square = chess.square_name(move.to_square)

        move_data = {
            "piece_kind": chess.piece_name(temp_board.piece_at(move.from_square).piece_type),
            "piece_color": "white" if temp_board.turn == chess.WHITE else "black",
            "camera_directive": camera_directive,
            "pause": pause,
            "start_meme": start_meme,
            "from": from_square,
            "to": to_square,
            "capture": None,
            "captured_kind": None,
            "captured_color": None,
            "en_passant": temp_board.is_en_passant(move),
            "promotion": None,
            "rook_from": None,
            "rook_to": None,
            "annotation": annotation,
            "annotation_style": ANNOTATIONS.get(annotation, {}).get("style"),
            "annotation_label": ANNOTATIONS.get(annotation, {}).get("label"),
        }

        # Normal capture
        if temp_board.is_capture(move):
            if temp_board.is_en_passant(move):
                capture_square = chess.square(
                    chess.square_file(move.to_square),
                    chess.square_rank(move.from_square),
                )
                move_data["capture"] = chess.square_name(capture_square)
            else:
                move_data["capture"] = to_square
            victim = temp_board.piece_at(chess.parse_square(move_data["capture"]))
            if victim:
                move_data["captured_kind"] = chess.piece_name(victim.piece_type)
                move_data["captured_color"] = "white" if victim.color == chess.WHITE else "black"

        # Castling
        if temp_board.is_castling(move):
            if chess.square_file(move.to_square) > chess.square_file(move.from_square):
                rook_from = chess.square(7, chess.square_rank(move.from_square))
                rook_to = chess.square(5, chess.square_rank(move.from_square))
            else:
                rook_from = chess.square(0, chess.square_rank(move.from_square))
                rook_to = chess.square(3, chess.square_rank(move.from_square))

            move_data["rook_from"] = chess.square_name(rook_from)
            move_data["rook_to"] = chess.square_name(rook_to)

        temp_board.push(move)
        move_data["check"] = temp_board.is_check()
        move_data["checkmate"] = temp_board.is_checkmate()
        move_data["check_targets"] = []
        move_data["check_paths"] = []
        move_data["checker_squares"] = []
        move_data["checked_king"] = None
        if move_data["check"]:
            checkers = temp_board.checkers()
            king = temp_board.king(temp_board.turn)
            targets = {king}
            paths = set()
            for checker in checkers:
                checker_targets = {
                    square for square in temp_board.attacks(checker)
                    if temp_board.color_at(square) == temp_board.turn
                }
                targets.update(checker_targets)
                if temp_board.piece_type_at(checker) in (chess.ROOK, chess.BISHOP, chess.QUEEN):
                    for target in checker_targets:
                        paths.update(chess.SquareSet(chess.between(checker, target)))
            move_data["check_paths"] = [
                chess.square_name(square) for square in sorted(paths - targets)
                if temp_board.piece_at(square) is None
            ]
            move_data["check_targets"] = [chess.square_name(square) for square in sorted(targets)]
            move_data["checker_squares"] = [chess.square_name(square) for square in checkers]
            move_data["checked_king"] = chess.square_name(king)

        # Promotion
        if move.promotion:
            promoted_piece = temp_board.piece_at(move.to_square)
            move_data["promotion"] = piece_asset(promoted_piece)

        moves.append(move_data)
        timeline.append({"type": "move", "move": move_data})


    return {"pieces": pieces, "moves": moves, "timeline": timeline}
