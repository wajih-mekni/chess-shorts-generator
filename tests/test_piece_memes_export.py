"""Export a real muted piece video and verify its pixels in the captured MP4."""
from pathlib import Path
import json
import subprocess
import sys
import tempfile
import chess
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.renderer.chess_state import compile_sequence
from src.renderer.composition import render_scene


def main():
    with tempfile.TemporaryDirectory(prefix='piece-media-',dir=ROOT/'assets') as assets, tempfile.TemporaryDirectory(prefix='piece-export-',dir=ROOT/'output') as folder:
        video=Path(assets)/'pink.mp4'
        subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','color=c=magenta:s=64x64:r=30','-f','lavfi','-i','sine=frequency=997:sample_rate=48000','-t','2',
                        '-c:a','aac','-c:v','libx264','-pix_fmt','yuv420p',str(video)],check=True)
        scene=compile_sequence(chess.Board(),'Nf3^N@J(piece:Pink,when=land,dur=1.4,audio=true)(0s)')
        html=render_scene(scene,directing_profile='AUTO',meme_mode='off',piece_meme_mode='on',
                          initial_piece_memes=[dict(square='e8',meme='Pink',hold=True,loop=True)],
                          piece_memes={'Pink':dict(src=video.relative_to(ROOT).as_posix(),type='video')})
        path=Path(folder)/'scene.html';path.write_text(html.replace('../assets/','../../assets/'))
        output=Path(folder)/'clip.mp4'
        subprocess.run([sys.executable,str(ROOT/'src/export_video.py'),'--html',str(path),'--output',str(output),'--fps','60'],check=True,timeout=60)
        info=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_format','-of','json',str(output)]))
        duration=float(info['format']['duration'])
        assert duration>=1.4,duration
        # Full-board safe layout: board x=136,y=556,size=808. Knight lands on f3.
        x=round(136+808*5.5/8);y=round(556+808*5.5/8)
        pixel=subprocess.check_output(['ffmpeg','-v','error','-ss',str(duration-.5),'-i',str(output),'-frames:v','1',
            '-vf',f'crop=2:2:{x}:{y},scale=1:1','-pix_fmt','rgb24','-f','rawvideo','-'])
        assert pixel[0]>180 and pixel[1]<65 and pixel[2]>180,list(pixel)
        # The held initial king face remains through the timed tail, without hanging export.
        x=round(136+808*4.5/8);y=round(556+808*.5/8)-8
        pixel=subprocess.check_output(['ffmpeg','-v','error','-ss',str(duration-.5),'-i',str(output),'-frames:v','1',
            '-vf',f'crop=2:2:{x}:{y},scale=1:1','-pix_fmt','rgb24','-f','rawvideo','-'])
        assert pixel[0]>180 and pixel[1]<65 and pixel[2]>180,list(pixel)
        assert duration<10,duration
        # Detect the source's 997Hz tone late in the overlay, after chess SFX.
        import array, math
        raw=subprocess.check_output(['ffmpeg','-v','error','-ss',str(duration-.6),'-i',str(output),
            '-t','0.3','-vn','-ac','1','-ar','8000','-f','f32le','-'])
        samples=array.array('f',raw)
        magnitude=2*abs(sum(value*complex(math.cos(2*math.pi*997*i/8000),
                          math.sin(2*math.pi*997*i/8000)) for i,value in enumerate(samples)))/len(samples)
        assert magnitude>.025,('piece audio missing',magnitude)
        print('PASS: held initial face and timed overlay in 60 fps MP4 contains piece video; export waits for overlay tail',flush=True)

if __name__=='__main__':main()
