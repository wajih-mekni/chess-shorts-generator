"""Piece-meme parser, registry, off-mode equivalence and production switch."""
from itertools import permutations
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import chess
from src.renderer.chess_state import compile_sequence
from src.renderer.composition import render_scene
from src.renderer.piece_memes import PIECE_MEME_DEFAULTS
from src import generate_sequence_animation as production

REGISTRY = {
    'Face': dict(src='assets/pieces/wQ.svg',type='image'),
    'Laugh': dict(src='assets/memes/hikaruLaughExecuseme.mp4',type='video'),
}


def config(html):
    return json.loads(html.split('const pieceMemeConfig = ')[1].split(';\n')[0])


class PieceMemeTests(unittest.TestCase):
    def test_parser_and_existing_directives(self):
        for tier in ('^N','^A','^VA'):
            for parts in permutations(['!!',tier,'~jump','@K','(piece:Laugh)']):
                move=compile_sequence(chess.Board(),'Nf3'+''.join(parts)+'(meme)(0s)')['moves'][0]
                self.assertEqual(move['piece_meme'],{'id':'Laugh'})
                self.assertEqual((move['annotation'],move['camera_directive'],move['choreography_preset']),('!!','K','KNIGHT_JUMP'))
                self.assertEqual(move['pause'],0)
                self.assertTrue(move['start_meme'])
        move=compile_sequence(chess.Board(),'Nf3(piece:Laugh,when=start,dur=1.2,scale=1.5,x=-10,y=8,shape=circle,loop=true)')['moves'][0]
        self.assertEqual(move['piece_meme'],dict(id='Laugh',when='start',dur=1.2,scale=1.5,x=-10,y=8,shape='circle',loop=True))
        self.assertNotIn('piece_meme',compile_sequence(chess.Board(),'e4')['moves'][0])

    def test_off_equivalence(self):
        plain=compile_sequence(chess.Board(),'Nf3!!^VA~jump@K(meme)(0s)')
        decorated='Nf3!!^VA~jump@K(piece:Missing,dur=bad,follow=position)(meme)(0s)'
        off=compile_sequence(chess.Board(),decorated,piece_meme_mode='off')
        self.assertEqual(off,plain)
        enabled=compile_sequence(chess.Board(),'Nf3!!^VA~jump@K(piece:Missing)(meme)(0s)')
        opts=dict(meme_path='../assets/memes/Cr7.mp4',directing_profile='AUTO')
        self.assertEqual(render_scene(enabled,**opts),render_scene(plain,**opts))
        self.assertFalse(config(render_scene(enabled))['enabled'])
        self.assertEqual(config(render_scene(enabled))['entries'],{})

    def test_serialization_and_validation(self):
        scene=compile_sequence(chess.Board(),'e4(piece:Face) e5(piece:Laugh,when=start,dur=1.1,loop=true)')
        original=json.dumps(scene)
        html=render_scene(json.loads(original),piece_meme_mode='on',piece_memes=REGISTRY)
        entries=config(html)['entries']
        self.assertEqual(entries['0'],dict(PIECE_MEME_DEFAULTS,id='Face',type='image',src='../assets/pieces/wQ.svg',placement={}))
        self.assertEqual(entries['1']['type'],'video')
        self.assertEqual(entries['1']['dur'],1.1)
        self.assertTrue(entries['1']['loop'])
        data=json.loads(html.split('const scene = ')[1].split(';\n')[0])
        self.assertEqual(data['timeline'][0]['move']['piece_meme'],'0')
        self.assertEqual(json.dumps(scene),original)
        with self.assertRaisesRegex(ValueError,'Unknown piece meme ID'):
            render_scene(scene,piece_meme_mode='on')
        for registry in [dict(Face={'src':'https://example.com/a.png','type':'image'}),
                         dict(Face={'src':'assets/../README.md','type':'image'}),
                         dict(Face={'src':'assets/missing.png','type':'image'}),
                         dict(Face={'src':'assets/pieces/wQ.svg','type':'audio'})]:
            with self.assertRaises(ValueError):render_scene(scene,piece_meme_mode='on',piece_memes=registry)
        for option in ['dur=-1','dur=nan','scale=0','x=inf','when=later','loop=yes','follow=position','shape=bad','typo=2','dur=1,dur=2']:
            with self.assertRaises(ValueError):compile_sequence(chess.Board(),'e4(piece:Face,'+option+')')
        for token in ['e4(piece:Face','e4(piece:assets/x.png)']:
            with self.assertRaises(ValueError):compile_sequence(chess.Board(),token)

    def test_square_targets_and_multiple(self):
        line = 'e4(pm:e8:Laugh,when=start)(pm:h8:Face,scale=.65,y=-5)(piece:Face)'
        scene = compile_sequence(chess.Board(), line)
        directives = scene['moves'][0]['piece_meme']
        self.assertEqual([d.get('target') for d in directives], ['e8','h8',None])
        rendered = render_scene(scene,piece_meme_mode='on',piece_memes=REGISTRY)
        entries = config(rendered)['entries']
        self.assertEqual(len(entries),3)
        self.assertEqual(entries['0:1']['placement'],dict(scale=.65,y=-5))
        self.assertLessEqual(config(rendered)['anchors']['king']['scale'],.5)
        plain = compile_sequence(chess.Board(),'e4')
        self.assertEqual(compile_sequence(chess.Board(),line,piece_meme_mode='off'),plain)
        self.assertEqual(render_scene(scene),render_scene(plain))
        self.assertEqual(compile_sequence(chess.Board(),'e4(pm:z9:Missing,dur=bad)',piece_meme_mode='off'),plain)
        for target in ('z9', 'E8', 'e0', 'e8:Face:Other', ''):
            with self.assertRaises(ValueError):
                compile_sequence(chess.Board(),'e4(pm:'+target+':Face)')

    def test_global_production_switch(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(production,'PIECE_MEME_MODE','off'):
            path=Path(folder)/'scene.html'
            production.generate(path,start_fen=chess.STARTING_FEN,sequence='e4(piece:Missing)')
            self.assertFalse(config(path.read_text())['enabled'])
            with patch.object(production,'PIECE_MEME_MODE','on'),patch.object(production,'PIECE_MEMES',REGISTRY),patch.object(production,'INITIAL_PIECE_MEMES',[]):
                production.generate(path,start_fen=chess.STARTING_FEN,sequence='e4(piece:Face)')
                self.assertTrue(config(path.read_text())['enabled'])


if __name__=='__main__':unittest.main()
