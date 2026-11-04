"""Production entry point: edit START_FEN / SEQUENCE, then run this file.

Default output is cinematic HTML. Add --video for MP4 using the existing exporter.
"""
from pathlib import Path
import argparse
import os
import subprocess
import sys
import chess

try:
    from .renderer.chess_state import compile_sequence, parse_move_token, split_annotated_san
    from .renderer.composition import render_scene
    from .renderer.directing import DIRECTING_PROFILE
except ImportError:
    from renderer.chess_state import compile_sequence, parse_move_token, split_annotated_san
    from renderer.composition import render_scene
    from renderer.directing import DIRECTING_PROFILE

ROOT = Path(__file__).resolve().parents[1]
DEMO_FEN = chess.STARTING_FEN
# Legal Italian/Fried Liver line. Annotations are artistic input, not engine scores.
DEMO_SEQUENCE = 'Bd3+(pm:b1:YesYes,hold=true,shape=circle,audio=true)(0.3s) Ka2^N(0.3s) Bc4+^N(0.3s) Kb1^N(0.3s) Bb3!^N(pm-remove:b1)(pm:b1:WtfIsGoingOnHere,dur=3,shape=circle,audio=true)(pm:h4:SusDog,dur=3,shape=circle,audio=true)(0.3s) a2^N Kg5!^N Kc1^N(pm:g5:HikaruLaugh,dur=9,shape=circle,audio=true) Kg4+!^N Kb1^N Kf4!^N Kc1^N(pm:c1:MonkeyCry,hold=true,shape=circle,audio=true) Ke4+!^N Kb1^N Ke3!^N Kc1^N Kd3+!^N Kb1^N Bc2#'
START_FEN = "8/8/7B/8/2B4K/p7/1p6/bk6 w - - 0 1"
SEQUENCE = DEMO_SEQUENCE
OUTPUT_PATH = ROOT / 'output/sequence_demo.html'
MEME_MODE = "off"  # "fixed" or "off"; "piece" is reserved for future support.
LAYOUT_MODE = "safe"  # "safe" or "crop" for MEME_MODE="off"; fixed memes keep their layout.
MEME_PATH = '../assets/memes/LevySacTheQueen.mp4'  # None disables only the video.
# Independent from the existing reaction panel. Register local paths once here.
PIECE_MEME_MODE = "on"

INITIAL_PIECE_MEMES = []

PIECE_MEMES = {
    "YesYes": {
        "src": "assets/memes/meme_source.mp4",
        "type": "video",
    },

    "HikaruLaugh": {
        "src": "assets/memes/hikaruLaughExecuseme.mp4",
        "type": "video",
    },

    "MonkeyCry": {
        "src": "assets/memes/MonkeyCry.mp4",
        "type": "video",
    },

    "WaitAMinute": {
        "src": "assets/memes/WaitAMinute.mp4",
        "type": "video",
    },

    "SusDog": {
        "src": "assets/memes/SusDog.mp4",
        "type": "video",
    },

    "CR7": {
        "src": "assets/memes/Cr7.mp4",
        "type": "video",
    },

    "HikaruFace": {
        "src": "assets/memes/piece_meme_demo.png",
        "type": "image",
    },
    "WtfIsGoingOnHere": {
    "src": "assets/memes/WtfIsGoingOnHere.mp4",
    "type": "video",
},
}

MEME_VOLUME = .35
MEME_COMMENT = ''
MUSIC_PATH = None
MUSIC_VOLUME = .8
BRILLIANT_MODE = "standard"  # "aggressive" boosts !!; ^A forces it per move, ^N stays NORMAL.
INITIAL_DELAY = 0.0  # Seconds to show the starting board before the sequence (e.g. 2.5).
DEFAULT_PAUSE = 2  # LEGACY fallback only; AUTO uses tier pacing unless (Xs) is authored.


