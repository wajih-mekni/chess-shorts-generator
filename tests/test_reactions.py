"""Stage 4 metadata/configuration contracts."""
from pathlib import Path
import sys,unittest
import chess
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.renderer.chess_state import compile_sequence
from src.renderer.composition import render_scene
from src.renderer.reactions import reaction_config
from src.generate_reaction_demo import examples

class ReactionTests(unittest.TestCase):
    def test_capture_metadata(self):
        scene=compile_sequence(chess.Board(),'e4 a6 e5 d5 exd6',0)
        move=scene['moves'][-1]
        self.assertEqual((move['capture'],move['to']),('d5','d6'))
        self.assertEqual((move['captured_kind'],move['captured_color']),('pawn','black'))
        self.assertTrue(move['en_passant'])
        mate=compile_sequence(chess.Board(),'f3 e5 g4 Qh4#',0)['moves'][-1]
        self.assertTrue(mate['checkmate'])
        self.assertEqual(mate['checked_king'],'e1')

    def test_profiles_and_overrides(self):
        self.assertEqual(reaction_config()['profile'],'LEGACY')
        config=reaction_config('REFERENCE')
        self.assertEqual(config['defaults'],{'capture':'CAPTURE_TUMBLE','king':'KING_RECOIL'})
        with self.assertRaisesRegex(ValueError,'profile'):reaction_config('typo')
        scene=examples()[0][1]
        scene['moves'][0]['capture_reaction']='KING_RECOIL'
        with self.assertRaisesRegex(ValueError,'capture reaction'):render_scene(scene)
        scene['moves'][0]['capture_reaction']='NONE'
        html=render_scene(scene,reaction_profile='REFERENCE')
        self.assertNotIn('${',html)
        self.assertIn('CAPTURE_TUMBLE',html)

if __name__=='__main__':unittest.main()
