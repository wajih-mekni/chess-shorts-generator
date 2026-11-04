"""Held/removal syntax, initial config, conflicts and disabled equivalence."""
import unittest
import chess
from src.renderer.chess_state import compile_sequence
from src.renderer.piece_memes import configure_piece_memes
from src.renderer.composition import render_scene

REGISTRY = {'Face': dict(src='assets/pieces/wQ.svg', type='image')}

class PersistenceTests(unittest.TestCase):
    def test_hold_removal_and_conflicts(self):
        scene=compile_sequence(chess.Board(),'e4(piece:Face,hold=true)(pm:e8:Face,hold=true)(pm-remove:a8,when=start)')
        directives=scene['moves'][0]['piece_meme']
        self.assertTrue(directives[0]['hold'])
        self.assertEqual(directives[2],dict(remove=True,target='a8',when='start'))
        _,config=configure_piece_memes(scene,'on',REGISTRY)
        self.assertNotIn('src',config['entries']['0:2'])
        for directive in ('piece:Face,dur=1,hold=true','pm:e8:Face,hold=yes','pm-remove:z8','pm-remove:e8,dur=1','pm-remove:e8,when=bad'):
            with self.assertRaises(ValueError):compile_sequence(chess.Board(),'e4('+directive+')')
        held=compile_sequence(chess.Board(),'e4(piece:Face,hold=true)')
        with self.assertRaisesRegex(ValueError,'dur and hold'):
            configure_piece_memes(held,'on',{'Face':dict(REGISTRY['Face'],dur=2)})
        self.assertFalse(compile_sequence(chess.Board(),'e4(piece:Face,dur=1,hold=false)')['moves'][0]['piece_meme']['hold'])

    def test_audio_option(self):
        scene=compile_sequence(chess.Board(),'e4(piece:Face,audio=true)(pm:e8:Face,audio=false,hold=true)')
        _,config=configure_piece_memes(scene,'on',REGISTRY)
        self.assertTrue(config['entries']['0:0']['audio'])
        self.assertFalse(config['entries']['0:1']['audio'])
        with self.assertRaisesRegex(ValueError,'audio must be true or false'):
            compile_sequence(chess.Board(),'e4(piece:Face,audio=yes)')
        plain=compile_sequence(chess.Board(),'e4')
        self.assertEqual(compile_sequence(chess.Board(),'e4(piece:Face,audio=bad)',piece_meme_mode='off'),plain)

    def test_initial_and_disabled(self):
        scene=compile_sequence(chess.Board(),'e4(pm-remove:e8)')
        initial=[dict(square='e8',meme='Face',hold=True,scale=.4)]
        _,config=configure_piece_memes(scene,'on',REGISTRY,initial)
        self.assertEqual(config['initial'],['initial:0'])
        self.assertTrue(config['entries']['initial:0']['hold'])
        plain=compile_sequence(chess.Board(),'e4')
        self.assertEqual(render_scene(scene,initial_piece_memes=initial),render_scene(plain))
        self.assertEqual(compile_sequence(chess.Board(),'e4(pm-remove:bad)(piece:X,hold=bad)',piece_meme_mode='off'),plain)
        for entry in [dict(square='z0',meme='Face'),dict(square='e8'),dict(square='e8',meme='Face',when='start'),dict(square='e8',meme='Face',dur=1,hold=True)]:
            with self.assertRaises(ValueError):configure_piece_memes(plain,'on',REGISTRY,[entry])
        self.assertEqual(render_scene(plain,initial_piece_memes=[]),render_scene(plain))

if __name__=='__main__':unittest.main()
