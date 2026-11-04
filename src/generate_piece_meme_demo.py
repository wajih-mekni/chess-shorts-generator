"""Generate a local image/video piece-meme demo; never overwrite production input."""
from pathlib import Path
import subprocess
import chess
try:
    from .renderer.chess_state import compile_sequence
    from .renderer.composition import render_scene
except ImportError:
    from renderer.chess_state import compile_sequence
    from renderer.composition import render_scene

ROOT = Path(__file__).resolve().parents[1]
START_FEN = '4k2r/8/8/8/8/8/7Q/K7 w - - 0 1'
INITIAL_PIECE_MEMES = [
    dict(square='e8', meme='HikaruFace', scale=.48, shape='circle', hold=True),
]
DEMO_SEQUENCE = (
    'Qh5+^N@J(0.6s) Kd7^N@J(0.6s) '
    'Qh4^N@J(pm:d7:HikaruLaugh,hold=true,shape=circle)'
    '(pm:h8:HikaruFace,hold=true,shape=circle)(0.6s) '
    'Kc6^N@J(0.6s) Qxh8^N@J(pm-remove:c6)(0.6s)'
)
REGISTRY = {
    'HikaruFace': dict(src='assets/memes/piece_meme_demo.png', type='image'),
    'HikaruLaugh': dict(src='assets/memes/hikaruLaughExecuseme.mp4', type='video'),
}


def main():
    image = ROOT / REGISTRY['HikaruFace']['src']
    if not image.exists():
        # One small still extracted from an existing local clip; no video copies.
        subprocess.run(['ffmpeg','-v','error','-ss','0.5','-i',str(ROOT/REGISTRY['HikaruLaugh']['src']),
                        '-frames:v','1','-vf','scale=192:-1',str(image)],check=True)
    scene = compile_sequence(chess.Board(START_FEN), DEMO_SEQUENCE)
    html = render_scene(scene,directing_profile='AUTO',piece_meme_mode='on',piece_memes=REGISTRY,
                        initial_piece_memes=INITIAL_PIECE_MEMES,initial_delay=1,
                        meme_mode='fixed',meme_path='../assets/memes/Cr7.mp4',meme_volume=0)
    output = ROOT/'output/piece_meme_demo.html'
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(html,encoding='utf-8')
    print(f'Created {output}')


if __name__ == '__main__':
    main()
