"""Generate a three-level brilliant comparison without changing production input."""
from pathlib import Path
import chess
try:
    from .renderer.chess_state import compile_sequence
    from .renderer.composition import render_scene
except ImportError:
    from renderer.chess_state import compile_sequence
    from renderer.composition import render_scene

ROOT = Path(__file__).resolve().parents[1]
SEQUENCE = 'Nf3!!(1.5s) Nf6!!^A(1.5s) Nc3!!^VA(1.5s)'


def main():
    scene = compile_sequence(chess.Board(), SEQUENCE)
    for move, label in zip(scene['moves'], ('Standard', 'Aggressive', 'Very aggressive')):
        move['annotation_label'] = label
    html = render_scene(scene, directing_profile='AUTO', brilliant_mode='standard', meme_mode='off')
    output = ROOT / 'output/brilliant_comparison.html'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(html, encoding='utf-8')
    print(f'Created {output}')


if __name__ == '__main__':
    main()
