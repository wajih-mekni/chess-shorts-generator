"""Compose the static scene and inline runtime into a portable HTML preview."""
import json
from html import escape
from pathlib import Path
from string import Template
from . import layout
from .motion import movement_presets
from .camera import camera_config, CAMERA_OVERSCAN

ASSETS = Path(__file__).parent
RUNTIME_ORDER = ("board", "camera", "motion", "pieces", "effects", "media", "audio", "timeline")


def render_scene(scene, *, meme_path=None, meme_volume=0.25,
                 meme_comment_text=None, music_path=None, music_volume=0.8, movement_preset="NORMAL_MOVE", camera_enabled=None):
    presets = movement_presets()
    if movement_preset not in presets:
        raise ValueError(f"Unknown movement preset: {movement_preset}")
    meme_video = (
        f'<video id="memeVideo" src="{escape(meme_path, quote=True)}" '
        'preload="auto" loop playsinline></video>'
        if meme_path else ""
    )

    meme_comment = (
        f'<div class="meme-comment">{escape(meme_comment_text)}</div>'
        if meme_comment_text else ""
    )

    music_audio = (
        f'<audio id="backgroundMusic" src="{escape(music_path, quote=True)}" '
        'preload="auto" loop></audio>'
        if music_path else ""
    )


    values = {name: value for name, value in vars(layout).items() if name.isupper()}
    values.update(CAMERA_OVERSCAN=CAMERA_OVERSCAN, SQUARE_SIZE=layout.BOARD_LOGICAL_SIZE / 8,
                  CAPTION_RIGHT=max(24, layout.MEME_X + layout.MEME_WIDTH -
                                    (layout.CANVAS_WIDTH - layout.RIGHT_UI_SAFE_AREA)),
                  meme_video=meme_video, meme_comment=meme_comment, music_audio=music_audio)
    data = {"scene": scene,
            "cameraConfig": camera_config(camera_enabled),
            "motion": {"presets": presets, "defaultPreset": movement_preset},
            "media": {"memeVolume": meme_volume, "musicVolume": music_volume},
            "layout": {"squareSize": layout.BOARD_LOGICAL_SIZE / 8,
                       "labelRight": (layout.CANVAS_WIDTH - layout.RIGHT_UI_SAFE_AREA -
                                      layout.BOARD_X) / layout.BOARD_SCALE}}
    # Escape '<' so user content cannot terminate the inline script element.
    runtime = "\n".join("const " + name + " = " + json.dumps(value).replace("<", "\\u003c") + ";"
                        for name, value in data.items())
    runtime += """
const initialPieces = scene.pieces;
const moves = scene.moves;
const timeline = scene.timeline;
const hasMemeTriggers = timeline.some(event =>
    event.type === "meme" || event.move?.start_meme);
"""
    runtime += "\n" + "\n".join((ASSETS / (name + ".js")).read_text() for name in RUNTIME_ORDER)
    runtime += "\ncamera.reset();\ncreatePieces();\n"
    values["runtime"] = runtime
    values["styles"] = Template((ASSETS / "scene.css").read_text()).substitute(values)
    return Template((ASSETS / "scene.html").read_text()).substitute(values)
