"""Run with: python -m unittest discover -s tests -p test_move_token_parser.py"""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import chess

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.renderer.chess_state import compile_sequence, parse_move_token


def generate(output, line=None):
    # Explicit position for Bxh4 and Rf7+, independent of the editable demo.
    board = chess.Board("5rk1/K7/8/8/7p/6B1/8/8 w - - 0 1")
    scene = compile_sequence(board, line or "", 0.7)
    return {**scene, "parse_move_token": parse_move_token}


class MoveTokenParserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with tempfile.TemporaryDirectory() as folder:
            cls.scope = generate(Path(folder) / 'sequence.html')

    def test_requested_examples_and_suffix_orders(self):
        cases = [
            ('Bxh4??(1s)', ('Bxh4', '??', 1.0, False)),
            ('Bxh4??(meme)(2s)', ('Bxh4', '??', 2.0, True)),
            ('Rf7+(0.8s)', ('Rf7+', None, 0.8, False)),
            ('Qh5+!', ('Qh5+', '!', 0.7, False)),
            ('Rxe7+!!(meme)(3s)', ('Rxe7+', '!!', 3.0, True)),
            ('Bxh4??(1s)(meme)', ('Bxh4', '??', 1.0, True)),
            ('Rf7+(meme)(0s)', ('Rf7+', None, 0.0, True)),
            ('Rf7+', ('Rf7+', None, 0.7, False)),
        ]
        for token, expected in cases:
            with self.subTest(token=token):
                self.assertEqual(self.scope['parse_move_token'](token, 0.7), expected)

    def test_all_annotations_preserve_check_and_mate(self):
        for annotation in ('!!', '!', '!?', '?!', '?', '??'):
            for san in ('Qh5+', 'Qh5#'):
                with self.subTest(annotation=annotation, san=san):
                    self.assertEqual(
                        self.scope['parse_move_token'](san + annotation + '(meme)(3s)', 0.7),
                        (san, annotation, 3.0, True),
                    )

    def test_clean_san_reaches_chess_and_standalone_meme_survives(self):
        original = chess.Board.parse_san
        for token in ('Bxh4??(1s)', 'Bxh4??(meme)(2s)', 'Bxh4??(1s)(meme)'):
            received = []

            def parse_san(board, san):
                received.append(san)
                return original(board, san)

            with self.subTest(token=token), tempfile.TemporaryDirectory() as folder:
                with patch.object(chess.Board, 'parse_san', parse_san):
                    scope = generate(Path(folder) / 'sequence.html', f'{token} (meme) Rf7+(0.8s)')
                self.assertEqual(received, ['Bxh4', 'Rf7+'])
                self.assertEqual([event['type'] for event in scope['timeline']], ['move', 'meme', 'move'])
                self.assertEqual(scope['moves'][0]['annotation'], '??')
                self.assertEqual(scope['moves'][0]['start_meme'], '(meme)' in token)
                self.assertEqual(scope['moves'][1]['pause'], 0.8)


if __name__ == '__main__':
    unittest.main()
