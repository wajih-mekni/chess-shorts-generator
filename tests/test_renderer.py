"""Pure scene compilation/composition and existing JS audio regression checks."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import chess

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.renderer.chess_state import compile_sequence
from src.renderer.composition import render_scene
from src.renderer import layout


class RendererTests(unittest.TestCase):
    def test_special_moves_and_input_immutability(self):
        board = chess.Board('4k3/8/8/3p4/4P3/8/p7/3QK2R w K - 0 1')
        before = board.fen()
        scene = compile_sequence(board, 'O-O a1=Q exd5 Qa7+ Kh1', 0)
        self.assertEqual(board.fen(), before)
        moves = scene['moves']
        self.assertEqual((moves[0]['rook_from'], moves[0]['rook_to']), ('h1', 'f1'))
        self.assertEqual(moves[1]['promotion'], 'bQ.svg')
        self.assertEqual(moves[2]['capture'], 'd5')
        self.assertTrue(moves[3]['check'])
        self.assertEqual(moves[3]['checked_king'], 'g1')
        self.assertIn('g1', moves[3]['check_targets'])
        self.assertIn('f2', moves[3]['check_paths'])
        self.assertFalse(moves[4]['check'])
        with tempfile.NamedTemporaryFile(suffix='.html', dir=ROOT/'output') as f:
            Path(f.name).write_text(render_scene(scene))
            subprocess.run(['node', str(ROOT/'tests/test_sequence_audio.cjs'), f.name], check=True)

    def test_en_passant_and_illegal_move(self):
        scene = compile_sequence(chess.Board(), 'e4 a6 e5 d5 exd6', 0)
        self.assertEqual(scene['moves'][-1]['capture'], 'd5')
        self.assertEqual(scene['moves'][-1]['to'], 'd6')
        with self.assertRaises(chess.IllegalMoveError):
            compile_sequence(chess.Board(), 'e5')

    def test_composition_and_optional_media(self):
        scene = compile_sequence(chess.Board(), '(meme) e4!!(meme)(0.8s)', 2)
        html = render_scene(scene, meme_path='../assets/a"b.mp4',
                            meme_comment_text='<hello> & goodbye')
        self.assertIn('a&quot;b.mp4', html)
        self.assertIn('&lt;hello&gt; &amp; goodbye', html)
        self.assertEqual(html.count('<script>'), 1)
        self.assertNotIn('${', html)
        self.assertIn('class="board-camera"', html)
        self.assertNotIn('<video', render_scene(scene))
        self.assertNotIn('<audio', render_scene(scene))
        self.assertEqual(scene['timeline'][0], {'type': 'meme'})
        self.assertTrue(scene['moves'][0]['start_meme'])
        self.assertEqual(scene['moves'][0]['pause'], 0.8)
        self.assertEqual(layout.BOARD_X * 2 + layout.BOARD_SIZE, layout.CANVAS_WIDTH)
        self.assertEqual(layout.MEME_Y + layout.MEME_HEIGHT,
                         layout.CANVAS_HEIGHT - layout.BOTTOM_SAFE_AREA)


if __name__ == '__main__':
    unittest.main()
