"""Persistent @J/@K/@L camera-directing demo; piece presets are unchanged."""
from pathlib import Path
import chess
try:
    from .renderer.chess_state import compile_sequence
    from .renderer.composition import render_scene
except ImportError:
    from renderer.chess_state import compile_sequence
    from renderer.composition import render_scene


def generate():
    # Sparse legal position makes the long d1-d5 queen entrance easy to inspect.
    board = chess.Board("6k1/p4p1p/8/8/8/8/8/R2QKBN1 w - - 0 1")
    scene = compile_sequence(board,
        'Nf3@K a6 Bc4@J h6 Qd5@K a5 Qe5!!@L Kh7@J', 0.6)
    path = Path('output/camera_demo.html')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_scene(scene,
        meme_path='../assets/memes/MonkeyCry.mp4', meme_volume=0.25,
        meme_comment_text='Destination focus · Qd5 entrance · Qe5!! hold'), encoding='utf-8')
    print(f'Created {path}')


if __name__ == '__main__':
    generate()
