"""Generate the five-move preset comparison without changing the main demo."""
from pathlib import Path
import chess
try:
    from .renderer.chess_state import compile_sequence
    from .renderer.composition import render_scene
except ImportError:
    from renderer.chess_state import compile_sequence
    from renderer.composition import render_scene


def generate():
    scene = compile_sequence(chess.Board(), 'e4 e5 Nf3 Nc6 Bc4', 0.8)
    presets = ['NORMAL_MOVE', 'FAST_MOVE', 'DRAMATIC_MOVE', 'NORMAL_MOVE', 'DRAMATIC_MOVE']
    for move, preset in zip(scene['moves'], presets):
        move['animation_preset'] = preset
    path = Path('output/motion_demo.html')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_scene(scene, camera_enabled=False,
        meme_path='../assets/memes/MonkeyCry.mp4', meme_volume=0.25,
        meme_comment_text='e4 · e5 · Nf3 · Nc6 · Bc4'), encoding='utf-8')
    print(f'Created {path}')


if __name__ == '__main__':
    generate()