# ============================================================
# CINEMATIC SEQUENCE CHEAT SHEET
# ============================================================
#
# BASIC MOVE:
#   Nf3
#   Bc4
#   Qxh7+
#
#
# ---------- IMPORTANCE / DIRECTOR ----------
#
#   !       Tactical / important move
#   !!      HERO / brilliant move
#   !!^A    Existing aggressive HERO
#   !!^VA   Very aggressive HERO: 720-degree spin + zoom + aggressive rocking
#   !!^N    NORMAL override
#   ?       Negative/danger treatment
#   ??      Strong negative/danger treatment
#   !?      Interesting / tension
#   ?!      Dubious / tension
#
# Examples:
#   Bxf7+!
#   Qh7!!
#   Qe5?!
#
# Automatic effects:
#
#   NORMAL:
#       restrained camera + normal choreography + local effects
#
#   ! / capture / check:
#       TACTICAL
#       stronger camera + reactions + lighting + medium hold
#
#   !!:
#       HERO
#       strong camera tremble/kick
#       zoom pulse
#       strong choreography
#       whole-board color wash
#       bloom + flash + rings + particles
#       long hero hold
#
#
# ---------- CAMERA ----------
#
#   @J      Wide shot
#   @K      Medium shot
#   @L      Close / hero shot
#
# Without @J/@K/@L:
#   the automatic director chooses the camera.
#
# Examples:
#   Nf3@K
#   Bxf7+!@K
#   Qh7!!@L
#
# NOTE:
# There is currently no "~tremble" command.
# Strong trembling / camera impact is automatically selected
# for TACTICAL/HERO moves, especially !!.
#
#
# ---------- PIECE CHOREOGRAPHY OVERRIDES ----------
#
#   ~lift
#       LIFT_MOVE
#       Example: e4~lift
#
#   ~jump
#       KNIGHT_JUMP
#       Example: Nf3~jump
#
#   ~sweep
#       BISHOP_SWEEP
#       Example: Bc4~sweep
#
#   ~spin
#       SPIN_WITH_HANG
#       Example: Qh5~spin
#
#   ~flip
#       ROOK_FLIP
#       Example: Rd7~flip
#
#   ~rook-spin
#       ROOK_FLIP
#       Example: Rxd5~rook-spin
#
#   ~queen-spin
#       QUEEN_SPIN
#       Example: Qg3!!~queen-spin
#
#   ~bishop-spin
#       BISHOP_SPIN
#       Example: Bxf7+!~bishop-spin
#
#   ~legacy
#       Original / old movement animation
#       Example: Nf3~legacy
#
#
# ---------- MANUAL PAUSES ----------
#
#   (Xs)
#
# Adds an authored pause.
#
# Examples:
#   Qh7!!(2s)
#   Rxf7+!(1.2s)
#
# Automatic NORMAL / TACTICAL / HERO holds already exist,
# so only use this when you specifically want custom timing.
#
#
# ---------- MEME ----------
#
#   (meme)
#
# Triggers the existing authored meme behavior.
#
# Example:
#   Qh7!!@L(meme)
#
#
# ---------- COMBINATIONS ----------
#
# You can combine directives:
#
#   Nf3~jump@K
#
#       knight jump
#       + forced medium camera
#
#
#   Bxf7+!~bishop-spin@K
#
#       check + tactical
#       + forced bishop spin
#       + medium camera
#
#
#   Rxe7+!!~flip@L
#
#       HERO
#       + rook flip
#       + close camera
#       + automatic hero lighting/tremble/particles
#
#
#   Qxh7+!!~queen-spin@L(2.5s)
#
#       HERO
#       + queen spin
#       + close camera
#       + custom 2.5 second pause
#
#
# ---------- AUTOMATIC REACTIONS ----------
#
# You DON'T need to specify these manually.
#
# Captures automatically get:
#   shrink / tumble / knockback
#
# Checks automatically get:
#   king recoil / tilt / recovery
#
# Hero/tactical moves automatically get appropriate:
#   camera impact
#   colors
#   glow
#   flashes
#   particles
#   rings
#
#
# ---------- COLORS ----------
#
# Automatic defaults:
#
#   !!          -> cyan HERO
#   check       -> red
#   ? / ??      -> red
#   !? / ?!     -> orange
#   positive/capture contexts -> green where selected by director
#
#
# ---------- LAYOUT ----------
#
# Original meme version:
#   MEME_MODE = "fixed"
#   LAYOUT_MODE = "safe"
#
# No meme + full board visible:
#   MEME_MODE = "off"
#   LAYOUT_MODE = "safe"
#
# No meme + huge cinematic cropped board:
#   MEME_MODE = "off"
#   LAYOUT_MODE = "crop"
#
#
# ---------- EXAMPLE ----------
#
# SEQUENCE = (
#     "e4 "
#     "e5 "
#     "Nf3~jump@K "
#     "Nc6 "
#     "Bc4~sweep "
#     "Nf6 "
#     "Bxf7+!~bishop-spin@K "
#     "Kxf7 "
#     "Qh5+!!~queen-spin@L"
# )
#
# ============================================================

