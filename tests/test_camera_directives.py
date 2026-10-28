from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import chess
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.renderer.chess_state import compile_sequence, parse_camera_directive, parse_move_token


class CameraDirectiveTests(unittest.TestCase):
    def test_suffix_orders(self):
        for token in ['Nf3!!@K(0.8s)(meme)', 'Nf3@K!!(0.8s)(meme)', 'Nf3!!(0.8s)(meme)@K']:
            stripped, directive = parse_camera_directive(token)
            self.assertEqual(directive, 'K')
            self.assertEqual(parse_move_token(stripped,2), ('Nf3','!!',0.8,True))
        self.assertEqual(parse_camera_directive('O-O@J'), ('O-O','J'))
        self.assertEqual(parse_camera_directive('a8=Q+@L'), ('a8=Q+','L'))
        for token in ['e4@X','e4@K@L','e@K4','e4@','@K']:
            with self.assertRaises(ValueError): parse_camera_directive(token)

    def test_san_and_timeline(self):
        received=[]
        original=chess.Board.parse_san
        def parse(board, san):
            received.append(san)
            return original(board,san)
        with patch.object(chess.Board,'parse_san',parse):
            scene=compile_sequence(chess.Board(),'e4 e5 Nf3!!@K Nc6 Bc4@L Nf6@J (meme)',0.2)
        self.assertEqual(received,['e4','e5','Nf3','Nc6','Bc4','Nf6'])
        self.assertEqual([m['camera_directive'] for m in scene['moves']],[None,None,'K',None,'L','J'])
        self.assertIs(scene['moves'][2],scene['timeline'][2]['move'])
        self.assertEqual(scene['moves'][2]['annotation'],'!!')
        self.assertEqual(scene['timeline'][-1], {'type':'meme'})
