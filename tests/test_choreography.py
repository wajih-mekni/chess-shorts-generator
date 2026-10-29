"""Configuration and compiler contracts for opt-in piece choreography."""
from pathlib import Path
import sys
import unittest
import chess
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.renderer.choreography import choreography_config
from src.renderer.chess_state import compile_sequence
from src.renderer.composition import render_scene


class ChoreographyTests(unittest.TestCase):
    def test_metadata_and_explicit_selection(self):
        board=chess.Board()
        before=board.fen()
        scene=compile_sequence(board,'e4 e5 Nf3@K Nc6 Bc4',.1)
        self.assertEqual(board.fen(),before)
        self.assertEqual([m['piece_kind'] for m in scene['moves']],['pawn','pawn','knight','knight','bishop'])
        self.assertEqual([m['piece_color'] for m in scene['moves']],['white','black','white','black','white'])
        scene['moves'][2]['choreography_preset']='KNIGHT_JUMP'
        html=render_scene(scene,choreography_profile='REFERENCE')
        self.assertIn('KNIGHT_JUMP',html)
        self.assertNotIn('${',html)
        scene['moves'][2]['choreography_preset']='typo'
        with self.assertRaisesRegex(ValueError,'Unknown choreography preset'):
            render_scene(scene)
        with self.assertRaisesRegex(ValueError,'profile'):
            choreography_config('typo')

    def test_spin_phase_contract(self):
        config=choreography_config()
        self.assertEqual(config['profile'],'LEGACY')
        self.assertEqual(len(config['presets']),7)
        for name,p in config['presets'].items():
            if p['kind']=='spin':
                with self.subTest(name=name):
                    self.assertEqual(p['duration'],sum(p[k] for k in ['launch','hang','finish','settle']))
                    self.assertEqual(p['hang'],130)
                    self.assertLess(p['finish'],p['launch'])
                    self.assertGreater(p['settle'],0)

if __name__=='__main__': unittest.main()
