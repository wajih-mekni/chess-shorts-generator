import json
from html import escape
from pathlib import Path

import chess
import re


OUTPUT_PATH = Path("output/sequence_demo.html")
OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)


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


# --------------------------------------------------
# Initial position + sequence
# --------------------------------------------------

MEME_PATH = "../assets/memes/reaction1.mp4"
MEME_VOLUME = 0.8

MUSIC_PATH = "../assets/music/background.mp3"
MUSIC_VOLUME = 0.12

DEFAULT_PAUSE = 0.7

board = chess.Board(
    "k2q4/8/8/8/8/8/1p6/4K2R w K - 0 1"
)

annotated_line = "O-O!!(3s) b1=Q?(1s) Rxb1?! Qd4+!(4s) Kh1?? Qe4!!"
move_tokens = annotated_line.split()


# --------------------------------------------------
# Initial pieces
# --------------------------------------------------

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

moves = []

temp_board = board.copy()

for token in move_tokens:

    pause = DEFAULT_PAUSE
    timing = re.search(r"\((\d+(?:\.\d+)?)s\)$", token)
    if timing:
        pause = float(timing.group(1))
        token = token[:timing.start()]

    san, annotation = split_annotated_san(token)

    move = temp_board.parse_san(san)

    from_square = chess.square_name(move.from_square)
    to_square = chess.square_name(move.to_square)

    move_data = {
        "pause": pause,
        "from": from_square,
        "to": to_square,
        "capture": None,
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


meme_video = (
    f'<video id="memeVideo" src="{escape(MEME_PATH, quote=True)}" '
    'preload="auto" loop playsinline></video>'
    if MEME_PATH else ""
)

music_audio = (
    f'<audio id="backgroundMusic" src="{escape(MUSIC_PATH, quote=True)}" '
    'preload="auto" loop></audio>'
    if MUSIC_PATH else ""
)

html = f"""
<!DOCTYPE html>

<html lang="en">

<head>

<meta charset="UTF-8">

<title>Chess Sequence Animation</title>

<style>

body {{
    margin: 0;
    background: #222;

    min-height: 100vh;

    display: flex;
    justify-content: center;
    align-items: flex-start;
}}


.short-canvas {{
    position: relative;

    width: 1080px;
    height: 1920px;

    background: #111;

    overflow: hidden;
}}


/* Chess board section */
.board-area {{
    position: relative;

    width: 1080px;
    height: 1080px;

    display: flex;
    justify-content: center;
    align-items: flex-start;
}}


.board-container {{
    position: relative;

    width: 1080px;
    height: 1080px;
}}


.board-background {{
    position: absolute;

    width: 1080px;
    height: 1080px;

    left: 0;
    top: 0;

    z-index: 1;
}}


.piece {{
    position: absolute;

    width: 135px;
    height: 135px;

    z-index: 5;

    transition:
        left 0.45s cubic-bezier(.22,.61,.36,1),
        top 0.45s cubic-bezier(.22,.61,.36,1);
}}
/* Effects use one shared color, with independent layer opacity. */
.move-highlight {{
    position: absolute;
    width: 135px;
    height: 135px;
    z-index: 3;
    display: none;
    pointer-events: none;
    background: var(--annotation-color);
}}

.from-highlight {{ opacity: 0.25; }}
.to-highlight {{ opacity: 0.46; }}

.check-target-layer {{
    position: absolute;
    inset: 0;
    z-index: 3;
    pointer-events: none;
}}

.check-target {{
    position: absolute;
    width: 135px;
    height: 135px;
    display: none;
    background: #ff3b30;
}}

.arrow-layer {{
    position: absolute;
    inset: 0;
    width: 1080px;
    height: 1080px;
    z-index: 4;
    display: none;
    pointer-events: none;
    color: var(--annotation-color);
    opacity: 0.85;
}}

.annotation-badge {{
    position: absolute;
    z-index: 10;
    display: none;
    width: 58px;
    height: 58px;
    box-sizing: border-box;
    border: 2px solid rgba(255, 255, 255, 0.8);
    border-radius: 50%;
    background: var(--annotation-color);
    color: #fff;
    font-family: Arial, sans-serif;
    font-weight: 900;
    font-size: 30px;
    line-height: 1;
    letter-spacing: -2px;
    align-items: center;
    justify-content: center;
    pointer-events: none;
    text-shadow: 0 1px 2px rgba(0, 0, 0, 0.18);
    box-shadow: 0 4px 10px rgba(0, 0, 0, 0.35),
                inset 0 1px 0 rgba(255, 255, 255, 0.25);
}}

.annotation-pill {{
    position: absolute;
    z-index: 9;
    display: none;
    box-sizing: border-box;
    height: 46px;
    padding: 0 16px;
    border: 1px solid rgba(255, 255, 255, 0.16);
    border-radius: 23px;
    background: var(--annotation-color);
    background: color-mix(in srgb, var(--annotation-color) 94%, transparent);
    color: #fff;
    font: 700 26px/1 Arial, sans-serif;
    white-space: nowrap;
    align-items: center;
    pointer-events: none;
    box-shadow: 0 3px 10px rgba(0, 0, 0, 0.3);
}}

.brilliant {{ --annotation-color: #26C2A3; }}
.great {{ --annotation-color: #4A90E2; }}
.excellent {{ --annotation-color: #7FAE3F; }}
.inaccuracy {{ --annotation-color: #E6B73C; }}
.mistake {{ --annotation-color: #F08A35; }}
.blunder {{ --annotation-color: #E04B4B; }}


/* Reaction / meme */
.reaction-area {{
    width: 1080px;
    height: 560px;
    overflow: hidden;

    background: #181818;

    display: flex;
    justify-content: center;
    align-items: center;

    font-family: Arial, sans-serif;
    font-size: 42px;
    color: #777;
}}


.reaction-area video {{
    display: block;
    width: 100%;
    height: 100%;
    object-fit: cover;
}}

/* Play button only for development */
.controls {{
    position: fixed;

    top: 20px;
    right: 20px;

    z-index: 9999;
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


<div class="short-canvas">

    <div class="board-area">

        <div class="board-container" id="board">

            <img
                class="board-background"
                src="../assets/board.svg"
            >

            <div id="fromHighlight" class="move-highlight from-highlight" aria-hidden="true"></div>
            <div id="toHighlight" class="move-highlight to-highlight" aria-hidden="true"></div>
            <div id="checkTargetLayer" class="check-target-layer" aria-hidden="true"></div>
            <svg id="arrowLayer" class="arrow-layer brilliant" viewBox="0 0 1080 1080" aria-hidden="true">
                <defs>
                    <marker id="brilliantArrowhead" viewBox="0 0 48 48"
                            markerWidth="48" markerHeight="48" refX="46" refY="24"
                            orient="auto" markerUnits="userSpaceOnUse">
                        <path d="M 2 2 L 46 24 L 2 46 L 12 24 Z" fill="currentColor" />
                    </marker>
                </defs>
                <line id="brilliantArrow" stroke="currentColor" stroke-width="18"
                      stroke-linecap="round" marker-end="url(#brilliantArrowhead)" />
            </svg>
            <div id="annotationBadge" class="annotation-badge" aria-hidden="true"></div>
            <div id="annotationPill" class="annotation-pill" aria-hidden="true"></div>

        </div>

    </div>

    <div class="reaction-area">
        {meme_video}
    </div>

</div>


<div class="controls">

    <button id="playButton" onclick="playSequence()">
        Play Sequence
    </button>

</div>


{music_audio}

<script>

const initialPieces = {json.dumps(pieces)};

const moves = {json.dumps(moves)};

const board = document.getElementById("board");

const playButton = document.getElementById("playButton");
const memeVideo = document.getElementById("memeVideo");

function startMemeVideo() {{
    if (!memeVideo) return;
    memeVideo.volume = {json.dumps(MEME_VOLUME)};
    memeVideo.muted = false;
    memeVideo.currentTime = 0;
    memeVideo.play().catch(error => {{
        console.warn("Could not play meme video:", error);
    }});
}}

const backgroundMusic = document.getElementById("backgroundMusic");

function startBackgroundMusic() {{
    if (!backgroundMusic) return;
    backgroundMusic.volume = {json.dumps(MUSIC_VOLUME)};
    backgroundMusic.currentTime = 0;
    backgroundMusic.play().catch(error => {{
        console.warn("Could not play background music:", error);
    }});
}}

const squareSize = 135;
const checkTargetLayer = document.getElementById("checkTargetLayer");
// One reusable overlay per square; checking moves never create new nodes.
const checkOverlays = Array.from({{ length: 64 }}, () => {{
    const overlay = document.createElement("div");
    overlay.className = "check-target";
    checkTargetLayer.appendChild(overlay);
    return overlay;
}});

function clearCheckEffects() {{
    checkOverlays.forEach(overlay => {{
        overlay.getAnimations().forEach(animation => animation.cancel());
        overlay.style.display = "none";
    }});
}}

function showCheckEffects(move) {{
    clearCheckEffects();
    if (!move.check) return;
    const targets = new Set(move.check_targets || []);
    const squares = new Set([...(move.check_paths || []), ...targets]);
    squares.forEach(square => {{
        const coords = squareToCoords(square);
        const overlay = checkOverlays[coords.y * 8 + coords.x];
        const opacity = square === move.checked_king ? 0.7
            : targets.has(square) ? 0.55 : 0.32;
        placePiece(overlay, square);
        overlay.style.opacity = opacity;
        overlay.style.display = "block";
        overlay.animate([{{ opacity: 0 }}, {{ opacity }}],
            {{ duration: 180, easing: "ease-out" }});
    }});
}}

const fromHighlight = document.getElementById("fromHighlight");
const toHighlight = document.getElementById("toHighlight");
const arrowLayer = document.getElementById("arrowLayer");
const brilliantArrow = document.getElementById("brilliantArrow");
const annotationBadge = document.getElementById("annotationBadge");
const annotationPill = document.getElementById("annotationPill");
const effectElements = [fromHighlight, toHighlight, arrowLayer, annotationBadge, annotationPill];


let pieceBySquare = {{}};

let playing = false;
let hasPlayed = false;



function sleep(ms) {{

    return new Promise(
        resolve => setTimeout(resolve, ms)
    );

}}



// Reuse five local audio elements. Begin loading as soon as the page opens.
const moveAudio = new Map();
const audioReady = [];
for (const kind of ["move", "capture", "check", "castle", "promotion"]) {{
    const audio = new Audio();
    audio.preload = "auto";
    audio.src = "../assets/sfx/" + kind + ".webm";
    moveAudio.set(kind, audio);
    audioReady.push(new Promise(resolve => {{
        const finish = (ready) => {{
            clearTimeout(timeout);
            audio.removeEventListener("canplaythrough", loaded);
            audio.removeEventListener("error", failed);
            if (!ready) console.warn("Could not preload chess sound:", audio.src);
            resolve(ready);
        }};
        const loaded = () => finish(true);
        const failed = () => finish(false);
        const timeout = setTimeout(failed, 15000);
        audio.addEventListener("canplaythrough", loaded, {{ once: true }});
        audio.addEventListener("error", failed, {{ once: true }});
        audio.load();
    }}));
}}

async function prepareMoveAudio() {{
    // Start muted playback on every element synchronously in the Play click
    // gesture, then pause/reset. This unlocks later landing-triggered playback.
    const unlock = Array.from(moveAudio.values(), async audio => {{
        audio.muted = true;
        try {{
            await audio.play();
        }} catch (error) {{
            console.warn("Could not unlock chess audio:", audio.src, error);
        }} finally {{
            audio.pause();
            audio.currentTime = 0;
            audio.muted = false;
        }}
    }});
    await Promise.all([...audioReady, ...unlock]);
}}

function moveSoundKind(move) {{
    // One sound per landing, even for captures/promotions that also give check.
    if (move.promotion) return "promotion";
    if (move.check) return "check";
    if (move.rook_from && move.rook_to) return "castle";
    if (move.capture) return "capture";
    return "move";
}}

function playMoveSound(move) {{
    const audio = moveAudio.get(moveSoundKind(move));
    if (!audio) return;
    // Always rewind, including consecutive uses of the same sound and replay.
    audio.pause();
    audio.currentTime = 0;
    audio.play().catch(error => {{
        console.warn("Could not play chess sound:", audio.src, error);
    }});
}}

async function slidePieceToSquare(element, square) {{
    // Flush the start position, then read the actual CSS transitions created
    // by placePiece. Both axes must finish before a diagonal move has landed.
    void element.offsetWidth;
    placePiece(element, square);
    const transitions = element.getAnimations().filter(animation =>
        animation.transitionProperty === "left" || animation.transitionProperty === "top");
    await Promise.all(transitions.map(animation => animation.finished));
}}


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



function placePiece(element, square) {{

    const coords =
        squareToCoords(square);

    element.style.left =
        (coords.x * squareSize)
        +
        "px";

    element.style.top =
        (coords.y * squareSize)
        +
        "px";

}}

function clearMoveEffects(clearCheck = true) {{

    if (clearCheck) clearCheckEffects();

    effectElements.forEach(element => {{
        element.getAnimations().forEach(animation => animation.cancel());
        element.style.display = "none";
    }});
    annotationBadge.textContent = "";
    annotationPill.textContent = "";

}}


function showMoveEffects(move) {{

    clearMoveEffects(false);
    if (!move.annotation || !move.annotation_style) return;

    const from = squareToCoords(move.from);
    const to = squareToCoords(move.to);

    [fromHighlight, toHighlight].forEach((element, index) => {{
        element.className = "move-highlight "
            + (index === 0 ? "from-highlight " : "to-highlight ")
            + move.annotation_style;
        placePiece(element, index === 0 ? move.from : move.to);
        element.style.display = "block";
        element.animate([
            {{ opacity: 0 }},
            {{ opacity: index === 0 ? 0.25 : 0.46 }}
        ], {{ duration: 140, easing: "ease-out" }});
    }});

    if (move.annotation === "!!") {{
        // Center-to-center in board coordinates; SVG rotates the head automatically.
        // The arrow is above highlights but below pieces to keep them readable.
        brilliantArrow.setAttribute("x1", (from.x + 0.5) * squareSize);
        brilliantArrow.setAttribute("y1", (from.y + 0.5) * squareSize);
        brilliantArrow.setAttribute("x2", (to.x + 0.5) * squareSize);
        brilliantArrow.setAttribute("y2", (to.y + 0.5) * squareSize);
        arrowLayer.style.display = "block";
        arrowLayer.animate([{{ opacity: 0 }}, {{ opacity: 0.85 }}],
            {{ duration: 160, easing: "ease-out" }});
    }}

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
        preferredRight - componentWidth, boardSize - edgeInset - componentWidth));
    const squareTop = to.y * squareSize;
    // Let about one-third of the badge cross the square edge. The shorter
    // pill extends less deeply, leaving the piece's crown clear.
    const overlap = badgeHeight * 0.30;
    const above = squareTop - componentHeight + overlap;
    const top = above >= edgeInset ? above : Math.min(
        squareTop + squareSize + pieceGap, boardSize - edgeInset - componentHeight);

    annotationBadge.style.left = (left + pillWidth + gap) + "px";
    annotationBadge.style.top = (top + (componentHeight - badgeHeight) / 2) + "px";
    if (hasLabel) {{
        annotationPill.style.left = left + "px";
        annotationPill.style.top = (top + (componentHeight - pillHeight) / 2) + "px";
        annotationPill.style.transform = "none";
        annotationPill.style.transformOrigin = "right center";
        annotationPill.animate([
            {{ transform: "scale(0.94)", opacity: 0 }},
            {{ transform: "scale(1)", opacity: 1 }}
        ], {{ duration: 200, easing: "ease-out" }});
    }}

    annotationBadge.animate([
        {{ transform: "scale(0.7)", opacity: 0 }},
        {{ transform: "scale(1.1)", opacity: 1, offset: 0.65 }},
        {{ transform: "scale(1)", opacity: 1 }}
    ], {{ duration: 220, easing: "cubic-bezier(.22,.61,.36,1)" }});

}}

function createPieces() {{

    initialPieces.forEach(piece => {{

        const img =
            document.createElement("img");

        img.className = "piece";

        img.src =
            "../assets/pieces/"
            +
            piece.asset;

        img.dataset.square =
            piece.square;

        placePiece(
            img,
            piece.square
        );

        board.appendChild(img);

        pieceBySquare[piece.square] =
            img;

    }});

}}



async function animateMove(move) {{

    clearMoveEffects();

    const movingPiece =
        pieceBySquare[move.from];

    if (!movingPiece) {{

        console.error(
            "No piece found on",
            move.from
        );

        return;
    }}


    // Captures
    if (move.capture) {{

        const captured =
            pieceBySquare[move.capture];

        if (captured) {{

            captured.remove();

            delete pieceBySquare[
                move.capture
            ];

        }}

    }}


    // Remove old square mapping
    delete pieceBySquare[
        move.from
    ];


    // Sound starts at the moving piece's actual landing, before any rook slide.
    await slidePieceToSquare(movingPiece, move.to);
    playMoveSound(move);
    showCheckEffects(move);


    // Update mapping
    movingPiece.dataset.square =
        move.to;

    pieceBySquare[
        move.to
    ] =
        movingPiece;


    // Promotion
    if (move.promotion) {{

        movingPiece.src =
            "../assets/pieces/"
            +
            move.promotion;

    }}


    // Castling
    if (
        move.rook_from
        &&
        move.rook_to
    ) {{

        const rook =
            pieceBySquare[
                move.rook_from
            ];

        if (rook) {{

            delete pieceBySquare[
                move.rook_from
            ];

            await slidePieceToSquare(rook, move.rook_to);

            pieceBySquare[
                move.rook_to
            ] =
                rook;

        }}

    }}


    // Annotation effect
    showMoveEffects(move);


    await sleep(
        move.pause * 1000
    );

}}



async function playSequence() {{

    if (playing) return;

    playing = true;

    playButton.disabled = true;

    // Start with audio in the click gesture, before any asynchronous chess work.
    // The media element runs independently of every per-move pause.
    startMemeVideo();
    startBackgroundMusic();
    await prepareMoveAudio();

    if (hasPlayed) {{
        clearMoveEffects();
        Object.values(pieceBySquare).forEach(piece => piece.remove());
        pieceBySquare = {{}};
        createPieces();
    }}

    for (const move of moves) {{

        await animateMove(
            move
        );

    }}


    hasPlayed = true;
    playing = false;
    playButton.disabled = false;
    playButton.textContent = "Replay Sequence";

}}


createPieces();

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