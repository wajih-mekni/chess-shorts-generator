"""Compose the static scene and inline runtime into a portable HTML preview."""
import json
from html import escape
from pathlib import Path
from string import Template
from . import layout
from .motion import movement_presets
from .camera import camera_config, CAMERA_OVERSCAN
from .timing import TIMING_PROFILE, timing_config
from .choreography import CHOREOGRAPHY_PROFILE, choreography_config
from .reactions import REACTION_PROFILE, reaction_config
from .lighting import LIGHTING_PROFILE, lighting_config
from urllib.parse import quote

ASSETS = Path(__file__).parent
RUNTIME_ORDER = ("board", "camera", "camera_impulses", "motion", "choreography", "pieces",
                 "reactions", "effects", "lighting_plan", "particles", "lighting",
                 "media", "audio", "director", "scheduler", "timeline")


def render_scene(scene, *, meme_path=None, meme_volume=0.25,
                 meme_comment_text=None, music_path=None, music_volume=0.8,
                 movement_preset="NORMAL_MOVE", camera_enabled=None,
                 timing_profile=TIMING_PROFILE, choreography_profile=CHOREOGRAPHY_PROFILE,
                 reaction_profile=REACTION_PROFILE, lighting_profile=LIGHTING_PROFILE):
    presets = movement_presets()
    if movement_preset not in presets:
        raise ValueError(f"Unknown movement preset: {movement_preset}")
    choreography = choreography_config(choreography_profile)
    reactions = reaction_config(reaction_profile)
    lighting = lighting_config(lighting_profile)
    for event in scene.get("timeline", []):
        move = event.get("move", {})
        name = move.get("effect_preset", lighting["defaultPreset"])
        if name != "NONE" and name not in lighting["presets"]:
            raise ValueError(f"Unknown effect preset: {name}")
        palette = move.get("effect_palette", lighting["defaultPalette"])
        if palette not in lighting["palettes"]:
            raise ValueError(f"Unknown effect palette: {palette}")
        for key in ("choreography_preset", "rook_choreography_preset"):
            name = event.get("move", {}).get(key)
            if name and name != "LEGACY" and name not in choreography["presets"]:
                raise ValueError(f"Unknown choreography preset: {name}")
        for channel in ("capture", "king"):
            name = event.get("move", {}).get(channel + "_reaction")
            if name is not None and name != "NONE":
                if name not in reactions["presets"] or reactions["presets"][name]["kind"] != channel:
                    raise ValueError(f"Invalid {channel} reaction: {name}")
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
    theme = lighting['theme']
    board_image = '../assets/board.svg'
    if lighting['enabled']:
        svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 8 8">'
               '<defs><pattern id="squares" width="2" height="2" patternUnits="userSpaceOnUse">'
               f'<rect width="2" height="2" fill="{theme["light"]}"/>'
               f'<path d="M1 0h1v1H1zM0 1h1v1H0z" fill="{theme["dark"]}"/>'
               '</pattern></defs><rect width="8" height="8" fill="url(#squares)"/></svg>')
        board_image = 'data:image/svg+xml,' + quote(svg)
    values.update(board_image=board_image,
                  theme_class='lighting-reference' if lighting['enabled'] else '',
                  LIGHT_CANVAS=theme['canvas'], LIGHT_BACKING=theme['backing'])
    values.update(CAMERA_OVERSCAN=CAMERA_OVERSCAN, SQUARE_SIZE=layout.BOARD_LOGICAL_SIZE / 8,
                  CAPTION_RIGHT=max(24, layout.MEME_X + layout.MEME_WIDTH -
                                    (layout.CANVAS_WIDTH - layout.RIGHT_UI_SAFE_AREA)),
                  meme_video=meme_video, meme_comment=meme_comment, music_audio=music_audio)
    data = {"scene": scene,
            "cameraConfig": camera_config(camera_enabled, timing_profile),
            "timingConfig": timing_config(timing_profile),
            "choreographyConfig": choreography,
            "reactionConfig": reactions,
            "lightingConfig": lighting,
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
    runtime += "\ncamera.reset();\ncameraMotion.reset();\ncreatePieces();\n"
    values["runtime"] = runtime
    values["styles"] = Template((ASSETS / "scene.css").read_text() +
                                (ASSETS / "lighting.css").read_text()).substitute(values)
    return Template((ASSETS / "scene.html").read_text()).substitute(values)