def generate(output=OUTPUT_PATH, *, start_fen=None, sequence=None, directing_profile=DIRECTING_PROFILE, brilliant_mode=None, initial_delay=None, piece_meme_mode=None, initial_piece_memes=None):
    board = chess.Board(START_FEN if start_fen is None else start_fen)
    piece_mode = PIECE_MEME_MODE if piece_meme_mode is None else piece_meme_mode
    scene = compile_sequence(board, SEQUENCE if sequence is None else sequence, DEFAULT_PAUSE,
                             piece_meme_mode=piece_mode)
    legacy = dict(timing_profile='LEGACY', choreography_profile='LEGACY',
                  reaction_profile='LEGACY', lighting_profile='LEGACY') if directing_profile=='LEGACY' else {}
    html = render_scene(scene, directing_profile=directing_profile, **legacy,
                        piece_meme_mode=piece_mode, piece_memes=PIECE_MEMES,
                        initial_piece_memes=INITIAL_PIECE_MEMES if initial_piece_memes is None else initial_piece_memes,
                        initial_delay=INITIAL_DELAY if initial_delay is None else initial_delay,
                        brilliant_mode=BRILLIANT_MODE if brilliant_mode is None else brilliant_mode,
                        meme_mode=MEME_MODE, layout_mode=LAYOUT_MODE,
                        meme_path=MEME_PATH, meme_volume=MEME_VOLUME,
                        meme_comment_text=MEME_COMMENT, music_path=MUSIC_PATH, music_volume=MUSIC_VOLUME)
    output = Path(output).resolve()
    assets = Path(os.path.relpath(ROOT/'assets',output.parent)).as_posix()+'/'
    html = html.replace('../assets/',assets)
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(html,encoding='utf-8')
    return scene


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,help='HTML output path')
    parser.add_argument('--demo',action='store_true',help='Use the built-in legal multi-move Stage 6 demo')
    parser.add_argument('--legacy',action='store_true',help='Disable automatic directing and use legacy rendering profiles')
    parser.add_argument('--brilliant-mode', choices=('standard', 'aggressive'), default=None)
    parser.add_argument('--video',type=Path,help='Also export an MP4 to this path')
    parser.add_argument('--fps',type=int,choices=(30,60),default=30)
    args = parser.parse_args()
    output = args.output or (ROOT/'output/cinematic_demo.html' if args.demo else OUTPUT_PATH)
    generate(output, start_fen=DEMO_FEN if args.demo else None,
             sequence=DEMO_SEQUENCE if args.demo else None,
             directing_profile='LEGACY' if args.legacy else DIRECTING_PROFILE, brilliant_mode=args.brilliant_mode)
    print(f'Created {output}',flush=True)
    if args.video:
        subprocess.run([sys.executable,str(ROOT/'src/export_video.py'),'--html',str(output.resolve()),
                        '--output',str(args.video.resolve()),'--fps',str(args.fps)],check=True,cwd=ROOT)


if __name__=='__main__':main()
