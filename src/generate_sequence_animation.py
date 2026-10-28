"""Edit the demo settings here, then run this file to generate the HTML scene."""
from pathlib import Path
import chess

try:  # Support both `python -m src.generate_sequence_animation` and direct execution.
    from .renderer.chess_state import compile_sequence, parse_move_token, split_annotated_san
    from .renderer.composition import render_scene
except ImportError:
    from renderer.chess_state import compile_sequence, parse_move_token, split_annotated_san
    from renderer.composition import render_scene

OUTPUT_PATH = Path("output/sequence_demo.html")

MEME_PATH = "../assets/memes/MonkeyCry.mp4"
MEME_VOLUME = 0.25
# Set to None or "" to hide the reaction caption.
MEME_COMMENT = "💀 Black after this move 💀 "
# 💀🔥💀🔥💀🔥

MUSIC_PATH = None
MUSIC_VOLUME = 0.8

DEFAULT_PAUSE = 2

board = chess.Board(
    "r4rk1/1b1R3p/p1p1p3/Pp2Bp1q/nb2nQ2/7P/1P3PP1/6K1 w - - 0 1"
)

annotated_line = "Qg3!!(5s) "


def generate(output=OUTPUT_PATH):
    scene = compile_sequence(board, annotated_line, DEFAULT_PAUSE)
    html = render_scene(scene, meme_path=MEME_PATH, meme_volume=MEME_VOLUME,
                        meme_comment_text=MEME_COMMENT, music_path=MUSIC_PATH,
                        music_volume=MUSIC_VOLUME)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(html, encoding="utf-8")
    return scene


if __name__ == "__main__":
    generate()
    print(f"Created {OUTPUT_PATH}")
